import os
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = Path(__file__).resolve().parent
UPLOADS_DIR = BASE_DIR / "uploads"
EXPORTS_DIR = BASE_DIR / "exports"
DATA_DIR = BASE_DIR / "data"
TEMPLATES_DIR = BASE_DIR / "templates"
CONTRACTS_DIR = BASE_DIR / "contracts_generated"

# Create required directories if they don't exist
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
CONTRACTS_DIR.mkdir(parents=True, exist_ok=True)

# Database
DB_PATH = DATA_DIR / "records.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

# Master Excel File & Source Data
MASTER_EXCEL_PATH = EXPORTS_DIR / "Registros.xlsx"
DEFAULT_EMAIL_DOMAIN = os.getenv("DEFAULT_EMAIL_DOMAIN", "empresa.com.pe")

# Image Processing Configuration
# Laplacian variance threshold under which the image is considered blurry
BLUR_THRESHOLD = float(os.getenv("BLUR_THRESHOLD", "75.0"))

# Standard ISO/IEC 7810 ID-1 card dimensions (85.60 mm × 53.98 mm -> aspect ratio ~1.586)
TARGET_CARD_WIDTH = 1014
TARGET_CARD_HEIGHT = 640

# OCR Configuration
OCR_ENGINE = os.getenv("OCR_ENGINE", "rapidocr").lower()  # rapidocr, tesseract, cloud_vision, textract
TESSERACT_LANG = os.getenv("TESSERACT_LANG", "spa+eng")

def find_tesseract_binary() -> str | None:
    """Auto-detect Tesseract executable on Windows or Unix systems."""
    custom_path = os.getenv("TESSERACT_PATH")
    if custom_path and os.path.isfile(custom_path):
        return custom_path

    # Common Windows installation locations
    candidate_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Tesseract-OCR\tesseract.exe"),
    ]

    for path in candidate_paths:
        if os.path.isfile(path):
            return path

    # Check PATH
    which_tesseract = shutil.which("tesseract")
    if which_tesseract:
        return which_tesseract

    return None

TESSERACT_CMD = find_tesseract_binary()

# Zona Horaria Oficial: Perú (America/Lima - UTC-5)
from datetime import datetime, timezone, timedelta
PERU_TZ = timezone(timedelta(hours=-5), name="America/Lima")

def get_peru_now() -> datetime:
    """
    Retorna la fecha y hora actual exacta en la zona horaria oficial de Perú (America/Lima, UTC-5).
    No depende de la hora del servidor ni requiere paquetes externos.
    """
    return datetime.now(PERU_TZ)

