import tempfile
import uuid
from os.path import join
from pathlib import Path
from typing import AnyStr
from ..data_model.SegmentBox import SegmentBox
from ..ditod.VGTTrainer import VGTTrainer
from ..extraction_formats.extract_formula_formats import extract_formula_format
from ..extraction_formats.extract_table_formats import extract_table_format
from ..vgt.get_json_annotations import get_annotations
from ..vgt.get_model_configuration import get_model_configuration
from ..vgt.get_most_probable_pdf_segments import get_most_probable_pdf_segments
from ..vgt.get_reading_orders import get_reading_orders
from ..data_model.PdfImages import PdfImages
from ..configuration import service_logger, JSON_TEST_FILE_PATH, IMAGES_ROOT_PATH
from ..vgt.create_word_grid import create_word_grid, remove_word_grids
from detectron2.checkpoint import DetectionCheckpointer
from detectron2.data.datasets import register_coco_instances
from detectron2.data import DatasetCatalog

# Global variables for lazy loading
_model = None
_configuration = None

def get_model_and_config():
    """Lazy load the model and configuration when first needed"""
    global _model, _configuration
    if _model is None:
        service_logger.info("Loading VGT model and configuration...")
        _configuration = get_model_configuration()
        _model = VGTTrainer.build_model(_configuration)
        DetectionCheckpointer(_model, save_dir=_configuration.OUTPUT_DIR).resume_or_load(
            _configuration.MODEL.WEIGHTS, resume=True
        )
        service_logger.info("VGT model loaded successfully")
    return _model, _configuration

def get_file_path(file_name, extension):
    return join(tempfile.gettempdir(), file_name + "." + extension)

def pdf_content_to_pdf_path(file_content):
    file_id = str(uuid.uuid1())

    pdf_path = Path(get_file_path(file_id, "pdf"))
    pdf_path.write_bytes(file_content)

    return pdf_path

def register_data():
    try:
        DatasetCatalog.remove("predict_data")
    except KeyError:
        pass

    register_coco_instances("predict_data", {}, JSON_TEST_FILE_PATH, IMAGES_ROOT_PATH)

def predict_doclaynet():
    model, configuration = get_model_and_config()  # Get model lazily
    register_data()
    VGTTrainer.test(configuration, model)

def analyze_pdf(file: AnyStr, xml_file_name: str, extraction_format: str = "", keep_pdf: bool = False) -> list[dict]:
    pdf_path = pdf_content_to_pdf_path(file)
    service_logger.info("Creating PDF images")
    pdf_images_list: list[PdfImages] = [PdfImages.from_pdf_path(pdf_path, "", xml_file_name)]
    create_word_grid([pdf_images.pdf_features for pdf_images in pdf_images_list])
    get_annotations(pdf_images_list)
    predict_doclaynet()
    remove_files()
    predicted_segments = get_most_probable_pdf_segments("doclaynet", pdf_images_list, False)
    predicted_segments = get_reading_orders(pdf_images_list, predicted_segments)
    extract_formula_format(pdf_images_list[0], predicted_segments)
    if extraction_format:
        extract_table_format(pdf_images_list[0], predicted_segments, extraction_format)

    if not keep_pdf:
        pdf_path.unlink(missing_ok=True)

    return [
        SegmentBox.from_pdf_segment(pdf_segment, pdf_images_list[0].pdf_features.pages).to_dict()
        for pdf_segment in predicted_segments
    ]

def remove_files():
    PdfImages.remove_images()
    remove_word_grids()
