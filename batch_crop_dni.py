import os
import sys
import shutil
import time
from pathlib import Path
from typing import List, Optional, Tuple
import cv2
import numpy as np


# Rutas base
BASE_DIR = Path(__file__).resolve().parent
DIR_ENTRADA = BASE_DIR / "ENTRADA"
DIR_PROCESADOS = BASE_DIR / "PROCESADOS"
DIR_ERRORES = BASE_DIR / "ERRORES"

# Dimensiones estándar ID-1 (DNI Peruano / Carnet Extranjería)
STD_WIDTH = 1014
STD_HEIGHT = 640
ASPECT_RATIO_TARGET = 1.586  # 85.6 / 53.98
MARGIN_PX = 10  # Margen de seguridad en píxeles para no cortar bordes de texto


def init_directories():
    """Crea las carpetas necesarias si no existen."""
    for d in [DIR_ENTRADA, DIR_PROCESADOS, DIR_ERRORES]:
        d.mkdir(parents=True, exist_ok=True)


def order_points(pts: np.ndarray) -> np.ndarray:
    """Ordena 4 puntos: [top-left, top-right, bottom-right, bottom-left]."""
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]

    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


def warp_card(image: np.ndarray, pts: np.ndarray, target_w: int = STD_WIDTH, target_h: int = STD_HEIGHT) -> np.ndarray:
    """Aplica corrección de perspectiva y enderezado."""
    rect = order_points(pts)
    
    # Agregar margen de seguridad expandiendo ligeramente el cuadrilátero desde su centro
    center = np.mean(rect, axis=0)
    expanded = np.zeros_like(rect)
    for i in range(4):
        vec = rect[i] - center
        expanded[i] = center + vec * 1.03  # 3% de margen de seguridad extra

    # Asegurar dentro de límites de imagen
    h_img, w_img = image.shape[:2]
    expanded[:, 0] = np.clip(expanded[:, 0], 0, w_img - 1)
    expanded[:, 1] = np.clip(expanded[:, 1], 0, h_img - 1)

    dst = np.array([
        [0, 0],
        [target_w - 1, 0],
        [target_w - 1, target_h - 1],
        [0, target_h - 1]
    ], dtype="float32")

    M = cv2.getPerspectiveTransform(expanded, dst)
    warped = cv2.warpPerspective(image, M, (target_w, target_h), flags=cv2.INTER_CUBIC)
    return warped


def find_card_contours(image: np.ndarray) -> List[np.ndarray]:
    """
    Detecta automáticamente 1 o 2 áreas de DNI en la imagen usando visión por computadora.
    Devuelve lista de cuadriláteros ordenados por posición vertical.
    """
    h_img, w_img = image.shape[:2]
    total_area = h_img * w_img
    min_area = total_area * 0.05   # Al menos 5% del área total
    max_area = total_area * 0.98

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.bilateralFilter(gray, 9, 75, 75)

    # Multi-estrategia de detección de bordes
    edge_maps = [
        cv2.Canny(blurred, 30, 120),
        cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), 50, 150),
        cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 15, 4),
    ]

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    found_cards = []

    for edge in edge_maps:
        closed = cv2.morphologyEx(edge, cv2.MORPH_CLOSE, kernel, iterations=3)
        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)[:10]

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < min_area or area > max_area:
                continue

            peri = cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, 0.025 * peri, True)

            if len(approx) == 4 and cv2.isContourConvex(approx):
                pts = approx.reshape(4, 2).astype("float32")
                rect = order_points(pts)

                # Calcular ancho y alto detectados
                w_top = np.linalg.norm(rect[1] - rect[0])
                w_bot = np.linalg.norm(rect[2] - rect[3])
                h_left = np.linalg.norm(rect[3] - rect[0])
                h_right = np.linalg.norm(rect[2] - rect[1])

                w_card = max(w_top, w_bot)
                h_card = max(h_left, h_right)

                if w_card < 50 or h_card < 50:
                    continue

                aspect = w_card / h_card if w_card > h_card else h_card / w_card
                # Aspect ratio DNI ~1.586 (tolerancia entre 1.25 y 2.10)
                if 1.25 <= aspect <= 2.10:
                    # Evitar duplicados comparando centroides
                    center = np.mean(pts, axis=0)
                    is_duplicate = False
                    for existing in found_cards:
                        ex_center = np.mean(existing, axis=0)
                        if np.linalg.norm(center - ex_center) < (min(w_img, h_img) * 0.15):
                            is_duplicate = True
                            break

                    if not is_duplicate:
                        found_cards.append(pts)

        if len(found_cards) >= 2:
            break

    # Si no encontró polígono exacto de 4 lados, intentar mediante bounding box rotado
    if not found_cards:
        for edge in edge_maps[:2]:
            contours, _ = cv2.findContours(edge, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if min_area <= area <= max_area:
                    rect_box = cv2.minAreaRect(cnt)
                    (cx, cy), (bw, bh), angle = rect_box
                    if bw > 0 and bh > 0:
                        aspect = max(bw, bh) / min(bw, bh)
                        if 1.30 <= aspect <= 2.0:
                            box_pts = cv2.boxPoints(rect_box).astype("float32")
                            found_cards.append(box_pts)
                            break
            if found_cards:
                break

    # Ordenar las tarjetas detectadas de arriba a abajo
    found_cards = sorted(found_cards, key=lambda p: np.mean(p[:, 1]))
    return found_cards[:2]


def process_single_image(image_path: Path) -> Tuple[bool, str]:
    """Procesa una imagen: detecta, recorta, endereza y guarda."""
    try:
        # Cargar con soporte Unicode en Windows
        data = np.fromfile(str(image_path), dtype=np.uint8)
        img = cv2.imdecode(data, cv2.IMREAD_COLOR)

        if img is None:
            return False, "No se pudo decodificar la imagen"

        cards_pts = find_card_contours(img)

        if not cards_pts:
            # Detección fallida -> Mover/Copiar a ERRORES
            dest = DIR_ERRORES / image_path.name
            shutil.copy2(str(image_path), str(dest))
            return False, "No se detectó el documento DNI con suficiente claridad"

        cropped_cards = []
        for pts in cards_pts:
            warped = warp_card(img, pts, STD_WIDTH, STD_HEIGHT)
            cropped_cards.append(warped)

        # Si detectó 2 caras (Anverso y Reverso en la misma foto), unirlas verticalmente
        if len(cropped_cards) == 2:
            # Separador estético de 12px
            sep = np.full((12, STD_WIDTH, 3), 40, dtype=np.uint8)
            final_img = np.vstack([cropped_cards[0], sep, cropped_cards[1]])
        else:
            final_img = cropped_cards[0]

        # Guardar en PROCESADOS
        out_path = DIR_PROCESADOS / image_path.name
        is_success, encoded_buf = cv2.imencode(out_path.suffix or ".jpg", final_img, [cv2.IMWRITE_JPEG_QUALITY, 95])
        if is_success:
            encoded_buf.tofile(str(out_path))
            return True, f"OK ({len(cropped_cards)} cara{'s' if len(cropped_cards)>1 else ''} detectada{'s' if len(cropped_cards)>1 else ''})"
        else:
            return False, "Error al guardar imagen procesada"

    except Exception as e:
        dest = DIR_ERRORES / image_path.name
        try:
            shutil.copy2(str(image_path), str(dest))
        except Exception:
            pass
        return False, f"Excepción: {str(e)}"


def run_batch():
    """Ejecuta el procesamiento por lotes sobre la carpeta ENTRADA."""
    init_directories()

    valid_extensions = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
    all_files = [f for f in DIR_ENTRADA.iterdir() if f.is_file() and f.suffix.lower() in valid_extensions]

    print("=" * 65)
    print(" >>> PROCESADOR DE DNI POR LOTES (Deteccion + Recorte Automatico)")
    print("=" * 65)
    print(f" Carpeta de Entrada:     {DIR_ENTRADA}")
    print(f" Carpeta de Procesados:  {DIR_PROCESADOS}")
    print(f" Carpeta de Errores:     {DIR_ERRORES}")
    print("=" * 65)

    if not all_files:
        print(f"\n[AVISO] No hay imagenes en la carpeta '{DIR_ENTRADA.name}'.")
        print("        Copia tus imagenes (.jpg, .png) dentro de 'ENTRADA' y vuelve a ejecutar.\n")
        return

    print(f"\nIniciando procesamiento de {len(all_files)} imagenes...\n")

    t_start = time.time()
    count_ok = 0
    count_err = 0

    for i, file_path in enumerate(all_files, 1):
        ok, msg = process_single_image(file_path)
        if ok:
            count_ok += 1
            status_icon = "[OK]"
        else:
            count_err += 1
            status_icon = "[ERR]"

        print(f" [{i}/{len(all_files)}] {status_icon} {file_path.name:<30} -> {msg}")

    t_total = time.time() - t_start

    print("\n" + "=" * 65)
    print(" RESUMEN FINAL DEL PROCESAMIENTO:")
    print("=" * 65)
    print(f" Total de imagenes:    {len(all_files)}")
    print(f" Procesadas con exito: {count_ok} (guardadas en 'PROCESADOS')")
    print(f" Con error/no detect:  {count_err} (enviadas a 'ERRORES')")
    print(f" Tiempo total:         {t_total:.2f} segundos ({t_total/max(1, len(all_files)):.2f}s por imagen)")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    run_batch()
