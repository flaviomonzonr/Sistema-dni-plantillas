import re
import cv2
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from backend.ocr.base import BaseOCREngine, OCRResult, OCRLine, OCRWord


class RapidOCREngine(BaseOCREngine):
    """
    High-performance, standalone OCR engine powered by RapidOCR (ONNX Runtime).
    Does not require external executables or system dependencies.
    """

    def __init__(self):
        self._ocr = None

    def _init_ocr(self):
        if self._ocr is not None:
            return
        try:
            import os
            os.environ.setdefault("OMP_NUM_THREADS", "1")
            os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
            from rapidocr_onnxruntime import RapidOCR
            self._ocr = RapidOCR()
        except Exception as e:
            self._ocr = None

    def is_available(self) -> bool:
        if self._ocr is not None:
            return True
        try:
            import importlib.util
            spec = importlib.util.find_spec("rapidocr_onnxruntime")
            return spec is not None
        except Exception:
            return False

    def warmup(self):
        """Precalienta el motor RapidOCR ejecutando una inferencia dummy."""
        try:
            self._init_ocr()
            if self._ocr is not None:
                dummy = np.zeros((100, 300, 3), dtype=np.uint8)
                self._ocr(dummy)
        except Exception:
            pass


    def extract(self, image: np.ndarray, psm: int = 6) -> OCRResult:
        """
        Runs RapidOCR on an image (BGR or Grayscale) and produces structured
        OCRResult with lines, words, confidences, and bounding boxes.
        """
        if self._ocr is None:
            self._init_ocr()
        if self._ocr is None:
            return OCRResult(
                full_text="",
                lines=[],
                words=[],
                average_confidence=0.0,
                engine_name="RapidOCR (Not Available)"
            )

        # Prepare image for RapidOCR (BGR or RGB) without unnecessary memory copies
        if len(image.shape) == 2:
            img_input = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        else:
            img_input = image

        try:
            results, elapse_list = self._ocr(img_input)
        except Exception as e:
            return OCRResult(
                full_text="",
                lines=[],
                words=[],
                average_confidence=0.0,
                engine_name=f"RapidOCR (Error: {str(e)})"
            )

        if not results:
            return OCRResult(
                full_text="",
                lines=[],
                words=[],
                average_confidence=0.0,
                engine_name="RapidOCR AI",
                raw_data=[]
            )

        words: List[OCRWord] = []
        lines: List[OCRLine] = []
        total_conf = 0.0
        word_count = 0

        # Sort results by vertical position (top-to-bottom) then horizontal (left-to-right)
        sorted_results = sorted(results, key=lambda item: (min(pt[1] for pt in item[0]), min(pt[0] for pt in item[0])))

        for line_idx, item in enumerate(sorted_results):
            # item is: [box_points, text, confidence]
            pts = item[0]
            raw_text = str(item[1]).strip()
            
            # Confidence from RapidOCR is 0.0 - 1.0 (float or string)
            try:
                conf_val = float(item[2]) * 100.0
            except (ValueError, TypeError):
                conf_val = 80.0

            if not raw_text:
                continue

            xs = [pt[0] for pt in pts]
            ys = [pt[1] for pt in pts]
            left = int(min(xs))
            top = int(min(ys))
            width = int(max(xs) - min(xs))
            height = int(max(ys) - min(ys))

            # Split line into words for word-level granularity
            text_tokens = raw_text.split()
            token_width = width // max(1, len(text_tokens))
            line_words: List[OCRWord] = []

            for w_idx, token in enumerate(text_tokens):
                w_left = left + (w_idx * token_width)
                w_obj = OCRWord(
                    text=token,
                    left=w_left,
                    top=top,
                    width=token_width,
                    height=height,
                    confidence=round(conf_val, 1),
                    line_num=line_idx + 1,
                    block_num=1,
                    word_num=w_idx + 1
                )
                words.append(w_obj)
                line_words.append(w_obj)
                total_conf += conf_val
                word_count += 1

            line_obj = OCRLine(
                words=line_words,
                text=raw_text,
                confidence=round(conf_val, 1),
                box=(left, top, width, height)
            )
            lines.append(line_obj)

        full_text = "\n".join([l.text for l in lines])
        avg_conf = (total_conf / word_count) if word_count > 0 else 0.0

        return OCRResult(
            full_text=full_text,
            lines=lines,
            words=words,
            average_confidence=round(avg_conf, 1),
            engine_name="RapidOCR AI",
            raw_data=results
        )

    def extract_mrz(self, image: np.ndarray) -> str:
        """
        Specialized pass for Machine Readable Zone (MRZ) on ID cards.
        Analyzes the bottom region as well as the full image for complete 3-line TD1 MRZ reading.
        """
        if not self.is_available():
            return ""

        h, w = image.shape[:2]
        # Crop bottom 45% of the card
        mrz_crop = image[int(h * 0.55):h, 0:w]
        
        mrz_candidates = []
        seen = set()

        # Run OCR on the bottom crop first
        mrz_result = self.extract(mrz_crop)
        for line in mrz_result.lines:
            raw = line.text.strip().upper()
            clean_l = re.sub(r"[^A-Z0-9<KX]", "", raw)
            if (len(clean_l) >= 10 or "<" in clean_l or clean_l.startswith("I") or clean_l.startswith("P")) and raw not in seen:
                mrz_candidates.append(raw)
                seen.add(raw)

        # If less than 3 lines found, also scan full image
        if len(mrz_candidates) < 3:
            full_res = self.extract(image)
            for line in full_res.lines:
                raw = line.text.strip().upper()
                clean_l = re.sub(r"[^A-Z0-9<KX]", "", raw)
                if (clean_l.startswith("I<PER") or clean_l.startswith("IDPER") or clean_l.startswith("I<") or (len(clean_l) >= 12 and "<" in clean_l)) and raw not in seen:
                    mrz_candidates.append(raw)
                    seen.add(raw)

        return "\n".join(mrz_candidates)
