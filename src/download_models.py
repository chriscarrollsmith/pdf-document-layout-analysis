import math
from os import makedirs
from os.path import join, exists
from pathlib import Path
from urllib.request import urlretrieve
from huggingface_hub import snapshot_download, hf_hub_download

from configuration import service_logger, MODELS_PATH


def download_progress(count, block_size, total_size):
    total_counts = total_size // block_size
    show_counts_percentages = total_counts // 5
    percent = count * block_size * 100 / total_size
    if count % show_counts_percentages == 0:
        service_logger.info(f"Downloaded {math.ceil(percent)}%")


def download_vgt_model(model_name: str):
    service_logger.info(f"Downloading {model_name} model")
    makedirs(MODELS_PATH, exist_ok=True)
    model_path = join(MODELS_PATH, f"{model_name}_VGT_model.pth")
    if exists(model_path):
        return
    download_link = f"https://github.com/AlibabaResearch/AdvancedLiterateMachinery/releases/download/v1.3.0-VGT-release/{model_name}_VGT_model.pth"
    urlretrieve(download_link, model_path, reporthook=download_progress)


def download_embedding_model():
    makedirs(MODELS_PATH, exist_ok=True)
    model_path = join(MODELS_PATH, "layoutlm-base-uncased")
    if exists(model_path):
        return
    makedirs(model_path, exist_ok=True)
    service_logger.info("Embedding model is being downloaded")
    snapshot_download(repo_id="microsoft/layoutlm-base-uncased", local_dir=model_path)


def download_from_hf_hub(path: Path):
    if path.exists():
        return

    file_name = path.name
    makedirs(MODELS_PATH, exist_ok=True)
    makedirs(path.parent, exist_ok=True)
    repo_id = "HURIDOCS/pdf-document-layout-analysis"
    hf_hub_download(repo_id=repo_id, filename=file_name, local_dir=path.parent)


def download_lightgbm_models():
    download_from_hf_hub(Path(MODELS_PATH, "token_type_lightgbm.model"))
    download_from_hf_hub(Path(MODELS_PATH, "paragraph_extraction_lightgbm.model"))
    download_from_hf_hub(Path(MODELS_PATH, "config.json"))


def download_models(model_name: str = "doclaynet"):
    makedirs(MODELS_PATH, exist_ok=True)
    if model_name == "fast":
        download_lightgbm_models()
        return
    download_vgt_model(model_name)
    download_embedding_model()


def are_models_downloaded():
    """Check if both doclaynet and fast models are downloaded"""
    from .configuration import MODELS_PATH
    
    models_path = Path(MODELS_PATH)
    
    # Check doclaynet model
    doclaynet_vgt = models_path / "doclaynet_VGT_model.pth"
    if not doclaynet_vgt.exists():
        return False
    
    # Check embedding model - ensure directory exists and has content
    embedding_dir = models_path / "layoutlm-base-uncased"
    if not embedding_dir.exists():
        return False
    
    try:
        contents = list(embedding_dir.iterdir())
        if not contents:
            return False
    except Exception:
        return False
    
    # Check fast models
    fast_model_files = [
        models_path / "token_type_lightgbm.model",
        models_path / "paragraph_extraction_lightgbm.model",
        models_path / "config.json"
    ]
    all_exist = True
    for f in fast_model_files:
        if not f.exists():
            all_exist = False
    if not all_exist:
        return False
    
    return True


if __name__ == "__main__":
    download_models("doclaynet")
    download_models("fast")
