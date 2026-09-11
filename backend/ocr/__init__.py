import os
from backend.config import OCR_ENGINE
from backend.ocr.base import BaseOCREngine, OCRResult, OCRLine, OCRWord
from backend.ocr.rapid_engine import RapidOCREngine
from backend.ocr.tesseract_engine import TesseractOCREngine
from backend.ocr.cloud_vision import CloudVisionOCREngine
from backend.ocr.textract import AWSTextractOCREngine


_CACHED_ENGINES = {}


def get_ocr_engine(engine_type: str = OCR_ENGINE) -> BaseOCREngine:
    """
    Retorna la instancia Singleton del motor OCR configurado.
    Reutiliza la instancia en memoria para evitar recargas del modelo ONNX y garantizar velocidad máxima.
    """
    engine_key = (engine_type or OCR_ENGINE or "rapidocr").lower().strip()
    if engine_key in _CACHED_ENGINES:
        return _CACHED_ENGINES[engine_key]
    
    engine_inst = None
    if engine_key == "cloud_vision":
        cv = CloudVisionOCREngine()
        if cv.is_available():
            engine_inst = cv
    elif engine_key == "textract":
        tx = AWSTextractOCREngine()
        if tx.is_available():
            engine_inst = tx
    elif engine_key == "tesseract":
        tess = TesseractOCREngine()
        if tess.is_available():
            engine_inst = tess

    if engine_inst is None:
        # Default / Primary engine: RapidOCR (built-in ONNX runtime)
        rapid = RapidOCREngine()
        if rapid.is_available():
            engine_inst = rapid
        else:
            tess = TesseractOCREngine()
            if tess.is_available():
                engine_inst = tess
            else:
                engine_inst = rapid

    _CACHED_ENGINES[engine_key] = engine_inst
    return engine_inst



__all__ = [
    "BaseOCREngine",
    "OCRResult",
    "OCRLine",
    "OCRWord",
    "RapidOCREngine",
    "TesseractOCREngine",
    "CloudVisionOCREngine",
    "AWSTextractOCREngine",
    "get_ocr_engine",
]

