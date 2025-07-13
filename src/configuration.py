import logging
from pathlib import Path


SRC_PATH = Path(__file__).parent.absolute()
PERSISTED_VOLUME_PATH = "/storage"

handlers = [logging.StreamHandler()]
logging.root.handlers = []
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", handlers=handlers)
service_logger = logging.getLogger(__name__)

IMAGES_ROOT_PATH = Path(SRC_PATH, "images")
WORD_GRIDS_PATH = Path(SRC_PATH, "word_grids")
JSONS_ROOT_PATH = Path(SRC_PATH, "jsons")
PDF_OUTPUTS_PATH = Path(SRC_PATH, "pdf_outputs")
OCR_SOURCE = Path(SRC_PATH, "ocr", "source")
OCR_OUTPUT = Path(SRC_PATH, "ocr", "output")
OCR_FAILED = Path(SRC_PATH, "ocr", "failed")
JSON_TEST_FILE_PATH = Path(JSONS_ROOT_PATH, "test.json")
MODELS_PATH = Path(PERSISTED_VOLUME_PATH, "models")
XMLS_PATH = Path(SRC_PATH, "xmls")

DOCLAYNET_TYPE_BY_ID = {
    1: "Caption",
    2: "Footnote",
    3: "Formula",
    4: "List_Item",
    5: "Page_Footer",
    6: "Page_Header",
    7: "Picture",
    8: "Section_Header",
    9: "Table",
    10: "Text",
    11: "Title",
}
