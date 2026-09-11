from abc import ABC, abstractmethod
from typing import List, Tuple, Dict, Any, Optional
from dataclasses import dataclass, field
import numpy as np


@dataclass
class OCRWord:
    text: str
    left: int
    top: int
    width: int
    height: int
    confidence: float  # 0.0 to 100.0
    line_num: int = 0
    block_num: int = 0
    word_num: int = 0


@dataclass
class OCRLine:
    words: List[OCRWord] = field(default_factory=list)
    text: str = ""
    confidence: float = 0.0
    box: Tuple[int, int, int, int] = (0, 0, 0, 0)  # left, top, width, height


@dataclass
class OCRResult:
    full_text: str = ""
    lines: List[OCRLine] = field(default_factory=list)
    words: List[OCRWord] = field(default_factory=list)
    average_confidence: float = 0.0
    engine_name: str = "Tesseract"
    raw_data: Optional[Dict[str, Any]] = None


class BaseOCREngine(ABC):
    """Abstract interface for pluggable OCR engines (Tesseract, Cloud Vision, Textract)."""

    @abstractmethod
    def is_available(self) -> bool:
        """Returns True if the OCR engine is configured and operational."""
        pass

    @abstractmethod
    def extract(self, image: np.ndarray, psm: int = 6) -> OCRResult:
        """
        Executes OCR on an image matrix (BGR or grayscale) and returns
        structured OCRResult with words, bounding boxes, and confidence levels.
        """
        pass

    @abstractmethod
    def extract_mrz(self, image: np.ndarray) -> str:
        """Specialized pass for Machine Readable Zone (MRZ)."""
        pass
