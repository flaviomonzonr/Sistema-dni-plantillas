import re
import unicodedata
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from sqlalchemy.orm import Session
from backend.database import ScannedRecord
from backend.services.excel_analyzer import ExcelAnalyzer
from backend.config import MASTER_EXCEL_PATH
from backend.ocr.consensus_engine import normalize_numeric_ocr, DIGIT_FROM_CHAR_MAP


@dataclass
class WorkerMatchResult:
    match_type: str  # "EXACT_MATCH" | "FUZZY_MATCH" | "NOT_FOUND"
    worker_dni: str = ""
    worker_name: str = ""
    confidence: float = 0.0
    is_probable_correction: bool = False
    correction_message: Optional[str] = None
    duplicate_record_id: Optional[int] = None
    duplicate_warning: Optional[str] = None
    excel_data: Optional[Dict[str, Any]] = None
    db_record: Optional[Dict[str, Any]] = None


def levenshtein_distance(s1: str, s2: str) -> int:
    """Computes Levenshtein edit distance between two strings."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def normalize_str(s: str) -> str:
    """Normalizes string for fuzzy name comparisons."""
    if not s:
        return ""
    nfkd = unicodedata.normalize("NFKD", s)
    no_acc = "".join([c for c in nfkd if not unicodedata.combining(c)]).upper().strip()
    return re.sub(r"[^A-Z0-9 ]", "", no_acc)


class WorkerMatcher:
    """
    Intelligent cross-validation and fuzzy matcher against:
    1. Excel master employee roster (`Registros.xlsx` and auxiliary sheets).
    2. SQLite database of prior scans (`ScannedRecord`).
    """

    def __init__(self, excel_analyzer: Optional[ExcelAnalyzer] = None):
        self.excel_analyzer = excel_analyzer or ExcelAnalyzer(MASTER_EXCEL_PATH)

    def find_worker(
        self,
        raw_dni: str,
        first_names: str = "",
        paternal_surname: str = "",
        maternal_surname: str = "",
        db: Optional[Session] = None,
    ) -> WorkerMatchResult:
        """
        Executes exact and fuzzy multi-factor matching for a scanned worker.
        """
        clean_dni = re.sub(r"\D", "", raw_dni or "").strip()
        norm_names = normalize_str(first_names)
        norm_surnames = normalize_str(f"{paternal_surname} {maternal_surname}".strip())

        # 1. Exact DNI check in Excel
        if len(clean_dni) == 8:
            excel_worker = self.excel_analyzer.find_worker_by_dni(clean_dni)
            if excel_worker:
                name = excel_worker.get("full_name") or f"{paternal_surname} {first_names}".strip()
                dup_id, dup_warn = self._check_duplicate(clean_dni, db)
                return WorkerMatchResult(
                    match_type="EXACT_MATCH",
                    worker_dni=clean_dni,
                    worker_name=name,
                    confidence=99.0,
                    is_probable_correction=False,
                    duplicate_record_id=dup_id,
                    duplicate_warning=dup_warn,
                    excel_data=excel_worker,
                )

        # 2. Check OCR Confusion Permutations (e.g. OCR read '4269427I' -> '42694271')
        corrected_dni = normalize_numeric_ocr(raw_dni)
        if corrected_dni and len(corrected_dni) == 8 and corrected_dni != clean_dni:
            excel_worker = self.excel_analyzer.find_worker_by_dni(corrected_dni)
            if excel_worker:
                name = excel_worker.get("full_name") or f"{paternal_surname} {first_names}".strip()
                dup_id, dup_warn = self._check_duplicate(corrected_dni, db)
                return WorkerMatchResult(
                    match_type="FUZZY_MATCH",
                    worker_dni=corrected_dni,
                    worker_name=name,
                    confidence=95.0,
                    is_probable_correction=True,
                    correction_message=f"DNI detectado con corrección probable (OCR: '{raw_dni}' → Base: '{corrected_dni}'). Confirmar.",
                    duplicate_record_id=dup_id,
                    duplicate_warning=dup_warn,
                    excel_data=excel_worker,
                )

        # 3. Fuzzy search against all known workers in Excel (Levenshtein distance <= 2 on DNI or Name match)
        all_workers = self.excel_analyzer.list_all_workers()
        best_candidate = None
        best_score = 0.0

        for w in all_workers:
            w_dni = re.sub(r"\D", "", w.get("dni", ""))
            w_name = normalize_str(w.get("full_name", ""))

            dni_dist = levenshtein_distance(clean_dni or corrected_dni, w_dni) if len(w_dni) == 8 else 99
            
            # If DNI edit distance is 1 (e.g. 1 single digit flipped or dropped)
            if dni_dist == 1:
                score = 85.0
                if norm_surnames and any(s_part in w_name for s_part in norm_surnames.split() if len(s_part) > 2):
                    score += 12.0
                if score > best_score:
                    best_score = score
                    best_candidate = (w, w_dni, f"DNI con 1 dígito de diferencia (OCR: '{clean_dni}' → Base: '{w_dni}').")

            # Or if Surnames and Names match strongly
            elif norm_surnames and norm_names and len(norm_surnames) > 4:
                if norm_surnames in w_name and (norm_names.split()[0] in w_name if norm_names.split() else False):
                    score = 90.0 - (dni_dist * 2.0)
                    if score > best_score:
                        best_score = score
                        best_candidate = (w, w_dni, f"Coincidencia de Nombres en Base (DNI base: '{w_dni}').")

        if best_candidate and best_score >= 80.0:
            cand_worker, cand_dni, cand_msg = best_candidate
            dup_id, dup_warn = self._check_duplicate(cand_dni, db)
            return WorkerMatchResult(
                match_type="FUZZY_MATCH",
                worker_dni=cand_dni,
                worker_name=cand_worker.get("full_name", ""),
                confidence=round(best_score, 1),
                is_probable_correction=True,
                correction_message=f"DNI detectado con corrección probable. {cand_msg} Confirmar.",
                duplicate_record_id=dup_id,
                duplicate_warning=dup_warn,
                excel_data=cand_worker,
            )

        # 4. Check SQLite exact duplicate even if not in master Excel
        if clean_dni and len(clean_dni) == 8 and db:
            dup_id, dup_warn = self._check_duplicate(clean_dni, db)
            if dup_id:
                latest = db.query(ScannedRecord).filter(ScannedRecord.id == dup_id).first()
                if latest:
                    return WorkerMatchResult(
                        match_type="EXACT_MATCH",
                        worker_dni=clean_dni,
                        worker_name=f"{latest.paternal_surname} {latest.first_names}".strip(),
                        confidence=90.0,
                        is_probable_correction=False,
                        duplicate_record_id=dup_id,
                        duplicate_warning=dup_warn,
                        db_record=latest.to_dict(),
                    )

        # 5. Not found
        return WorkerMatchResult(
            match_type="NOT_FOUND",
            worker_dni=clean_dni or raw_dni,
            worker_name=f"{paternal_surname} {first_names}".strip(),
            confidence=50.0 if clean_dni else 0.0,
            is_probable_correction=False,
            duplicate_record_id=None,
            duplicate_warning=None,
        )

    def _check_duplicate(self, dni: str, db: Optional[Session]) -> Tuple[Optional[int], Optional[str]]:
        """Checks if document was already scanned in SQLite database."""
        if not db or not dni:
            return None, None
        try:
            existing = (
                db.query(ScannedRecord)
                .filter(ScannedRecord.doc_number == dni)
                .order_by(ScannedRecord.scan_date.desc())
                .first()
            )
            if existing:
                dt_str = existing.scan_date.strftime("%d/%m/%Y %H:%M") if existing.scan_date else "fecha previa"
                warn = f"Documento posiblemente duplicado: Registrado previamente el {dt_str} (Registro #{existing.id})."
                return existing.id, warn
        except Exception:
            pass
        return None, None
