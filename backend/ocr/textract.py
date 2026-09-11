import os
import cv2
import numpy as np
from typing import Optional
from backend.ocr.base import BaseOCREngine, OCRResult, OCRLine, OCRWord


class AWSTextractOCREngine(BaseOCREngine):
    """
    Adapter for AWS Textract (DetectDocumentText / AnalyzeID).
    Ready to use by configuring AWS credentials / boto3.
    """

    def __init__(self, region_name: str = "us-east-1"):
        self.region_name = os.getenv("AWS_DEFAULT_REGION", region_name)

    def is_available(self) -> bool:
        try:
            import boto3
            # Check for AWS credentials in env
            if os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY"):
                return True
            return False
        except ImportError:
            return False

    def extract(self, image: np.ndarray, psm: int = 6) -> OCRResult:
        if not self.is_available():
            raise RuntimeError(
                "AWS Textract no está configurado. Instale 'boto3' y configure "
                "AWS_ACCESS_KEY_ID y AWS_SECRET_ACCESS_KEY."
            )

        import boto3

        success, encoded_img = cv2.imencode(".jpg", image)
        if not success:
            raise ValueError("Error codificando imagen para AWS Textract.")

        client = boto3.client("textract", region_name=self.region_name)
        response = client.detect_document_text(
            Document={"Bytes": encoded_img.tobytes()}
        )

        h, w = image.shape[:2]
        words = []
        lines = []
        total_conf = 0.0
        word_count = 0

        for block in response.get("Blocks", []):
            if block["BlockType"] == "LINE":
                text = block.get("Text", "")
                conf = float(block.get("Confidence", 0.0))
                bb = block.get("Geometry", {}).get("BoundingBox", {})
                box = (
                    int(bb.get("Left", 0) * w),
                    int(bb.get("Top", 0) * h),
                    int(bb.get("Width", 0) * w),
                    int(bb.get("Height", 0) * h),
                )
                lines.append(OCRLine(
                    text=text,
                    confidence=round(conf, 1),
                    box=box
                ))
            elif block["BlockType"] == "WORD":
                text = block.get("Text", "")
                conf = float(block.get("Confidence", 0.0))
                bb = block.get("Geometry", {}).get("BoundingBox", {})
                words.append(OCRWord(
                    text=text,
                    left=int(bb.get("Left", 0) * w),
                    top=int(bb.get("Top", 0) * h),
                    width=int(bb.get("Width", 0) * w),
                    height=int(bb.get("Height", 0) * h),
                    confidence=round(conf, 1)
                ))
                total_conf += conf
                word_count += 1

        full_text = "\n".join([line.text for line in lines])
        avg_conf = (total_conf / word_count) if word_count > 0 else 0.0

        return OCRResult(
            full_text=full_text,
            lines=lines,
            words=words,
            average_confidence=round(avg_conf, 1),
            engine_name="AWS Textract"
        )

    def extract_mrz(self, image: np.ndarray) -> str:
        res = self.extract(image)
        return res.full_text
