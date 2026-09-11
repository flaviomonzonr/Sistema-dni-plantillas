import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import openpyxl
from openpyxl.utils import get_column_letter


class ExcelAnalyzer:
    """
    Motor de análisis exhaustivo de archivos Excel para Recursos Humanos y Planillas.
    Capaz de inspeccionar:
    - Todas las hojas (visibles, ocultas y muy ocultas)
    - Encabezados, filas y columnas (visibles y ocultas)
    - Comentarios y notas de celdas (cell.comment)
    - Fórmulas y valores calculados
    - Tablas auxiliares y referencias
    - Cero alteración del archivo original (Modo solo lectura).
    """

    def __init__(self, excel_path: Optional[Path] = None):
        self.excel_path = excel_path

    @staticmethod
    def _normalize_str(text: Any) -> str:
        if text is None:
            return ""
        return str(text).strip()

    @staticmethod
    def _clean_dni(text: Any) -> str:
        s = str(text or "").strip()
        # Remove decimals if stored as float e.g. 42694271.0
        if s.endswith(".0"):
            s = s[:-2]
        # Keep only digits
        return re.sub(r"\D", "", s)

    def find_worker_by_dni(self, dni_target: str, excel_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
        """
        Busca integralmente un trabajador por su DNI (o número de documento)
        en todas las hojas del Excel, analizando celdas visibles, ocultas y comentarios.
        """
        target_path = excel_path or self.excel_path
        if not target_path or not Path(target_path).exists():
            return None

        clean_target = self._clean_dni(dni_target)
        if not clean_target:
            return None

        try:
            wb = openpyxl.load_workbook(target_path, data_only=True, keep_vba=True)
        except Exception as e:
            print(f"[ExcelAnalyzer] Error al abrir {target_path}: {e}")
            return None

        found_fields: Dict[str, Dict[str, Any]] = {}
        all_matches_info = []

        for sheetname in wb.sheetnames:
            ws = wb[sheetname]
            is_sheet_hidden = ws.sheet_state in ("hidden", "veryHidden")

            # Mapear encabezados de la fila 1 a 3 para detectar columnas
            header_map = {}
            header_row_idx = 1
            for r in range(1, min(5, ws.max_row + 1)):
                row_vals = [ws.cell(row=r, column=c).value for c in range(1, ws.max_column + 1)]
                has_headers = any(
                    isinstance(v, str) and any(k in v.lower() for k in ["dni", "doc", "nombre", "apellido", "cargo", "remun", "afp"])
                    for v in row_vals if v
                )
                if has_headers:
                    header_row_idx = r
                    for col_idx in range(1, ws.max_column + 1):
                        val = ws.cell(row=r, column=col_idx).value
                        if val:
                            header_map[col_idx] = str(val).strip()
                    break

            # Escanear filas en busca del DNI
            for row_idx in range(header_row_idx + 1, ws.max_row + 1):
                is_row_hidden = ws.row_dimensions[row_idx].hidden or False
                
                # Revisar cada celda de la fila
                row_has_target = False
                dni_col_idx = None

                for col_idx in range(1, ws.max_column + 1):
                    cell = ws.cell(row=row_idx, column=col_idx)
                    val_str = self._clean_dni(cell.value)
                    
                    if val_str == clean_target:
                        row_has_target = True
                        dni_col_idx = col_idx
                        break
                    
                    # También revisar si el DNI está dentro del comentario de la celda
                    if cell.comment and cell.comment.text:
                        comment_dni = self._clean_dni(cell.comment.text)
                        if clean_target in comment_dni:
                            row_has_target = True
                            dni_col_idx = col_idx
                            break

                if row_has_target:
                    # Extraer toda la fila con su metadata y comentarios
                    sheet_data = self._extract_row_data(ws, row_idx, header_map, sheetname, is_sheet_hidden, is_row_hidden)
                    all_matches_info.append({
                        "sheet": sheetname,
                        "row": row_idx,
                        "data": sheet_data
                    })

                    # Fusionar en found_fields dando prioridad a celdas con más contenido
                    for k, v in sheet_data.items():
                        if k not in found_fields or (not found_fields[k]["value"] and v["value"]):
                            found_fields[k] = v

        if not found_fields:
            return None

        return {
            "dni": clean_target,
            "fields": found_fields,
            "matches_count": len(all_matches_info),
            "sheets_found": [m["sheet"] for m in all_matches_info],
        }

    def _extract_row_data(
        self,
        ws: openpyxl.worksheet.worksheet.Worksheet,
        row_idx: int,
        header_map: Dict[int, str],
        sheetname: str,
        is_sheet_hidden: bool,
        is_row_hidden: bool,
    ) -> Dict[str, Dict[str, Any]]:
        """Extrae los valores de una fila reconociendo encabezados, comentarios y columnas ocultas."""
        fields = {}

        for col_idx in range(1, ws.max_column + 1):
            cell = ws.cell(row=row_idx, column=col_idx)
            header_name = header_map.get(col_idx, f"Columna_{get_column_letter(col_idx)}")
            norm_header = header_name.lower()
            
            is_col_hidden = ws.column_dimensions[get_column_letter(col_idx)].hidden or False
            val = cell.value
            val_str = self._normalize_str(val)

            # Extraer comentario o nota
            comment_text = None
            if cell.comment and cell.comment.text:
                comment_text = cell.comment.text.strip()

            origin_type = "EXCEL_VISIBLE"
            origin_desc = f"Excel: Hoja '{sheetname}' [Col {get_column_letter(col_idx)}, Fila {row_idx}] - Encabezado: '{header_name}'"

            if is_sheet_hidden:
                origin_type = "EXCEL_HIDDEN_SHEET"
                origin_desc += " (Hoja Oculta)"
            elif is_row_hidden:
                origin_type = "EXCEL_HIDDEN_ROW"
                origin_desc += " (Fila Oculta)"
            elif is_col_hidden:
                origin_type = "EXCEL_HIDDEN_COL"
                origin_desc += " (Columna Oculta)"

            if comment_text:
                origin_desc += f" | Nota: '{comment_text}'"

            # Clasificar el campo según el encabezado
            field_key = self._map_header_to_key(norm_header)
            
            # Si el valor está vacío pero hay nota, el valor puede estar en la nota
            effective_value = val_str
            if not effective_value and comment_text:
                effective_value = comment_text
                origin_type = "EXCEL_COMMENT"

            # También si hay notas que indiquen AFP o asignaciones
            if comment_text and ("afp" in comment_text.lower() or "onp" in comment_text.lower() or "habitat" in comment_text.lower() or "prima" in comment_text.lower() or "integra" in comment_text.lower() or "profuturo" in comment_text.lower()):
                fields["afp_nota"] = {
                    "field_name": "afp",
                    "value": comment_text,
                    "origin": f"Excel: Nota/Comentario en {get_column_letter(col_idx)}{row_idx}",
                    "origin_type": "EXCEL_COMMENT",
                    "is_hidden": False,
                    "is_editable": True,
                }

            fields[field_key] = {
                "field_name": field_key,
                "header_original": header_name,
                "value": effective_value,
                "raw_value": val,
                "origin": origin_desc,
                "origin_type": origin_type,
                "is_hidden": is_sheet_hidden or is_row_hidden or is_col_hidden,
                "comment": comment_text,
                "is_editable": True,
            }

        return fields

    def _map_header_to_key(self, norm_header: str) -> str:
        """Mapea el nombre del encabezado a una clave estandarizada de trabajador."""
        if any(w in norm_header for w in ["dni", "documento", "nro_doc", "num_doc", "cedula"]):
            return "dni"
        if "paterno" in norm_header or "ape_pat" in norm_header:
            return "paternal_surname"
        if "materno" in norm_header or "ape_mat" in norm_header:
            return "maternal_surname"
        if "apellido" in norm_header:
            return "apellidos"
        if "nombre" in norm_header:
            return "first_names"
        if "cargo" in norm_header or "puesto" in norm_header or "ocupacion" in norm_header:
            return "cargo"
        if "area" in norm_header or "departamento" in norm_header or "seccion" in norm_header:
            return "area"
        if "regimen" in norm_header:
            return "regimen"
        if "remun" in norm_header or "sueldo" in norm_header or "salario" in norm_header or "basico" in norm_header:
            return "remuneracion"
        if "afp" in norm_header or "pension" in norm_header or "spp" in norm_header or "onp" in norm_header:
            return "afp"
        if "asignacion" in norm_header or "asig_fam" in norm_header:
            return "asignacion_familiar"
        if "centro_costo" in norm_header or "cc" in norm_header:
            return "centro_costo"
        if "nacimiento" in norm_header or "fec_nac" in norm_header:
            return "birth_date"
        if "sexo" in norm_header or "genero" in norm_header:
            return "sex"
        if "civil" in norm_header or "est_civ" in norm_header:
            return "civil_status"
        if "direccion" in norm_header or "domicilio" in norm_header:
            return "address"
        if "distrito" in norm_header:
            return "district"
        if "provincia" in norm_header:
            return "province"
        if "departamento" in norm_header and "area" not in norm_header:
            return "department"
        if "celular" in norm_header or "movil" in norm_header or "telefono" in norm_header or "telf" in norm_header:
            return "celular"
        if "correo" in norm_header or "email" in norm_header or "mail" in norm_header:
            return "correo"
        if "tipo_contrato" in norm_header or "modalidad" in norm_header:
            return "tipo_contrato"
        if "ingreso" in norm_header or "fec_ing" in norm_header or "inicio" in norm_header:
            return "fecha_ingreso"

        # Slugify fallback
        return re.sub(r"\W+", "_", norm_header).strip("_")

    def inspect_excel_file(self, excel_path: Optional[Path] = None) -> Dict[str, Any]:
        """
        Genera un informe de diagnóstico detallado de la estructura del Excel:
        Hojas, estados de visibilidad, comentarios detectados, filas/columnas ocultas.
        """
        target_path = excel_path or self.excel_path
        if not target_path or not Path(target_path).exists():
            return {"status": "error", "message": f"Archivo no encontrado: {target_path}"}

        try:
            wb = openpyxl.load_workbook(target_path, data_only=True, keep_vba=True)
        except Exception as e:
            return {"status": "error", "message": f"Error abriendo Excel: {str(e)}"}

        sheets_summary = []
        total_comments = 0
        total_hidden_rows = 0
        total_hidden_cols = 0
        comments_list = []

        for name in wb.sheetnames:
            ws = wb[name]
            is_hidden = ws.sheet_state in ("hidden", "veryHidden")
            
            # Contar filas y columnas ocultas
            hidden_rows_in_sheet = sum(1 for r_idx in range(1, ws.max_row + 1) if ws.row_dimensions[r_idx].hidden)
            hidden_cols_in_sheet = sum(1 for c_idx in range(1, ws.max_column + 1) if ws.column_dimensions[get_column_letter(c_idx)].hidden)
            
            total_hidden_rows += hidden_rows_in_sheet
            total_hidden_cols += hidden_cols_in_sheet

            # Contar comentarios y registrar muestras
            sheet_comments = []
            for row in ws.iter_rows():
                for cell in row:
                    if cell.comment:
                        total_comments += 1
                        sheet_comments.append({
                            "coordinate": cell.coordinate,
                            "text": cell.comment.text,
                            "author": cell.comment.author,
                            "cell_value": str(cell.value or "")[:50],
                        })

            comments_list.extend([{"sheet": name, **c} for c in sheet_comments])

            # Detectar encabezados de muestra
            sample_headers = [str(ws.cell(row=1, column=c).value or "") for c in range(1, min(15, ws.max_column + 1))]

            sheets_summary.append({
                "sheet_name": name,
                "is_hidden": is_hidden,
                "sheet_state": ws.sheet_state,
                "max_rows": ws.max_row,
                "max_cols": ws.max_column,
                "hidden_rows": hidden_rows_in_sheet,
                "hidden_cols": hidden_cols_in_sheet,
                "comments_count": len(sheet_comments),
                "sample_headers": [h for h in sample_headers if h],
            })

        return {
            "status": "success",
            "file_path": str(target_path),
            "file_name": Path(target_path).name,
            "total_sheets": len(wb.sheetnames),
            "total_comments": total_comments,
            "total_hidden_rows": total_hidden_rows,
            "total_hidden_cols": total_hidden_cols,
            "sheets": sheets_summary,
            "comments_sample": comments_list[:20],
        }

    def list_all_workers(self, excel_path: Optional[Path] = None) -> List[Dict[str, Any]]:
        """
        Retorna la lista consolidada de todos los trabajadores encontrados en el Excel
        para su uso en el módulo de Generación Masiva.
        """
        target_path = excel_path or self.excel_path
        if not target_path or not Path(target_path).exists():
            return []

        try:
            wb = openpyxl.load_workbook(target_path, data_only=True, keep_vba=True)
        except Exception:
            return []

        workers_map: Dict[str, Dict[str, Any]] = {}

        for sheetname in wb.sheetnames:
            ws = wb[sheetname]
            is_sheet_hidden = ws.sheet_state in ("hidden", "veryHidden")

            header_map = {}
            header_row_idx = 1
            for r in range(1, min(5, ws.max_row + 1)):
                row_vals = [ws.cell(row=r, column=c).value for c in range(1, ws.max_column + 1)]
                has_dni = any(isinstance(v, str) and ("dni" in v.lower() or "documento" in v.lower() or "doc" in v.lower()) for v in row_vals if v)
                if has_dni:
                    header_row_idx = r
                    for col_idx in range(1, ws.max_column + 1):
                        val = ws.cell(row=r, column=col_idx).value
                        if val:
                            header_map[col_idx] = str(val).strip()
                    break

            if not header_map:
                continue

            for row_idx in range(header_row_idx + 1, ws.max_row + 1):
                is_row_hidden = ws.row_dimensions[row_idx].hidden or False
                row_data = self._extract_row_data(ws, row_idx, header_map, sheetname, is_sheet_hidden, is_row_hidden)
                
                dni_val = self._clean_dni(row_data.get("dni", {}).get("value", ""))
                if dni_val and len(dni_val) >= 7:
                    # Consolidar nombre completo
                    nombres = row_data.get("first_names", {}).get("value", "")
                    ap_pat = row_data.get("paternal_surname", {}).get("value", "")
                    ap_mat = row_data.get("maternal_surname", {}).get("value", "")
                    apellidos = row_data.get("apellidos", {}).get("value", "")
                    
                    if not apellidos:
                        apellidos = f"{ap_pat} {ap_mat}".strip()
                    
                    full_name = f"{apellidos} {nombres}".strip() if apellidos or nombres else f"Trabajador {dni_val}"
                    cargo = row_data.get("cargo", {}).get("value", "OPERARIO")
                    area = row_data.get("area", {}).get("value", "OPERACIONES")
                    remuneracion = row_data.get("remuneracion", {}).get("value", "")

                    if dni_val not in workers_map:
                        workers_map[dni_val] = {
                            "dni": dni_val,
                            "full_name": full_name,
                            "paternal_surname": ap_pat,
                            "maternal_surname": ap_mat,
                            "first_names": nombres,
                            "cargo": cargo,
                            "area": area,
                            "remuneracion": remuneracion,
                            "sheet_origin": sheetname,
                            "row_index": row_idx,
                            "raw_fields": row_data,
                        }

        return list(workers_map.values())
