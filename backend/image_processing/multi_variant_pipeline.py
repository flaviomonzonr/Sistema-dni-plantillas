import cv2
import numpy as np
from typing import Dict, Any, Tuple, List, Optional
from dataclasses import dataclass, field
from backend.config import BLUR_THRESHOLD, TARGET_CARD_WIDTH, TARGET_CARD_HEIGHT
from backend.image_processing.perspective import detect_and_warp_card


@dataclass
class ImageVariant:
    name: str
    description: str
    image: np.ndarray  # BGR or Grayscale
    quality_score: float
    is_binary: bool = False


@dataclass
class MultiVariantResult:
    original_bgr: np.ndarray
    warped_bgr: np.ndarray
    variants: Dict[str, ImageVariant] = field(default_factory=dict)
    laplacian_variance: float = 0.0
    is_blurry: bool = False
    has_shadows: bool = False
    has_glare: bool = False
    perspective_corrected: bool = False
    quality_message: str = ""


def calculate_sharpness(gray_img: np.ndarray) -> float:
    """Calculates the variance of the Laplacian as a sharpness metric."""
    laplacian = cv2.Laplacian(gray_img, cv2.CV_64F)
    return float(laplacian.var())


def detect_shadows_and_glare(gray_img: np.ndarray) -> Tuple[bool, bool]:
    """
    Detects presence of strong lighting gradients (shadows) and specular glare.
    """
    # Glare: Percentage of pure saturated white pixels (> 250)
    glare_pixels = np.sum(gray_img > 250)
    total_pixels = gray_img.size
    has_glare = (glare_pixels / total_pixels) > 0.035

    # Shadow gradient: Standard deviation of low-frequency illumination
    small = cv2.resize(gray_img, (64, 64))
    blur = cv2.GaussianBlur(small, (15, 15), 0)
    shadow_std = float(np.std(blur))
    has_shadows = shadow_std > 38.0

    return has_shadows, has_glare


def remove_illumination_gradient(gray_img: np.ndarray) -> np.ndarray:
    """
    Normalizes uneven lighting and shadow gradients across the card surface
    using morphological background division.
    """
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (41, 41))
    background = cv2.morphologyEx(gray_img, cv2.MORPH_OPEN, kernel)
    normalized = cv2.divide(gray_img, background, scale=255)
    return normalized


def apply_gamma_correction(image: np.ndarray, gamma: float = 1.0) -> np.ndarray:
    """Adjusts exposure using non-linear gamma curve."""
    inv_gamma = 1.0 / gamma
    table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in range(256)]).astype("uint8")
    return cv2.LUT(image, table)


def enhance_sharpness_multiscale(image: np.ndarray) -> np.ndarray:
    """Applies multi-scale unsharp masking tuned for ID card typography."""
    gaussian_fine = cv2.GaussianBlur(image, (0, 0), sigmaX=1.0)
    sharp_fine = cv2.addWeighted(image, 1.6, gaussian_fine, -0.6, 0)

    gaussian_med = cv2.GaussianBlur(sharp_fine, (0, 0), sigmaX=2.5)
    sharp_med = cv2.addWeighted(sharp_fine, 1.3, gaussian_med, -0.3, 0)

    kernel_boost = np.array([
        [ 0.0, -0.25,  0.0],
        [-0.25,  2.0, -0.25],
        [ 0.0, -0.25,  0.0]
    ], dtype=np.float32)
    boosted = cv2.filter2D(sharp_med, -1, kernel_boost)
    return boosted


def apply_clahe(gray_img: np.ndarray, clip_limit: float = 3.2, grid_size: int = 8) -> np.ndarray:
    """Applies Contrast Limited Adaptive Histogram Equalization."""
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(grid_size, grid_size))
    return clahe.apply(gray_img)


def deskew_image(gray_img: np.ndarray) -> Tuple[np.ndarray, float]:
    """
    Detects subtle text line orientation angles and straightens the image.
    """
    edges = cv2.Canny(gray_img, 50, 150, apertureSize=3)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 100, minLineLength=80, maxLineGap=10)

    if lines is None or len(lines) == 0:
        return gray_img, 0.0

    angles = []
    for line in lines:
        coords = line[0] if (hasattr(line, "shape") and len(line.shape) > 1) else line
        x1, y1, x2, y2 = int(coords[0]), int(coords[1]), int(coords[2]), int(coords[3])
        angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
        # Keep only near-horizontal lines (-35 to +35 degrees)
        if abs(angle) < 35:
            angles.append(angle)

    if not angles:
        return gray_img, 0.0

    median_angle = float(np.median(angles))
    if abs(median_angle) < 0.4:
        return gray_img, 0.0

    # Rotate around center
    h, w = gray_img.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
    rotated = cv2.warpAffine(gray_img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return rotated, median_angle


def generate_multi_variants(
    image_bytes: bytes,
    blur_threshold: float = BLUR_THRESHOLD,
) -> MultiVariantResult:
    """
    Generates a suite of up to 6 specialized image variants optimized for different
    challenging conditions (glare, cell phone shadows, worn cards, dark lighting, DNIe MRZ).
    """
    nparr = np.frombuffer(image_bytes, np.uint8)
    original_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if original_bgr is None:
        raise ValueError("No se pudo decodificar la imagen enviada. Formato inválido.")

    # 1. Perspective correction & card border detection
    warped_bgr, perspective_corrected = detect_and_warp_card(
        original_bgr,
        target_width=TARGET_CARD_WIDTH,
        target_height=TARGET_CARD_HEIGHT,
    )

    # Convert to grayscale
    gray = cv2.cvtColor(warped_bgr, cv2.COLOR_BGR2GRAY)
    
    # Sharpness & lighting metrics
    sharpness = calculate_sharpness(gray)
    is_blurry = sharpness < blur_threshold
    has_shadows, has_glare = detect_shadows_and_glare(gray)

    variants: Dict[str, ImageVariant] = {}

    # Variant 1: CLAHE + Multiscale Sharpness (Default high precision - Ultra Fast)
    denoised_base = cv2.GaussianBlur(gray, (3, 3), 0.8)
    sharpened_base = enhance_sharpness_multiscale(denoised_base)
    clahe_v1 = apply_clahe(sharpened_base, clip_limit=3.0, grid_size=8)
    variants["clahe_enhanced"] = ImageVariant(
        name="clahe_enhanced",
        description="CLAHE + Realce de Nitidez Multiescala",
        image=clahe_v1,
        quality_score=round(sharpness * 1.5, 1),
    )

    # Variant 2: Shadow-Free / Illumination Flattening (Cell phone photos & flash shadows)
    flat_gray = remove_illumination_gradient(gray)
    denoised_flat = cv2.GaussianBlur(flat_gray, (3, 3), 0.8)
    sharp_flat = enhance_sharpness_multiscale(denoised_flat)
    variants["shadow_free"] = ImageVariant(
        name="shadow_free",
        description="Aplanado de Iluminación y Eliminación de Sombras",
        image=sharp_flat,
        quality_score=round(sharpness * 1.4, 1),
    )

    # Variant 3: Adaptive Gaussian Thresholding (High contrast binary for patterned/blue backgrounds)
    adaptive_thresh = cv2.adaptiveThreshold(
        clahe_v1,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        blockSize=15,
        C=8,
    )
    variants["adaptive_thresh"] = ImageVariant(
        name="adaptive_thresh",
        description="Binarización Adaptativa Gaussian C",
        image=adaptive_thresh,
        quality_score=round(sharpness, 1),
        is_binary=True,
    )

    # Variant 4: Otsu Global Thresholding with morphological stroke boost
    _, otsu_raw = cv2.threshold(clahe_v1, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    # Subtle morphological closing to repair broken character strokes
    kernel_stroke = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    otsu_closed = cv2.morphologyEx(otsu_raw, cv2.MORPH_CLOSE, kernel_stroke)
    variants["otsu_closed"] = ImageVariant(
        name="otsu_closed",
        description="Binarización Otsu con Cierre de Trazos",
        image=otsu_closed,
        quality_score=round(sharpness, 1),
        is_binary=True,
    )

    # Variant 5: Gamma & Contrast Expansion (Underexposed/Dark photos vs Overexposed/Glare)
    mean_brightness = float(np.mean(gray))
    gamma_val = 1.65 if mean_brightness < 110 else 0.75
    gamma_img = apply_gamma_correction(clahe_v1, gamma=gamma_val)
    variants["gamma_contrast"] = ImageVariant(
        name="gamma_contrast",
        description=f"Corrección Gamma (γ={gamma_val}) y Expansión de Rango Dinámico",
        image=gamma_img,
        quality_score=round(calculate_sharpness(gamma_img), 1),
    )

    # Variant 6: Deskewed or Super-Resolution Sharpness
    deskewed_img, deskew_angle = deskew_image(clahe_v1)
    if abs(deskew_angle) >= 0.5:
        variants["deskewed"] = ImageVariant(
            name="deskewed",
            description=f"Enderezamiento Angular ({deskew_angle:+.1f}°)",
            image=deskewed_img,
            quality_score=round(calculate_sharpness(deskewed_img), 1),
        )
    else:
        # 1.35x Bicubic scaling + subtle unsharp mask for recovering low-res small fonts
        h, w = clahe_v1.shape[:2]
        upscaled = cv2.resize(clahe_v1, (int(w * 1.3), int(h * 1.3)), interpolation=cv2.INTER_CUBIC)
        kernel_sr = np.array([[0, -0.3, 0], [-0.3, 2.2, -0.3], [0, -0.3, 0]], dtype=np.float32)
        sr_sharp = cv2.filter2D(upscaled, -1, kernel_sr)
        variants["super_res"] = ImageVariant(
            name="super_res",
            description="Super-Resolución Bicúbica (1.3x) + Realce de Microcaracteres",
            image=sr_sharp,
            quality_score=round(calculate_sharpness(sr_sharp), 1),
        )

    # Quality message
    quality_notes = []
    if is_blurry:
        quality_notes.append(f"baja nitidez ({sharpness:.1f}/{blur_threshold:.0f})")
    if has_shadows:
        quality_notes.append("sombras/iluminación desigual")
    if has_glare:
        quality_notes.append("reflejos de luz")

    if quality_notes:
        quality_message = f"Imagen con {', '.join(quality_notes)}. Pipeline multi-variante compensando activamente."
    else:
        quality_message = f"Calidad de imagen óptima (nitidez: {sharpness:.1f})."

    return MultiVariantResult(
        original_bgr=original_bgr,
        warped_bgr=warped_bgr,
        variants=variants,
        laplacian_variance=round(sharpness, 2),
        is_blurry=is_blurry,
        has_shadows=has_shadows,
        has_glare=has_glare,
        perspective_corrected=perspective_corrected,
        quality_message=quality_message,
    )
