from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from backend.database import OCRLearningRecord


class LearningService:
    """
    Manages OCR audit logging and continuous learning tracking when operators
    manually edit or confirm fields that differ from OCR predictions.
    """

    @staticmethod
    def log_corrections(
        db: Session,
        doc_type: str,
        doc_number: str,
        raw_ocr_fields: Dict[str, Any],
        confirmed_fields: Dict[str, Any],
        doc_subtype: str = "DNI Azul Clásico",
        winning_variant: str = "clahe_enhanced",
    ) -> List[OCRLearningRecord]:
        """
        Compares raw OCR values against confirmed values and records discrepancies.
        """
        records_created = []

        for field_name, conf_val in confirmed_fields.items():
            conf_str = str(conf_val or "").strip().upper()
            
            # Extract raw value and confidence from raw_ocr_fields
            raw_meta = raw_ocr_fields.get(field_name)
            raw_str = ""
            conf_score = 80.0

            if isinstance(raw_meta, dict):
                raw_str = str(raw_meta.get("value", "")).strip().upper()
                conf_score = float(raw_meta.get("confidence", 80.0))
            elif isinstance(raw_meta, str):
                raw_str = raw_meta.strip().upper()

            # If user corrected something or if it required validation
            if conf_str and raw_str and conf_str != raw_str:
                rec = OCRLearningRecord(
                    doc_type=doc_type,
                    doc_subtype=doc_subtype,
                    doc_number=doc_number,
                    field_name=field_name,
                    ocr_raw_value=raw_str,
                    user_corrected_value=conf_str,
                    confidence_score=conf_score,
                    image_variant_winner=winning_variant,
                    created_at=datetime.utcnow(),
                )
                db.add(rec)
                records_created.append(rec)

        if records_created:
            db.commit()

        return records_created

    @staticmethod
    def get_learning_stats(db: Session) -> Dict[str, Any]:
        """Returns summary metrics on OCR accuracy and top corrected fields."""
        total_corrections = db.query(OCRLearningRecord).count()
        recent_logs = (
            db.query(OCRLearningRecord)
            .order_by(OCRLearningRecord.created_at.desc())
            .limit(50)
            .all()
        )
        return {
            "total_corrections_logged": total_corrections,
            "recent_records": [l.to_dict() for l in recent_logs],
        }
