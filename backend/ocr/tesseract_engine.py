import re
import cv2
import numpy as np
import pytesseract
from pytesseract import Output
from typing import List, Dict, Any, Optional
from backend.ocr.base import BaseOCREngine, OCRResult, OCRLine, OCRWord
from backend.config import TESSERACT_CMD, TESSERACT_LANG, find_tesseract_binary


class TesseractOCREngine(BaseOCREngine):
    def __init__(self, tesseract_cmd: Optional[str] = None, lang: str = TESSERACT_LANG):
        self.cmd = tesseract_cmd or TESSERACT_CMD or find_tesseract_binary()
        self.lang = lang
        if self.cmd:
            pytesseract.pytesseract.tesseract_cmd = self.cmd

    def is_available(self) -> bool:
        cmd = self.cmd or find_tesseract_binary()
        if not cmd:
            return False
        try:
            pytesseract.pytesseract.tesseract_cmd = cmd
            version = pytesseract.get_tesseract_version()
            return version is not None
        except Exception:
            return False

    def extract(self, image: np.ndarray, psm: int = 6) -> OCRResult:
        """
        Runs Tesseract OCR using image_to_data to capture word-level confidence
        and bounding boxes.
        """
        # Ensure Tesseract path is set
        cmd = self.cmd or find_tesseract_binary()
        if cmd:
            pytesseract.pytesseract.tesseract_cmd = cmd
            self.cmd = cmd

        # Configuration for Tesseract
        # psm 6: Assume a single uniform block of text
        # psm 4: Assume a single column of text of variable sizes
        # psm 11: Sparse text. Find as much text as possible in no particular order.
        config_str = f"--oem 3 --psm {psm}"

        try:
            # First try with configured language, fallback to eng if spa is not downloaded
            try:
                data = pytesseract.image_to_data(
                    image,
                    lang=self.lang,
                    config=config_str,
                    output_type=Output.DICT
                )
            except pytesseract.TesseractError:
                # Fallback to English if Spanish language pack is missing
                data = pytesseract.image_to_data(
                    image,
                    lang="eng",
                    config=config_str,
                    output_type=Output.DICT
                )
        except Exception as e:
            # Return empty result on failure
            return OCRResult(
                full_text="",
                lines=[],
                words=[],
                average_confidence=0.0,
                engine_name="Tesseract (Error: " + str(e) + ")"
            )

        words: List[OCRWord] = []
        lines_dict: Dict[int, List[OCRWord]] = {}
        total_conf = 0.0
        valid_words_count = 0

        n_boxes = len(data["text"])
        for i in range(n_boxes):
            text = str(data["text"][i]).strip()
            conf = float(data["conf"][i])

            # Skip empty entries or invalid confidence
            if not text or conf < 0:
                continue

            word = OCRWord(
                text=text,
                left=int(data["left"][i]),
                top=int(data["top"][i]),
                width=int(data["width"][i]),
                height=int(data["height"][i]),
                confidence=conf,
                line_num=int(data["line_num"][i]),
                block_num=int(data["block_num"][i]),
                word_num=int(data["word_num"][i])
            )
            words.append(word)
            total_conf += conf
            valid_words_count += 1

            # Group words by block and line
            line_key = word.block_num * 1000 + word.line_num
            if line_key not in lines_dict:
                lines_dict[line_key] = []
            lines_dict[line_key].append(word)

        # Build lines
        lines: List[OCRLine] = []
        for line_key in sorted(lines_dict.keys()):
            line_words = lines_dict[line_key]
            line_text = " ".join([w.text for w in line_words])
            line_conf = sum([w.confidence for w in line_words]) / len(line_words) if line_words else 0.0
            
            # Compute line bounding box
            min_left = min([w.left for w in line_words])
            min_top = min([w.top for w in line_words])
            max_right = max([w.left + w.width for w in line_words])
            max_bottom = max([w.top + w.height for w in line_words])
            box = (min_left, min_top, max_right - min_left, max_bottom - min_top)

            lines.append(OCRLine(
                words=line_words,
                text=line_text,
                confidence=round(line_conf, 1),
                box=box
            ))

        full_text = "\n".join([line.text for line in lines])
        avg_conf = (total_conf / valid_words_count) if valid_words_count > 0 else 0.0

        return OCRResult(
            full_text=full_text,
            lines=lines,
            words=words,
            average_confidence=round(avg_conf, 1),
            engine_name="Tesseract OCR",
            raw_data=data
        )

    def extract_mrz(self, image: np.ndarray) -> str:
        """
        Specialized OCR for Machine Readable Zone (MRZ) on ID cards.
        Usually located in the bottom 35% of the card reverse.
        """
        h, w = image.shape[:2]
        # Crop bottom 38%
        mrz_crop = image[int(h * 0.62):h, 0:w]

        # Preprocess MRZ region: grayscale, increase contrast, binarize
        if len(mrz_crop.shape) == 3:
            mrz_gray = cv2.cvtColor(mrz_crop, cv2.COLOR_BGR2GRAY)
        else:
            mrz_gray = mrz_crop.copy()

        # Rescale for better OCR accuracy on MRZ monospace font (OCR-B)
        mrz_resized = cv2.resize(mrz_gray, (0, 0), fx=1.8, fy=1.8, interpolation=cv2.INTER_CUBIC)
        _, mrz_bin = cv2.threshold(mrz_resized, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # MRZ uses strict characters: A-Z, 0-9, <
        mrz_config = "--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789<"
        try:
            cmd = self.cmd or find_tesseract_binary()
            if cmd:
                pytesseract.pytesseract.tesseract_cmd = cmd
            mrz_text = pytesseract.image_to_string(mrz_bin, lang="eng", config=mrz_config)
            return mrz_text.strip()
        except Exception:
            return ""
