import cv2
import numpy as np
from typing import Dict, Any, Tuple
from dataclasses import dataclass
from backend.config import BLUR_THRESHOLD, TARGET_CARD_WIDTH, TARGET_CARD_HEIGHT
from backend.image_processing.perspective import detect_and_warp_card


@dataclass
class ProcessedImageResult:
    original_bgr: np.ndarray
    warped_bgr: np.ndarray
    grayscale: np.ndarray
    denoised: np.ndarray
    sharpened: np.ndarray
    clahe_enhanced: np.ndarray
    adaptive_thresh: np.ndarray
    otsu_thresh: np.ndarray
    laplacian_variance: float
    is_blurry: bool
    quality_message: str
    perspective_corrected: bool


def calculate_sharpness(gray_img: np.ndarray) -> float:
    """Calculates the variance of the Laplacian as a sharpness metric."""
    laplacian = cv2.Laplacian(gray_img, cv2.CV_64F)
    variance = float(laplacian.var())
    return variance


def remove_illumination_gradient(gray_img: np.ndarray) -> np.ndarray:
    """
    Normalizes uneven lighting and shadow gradients across the card surface
    using morphological background estimation.
    """
    # Morphological opening with large structuring element estimates background lighting
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (41, 41))
    background = cv2.morphologyEx(gray_img, cv2.MORPH_OPEN, kernel)
    # Divide original by background to flatten illumination
    normalized = cv2.divide(gray_img, background, scale=255)
    return normalized


def enhance_sharpness_multiscale(image: np.ndarray) -> np.ndarray:
    """
    Applies multi-scale unsharp masking specifically tuned for fine document typography.
    Crisps up text strokes without amplifying background noise.
    """
    # Fine-scale unsharp mask (sigma=1.0)
    gaussian_fine = cv2.GaussianBlur(image, (0, 0), sigmaX=1.0)
    sharp_fine = cv2.addWeighted(image, 1.6, gaussian_fine, -0.6, 0)

    # Medium-scale unsharp mask for larger titles and DNI numbers
    gaussian_med = cv2.GaussianBlur(sharp_fine, (0, 0), sigmaX=2.5)
    sharp_med = cv2.addWeighted(sharp_fine, 1.3, gaussian_med, -0.3, 0)

    # 3x3 subtle Laplacian edge boost
    kernel_boost = np.array([
        [ 0.0, -0.3,  0.0],
        [-0.3,  2.2, -0.3],
        [ 0.0, -0.3,  0.0]
    ], dtype=np.float32)
    boosted = cv2.filter2D(sharp_med, -1, kernel_boost)
    return boosted


def apply_clahe(gray_img: np.ndarray, clip_limit: float = 3.2, grid_size: int = 8) -> np.ndarray:
    """
    Applies Contrast Limited Adaptive Histogram Equalization (CLAHE).
    """
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(grid_size, grid_size))
    return clahe.apply(gray_img)


def process_id_image(
    image_bytes: bytes,
    blur_threshold: float = BLUR_THRESHOLD
) -> ProcessedImageResult:
    """
    Full 8-stage image enhancement pipeline for Peruvian ID documents.
    Optimized for high-throughput batch processing and maximum OCR readability.
    """
    # Decode bytes to OpenCV BGR image
    nparr = np.frombuffer(image_bytes, np.uint8)
    original_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if original_bgr is None:
        raise ValueError("No se pudo decodificar la imagen enviada. Formato inválido.")

    # 1. Perspective correction & Document boundary detection
    warped_bgr, perspective_corrected = detect_and_warp_card(
        original_bgr,
        target_width=TARGET_CARD_WIDTH,
        target_height=TARGET_CARD_HEIGHT
    )

    # 2. Grayscale conversion
    gray = cv2.cvtColor(warped_bgr, cv2.COLOR_BGR2GRAY)

    # 3. Illumination flattening (removes shadows, flash glare falloff)
    flat_gray = remove_illumination_gradient(gray)

    # 4. Bilateral filtering (noise reduction preserving sharp text edges)
    denoised = cv2.bilateralFilter(flat_gray, d=7, sigmaColor=40, sigmaSpace=40)

    # 5. Multi-scale text stroke sharpening
    sharpened = enhance_sharpness_multiscale(denoised)

    # 6. Contrast & Details enhancement (CLAHE)
    clahe_enhanced = apply_clahe(sharpened, clip_limit=3.2, grid_size=8)

    # 7. Adaptive & Otsu Binarization for high-contrast OCR passes
    adaptive_thresh = cv2.adaptiveThreshold(
        clahe_enhanced,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        blockSize=15,
        C=8
    )
    _, otsu_thresh = cv2.threshold(clahe_enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # 8. Quality detection (Laplacian Variance Sharpness Metric)
    laplacian_var = calculate_sharpness(clahe_enhanced)
    is_blurry = laplacian_var < blur_threshold

    if is_blurry:
        quality_message = (
            f"La imagen presenta baja nitidez o está borrosa (puntaje: {laplacian_var:.1f}/{blur_threshold:.0f}). "
            "Por favor verifique los datos extraídos."
        )
    else:
        quality_message = f"Calidad de imagen óptima (nitidez: {laplacian_var:.1f})."

    return ProcessedImageResult(
        original_bgr=original_bgr,
        warped_bgr=warped_bgr,
        grayscale=gray,
        denoised=denoised,
        sharpened=sharpened,
        clahe_enhanced=clahe_enhanced,
        adaptive_thresh=adaptive_thresh,
        otsu_thresh=otsu_thresh,
        laplacian_variance=round(laplacian_var, 2),
        is_blurry=is_blurry,
        quality_message=quality_message,
        perspective_corrected=perspective_corrected
    )
