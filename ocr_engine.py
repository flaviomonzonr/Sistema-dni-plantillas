"""
Módulo raíz ocr_engine.py (Re-exporta backend.ocr_engine)
"""
from backend.ocr_engine import (
    extract_dni_from_bytes,
    process_dni_image,
    preprocess_image,
    get_rapid_ocr_instance,
    extract_dni_number,
    extract_names_and_surnames,
)

__all__ = [
    "extract_dni_from_bytes",
    "process_dni_image",
    "preprocess_image",
    "get_rapid_ocr_instance",
    "extract_dni_number",
    "extract_names_and_surnames",
]
