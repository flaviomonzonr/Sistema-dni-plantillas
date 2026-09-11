import os
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from backend.config import MASTER_EXCEL_PATH, get_peru_now

# Column definitions
EXCEL_COLUMNS = [
    ("Fecha de escaneo", 20),
    ("Tipo de documento", 22),
    ("Apellido Paterno", 20),
    ("Apellido Materno", 20),
    ("Nombres", 26),
    ("Número de documento", 22),
    ("Nacionalidad", 18),
    ("Fecha de Nacimiento", 20),
    ("Sexo", 10),
    ("Celular", 16),
    ("Correo Electrónico", 28),
    ("Dirección", 36),
    ("Sistema Pensionario", 22),
    ("Comisión", 16),
    ("CUSPP", 18),
    ("Fecha de Emisión", 18),
    ("Fecha de Vencimiento", 20),
    ("Observaciones", 30),
]


def create_styled_workbook() -> openpyxl.Workbook:
    """Creates a new workbook with the standard 'Registros' sheet and styled headers."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Registros"

    # Header styling
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")  # Navy Blue
    header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)

    thin_border = Border(
        left=Side(style="thin", color="CBD5E1"),
        right=Side(style="thin", color="CBD5E1"),
        top=Side(style="thin", color="CBD5E1"),
        bottom=Side(style="thin", color="CBD5E1")
    )

    ws.row_dimensions[1].height = 28

    for col_idx, (col_name, col_width) in enumerate(EXCEL_COLUMNS, start=1):
        cell = ws.cell(row=1, column=col_idx, value=col_name)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        cell.border = thin_border
        
        col_letter = get_column_letter(col_idx)
        ws.column_dimensions[col_letter].width = col_width

    # Freeze top row
    ws.freeze_panes = "A2"
    return wb


def append_record_to_excel(record: Dict[str, Any], excel_path: Path = MASTER_EXCEL_PATH):
    """
    Appends a new record to the master Excel file without overwriting existing data.
    """
    excel_path.parent.mkdir(parents=True, exist_ok=True)

    if not excel_path.exists():
        wb = create_styled_workbook()
    else:
        try:
            wb = openpyxl.load_workbook(excel_path)
            if "Registros" not in wb.sheetnames:
                ws = wb.create_sheet("Registros")
            else:
                ws = wb["Registros"]
        except Exception:
            wb = create_styled_workbook()

    ws = wb["Registros"]
    next_row = ws.max_row + 1

    # Extract values in defined column order
    scan_date_str = record.get("scan_date")
    if isinstance(scan_date_str, datetime):
        scan_date_str = scan_date_str.strftime("%d/%m/%Y %H:%M:%S")
    elif not scan_date_str:
        scan_date_str = get_peru_now().strftime("%d/%m/%Y %H:%M:%S")

    row_data = [
        scan_date_str,
        record.get("doc_type", ""),
        record.get("paternal_surname", ""),
        record.get("maternal_surname", ""),
        record.get("first_names", ""),
        str(record.get("doc_number", "")),
        record.get("nationality", "PERUANA"),
        record.get("birth_date", ""),
        record.get("sex", ""),
        record.get("phone", "999999999") or "999999999",
        record.get("email", "sincorreo@gmail.com") or "sincorreo@gmail.com",
        record.get("address", ""),
        record.get("pension_system", ""),
        record.get("pension_commission", ""),
        record.get("cuspp", ""),
        record.get("issue_date", ""),
        record.get("expiry_date", ""),
        record.get("observations", ""),
    ]

    data_font = Font(name="Calibri", size=10)
    data_border = Border(
        left=Side(style="thin", color="E2E8F0"),
        right=Side(style="thin", color="E2E8F0"),
        top=Side(style="thin", color="E2E8F0"),
        bottom=Side(style="thin", color="E2E8F0")
    )

    # Zebra striping
    row_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid") if next_row % 2 == 0 else PatternFill(fill_type=None)

    ws.row_dimensions[next_row].height = 20

    for col_idx, value in enumerate(row_data, start=1):
        cell = ws.cell(row=next_row, column=col_idx, value=value)
        cell.font = data_font
        cell.border = data_border
        if row_fill.fill_type:
            cell.fill = row_fill

        # Alignments
        if col_idx in [1, 2, 6, 7, 8, 9, 11, 12]:
            cell.alignment = Alignment(horizontal="center", vertical="center")
        else:
            cell.alignment = Alignment(horizontal="left", vertical="center")

    wb.save(excel_path)


def generate_filtered_excel(records: List[Dict[str, Any]], target_path: Path):
    """
    Generates an on-demand Excel file containing the provided records.
    """
    wb = create_styled_workbook()
    ws = wb["Registros"]

    data_font = Font(name="Calibri", size=10)
    data_border = Border(
        left=Side(style="thin", color="E2E8F0"),
        right=Side(style="thin", color="E2E8F0"),
        top=Side(style="thin", color="E2E8F0"),
        bottom=Side(style="thin", color="E2E8F0")
    )

    for idx, rec in enumerate(records, start=2):
        scan_date_str = rec.get("scan_date", "")
        if isinstance(scan_date_str, datetime):
            scan_date_str = scan_date_str.strftime("%d/%m/%Y %H:%M:%S")

        row_data = [
            scan_date_str,
            rec.get("doc_type", ""),
            rec.get("paternal_surname", ""),
            rec.get("maternal_surname", ""),
            rec.get("first_names", ""),
            str(rec.get("doc_number", "")),
            rec.get("nationality", "PERUANA"),
            rec.get("birth_date", ""),
            rec.get("sex", ""),
            rec.get("address", ""),
            rec.get("issue_date", ""),
            rec.get("expiry_date", ""),
            rec.get("observations", ""),
        ]

        ws.row_dimensions[idx].height = 20
        row_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid") if idx % 2 == 0 else PatternFill(fill_type=None)

        for col_idx, value in enumerate(row_data, start=1):
            cell = ws.cell(row=idx, column=col_idx, value=value)
            cell.font = data_font
            cell.border = data_border
            if row_fill.fill_type:
                cell.fill = row_fill

            if col_idx in [1, 2, 6, 7, 8, 9, 11, 12]:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")

    wb.save(target_path)
