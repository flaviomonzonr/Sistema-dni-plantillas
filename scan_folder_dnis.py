"""
Script de Escaneo Masivo de Carpetas de DNI (scan_folder_dnis.py)
Permite señalar cualquier carpeta dentro del proyecto (por ejemplo: DNIS, ENTRADA o una ruta personalizada)
y procesar todas las fotos de DNI con OpenCV + RapidOCR + Regex.
"""

import sys
import os
import time
import json
from pathlib import Path
from typing import List, Dict, Any

# Asegurar que el backend y raíz estén en el path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.ocr_engine import extract_dni_from_bytes


def scan_folder(folder_path: str = "DNIS", recursive: bool = True) -> List[Dict[str, Any]]:
    """
    Escanea todos los archivos de imagen dentro de la carpeta especificada y extrae DNI, Nombres y Apellidos.
    """
    target_dir = Path(folder_path)
    if not target_dir.is_absolute():
        target_dir = ROOT_DIR / folder_path

    if not target_dir.exists():
        print(f"\n[ERROR] La carpeta '{target_dir}' no existe.")
        return []

    valid_extensions = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}

    if recursive:
        image_files = [f for f in target_dir.rglob("*") if f.is_file() and f.suffix.lower() in valid_extensions]
    else:
        image_files = [f for f in target_dir.iterdir() if f.is_file() and f.suffix.lower() in valid_extensions]

    # Ordenar alfabéticamente
    image_files.sort(key=lambda x: str(x).lower())

    print("=" * 80)
    print(" >>> ESCANEO DE CARPETA DE DNI CON OPENCV + RAPIDOCR + REGEX")
    print("=" * 80)
    print(f" Carpeta señalada: {target_dir}")
    print(f" Total de imágenes encontradas: {len(image_files)}")
    print("=" * 80)

    if not image_files:
        print("\n[AVISO] No se encontraron archivos de imagen en la carpeta señalada.\n")
        return []

    results = []
    t_start = time.time()
    count_ok = 0

    print(f"\n{'N°':<4} | {'ARCHIVO':<35} | {'DNI':<10} | {'APELLIDOS':<22} | {'NOMBRES':<20}")
    print("-" * 105)

    for idx, img_path in enumerate(image_files, 1):
        rel_name = img_path.name
        if len(rel_name) > 34:
            rel_name = rel_name[:31] + "..."

        try:
            img_bytes = img_path.read_bytes()
            extracted = extract_dni_from_bytes(img_bytes)

            dni = extracted.get("dni", "")
            apellidos = extracted.get("apellidos", "")
            nombres = extracted.get("nombres", "")
            success = extracted.get("success", False)

            if success:
                count_ok += 1

            disp_dni = dni if dni else "[NO DETECT]"
            disp_ape = apellidos[:21] if apellidos else "[NO DETECT]"
            disp_nom = nombres[:19] if nombres else "[NO DETECT]"

            print(f"{idx:<4} | {rel_name:<35} | {disp_dni:<10} | {disp_ape:<22} | {disp_nom:<20}")

            results.append({
                "index": idx,
                "file_name": img_path.name,
                "file_path": str(img_path),
                "dni": dni,
                "apellidos": apellidos,
                "nombres": nombres,
                "paterno": extracted.get("paterno", ""),
                "materno": extracted.get("materno", ""),
                "success": success,
                "confidence": extracted.get("confidence", {}),
                "raw_text": extracted.get("raw_text", ""),
            })

        except Exception as e:
            print(f"{idx:<4} | {rel_name:<35} | [ERROR: {str(e)[:40]}]")
            results.append({
                "index": idx,
                "file_name": img_path.name,
                "file_path": str(img_path),
                "error": str(e),
                "success": False
            })

    t_total = time.time() - t_start

    # Guardar resultados en JSON
    exports_dir = ROOT_DIR / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)
    out_json = exports_dir / "escaneo_carpeta_dnis.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 80)
    print(" RESUMEN DEL ESCANEO:")
    print("=" * 80)
    print(f" Total de imágenes analizadas: {len(image_files)}")
    print(f" DNI/Datos extraídos con éxito: {count_ok} / {len(image_files)} ({count_ok/max(1, len(image_files))*100:.1f}%)")
    print(f" Tiempo total de procesamiento:  {t_total:.2f} s ({t_total/max(1, len(image_files)):.2f} s/imagen)")
    print(f" Resultados guardados en:        {out_json}")
    print("=" * 80 + "\n")

    return results


if __name__ == "__main__":
    folder_arg = sys.argv[1] if len(sys.argv) > 1 else "DNIS"
    scan_folder(folder_arg)
