import os
import cv2
import numpy as np
from typing import Optional
from backend.ocr.base import BaseOCREngine, OCRResult, OCRLine, OCRWord


class CloudVisionOCREngine(BaseOCREngine):
    """
    Adapter for Google Cloud Vision API (DOCUMENT_TEXT_DETECTION).
    Ready to use by setting GOOGLE_APPLICATION_CREDENTIALS or Vision client.
    """

    def __init__(self, credentials_path: Optional[str] = None):
        self.credentials_path = credentials_path or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

    def is_available(self) -> bool:
        if not self.credentials_path or not os.path.exists(self.credentials_path):
            return False
        try:
            from google.cloud import vision
            return True
        except ImportError:
            return False

    def extract(self, image: np.ndarray, psm: int = 6) -> OCRResult:
        """
        Executes Google Cloud Vision Document Text Detection if credentials are provided.
        """
        if not self.is_available():
            raise RuntimeError(
                "Google Cloud Vision API no está configurado. Instale 'google-cloud-vision' "
                "y configure la variable de entorno GOOGLE_APPLICATION_CREDENTIALS."
            )

        from google.cloud import vision

        success, encoded_img = cv2.imencode(".jpg", image)
        if not success:
            raise ValueError("Error codificando imagen para Cloud Vision.")

        client = vision.ImageAnnotatorClient()
        image_obj = vision.Image(content=encoded_img.tobytes())
        response = client.document_text_detection(image=image_obj)

        if response.error.message:
            raise RuntimeError(f"Cloud Vision API Error: {response.error.message}")

        words = []
        lines = []
        total_conf = 0.0
        word_count = 0

        for page in response.full_text_annotation.pages:
            for block in page.blocks:
                for paragraph in block.paragraphs:
                    line_words = []
                    for word in paragraph.words:
                        word_text = "".join([s.text for s in word.symbols])
                        conf = float(word.confidence * 100.0)
                        
                        # Bounding box
                        v = word.bounding_box.vertices
                        left = v[0].x if v else 0
                        top = v[0].y if v else 0
                        right = v[1].x if len(v) > 1 else left
                        bottom = v[2].y if len(v) > 2 else top

                        ocr_w = OCRWord(
                            text=word_text,
                            left=left,
                            top=top,
                            width=max(0, right - left),
                            height=max(0, bottom - top),
                            confidence=round(conf, 1)
                        )
                        words.append(ocr_w)
                        line_words.append(ocr_w)
                        total_conf += conf
                        word_count += 1

                    if line_words:
                        line_text = " ".join([w.text for w in line_words])
                        line_conf = sum([w.confidence for w in line_words]) / len(line_words)
                        lines.append(OCRLine(
                            words=line_words,
                            text=line_text,
                            confidence=round(line_conf, 1)
                        ))

        full_text = response.full_text_annotation.text
        avg_conf = (total_conf / word_count) if word_count > 0 else 0.0

        return OCRResult(
            full_text=full_text,
            lines=lines,
            words=words,
            average_confidence=round(avg_conf, 1),
            engine_name="Google Cloud Vision"
        )

    def extract_mrz(self, image: np.ndarray) -> str:
        res = self.extract(image)
        return res.full_text
