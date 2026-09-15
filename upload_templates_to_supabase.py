"""
Script de Subida Automática de Plantillas a Supabase (upload_templates_to_supabase.py)
Sube automáticamente las plantillas de Excel locales a Supabase Storage y Database.
"""

import sys
import os
from pathlib import Path

# Asegurar path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.services.supabase_template_service import supabase_template_service


def upload_all_local_templates():
    """
    Sube todas las plantillas encontradas en templates/excel a Supabase.
    """
    templates_dir = ROOT_DIR / "templates" / "excel"
    if not templates_dir.exists():
        print(f"[ERROR] No se encontró el directorio {templates_dir}")
        return

    xlsx_files = list(templates_dir.glob("*.xlsx"))
    if not xlsx_files:
        print("[AVISO] No se encontraron archivos .xlsx en templates/excel/")
        return

    print("=" * 70)
    print(" >>> SUBIDA DE PLANTILLAS EXCEL A SUPABASE")
    print("=" * 70)

    # Verificar estado de conexión
    conn_status = supabase_template_service.check_connection()
    print(f" Estado de conexión con Supabase: {conn_status.get('status', 'DESCONOCIDO')}")
    if not conn_status.get("storage_connected") or not conn_status.get("database_connected"):
        print("\n[!] Advertencia: Verifique sus credenciales de Supabase (SUPABASE_URL y SUPABASE_KEY).")
        print(f"    Detalles: {conn_status.get('message')}\n")

    for tpl_file in xlsx_files:
        print(f" Procesando archivo: {tpl_file.name} ...")
        try:
            file_bytes = tpl_file.read_bytes()
            res = supabase_template_service.upload_template(
                file_bytes=file_bytes,
                filename=tpl_file.name,
                name=tpl_file.stem,
                template_type="EXCEL_CARGA_MASIVA",
                version="1.0",
                user_name="Flavio Monzón"
            )
            print(f" [OK] Plantilla '{tpl_file.name}' subida con éxito.")
            print(f"      ID: {res.get('template', {}).get('id')}")
            print(f"      Hojas analizadas: {len(res.get('template', {}).get('sheets', []))}")
        except Exception as e:
            print(f" [ERROR] No se pudo subir '{tpl_file.name}': {str(e)}")

    print("=" * 70 + "\n")


if __name__ == "__main__":
    upload_all_local_templates()
