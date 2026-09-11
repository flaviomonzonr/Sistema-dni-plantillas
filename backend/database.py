import json
from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    Text,
    create_engine,
    text,
)
from sqlalchemy.orm import declarative_base, sessionmaker
from backend.config import DATABASE_URL, get_peru_now

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class ScannedRecord(Base):
    __tablename__ = "scanned_records"

    id = Column(Integer, primary_key=True, index=True)
    scan_date = Column(DateTime, default=get_peru_now, nullable=False)
    doc_type = Column(String(50), nullable=False, index=True)  # "DNI" | "Carnet de Extranjería"
    
    # Core personal data
    paternal_surname = Column(String(100), default="", nullable=True)
    maternal_surname = Column(String(100), default="", nullable=True)
    first_names = Column(String(150), default="", nullable=True)
    doc_number = Column(String(50), default="", nullable=False, index=True)
    nationality = Column(String(50), default="PERUANA", nullable=True)
    birth_date = Column(String(20), default="", nullable=True)
    sex = Column(String(20), default="", nullable=True)
    
    # Address and location
    address = Column(Text, default="", nullable=True)
    ubigeo = Column(String(100), default="", nullable=True)
    
    # Document validity
    issue_date = Column(String(20), default="", nullable=True)
    expiry_date = Column(String(20), default="", nullable=True)
    
    # Optional / Specific fields
    blood_type = Column(String(10), default="", nullable=True)
    civil_status = Column(String(50), default="", nullable=True)
    migratory_status = Column(String(100), default="", nullable=True)

    # Contact & Pension Previsional fields
    phone = Column(String(50), default="999999999", nullable=True)
    email = Column(String(100), default="sincorreo@gmail.com", nullable=True)
    pension_system = Column(String(50), default="", nullable=True)
    pension_commission = Column(String(50), default="", nullable=True)
    cuspp = Column(String(50), default="", nullable=True)
    
    # Notes & observations
    observations = Column(Text, default="", nullable=True)
    
    # Image references
    front_image_orig = Column(String(255), default="", nullable=True)
    front_image_enhanced = Column(String(255), default="", nullable=True)
    back_image_orig = Column(String(255), default="", nullable=True)
    back_image_enhanced = Column(String(255), default="", nullable=True)
    
    # Quality metrics
    quality_score_front = Column(Float, default=0.0)
    quality_score_back = Column(Float, default=0.0)
    is_blurry_front = Column(Boolean, default=False)
    is_blurry_back = Column(Boolean, default=False)
    
    # JSON containing per-field confidence scores (0-100)
    field_confidences = Column(Text, default="{}")

    def to_dict(self):
        confidences = {}
        if self.field_confidences:
            try:
                confidences = json.loads(self.field_confidences)
            except Exception:
                confidences = {}

        return {
            "id": self.id,
            "scan_date": self.scan_date.isoformat() if self.scan_date else "",
            "doc_type": self.doc_type,
            "paternal_surname": self.paternal_surname or "",
            "maternal_surname": self.maternal_surname or "",
            "first_names": self.first_names or "",
            "doc_number": self.doc_number or "",
            "nationality": self.nationality or "",
            "birth_date": self.birth_date or "",
            "sex": self.sex or "",
            "address": self.address or "",
            "ubigeo": self.ubigeo or "",
            "issue_date": self.issue_date or "",
            "expiry_date": self.expiry_date or "",
            "blood_type": self.blood_type or "",
            "civil_status": self.civil_status or "",
            "migratory_status": self.migratory_status or "",
            "phone": self.phone or "999999999",
            "email": self.email or "sincorreo@gmail.com",
            "pension_system": self.pension_system or "",
            "pension_commission": self.pension_commission or "",
            "cuspp": self.cuspp or "",
            "observations": self.observations or "",
            "front_image_orig": self.front_image_orig or "",
            "front_image_enhanced": self.front_image_enhanced or "",
            "back_image_orig": self.back_image_orig or "",
            "back_image_enhanced": self.back_image_enhanced or "",
            "quality_score_front": self.quality_score_front,
            "quality_score_back": self.quality_score_back,
            "is_blurry_front": self.is_blurry_front,
            "is_blurry_back": self.is_blurry_back,
            "field_confidences": confidences,
        }


class GeneratedContractLog(Base):
    __tablename__ = "generated_contracts"

    id = Column(Integer, primary_key=True, index=True)
    dni = Column(String(50), nullable=False, index=True)
    worker_name = Column(String(250), nullable=False, index=True)
    contract_type = Column(String(100), default="SUJETO A MODALIDAD")
    start_date = Column(String(50), default="")
    end_date = Column(String(50), default="")
    duration = Column(String(50), default="")
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size_kb = Column(Float, default=0.0)
    status = Column(String(50), default="GENERADO")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    provenance_summary = Column(Text, default="{}")

    def to_dict(self):
        return {
            "id": self.id,
            "dni": self.dni,
            "worker_name": self.worker_name,
            "contract_type": self.contract_type,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "duration": self.duration,
            "file_name": self.file_name,
            "file_path": self.file_path,
            "file_size_kb": self.file_size_kb,
            "status": self.status,
            "created_at": self.created_at.strftime("%d/%m/%Y %H:%M:%S") if self.created_at else "",
        }


class OCRLearningRecord(Base):
    __tablename__ = "ocr_learning_records"

    id = Column(Integer, primary_key=True, index=True)
    doc_type = Column(String(50), default="DNI")
    doc_subtype = Column(String(100), default="")
    doc_number = Column(String(50), index=True)
    field_name = Column(String(50), nullable=False)
    ocr_raw_value = Column(String(255), default="")
    user_corrected_value = Column(String(255), default="")
    confidence_score = Column(Float, default=0.0)
    image_variant_winner = Column(String(100), default="clahe_enhanced")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "doc_type": self.doc_type,
            "doc_subtype": self.doc_subtype,
            "doc_number": self.doc_number,
            "field_name": self.field_name,
            "ocr_raw_value": self.ocr_raw_value,
            "user_corrected_value": self.user_corrected_value,
            "confidence_score": self.confidence_score,
            "image_variant_winner": self.image_variant_winner,
            "created_at": self.created_at.strftime("%d/%m/%Y %H:%M:%S") if self.created_at else "",
        }


def init_db():
    Base.metadata.create_all(bind=engine)
    # Safe migration for new columns in SQLite
    with engine.connect() as conn:
        for col_name, col_type, default_val in [
            ("phone", "VARCHAR(50)", "'999999999'"),
            ("email", "VARCHAR(100)", "'sincorreo@gmail.com'"),
            ("pension_system", "VARCHAR(50)", "''"),
            ("pension_commission", "VARCHAR(50)", "''"),
            ("cuspp", "VARCHAR(50)", "''"),
        ]:
            try:
                conn.execute(text(f"ALTER TABLE scanned_records ADD COLUMN {col_name} {col_type} DEFAULT {default_val}"))
                conn.commit()
            except Exception:
                pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
