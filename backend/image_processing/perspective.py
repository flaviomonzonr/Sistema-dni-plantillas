import cv2
import numpy as np
from typing import Tuple, Optional, List


def order_points(pts: np.ndarray) -> np.ndarray:
    """
    Orders 4 coordinate points in the following order:
    0: top-left, 1: top-right, 2: bottom-right, 3: bottom-left.
    """
    rect = np.zeros((4, 2), dtype="float32")

    # Sum of coordinates: top-left has smallest sum, bottom-right has largest sum
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]

    # Difference of coordinates: top-right has smallest diff (x - y), bottom-left has largest diff
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]

    return rect


def find_document_contour(image: np.ndarray) -> Optional[np.ndarray]:
    """
    Detects the 4-corner polygon contour of an ID document card using
    multi-threshold edge detection and morphological analysis.
    Optimized for speed: downscales huge high-res phone images for instantaneous contour search.
    """
    h_orig, w_orig = image.shape[:2]
    
    # Scale down for ultra-fast edge analysis (max 960px)
    max_dim = max(h_orig, w_orig)
    scale = 1.0
    if max_dim > 960:
        scale = 960.0 / max_dim
        small_img = cv2.resize(image, (int(w_orig * scale), int(h_orig * scale)), interpolation=cv2.INTER_AREA)
    else:
        small_img = image

    h, w = small_img.shape[:2]
    total_area = h * w
    min_area = total_area * 0.08  # Document should occupy at least 8% of frame
    max_area = total_area * 0.99

    gray = cv2.cvtColor(small_img, cv2.COLOR_BGR2GRAY)
    
    # Try multiple blur and edge strategies for maximum detection robustness
    edge_candidates = []
    
    # Strategy 1: Bilateral filter + Canny (preserves sharp card edges)
    bilateral = cv2.bilateralFilter(gray, 7, 50, 50)
    edge_candidates.append(cv2.Canny(bilateral, 30, 120))
    
    # Strategy 2: Gaussian Blur + Otsu Thresholding
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, otsu = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    edge_candidates.append(cv2.Canny(otsu, 50, 150))
    
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    best_pts = None
    best_score = -1.0

    for edges in edge_candidates:
        closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=3)
        dilated = cv2.dilate(closed, kernel, iterations=1)

        contours, _ = cv2.findContours(dilated, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)

        for c in contours[:10]:
            area = cv2.contourArea(c)
            if area < min_area or area > max_area:
                continue

            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.025 * peri, True)

            pts = None
            if len(approx) == 4 and cv2.isContourConvex(approx):
                pts = approx.reshape(4, 2)
            else:
                # If 4-point polygon has slightly rounded corners, use minAreaRect
                rect = cv2.minAreaRect(c)
                box = cv2.boxPoints(rect)
                box_area = cv2.contourArea(box)
                if abs(area - box_area) / max(1.0, box_area) < 0.25:
                    pts = box.astype("float32")

            if pts is not None:
                ordered = order_points(pts)
                (tl, tr, br, bl) = ordered
                width_a = np.linalg.norm(br - bl)
                width_b = np.linalg.norm(tr - tl)
                max_width = max(float(width_a), float(width_b))

                height_a = np.linalg.norm(tr - br)
                height_b = np.linalg.norm(tl - bl)
                max_height = max(float(height_a), float(height_b))

                if max_height > 10 and max_width > 10:
                    aspect_ratio = max_width / max_height
                    # ID-1 standard ratio ~1.586 (landscape) or ~0.63 (portrait)
                    if (1.15 <= aspect_ratio <= 2.1) or (0.45 <= aspect_ratio <= 0.85):
                        # Score by area and aspect ratio closeness to 1.586
                        ideal_ratio = 1.586 if aspect_ratio >= 1.0 else (1.0 / 1.586)
                        ratio_diff = abs(aspect_ratio - ideal_ratio)
                        score = area * (1.0 / (1.0 + ratio_diff))
                        if score > best_score:
                            best_score = score
                            best_pts = pts

        if best_pts is not None and best_score > (total_area * 0.3):
            break

    if best_pts is not None and scale != 1.0:
        best_pts = (best_pts / scale).astype("float32")

    return best_pts


def auto_crop_margins(image: np.ndarray, tolerance: int = 25) -> np.ndarray:
    """
    Fallback margin cropper: removes uniform outer borders (scanner glass white/black margins)
    if no perspective polygon could be identified.
    """
    h, w = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Check if border pixels have uniform intensity
    top_edge = np.median(gray[0:max(3, int(h * 0.02)), :])
    bottom_edge = np.median(gray[min(h - 1, int(h * 0.98)):h, :])
    left_edge = np.median(gray[:, 0:max(3, int(w * 0.02))])
    right_edge = np.median(gray[:, min(w - 1, int(w * 0.98)):w])

    avg_border = (top_edge + bottom_edge + left_edge + right_edge) / 4.0
    
    # Mask of pixels significantly different from the background border
    diff = np.abs(gray.astype("float32") - avg_border)
    mask = (diff > tolerance).astype(np.uint8) * 255
    
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))
    mask_closed = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=3)
    
    contours, _ = cv2.findContours(mask_closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        largest = max(contours, key=cv2.contourArea)
        if cv2.contourArea(largest) > (h * w * 0.2):
            x, y, cw, ch = cv2.boundingRect(largest)
            # Inset slightly to avoid border residue
            pad_x = int(cw * 0.01)
            pad_y = int(ch * 0.01)
            x1 = max(0, x + pad_x)
            y1 = max(0, y + pad_y)
            x2 = min(w, x + cw - pad_x)
            y2 = min(h, y + ch - pad_y)
            if (x2 - x1) > 100 and (y2 - y1) > 60:
                return image[y1:y2, x1:x2]

    return image


def detect_and_warp_card(
    image: np.ndarray,
    target_width: int = 1200,
    target_height: int = 760
) -> Tuple[np.ndarray, bool]:
    """
    Corrects perspective distortion by locating the card's 4 corners and warping
    to a canonical ID-1 card size with high resolution.
    Returns: (warped_or_original_image, perspective_corrected_bool)
    """
    card_pts = find_document_contour(image)

    if card_pts is None:
        # Fallback: tightly crop outer borders/scanner background if present
        cropped = auto_crop_margins(image)
        # Resize to standard high resolution if needed
        h, w = cropped.shape[:2]
        if w < 900 or h < 550:
            scale = max(target_width / max(1, w), target_height / max(1, h))
            cropped = cv2.resize(cropped, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_CUBIC)
        return cropped, False

    ordered_pts = order_points(card_pts)
    (tl, tr, br, bl) = ordered_pts

    # Determine whether document is oriented landscape or portrait
    width_a = np.linalg.norm(br - bl)
    width_b = np.linalg.norm(tr - tl)
    max_w = max(float(width_a), float(width_b))

    height_a = np.linalg.norm(tr - br)
    height_b = np.linalg.norm(tl - bl)
    max_h = max(float(height_a), float(height_b))

    # Apply a tiny 0.8% inset on corners to eliminate any outside edge borders/shadows
    center = np.mean(ordered_pts, axis=0)
    ordered_pts_inset = ordered_pts + 0.008 * (center - ordered_pts)

    # If oriented vertically in image, adjust target dimensions accordingly then rotate
    if max_h > max_w:
        dst_pts = np.array([
            [0, 0],
            [target_height - 1, 0],
            [target_height - 1, target_width - 1],
            [0, target_width - 1]
        ], dtype="float32")
        matrix = cv2.getPerspectiveTransform(ordered_pts_inset.astype("float32"), dst_pts)
        warped = cv2.warpPerspective(image, matrix, (target_height, target_width), flags=cv2.INTER_CUBIC)
        # Rotate 90 degrees clockwise to standard landscape orientation
        warped = cv2.rotate(warped, cv2.ROTATE_90_CLOCKWISE)
    else:
        dst_pts = np.array([
            [0, 0],
            [target_width - 1, 0],
            [target_width - 1, target_height - 1],
            [0, target_height - 1]
        ], dtype="float32")
        matrix = cv2.getPerspectiveTransform(ordered_pts_inset.astype("float32"), dst_pts)
        warped = cv2.warpPerspective(image, matrix, (target_width, target_height), flags=cv2.INTER_CUBIC)

    return warped, True
