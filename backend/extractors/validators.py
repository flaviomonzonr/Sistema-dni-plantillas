import re
from datetime import datetime
from typing import Tuple, Optional

# Month abbreviations in Spanish
SPANISH_MONTHS = {
    "ENE": "01", "ENERO": "01",
    "FEB": "02", "FEBRERO": "02",
    "MAR": "03", "MARZO": "03",
    "ABR": "04", "ABRIL": "04",
    "MAY": "05", "MAYO": "05",
    "JUN": "06", "JUNIO": "06",
    "JUL": "07", "JULIO": "07",
    "AGO": "08", "AGOSTO": "08",
    "SET": "09", "SEP": "09", "SETIEMBRE": "09", "SEPTIEMBRE": "09",
    "OCT": "10", "OCTUBRE": "10",
    "NOV": "11", "NOVIEMBRE": "11",
    "DIC": "12", "DICIEMBRE": "12",
}

# Standard Peruvian Departments for Ubigeo validation
PERU_DEPARTMENTS = [
    "AMAZONAS", "ANCASH", "APURIMAC", "AREQUIPA", "AYACUCHO", "CAJAMARCA",
    "CALLAO", "CUSCO", "HUANCAVELICA", "HUANUCO", "ICA", "JUNIN",
    "LA LIBERTAD", "LAMBAYEQUE", "LIMA", "LORETO", "MADRE DE DIOS",
    "MOQUEGUA", "PASCO", "PIURA", "PUNO", "SAN MARTIN", "TACNA",
    "TUMBES", "UCAYALI"
]

# Common Peruvian Given Names for separating concatenated names
COMMON_PERU_GIVEN_NAMES = {
    "AARON", "ABEL", "ABRAHAM", "ADA", "ADAN", "ADELA", "ADOLFO", "ADRIAN", "ADRIANA",
    "AGUSTIN", "AIDA", "ALAN", "ALBERTO", "ALEJANDRA", "ALEJANDRO", "ALEX", "ALEXA",
    "ALEXANDER", "ALEXANDRA", "ALEXIS", "ALFONSO", "ALFREDO", "ALICIA", "ALINA", "ALVARO",
    "AMALIA", "AMANDA", "AMERICO", "ANA", "ANALI", "ANASTACIA", "ANDREA", "ANDRES",
    "ANGEL", "ANGELA", "ANGELICA", "ANIBAL", "ANITA", "ANTONIA", "ANTONIO", "ARMANDO",
    "ARNALDO", "ARTURO", "AUGUSTO", "AURELIO", "AURORA", "BEATRIZ", "BENJAMIN", "BERTHA",
    "BETY", "BETTY", "BLANCA", "BORIS", "BRAULIO", "BRENDA", "BRYAN", "CAMILA", "CARIDAD",
    "CARLA", "CARLOS", "CARMEN", "CAROLINA", "CECILIA", "CELIA", "CESAR", "CHRISTIAN",
    "CINTHIA", "CINTIA", "CLAUDIA", "CLAUDIO", "CLELIA", "CONSUELO", "CRISTHIAN", "CRISTIAN",
    "CRISTINA", "CYNTHIA", "DAISY", "DANIEL", "DANIELA", "DARIO", "DAVID", "DEBORA",
    "DELIA", "DENIS", "DENISSE", "DENNIS", "DIANA", "DIEGO", "DINA", "DIONISIO", "DOMINGO",
    "DORA", "DORIS", "EDGAR", "EDGARDO", "EDILBERTO", "EDITH", "EDSON", "EDUARDO", "EDWIN",
    "EFRAIN", "ELBA", "ELENA", "ELIA", "ELIAN", "ELIAS", "ELISA", "ELIZABETH", "ELMER",
    "ELOY", "ELSA", "ELVIRA", "EMILIA", "EMILIANO", "EMILIO", "EMMA", "ENRIQUE", "ERICH",
    "ERICK", "ERIKA", "ERNESTO", "ESMERALDA", "ESPERANZA", "ESTEBAN", "ESTELA", "ESTHER",
    "EUGENIO", "EVA", "EVELYN", "EVER", "FABIAN", "FABIOLA", "FATIMA", "FEDERICO", "FELICIA",
    "FELICITA", "FELIPE", "FELIX", "FERMIN", "FERNANDO", "FIORELLA", "FLAVIA", "FLAVIO",
    "FLOR", "FLORA", "FORTUNATO", "FRANCISCA", "FRANCISCO", "FRANK", "FRANKLIN", "FREDDY",
    "FREDI", "FREDY", "GABRIEL", "GABRIELA", "GENARO", "GERARDO", "GERMAN", "GIOVANNA",
    "GISELA", "GISELLA", "GLADYS", "GLORIA", "GONZALO", "GRACIELA", "GREGORIO", "GUADALUPE",
    "GUILLERMO", "GUSTAVO", "HAYDEE", "HECTOR", "HELEN", "HENRY", "HERBERT", "HERNAN",
    "HILARIO", "HILDA", "HILDEBRANDO", "HONORATO", "HUGO", "HUMBERTO", "IGNACIO", "INES",
    "INGRID", "IRENE", "IRMA", "ISABEL", "ISIDRO", "ISMAEL", "IVAN", "IVONNE", "JACINTO",
    "JAIME", "JANET", "JAVIER", "JEAN", "JENNY", "JESSICA", "JESUS", "JHON", "JHONATAN",
    "JHONY", "JIMMY", "JOEL", "JOHAN", "JOHANA", "JORGE", "JOSE", "JOSEFA", "JOSEFINA",
    "JOSELYN", "JOSHUA", "JOSUE", "JUAN", "JUANA", "JUDITH", "JULIA", "JULIAN", "JULIO",
    "JUNIOR", "JUSTO", "KAREN", "KARINA", "KARLA", "KATHERINE", "KATTY", "KEVIN", "LEILA",
    "LEONARDO", "LEONCIO", "LEONOR", "LEOPOLDO", "LESLIE", "LEYDI", "LIDIA", "LILIANA",
    "LINA", "LINO", "LIZ", "LIZBETH", "LORENA", "LOURDES", "LUCERO", "LUCIA", "LUCIANA",
    "LUCIANO", "LUCIO", "LUCRECIA", "LUIS", "LUISA", "LUPE", "LUZ", "MAGALI", "MAGALY",
    "MAGDALENA", "MANUEL", "MANUELA", "MARCELA", "MARCELINO", "MARCELO", "MARCIAL", "MARCO",
    "MARCOS", "MARGARITA", "MARIA", "MARIANA", "MARIANO", "MARIBEL", "MARINA", "MARIO",
    "MARISOL", "MARITZA", "MARLENE", "MARTA", "MARTHA", "MARTIN", "MARY", "MATILDE",
    "MAURA", "MAURICIO", "MAURO", "MAX", "MAXIMO", "MAYRA", "MELANIE", "MELCHOR", "MELISSA",
    "MERCEDES", "MIA", "MICHAEL", "MIGUEL", "MILAGROS", "MIRIAM", "MIRTHA", "MOISES",
    "MONICA", "MYRIAM", "NANCY", "NATALIA", "NATALY", "NELLY", "NELSON", "NESTOR", "NICOLAS",
    "NIDIA", "NILDA", "NILO", "NILVER", "NOEMI", "NORA", "NORMA", "OCTAVIO", "OLGA", "ORLANDO",
    "OSCAR", "OSWALDO", "PABLO", "PAOLA", "PAOLO", "PATRICIA", "PATRICIO", "PAULA", "PAULINA",
    "PAULO", "PEDRO", "PERCY", "PILAR", "RAFAEL", "RAIZA", "RAMIRO", "RAMON", "RAQUEL",
    "RAUL", "REBECA", "REGINA", "RENAN", "RENATO", "RENE", "RENEE", "RICARDO", "RICHARD",
    "RITA", "ROBERT", "ROBERTO", "ROCIO", "RODOLFO", "RODRIGO", "ROGELIO", "ROGER", "ROLANDO",
    "ROMAN", "ROMEL", "ROMINA", "RONALD", "ROQUE", "ROSA", "ROSALIA", "ROSARIO", "ROSAURA",
    "ROXANA", "RUBEN", "RUTH", "SABINA", "SAMUEL", "SANDRA", "SANTIAGO", "SANTOS", "SARA",
    "SAUL", "SEBASTIAN", "SEGUNDO", "SERGIO", "SILVIA", "SILVIO", "SIMON", "SOFIA", "SOL",
    "SONIA", "STEPHANIE", "SUSANA", "TANIA", "TERESA", "TOMAS", "URIEL", "URSULA", "VALENTIN",
    "VALENTINA", "VALERIA", "VALERIANA", "VANESSA", "VERONICA", "VICENTE", "VICTOR",
    "VICTORIA", "VILMA", "VIRGILIO", "VIRGINIA", "VLADIMIR", "WALTER", "WASHINGTON",
    "WILDER", "WILFREDO", "WILLIAMS", "WILLIAM", "WILLY", "WILMER", "WILSON", "YADIRA",
    "YANET", "YENI", "YENNY", "YESENIA", "YESSICA", "YOLANDA", "YOSHI", "YURI", "ZULEMA"
}


def separate_concatenated_names(text: str) -> str:
    """
    Separates names that have been concatenated without spaces by OCR
    (e.g., 'BETYVALERIANA' -> 'BETY VALERIANA', 'JUANCARLOS' -> 'JUAN CARLOS').
    """
    if not text:
        return text

    clean = text.strip()
    tokens = clean.split()
    res_tokens = []

    for tok in tokens:
        tok_upper = tok.upper()
        # If token is long and not in name dictionary as a standalone name
        if len(tok_upper) >= 6 and tok_upper not in COMMON_PERU_GIVEN_NAMES:
            split_found = False
            # Try splitting into two known names
            for i in range(3, len(tok_upper) - 2):
                p1, p2 = tok_upper[:i], tok_upper[i:]
                if p1 in COMMON_PERU_GIVEN_NAMES and p2 in COMMON_PERU_GIVEN_NAMES:
                    res_tokens.extend([p1, p2])
                    split_found = True
                    break
            if not split_found:
                res_tokens.append(tok)
        else:
            res_tokens.append(tok)

    return " ".join(res_tokens)


def is_invalid_address_candidate(text: str) -> bool:
    """
    Validates whether a line text can possibly be a Peruvian street address.
    Rejects barcode numbers, voting group codes, pure digit sequences, and administrative headers.
    """
    if not text or len(text.strip()) < 3:
        return True

    t = text.strip().upper()

    # 1. Reject pure digits, spaces, dots, dashes, slashes (e.g. '000025 000025 021843 0005 96180309')
    if re.match(r"^[\d\s\-\.\,\/]+$", t):
        return True

    # 2. Reject lines where digits heavily outnumber letters (barcodes with minimal text)
    digits_count = sum(c.isdigit() for c in t)
    alpha_count = sum(c.isalpha() for c in t)
    if alpha_count < 3:
        return True
    if digits_count > alpha_count:
        return True

    # 3. Reject barcode sequences (repeated 4+ digit blocks)
    if re.search(r"^\d{4,}(\s+\d{4,})+$", t):
        return True

    # 4. Reject administrative headers and document labels
    stop_words = [
        "CONSTANCIA", "SUFRAGIO", "DE SUFRAGIO", "REPUBLICA DEL PERU", "REPUBLICA",
        "RENIEC", "ELECCIONES", "TRIBUNAL", "ORGANOS", "DONACION", "FIRMA", "HUELLA",
        "CUARTO NIVEL", "CUARTONIVEL", "CUARTONVEL", "OBSERVACIONES", "OBSERVACION",
        "BSERVACIONES", "BSERVACION", "ESTADO CIVIL", "DEPARTAMENTO", "PROVINCIA", "DISTRITO",
        "FECHA DE NACIMIENTO", "FECHA DE EMISION", "FECHA DE CADUCIDAD", "CADUCIDAD"
    ]
    if any(sk in t for sk in stop_words):
        return True

    # 5. Reject standalone department names
    for dep in PERU_DEPARTMENTS:
        if t == dep:
            return True

    return False


# Civil Status Mapping for Peruvian IDs (S, C, V, D, CO)
CIVIL_STATUS_MAP = {
    "S": "SOLTERO",
    "SOLTERO": "SOLTERO",
    "SOLTERA": "SOLTERO",
    "C": "CASADO",
    "CASADO": "CASADO",
    "CASADA": "CASADO",
    "V": "VIUDO",
    "VIUDO": "VIUDO",
    "VIUDA": "VIUDO",
    "D": "DIVORCIADO",
    "DIVORCIADO": "DIVORCIADO",
    "DIVORCIADA": "DIVORCIADO",
    "CO": "CONVIVIENTE",
    "CONVIVIENTE": "CONVIVIENTE",
}


def clean_text(text: str) -> str:
    """Removes unwanted OCR noise, multiple spaces and invalid characters."""
    if not text:
        return ""
    cleaned = re.sub(r"[\t\r\n]+", " ", text)
    cleaned = re.sub(r"[<>|]+", "", cleaned)
    cleaned = re.sub(r" +", " ", cleaned)
    return cleaned.strip()


def validate_dni(dni_str: str) -> Tuple[bool, str, Optional[str]]:
    """
    Validates Peruvian DNI format (must be exactly 8 digits).
    Returns: (is_valid, normalized_dni, error_message)
    """
    if not dni_str:
        return False, "", "Número de DNI no detectado"

    # If format like 02763215-2 or 02763215<8, extract the primary 8 digits
    m = re.search(r"\b(\d{8})\b", dni_str)
    if m:
        return True, m.group(1), None

    cleaned = re.sub(r"[^\d]", "", dni_str)
    if len(cleaned) == 8:
        return True, cleaned, None
    elif len(cleaned) > 8:
        # Might include check digit or extra trailing number
        return True, cleaned[:8], None
    elif len(cleaned) == 0:
        return False, "", "Número de DNI no detectado"
    else:
        return False, cleaned, f"DNI inválido: debe tener 8 dígitos (detectados {len(cleaned)})"


def validate_ce(ce_str: str) -> Tuple[bool, str, Optional[str]]:
    """
    Validates Carnet de Extranjería format (usually 9 digits or alphanumeric 8-10 chars).
    """
    if not ce_str:
        return False, "", "Número de Carnet de Extranjería no detectado"

    cleaned = re.sub(r"[^A-Za-z0-9]", "", ce_str.upper())
    if 7 <= len(cleaned) <= 12:
        return True, cleaned, None
    elif len(cleaned) == 0:
        return False, "", "Número de Carnet de Extranjería no detectado"
    else:
        return False, cleaned, f"Formato de CE inusual ({len(cleaned)} caracteres)"


def normalize_and_validate_date(date_raw: str) -> Tuple[bool, str, Optional[str]]:
    """
    Normalizes a date string into standard DD/MM/AAAA format and verifies calendar validity.
    Handles formats like: "15/08/1990", "15-08-1990", "15 08 1990", "15081990", "02 061997", "15 AGO 1990", "NO CADUCA".
    """
    if not date_raw:
        return False, "", "Fecha vacía"

    clean = date_raw.upper().strip()

    # Special handling for non-expiring IDs in Peru
    if any(k in clean for k in ["NO CADUCA", "NO CADUC", "NO VENCE", "PERMANENTE", "ILIMITAD", "INDEFINID"]):
        return True, "NO CADUCA", None
    
    if "00/01/01" in clean or "01/01/0000" in clean or "000101" in clean:
        return True, "NO CADUCA", None

    # Replace month text with numbers if present
    for month_name, month_num in SPANISH_MONTHS.items():
        clean = re.sub(rf"\b{month_name}\b", month_num, clean)

    # 1. Search for standard delimited date: DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY, DD MM YYYY, DD  MM  YYYY
    match = re.search(r"\b(0?[1-9]|[12][0-9]|3[01])[\/\-\.\s]+(0?[1-9]|1[0-2])[\/\-\.\s]+(\d{4}|\d{2})\b", clean)
    if match:
        day, month, year = match.groups()
    else:
        # 2. Search for mixed spaced date: e.g. "02 061997" or "0206 1997"
        mixed_match = re.search(r"\b(0[1-9]|[12][0-9]|3[01])\s*(0[1-9]|1[0-2])\s*(\d{4})\b", clean)
        if mixed_match:
            day, month, year = mixed_match.groups()
        else:
            # 3. Search compact 8-digit date: e.g. 20092023, 24121996, 17092014, 08052008
            compact_match = re.search(r"\b(0[1-9]|[12][0-9]|3[01])(0[1-9]|1[0-2])(\d{4})\b", clean)
            if compact_match:
                day, month, year = compact_match.groups()
            else:
                return False, date_raw, f"Formato de fecha inválido ({date_raw})"

    day = day.zfill(2)
    month = month.zfill(2)

    # Convert 2-digit year to 4-digit year (MRZ or old dates)
    if len(year) == 2:
        y_int = int(year)
        current_yy = datetime.now().year % 100
        year = str(2000 + y_int) if y_int <= (current_yy + 15) else str(1900 + y_int)

    formatted_date = f"{day}/{month}/{year}"

    # Verify true calendar validity
    try:
        dt = datetime.strptime(formatted_date, "%d/%m/%Y")
        if 1900 <= dt.year <= 2100:
            return True, formatted_date, None
        else:
            return False, formatted_date, f"Año fuera de rango ({dt.year})"
    except ValueError:
        return False, formatted_date, f"Fecha de calendario inexistente ({formatted_date})"


def normalize_sex(sex_str: str) -> Tuple[bool, str, Optional[str]]:
    """Normalizes sex to 'M' or 'F'."""
    if not sex_str:
        return False, "", "Sexo no especificado"

    clean = sex_str.upper().strip()
    if clean.startswith("M") or "MASCULINO" in clean or clean == "1":
        return True, "M", None
    elif clean.startswith("F") or "FEMENINO" in clean or clean == "2":
        return True, "F", None
    else:
        return False, clean, "Sexo desconocido (esperado M o F)"


def normalize_civil_status(status_raw: str) -> Tuple[bool, str, Optional[str]]:
    """
    Normalizes civil status for Peruvian IDs (handles S, C, V, D, CO, SOLTERO, etc.).
    """
    if not status_raw:
        return False, "", "Estado civil no detectado"

    clean = re.sub(r"[^A-Z]", "", status_raw.upper().strip())
    if clean in CIVIL_STATUS_MAP:
        return True, CIVIL_STATUS_MAP[clean], None

    for k, v in CIVIL_STATUS_MAP.items():
        if len(k) > 2 and k in clean:
            return True, v, None

    return False, status_raw, f"Estado civil no reconocido ({status_raw})"

