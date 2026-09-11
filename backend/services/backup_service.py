import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
from backend.config import DATA_DIR, EXPORTS_DIR, TEMPLATES_DIR, MASTER_EXCEL_PATH, DB_PATH, get_peru_now

BACKUPS_DIR = DATA_DIR / "backups"
BACKUPS_DIR.mkdir(parents=True, exist_ok=True)


class BackupService:
    """
    Servicio de Copias de Seguridad Automáticas y Restauración.
    Protege la base de datos SQLite records.db, el archivo maestro Registros.xlsx
    y las plantillas personalizadas.
    """

    def __init__(self):
        self.backups_dir = BACKUPS_DIR
        self.backups_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(self, trigger_reason: str = "manual") -> Dict[str, Any]:
        """
        Crea una copia de seguridad timestamped de la base de datos y archivos maestros.
        """
        now = get_peru_now()
        timestamp_str = now.strftime("%Y%m%d_%H%M%S")
        
        db_backup_name = f"records_backup_{timestamp_str}.db"
        db_backup_path = self.backups_dir / db_backup_name

        excel_backup_name = f"Registros_backup_{timestamp_str}.xlsx"
        excel_backup_path = self.backups_dir / excel_backup_name

        backed_up_files = []

        # 1. Copiar base de datos SQLite
        if DB_PATH.exists():
            shutil.copy2(DB_PATH, db_backup_path)
            backed_up_files.append(str(db_backup_name))

        # 2. Copiar archivo maestro Excel
        if MASTER_EXCEL_PATH.exists():
            shutil.copy2(MASTER_EXCEL_PATH, excel_backup_path)
            backed_up_files.append(str(excel_backup_name))

        # Limpiar backups antiguos (mantener los últimos 30)
        self._prune_old_backups(max_keep=30)

        return {
            "success": True,
            "timestamp": now.isoformat(),
            "trigger": trigger_reason,
            "files": backed_up_files,
            "backup_dir": str(self.backups_dir),
            "message": f"Copia de seguridad creada exitosamente con {len(backed_up_files)} archivos.",
        }

    def create_full_zip_package(self) -> Path:
        """
        Empaqueta la base de datos completa, plantillas Excel y archivos maestros
        en un archivo ZIP descargable para respaldos externos (USB, Drive, etc.).
        """
        now = get_peru_now()
        zip_filename = f"RESPALDO_COMPLETO_ESCANDNI_{now.strftime('%Y%m%d_%H%M%S')}.zip"
        zip_path = self.backups_dir / zip_filename

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            # 1. Base de datos
            if DB_PATH.exists():
                zipf.write(DB_PATH, arcname=f"data/{DB_PATH.name}")

            # 2. Excel Maestro
            if MASTER_EXCEL_PATH.exists():
                zipf.write(MASTER_EXCEL_PATH, arcname=f"exports/{MASTER_EXCEL_PATH.name}")

            # 3. Plantillas Excel
            excel_templates_dir = TEMPLATES_DIR / "excel"
            if excel_templates_dir.exists():
                for file_p in excel_templates_dir.glob("*.*"):
                    if file_p.is_file():
                        zipf.write(file_p, arcname=f"templates/excel/{file_p.name}")

            # 4. Plantillas Word (.docx)
            if TEMPLATES_DIR.exists():
                for file_p in TEMPLATES_DIR.glob("*.docx"):
                    zipf.write(file_p, arcname=f"templates/{file_p.name}")

        return zip_path

    def get_backup_status(self) -> Dict[str, Any]:
        """
        Retorna el estado de persistencia, total de respaldos disponibles y tamaño en disco.
        """
        backups = list(self.backups_dir.glob("*_backup_*.db"))
        backups.sort(key=lambda p: p.stat().st_mtime, reverse=True)

        last_backup_time = None
        if backups:
            last_backup_time = datetime.fromtimestamp(backups[0].stat().st_mtime).strftime("%d/%m/%Y %H:%M:%S")

        db_size_kb = round(DB_PATH.stat().st_size / 1024, 2) if DB_PATH.exists() else 0
        excel_size_kb = round(MASTER_EXCEL_PATH.stat().st_size / 1024, 2) if MASTER_EXCEL_PATH.exists() else 0

        return {
            "status": "protected",
            "db_exists": DB_PATH.exists(),
            "db_size_kb": db_size_kb,
            "master_excel_exists": MASTER_EXCEL_PATH.exists(),
            "master_excel_size_kb": excel_size_kb,
            "total_backups_count": len(backups),
            "last_backup_time": last_backup_time or "Ninguno aún",
            "backup_directory": str(self.backups_dir),
        }

    def _prune_old_backups(self, max_keep: int = 30):
        """Elimina copias de seguridad antiguas si exceden el límite de retención."""
        try:
            for pattern in ["*_backup_*.db", "*_backup_*.xlsx"]:
                files = sorted(self.backups_dir.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
                if len(files) > max_keep:
                    for old_file in files[max_keep:]:
                        try:
                            old_file.unlink()
                        except Exception:
                            pass
        except Exception:
            pass


backup_service = BackupService()
