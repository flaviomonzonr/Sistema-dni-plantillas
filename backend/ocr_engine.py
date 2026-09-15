"""
Módulo OCR para DNI Peruano (ocr_engine.py)
Utiliza OpenCV para preprocesamiento de fotos móviles (escalado a grises, CLAHE,
normalización de iluminación y binarización), RapidOCR (ONNX Runtime) para inferencia
sin dependencias de servidor externo, y Expresiones Regulares (Regex) con heurísticas
de anclas y filtrado para extraer DNI (8 dígitos), nombres y apellidos.
"""

import re
import os
from typing import Dict, Any, List, Optional, Tuple
import cv2
import numpy as np

# RapidOCR Singleton instance
_RAPID_OCR_INSTANCE = None


def get_rapid_ocr_instance():
    """
    Retorna la instancia Singleton de RapidOCR para evitar recargas del modelo ONNX
    y garantizar máxima velocidad de respuesta.
    """
    global _RAPID_OCR_INSTANCE
    if _RAPID_OCR_INSTANCE is None:
        os.environ.setdefault("OMP_NUM_THREADS", "1")
        os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
        try:
            from rapidocr_onnxruntime import RapidOCR
            _RAPID_OCR_INSTANCE = RapidOCR()
        except Exception as e:
            raise RuntimeError(f"Error inicializando RapidOCR: {str(e)}")
    return _RAPID_OCR_INSTANCE


def preprocess_image(image_bytes: bytes) -> Dict[str, np.ndarray]:
    """
    Aplica preprocesamiento avanzado con OpenCV para fotos tomadas con celular o escaneadas:
    1. Decodificación de bytes a matriz BGR.
    2. Redimensionamiento adaptativo manteniendo relación de aspecto.
    3. Conversión a escala de grises.
    4. Corrección de contraste adaptativo CLAHE.
    5. Normalización de iluminación y remoción de sombras/reflejos mediante división morfológica.
    6. Binarización adaptativa (Adaptive Thresholding).
    """
    np_arr = np.frombuffer(image_bytes, np.uint8)
    img_bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    if img_bgr is None:
        raise ValueError("No se pudo decodificar la imagen. Verifique que sea un archivo de imagen válido.")

    # 1. Redimensionamiento adaptativo para OCR óptimo
    h, w = img_bgr.shape[:2]
    target_width = 1400
    if w < 900 or w > 2200:
        scale = target_width / float(w)
        target_height = int(h * scale)
        img_bgr = cv2.resize(img_bgr, (target_width, target_height), interpolation=cv2.INTER_CUBIC)

    # 2. Escala de grises
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    # 3. Corrección de contraste CLAHE (Contrast Limited Adaptive Histogram Equalization)
    clahe = cv2.createCLAHE(clipLimit=2.8, tileGridSize=(8, 8))
    clahe_enhanced = clahe.apply(gray)

    # 4. Normalización de sombras y gradientes de luz (División morfológica)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (35, 35))
    background = cv2.morphologyEx(clahe_enhanced, cv2.MORPH_OPEN, kernel)
    normalized = cv2.divide(clahe_enhanced, background, scale=255)

    # 5. Denoising preservando bordes
    denoised = cv2.bilateralFilter(normalized, d=7, sigmaColor=50, sigmaSpace=50)

    # 6. Binarización adaptativa para remover fondos complejos y sombras
    binarized = cv2.adaptiveThreshold(
        denoised,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        blockSize=21,
        C=8
    )

    # Convertir CLAHE a BGR para alimentar a RapidOCR
    clahe_bgr = cv2.cvtColor(clahe_enhanced, cv2.COLOR_GRAY2BGR)

    return {
        "original_bgr": img_bgr,
        "gray": gray,
        "clahe": clahe_enhanced,
        "clahe_bgr": clahe_bgr,
        "normalized": normalized,
        "binarized": binarized,
    }


# Palabras clave y etiquetas institucionales del DNI Peruano a filtrar/ignorar
DNI_STOPWORDS = {
    "REPUBLICA", "REPUBLICA DEL PERU", "PERU", "REGISTRO", "NACIONAL",
    "IDENTIFICACION", "ESTADO", "CIVIL", "RENIEC", "DOCUMENTO", "DNI",
    "DOCUMENTO NACIONAL DE IDENTIDAD", "FECHA", "NACIMIENTO", "EMISION",
    "CADUCIDAD", "VENCIMIENTO", "EXPEDICION", "SEXO", "MASCULINO", "FEMENINO",
    "ESTADO CIVIL", "SOLTERO", "CASADO", "VIUDO", "DIVORCIADO", "CONVIVIENTE",
    "DONACION", "ORGANOS", "SI", "NO", "GRUPO", "SANGUINEO", "VOTACION",
    "FIRMA", "TITULAR", "CONSTANCIA", "SUFRAGIO", "MULTA", "OBSERVACIONES",
    "TRIBUNAL", "MINISTERIO", "DIGITO", "VERIFICACION", "PRIMER", "SEGUNDO",
    "APELLIDO", "APELLIDOS", "PRENOMBRES", "NOMBRES", "NOMBRE", "UBIGEO",
    "DEPARTAMENTO", "PROVINCIA", "DISTRITO", "DIRECCION", "LUGAR", "NAC",
    "FOTO", "HUELLA", "CHIP", "INDICE", "ELECTRONICO"
}

# Regex precompiladas
RE_DNI_EXACT = re.compile(r"\b\d{8}\b")
RE_DNI_WITH_DIGIT = re.compile(r"\b(\d{8})[-\s<](\d)\b")
RE_DNI_PREFIX = re.compile(r"(?:DNI|N[ÚU]MERO|NUM|DOC|N[°º])[:\s\.]*(\b\d{8}\b)", re.IGNORECASE)
RE_CLEAN_TEXT = re.compile(r"[^A-ZÁÉÍÓÚÑ0-9\s<\-]")
RE_WORDS_ONLY = re.compile(r"^[A-ZÁÉÍÓÚÑ\s]+$")


def extract_dni_number(lines_text: List[str], full_text: str) -> Tuple[str, float]:
    """
    Extrae el DNI peruano de 8 dígitos utilizando expresiones regulares y descarte de fechas.
    """
    candidates: List[Tuple[str, float]] = []

    # 1. Búsqueda con prefijo DNI / DOC / Nº
    for line in lines_text:
        match_pref = RE_DNI_PREFIX.search(line)
        if match_pref:
            num = match_pref.group(1)
            if _is_valid_dni_candidate(num):
                candidates.append((num, 98.0))

    # 2. Búsqueda con dígito verificador ej: 71234567-9 o 71234567 9
    for line in lines_text:
        match_dig = RE_DNI_WITH_DIGIT.search(line)
        if match_dig:
            num = match_dig.group(1)
            if _is_valid_dni_candidate(num):
                candidates.append((num, 95.0))

    # 3. Búsqueda de cualquier bloque de 8 dígitos consecutivos (\b\d{8}\b)
    matches = RE_DNI_EXACT.findall(full_text)
    for m in matches:
        if _is_valid_dni_candidate(m):
            candidates.append((m, 88.0))

    # 4. Búsqueda en formato MRZ (I<PER0712345678<... o IDPER71234567...)
    mrz_match = re.search(r"I[<D]PER(\d{8})", full_text.replace(" ", ""))
    if mrz_match:
        candidates.append((mrz_match.group(1), 99.0))

    if not candidates:
        # Fallback: buscar secuencias de 8 dígitos pegadas
        digits_only = re.findall(r"\d{8}", full_text)
        for d in digits_only:
            if _is_valid_dni_candidate(d):
                candidates.append((d, 75.0))

    if candidates:
        # Retornar el candidato con mayor confianza
        best_candidate = max(candidates, key=lambda x: x[1])
        return best_candidate[0], best_candidate[1]

    return "", 0.0


def _is_valid_dni_candidate(num: str) -> bool:
    """Valida que no sea una fecha (ej: 19900101, 20260914) ni números repetidos triviales (ej: 00000000, 11111111)."""
    if len(num) != 8 or not num.isdigit():
        return False
    if len(set(num)) == 1:
        return False
    # Descartar fechas como 2020xxxx o 1990xxxx si son fechas de emisión/nacimiento
    if num.startswith(("195", "196", "197", "198", "199", "200", "201", "202")):
        month = int(num[4:6])
        day = int(num[6:8])
        if 1 <= month <= 12 and 1 <= day <= 31:
            # Podría ser una fecha concatenada YYYYMMDD
            return False
    return True


def parse_mrz_td1(full_text: str) -> Optional[Dict[str, str]]:
    """
    Analiza la zona de lectura mecánica (MRZ) de 3 líneas del DNI si está presente.
    Línea 3 típica: APELLIDO1<APELLIDO2<<NOMBRE1<NOMBRE2...
    """
    lines = [l.strip().replace(" ", "").upper() for l in full_text.splitlines() if len(l.strip()) >= 15]
    for line in lines:
        if "<<" in line and "<" in line:
            # Posible línea 3 de nombres MRZ
            clean = re.sub(r"[^A-Z<]", "", line)
            parts = clean.split("<<")
            if len(parts) >= 2:
                surnames_part = parts[0].replace("<", " ").strip()
                names_part = parts[1].replace("<", " ").strip()
                if surnames_part and names_part:
                    return {
                        "apellidos": surnames_part,
                        "nombres": names_part
                    }
    return None


def extract_names_and_surnames(lines: List[Dict[str, Any]], full_text: str) -> Tuple[str, str, str, str]:
    """
    Extrae apellidos y nombres filtrando líneas no deseadas y buscando anclas visuales:
    - 1er Apellido / Apellido Paterno
    - 2do Apellido / Apellido Materno
    - Prenombres / Nombres
    Retorna: (apellidos, nombres, paterno, materno)
    """
    # 1. Intentar primero con MRZ si está visible
    mrz_res = parse_mrz_td1(full_text)
    if mrz_res:
        surnames = mrz_res["apellidos"]
        names = mrz_res["nombres"]
        parts = surnames.split()
        paterno = parts[0] if len(parts) > 0 else surnames
        materno = " ".join(parts[1:]) if len(parts) > 1 else ""
        return surnames, names, paterno, materno

    paterno = ""
    materno = ""
    nombres = ""
    apellidos = ""

    raw_lines = [l["text"].strip() for l in lines if l.get("text", "").strip()]

    # Limpiar líneas descartando encabezados oficiales
    filtered_lines = []
    for line_text in raw_lines:
        clean_upper = line_text.upper().replace(".", " ").replace("-", " ").strip()
        # Verificar si es encabezado institucional
        if any(h in clean_upper for h in [
            "REPUBLICA DEL PERU", "REGISTRO NACIONAL", "IDENTIFICACION Y ESTADO CIVIL",
            "DOCUMENTO NACIONAL DE IDENTIDAD", "RENIEC"
        ]):
            continue
        filtered_lines.append(line_text)

    # 2. Búsqueda por anclas de etiquetas peruanas
    for i, line_text in enumerate(filtered_lines):
        upper = line_text.upper()
        upper_nospaces = re.sub(r"[\s\.\:\-]+", "", upper)

        # APELLIDO PATERNO / 1ER APELLIDO
        is_paternal_anchor = (
            any(k in upper for k in ["1ER APELLIDO", "PRIMER APELLIDO", "APELLIDO PATERNO"])
            or any(k in upper_nospaces for k in ["1ERAPELLIDO", "PRIMERAPELLIDO", "APELLIDOPATERNO"])
        )
        if is_paternal_anchor and not paterno:
            val = _clean_name_value(re.sub(r"^.*?(1ER\s*APELLIDO|PRIMER\s*APELLIDO|APELLIDO\s*PATERNO|1ERAPELLIDO|PRIMERAPELLIDO|APELLIDOPATERNO)[:\s\-]*", "", line_text, flags=re.IGNORECASE))
            if not val and i + 1 < len(filtered_lines):
                val = _clean_name_value(filtered_lines[i + 1])
            if val:
                paterno = val

        # APELLIDO MATERNO / 2DO APELLIDO
        is_maternal_anchor = (
            any(k in upper for k in ["2DO APELLIDO", "SEGUNDO APELLIDO", "APELLIDO MATERNO"])
            or any(k in upper_nospaces for k in ["2DOAPELLIDO", "SEGUNDOAPELLIDO", "APELLIDOMATERNO"])
        )
        if is_maternal_anchor and not materno:
            val = _clean_name_value(re.sub(r"^.*?(2DO\s*APELLIDO|SEGUNDO\s*APELLIDO|APELLIDO\s*MATERNO|2DOAPELLIDO|SEGUNDOAPELLIDO|APELLIDOMATERNO)[:\s\-]*", "", line_text, flags=re.IGNORECASE))
            if not val and i + 1 < len(filtered_lines):
                val = _clean_name_value(filtered_lines[i + 1])
            if val:
                materno = val

        # APELLIDOS (JUNTOS)
        is_apellidos_anchor = "APELLIDOS" in upper or "APELLIDOS" in upper_nospaces
        if is_apellidos_anchor and not paterno and not apellidos:
            val = _clean_name_value(re.sub(r"^.*?APELLIDOS?[:\s\-]*", "", line_text, flags=re.IGNORECASE))
            if not val and i + 1 < len(filtered_lines):
                val = _clean_name_value(filtered_lines[i + 1])
            if val:
                apellidos = val

        # PRENOMBRES / NOMBRES
        is_nombres_anchor = (
            any(k in upper for k in ["PRENOMBRES", "PRE NOMBRE", "NOMBRES", "NOMBRE"])
            or any(k in upper_nospaces for k in ["PRENOMBRES", "PRENOMBRE", "NOMBRES"])
        )
        if is_nombres_anchor and not nombres:
            val = _clean_name_value(re.sub(r"^.*?(PRENOMBRES?|PRE\s*NOMBRES?|NOMBRES?)[:\s\-]*", "", line_text, flags=re.IGNORECASE))
            if not val and i + 1 < len(filtered_lines):
                val = _clean_name_value(filtered_lines[i + 1])
            if val:
                nombres = val

    # 3. Ensamblar apellidos si se extrajeron por separado
    if paterno or materno:
        apellidos = f"{paterno} {materno}".strip()
    elif apellidos:
        parts = apellidos.split()
        paterno = parts[0] if len(parts) > 0 else apellidos
        materno = " ".join(parts[1:]) if len(parts) > 1 else ""

    # 4. Heurística de respaldo si no se encontraron anclas claras
    if not apellidos or not nombres:
        candidate_words_lines = []
        for line_text in filtered_lines:
            cleaned = _clean_name_value(line_text)
            if len(cleaned) >= 3 and RE_WORDS_ONLY.match(cleaned):
                # Verificar que ninguna palabra sea un stopword del DNI
                words = cleaned.split()
                if not any(w in DNI_STOPWORDS for w in words):
                    candidate_words_lines.append(cleaned)

        if len(candidate_words_lines) >= 2:
            if not apellidos:
                apellidos = candidate_words_lines[0]
                parts = apellidos.split()
                paterno = parts[0] if len(parts) > 0 else apellidos
                materno = " ".join(parts[1:]) if len(parts) > 1 else ""
            if not nombres:
                nombres = candidate_words_lines[1]
        elif len(candidate_words_lines) == 1:
            if not apellidos:
                apellidos = candidate_words_lines[0]

    return apellidos, nombres, paterno, materno


def _clean_name_value(text: str) -> str:
    """Limpia cadenas de nombres eliminando caracteres especiales y números."""
    if not text:
        return ""
    cleaned = re.sub(r"[^A-ZÁÉÍÓÚÑa-záéíóúñ\s]", " ", text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip().upper()
    tokens = [w for w in cleaned.split() if w not in DNI_STOPWORDS and len(w) > 1]
    return " ".join(tokens)


def extract_dni_from_bytes(image_bytes: bytes) -> Dict[str, Any]:
    """
    Función principal de extracción OCR para DNI Peruano:
    1. Preprocesa la imagen con OpenCV (CLAHE, eliminación de sombras, binarización).
    2. Ejecuta RapidOCR (ONNX).
    3. Extrae DNI (8 dígitos) con Regex y nombres/apellidos mediante filtrado inteligente.
    """
    # 1. Preprocesamiento OpenCV
    preprocessed = preprocess_image(image_bytes)
    clahe_bgr = preprocessed["clahe_bgr"]

    # 2. Inferencia RapidOCR
    ocr_engine = get_rapid_ocr_instance()
    results, elapse_list = ocr_engine(clahe_bgr)

    # Si no hubo detecciones en CLAHE, probar en la imagen normalizada
    if not results:
        norm_bgr = cv2.cvtColor(preprocessed["normalized"], cv2.COLOR_GRAY2BGR)
        results, _ = ocr_engine(norm_bgr)

    lines: List[Dict[str, Any]] = []
    lines_text: List[str] = []

    if results:
        # Ordenar resultados de arriba a abajo y de izquierda a derecha
        sorted_res = sorted(results, key=lambda item: (min(pt[1] for pt in item[0]), min(pt[0] for pt in item[0])))
        for item in sorted_res:
            raw_text = str(item[1]).strip()
            conf = float(item[2]) * 100.0 if len(item) > 2 else 85.0
            if raw_text:
                lines.append({
                    "text": raw_text,
                    "confidence": round(conf, 1),
                    "box": item[0]
                })
                lines_text.append(raw_text)

    full_text = "\n".join(lines_text)

    # 3. Extracción de DNI mediante Regex
    dni_number, dni_conf = extract_dni_number(lines_text, full_text)

    # 4. Extracción de Nombres y Apellidos
    apellidos, nombres, paterno, materno = extract_names_and_surnames(lines, full_text)

    return {
        "dni": dni_number,
        "nombres": nombres,
        "apellidos": apellidos,
        "paterno": paterno,
        "materno": materno,
        "raw_text": full_text,
        "success": bool(dni_number or (nombres and apellidos)),
        "confidence": {
            "dni": dni_conf,
            "line_count": len(lines),
        }
    }


# Aliases
process_dni_image = extract_dni_from_bytes
