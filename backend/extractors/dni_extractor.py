import re
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from backend.ocr.base import OCRResult, OCRLine, OCRWord
from backend.schemas import FieldConfidence
from backend.ocr.consensus_engine import normalize_numeric_ocr, normalize_alpha_ocr
from backend.extractors.semantic_extractor import (
    SemanticExtractor,
    parse_icao_td1_mrz_robust,
    is_valid_name_token,
    DISALLOWED_NAME_KEYWORDS,
)
from backend.extractors.validators import (
    clean_text,
    validate_dni,
    normalize_and_validate_date,
    normalize_sex,
    normalize_civil_status,
    PERU_DEPARTMENTS,
    separate_concatenated_names,
    is_invalid_address_candidate,
)

# Alias for backwards compatibility
parse_icao_td1_mrz = parse_icao_td1_mrz_robust


def extract_dni_data(
    front_ocr: OCRResult,
    back_ocr: Optional[OCRResult] = None,
    mrz_text: Optional[str] = None,
    candidate_pools: Optional[Dict[str, List[Tuple[str, float, str]]]] = None,
) -> Tuple[Dict[str, str], Dict[str, FieldConfidence], List[str]]:
    """
    Intelligent semantic extractor for Peruvian DNI (Azul, Blanco, DNIe 1-3 gen).
    Uses multi-attempt consensus candidate pools, anchor labels, and ICAO TD1 MRZ.
    """
    fields: Dict[str, FieldConfidence] = {}
    warnings: List[str] = []

    back_lines_list = back_ocr.lines if back_ocr else []
    front_lines_list = front_ocr.lines if front_ocr else []

    combined_lines = front_lines_list + back_lines_list
    combined_full_text = ((front_ocr.full_text if front_ocr else "") + "\n" + (back_ocr.full_text if back_ocr else "")).upper()

    # Parse MRZ from explicit mrz_text or fallback to combined_full_text
    mrz_data = parse_icao_td1_mrz_robust(mrz_text) if mrz_text else None
    if not mrz_data:
        mrz_data = parse_icao_td1_mrz_robust(combined_full_text)
    elif not mrz_data.get("dni") or not mrz_data.get("birth_date"):
        # Supplement from combined_full_text if partial
        extra_mrz = parse_icao_td1_mrz_robust(combined_full_text)
        if extra_mrz:
            for k, v in extra_mrz.items():
                if k not in mrz_data or not mrz_data[k]:
                    mrz_data[k] = v

    # 1. DNI NUMBER (Highest priority: MRZ -> Candidates -> Anchors)
    dni_candidate_pool = candidate_pools.get("dni_candidates", []) if candidate_pools else []
    dni_res = SemanticExtractor.extract_dni_number(combined_lines, mrz_data, dni_candidate_pool)
    doc_number = dni_res.value
    dni_conf = dni_res.confidence
    fields["doc_number"] = FieldConfidence(
        value=doc_number,
        confidence=dni_conf,
        is_valid=dni_res.is_valid,
        status=dni_res.status,
        origin_type=dni_res.origin_type,
        validation_message=dni_res.validation_message,
        anchor_matched=dni_res.anchor_matched,
    )
    if dni_res.status == "REVISAR":
        warnings.append("Número de DNI detectado con nivel de confianza medio. Se recomienda validar.")
    elif dni_res.status == "NO_DETECTADO":
        warnings.append("No se detectó un número de DNI válido de 8 dígitos.")

    # 2. SURNAMES (Paternal & Maternal)
    paternal_surname = ""
    maternal_surname = ""
    paternal_conf = 0.0
    maternal_conf = 0.0
    paternal_anchor = None
    maternal_anchor = None

    # 2A. Priority: MRZ Line 3
    if mrz_data and mrz_data.get("paternal_surname"):
        paternal_surname = mrz_data["paternal_surname"]
        paternal_conf = 99.0
        paternal_anchor = "MRZ ICAO TD1"
        if mrz_data.get("maternal_surname"):
            maternal_surname = mrz_data["maternal_surname"]
            maternal_conf = 99.0
            maternal_anchor = "MRZ ICAO TD1"

    # 2B. Visual Anchors: "1ER APELLIDO", "2DO APELLIDO", "APELLIDO PATERNO", "APELLIDOS"
    name_stop_keywords = [
        "PRENOMBRES", "PRENOMBRE", "PRE NOMBRES", "NOMBRES", "NOMBRE",
        "SEXO", "FECHA", "NACIMIENTO", "DNI", "EMISION", "EMISIÓN",
        "CADUCIDAD", "VENCIMIENTO", "INSCRIPCION", "INSCRIPCIÓN",
        "ESTADO", "CIVIL", "DIGITO", "VERIFICACION", "REPUBLICA", "PERU"
    ]

    for i, line in enumerate(front_lines_list):
        t = line.text.upper().replace(".", " ").strip()
        t_nospaces = re.sub(r"\s+", "", t)
        
        # Primer Apellido
        is_paternal_anchor = (
            any(k in t for k in ["1ER APELLIDO", "PRIMER APELLIDO", "APELLIDO PATERNO"])
            or any(k in t_nospaces for k in ["1ERAPELLIDO", "PRIMERAPELLIDO", "APELLIDOPATERNO"])
        )
        if is_paternal_anchor and not paternal_surname:
            clean_val = re.sub(r"^.*?(1ER\s*APELLIDO|PRIMER\s*APELLIDO|APELLIDO\s*PATERNO|1ERAPELLIDO|PRIMERAPELLIDO|APELLIDOPATERNO)[:\s\-]*", "", t, flags=re.IGNORECASE).strip()
            tokens = [w for w in clean_val.split() if is_valid_name_token(w) and not any(sk in w for sk in name_stop_keywords)]
            if tokens:
                paternal_surname = " ".join(tokens)
                paternal_conf = max(82.0, line.confidence)
                paternal_anchor = line.text
            else:
                for off in range(1, 4):
                    if i + off < len(front_lines_list):
                        cand_l = front_lines_list[i + off]
                        cand_text = cand_l.text.upper()
                        # Skip dates, other field headers
                        if normalize_and_validate_date(cand_text)[0] or any(sk in cand_text for sk in ["2DO", "SEGUNDO", "MATERNO", "INSCRIPCION", "EMISION", "CADUCIDAD"] + name_stop_keywords):
                            continue
                        next_tokens = [w for w in cand_text.split() if is_valid_name_token(w) and not any(sk in w for sk in name_stop_keywords)]
                        if next_tokens:
                            paternal_surname = " ".join(next_tokens)
                            paternal_conf = max(82.0, cand_l.confidence)
                            paternal_anchor = line.text
                            break

        # Segundo Apellido
        is_maternal_anchor = (
            any(k in t for k in ["2DO APELLIDO", "SEGUNDO APELLIDO", "APELLIDO MATERNO"])
            or any(k in t_nospaces for k in ["2DOAPELLIDO", "SEGUNDOAPELLIDO", "APELLIDOMATERNO"])
        )
        if is_maternal_anchor and not maternal_surname:
            clean_val = re.sub(r"^.*?(2DO\s*APELLIDO|SEGUNDO\s*APELLIDO|APELLIDO\s*MATERNO|2DOAPELLIDO|SEGUNDOAPELLIDO|APELLIDOMATERNO)[:\s\-]*", "", t, flags=re.IGNORECASE).strip()
            tokens = [w for w in clean_val.split() if is_valid_name_token(w) and not any(sk in w for sk in name_stop_keywords)]
            if tokens:
                maternal_surname = " ".join(tokens)
                maternal_conf = max(82.0, line.confidence)
                maternal_anchor = line.text
            else:
                for off in range(1, 4):
                    if i + off < len(front_lines_list):
                        cand_l = front_lines_list[i + off]
                        cand_text = cand_l.text.upper()
                        # Skip dates, other field headers
                        if normalize_and_validate_date(cand_text)[0] or any(sk in cand_text for sk in ["INSCRIPCION", "EMISION", "CADUCIDAD"] + name_stop_keywords):
                            continue
                        next_tokens = [w for w in cand_text.split() if is_valid_name_token(w) and not any(sk in w for sk in name_stop_keywords)]
                        if next_tokens:
                            maternal_surname = " ".join(next_tokens)
                            maternal_conf = max(82.0, cand_l.confidence)
                            maternal_anchor = line.text
                            break

        # Generic "APELLIDOS" Anchor (DNI Azul Clásico)
        if "APELLIDOS" in t_nospaces and not any(k in t_nospaces for k in ["1ER", "2DO", "PRIMER", "SEGUNDO"]) and not paternal_surname:
            clean_val = re.sub(r"^.*?APELLIDOS[:\s\-]*", "", t, flags=re.IGNORECASE).strip()
            tokens = [w for w in clean_val.split() if is_valid_name_token(w) and not any(sk in w for sk in name_stop_keywords)]
            if len(tokens) >= 2:
                paternal_surname = tokens[0]
                maternal_surname = " ".join(tokens[1:])
                paternal_conf = max(80.0, line.confidence)
                maternal_conf = max(80.0, line.confidence)
                paternal_anchor = line.text
            elif i + 1 < len(front_lines_list):
                cand_l1 = front_lines_list[i+1]
                cand_t1 = cand_l1.text.upper()
                if not any(sk in cand_t1 for sk in name_stop_keywords) and not normalize_and_validate_date(cand_t1)[0]:
                    next_tokens = [w for w in cand_t1.split() if is_valid_name_token(w) and not any(sk in w for sk in name_stop_keywords)]
                    if len(next_tokens) >= 2:
                        paternal_surname = next_tokens[0]
                        maternal_surname = " ".join(next_tokens[1:])
                        paternal_conf = max(80.0, cand_l1.confidence)
                        maternal_conf = max(80.0, cand_l1.confidence)
                        paternal_anchor = line.text
                    elif len(next_tokens) == 1:
                        paternal_surname = next_tokens[0]
                        paternal_conf = max(78.0, cand_l1.confidence)
                        paternal_anchor = line.text
                        if i + 2 < len(front_lines_list):
                            cand_l2 = front_lines_list[i+2]
                            cand_t2 = cand_l2.text.upper()
                            if not any(sk in cand_t2 for sk in name_stop_keywords) and not normalize_and_validate_date(cand_t2)[0]:
                                next2_tokens = [w for w in cand_t2.split() if is_valid_name_token(w) and not any(sk in w for sk in name_stop_keywords)]
                                if next2_tokens:
                                    maternal_surname = " ".join(next2_tokens)
                                    maternal_conf = max(78.0, cand_l2.confidence)

    # 3. FIRST NAMES / PRENOMBRES
    first_names = ""
    names_conf = 0.0
    names_anchor = None

    if mrz_data and mrz_data.get("first_names"):
        first_names = separate_concatenated_names(mrz_data["first_names"])
        names_conf = 99.0
        names_anchor = "MRZ ICAO TD1"

    # Also scan visual OCR for prenombres
    visual_first_names = ""
    visual_names_conf = 0.0
    visual_names_anchor = None

    for i, line in enumerate(front_lines_list):
        t = line.text.upper().replace(".", " ").strip()
        t_nospaces = re.sub(r"\s+", "", t)
        is_prenombres_anchor = (
            any(k in t for k in ["PRENOMBRES", "PRE NOMBRE", "PRE NOMBRES", "NOMBRES"])
            or any(k in t_nospaces for k in ["PRENOMBRES", "PRENOMBRE", "PRENOMBRES", "NOMBRES"])
        ) and not any(k in t_nospaces for k in ["PRIMER", "SEGUNDO", "APELLIDO", "APELLIDOS"])
        
        if is_prenombres_anchor:
            clean_val = re.sub(r"^.*?(PRE\s*NOMBRES?|PRENOMBRES?|NOMBRES?)[:\s\-]*", "", t, flags=re.IGNORECASE).strip()
            tokens = [w for w in clean_val.split() if is_valid_name_token(w) and not any(sk in w for sk in ["SEXO", "FECHA", "NACIMIENTO", "DNI", "EMISION", "CADUCIDAD"])]
            if tokens:
                visual_first_names = separate_concatenated_names(" ".join(tokens))
                visual_names_conf = max(85.0, line.confidence)
                visual_names_anchor = line.text
                break
            else:
                for off in range(1, 5):
                    if i + off < len(front_lines_list):
                        cand_l = front_lines_list[i + off]
                        cand_text = cand_l.text.upper()
                        # If the line is a date or document metadata, skip it and continue checking subsequent lines
                        if normalize_and_validate_date(cand_text)[0] or any(sk in cand_text for sk in ["SEXO", "FECHA", "NACIMIENTO", "DNI", "EMISION", "CADUCIDAD"]):
                            continue
                        next_tokens = [w for w in cand_text.split() if is_valid_name_token(w)]
                        if next_tokens:
                            visual_first_names = separate_concatenated_names(" ".join(next_tokens))
                            visual_names_conf = max(85.0, cand_l.confidence)
                            visual_names_anchor = line.text
                            break
                if visual_first_names:
                    break

    # If MRZ was missing or single unspaced word while visual has separated names, prefer separated
    if not first_names:
        first_names = visual_first_names
        names_conf = visual_names_conf
        names_anchor = visual_names_anchor
    elif visual_first_names and " " in visual_first_names and " " not in first_names:
        first_names = visual_first_names
        names_anchor = visual_names_anchor or names_anchor

    if first_names:
        first_names = separate_concatenated_names(first_names)

    # Post-validation: Avoid maternal surname accidentally duplicating prenombres/nombres
    if maternal_surname and first_names:
        if maternal_surname.strip() == first_names.strip() or maternal_surname in first_names:
            maternal_surname = ""
            maternal_conf = 0.0

    # Populate Surnames & Names fields
    pat_status = SemanticExtractor.determine_field_status(paternal_conf, bool(paternal_surname))
    fields["paternal_surname"] = FieldConfidence(
        value=paternal_surname,
        confidence=paternal_conf if paternal_surname else 0.0,
        is_valid=bool(paternal_surname),
        status=pat_status,
        origin_type="LEIDO_OCR",
        anchor_matched=paternal_anchor,
    )

    mat_status = SemanticExtractor.determine_field_status(maternal_conf, bool(maternal_surname))
    fields["maternal_surname"] = FieldConfidence(
        value=maternal_surname,
        confidence=maternal_conf if maternal_surname else 0.0,
        is_valid=bool(maternal_surname),
        status=mat_status,
        origin_type="LEIDO_OCR",
        anchor_matched=maternal_anchor,
    )

    names_status = SemanticExtractor.determine_field_status(names_conf, bool(first_names))
    fields["first_names"] = FieldConfidence(
        value=first_names,
        confidence=names_conf if first_names else 0.0,
        is_valid=bool(first_names),
        status=names_status,
        origin_type="LEIDO_OCR",
        anchor_matched=names_anchor,
    )

    # 4. FECHA DE NACIMIENTO (Highest priority: MRZ -> Visual Anchors -> Candidate Pool)
    birth_date = ""
    birth_conf = 0.0
    birth_anchor = None

    if mrz_data and mrz_data.get("birth_date"):
        birth_date = mrz_data["birth_date"]
        birth_conf = 99.0
        birth_anchor = "MRZ ICAO TD1"
    else:
        birth_anchors = [
            "FECHA Y UBIGEO", "NACIMIENTO: FECHA Y UBIGEO", "FECHA DE NACIMIENTO",
            "FECHA NACIMIENTO", "NACIMIENTO", "F. NAC", "F. NACIMIENTO", "NACIMIENTO."
        ]
        for i, line in enumerate(combined_lines):
            t = line.text.upper()
            if any(k in t for k in birth_anchors):
                # Check if the line itself contains the date (e.g. "11 05 1963 190109")
                clean_t = re.sub(r"^.*?(NACIMIENTO|FECHA\s*Y\s*UBIGEO|FECHA\s*DE\s*NACIMIENTO|F\.?\s*NAC)[\:\s\-]*", "", t).strip()
                valid, formatted, _ = normalize_and_validate_date(clean_t or t)
                if valid and formatted != "NO CADUCA":
                    birth_date = formatted
                    birth_conf = max(88.0, line.confidence)
                    birth_anchor = line.text
                    break
                else:
                    # Scan next 1-4 lines
                    for offset in range(1, 5):
                        if i + offset < len(combined_lines):
                            next_t = combined_lines[i + offset].text.upper()
                            # Skip if line is another field label
                            if any(sk in next_t for sk in ["SEXO", "ESTADO", "CIVIL", "EMISION", "CADUCIDAD"]):
                                continue
                            val_ok, fmt_d, _ = normalize_and_validate_date(next_t)
                            if val_ok and fmt_d != "NO CADUCA":
                                birth_date = fmt_d
                                birth_conf = max(86.0, combined_lines[i + offset].confidence)
                                birth_anchor = line.text
                                break
                    if birth_date:
                        break

        # Fallback to date candidates pool if visual anchors didn't match
        if not birth_date and candidate_pools and candidate_pools.get("dates_candidates"):
            for cand_val, cand_conf, _ in candidate_pools["dates_candidates"]:
                v_ok, fmt_d, _ = normalize_and_validate_date(cand_val)
                if v_ok and fmt_d != "NO CADUCA":
                    # Birth date year is typically in the past (e.g. 1930 to current_year - 15)
                    try:
                        d_obj = datetime.strptime(fmt_d, "%d/%m/%Y")
                        if 1930 <= d_obj.year <= (datetime.now().year - 14):
                            birth_date = fmt_d
                            birth_conf = max(75.0, cand_conf)
                            birth_anchor = "Consenso Multi-Intento Fechas"
                            break
                    except ValueError:
                        pass

    val_birth_ok, val_birth_fmt, birth_err = normalize_and_validate_date(birth_date) if birth_date else (False, "", "No detectada")
    birth_status = SemanticExtractor.determine_field_status(birth_conf, val_birth_ok)
    fields["birth_date"] = FieldConfidence(
        value=val_birth_fmt if val_birth_ok else birth_date,
        confidence=birth_conf if val_birth_ok else 0.0,
        is_valid=val_birth_ok,
        status=birth_status,
        origin_type="LEIDO_OCR",
        validation_message=birth_err,
        anchor_matched=birth_anchor,
    )

    # 5. SEXO
    sex = ""
    sex_conf = 0.0
    sex_anchor = None

    if mrz_data and mrz_data.get("sex"):
        sex = mrz_data["sex"]
        sex_conf = 99.0
        sex_anchor = "MRZ ICAO TD1"
    else:
        for i, line in enumerate(combined_lines):
            t = line.text.upper()
            if "SEXO" in t:
                # Check within line
                tokens = t.replace("SEXO", "").replace(":", " ").replace("-", " ").split()
                if "M" in tokens or "MASCULINO" in tokens:
                    sex = "M"
                    sex_conf = 90.0
                    sex_anchor = line.text
                elif "F" in tokens or "FEMENINO" in tokens:
                    sex = "F"
                    sex_conf = 90.0
                    sex_anchor = line.text
                elif i + 1 < len(combined_lines):
                    next_val = combined_lines[i+1].text.strip().upper()
                    if next_val in ["M", "F", "MASCULINO", "FEMENINO"]:
                        sex = next_val[0]
                        sex_conf = 88.0
                        sex_anchor = line.text

    val_sex_ok, val_sex_fmt, sex_err = normalize_sex(sex) if sex else (False, "", "No detectado")
    sex_status = SemanticExtractor.determine_field_status(sex_conf, val_sex_ok)
    fields["sex"] = FieldConfidence(
        value=val_sex_fmt if val_sex_ok else sex,
        confidence=sex_conf if val_sex_ok else 0.0,
        is_valid=val_sex_ok,
        status=sex_status,
        origin_type="LEIDO_OCR",
        validation_message=sex_err,
        anchor_matched=sex_anchor,
    )

    # 6. FECHAS DE EMISIÓN, CADUCIDAD E INSCRIPCIÓN
    issue_date = ""
    issue_conf = 0.0
    expiry_date = ""
    expiry_conf = 0.0

    if mrz_data and mrz_data.get("expiry_date"):
        expiry_date = mrz_data["expiry_date"]
        expiry_conf = 99.0

    if not expiry_date and any(k in combined_full_text for k in ["NO CADUCA", "NO CADUC", "NO VENCE", "PERMANENTE"]):
        expiry_date = "NO CADUCA"
        expiry_conf = 99.0

    # 6A. Anchor-based date search (scan up to 4 lines forward)
    for i, line in enumerate(front_lines_list + back_lines_list):
        t = line.text.upper()

        # FECHA DE EMISIÓN
        if any(k in t for k in ["EMISION", "EMISIÓN", "FECHA EMISION", "FECHA DE EMISION", "FECHA EMISIÓN", "F. EMISION", "F. EMIS", "FECHAEMISION"]) and not issue_date:
            valid, formatted, _ = normalize_and_validate_date(t)
            if valid and formatted != "NO CADUCA":
                issue_date = formatted
                issue_conf = max(88.0, line.confidence)
            else:
                for off in range(1, 5):
                    if i + off < len(front_lines_list + back_lines_list):
                        candidate_t = (front_lines_list + back_lines_list)[i + off].text.upper()
                        # Avoid taking other known field headers
                        if any(h in candidate_t for h in ["CADUCIDAD", "INSCRIPCION", "NACIMIENTO"]):
                            continue
                        val_ok, fmt_d, _ = normalize_and_validate_date(candidate_t)
                        if val_ok and fmt_d != "NO CADUCA":
                            issue_date = fmt_d
                            issue_conf = max(85.0, (front_lines_list + back_lines_list)[i + off].confidence)
                            break

        # FECHA DE CADUCIDAD
        if any(k in t for k in ["CADUCIDAD", "VENCIMIENTO", "FECHA DE CADUCIDAD", "FECHA CADUCIDAD", "F. CADUCIDAD", "F. CAD", "FECHACADUCIDAD"]) and not expiry_date:
            if "NO CADUCA" in t or "NO CADUC" in t:
                expiry_date = "NO CADUCA"
                expiry_conf = 99.0
            else:
                valid, formatted, _ = normalize_and_validate_date(t)
                if valid:
                    expiry_date = formatted
                    expiry_conf = max(88.0, line.confidence)
                else:
                    for off in range(1, 4):
                        if i + off < len(front_lines_list + back_lines_list):
                            candidate_t = (front_lines_list + back_lines_list)[i + off].text.upper()
                            if "NO CADUCA" in candidate_t:
                                expiry_date = "NO CADUCA"
                                expiry_conf = 99.0
                                break
                            val_ok, fmt_d, _ = normalize_and_validate_date(candidate_t)
                            if val_ok:
                                expiry_date = fmt_d
                                expiry_conf = max(85.0, (front_lines_list + back_lines_list)[i + off].confidence)
                                break

    # 6B. Chronological Fallback across all detected dates on front
    if not issue_date or not expiry_date:
        all_front_dates = []
        for l in front_lines_list:
            v_ok, fmt_d, _ = normalize_and_validate_date(l.text)
            if v_ok and fmt_d != "NO CADUCA":
                try:
                    dt = datetime.strptime(fmt_d, "%d/%m/%Y")
                    # Filter out birth date if known
                    if not (val_birth_ok and fmt_d == val_birth_fmt):
                        all_front_dates.append((dt, fmt_d, l.confidence))
                except ValueError:
                    pass

        # Sort dates chronologically
        all_front_dates.sort(key=lambda x: x[0])
        if len(all_front_dates) >= 3:
            # Format on DNI Azul: Inscription < Emission < Expiry
            if not issue_date:
                issue_date = all_front_dates[-2][1]
                issue_conf = max(82.0, all_front_dates[-2][2])
            if not expiry_date:
                expiry_date = all_front_dates[-1][1]
                expiry_conf = max(82.0, all_front_dates[-1][2])
        elif len(all_front_dates) == 2:
            if not issue_date:
                issue_date = all_front_dates[0][1]
                issue_conf = max(80.0, all_front_dates[0][2])
            if not expiry_date:
                expiry_date = all_front_dates[1][1]
                expiry_conf = max(80.0, all_front_dates[1][2])
        elif len(all_front_dates) == 1:
            # If date is in future -> Expiry, if past -> Issue
            d_obj, d_str, d_c = all_front_dates[0]
            if d_obj.year > datetime.now().year and not expiry_date:
                expiry_date = d_str
                expiry_conf = max(80.0, d_c)
            elif d_obj.year <= datetime.now().year and not issue_date:
                issue_date = d_str
                issue_conf = max(80.0, d_c)

    val_iss_ok, val_iss_fmt, iss_err = normalize_and_validate_date(issue_date) if issue_date else (False, "", "No detectada")
    fields["issue_date"] = FieldConfidence(
        value=val_iss_fmt if val_iss_ok else issue_date,
        confidence=issue_conf if val_iss_ok else 0.0,
        is_valid=val_iss_ok,
        status=SemanticExtractor.determine_field_status(issue_conf, val_iss_ok),
        origin_type="LEIDO_OCR",
        validation_message=iss_err,
    )

    val_exp_ok = (expiry_date == "NO CADUCA") or bool(expiry_date and normalize_and_validate_date(expiry_date)[0])
    fields["expiry_date"] = FieldConfidence(
        value=expiry_date,
        confidence=expiry_conf if val_exp_ok else 0.0,
        is_valid=val_exp_ok,
        status=SemanticExtractor.determine_field_status(expiry_conf, val_exp_ok),
        origin_type="LEIDO_OCR",
    )

    # 7. UBIGEO, DEPARTAMENTO, PROVINCIA, DISTRITO & DIRECCIÓN
    ubigeo_code = ""
    dept_val = ""
    prov_val = ""
    dist_val = ""
    ubigeo_conf = 0.0
    address = ""
    address_conf = 0.0

    def is_valid_ubigeo_code(code: str) -> bool:
        return bool(re.match(r"^(0[1-9]|1[0-9]|2[0-5])\d{4}$", code))

    # 7A. Search 6-digit Ubigeo code on front (under birth date) and back (Cuarto Nivel / Ubigeo)
    for line in combined_lines:
        t = line.text.upper()
        if any(k in t for k in ["UBIGEO", "CUARTO NIVEL", "CUARTONIVEL", "CUARTONVEL", "CUARTO", "NIVEL"]):
            m_ub = re.search(r"\b(\d{6})\b", t)
            if m_ub and is_valid_ubigeo_code(m_ub.group(1)):
                ubigeo_code = m_ub.group(1)
                ubigeo_conf = max(88.0, line.confidence)
                break
        elif "NACIMIENTO" in t or "UOIGEO" in t or "UBIGEO" in t:
            m_6 = re.search(r"\b(\d{6})\b", t)
            if m_6 and is_valid_ubigeo_code(m_6.group(1)):
                ubigeo_code = m_6.group(1)
                ubigeo_conf = max(85.0, line.confidence)

    if not ubigeo_code:
        # Check standalone 6 digits in lines (must be a valid Peru department prefix 01-25)
        for line in combined_lines:
            m_6 = re.search(r"^\s*(\d{6})\s*$", line.text)
            if m_6 and is_valid_ubigeo_code(m_6.group(1)):
                ubigeo_code = m_6.group(1)
                ubigeo_conf = max(80.0, line.confidence)
                break

    # 7B. Parse Departamento, Provincia, Distrito from back OCR lines
    # Check for known department in back lines first
    for i, line in enumerate(back_lines_list):
        t = line.text.upper().strip()
        if any(k in t for k in ["DOMICILIO", "DIRECCION", "DIR.", "AV.", "JR.", "CALLE", "PSJE", "MZ", "LT"]):
            continue
        for dep in PERU_DEPARTMENTS:
            if re.search(rf"\b{dep}\b", t) or t == dep:
                dept_val = dep
                # Check if this line is part of a 3-tier vertical column layout: [Distrito_val, Provincia_val, Departamento_val]
                if i >= 2 and not prov_val and not dist_val:
                    cand_p = back_lines_list[i-1].text.upper().strip()
                    cand_d = back_lines_list[i-2].text.upper().strip()
                    if cand_p and is_valid_name_token(cand_p) and not any(k in cand_p for k in ["DEPARTAMENTO", "PROVINCIA", "DISTRITO", "CONSTANCIA", "SUFRAGIO"]):
                        prov_val = cand_p
                    if cand_d and is_valid_name_token(cand_d) and not any(k in cand_d for k in ["DEPARTAMENTO", "PROVINCIA", "DISTRITO", "CONSTANCIA", "SUFRAGIO"]):
                        dist_val = cand_d
                break
        if dept_val:
            break

    # If department was found but prov/dist are missing, check anchor labels
    if not dept_val or not prov_val or not dist_val:
        for i, line in enumerate(back_lines_list):
            t = line.text.upper().strip()
            
            # Departamento
            if any(k in t for k in ["DEPARTAMENTO", "DPTO."]) and not dept_val:
                clean_d = re.sub(r"^.*?(DEPARTAMENTO|DPTO\.)[:\s\-]*", "", t).strip()
                if clean_d and is_valid_name_token(clean_d):
                    for dep in PERU_DEPARTMENTS:
                        if dep in clean_d or clean_d in dep:
                            dept_val = dep
                            break
                else:
                    for off in range(1, 5):
                        if i + off < len(back_lines_list):
                            nxt = back_lines_list[i+off].text.upper().strip()
                            if nxt and is_valid_name_token(nxt) and not any(k in nxt for k in ["PROVINCIA", "DISTRITO", "SUFRAGIO", "CONSTANCIA"]):
                                for dep in PERU_DEPARTMENTS:
                                    if dep in nxt or nxt in dep:
                                        dept_val = dep
                                        break
                                if dept_val:
                                    break

            # Provincia
            if any(k in t for k in ["PROVINCIA", "PROVINCLA"]) and not prov_val:
                clean_p = re.sub(r"^.*?(PROVINCIA|PROVINCLA)[:\s\-]*", "", t).strip()
                if clean_p and is_valid_name_token(clean_p) and not any(k in clean_p for k in ["DEPARTAMENTO", "DISTRITO"]):
                    prov_val = clean_p
                else:
                    for off in range(1, 5):
                        if i + off < len(back_lines_list):
                            nxt = back_lines_list[i+off].text.upper().strip()
                            if nxt and is_valid_name_token(nxt) and not any(k in nxt for k in ["DEPARTAMENTO", "DISTRITO", "SUFRAGIO", "CONSTANCIA", "PROVINCIA"]):
                                if nxt != dept_val and nxt != dist_val:
                                    prov_val = nxt
                                    break

            # Distrito
            if "DISTRITO" in t and not dist_val:
                clean_di = re.sub(r"^.*?DISTRITO[:\s\-]*", "", t).strip()
                if clean_di and is_valid_name_token(clean_di) and not any(k in clean_di for k in ["DEPARTAMENTO", "PROVINCIA"]):
                    dist_val = clean_di
                else:
                    for off in range(1, 5):
                        if i + off < len(back_lines_list):
                            nxt = back_lines_list[i+off].text.upper().strip()
                            if nxt and is_valid_name_token(nxt) and not any(k in nxt for k in ["DEPARTAMENTO", "PROVINCIA", "SUFRAGIO", "CONSTANCIA", "DISTRITO"]):
                                if nxt != dept_val and nxt != prov_val:
                                    dist_val = nxt
                                    break

    # Build synthesized Ubigeo string
    # Clean OCR quirks on district / province names (e.g. OUILLO -> QUILLO)
    if dist_val:
        dist_val = re.sub(r"^OUI", "QUI", dist_val)
        dist_val = re.sub(r"^OUE", "QUE", dist_val)
        dist_val = re.sub(r"^OUA", "QUA", dist_val)
        if dist_val.startswith("O") and len(dist_val) > 3 and dist_val[1:] in ["UILLO", "EROBAMBA", "ERO", "ERECOTILLO", "ILMANA", "INUA", "IRUVILCA"]:
            dist_val = "Q" + dist_val[1:]

    if prov_val:
        prov_val = re.sub(r"^OUI", "QUI", prov_val)
        prov_val = re.sub(r"^OUE", "QUE", prov_val)
        prov_val = re.sub(r"^OUA", "QUA", prov_val)

    # Avoid duplicate parts in synthesized Ubigeo
    synthesized_parts = []
    seen_parts = set()
    for p in [dept_val, prov_val, dist_val]:
        if p:
            p_clean = re.sub(r"\bOUILLO\b", "QUILLO", p)
            p_clean = re.sub(r"\bOUERO\b", "QUERO", p_clean)
            p_clean = re.sub(r"\bOUI", "QUI", p_clean)
            if p_clean not in seen_parts:
                seen_parts.add(p_clean)
                synthesized_parts.append(p_clean)

    if synthesized_parts:
        ubigeo_str = " / ".join(synthesized_parts)
        if ubigeo_code and ubigeo_code not in ubigeo_str:
            ubigeo_str = f"{ubigeo_str} ({ubigeo_code})"
        ubigeo_conf = max(88.0, ubigeo_conf)
    elif ubigeo_code:
        ubigeo_str = ubigeo_code
        ubigeo_conf = max(85.0, ubigeo_conf)
    else:
        ubigeo_str = ""

    fields["ubigeo"] = FieldConfidence(
        value=ubigeo_str,
        confidence=ubigeo_conf if ubigeo_str else 0.0,
        is_valid=bool(ubigeo_str),
        status=SemanticExtractor.determine_field_status(ubigeo_conf, bool(ubigeo_str)),
        origin_type="LEIDO_OCR",
    )

    # 7C. DIRECCIÓN / DOMICILIO (Clean address without background leakage or barcode numbers)
    stop_address_keywords = [
        "CUARTO NIVEL", "CUARTONIVEL", "CUARTONVEL", "CUARTO", "NIVEL",
        "DEPARTAMENTO", "PROVINCIA", "DISTRITO", "OBSERVACIONES", "BSERVACIONES",
        "DONACION", "DONACIÓN", "ORGANOS", "ÓRGANOS", "VOTACION", "VOTACIÓN",
        "GRUPO", "FIRMA", "HUELLA", "I<PER", "REPUBLICA", "RENIEC", "SUFRAGIO", "CONSTANCIA"
    ]

    # Peruvian address indicators
    peru_address_prefixes = [
        "CASERIO", "CASERÍO", "CAS.", "C.P.", "CENTRO POBLADO", "SECTOR", "FUNDO", "ANEXO",
        "COMUNIDAD", "PARCELA", "ASENTAMIENTO", "A.H.", "AA.HH.", "AA HH",
        "AV.", "AVENIDA", "AV ", "JR.", "JIRON", "JIRÓN", "JR ", "CALLE", "PSJE", "PASAJE", "PSJ.",
        "MZ.", "MANZANA", "MZ ", "LT.", "LOTE", "LT ", "BLOCK", "BLQ.",
        "URB.", "URBANIZACION", "URBANIZACIÓN", "URB ", "COOP.", "COOPERATIVA", "VILLA", "BARRIO",
        "CARRETERA", "KM.", "KM ", "PANAMERICANA", "PROLONGACION", "PROL.", "PROL "
    ]

    address_header_pattern = r"(?:DOMICILI[OA0-9]|DIRE[A-Z0-9]{2,5}ON|DIREC[A-Z0-9]*|DIR\.?)"

    # Method 1: Header-based scan ("DOMICILIO", "DIRECCION", "DIREACLON", etc.)
    for i, line in enumerate(back_lines_list):
        t = line.text.upper().strip()
        if re.search(rf"\b{address_header_pattern}\b", t) or any(k in t for k in ["DOMICILIO", "DIRECCION", "DIRECCIÓN", "DIR."]):
            addr_parts = []
            val_in_line = re.sub(rf"^.*?{address_header_pattern}[:\s\-\/]*", "", t, flags=re.IGNORECASE).strip()
            
            # Clean header artifacts like "Y CONSTANCIAS DE SUFRAGIO"
            val_in_line = re.sub(r"^(Y\s+CONSTANCIAS(\s+DE\s+SUFRAGIO)?|CONSTANCIAS(\s+DE\s+SUFRAGIO)?|SUFRAGIO)[\s:]*", "", val_in_line).strip()

            if not is_invalid_address_candidate(val_in_line):
                addr_parts.append(val_in_line)

            # Check next lines
            for j in range(1, 4):
                if i + j < len(back_lines_list):
                    next_l = back_lines_list[i+j]
                    next_raw = next_l.text.upper().strip()
                    if any(sk in next_raw for sk in stop_address_keywords) or any(sk in next_raw for sk in ["DEPARTAMENTO", "PROVINCIA", "DISTRITO", "UBIGEO"]):
                        break
                    if not is_invalid_address_candidate(next_raw):
                        addr_parts.append(next_raw)
                        # If line had an address prefix or house number, address is complete
                        if any(ap in next_raw for ap in peru_address_prefixes) or re.search(r"\b(S/N|SN|\d+)\b", next_raw):
                            break

            if addr_parts:
                raw_addr = " ".join(addr_parts)
                raw_addr = re.sub(r"(CUARTO\s*NIVEL|CUARTONVEL|CUARTONIVEL)\s*\d*", "", raw_addr, flags=re.IGNORECASE).strip()
                raw_addr = re.sub(r",\s*,", ",", raw_addr).strip(" ,-")
                if not is_invalid_address_candidate(raw_addr):
                    address = raw_addr
                    address_conf = max(85.0, line.confidence)
                    break

    # Method 2: Autonomous Pattern Scanner across all back lines prioritizing genuine address prefixes
    if not address or is_invalid_address_candidate(address):
        # Pass 2A: Explicit address prefix search (e.g. CASERIO CORACOLLO SN, AV LOS HEROES 450)
        for line in back_lines_list:
            t = line.text.upper().strip()
            if is_invalid_address_candidate(t):
                continue
            has_addr_prefix = any(ap in t for ap in peru_address_prefixes)
            if has_addr_prefix:
                clean_cand = re.sub(rf"^.*?{address_header_pattern}[:\s\-\/]*", "", t, flags=re.IGNORECASE).strip()
                if not is_invalid_address_candidate(clean_cand):
                    address = clean_cand
                    address_conf = max(88.0, line.confidence)
                    break

    if not address or is_invalid_address_candidate(address):
        # Pass 2B: Fallback pattern search (street number or S/N)
        for line in back_lines_list:
            t = line.text.upper().strip()
            if is_invalid_address_candidate(t):
                continue
            has_street_num = bool(re.search(r"\b(S/N|SN|NRO|N°|#)\b", t))
            if has_street_num and len(t) >= 6:
                clean_cand = re.sub(rf"^.*?{address_header_pattern}[:\s\-\/]*", "", t, flags=re.IGNORECASE).strip()
                if not is_invalid_address_candidate(clean_cand):
                    address = clean_cand
                    address_conf = max(80.0, line.confidence)
                    break

    # Final cleanup of address string
    if address:
        if is_invalid_address_candidate(address):
            address = ""
            address_conf = 0.0
        else:
            address = clean_text(address)

    fields["address"] = FieldConfidence(
        value=address,
        confidence=address_conf if address else 0.0,
        is_valid=bool(address),
        status=SemanticExtractor.determine_field_status(address_conf, bool(address)),
        origin_type="LEIDO_OCR",
    )

    # 8. NACIONALIDAD (Predeterminada PERUANA para DNI)
    fields["nationality"] = FieldConfidence(
        value="PERUANA",
        confidence=99.0,
        is_valid=True,
        status="CONFIRMADO",
        origin_type="CALCULADO",
    )

    # 9. ESTADO CIVIL (Single letter S, C, V, D, CO or full word - Nunca omitir)
    civil_status = ""
    civil_conf = 0.0
    civil_anchor = None
    has_civil_label = False

    for i, line in enumerate(combined_lines):
        t = line.text.upper()
        if any(k in t for k in ["ESTADO CIVIL", "EST. CIVIL", "ESTADOCIVIL", "EDO. CIVIL", "ESTADO"]):
            has_civil_label = True
            civil_anchor = line.text
            # Extract token right after anchor
            val_after = re.sub(r"^.*?(ESTADO\s*CIVIL|EST\.\s*CIVIL|ESTADOCIVIL|EDO\.\s*CIVIL|ESTADO)[:\s\-]*", "", t).strip()
            if val_after:
                first_tok = val_after.split()[0]
                val_ok, norm_st, _ = normalize_civil_status(first_tok)
                if val_ok:
                    civil_status = norm_st
                    civil_conf = max(88.0, line.confidence)
                    break
            # Check next lines up to 4 lines forward
            for off in range(1, 5):
                if i + off < len(combined_lines):
                    next_tok = combined_lines[i+off].text.strip().upper()
                    if next_tok:
                        first_w = next_tok.split()[0]
                        val_ok, norm_st, _ = normalize_civil_status(first_w)
                        if val_ok:
                            civil_status = norm_st
                            civil_conf = max(85.0, combined_lines[i+off].confidence)
                            break
            if civil_status:
                break

    if not civil_status:
        # Fallback check for standalone words
        for line in combined_lines:
            t = line.text.upper()
            for st in ["SOLTERO", "CASADO", "VIUDO", "DIVORCIADO", "CONVIVIENTE", "SOLTERA", "CASADA", "VIUDA", "DIVORCIADA"]:
                if st in t.split():
                    val_ok, norm_st, _ = normalize_civil_status(st)
                    if val_ok:
                        civil_status = norm_st
                        civil_conf = max(80.0, line.confidence)
                        civil_anchor = line.text
                        break
            if civil_status:
                break

    # If anchor exists on DNI but no single character was isolated, default to SOLTERO to never omit civil status
    if not civil_status and has_civil_label:
        civil_status = "SOLTERO"
        civil_conf = 75.0
        val_civ_ok = True
        civ_err = "Preseleccionado SOLTERO (verificar con original)"
        civ_status_tier = "REVISAR"
    else:
        val_civ_ok, val_civ_fmt, civ_err = normalize_civil_status(civil_status) if civil_status else (False, "", "No detectado")
        if val_civ_ok:
            civil_status = val_civ_fmt
            civ_status_tier = SemanticExtractor.determine_field_status(civil_conf, val_civ_ok)
        else:
            civ_status_tier = "NO_DETECTADO"

    fields["civil_status"] = FieldConfidence(
        value=civil_status,
        confidence=civil_conf if val_civ_ok else 0.0,
        is_valid=val_civ_ok,
        status=civ_status_tier,
        origin_type="LEIDO_OCR",
        validation_message=civ_err,
        anchor_matched=civil_anchor,
    )

    # 10. GRUPO SANGUÍNEO
    blood_type = ""
    blood_conf = 0.0
    for line in combined_lines:
        t = line.text.upper()
        m_blood = re.search(r"\b(O|A|B|AB)\s*([\+\-])", t)
        if m_blood and any(k in t for k in ["SANGRE", "SANGUINEO", "SANGUÍNEO", "G.S.", "GRUPO"]):
            blood_type = f"{m_blood.group(1)}{m_blood.group(2)}"
            blood_conf = max(85.0, line.confidence)
            break

    fields["blood_type"] = FieldConfidence(
        value=blood_type,
        confidence=blood_conf if blood_type else 0.0,
        is_valid=bool(blood_type),
        status=SemanticExtractor.determine_field_status(blood_conf, bool(blood_type)),
        origin_type="LEIDO_OCR",
    )

    # 11. FIRMA / FIRMA DIGITAL
    has_digital_signature = any(
        k in combined_full_text for k in ["FIRMA DIGITAL", "FIRMA DEL TITULAR", "TITULAR", "DOCUMENTO FIRMADO DIGITALMENTE", "FIRMADO DIGITALMENTE", "FIRMA"]
    )
    fields["digital_signature"] = FieldConfidence(
        value="VERIFICADA" if has_digital_signature else "NO_DETECTADA",
        confidence=90.0 if has_digital_signature else 60.0,
        is_valid=has_digital_signature,
        status="CONFIRMADO" if has_digital_signature else "REVISAR",
        origin_type="LEIDO_OCR",
        anchor_matched="FIRMA DIGITAL" if has_digital_signature else None,
    )

    extracted_dict = {k: v.value for k, v in fields.items()}
    return extracted_dict, fields, warnings

