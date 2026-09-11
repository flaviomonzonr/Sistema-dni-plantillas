import re
from typing import Dict, Any, List, Tuple, Optional
from backend.ocr.base import OCRResult, OCRLine, OCRWord
from backend.schemas import FieldConfidence
from backend.extractors.semantic_extractor import (
    SemanticExtractor,
    is_valid_name_token,
)
from backend.extractors.validators import (
    clean_text,
    validate_ce,
    normalize_and_validate_date,
    normalize_sex,
)

NATIONALITY_LIST = [
    "VENEZOLANA", "VENEZUELA", "COLOMBIANA", "COLOMBIA", "ESPAÑOLA", "ESPAÑA",
    "ARGENTINA", "CHILENA", "CHILE", "ECUATORIANA", "ECUADOR", "ESTADOUNIDENSE",
    "ESTADOS UNIDOS", "ITALIANA", "ITALIA", "BRASILEÑA", "BRASIL", "CHINA",
    "BOLIVIANA", "BOLIVIA", "CUBANA", "CUBA", "MEXICANA", "MEXICO", "FRANCESA",
    "FRANCIA", "ALEMANA", "ALEMANIA", "PORTUGUESA", "PORTUGAL", "HAITIANA",
    "CANADIENSE", "URUGUAYA", "PARAGUAYA", "DOMINICANA", "PERUANA"
]

MIGRATION_STATUS_LIST = [
    "TRABAJADOR RESIDENTE", "FAMILIAR DE RESIDENTE", "RESIDENTE PERMANENTE",
    "PERMANENTE", "ESTUDIANTE", "HUMANITARIA", "ESPECIAL RESIDENTE",
    "INMIGRANTE", "RELIGIOSO", "RENTISTA", "PROFESIONAL INDEPENDIENTE",
    "COOPERANTE", "DESIGNADO", "TRABAJADOR", "RESIDENTE"
]


def extract_ce_data(
    front_ocr: OCRResult,
    back_ocr: Optional[OCRResult] = None,
    mrz_text: Optional[str] = None,
    candidate_pools: Optional[Dict[str, List[Tuple[str, float, str]]]] = None,
) -> Tuple[Dict[str, str], Dict[str, FieldConfidence], List[str]]:
    """
    Extracts fields from Peruvian Carnet de Extranjería (Anverso and Reverso).
    """
    fields: Dict[str, FieldConfidence] = {}
    warnings: List[str] = []

    front_lines = front_ocr.lines if front_ocr else []
    back_lines = back_ocr.lines if back_ocr else []
    combined_lines = front_lines + back_lines

    all_front_text = " \n ".join([l.text.upper() for l in front_lines])
    all_back_text = " \n ".join([l.text.upper() for l in back_lines])

    # 1. CARNET NUMBER (9 digits or alphanumeric)
    ce_number = ""
    ce_conf = 0.0
    ce_candidates = []

    for line in combined_lines:
        t = line.text.upper()
        matches = re.finditer(r"\b([A-Z0-9]{8,10})\b", t)
        for m in matches:
            val = m.group(1)
            if not any(k in val for k in ["REPUBLICA", "MIGRAC", "EXTRANJ", "PERU", "NACIONAL", "DOCUMENTO"]):
                weight = line.confidence
                if any(kw in t for kw in ["CARNE", "CARNET", "N°", "Nº", "NUMERO", "CE"]):
                    weight += 25
                if val.isdigit() and len(val) == 9:
                    weight += 15
                ce_candidates.append((val, weight, line.text))

    if ce_candidates:
        ce_candidates.sort(key=lambda x: x[1], reverse=True)
        ce_number = ce_candidates[0][0]
        ce_conf = min(98.0, ce_candidates[0][1])
        anchor_ce = ce_candidates[0][2]
    else:
        m = re.search(r"\b(\d{9})\b", all_front_text + "\n" + all_back_text)
        if m:
            ce_number = m.group(1)
            ce_conf = 65.0
            anchor_ce = "Búsqueda global"
        else:
            anchor_ce = None

    val_ce_ok, val_ce_num, ce_err = validate_ce(ce_number) if ce_number else (False, "", "No detectado")
    fields["doc_number"] = FieldConfidence(
        value=val_ce_num if val_ce_ok else ce_number,
        confidence=ce_conf if val_ce_ok else 0.0,
        is_valid=val_ce_ok,
        status=SemanticExtractor.determine_field_status(ce_conf, val_ce_ok),
        origin_type="LEIDO_OCR",
        validation_message=ce_err,
        anchor_matched=anchor_ce,
    )
    if not val_ce_ok:
        warnings.append("Número de Carnet de Extranjería no verificado con total claridad.")

    # 2. SURNAMES & FIRST NAMES
    paternal = ""
    maternal = ""
    first_names = ""
    paternal_conf = 0.0
    maternal_conf = 0.0
    names_conf = 0.0

    for i, line in enumerate(front_lines):
        t = line.text.upper()
        if "PRIMER APELLIDO" in t or "APELLIDO PATERNO" in t:
            val = re.sub(r".*(PRIMER APELLIDO|APELLIDO PATERNO)[:\s\-]*", "", t).strip()
            tokens = [w for w in val.split() if is_valid_name_token(w)]
            if tokens:
                paternal = " ".join(tokens)
                paternal_conf = line.confidence
            elif i + 1 < len(front_lines):
                next_tokens = [w for w in front_lines[i+1].text.split() if is_valid_name_token(w)]
                if next_tokens:
                    paternal = " ".join(next_tokens)
                    paternal_conf = front_lines[i+1].confidence

        if "SEGUNDO APELLIDO" in t or "APELLIDO MATERNO" in t:
            val = re.sub(r".*(SEGUNDO APELLIDO|APELLIDO MATERNO)[:\s\-]*", "", t).strip()
            tokens = [w for w in val.split() if is_valid_name_token(w)]
            if tokens:
                maternal = " ".join(tokens)
                maternal_conf = line.confidence
            elif i + 1 < len(front_lines):
                next_tokens = [w for w in front_lines[i+1].text.split() if is_valid_name_token(w)]
                if next_tokens:
                    maternal = " ".join(next_tokens)
                    maternal_conf = front_lines[i+1].confidence

        if any(k in t for k in ["NOMBRES", "PRENOMBRES"]):
            val = re.sub(r".*(NOMBRES|PRENOMBRES)[:\s\-]*", "", t).strip()
            tokens = [w for w in val.split() if is_valid_name_token(w)]
            if tokens:
                first_names = " ".join(tokens)
                names_conf = line.confidence
            elif i + 1 < len(front_lines):
                next_tokens = [w for w in front_lines[i+1].text.split() if is_valid_name_token(w)]
                if next_tokens:
                    first_names = " ".join(next_tokens)
                    names_conf = front_lines[i+1].confidence

    fields["paternal_surname"] = FieldConfidence(
        value=paternal,
        confidence=paternal_conf if paternal else 0.0,
        is_valid=bool(paternal),
        status=SemanticExtractor.determine_field_status(paternal_conf, bool(paternal)),
        origin_type="LEIDO_OCR",
    )
    fields["maternal_surname"] = FieldConfidence(
        value=maternal,
        confidence=maternal_conf if maternal else 0.0,
        is_valid=bool(maternal),
        status=SemanticExtractor.determine_field_status(maternal_conf, bool(maternal)),
        origin_type="LEIDO_OCR",
    )
    fields["first_names"] = FieldConfidence(
        value=first_names,
        confidence=names_conf if first_names else 0.0,
        is_valid=bool(first_names),
        status=SemanticExtractor.determine_field_status(names_conf, bool(first_names)),
        origin_type="LEIDO_OCR",
    )

    # 3. NACIONALIDAD
    nationality = ""
    nat_conf = 0.0
    for line in combined_lines:
        t = line.text.upper()
        for nat in NATIONALITY_LIST:
            if nat in t:
                nationality = nat
                nat_conf = max(80.0, line.confidence)
                break
        if nationality:
            break

    fields["nationality"] = FieldConfidence(
        value=nationality,
        confidence=nat_conf if nationality else 0.0,
        is_valid=bool(nationality),
        status=SemanticExtractor.determine_field_status(nat_conf, bool(nationality)),
        origin_type="LEIDO_OCR",
    )

    # 4. CALIDAD MIGRATORIA
    migratory_status = ""
    mig_conf = 0.0
    for line in combined_lines:
        t = line.text.upper()
        for status in MIGRATION_STATUS_LIST:
            if status in t:
                migratory_status = status
                mig_conf = max(80.0, line.confidence)
                break
        if migratory_status:
            break

    fields["migratory_status"] = FieldConfidence(
        value=migratory_status,
        confidence=mig_conf if migratory_status else 0.0,
        is_valid=bool(migratory_status),
        status=SemanticExtractor.determine_field_status(mig_conf, bool(migratory_status)),
        origin_type="LEIDO_OCR",
    )

    # 5. DATES (Birth, Issue, Expiry)
    birth_date = ""
    issue_date = ""
    expiry_date = ""
    for line in combined_lines:
        t = line.text.upper()
        valid, formatted, _ = normalize_and_validate_date(t)
        if valid:
            if any(k in t for k in ["NACIMIENTO", "F. NAC"]) and not birth_date:
                birth_date = formatted
            elif any(k in t for k in ["EMISION", "EMISIÓN", "F. EMI"]) and not issue_date:
                issue_date = formatted
            elif any(k in t for k in ["CADUCIDAD", "VENCIMIENTO", "VENCE", "F. VENC"]) and not expiry_date:
                expiry_date = formatted

    fields["birth_date"] = FieldConfidence(
        value=birth_date,
        confidence=80.0 if birth_date else 0.0,
        is_valid=bool(birth_date),
        status=SemanticExtractor.determine_field_status(80.0, bool(birth_date)),
        origin_type="LEIDO_OCR",
    )
    fields["issue_date"] = FieldConfidence(
        value=issue_date,
        confidence=80.0 if issue_date else 0.0,
        is_valid=bool(issue_date),
        status=SemanticExtractor.determine_field_status(80.0, bool(issue_date)),
        origin_type="LEIDO_OCR",
    )
    fields["expiry_date"] = FieldConfidence(
        value=expiry_date,
        confidence=80.0 if expiry_date else 0.0,
        is_valid=bool(expiry_date),
        status=SemanticExtractor.determine_field_status(80.0, bool(expiry_date)),
        origin_type="LEIDO_OCR",
    )

    # 6. SEX & ADDRESS
    sex = ""
    for line in combined_lines:
        t = line.text.upper()
        if "SEXO" in t:
            if "M" in t.split():
                sex = "M"
            elif "F" in t.split():
                sex = "F"

    fields["sex"] = FieldConfidence(
        value=sex,
        confidence=80.0 if sex else 0.0,
        is_valid=bool(sex),
        status=SemanticExtractor.determine_field_status(80.0, bool(sex)),
        origin_type="LEIDO_OCR",
    )

    fields["address"] = FieldConfidence(
        value="",
        confidence=0.0,
        is_valid=False,
        status="NO_DETECTADO",
        origin_type="LEIDO_OCR",
    )
    fields["ubigeo"] = FieldConfidence(
        value="",
        confidence=0.0,
        is_valid=False,
        status="NO_DETECTADO",
        origin_type="LEIDO_OCR",
    )
    fields["blood_type"] = FieldConfidence(
        value="",
        confidence=0.0,
        is_valid=False,
        status="NO_DETECTADO",
        origin_type="LEIDO_OCR",
    )
    fields["civil_status"] = FieldConfidence(
        value="",
        confidence=0.0,
        is_valid=False,
        status="NO_DETECTADO",
        origin_type="LEIDO_OCR",
    )
    fields["observations"] = FieldConfidence(
        value="",
        confidence=0.0,
        is_valid=False,
        status="NO_DETECTADO",
        origin_type="LEIDO_OCR",
    )

    extracted_dict = {k: v.value for k, v in fields.items()}
    return extracted_dict, fields, warnings
