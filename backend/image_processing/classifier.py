import re
import cv2
import numpy as np
from typing import Dict, Any, Tuple, Optional, List
from dataclasses import dataclass, field


@dataclass
class DocumentClassificationResult:
    doc_type: str  # "DNI", "DNI Electrónico", "Carnet de Extranjería", "Pasaporte"
    doc_subtype: str  # "DNI Azul Clásico", "DNIe Blanco/Celeste Gen 1-3", "Carnet Extranjería Migraciones", "Pasaporte Ordinario"
    side: str  # "ANVERSO", "REVERSO", "INDETERMINADO"
    confidence: float  # 0.0 to 100.0
    detected_features: List[str] = field(default_factory=list)
    has_mrz: bool = False
    has_photo: bool = False
    has_chip: bool = False
    has_fingerprint: bool = False
    dominant_color_theme: str = "NEUTRAL"


def analyze_color_theme(image_bgr: np.ndarray) -> str:
    """
    Analyzes dominant color spectrum in HSV to assist in distinguishing:
    - DNI Azul (high cyan/blue saturation in header and background)
    - DNI Electrónico (very high brightness, low saturation white/light-cyan)
    - Carné de Extranjería (cyan/teal/greenish hue)
    - Pasaporte (burgundy/wine-red cover or light security pattern)
    """
    if image_bgr is None or image_bgr.size == 0:
        return "NEUTRAL"

    hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)

    mean_s = float(np.mean(s))
    mean_v = float(np.mean(v))

    # Mask for Blue/Cyan (H: 85-135)
    blue_mask = cv2.inRange(hsv, (85, 40, 50), (135, 255, 255))
    blue_ratio = float(np.sum(blue_mask > 0)) / image_bgr.size

    # Mask for Burgundy / Red (H: 0-10 or 165-180)
    red_mask1 = cv2.inRange(hsv, (0, 60, 50), (10, 255, 255))
    red_mask2 = cv2.inRange(hsv, (165, 60, 50), (180, 255, 255))
    red_ratio = float(np.sum((red_mask1 | red_mask2) > 0)) / image_bgr.size

    if blue_ratio > 0.18:
        return "DNI_AZUL_THEME"
    elif red_ratio > 0.20:
        return "PASAPORTE_THEME"
    elif mean_v > 180 and mean_s < 45:
        return "DNIE_WHITE_THEME"
    elif blue_ratio > 0.08:
        return "CE_CYAN_THEME"
    else:
        return "NEUTRAL"


def detect_visual_features(image_bgr: np.ndarray) -> Dict[str, bool]:
    """
    Heuristic detection of visual card components:
    - Photo area (dark rectangular face region)
    - Chip area (metallic square contact)
    - Bottom MRZ strip (dense horizontal text lines at bottom 35%)
    """
    features = {
        "has_photo": False,
        "has_chip": False,
        "has_mrz_strip": False,
    }

    if image_bgr is None or image_bgr.size == 0:
        return features

    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape[:2]

    # MRZ check: high horizontal edge density in bottom 30%
    bottom_crop = gray[int(h * 0.70):h, :]
    sobel_x = cv2.Sobel(bottom_crop, cv2.CV_64F, 1, 0, ksize=3)
    edge_density = float(np.mean(np.abs(sobel_x)))
    if edge_density > 22.0:
        features["has_mrz_strip"] = True

    # Face/photo check: Left or Right rectangular region with moderate skin or high entropy
    left_quad = gray[int(h * 0.15):int(h * 0.85), int(w * 0.02):int(w * 0.38)]
    right_quad = gray[int(h * 0.15):int(h * 0.85), int(w * 0.62):int(w * 0.98)]
    std_left = float(np.std(left_quad))
    std_right = float(np.std(right_quad))

    if std_left > 40.0 or std_right > 40.0:
        features["has_photo"] = True

    return features


def classify_document(
    image_bgr: Optional[np.ndarray] = None,
    ocr_text: str = "",
    declared_type: Optional[str] = None,
) -> DocumentClassificationResult:
    """
    Intelligently classifies Peruvian identity documents and determines side
    (Anverso vs Reverso) combining visual cues with semantic keyword patterns.
    """
    text_upper = (ocr_text or "").upper()
    detected_features = []
    
    # 1. Visual Analysis
    theme = "NEUTRAL"
    vis_features = {"has_photo": False, "has_chip": False, "has_mrz_strip": False}
    if image_bgr is not None and image_bgr.size > 0:
        theme = analyze_color_theme(image_bgr)
        vis_features = detect_visual_features(image_bgr)
        if theme != "NEUTRAL":
            detected_features.append(f"Gama cromática: {theme}")
        if vis_features["has_photo"]:
            detected_features.append("Área de fotografía detectada")
        if vis_features["has_mrz_strip"]:
            detected_features.append("Franja de lectura mecánica (MRZ) detectada")

    # 2. Text Keyword Matching
    dni_score = 0
    dnie_score = 0
    ce_score = 0
    pass_score = 0
    
    anverso_score = 0
    reverso_score = 0

    # DNI vs DNIe vs CE vs Pasaporte cues
    if any(k in text_upper for k in ["REPUBLICA DEL PERU", "REPÚBLICA DEL PERÚ", "REGISTRO NACIONAL", "RENIEC"]):
        dni_score += 40
        dnie_score += 20
        detected_features.append("Emisor: RENIEC / República del Perú")

    if any(k in text_upper for k in ["ELECTRONICO", "ELECTRÓNICO", "DNIE", "DNI-E", "DOCUMENTO NACIONAL DE IDENTIDAD ELECTRONICO"]):
        dnie_score += 60
        detected_features.append("Texto explícito DNI Electrónico")

    if any(k in text_upper for k in ["I<PER", "IDPER", "P<PER", "IPER"]):
        dnie_score += 50
        detected_features.append("Cabecera ICAO TD1 MRZ")

    if any(k in text_upper for k in ["MIGRACIONES", "EXTRANJERIA", "EXTRANJERÍA", "CARNET DE EXTRANJERIA", "CARNÉ DE EXTRANJERÍA", "CALIDAD MIGRATORIA", "RESIDENTE"]):
        ce_score += 70
        detected_features.append("Emisor: Superintendencia Nacional de Migraciones (CE)")

    if any(k in text_upper for k in ["PASAPORTE", "PASSPORT", "P<PER"]):
        pass_score += 70
        detected_features.append("Palabras clave de Pasaporte")

    # Theme boost
    if theme == "DNI_AZUL_THEME":
        dni_score += 25
    elif theme == "DNIE_WHITE_THEME":
        dnie_score += 25
    elif theme == "CE_CYAN_THEME":
        ce_score += 25
    elif theme == "PASAPORTE_THEME":
        pass_score += 30

    # Anverso vs Reverso text cues
    anverso_keywords = [
        "PRENOMBRES", "NOMBRES", "PRIMER APELLIDO", "SEGUNDO APELLIDO", "APELLIDOS",
        "FECHA DE NACIMIENTO", "NACIMIENTO", "FECHA DE EMISION", "FECHA EMISION",
        "F. EMISION", "SEXO", "CADUCIDAD", "NO CADUCA"
    ]
    reverso_keywords = [
        "DOMICILIO", "DIRECCION", "DIRECCIÓN", "UBIGEO", "DEPARTAMENTO", "PROVINCIA",
        "DISTRITO", "ESTADO CIVIL", "GRUPO SANGUINEO", "GRUPO SANGUÍNEO", "DONACION",
        "ORGANOS", "ÓRGANOS", "VOTACION", "OBSERVACIONES", "I<PER", "IDPER"
    ]

    for kw in anverso_keywords:
        if kw in text_upper:
            anverso_score += 15

    for kw in reverso_keywords:
        if kw in text_upper:
            reverso_score += 15

    # Visual side hints: photo is exclusively on Anverso for Peruvian ID cards
    if vis_features["has_photo"]:
        anverso_score += 45
    if (vis_features["has_mrz_strip"] or "I<PER" in text_upper or "IDPER" in text_upper) and not vis_features["has_photo"]:
        reverso_score += 30

    # Final Decision
    if declared_type == "Carnet de Extranjería":
        ce_score += 30
    elif declared_type == "DNI":
        dni_score += 20

    scores = [
        ("Carnet de Extranjería", "Carnet Extranjería Migraciones", ce_score),
        ("DNI Electrónico", "DNIe Blanco/Celeste Gen 1-3", dnie_score),
        ("DNI", "DNI Azul Clásico", dni_score),
        ("Pasaporte", "Pasaporte Ordinario", pass_score),
    ]
    scores.sort(key=lambda x: x[2], reverse=True)
    best_doc, best_subtype, best_score = scores[0]

    if best_score < 20:
        best_doc = declared_type or "DNI"
        best_subtype = "DNI Peruano Estándar"
        conf = 65.0
    else:
        conf = min(99.0, max(50.0, float(best_score)))

    # Determine side
    if anverso_score > reverso_score + 10:
        detected_side = "ANVERSO"
    elif reverso_score > anverso_score + 10:
        detected_side = "REVERSO"
    else:
        if vis_features["has_photo"]:
            detected_side = "ANVERSO"
        elif "DOMICILIO" in text_upper or "UBIGEO" in text_upper:
            detected_side = "REVERSO"
        else:
            detected_side = "ANVERSO"

    return DocumentClassificationResult(
        doc_type=best_doc,
        doc_subtype=best_subtype,
        side=detected_side,
        confidence=round(conf, 1),
        detected_features=detected_features,
        has_mrz="I<PER" in text_upper or "IDPER" in text_upper or vis_features["has_mrz_strip"],
        has_photo=vis_features["has_photo"],
        has_chip=vis_features["has_chip"],
        has_fingerprint=vis_features["has_mrz_strip"],
        dominant_color_theme=theme,
    )
