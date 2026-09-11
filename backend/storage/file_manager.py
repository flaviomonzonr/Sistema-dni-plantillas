import uuid
import cv2
import numpy as np
from pathlib import Path
from backend.config import UPLOADS_DIR


def save_image_matrix(img_matrix: np.ndarray, prefix: str, suffix: str = ".jpg") -> str:
    """
    Saves an OpenCV BGR image matrix to the uploads folder and returns its filename.
    """
    file_id = f"{uuid.uuid4().hex[:12]}_{prefix}{suffix}"
    dest_path = UPLOADS_DIR / file_id
    cv2.imwrite(str(dest_path), img_matrix, [cv2.IMWRITE_JPEG_QUALITY, 92])
    return file_id


def save_uploaded_bytes(file_bytes: bytes, prefix: str, suffix: str = ".jpg") -> str:
    """
    Saves raw image bytes to the uploads folder and returns its filename.
    """
    file_id = f"{uuid.uuid4().hex[:12]}_{prefix}{suffix}"
    dest_path = UPLOADS_DIR / file_id
    with open(dest_path, "wb") as f:
        f.write(file_bytes)
    return file_id
