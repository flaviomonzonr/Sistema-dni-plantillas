import re
import cv2
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from backend.ocr.base import BaseOCREngine, OCRResult, OCRLine, OCRWord
from backend.image_processing.multi_variant_pipeline import MultiVariantResult, ImageVariant


@dataclass
class VariantOCRPass:
    variant_name: str
    description: str
    ocr_result: OCRResult
    mrz_text: str = ""
    quality_score: float = 0.0
    line_count: int = 0
    word_count: int = 0
    avg_confidence: float = 0.0


@dataclass
class MultiVariantConsensusResult:
    primary_ocr: OCRResult
    combined_mrz: str
    passes: List[VariantOCRPass] = field(default_factory=list)
    consensus_agreements: Dict[str, float] = field(default_factory=dict)
    candidate_pools: Dict[str, List[Tuple[str, float, str]]] = field(default_factory=dict)  # field -> [(value, weight, variant_name)]
    total_variants_run: int = 0
    best_variant_name: str = "clahe_enhanced"
    consensus_summary: str = ""


# Common OCR character confusion maps
DIGIT_FROM_CHAR_MAP = {
    "O": "0", "o": "0", "D": "0", "Q": "0",
    "I": "1", "i": "1", "l": "1", "L": "1", "|": "1", "!": "1",
    "Z": "2", "z": "2",
    "E": "3",
    "A": "4",
    "S": "5", "s": "5",
    "G": "6", "b": "6",
    "T": "7",
    "B": "8",
    "g": "9", "q": "9",
}

CHAR_FROM_DIGIT_MAP = {
    "0": "O",
    "1": "I",
    "2": "Z",
    "3": "E",
    "4": "A",
    "5": "S",
    "6": "G",
    "7": "T",
    "8": "B",
    "9": "G",
}


def normalize_numeric_ocr(text: str) -> str:
    """Normalizes OCR misreads in strictly numeric strings (e.g. DNI, dates, ubigeo)."""
    res = []
    for ch in text.strip():
        if ch.isdigit():
            res.append(ch)
        elif ch in DIGIT_FROM_CHAR_MAP:
            res.append(DIGIT_FROM_CHAR_MAP[ch])
    return "".join(res)


def normalize_alpha_ocr(text: str) -> str:
    """Normalizes OCR digit misreads in strictly alphabetic name strings."""
    res = []
    for ch in text.strip().upper():
        if ch.isalpha() or ch in " -'":
            res.append(ch)
        elif ch in CHAR_FROM_DIGIT_MAP:
            res.append(CHAR_FROM_DIGIT_MAP[ch])
    return "".join(res)


class ConsensusEngine:
    """
    Executes multi-attempt OCR across up to 6 specialized OpenCV preprocessed variants.
    Performs field-by-field candidate pool collection, voting, and consensus validation.
    """

    def __init__(self, ocr_engine: BaseOCREngine):
        self.ocr_engine = ocr_engine

    def run_multi_attempt_ocr(
        self,
        variant_result: MultiVariantResult,
        max_variants_to_run: int = 6,
    ) -> MultiVariantConsensusResult:
        """
        Executes OCR on all generated image variants and merges results with consensus scoring.
        """
        passes: List[VariantOCRPass] = []
        mrz_fragments: List[str] = []
        seen_mrz_lines = set()

        variants_to_process = list(variant_result.variants.values())[:max_variants_to_run]
        
        # If warped original is not in variants, ensure it's evaluated
        if not variants_to_process:
            variants_to_process = [
                ImageVariant(
                    name="warped_bgr",
                    description="Imagen Enderezada Original",
                    image=variant_result.warped_bgr,
                    quality_score=variant_result.laplacian_variance,
                )
            ]

        # Prioritize top quality variants for speed and accuracy
        # (clahe_enhanced, shadow_free, adaptive_thresh / otsu_closed)
        top_variants = []
        priority_order = ["clahe_enhanced", "shadow_free", "adaptive_thresh", "otsu_closed"]
        variant_map = {v.name: v for v in variants_to_process}
        for name in priority_order:
            if name in variant_map:
                top_variants.append(variant_map[name])
        if not top_variants:
            top_variants = variants_to_process[:2]
        else:
            top_variants = top_variants[:3]

        found_mrz = False
        for variant in top_variants:
            try:
                ocr_res = self.ocr_engine.extract(variant.image)
            except Exception:
                continue

            # Check if MRZ lines exist in the full text (Line 1: DNI, Line 2: DOB/Sex/Expiry, Line 3: Names)
            mrz_text = ""
            for line in ocr_res.lines:
                t_raw = line.text.strip().upper()
                t_clean = t_raw.replace(" ", "")
                is_mrz_line = (
                    bool(re.search(r"(?:[I1]<PER|[I1]DPER|<PER|PER|[I1]<|[I1]D)<*[0-9A-Z]{8}", t_clean))
                    or bool(re.search(r"[0-9A-Z]{6}<*[0-9A-Z<]?[MF<]", t_clean))
                    or ("PER" in t_clean and any(c.isdigit() for c in t_clean) and len(t_clean) >= 14)
                    or ("<<" in t_clean and len(t_clean) >= 10)
                    or (t_clean.count("<") >= 2 and len(t_clean) >= 10)
                )
                if is_mrz_line:
                    if t_clean not in seen_mrz_lines:
                        mrz_fragments.append(t_raw)
                        seen_mrz_lines.add(t_clean)
                        found_mrz = True

            # If document appears to have MRZ but we have < 3 lines, perform a targeted bottom-strip pass
            if (found_mrz or any("PER" in l.text.upper() for l in ocr_res.lines)) and len(mrz_fragments) < 3:
                try:
                    img_h, img_w = variant.image.shape[:2]
                    if img_h > 100 and img_w > 150:
                        mrz_crop = variant.image[int(img_h * 0.62):img_h, 0:img_w]
                        crop_ocr = self.ocr_engine.extract(mrz_crop)
                        for c_line in crop_ocr.lines:
                            c_raw = c_line.text.strip().upper()
                            c_clean = c_raw.replace(" ", "")
                            if (c_clean.count("<") >= 1 or "PER" in c_clean or "<<" in c_clean) and len(c_clean) >= 8:
                                if c_clean not in seen_mrz_lines:
                                    mrz_fragments.append(c_raw)
                                    seen_mrz_lines.add(c_clean)
                except Exception:
                    pass

            line_cnt = len(ocr_res.lines)
            word_cnt = len(ocr_res.words)
            avg_conf = ocr_res.average_confidence

            pass_obj = VariantOCRPass(
                variant_name=variant.name,
                description=variant.description,
                ocr_result=ocr_res,
                mrz_text=mrz_text,
                quality_score=variant.quality_score,
                line_count=line_cnt,
                word_count=word_cnt,
                avg_confidence=avg_conf,
            )
            passes.append(pass_obj)

            # Early exit inteligente: Si la variante CLAHE principal leyó el DNI o tiene buena confianza (>=70%) y palabras, retornar inmediatamente
            has_dni_candidate = any(re.search(r"\b[0-9OIlLSZB]{8}\b", l.text.upper()) for l in ocr_res.lines)
            if len(passes) >= 1 and (has_dni_candidate or (avg_conf >= 70.0 and word_cnt >= 4)):
                break


        if not passes:
            # Fallback if all attempts failed
            empty_ocr = OCRResult(full_text="", lines=[], words=[], average_confidence=0.0)
            return MultiVariantConsensusResult(
                primary_ocr=empty_ocr,
                combined_mrz="",
                passes=[],
                total_variants_run=0,
                best_variant_name="none",
                consensus_summary="No se obtuvieron resultados en ninguna variante."
            )

        # Select primary OCR pass: highest composite of word count and confidence
        def score_pass(p: VariantOCRPass) -> float:
            base_score = (p.word_count * 2.0) + (p.avg_confidence * 1.5)
            if p.variant_name == "clahe_enhanced":
                base_score += 15.0  # Prefer CLAHE if results are comparable
            return base_score

        best_pass = max(passes, key=score_pass)

        # Synthesize combined MRZ text prioritizing TD1 format
        combined_mrz_str = "\n".join(mrz_fragments)

        # Aggregate candidate pools for cross-pass voting
        candidate_pools: Dict[str, List[Tuple[str, float, str]]] = {
            "dni_candidates": [],
            "names_candidates": [],
            "surnames_candidates": [],
            "dates_candidates": [],
            "ubigeo_candidates": [],
        }

        for p in passes:
            pass_weight = max(1.0, p.avg_confidence / 20.0)
            # Find DNI candidates (8 digits)
            for line in p.ocr_result.lines:
                t = line.text.upper()
                # 8 digit candidates
                matches = re.finditer(r"\b([0-9OIlLSZB]{8})\b", t)
                for m in matches:
                    raw_val = m.group(1)
                    norm_val = normalize_numeric_ocr(raw_val)
                    if len(norm_val) == 8 and norm_val.isdigit():
                        candidate_pools["dni_candidates"].append((norm_val, pass_weight * line.confidence, p.variant_name))

        # Consensus summary
        total_runs = len(passes)
        consensus_summary = f"{total_runs} variantes procesadas con éxito. Variante primaria seleccionada: '{best_pass.description}'."

        return MultiVariantConsensusResult(
            primary_ocr=best_pass.ocr_result,
            combined_mrz=combined_mrz_str,
            passes=passes,
            candidate_pools=candidate_pools,
            total_variants_run=total_runs,
            best_variant_name=best_pass.variant_name,
            consensus_summary=consensus_summary,
        )


def evaluate_field_consensus(
    extracted_val: str,
    candidates: List[Tuple[str, float, str]],
    is_numeric: bool = False,
) -> Tuple[str, float, int, int]:
    """
    Evaluates candidate consensus across multiple passes:
    Returns (winner_value, confidence_boosted, votes_won, total_votes).
    """
    if not candidates:
        return extracted_val, 75.0, 1, 1

    # Group and accumulate weights
    vote_weights: Dict[str, float] = {}
    vote_counts: Dict[str, int] = {}
    total_votes = len(candidates)

    for val, weight, _ in candidates:
        norm_val = normalize_numeric_ocr(val) if is_numeric else val.strip().upper()
        if not norm_val:
            continue
        vote_weights[norm_val] = vote_weights.get(norm_val, 0.0) + weight
        vote_counts[norm_val] = vote_counts.get(norm_val, 0) + 1

    if not vote_weights:
        return extracted_val, 70.0, 1, 1

    winner_val = max(vote_weights, key=vote_weights.get)
    winner_votes = vote_counts[winner_val]
    agreement_ratio = winner_votes / total_votes

    # Confidence calculation based on multi-attempt agreement
    base_conf = min(99.0, 60.0 + (agreement_ratio * 35.0) + (winner_votes * 3.0))

    return winner_val, round(base_conf, 1), winner_votes, total_votes
