import os
import shutil
import re
from copy import copy
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from backend.config import TEMPLATES_DIR, EXPORTS_DIR, get_peru_now

EXCEL_TEMPLATES_DIR = TEMPLATES_DIR / "excel"
EXCEL_TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

# Standard semantic mapping aliases from DNI fields to possible Excel column names
COLUMN_MAPPINGS = {
    "full_name": [
        "APELLIDOS_Y_NOMBRES", "APELLIDOS Y NOMBRES", "APELLIDOS Y NOMBRE", "APELLIDOS_NOMBRE",
        "NOMBRES_Y_APELLIDOS", "NOMBRES Y APELLIDOS", "NOMBRE_COMPLETO", "NOMBRE COMPLETO",
        "DATOS_PERSONALES", "TRABAJADOR", "EMPLEADO", "COLABORADOR"
    ],
    "doc_number": [
        "DNI", "NUM_DOC", "NRO_DOCUMENTO", "NUMERO_DOCUMENTO", "DOCUMENTO", "DOC_IDENTIDAD",
        "NUMERO DNI", "NRO DNI", "CODIGO", "COD_TRABAJADOR", "CODIGO_EMPLEADO", "NRO_DOC",
        "COD.PERSONAL", "COD PERSONAL", "IDCODIGOGENERAL", "COD.CONTROL", "CODIGO_CONTROL",
        "NRO.DOCUME", "NRO. DOCUMENTO", "NRODOCUMENTO"
    ],
    "paternal_surname": [
        "APELLIDO_PATERNO", "APELLIDO PATERNO", "APE_PATERNO", "PATERNO", "PRIMER_APELLIDO",
        "PRIMER APELLIDO", "1ER APELLIDO", "1ER_APELLIDO", "APEL. PATERNO", "APEL PATERNO",
        "A_PATERNO", "APEL.PATERNO"
    ],
    "maternal_surname": [
        "APELLIDO_MATERNO", "APELLIDO MATERNO", "APE_MATERNO", "MATERNO", "SEGUNDO_APELLIDO",
        "SEGUNDO APELLIDO", "2DO APELLIDO", "2DO_APELLIDO", "APEL. MATERNO", "APEL MATERNO",
        "A_MATERNO", "APEL.MATERNO"
    ],
    "first_names": [
        "NOMBRES", "PRENOMBRES", "NOMBRE", "PRENOMBRE", "NOMBRES_TRABAJADOR", "NOMBRES COMPLETOS"
    ],
    "birth_date": [
        "FECHA_NACIMIENTO", "FECHA DE NACIMIENTO", "FEC_NACIMIENTO", "FEC_NAC", "FECHA_NAC",
        "NACIMIENTO", "F_NACIMIENTO", "FEC NAC", "FEC.NACIMIENTO", "FEC NACIMIENTO"
    ],
    "sex": [
        "SEXO", "GENERO", "GÉNERO", "SEX"
    ],
    "civil_status": [
        "ESTADO_CIVIL", "ESTADO CIVIL", "EST_CIVIL", "EDO_CIVIL", "EST CIVIL", "CIVIL",
        "EST. CIVIL", "EST.CIVIL", "IDESTADOCIVIL"
    ],
    "address": [
        "DIRECCION", "DIRECCIÓN", "DOMICILIO", "DIR_DOMICILIO", "DIRECCION_ACTUAL", "DOMICILIO_ACTUAL",
        "DIRECCION REFERENCIA", "DIRECCIÓN REFERENCIA", "DIRECCION_REFERENCIA"
    ],
    "ubigeo": [
        "UBIGEO", "COD_UBIGEO", "CODIGO_UBIGEO", "UBIGEO_RENIEC", "UBIGEO_DOMICILIO",
        "COD.UBIGEO", "COD. UBIGEO", "IDUBIGEO"
    ],
    "department": [
        "DEPARTAMENTO", "DPTO", "REGION", "REGIÓN", "DEPARTAMENTO_DOMICILIO"
    ],
    "province": [
        "PROVINCIA", "PROV", "PROVINCIA_DOMICILIO"
    ],
    "district": [
        "DISTRITO", "DIST", "DISTRITO_DOMICILIO"
    ],
    "issue_date": [
        "FECHA_EMISION", "FECHA DE EMISION", "FECHA_EMISIÓN", "FECHA DE EMISIÓN", "FEC_EMISION",
        "FEC_EMI", "FECHA_EXPEDICION", "F_EMISION", "FEC EMISION", "FEC.EMISION", "FEC. EMISION"
    ],
    "expiry_date": [
        "FECHA_CADUCIDAD", "FECHA DE CADUCIDAD", "FECHA_VENCIMIENTO", "FECHA DE VENCIMIENTO",
        "FEC_CADUCIDAD", "FEC_VENCIMIENTO", "FEC_VENC", "FECHA_VENCE", "CADUCIDAD", "VENCIMIENTO",
        "FEC.VENCIMIENTO", "FEC. VENCIMIENTO"
    ],
    "nationality": [
        "NACIONALIDAD", "PAIS_ORIGEN", "PAÍS", "PAIS", "IDNACIONALIDAD"
    ],
    "blood_type": [
        "GRUPO_SANGUINEO", "GRUPO SANGUINEO", "GRUPO_SANGUÍNEO", "GRUPO SANGUÍNEO", "TIPO_SANGRE", "SANGRE"
    ],
    "phone": [
        "CELULAR", "TELEFONO", "TELÉFONO", "TEL", "CEL", "MOVIL", "MÓVIL", "NUMERO_CELULAR",
        "NRO_CELULAR", "TELEFONO_MOVIL", "TEL_MOVIL", "NUMERO CELULAR", "NRO CELULAR", "TELEFONO MOVIL"
    ],
    "email": [
        "CORREO", "EMAIL", "CORREO_ELECTRONICO", "CORREO ELECTRÓNICO", "CORREO_ELECTRÓNICO",
        "CORREO ELECTRONICO", "E-MAIL", "MAIL", "CORREO PERSONAL", "CORREO_PERSONAL"
    ],
    "pension_system": [
        "SISTEMA_PENSIONARIO", "SISTEMA PENSIONARIO", "SISTEMA_PENSIONES", "SISTEMA PENSIONES",
        "REGIMEN_PENSIONARIO", "REGIMEN PENSIONARIO", "AFP_ONP", "AFP / ONP", "AFP", "TIPO_SISTEMA_PENSIONARIO",
        "SIST. PENSIONARIO", "SIST PENSIONARIO", "IDREGIMENPENSIONARIO", "SISTEMA DE PENSIONES"
    ],
    "pension_commission": [
        "COMISION", "COMISIÓN", "TIPO_COMISION", "TIPO DE COMISION", "TIPO_COMISIÓN", "TIPO DE COMISIÓN",
        "COMISION_AFP", "COMISIÓN AFP", "COMISION AFP", "TIPO COMISION"
    ],
    "cuspp": [
        "CUSPP", "CODIGO_CUSPP", "CODIGO CUSPP", "NRO_CUSPP", "NUMERO_CUSPP", "CUSSP", "COD_CUSPP", "NRO CUSPP"
    ],
}


def normalize_header(header: str) -> str:
    """Normalizes header string for robust matching."""
    if not header:
        return ""
    h = header.strip().upper()
    h = h.replace("Á", "A").replace("É", "E").replace("Í", "I").replace("Ó", "O").replace("Ú", "U")
    h = re.sub(r"[_\-\./\\:]+", " ", h)
    h = re.sub(r"\s+", " ", h)
    return h.strip()


def match_field_to_header(field_key: str, header_raw: str) -> bool:
    """Checks if a given column header matches a DNI field."""
    norm_h = normalize_header(header_raw)
    aliases = COLUMN_MAPPINGS.get(field_key, [])
    for alias in aliases:
        norm_alias = normalize_header(alias)
        if norm_h == norm_alias or norm_h.startswith(norm_alias) or norm_alias in norm_h:
            return True
    return False


def is_yellow_color(color_obj) -> bool:
    """Detects whether an openpyxl color object represents a yellow/highlighted cell."""
    if not color_obj:
        return False
    rgb = None
    try:
        rgb = color_obj.rgb
    except Exception:
        pass
    if not rgb or not isinstance(rgb, str):
        return False
    rgb_clean = rgb.upper().replace('#', '').strip()
    if len(rgb_clean) == 8:
        # ARGB format
        a, r, g, b = rgb_clean[:2], rgb_clean[2:4], rgb_clean[4:6], rgb_clean[6:8]
    elif len(rgb_clean) == 6:
        r, g, b = rgb_clean[:2], rgb_clean[2:4], rgb_clean[4:6]
    else:
        return False
    try:
        r_int = int(r, 16)
        g_int = int(g, 16)
        b_int = int(b, 16)
        # Yellow has strong red and green, low blue
        # e.g. FFFF00 (255, 255, 0), FFF2CC (255, 242, 204), FFE599 (255, 229, 153), FFD966 (255, 217, 102)
        return r_int >= 180 and g_int >= 160 and b_int <= 175 and (r_int + g_int > b_int * 2.0)
    except Exception:
        return False


def is_cell_yellow(cell) -> bool:
    """Checks if a cell has a yellow background fill."""
    if not cell or not cell.fill:
        return False
    fill = cell.fill
    if fill.fill_type == 'solid' and fill.start_color:
        return is_yellow_color(fill.start_color)
    return False


def is_data_row(row_cells) -> bool:
    """Returns True if the row contains typical data cell values (dates, numbers, DNIs)."""
    for cell in row_cells:
        v = cell.value
        if v is None:
            continue
        if isinstance(v, (int, float, datetime)):
            return True
        v_str = str(v).strip()
        if not v_str:
            continue
        if v_str.isdigit():
            return True
        if re.match(r"^\d{4}[-/]\d{2}[-/]\d{2}", v_str) or re.match(r"^\d{1,2}[-/]\d{1,2}[-/]\d{4}", v_str):
            return True
    return False


def get_sheet_header_rows(ws) -> List[int]:
    """Detects rows belonging to column headers."""
    header_rows = []
    for r_idx in range(1, min(10, ws.max_row + 1)):
        row_cells = [ws.cell(row=r_idx, column=c_idx) for c_idx in range(1, ws.max_column + 1)]
        non_empty = [c for c in row_cells if c.value is not None and str(c.value).strip()]
        if not non_empty:
            if header_rows:
                break
            continue
        if is_data_row(row_cells):
            break
        header_rows.append(r_idx)
    return header_rows if header_rows else [1]


class ExcelTemplateService:
    """
    Manages Excel templates, sheet analysis, yellow variable cell detection,
    and safe batch population for scanned DNI workers.
    """

    def __init__(self, templates_dir: Path = EXCEL_TEMPLATES_DIR, exports_dir: Path = EXPORTS_DIR):
        self.templates_dir = templates_dir
        self.exports_dir = exports_dir
        self.ensure_initial_templates()

    def ensure_initial_templates(self):
        """Creates initial standard templates only on first-time setup if directory has no templates."""
        existing_xlsx = [p for p in self.templates_dir.glob("*.xlsx") if not p.name.startswith("~$")]
        if existing_xlsx:
            return

        t1 = self.templates_dir / "CARGA DATOS CONTRATOS - 20260909.xlsx"
        if not t1.exists():
            wb1 = openpyxl.Workbook()
            ws1 = wb1.active
            ws1.title = "DATOS CONTRATOS"
            headers1 = [
                "NRO", "TIPO_DOC", "DNI / NRO_DOCUMENTO", "APELLIDO PATERNO", "APELLIDO MATERNO",
                "NOMBRES", "FECHA NACIMIENTO", "SEXO", "ESTADO CIVIL", "DIRECCION",
                "DEPARTAMENTO", "PROVINCIA", "DISTRITO", "UBIGEO", "FECHA EMISION",
                "FECHA CADUCIDAD", "NACIONALIDAD"
            ]
            ws1.append(headers1)
            header_fill = PatternFill(start_color="FFFFFF00", end_color="FFFFFF00", fill_type="solid")
            header_font = Font(name="Calibri", size=11, bold=True, color="000000")
            for col_idx in range(1, len(headers1) + 1):
                cell = ws1.cell(row=1, column=col_idx)
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal="center", vertical="center")
                ws1.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = max(16, len(headers1[col_idx - 1]) + 4)
            wb1.save(t1)

        t2 = self.templates_dir / "CARGA MASIVA DE DATOS NISIRA - 20260909.xlsx"
        if not t2.exists():
            wb2 = openpyxl.Workbook()
            ws2 = wb2.active
            ws2.title = "NISIRA_CARGA"
            headers2 = [
                "ITEM", "CODIGO_EMPLEADO", "TIPO_DOCUMENTO", "NUM_DOC", "APE_PATERNO",
                "APE_MATERNO", "NOMBRES", "FEC_NACIMIENTO", "SEXO", "EST_CIVIL",
                "DIRECCION", "DPTO", "PROV", "DIST", "UBIGEO", "FEC_EMISION",
                "FEC_VENCIMIENTO", "GRUPO_SANGUINEO"
            ]
            ws2.append(headers2)
            header_fill2 = PatternFill(start_color="FFFFFF00", end_color="FFFFFF00", fill_type="solid")
            header_font2 = Font(name="Calibri", size=11, bold=True, color="000000")
            for col_idx in range(1, len(headers2) + 1):
                cell = ws2.cell(row=1, column=col_idx)
                cell.fill = header_fill2
                cell.font = header_font2
                cell.alignment = Alignment(horizontal="center", vertical="center")
                ws2.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = max(16, len(headers2[col_idx - 1]) + 4)
            wb2.save(t2)

    def list_templates(self) -> List[Dict[str, Any]]:
        """Lists all registered Excel templates and analyzes their structure."""
        templates_list = []

        for p in self.templates_dir.glob("*.xlsx"):
            if p.name.startswith("~$"):
                continue
            try:
                analysis = self.analyze_template(p.name)
                templates_list.append({
                    "filename": p.name,
                    "file_size_kb": round(p.stat().st_size / 1024.0, 1),
                    "sheets": analysis["sheets"],
                    "total_sheets": len(analysis["sheets"]),
                    "default_sheet": analysis["default_sheet"],
                })
            except Exception as e:
                templates_list.append({
                    "filename": p.name,
                    "file_size_kb": round(p.stat().st_size / 1024.0, 1),
                    "sheets": [],
                    "total_sheets": 0,
                    "error": str(e),
                })

        return templates_list

    def get_custom_mappings_file(self) -> Path:
        return self.templates_dir / "custom_mappings.json"

    def load_custom_mappings(self) -> Dict[str, Any]:
        cm_file = self.get_custom_mappings_file()
        if cm_file.exists():
            try:
                import json
                with open(cm_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save_custom_mappings_file(self, data: Dict[str, Any]):
        cm_file = self.get_custom_mappings_file()
        try:
            import json
            with open(cm_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving custom mappings: {e}")

    def save_template_mapping(self, filename: str, sheet_name: str, mappings: Dict[str, str]) -> Dict[str, Any]:
        """Saves user-customized field-to-column mappings for a specific template & sheet."""
        all_maps = self.load_custom_mappings()
        if filename not in all_maps:
            all_maps[filename] = {}
        all_maps[filename][sheet_name] = mappings
        self.save_custom_mappings_file(all_maps)
        return self.analyze_template(filename)

    def _find_template_file(self, filename: str) -> Optional[Path]:
        """Finds a template file supporting exact, normalized and stripped matches."""
        safe_name = Path(filename).name
        direct_path = self.templates_dir / safe_name
        if direct_path.exists():
            return direct_path

        import urllib.parse
        decoded_name = Path(urllib.parse.unquote(filename)).name
        decoded_path = self.templates_dir / decoded_name
        if decoded_path.exists():
            return decoded_path

        # Check glob matching
        for p in self.templates_dir.glob("*.xlsx"):
            if p.name == safe_name or p.name == decoded_name or p.name.strip() == safe_name.strip() or p.name.strip() == decoded_name.strip():
                return p
        return None

    def delete_template(self, filename: str) -> bool:
        """Deletes a template file and its custom mappings."""
        file_path = self._find_template_file(filename)
        if not file_path or not file_path.exists():
            raise FileNotFoundError(f"Plantilla '{filename}' no encontrada.")
        
        actual_name = file_path.name
        file_path.unlink()

        # Remove from custom mappings
        all_maps = self.load_custom_mappings()
        if actual_name in all_maps:
            del all_maps[actual_name]
            self.save_custom_mappings_file(all_maps)

        return True

    def rename_template(self, old_filename: str, new_filename: str) -> Dict[str, Any]:
        """Renames a template file and updates references."""
        old_path = self._find_template_file(old_filename)
        if not old_path or not old_path.exists():
            raise FileNotFoundError(f"Plantilla original '{old_filename}' no encontrada.")

        new_safe = Path(new_filename).name
        if not new_safe.lower().endswith(".xlsx"):
            new_safe += ".xlsx"

        new_path = self.templates_dir / new_safe
        if old_path != new_path and new_path.exists():
            raise FileExistsError(f"Ya existe una plantilla con el nombre '{new_safe}'.")

        old_actual = old_path.name
        old_path.rename(new_path)

        # Update custom mappings key
        all_maps = self.load_custom_mappings()
        if old_actual in all_maps:
            all_maps[new_safe] = all_maps.pop(old_actual)
            self.save_custom_mappings_file(all_maps)

        return self.analyze_template(new_safe)

    def get_template_path(self, filename: str) -> Path:
        """Returns safe path to template file."""
        path = self._find_template_file(filename)
        if not path or not path.exists():
            raise FileNotFoundError(f"Plantilla '{filename}' no encontrada.")
        return path

    def analyze_template(self, filename: str) -> Dict[str, Any]:
        """Inspects an Excel file to extract all sheets, column headers, and detects YELLOW variable cells."""
        file_path = self.get_template_path(filename)
        all_custom_maps = self.load_custom_mappings()
        tpl_custom_maps = all_custom_maps.get(file_path.name, {})

        wb = openpyxl.load_workbook(file_path, data_only=True)
        sheets_info = []

        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            
            # 1. Detect Header Rows
            header_row_indices = get_sheet_header_rows(ws)

            total_cols = ws.max_column
            headers = []
            columns_detail = []
            sheet_custom = tpl_custom_maps.get(sheet_name, {})
            mapped_fields = {}
            yellow_columns_count = 0

            for col_idx in range(1, total_cols + 1):
                h_parts = []
                col_is_yellow = False
                for r_idx in header_row_indices:
                    cell = ws.cell(row=r_idx, column=col_idx)
                    if cell.value is not None and str(cell.value).strip():
                        h_parts.append(str(cell.value).strip())
                    if is_cell_yellow(cell):
                        col_is_yellow = True

                # Check rows 1-3 if not found in header
                if not col_is_yellow:
                    for r_check in range(1, min(4, ws.max_row + 1)):
                        if is_cell_yellow(ws.cell(row=r_check, column=col_idx)):
                            col_is_yellow = True
                            break

                header_name = " / ".join(h_parts) if h_parts else f"Columna {col_idx}"
                headers.append(header_name)
                col_letter = openpyxl.utils.get_column_letter(col_idx)

                if col_is_yellow:
                    yellow_columns_count += 1

                # Check mapping
                col_key = str(col_idx)
                mapped_field_key = None
                is_custom = False

                if col_key in sheet_custom:
                    custom_field = sheet_custom[col_key]
                    if custom_field and custom_field != "none":
                        mapped_field_key = custom_field
                        is_custom = True
                elif header_name in sheet_custom:
                    custom_field = sheet_custom[header_name]
                    if custom_field and custom_field != "none":
                        mapped_field_key = custom_field
                        is_custom = True
                else:
                    # Auto semantic mapping for yellow columns (or any column matching DNI field)
                    for f_key in COLUMN_MAPPINGS.keys():
                        if match_field_to_header(f_key, header_name):
                            mapped_field_key = f_key
                            break

                if mapped_field_key:
                    mapped_fields[mapped_field_key] = {
                        "column_index": col_idx,
                        "column_letter": col_letter,
                        "header_name": header_name,
                        "is_custom": is_custom,
                        "is_yellow": col_is_yellow,
                    }

                columns_detail.append({
                    "column_index": col_idx,
                    "column_letter": col_letter,
                    "header_name": header_name,
                    "is_yellow": col_is_yellow,
                    "mapped_field": mapped_field_key,
                    "is_custom": is_custom,
                })

            sheets_info.append({
                "sheet_name": sheet_name,
                "header_rows": header_row_indices,
                "total_columns": total_cols,
                "yellow_columns_count": yellow_columns_count,
                "headers": headers,
                "columns_detail": columns_detail,
                "mapped_fields": mapped_fields,
                "custom_mappings": sheet_custom,
            })

        wb.close()
        default_sheet = sheets_info[0]["sheet_name"] if sheets_info else ""

        return {
            "filename": file_path.name,
            "sheets": sheets_info,
            "default_sheet": default_sheet,
        }

    def save_uploaded_template(self, file_bytes: bytes, original_filename: str) -> Dict[str, Any]:
        """Saves a newly uploaded template and analyzes it."""
        safe_name = Path(original_filename).name
        if not safe_name.lower().endswith(".xlsx"):
            safe_name += ".xlsx"

        dest_path = self.templates_dir / safe_name
        with open(dest_path, "wb") as f:
            f.write(file_bytes)

        return self.analyze_template(safe_name)

    def fill_template(
        self,
        template_name: str,
        data: Dict[str, Any],
        sheet_name: Optional[str] = None,
    ) -> Tuple[str, Path]:
        """
        Fills a single DNI record into the template using batch engine.
        Returns: (output_filename, output_filepath)
        """
        out_fn, out_p, _, _ = self.fill_template_batch(template_name, [data], sheet_name)
        return out_fn, out_p

    def fill_template_batch(
        self,
        template_name: str,
        records: List[Dict[str, Any]],
        sheet_name: Optional[str] = None,
    ) -> Tuple[str, Path, int, List[str]]:
        """
        Fills multiple scanned DNI records into the template adhering to the strict YELLOW CELL rule.
        - Only columns marked in YELLOW in the template (or in user custom mapping) are modified with DNI data.
        - Yellow columns with no available DNI information are left strictly BLANK.
        - Non-yellow columns retain their original formulas, fixed values, and styles.
        - The original template file is NEVER modified.
        - Generates and returns (output_filename, output_filepath, total_workers, yellow_col_names).
        """
        src_path = self.get_template_path(template_name)
        wb = openpyxl.load_workbook(src_path)
        target_sheet_name = sheet_name if sheet_name and sheet_name in wb.sheetnames else wb.sheetnames[0]
        ws = wb[target_sheet_name]

        # 1. Detect Header Rows and Structure
        header_row_indices = get_sheet_header_rows(ws)
        last_header_row = header_row_indices[-1]
        start_data_row = last_header_row + 1

        # 2. Extract Header Names and Yellow Status for each column
        total_cols = ws.max_column
        col_headers = {}
        yellow_cols = set()

        for c_idx in range(1, total_cols + 1):
            h_parts = []
            c_is_yellow = False
            for r_idx in header_row_indices:
                cell = ws.cell(row=r_idx, column=c_idx)
                if cell.value is not None and str(cell.value).strip():
                    h_parts.append(str(cell.value).strip())
                if is_cell_yellow(cell):
                    c_is_yellow = True

            if not c_is_yellow:
                for r_check in range(1, min(4, ws.max_row + 1)):
                    if is_cell_yellow(ws.cell(row=r_check, column=c_idx)):
                        c_is_yellow = True
                        break

            col_headers[c_idx] = " ".join(h_parts) if h_parts else f"Columna {c_idx}"
            if c_is_yellow:
                yellow_cols.add(c_idx)

        # 3. Load Custom Mappings
        all_custom_maps = self.load_custom_mappings()
        sheet_custom = all_custom_maps.get(template_name, {}).get(target_sheet_name, {})

        # Map each column to corresponding DNI field
        col_to_field_map = {}
        for c_idx in range(1, total_cols + 1):
            col_key = str(c_idx)
            header_name = col_headers.get(c_idx, "")

            # Check user custom mapping first
            custom_field = sheet_custom.get(col_key) or sheet_custom.get(header_name)
            if custom_field:
                if custom_field != "none":
                    col_to_field_map[c_idx] = custom_field
                    yellow_cols.add(c_idx)
                continue

            # Auto-match DNI field (prioritizing yellow columns)
            if c_idx in yellow_cols:
                for field_key in COLUMN_MAPPINGS.keys():
                    if match_field_to_header(field_key, header_name):
                        col_to_field_map[c_idx] = field_key
                        break

        # 4. Clone Template Baseline Row Properties
        baseline_row = start_data_row if ws.max_row >= start_data_row else last_header_row
        baseline_styles = {}
        baseline_values = {}
        for c_idx in range(1, total_cols + 1):
            b_cell = ws.cell(row=baseline_row, column=c_idx)
            baseline_styles[c_idx] = {
                "font": copy(b_cell.font) if b_cell.font else None,
                "border": copy(b_cell.border) if b_cell.border else None,
                "alignment": copy(b_cell.alignment) if b_cell.alignment else None,
                "number_format": b_cell.number_format,
            }
            if c_idx not in yellow_cols:
                baseline_values[c_idx] = b_cell.value

        # 5. Populate rows for each selected worker
        num_workers = len(records)
        for worker_idx, raw_rec in enumerate(records):
            current_row = start_data_row + worker_idx

            # Normalize worker record
            pat = (raw_rec.get("paternal_surname") or "").strip()
            mat = (raw_rec.get("maternal_surname") or "").strip()
            noms = (raw_rec.get("first_names") or "").strip()
            full_name = (raw_rec.get("full_name") or f"{pat} {mat} {noms}").strip()

            ubigeo_raw = (raw_rec.get("ubigeo") or "").strip()
            dept = (raw_rec.get("department") or "").strip()
            prov = (raw_rec.get("province") or "").strip()
            dist = (raw_rec.get("district") or "").strip()
            if "/" in ubigeo_raw and (not dept or not prov or not dist):
                parts = [p.strip() for p in ubigeo_raw.split("/")]
                if len(parts) >= 3:
                    dept = dept or parts[0]
                    prov = prov or parts[1]
                    dist_part = parts[2]
                    dist = dist or (dist_part.split("(")[0].strip() if "(" in dist_part else dist_part.strip())
                elif len(parts) == 2:
                    dept = dept or parts[0]
                    dist_part = parts[1]
                    dist = dist or (dist_part.split("(")[0].strip() if "(" in dist_part else dist_part.strip())

            raw_doc_type = raw_rec.get("doc_type", "DNI") or "DNI"
            is_dni_type = "DNI" in str(raw_doc_type).upper()

            worker_dni_data = {
                "doc_number": (raw_rec.get("doc_number") or "").strip(),
                "paternal_surname": pat,
                "maternal_surname": mat,
                "first_names": noms,
                "full_name": full_name,
                "birth_date": (raw_rec.get("birth_date") or "").strip(),
                "sex": (raw_rec.get("sex") or "").strip(),
                "civil_status": (raw_rec.get("civil_status") or "").strip(),
                "address": (raw_rec.get("address") or "").strip(),
                "department": dept,
                "province": prov,
                "district": dist,
                "ubigeo": ubigeo_raw,
                "issue_date": (raw_rec.get("issue_date") or "").strip(),
                "expiry_date": (raw_rec.get("expiry_date") or "").strip(),
                "nationality": (raw_rec.get("nationality") or "PERUANA").strip(),
                "blood_type": (raw_rec.get("blood_type") or "").strip(),
                "phone": (raw_rec.get("phone") or "999999999").strip(),
                "email": (raw_rec.get("email") or "sincorreo@gmail.com").strip(),
                "pension_system": (raw_rec.get("pension_system") or "").strip(),
                "pension_commission": (raw_rec.get("pension_commission") or "").strip(),
                "cuspp": (raw_rec.get("cuspp") or "").strip(),
            }

            for c_idx in range(1, total_cols + 1):
                cell = ws.cell(row=current_row, column=c_idx)

                # Apply baseline styling
                st = baseline_styles.get(c_idx, {})
                if st.get("font"): cell.font = st["font"]
                if st.get("border"): cell.border = st["border"]
                if st.get("alignment"): cell.alignment = st["alignment"]
                if st.get("number_format"): cell.number_format = st["number_format"]

                norm_h = normalize_header(col_headers.get(c_idx, ""))

                # Auto Item / correlativo column
                if norm_h in ["ITEM", "CORRELATIVO", "NRO", "N", "NO", "NUM", "ITEM CORRELATIVO"]:
                    cell.value = worker_idx + 1
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                    continue

                if norm_h in ["TIPO DOC", "TIPO DOCUMENTO", "DOC", "TIP DOCUMENTO", "IDDOCIDENTIDAD"]:
                    if "NISIRA" in template_name.upper():
                        cell.value = "01" if is_dni_type else "04"
                    else:
                        cell.value = "DNI" if is_dni_type else "CE"
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                    continue

                if c_idx in yellow_cols:
                    field_key = col_to_field_map.get(c_idx)
                    if field_key and field_key in worker_dni_data and worker_dni_data[field_key]:
                        val = worker_dni_data[field_key]
                        cell.value = str(val)
                    else:
                        # REGLA PRINCIPAL: Si un campo amarillo no tiene información disponible: DEJARLO EN BLANCO.
                        cell.value = ""
                else:
                    # Non-yellow column: keep baseline value / formula / fixed text from template
                    if c_idx in baseline_values and baseline_values[c_idx] is not None:
                        cell.value = baseline_values[c_idx]

        # 6. Clean up any trailing old sample rows from the template
        if ws.max_row > start_data_row + num_workers - 1:
            for r_del in range(start_data_row + num_workers, ws.max_row + 1):
                for c_del in range(1, total_cols + 1):
                    ws.cell(row=r_del, column=c_del).value = None

        # 7. Save output copy to exports/
        timestamp = get_peru_now().strftime("%Y%m%d_%H%M%S")
        clean_base = Path(template_name).stem
        out_filename = f"{clean_base}_LLENADO_{timestamp}.xlsx"
        out_path = self.exports_dir / out_filename
        wb.save(out_path)
        wb.close()

        yellow_headers_list = [col_headers[c] for c in yellow_cols if c in col_headers]
        return out_filename, out_path, num_workers, yellow_headers_list

    def fill_template_batch_from_file(
        self,
        source_file_path: Path,
        template_display_name: str,
        records: List[Dict[str, Any]],
        sheet_name: Optional[str] = None,
    ) -> Tuple[str, Path, int, List[str]]:
        """
        Llenado por lote a partir de una ruta de archivo física arbitraria (e.g. descargada de Supabase).
        """
        src_path = Path(source_file_path)
        if not src_path.exists():
            raise FileNotFoundError(f"No se encontró el archivo de plantilla: {src_path}")

        wb = openpyxl.load_workbook(src_path)
        target_sheet_name = sheet_name if sheet_name and sheet_name in wb.sheetnames else wb.sheetnames[0]
        ws = wb[target_sheet_name]

        header_row_indices = get_sheet_header_rows(ws)
        last_header_row = header_row_indices[-1]
        start_data_row = last_header_row + 1

        total_cols = ws.max_column
        col_headers = {}
        yellow_cols = set()

        for c_idx in range(1, total_cols + 1):
            h_parts = []
            c_is_yellow = False
            for r_idx in header_row_indices:
                cell = ws.cell(row=r_idx, column=c_idx)
                if cell.value is not None and str(cell.value).strip():
                    h_parts.append(str(cell.value).strip())
                if is_cell_yellow(cell):
                    c_is_yellow = True

            if not c_is_yellow:
                for r_check in range(1, min(4, ws.max_row + 1)):
                    if is_cell_yellow(ws.cell(row=r_check, column=c_idx)):
                        c_is_yellow = True
                        break

            col_headers[c_idx] = " ".join(h_parts) if h_parts else f"Columna {c_idx}"
            if c_is_yellow:
                yellow_cols.add(c_idx)

        # Mapeo semántico de campos DNI
        col_to_field_map = {}
        for c_idx in range(1, total_cols + 1):
            header_name = col_headers.get(c_idx, "")
            if c_idx in yellow_cols:
                for field_key in COLUMN_MAPPINGS.keys():
                    if match_field_to_header(field_key, header_name):
                        col_to_field_map[c_idx] = field_key
                        break

        # Baseline styles
        baseline_row = start_data_row if ws.max_row >= start_data_row else last_header_row
        baseline_styles = {}
        baseline_values = {}
        for c_idx in range(1, total_cols + 1):
            b_cell = ws.cell(row=baseline_row, column=c_idx)
            baseline_styles[c_idx] = {
                "font": copy(b_cell.font) if b_cell.font else None,
                "border": copy(b_cell.border) if b_cell.border else None,
                "alignment": copy(b_cell.alignment) if b_cell.alignment else None,
                "number_format": b_cell.number_format,
            }
            if c_idx not in yellow_cols:
                baseline_values[c_idx] = b_cell.value

        num_workers = len(records)
        for worker_idx, raw_rec in enumerate(records):
            current_row = start_data_row + worker_idx
            pat = (raw_rec.get("paternal_surname") or "").strip()
            mat = (raw_rec.get("maternal_surname") or "").strip()
            noms = (raw_rec.get("first_names") or "").strip()
            full_name = (raw_rec.get("full_name") or f"{pat} {mat} {noms}").strip()

            ubigeo_raw = (raw_rec.get("ubigeo") or "").strip()
            dept = (raw_rec.get("department") or "").strip()
            prov = (raw_rec.get("province") or "").strip()
            dist = (raw_rec.get("district") or "").strip()
            if "/" in ubigeo_raw and (not dept or not prov or not dist):
                parts = [p.strip() for p in ubigeo_raw.split("/")]
                if len(parts) >= 3:
                    dept = dept or parts[0]
                    prov = prov or parts[1]
                    dist_part = parts[2]
                    dist = dist or (dist_part.split("(")[0].strip() if "(" in dist_part else dist_part.strip())

            raw_doc_type = raw_rec.get("doc_type", "DNI") or "DNI"
            is_dni_type = "DNI" in str(raw_doc_type).upper()

            worker_dni_data = {
                "doc_number": (raw_rec.get("doc_number") or "").strip(),
                "paternal_surname": pat,
                "maternal_surname": mat,
                "first_names": noms,
                "full_name": full_name,
                "birth_date": (raw_rec.get("birth_date") or "").strip(),
                "sex": (raw_rec.get("sex") or "").strip(),
                "civil_status": (raw_rec.get("civil_status") or "").strip(),
                "address": (raw_rec.get("address") or "").strip(),
                "department": dept,
                "province": prov,
                "district": dist,
                "ubigeo": ubigeo_raw,
                "issue_date": (raw_rec.get("issue_date") or "").strip(),
                "expiry_date": (raw_rec.get("expiry_date") or "").strip(),
                "nationality": (raw_rec.get("nationality") or "PERUANA").strip(),
                "blood_type": (raw_rec.get("blood_type") or "").strip(),
                "phone": (raw_rec.get("phone") or "999999999").strip(),
                "email": (raw_rec.get("email") or "sincorreo@gmail.com").strip(),
                "pension_system": (raw_rec.get("pension_system") or "").strip(),
                "pension_commission": (raw_rec.get("pension_commission") or "").strip(),
                "cuspp": (raw_rec.get("cuspp") or "").strip(),
            }

            for c_idx in range(1, total_cols + 1):
                cell = ws.cell(row=current_row, column=c_idx)
                st = baseline_styles.get(c_idx, {})
                if st.get("font"): cell.font = st["font"]
                if st.get("border"): cell.border = st["border"]
                if st.get("alignment"): cell.alignment = st["alignment"]
                if st.get("number_format"): cell.number_format = st["number_format"]

                norm_h = normalize_header(col_headers.get(c_idx, ""))
                if norm_h in ["ITEM", "CORRELATIVO", "NRO", "N", "NO", "NUM", "ITEM CORRELATIVO"]:
                    cell.value = worker_idx + 1
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                    continue

                if norm_h in ["TIPO DOC", "TIPO DOCUMENTO", "DOC", "TIP DOCUMENTO", "IDDOCIDENTIDAD"]:
                    if "NISIRA" in template_display_name.upper():
                        cell.value = "01" if is_dni_type else "04"
                    else:
                        cell.value = "DNI" if is_dni_type else "CE"
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                    continue

                if c_idx in yellow_cols:
                    field_key = col_to_field_map.get(c_idx)
                    if field_key and field_key in worker_dni_data and worker_dni_data[field_key]:
                        cell.value = str(worker_dni_data[field_key])
                    else:
                        cell.value = ""
                else:
                    if c_idx in baseline_values and baseline_values[c_idx] is not None:
                        cell.value = baseline_values[c_idx]

        if ws.max_row > start_data_row + num_workers - 1:
            for r_del in range(start_data_row + num_workers, ws.max_row + 1):
                for c_del in range(1, total_cols + 1):
                    ws.cell(row=r_del, column=c_del).value = None

        timestamp = get_peru_now().strftime("%Y%m%d_%H%M%S")
        clean_base = Path(template_display_name).stem
        out_filename = f"{clean_base}_LLENADO_{timestamp}.xlsx"
        out_path = self.exports_dir / out_filename
        wb.save(out_path)
        wb.close()

        yellow_headers_list = [col_headers[c] for c in yellow_cols if c in col_headers]
        return out_filename, out_path, num_workers, yellow_headers_list


