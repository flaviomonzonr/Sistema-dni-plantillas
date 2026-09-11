import re
import unicodedata
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional, List
from backend.config import DEFAULT_EMAIL_DOMAIN, MASTER_EXCEL_PATH
from backend.services.excel_analyzer import ExcelAnalyzer
from backend.services.worker_matcher import WorkerMatcher


class WorkerConsolidator:
    """
    Consolidador inteligente de Ficha del Trabajador.
    Fusiona:
    1. Datos del escaneo OCR de DNI (anverso y reverso)
    2. Datos de búsqueda en Excel (celdas visibles, notas, comentarios y celdas ocultas)
    3. Trazabilidad de origen por cada campo
    4. Cálculos laborales peruanos (Fechas de vigencia de contrato, remuneración en letras, sugerencia de correo).
    """

    def __init__(self, excel_path: Optional[str] = None):
        self.excel_analyzer = ExcelAnalyzer(excel_path or MASTER_EXCEL_PATH)
        self.worker_matcher = WorkerMatcher(self.excel_analyzer)

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Elimina tildes y caracteres especiales para normalizar emails y códigos."""
        if not text:
            return ""
        nfkd = unicodedata.normalize("NFKD", text)
        return "".join([c for c in nfkd if not unicodedata.combining(c)]).lower().strip()

    @staticmethod
    def generate_email_proposal(first_names: str, paternal_surname: str, domain: str = DEFAULT_EMAIL_DOMAIN) -> str:
        """
        Genera una propuesta estándar de correo corporativo:
        Ejemplo: NADIA CELESTE GARCIA BRANDAN -> nadia.garcia@empresa.com.pe
        """
        fn_clean = WorkerConsolidator._normalize_text(first_names)
        first_word = fn_clean.split()[0] if fn_clean.split() else "usuario"
        
        sn_clean = WorkerConsolidator._normalize_text(paternal_surname)
        sn_word = sn_clean.split()[0] if sn_clean.split() else "trabajador"

        # Quitar caracteres no alfanuméricos
        first_word = re.sub(r"[^a-z0-9]", "", first_word)
        sn_word = re.sub(r"[^a-z0-9]", "", sn_word)

        return f"{first_word}.{sn_word}@{domain}"

    @staticmethod
    def calculate_contract_dates(start_date_str: str, duration_months: int) -> Dict[str, Any]:
        """
        Calcula la fecha de término del contrato laboral según la norma peruana:
        Inicio: 08/09/2026, Plazo: 3 meses -> Fin: 07/12/2026 (un día antes del aniversario mensual).
        """
        if not start_date_str:
            return {"start_date": "", "end_date": "", "duration_months": duration_months, "duration_text": ""}

        # Intentar parsear fecha en formatos comunes (DD/MM/YYYY, YYYY-MM-DD, etc.)
        parsed_date = None
        for fmt in ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d.%m.%Y"]:
            try:
                parsed_date = datetime.strptime(start_date_str.strip(), fmt).date()
                break
            except Exception:
                continue

        if not parsed_date:
            return {
                "start_date": start_date_str,
                "end_date": "",
                "duration_months": duration_months,
                "duration_text": f"{duration_months} meses",
                "error": "Formato de fecha de inicio inválido (se esperaba DD/MM/YYYY)"
            }

        # Calcular mes y año destino
        total_months = parsed_date.month - 1 + duration_months
        new_year = parsed_date.year + (total_months // 12)
        new_month = (total_months % 12) + 1
        target_day = parsed_date.day

        # Ajustar a fin de mes si el mes destino tiene menos días
        import calendar
        max_days_in_target_month = calendar.monthrange(new_year, new_month)[1]
        clamped_day = min(target_day, max_days_in_target_month)

        anniversary_date = date(new_year, new_month, clamped_day)
        # Un día antes del aniversario
        end_date = anniversary_date - timedelta(days=1)

        dur_text = "1 mes" if duration_months == 1 else f"{duration_months} meses"

        return {
            "start_date": parsed_date.strftime("%d/%m/%Y"),
            "end_date": end_date.strftime("%d/%m/%Y"),
            "duration_months": duration_months,
            "duration_text": dur_text,
            "start_date_iso": parsed_date.isoformat(),
            "end_date_iso": end_date.isoformat(),
        }

    @staticmethod
    def number_to_soles_words(amount_str: Any) -> str:
        """Convierte una cantidad numérica en Soles a formato de texto formal para contratos."""
        try:
            val_clean = str(amount_str).replace("S/", "").replace(",", "").strip()
            amount = float(val_clean)
        except Exception:
            return str(amount_str)

        units = ["", "UN", "DOS", "TRES", "CUATRO", "CINCO", "SEIS", "SIETE", "OCHO", "NUEVE"]
        tens = ["", "DIEZ", "VEINTE", "TREINTA", "CUARENTA", "CINCUENTA", "SESENTA", "SETENTA", "OCHENTA", "NOVENTA"]
        teens = ["DIEZ", "ONCE", "DOCE", "TRECE", "CATORCE", "QUINCE", "DIECISEIS", "DIECISIETE", "DIECIOCHO", "DIECINUEVE"]
        twenties = ["VEINTE", "VEINTIUNO", "VEINTIDOS", "VEINTITRES", "VEINTICUATRO", "VEINTICINCO", "VEINTISEIS", "VEINTISIETE", "VEINTIOCHO", "VEINTINUEVE"]
        hundreds = ["", "CIENTO", "DOSCIENTOS", "TRESCIENTOS", "CUATROCIENTOS", "QUINIENTOS", "SEISCIENTOS", "SETECIENTOS", "OCHOCIENTOS", "NOVECIENTOS"]

        integer_part = int(amount)
        cents = int(round((amount - integer_part) * 100))

        def convert_under_1000(n):
            if n == 0:
                return ""
            if n == 100:
                return "CIEN"
            res = []
            c = n // 100
            d = (n % 100) // 10
            u = n % 10

            if c > 0:
                res.append(hundreds[c])
            if d == 1:
                res.append(teens[u])
            elif d == 2:
                res.append(twenties[u])
            elif d > 2:
                if u > 0:
                    res.append(f"{tens[d]} Y {units[u]}")
                else:
                    res.append(tens[d])
            elif u > 0:
                res.append(units[u])
            return " ".join(res)

        if integer_part == 0:
            words = "CERO"
        elif integer_part < 1000:
            words = convert_under_1000(integer_part)
        elif integer_part < 1000000:
            thousands = integer_part // 1000
            rem = integer_part % 1000
            th_str = "MIL" if thousands == 1 else f"{convert_under_1000(thousands)} MIL"
            rem_str = convert_under_1000(rem)
            words = f"{th_str} {rem_str}".strip()
        else:
            words = str(integer_part)

        return f"{words} Y {cents:02d}/100 SOLES"

    def consolidate_worker_profile(
        self,
        dni: str,
        ocr_data: Optional[Dict[str, Any]] = None,
        custom_excel_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Construye la Ficha Integral del Trabajador cruzando DNI, OCR y Excel con trazabilidad de origen.
        """
        clean_dni = re.sub(r"\D", "", str(dni or "")).strip()
        ocr_data = ocr_data or {}

        # 1. Buscar en Excel
        excel_result = self.excel_analyzer.find_worker_by_dni(clean_dni, custom_excel_path)
        excel_fields = excel_result.get("fields", {}) if excel_result else {}

        # 2. Helper de consolidación de campo
        def resolve_field(key: str, default_val: str = "", default_origin: str = "No registrado", is_editable: bool = True) -> Dict[str, Any]:
            # Prioridad 1: Excel específico si existe
            if key in excel_fields and excel_fields[key].get("value"):
                f = excel_fields[key]
                return {
                    "field_key": key,
                    "value": str(f["value"]).strip(),
                    "origin": f["origin"],
                    "origin_type": f["origin_type"],
                    "is_hidden_or_note": f.get("is_hidden", False) or f.get("origin_type") == "EXCEL_COMMENT",
                    "comment": f.get("comment"),
                    "is_editable": is_editable,
                }

            # Prioridad 2: OCR si existe
            if key in ocr_data and ocr_data[key]:
                conf = ocr_data.get("field_confidences", {}).get(key, 90)
                return {
                    "field_key": key,
                    "value": str(ocr_data[key]).strip(),
                    "origin": f"Escaneo DNI (OCR {conf}%)",
                    "origin_type": "OCR",
                    "is_hidden_or_note": False,
                    "comment": None,
                    "is_editable": is_editable,
                }

            # Fallback
            return {
                "field_key": key,
                "value": default_val,
                "origin": default_origin,
                "origin_type": "SYSTEM",
                "is_hidden_or_note": False,
                "comment": None,
                "is_editable": is_editable,
            }

        # Identificación
        f_dni = resolve_field("dni", clean_dni, "Escaneo / Ingreso Directo", is_editable=False)
        f_paternal = resolve_field("paternal_surname", "", "Pendiente")
        f_maternal = resolve_field("maternal_surname", "", "Pendiente")
        f_first_names = resolve_field("first_names", "", "Pendiente")

        # Nombre completo
        nombres = f_first_names["value"]
        ap_pat = f_paternal["value"]
        ap_mat = f_maternal["value"]
        apellidos = f"{ap_pat} {ap_mat}".strip()
        full_name_val = f"{apellidos} {nombres}".strip() or f"TRABAJADOR {clean_dni}"

        f_full_name = {
            "field_key": "full_name",
            "value": full_name_val,
            "origin": "Consolidado de Apellidos y Nombres",
            "origin_type": "CALCULATED",
            "is_hidden_or_note": False,
            "is_editable": False,
        }

        # Datos Personales
        f_birth_date = resolve_field("birth_date", "", "Pendiente")
        f_sex = resolve_field("sex", "M", "Pendiente")
        f_civil_status = resolve_field("civil_status", "SOLTERO(A)", "Pendiente")
        f_address = resolve_field("address", "", "Pendiente")
        f_district = resolve_field("district", "LIMA", "Pendiente")
        f_province = resolve_field("province", "LIMA", "Pendiente")
        f_department = resolve_field("department", "LIMA", "Pendiente")

        # Contacto (Celular y Correo Inteligente)
        f_celular = resolve_field("celular", "", "Pendiente / Ingresar en revisión", is_editable=True)
        
        # Correo: Si no está en Excel, generar propuesta
        if "correo" in excel_fields and excel_fields["correo"].get("value"):
            f_correo = resolve_field("correo")
        else:
            proposed_email = self.generate_email_proposal(nombres, ap_pat)
            f_correo = {
                "field_key": "correo",
                "value": proposed_email,
                "origin": "Propuesta Automática del Sistema",
                "origin_type": "SYSTEM",
                "is_hidden_or_note": False,
                "is_editable": True,
            }

        # Datos Laborales
        f_cargo = resolve_field("cargo", "OPERARIO", "Excel / Predeterminado", is_editable=True)
        f_area = resolve_field("area", "OPERACIONES", "Excel / Predeterminado", is_editable=True)
        f_regimen = resolve_field("regimen", "RÉGIMEN GENERAL (D.L. 728)", "Predeterminado", is_editable=True)
        f_tipo_contrato = resolve_field("tipo_contrato", "NECESIDAD DE MERCADO", "Predeterminado", is_editable=True)
        
        # Remuneración
        remun_raw = resolve_field("remuneracion", "1500.00", "Excel / Mínimo", is_editable=True)
        remun_words = self.number_to_soles_words(remun_raw["value"])

        # AFP / Sistema Pensionario (Revisar si vino de comentario o celda oculta)
        afp_val = "AFP HABITAT"
        afp_origin = "Predeterminado"
        afp_type = "SYSTEM"
        afp_hidden = False

        if "afp_nota" in excel_fields:
            afp_val = excel_fields["afp_nota"]["value"]
            afp_origin = excel_fields["afp_nota"]["origin"]
            afp_type = excel_fields["afp_nota"]["origin_type"]
            afp_hidden = True
        elif "afp" in excel_fields and excel_fields["afp"].get("value"):
            afp_val = excel_fields["afp"]["value"]
            afp_origin = excel_fields["afp"]["origin"]
            afp_type = excel_fields["afp"]["origin_type"]

        f_afp = {
            "field_key": "afp",
            "value": afp_val,
            "origin": afp_origin,
            "origin_type": afp_type,
            "is_hidden_or_note": afp_hidden,
            "is_editable": True,
        }

        f_asig_fam = resolve_field("asignacion_familiar", "SI", "Excel / General", is_editable=True)
        f_centro_costo = resolve_field("centro_costo", "CC-101", "Excel / General", is_editable=True)

        # Configuración inicial de fechas de contrato
        today_str = datetime.now().strftime("%d/%m/%Y")
        dates_calc = self.calculate_contract_dates(today_str, 3)

        return {
            "dni": clean_dni,
            "full_name": full_name_val,
            "excel_found": bool(excel_result),
            "excel_sheets_scanned": excel_result.get("sheets_found", []) if excel_result else [],
            "fields": {
                # Identificación
                "dni": f_dni,
                "paternal_surname": f_paternal,
                "maternal_surname": f_maternal,
                "first_names": f_first_names,
                "full_name": f_full_name,
                # Personales
                "birth_date": f_birth_date,
                "sex": f_sex,
                "civil_status": f_civil_status,
                "address": f_address,
                "district": f_district,
                "province": f_province,
                "department": f_department,
                "celular": f_celular,
                "correo": f_correo,
                # Laborales
                "cargo": f_cargo,
                "area": f_area,
                "regimen": f_regimen,
                "tipo_contrato": f_tipo_contrato,
                "remuneracion": remun_raw,
                "remuneracion_letras": {
                    "field_key": "remuneracion_letras",
                    "value": remun_words,
                    "origin": "Calculado del monto numérico",
                    "origin_type": "CALCULATED",
                    "is_editable": True,
                },
                "afp": f_afp,
                "asignacion_familiar": f_asig_fam,
                "centro_costo": f_centro_costo,
            },
            "contract_dates": dates_calc,
        }
