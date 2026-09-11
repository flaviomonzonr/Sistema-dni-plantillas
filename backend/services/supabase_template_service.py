import os
import io
import json
import uuid
import re
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import requests
import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from backend.config import TEMPLATES_DIR, EXPORTS_DIR, DATA_DIR, get_peru_now
from backend.services.excel_template_service import (
    COLUMN_MAPPINGS,
    is_cell_yellow,
    normalize_header,
    match_field_to_header,
)


SUPABASE_CONFIG_PATH = DATA_DIR / "supabase_config.json"
SUPABASE_CACHE_DIR = TEMPLATES_DIR / "supabase_cache"
SUPABASE_CACHE_DIR.mkdir(parents=True, exist_ok=True)


class SupabaseTemplateService:
    """
    Servicio independiente de Gestión de Plantillas con Supabase (Storage + Database).
    - Almacena archivos binarios (.xlsx / .docx) en Supabase Storage (bucket 'templates').
    - Almacena metadatos estructurados en la tabla 'excel_templates' (PostgreSQL).
    - Inspecciona celdas amarillas y mapeos de campos DNI para el llenado automático.
    - Soporta control de versiones (v1.0, v1.1...), reemplazo, descarga y procesamiento por lote.
    """

    def __init__(self):
        self.config_path = SUPABASE_CONFIG_PATH
        self.cache_dir = SUPABASE_CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._load_config()

    def _load_config(self):
        """Carga credenciales desde variables de entorno o archivo de configuración local."""
        self.supabase_url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
        self.supabase_key = os.getenv("SUPABASE_KEY", os.getenv("SUPABASE_ANON_KEY", "")).strip()
        self.bucket_name = os.getenv("SUPABASE_BUCKET_NAME", "templates").strip()
        self.table_name = os.getenv("SUPABASE_TABLE_NAME", "excel_templates").strip()

        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if not self.supabase_url and data.get("supabase_url"):
                        self.supabase_url = data.get("supabase_url", "").strip().rstrip("/")
                    if not self.supabase_key and data.get("supabase_key"):
                        self.supabase_key = data.get("supabase_key", "").strip()
                    if data.get("bucket_name"):
                        self.bucket_name = data.get("bucket_name", "templates").strip()
                    if data.get("table_name"):
                        self.table_name = data.get("table_name", "excel_templates").strip()
            except Exception as e:
                print(f"Error loading supabase_config.json: {e}")

    def save_config(self, supabase_url: str, supabase_key: str, bucket_name: str = "templates") -> Dict[str, Any]:
        """Guarda y actualiza las credenciales de Supabase."""
        self.supabase_url = supabase_url.strip().rstrip("/")
        self.supabase_key = supabase_key.strip()
        self.bucket_name = (bucket_name or "templates").strip()

        data = {
            "supabase_url": self.supabase_url,
            "supabase_key": self.supabase_key,
            "bucket_name": self.bucket_name,
            "table_name": self.table_name,
            "updated_at": get_peru_now().isoformat(),
        }

        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        # Probar conexión inmediatamente
        test_res = self.check_connection()
        return {
            "success": True,
            "config": {
                "supabase_url": self.supabase_url,
                "has_key": bool(self.supabase_key),
                "bucket_name": self.bucket_name,
            },
            "connection_test": test_res,
        }

    def get_config(self) -> Dict[str, Any]:
        """Retorna configuración pública (ocultando llave completa por seguridad)."""
        masked_key = ""
        if self.supabase_key:
            if len(self.supabase_key) > 12:
                masked_key = f"{self.supabase_key[:6]}...{self.supabase_key[-4:]}"
            else:
                masked_key = "***"

        return {
            "supabase_url": self.supabase_url,
            "has_key": bool(self.supabase_key),
            "masked_key": masked_key,
            "bucket_name": self.bucket_name,
            "table_name": self.table_name,
            "is_configured": bool(self.supabase_url and self.supabase_key),
        }

    def is_configured(self) -> bool:
        """Indica si la URL y la API Key de Supabase están configuradas."""
        return bool(self.supabase_url and self.supabase_key)

    def inspect_excel_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Inspecciona hojas y columnas amarillas desde un archivo en disco."""
        with open(file_path, "rb") as f:
            content = f.read()
        return self.inspect_excel_bytes(content, file_path.name)

    def _get_headers(self) -> Dict[str, str]:
        return {
            "apikey": self.supabase_key,
            "Authorization": f"Bearer {self.supabase_key}",
        }

    def check_connection(self) -> Dict[str, Any]:
        """Verifica la conectividad con Supabase Database y Supabase Storage."""
        if not self.supabase_url or not self.supabase_key:
            return {
                "connected": False,
                "database_ok": False,
                "storage_ok": False,
                "message": "Faltan configurar la URL y la Llave (API Key) de Supabase.",
            }

        db_ok = False
        db_message = ""
        storage_ok = False
        storage_message = ""

        # 1. Probar PostgREST Database
        try:
            db_url = f"{self.supabase_url}/rest/v1/{self.table_name}?select=id&limit=1"
            headers = self._get_headers()
            headers["Accept"] = "application/json"
            r = requests.get(db_url, headers=headers, timeout=8)
            if r.status_code in [200, 206]:
                db_ok = True
                db_message = f"Tabla '{self.table_name}' accesible."
            elif r.status_code == 404 or "relation" in r.text or "not found" in r.text:
                db_ok = False
                db_message = f"La tabla '{self.table_name}' no existe en la base de datos. Ejecuta el script SQL en Supabase."
            else:
                db_ok = False
                db_message = f"Error HTTP {r.status_code}: {r.text[:150]}"
        except Exception as e:
            db_ok = False
            db_message = f"Error de conexión a Database: {str(e)}"

        # 2. Probar Supabase Storage Bucket
        try:
            storage_url = f"{self.supabase_url}/storage/v1/bucket/{self.bucket_name}"
            headers = self._get_headers()
            r = requests.get(storage_url, headers=headers, timeout=8)
            if r.status_code == 200:
                storage_ok = True
                storage_message = f"Bucket '{self.bucket_name}' accesible."
            elif r.status_code in [400, 404]:
                # Intentar listar objetos
                list_url = f"{self.supabase_url}/storage/v1/object/list/{self.bucket_name}"
                r_list = requests.post(list_url, headers=headers, json={"limit": 1, "offset": 0}, timeout=8)
                if r_list.status_code == 200:
                    storage_ok = True
                    storage_message = f"Bucket '{self.bucket_name}' accesible."
                else:
                    storage_ok = False
                    storage_message = f"El bucket '{self.bucket_name}' no existe en Storage. Créalo en Supabase."
            else:
                storage_ok = False
                storage_message = f"Error HTTP {r.status_code} en Storage: {r.text[:150]}"
        except Exception as e:
            storage_ok = False
            storage_message = f"Error de conexión a Storage: {str(e)}"

        all_ok = db_ok and storage_ok
        return {
            "connected": all_ok,
            "database_ok": db_ok,
            "database_message": db_message,
            "storage_ok": storage_ok,
            "storage_message": storage_message,
            "message": "Conexión a Supabase exitosa." if all_ok else f"DB: {db_message} | Storage: {storage_message}",
        }

    # =========================================================================
    # Inspección de Archivos Excel y Análisis de Celdas Amarillas
    # =========================================================================
    def inspect_excel_bytes(self, file_bytes: bytes, filename: str) -> List[Dict[str, Any]]:
        """Inspecciona hojas y columnas amarillas desde bytes de un archivo .xlsx."""
        sheets_info = []
        try:
            wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=False)
            for sheet_idx, sheet_name in enumerate(wb.sheetnames):
                ws = wb[sheet_name]
                yellow_columns = []
                headers = {}
                mapped_fields = {}

                # Buscar fila de encabezado (generalmente fila 1 o 2)
                header_row = 1
                for r in range(1, min(ws.max_row + 1, 5)):
                    non_empty = [ws.cell(row=r, column=c).value for c in range(1, min(ws.max_column + 1, 30)) if ws.cell(row=r, column=c).value]
                    if len(non_empty) >= 2:
                        header_row = r
                        break

                max_col = min(ws.max_column, 60)
                max_check_row = min(ws.max_row, 15)

                for col_idx in range(1, max_col + 1):
                    header_cell = ws.cell(row=header_row, column=col_idx)
                    header_val = str(header_cell.value).strip() if header_cell.value is not None else f"Columna {get_column_letter(col_idx)}"
                    headers[col_idx] = header_val

                    # Detectar si la columna tiene celdas con relleno amarillo
                    has_yellow = is_cell_yellow(header_cell)
                    if not has_yellow:
                        for row_idx in range(header_row + 1, max_check_row + 1):
                            cell = ws.cell(row=row_idx, column=col_idx)
                            if is_cell_yellow(cell):
                                has_yellow = True
                                break

                    if has_yellow:
                        yellow_columns.append({
                            "col_index": col_idx,
                            "col_letter": get_column_letter(col_idx),
                            "header_name": header_val,
                        })

                    # Mapeo semántico automático
                    for dni_field in COLUMN_MAPPINGS.keys():
                        if dni_field not in mapped_fields:
                            if match_field_to_header(dni_field, header_val):
                                mapped_fields[dni_field] = {
                                    "column_index": col_idx,
                                    "column_letter": get_column_letter(col_idx),
                                    "header_name": header_val,
                                    "is_yellow": has_yellow,
                                }
                                break


                sheets_info.append({
                    "sheet_index": sheet_idx,
                    "sheet_name": sheet_name,
                    "header_row": header_row,
                    "data_start_row": header_row + 1,
                    "total_columns": ws.max_column,
                    "total_rows": ws.max_row,
                    "yellow_columns_count": len(yellow_columns),
                    "yellow_columns": yellow_columns,
                    "mapped_fields": mapped_fields,
                    "custom_mappings": {},
                })
        except Exception as e:
            print(f"Error analyzing excel bytes for {filename}: {e}")
            sheets_info.append({
                "sheet_index": 0,
                "sheet_name": "DATOS",
                "header_row": 1,
                "data_start_row": 2,
                "total_columns": 0,
                "total_rows": 0,
                "yellow_columns_count": 0,
                "yellow_columns": [],
                "mapped_fields": {},
                "custom_mappings": {},
                "error": str(e),
            })
        return sheets_info

    # =========================================================================
    # Operaciones CRUD en Supabase Storage y Supabase Database
    # =========================================================================
    def list_templates(self) -> List[Dict[str, Any]]:
        """Obtiene la lista de todas las plantillas registradas en Supabase."""
        if not self.supabase_url or not self.supabase_key:
            return []

        url = f"{self.supabase_url}/rest/v1/{self.table_name}?select=*&order=updated_at.desc"
        headers = self._get_headers()
        headers["Accept"] = "application/json"

        try:
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code in [200, 206]:
                rows = r.json()
                templates = []
                for row in rows:
                    sheets = row.get("sheets_metadata") or []
                    if isinstance(sheets, str):
                        try:
                            sheets = json.loads(sheets)
                        except Exception:
                            sheets = []

                    templates.append({
                        "id": str(row.get("id")),
                        "name": row.get("name") or row.get("filename"),
                        "filename": row.get("filename"),
                        "template_type": row.get("template_type") or "EXCEL_CARGA_MASIVA",
                        "version": row.get("version") or "1.0",
                        "storage_path": row.get("storage_path"),
                        "file_size_kb": float(row.get("file_size_kb") or 0.0),
                        "created_at": row.get("created_at"),
                        "updated_at": row.get("updated_at"),
                        "user_name": row.get("user_name") or "Flavio Monzón",
                        "is_active": row.get("is_active", True),
                        "sheets": sheets,
                        "default_sheet": sheets[0]["sheet_name"] if sheets else "DATOS",
                        "source": "supabase",
                    })
                return templates
            else:
                print(f"Supabase list_templates error {r.status_code}: {r.text}")
                return []
        except Exception as e:
            print(f"Exception listing templates from Supabase: {e}")
            return []

    def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene metadatos de una plantilla específica por ID."""
        if not self.supabase_url or not self.supabase_key:
            return None

        url = f"{self.supabase_url}/rest/v1/{self.table_name}?id=eq.{template_id}&select=*"
        headers = self._get_headers()
        headers["Accept"] = "application/json"

        try:
            r = requests.get(url, headers=headers, timeout=8)
            if r.status_code == 200 and r.json():
                row = r.json()[0]
                sheets = row.get("sheets_metadata") or []
                if isinstance(sheets, str):
                    try:
                        sheets = json.loads(sheets)
                    except Exception:
                        sheets = []
                return {
                    "id": str(row.get("id")),
                    "name": row.get("name") or row.get("filename"),
                    "filename": row.get("filename"),
                    "template_type": row.get("template_type") or "EXCEL_CARGA_MASIVA",
                    "version": row.get("version") or "1.0",
                    "storage_path": row.get("storage_path"),
                    "file_size_kb": float(row.get("file_size_kb") or 0.0),
                    "created_at": row.get("created_at"),
                    "updated_at": row.get("updated_at"),
                    "user_name": row.get("user_name") or "Flavio Monzón",
                    "is_active": row.get("is_active", True),
                    "sheets": sheets,
                    "source": "supabase",
                }
        except Exception as e:
            print(f"Error fetching template {template_id}: {e}")
        return None

    def upload_template(
        self,
        file_bytes: bytes,
        filename: str,
        name: Optional[str] = None,
        template_type: str = "EXCEL_CARGA_MASIVA",
        version: str = "1.0",
        user_name: str = "Flavio Monzón",
    ) -> Dict[str, Any]:
        """
        Sube un archivo a Supabase Storage y crea el registro de metadatos en Supabase Database.
        """
        if not self.supabase_url or not self.supabase_key:
            raise RuntimeError("Supabase no está configurado. Ingrese URL y API Key en la configuración.")

        # Sanitizar nombre
        clean_filename = re.sub(r'[\\/*?:"<>|]', "", filename)
        if not clean_filename.lower().endswith(".xlsx"):
            clean_filename += ".xlsx"

        display_name = (name or Path(clean_filename).stem).strip()
        template_uuid = str(uuid.uuid4())
        storage_filename = f"{template_uuid}_{clean_filename}"
        storage_path = storage_filename

        file_size_kb = round(len(file_bytes) / 1024, 2)

        # 1. Subir archivo a Supabase Storage
        storage_upload_url = f"{self.supabase_url}/storage/v1/object/{self.bucket_name}/{storage_path}"
        headers = self._get_headers()
        headers["Content-Type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

        r_upload = requests.post(storage_upload_url, headers=headers, data=file_bytes, timeout=30)
        if r_upload.status_code not in [200, 201]:
            # Si da error de bucket no encontrado, intentar crearlo
            if "Bucket not found" in r_upload.text:
                raise RuntimeError(f"El bucket '{self.bucket_name}' no existe en Supabase Storage. Créalo como público.")
            raise RuntimeError(f"Error subiendo archivo a Supabase Storage ({r_upload.status_code}): {r_upload.text}")

        # 2. Analizar celdas amarillas y hojas
        sheets_metadata = self.inspect_excel_bytes(file_bytes, clean_filename)

        # 3. Guardar en Supabase Database
        now_iso = get_peru_now().isoformat()
        db_url = f"{self.supabase_url}/rest/v1/{self.table_name}"
        db_headers = self._get_headers()
        db_headers["Content-Type"] = "application/json"
        db_headers["Prefer"] = "return=representation"

        payload = {
            "id": template_uuid,
            "name": display_name,
            "filename": clean_filename,
            "template_type": template_type,
            "version": version or "1.0",
            "storage_path": storage_path,
            "file_size_kb": file_size_kb,
            "created_at": now_iso,
            "updated_at": now_iso,
            "user_name": user_name or "Flavio Monzón",
            "sheets_metadata": sheets_metadata,
            "is_active": True,
        }

        r_db = requests.post(db_url, headers=db_headers, json=payload, timeout=10)
        if r_db.status_code not in [200, 201]:
            # Limpiar archivo en storage si falló la base de datos
            try:
                requests.delete(storage_upload_url, headers=self._get_headers(), timeout=5)
            except Exception:
                pass
            raise RuntimeError(f"Error guardando metadatos en Supabase DB ({r_db.status_code}): {r_db.text}")

        # Guardar copia en caché local para acceso ultrarrápido
        cache_file_path = self.cache_dir / f"{template_uuid}.xlsx"
        with open(cache_file_path, "wb") as f:
            f.write(file_bytes)

        return {
            "success": True,
            "id": template_uuid,
            "name": display_name,
            "filename": clean_filename,
            "template_type": template_type,
            "version": version,
            "storage_path": storage_path,
            "file_size_kb": file_size_kb,
            "sheets": sheets_metadata,
            "message": f"Plantilla '{clean_filename}' subida y registrada en Supabase exitosamente.",
        }

    def replace_template_file(
        self,
        template_id: str,
        file_bytes: bytes,
        filename: str,
        user_name: str = "Flavio Monzón",
    ) -> Dict[str, Any]:
        """
        Reemplaza el archivo físico en Supabase Storage, recalcula las celdas amarillas
        e incrementa la versión en la base de datos (e.g. 1.0 -> 1.1).
        """
        current_tpl = self.get_template(template_id)
        if not current_tpl:
            raise RuntimeError(f"No se encontró la plantilla con ID {template_id} en Supabase.")

        clean_filename = re.sub(r'[\\/*?:"<>|]', "", filename)
        if not clean_filename.lower().endswith(".xlsx"):
            clean_filename += ".xlsx"

        old_storage_path = current_tpl.get("storage_path")
        old_version = current_tpl.get("version", "1.0")

        # Calcular nueva versión incrementada
        new_version = self._increment_version(old_version)

        # 1. Subir nuevo archivo (sobrescribir o nueva ruta)
        new_storage_path = f"{template_id}_{clean_filename}"
        storage_upload_url = f"{self.supabase_url}/storage/v1/object/{self.bucket_name}/{new_storage_path}"
        headers = self._get_headers()
        headers["Content-Type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        headers["x-upsert"] = "true"

        r_upload = requests.post(storage_upload_url, headers=headers, data=file_bytes, timeout=30)
        if r_upload.status_code not in [200, 201]:
            raise RuntimeError(f"Error al reemplazar archivo en Supabase Storage: {r_upload.text}")

        # Si cambió el nombre del archivo, eliminar el anterior de storage
        if old_storage_path and old_storage_path != new_storage_path:
            try:
                old_del_url = f"{self.supabase_url}/storage/v1/object/{self.bucket_name}/{old_storage_path}"
                requests.delete(old_del_url, headers=self._get_headers(), timeout=5)
            except Exception:
                pass

        # 2. Analizar nuevas celdas amarillas
        new_sheets_metadata = self.inspect_excel_bytes(file_bytes, clean_filename)

        # 3. Actualizar metadatos en Supabase DB
        now_iso = get_peru_now().isoformat()
        db_url = f"{self.supabase_url}/rest/v1/{self.table_name}?id=eq.{template_id}"
        db_headers = self._get_headers()
        db_headers["Content-Type"] = "application/json"
        db_headers["Prefer"] = "return=representation"

        payload = {
            "filename": clean_filename,
            "version": new_version,
            "storage_path": new_storage_path,
            "file_size_kb": round(len(file_bytes) / 1024, 2),
            "updated_at": now_iso,
            "user_name": user_name or "Flavio Monzón",
            "sheets_metadata": new_sheets_metadata,
        }

        r_db = requests.patch(db_url, headers=db_headers, json=payload, timeout=10)
        if r_db.status_code not in [200, 204]:
            raise RuntimeError(f"Error actualizando metadatos en Supabase DB: {r_db.text}")

        # Actualizar caché local
        cache_file_path = self.cache_dir / f"{template_id}.xlsx"
        with open(cache_file_path, "wb") as f:
            f.write(file_bytes)

        return {
            "success": True,
            "id": template_id,
            "filename": clean_filename,
            "version": new_version,
            "file_size_kb": payload["file_size_kb"],
            "sheets": new_sheets_metadata,
            "message": f"Plantilla actualizada con éxito a la versión {new_version}.",
        }

    def update_template_metadata(
        self,
        template_id: str,
        name: Optional[str] = None,
        template_type: Optional[str] = None,
        version: Optional[str] = None,
        sheets_metadata: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Actualiza el nombre, tipo, versión o mapeos personalizados de una plantilla."""
        payload = {"updated_at": get_peru_now().isoformat()}
        if name is not None:
            payload["name"] = name.strip()
        if template_type is not None:
            payload["template_type"] = template_type.strip()
        if version is not None:
            payload["version"] = version.strip()
        if sheets_metadata is not None:
            payload["sheets_metadata"] = sheets_metadata

        db_url = f"{self.supabase_url}/rest/v1/{self.table_name}?id=eq.{template_id}"
        headers = self._get_headers()
        headers["Content-Type"] = "application/json"
        headers["Prefer"] = "return=representation"

        r = requests.patch(db_url, headers=headers, json=payload, timeout=8)
        if r.status_code not in [200, 204]:
            raise RuntimeError(f"Error actualizando plantilla en Supabase: {r.text}")

        return {"success": True, "message": "Metadatos actualizados exitosamente."}

    def delete_template(self, template_id: str) -> Dict[str, Any]:
        """Elimina la plantilla de Supabase Storage y de Supabase Database."""
        current_tpl = self.get_template(template_id)
        if not current_tpl:
            raise RuntimeError(f"No se encontró la plantilla {template_id} en Supabase.")

        storage_path = current_tpl.get("storage_path")

        # 1. Eliminar archivo de Supabase Storage
        if storage_path:
            try:
                del_storage_url = f"{self.supabase_url}/storage/v1/object/{self.bucket_name}/{storage_path}"
                requests.delete(del_storage_url, headers=self._get_headers(), timeout=8)
            except Exception as e:
                print(f"Warning deleting from storage: {e}")

        # 2. Eliminar registro de Supabase Database
        db_url = f"{self.supabase_url}/rest/v1/{self.table_name}?id=eq.{template_id}"
        headers = self._get_headers()
        r = requests.delete(db_url, headers=headers, timeout=8)
        if r.status_code not in [200, 204]:
            raise RuntimeError(f"Error eliminando de Supabase DB: {r.text}")

        # Eliminar del caché local
        cache_file_path = self.cache_dir / f"{template_id}.xlsx"
        if cache_file_path.exists():
            try:
                cache_file_path.unlink()
            except Exception:
                pass

        return {"success": True, "message": "Plantilla eliminada de Supabase exitosamente."}

    def download_template_file(self, template_id: str) -> Tuple[bytes, str]:
        """Descarga el contenido binario del archivo desde Supabase Storage."""
        current_tpl = self.get_template(template_id)
        if not current_tpl:
            raise RuntimeError(f"No se encontró la plantilla {template_id} en Supabase.")

        storage_path = current_tpl.get("storage_path")
        filename = current_tpl.get("filename") or f"plantilla_{template_id}.xlsx"

        # Comprobar si está en caché local
        cache_file_path = self.cache_dir / f"{template_id}.xlsx"
        if cache_file_path.exists():
            with open(cache_file_path, "rb") as f:
                return f.read(), filename

        # Descargar de Supabase Storage
        download_url = f"{self.supabase_url}/storage/v1/object/{self.bucket_name}/{storage_path}"
        headers = self._get_headers()
        r = requests.get(download_url, headers=headers, timeout=25)
        if r.status_code != 200:
            raise RuntimeError(f"Error descargando archivo de Supabase Storage ({r.status_code}): {r.text}")

        file_bytes = r.content

        # Guardar en caché
        with open(cache_file_path, "wb") as f:
            f.write(file_bytes)

        return file_bytes, filename

    def get_template_path_for_processing(self, template_id: str) -> Path:
        """
        Garantiza que la plantilla esté en el caché local de disco para que openpyxl
        la procese ultrarrápido al generar archivos por lote.
        """
        cache_file_path = self.cache_dir / f"{template_id}.xlsx"
        if cache_file_path.exists() and cache_file_path.stat().st_size > 0:
            return cache_file_path

        file_bytes, _ = self.download_template_file(template_id)
        with open(cache_file_path, "wb") as f:
            f.write(file_bytes)

        return cache_file_path

    def _increment_version(self, version_str: str) -> str:
        """Incrementa versión semántica (ej. 1.0 -> 1.1, 1.9 -> 2.0, v1 -> v2)."""
        if not version_str:
            return "1.1"
        cleaned = version_str.strip().lower().lstrip("v")
        match = re.match(r"^(\d+)(?:\.(\d+))?$", cleaned)
        if match:
            major = int(match.group(1))
            minor = int(match.group(2)) if match.group(2) is not None else 0
            minor += 1
            if minor >= 10:
                major += 1
                minor = 0
            return f"{major}.{minor}"
        return f"{version_str}.1"


supabase_template_service = SupabaseTemplateService()
