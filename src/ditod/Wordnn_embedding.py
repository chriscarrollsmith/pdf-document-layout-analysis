import numpy as np
import torch
from torch import nn
from .tokenization_bros import BrosTokenizer
from ..configuration import MODELS_PATH
from pathlib import Path


def _init_weights(m):
    if isinstance(m, nn.Linear):
        # we use xavier_uniform following official JAX ViT:
        torch.nn.init.xavier_uniform_(m.weight)
        if isinstance(m, nn.Linear) and m.bias is not None:
            nn.init.constant_(m.bias, 0)
    elif isinstance(m, nn.LayerNorm):
        nn.init.constant_(m.bias, 0)
        nn.init.constant_(m.weight, 1.0)


class WordnnEmbedding(nn.Module):
    """Generate chargrid embedding feature map."""

    def __init__(
        self,
        vocab_size=30522,
        hidden_size=768,
        embedding_dim=64,
        bros_embedding_path="bros-base-uncased",
        use_pretrain_weight=True,
        use_UNK_text=False,
    ):
        """
        Args：
            vocab_size (int): size of vocabulary.
            embedding_dim (int): dim of input features
        """
        super().__init__()
        
        self.embedding = nn.Embedding(vocab_size, hidden_size)
        self.embedding_proj = nn.Linear(hidden_size, embedding_dim, bias=False)
        self.use_pretrain_weight = use_pretrain_weight
        self.use_UNK_text = use_UNK_text
        self.bros_embedding_path = bros_embedding_path
        self.weights_loaded = False  # Track if weights are loaded
        
        self.apply(_init_weights)

    def _load_weights(self):
        """Lazily load weights when needed"""
        if not self.use_pretrain_weight or self.weights_loaded:
            return

        print(f"Loading weights from {self.bros_embedding_path}")
        state_dict = torch.load(
            Path(MODELS_PATH, self.bros_embedding_path) / "pytorch_model.bin", 
            map_location="cpu",
            weights_only=True
        )

        if "bert" in self.bros_embedding_path:
            word_embs = state_dict["bert.embeddings.word_embeddings.weight"]
        elif "bros" in self.bros_embedding_path:
            word_embs = state_dict["embeddings.word_embeddings.weight"]
        elif "layoutlm" in self.bros_embedding_path:
            word_embs = state_dict["layoutlm.embeddings.word_embeddings.weight"]
        else:
            raise ValueError(f"Unsupported model path: {self.bros_embedding_path}")

        # Get current model device and move weights to it
        device = next(self.parameters()).device
        word_embs = word_embs.to(device)

        # Handle size mismatch by padding or truncating
        current_vocab_size = self.embedding.num_embeddings
        loaded_vocab_size = word_embs.size(0)
        
        if loaded_vocab_size != current_vocab_size:
            print(f"Vocab size mismatch: loaded {loaded_vocab_size}, expected {current_vocab_size}")
            if loaded_vocab_size < current_vocab_size:
                # Pad with random embeddings for the extra tokens
                extra_embeddings = torch.randn(
                    current_vocab_size - loaded_vocab_size, 
                    word_embs.size(1)
                ).to(device) * 0.02  # Small random initialization
                word_embs = torch.cat([word_embs, extra_embeddings], dim=0)
            else:
                # Truncate if somehow we have too many
                word_embs = word_embs[:current_vocab_size]
        
        # Update the existing embedding layer's weights instead of replacing it
        with torch.no_grad():
            self.embedding.weight.copy_(word_embs)
        
        self.weights_loaded = True

    def forward(self, img, batched_inputs, stride=1):
        """Forward computation
        Args:
            img (Tensor): in shape of [B x 3 x H x W]
            batched_inputs (list[dict]):
        Returns:
            Tensor: in shape of [B x N x L x D], where D is the embedding_dim.
        """
        if not self.weights_loaded:
            self._load_weights()

        device = img.device
        batch_b, _, batch_h, batch_w = img.size()

        chargrid_map = torch.zeros((batch_b, batch_h // stride, batch_w // stride), dtype=torch.int64).to(device)

        for iter_b in range(batch_b):
            per_input_ids = batched_inputs[iter_b]["input_ids"]
            per_input_bbox = batched_inputs[iter_b]["bbox"]

            short_length_w = min(len(per_input_ids), len(per_input_bbox))

            if short_length_w > 0:
                for word_idx in range(short_length_w):
                    per_id = per_input_ids[word_idx]

                    bbox = per_input_bbox[word_idx] / stride
                    w_start, h_start, w_end, h_end = bbox.round().astype(int).tolist()

                    if self.use_UNK_text:
                        chargrid_map[iter_b, h_start:h_end, w_start:w_end] = 100
                    else:
                        chargrid_map[iter_b, h_start:h_end, w_start:w_end] = per_id

        chargrid_map = self.embedding(chargrid_map)
        chargrid_map = self.embedding_proj(chargrid_map)

        return chargrid_map.permute(0, 3, 1, 2).contiguous()
