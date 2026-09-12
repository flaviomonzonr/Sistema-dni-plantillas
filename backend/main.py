import sys
from pathlib import Path

# Ensure project root is in sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import os
import re
import concurrent.futures
from datetime import datetime, date, timezone
from typing import Optional, List, Dict, Any, Tuple, Union
import json
import zipfile

from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc, func

from backend.config import (
    UPLOADS_DIR,
    EXPORTS_DIR,
    CONTRACTS_DIR,
    TEMPLATES_DIR,
    MASTER_EXCEL_PATH,
    BLUR_THRESHOLD,
    find_tesseract_binary,
    OCR_ENGINE,
    get_peru_now,
    PERU_TZ,
)
from backend.database import init_db, get_db, ScannedRecord, GeneratedContractLog
from backend.schemas import (
    ScanResponse,
    RecordCreate,
    RecordResponse,
    PaginatedRecordsResponse,
    StatsResponse,
    QualityMetric,
    FieldConfidence,
    WorkerProfileResponse,
    CalculateDatesRequest,
    ContractGenerateRequest,
    BatchContractGenerateRequest,
    ContractLogResponse,
)
from backend.image_processing.multi_variant_pipeline import generate_multi_variants
from backend.image_processing.classifier import classify_document
from backend.ocr import get_ocr_engine
from backend.ocr.consensus_engine import ConsensusEngine
from backend.extractors import extract_dni_data, extract_ce_data
from backend.storage.file_manager import save_image_matrix
from backend.storage.excel_manager import append_record_to_excel, generate_filtered_excel
from backend.services import (
    ExcelAnalyzer,
    WorkerConsolidator,
    ContractGenerator,
    ExcelTemplateService,
    backup_service,
    supabase_template_service,
)
from backend.services.worker_matcher import WorkerMatcher
from backend.services.learning_service import LearningService


app = FastAPI(
    title="Sistema de Escaneo de DNI y Carnet de Extranjería - Perú",
    description="Backend API con OpenCV, Tesseract OCR, SQLite y exportación incremental a Excel.",
    version="1.0.0",
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount uploads directory for static image serving
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")


@app.on_event("startup")
def on_startup():
    init_db()



# Global service instances
excel_analyzer = ExcelAnalyzer(MASTER_EXCEL_PATH)
worker_matcher = WorkerMatcher(excel_analyzer)
worker_consolidator = WorkerConsolidator(MASTER_EXCEL_PATH)
contract_generator = ContractGenerator(TEMPLATES_DIR, CONTRACTS_DIR)
excel_template_service = ExcelTemplateService()


@app.get("/")
def root():
    return {
        "system": "EscanDNI Perú - Backend API",
        "status": "online",
        "frontend_url": "http://localhost:5173",
        "docs_url": "/docs",
        "message": "El servidor Backend está funcionando correctamente. Para usar la interfaz gráfica abre http://localhost:5173 en tu navegador.",
    }


@app.get("/api/health")
def health_check():
    tesseract_path = find_tesseract_binary()
    ocr_engine = get_ocr_engine()
    ocr_ok = ocr_engine.is_available()
    engine_label = "RapidOCR AI" if "Rapid" in ocr_engine.__class__.__name__ else ocr_engine.__class__.__name__.replace("OCREngine", "")

    backup_info = backup_service.get_backup_status()

    return {
        "status": "healthy" if ocr_ok else "degraded",
        "ocr_engine": engine_label,
        "ocr_available": ocr_ok,
        "tesseract_installed": tesseract_path is not None,
        "tesseract_path": tesseract_path,
        "blur_threshold": BLUR_THRESHOLD,
        "master_excel_exists": MASTER_EXCEL_PATH.exists(),
        "backup": backup_info,
    }


@app.get("/api/backups/status")
def get_backups_status():
    """Retorna el estado de copias de seguridad y persistencia de datos."""
    return backup_service.get_backup_status()


@app.post("/api/backups/create")
def create_manual_backup():
    """Crea una copia de seguridad manual inmediata de records.db y Registros.xlsx."""
    res = backup_service.create_backup("manual_trigger")
    return res


@app.get("/api/backups/download-zip")
def download_full_backup_zip():
    """Descarga un archivo .ZIP completo con records.db, Registros.xlsx y todas las plantillas."""
    zip_path = backup_service.create_full_zip_package()
    if not zip_path.exists():
        raise HTTPException(status_code=500, detail="No se pudo empaquetar el archivo de respaldo.")
    return FileResponse(
        path=str(zip_path),
        filename=zip_path.name,
        media_type="application/zip",
    )



@app.post("/api/scan", response_model=ScanResponse)
def scan_document(
    front_image: UploadFile = File(...),
    back_image: Optional[UploadFile] = File(None),
    doc_type: str = Form("DNI"),
    db: Session = Depends(get_db),
):
    """
    Motor OCR Multi-Intento Ultrarrápido con Consenso Ponderado y Procesamiento Paralelo:
    1. Preprocesamiento OpenCV Multi-Variante en paralelo para Anverso y Reverso.
    2. Clasificación automática de documento y detección de caras.
    3. Ejecución concurrente de OCR Multi-Intento con matriz de confusión y votación de consenso.
    4. Extracción semántica por anclas y proximidad (cero coordenadas fijas).
    5. Búsqueda inteligente en base Excel / SQLite con corrección difusa y detección de duplicados.
    """
    # Read image bytes synchronously
    front_bytes = front_image.file.read()
    back_bytes = back_image.file.read() if back_image else None

    if not front_bytes:
        raise HTTPException(
            status_code=400,
            detail="Debe proporcionar al menos la imagen del anverso del documento.",
        )

    # 1. Generate Multi-Variants with OpenCV in parallel for Front and Back
    try:
        if back_bytes:
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                f_future = executor.submit(generate_multi_variants, front_bytes)
                b_future = executor.submit(generate_multi_variants, back_bytes)
                front_variants_res = f_future.result()
                back_variants_res = b_future.result()
        else:
            front_variants_res = generate_multi_variants(front_bytes)
            back_variants_res = None
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error durante el preprocesamiento de la imagen con OpenCV: {str(e)}",
        )

    # Save images
    front_orig_fn = save_image_matrix(front_variants_res.original_bgr, "front_orig")
    front_enh_fn = save_image_matrix(
        front_variants_res.variants.get("clahe_enhanced", list(front_variants_res.variants.values())[0]).image,
        "front_enhanced"
    )
    front_orig_url = f"/uploads/{front_orig_fn}"
    front_enh_url = f"/uploads/{front_enh_fn}"

    back_orig_url = ""
    back_enh_url = ""
    if back_variants_res:
        back_orig_fn = save_image_matrix(back_variants_res.original_bgr, "back_orig")
        back_enh_fn = save_image_matrix(
            back_variants_res.variants.get("clahe_enhanced", list(back_variants_res.variants.values())[0]).image,
            "back_enhanced"
        )
        back_orig_url = f"/uploads/{back_orig_fn}"
        back_enh_url = f"/uploads/{back_enh_fn}"

    # 2. Multi-Attempt OCR with Consensus Engine in parallel for Front and Back
    ocr_engine = get_ocr_engine()
    consensus_engine = ConsensusEngine(ocr_engine)

    if back_variants_res:
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            f_ocr_fut = executor.submit(consensus_engine.run_multi_attempt_ocr, front_variants_res)
            b_ocr_fut = executor.submit(consensus_engine.run_multi_attempt_ocr, back_variants_res)
            front_consensus = f_ocr_fut.result()
            back_consensus = b_ocr_fut.result()
    else:
        front_consensus = consensus_engine.run_multi_attempt_ocr(front_variants_res)
        back_consensus = None

    combined_mrz = (
        (front_consensus.combined_mrz or "") + "\n" + ((back_consensus.combined_mrz if back_consensus else "") or "")
    ).strip()

    # 3. Document Classification & Side Detection (100% Automático)
    front_classif = classify_document(
        image_bgr=front_variants_res.original_bgr,
        ocr_text=front_consensus.primary_ocr.full_text,
        declared_type=doc_type if doc_type != "AUTO" else "DNI",
    )
    back_classif = classify_document(
        image_bgr=back_variants_res.original_bgr,
        ocr_text=back_consensus.primary_ocr.full_text if back_consensus else "",
        declared_type=doc_type if doc_type != "AUTO" else "DNI",
    ) if back_variants_res else None

    # Automatic detection takes precedence
    if doc_type in ["AUTO", "", None] or front_classif.confidence >= 55:
        effective_doc_type = front_classif.doc_type
    else:
        effective_doc_type = doc_type or front_classif.doc_type

    doc_subtype = front_classif.doc_subtype

    # Merge Candidate Pools across front and back
    merged_candidate_pools = dict(front_consensus.candidate_pools)
    if back_consensus:
        for k, v in back_consensus.candidate_pools.items():
            merged_candidate_pools.setdefault(k, []).extend(v)

    # 4. Semantic Extraction
    all_warnings = []
    if front_variants_res.is_blurry:
        all_warnings.append(f"Anverso: {front_variants_res.quality_message}")
    if back_variants_res and back_variants_res.is_blurry:
        all_warnings.append(f"Reverso: {back_variants_res.quality_message}")

    if effective_doc_type in ["DNI", "DNI Electrónico"]:
        extracted_dict, fields_dict, doc_warnings = extract_dni_data(
            front_ocr=front_consensus.primary_ocr,
            back_ocr=back_consensus.primary_ocr if back_consensus else None,
            mrz_text=combined_mrz,
            candidate_pools=merged_candidate_pools,
        )
    else:
        extracted_dict, fields_dict, doc_warnings = extract_ce_data(
            front_ocr=front_consensus.primary_ocr,
            back_ocr=back_consensus.primary_ocr if back_consensus else None,
            mrz_text=combined_mrz,
            candidate_pools=merged_candidate_pools,
        )

    all_warnings.extend(doc_warnings)

    # 5. Worker Matcher & Duplicate Detection
    extracted_dni = extracted_dict.get("doc_number", "")
    first_names = extracted_dict.get("first_names", "")
    pat_surname = extracted_dict.get("paternal_surname", "")
    mat_surname = extracted_dict.get("maternal_surname", "")

    match_res = worker_matcher.find_worker(
        raw_dni=extracted_dni,
        first_names=first_names,
        paternal_surname=pat_surname,
        maternal_surname=mat_surname,
        db=db,
    )

    if match_res.duplicate_warning:
        all_warnings.append(match_res.duplicate_warning)

    if match_res.is_probable_correction and match_res.correction_message:
        all_warnings.append(match_res.correction_message)
        # Add candidate proposal to doc_number field
        if "doc_number" in fields_dict:
            fields_dict["doc_number"].status = "REVISAR"
            fields_dict["doc_number"].validation_message = match_res.correction_message
            fields_dict["doc_number"].origin_type = "CORREGIDO_PROBABLE"

    # Quality Metrics
    qm_front = QualityMetric(
        laplacian_var=front_variants_res.laplacian_variance,
        is_blurry=front_variants_res.is_blurry,
        quality_message=front_variants_res.quality_message,
        perspective_corrected=front_variants_res.perspective_corrected,
        original_size=[int(front_variants_res.original_bgr.shape[1]), int(front_variants_res.original_bgr.shape[0])],
        processed_size=[int(front_variants_res.variants.get("clahe_enhanced", list(front_variants_res.variants.values())[0]).image.shape[1]), int(front_variants_res.variants.get("clahe_enhanced", list(front_variants_res.variants.values())[0]).image.shape[0])],
    )
    qm_back = None
    if back_variants_res:
        qm_back = QualityMetric(
            laplacian_var=back_variants_res.laplacian_variance,
            is_blurry=back_variants_res.is_blurry,
            quality_message=back_variants_res.quality_message,
            perspective_corrected=back_variants_res.perspective_corrected,
            original_size=[int(back_variants_res.original_bgr.shape[1]), int(back_variants_res.original_bgr.shape[0])],
            processed_size=[int(back_variants_res.variants.get("clahe_enhanced", list(back_variants_res.variants.values())[0]).image.shape[1]), int(back_variants_res.variants.get("clahe_enhanced", list(back_variants_res.variants.values())[0]).image.shape[0])],
        )

    return ScanResponse(
        success=True,
        doc_type=effective_doc_type,
        doc_subtype=doc_subtype,
        detected_side_front=front_classif.side,
        detected_side_back=back_classif.side if back_classif else None,
        paternal_surname=extracted_dict.get("paternal_surname", ""),
        maternal_surname=extracted_dict.get("maternal_surname", ""),
        first_names=extracted_dict.get("first_names", ""),
        doc_number=extracted_dict.get("doc_number", ""),
        nationality=extracted_dict.get("nationality", "PERUANA"),
        birth_date=extracted_dict.get("birth_date", ""),
        sex=extracted_dict.get("sex", ""),
        address=extracted_dict.get("address", ""),
        ubigeo=extracted_dict.get("ubigeo", ""),
        issue_date=extracted_dict.get("issue_date", ""),
        expiry_date=extracted_dict.get("expiry_date", ""),
        blood_type=extracted_dict.get("blood_type", ""),
        civil_status=extracted_dict.get("civil_status", ""),
        migratory_status=extracted_dict.get("migratory_status", ""),
        phone="999999999",
        email="sincorreo@gmail.com",
        pension_system="",
        pension_commission="",
        cuspp="",
        observations=extracted_dict.get("observations", ""),
        fields=fields_dict,
        quality_front=qm_front,
        quality_back=qm_back,
        front_image_orig=front_orig_url,
        front_image_enhanced=front_enh_url,
        back_image_orig=back_orig_url,
        back_image_enhanced=back_enh_url,
        duplicate_warning=match_res.duplicate_warning,
        worker_match_status=match_res.match_type,
        matched_worker_name=match_res.worker_name,
        matched_worker_dni=match_res.worker_dni,
        warnings=all_warnings,
    )


@app.post("/api/records", response_model=RecordResponse)
def create_record(record_in: RecordCreate, db: Session = Depends(get_db)):
    """
    Guarda el registro confirmado/editado en SQLite, actualiza Registros.xlsx
    y audita las correcciones en el log de aprendizaje continuo.
    """
    now = get_peru_now()
    confidences_json = json.dumps(record_in.field_confidences or {})

    db_record = ScannedRecord(
        scan_date=now,
        doc_type=record_in.doc_type,
        paternal_surname=record_in.paternal_surname.strip().upper(),
        maternal_surname=record_in.maternal_surname.strip().upper(),
        first_names=record_in.first_names.strip().upper(),
        doc_number=record_in.doc_number.strip().upper(),
        nationality=record_in.nationality.strip().upper() or ("PERUANA" if record_in.doc_type == "DNI" else ""),
        birth_date=record_in.birth_date.strip(),
        sex=record_in.sex.strip().upper(),
        address=record_in.address.strip(),
        ubigeo=record_in.ubigeo.strip(),
        issue_date=record_in.issue_date.strip(),
        expiry_date=record_in.expiry_date.strip(),
        blood_type=record_in.blood_type.strip(),
        civil_status=record_in.civil_status.strip(),
        migratory_status=record_in.migratory_status.strip(),
        phone=(record_in.phone or "999999999").strip(),
        email=(record_in.email or "sincorreo@gmail.com").strip(),
        pension_system=(record_in.pension_system or "").strip().upper(),
        pension_commission=(record_in.pension_commission or "").strip().upper(),
        cuspp=(record_in.cuspp or "").strip().upper(),
        observations=record_in.observations.strip(),
        front_image_orig=record_in.front_image_orig or "",
        front_image_enhanced=record_in.front_image_enhanced or "",
        back_image_orig=record_in.back_image_orig or "",
        back_image_enhanced=record_in.back_image_enhanced or "",
        quality_score_front=record_in.quality_score_front,
        quality_score_back=record_in.quality_score_back,
        is_blurry_front=record_in.is_blurry_front,
        is_blurry_back=record_in.is_blurry_back,
        field_confidences=confidences_json,
    )

    db.add(db_record)
    db.commit()
    db.refresh(db_record)

    # Log user corrections for continuous learning
    if record_in.field_confidences:
        confirmed_map = {
            "doc_number": record_in.doc_number,
            "paternal_surname": record_in.paternal_surname,
            "maternal_surname": record_in.maternal_surname,
            "first_names": record_in.first_names,
            "birth_date": record_in.birth_date,
            "sex": record_in.sex,
            "address": record_in.address,
            "ubigeo": record_in.ubigeo,
            "issue_date": record_in.issue_date,
            "expiry_date": record_in.expiry_date,
        }
        try:
            LearningService.log_corrections(
                db=db,
                doc_type=record_in.doc_type,
                doc_number=record_in.doc_number,
                raw_ocr_fields=record_in.field_confidences,
                confirmed_fields=confirmed_map,
            )
        except Exception as e:
            print(f"Warning: No se pudo registrar log de aprendizaje: {e}")

    # Append to Master Excel file
    try:
        append_record_to_excel(db_record.to_dict())
    except Exception as e:
        print(f"Warning: No se pudo agregar al Excel maestro: {e}")

    # Auto backup to ensure permanent persistence and recovery point
    try:
        backup_service.create_backup("record_saved")
    except Exception as e:
        print(f"Warning: No se pudo generar copia de seguridad automática: {e}")

    return RecordResponse(**db_record.to_dict())



@app.post("/api/scan-and-save")
def scan_and_save_document(
    front_image: UploadFile = File(...),
    back_image: Optional[UploadFile] = File(None),
    doc_type: str = Form("DNI"),
    db: Session = Depends(get_db),
):
    """
    Escaneo y guardado atómico para procesamiento por lote de DNI:
    1. Ejecuta el recorte y lectura OCR con OpenCV y RapidOCR AI.
    2. Guarda de forma automática el registro en SQLite (ScannedRecord).
    3. Agrega el registro en Registros.xlsx.
    4. Retorna el resultado escaneado y el registro persistido con su ID.
    """
    # 1. Ejecutar escaneo
    scan_res = scan_document(
        front_image=front_image,
        back_image=back_image,
        doc_type=doc_type,
        db=db
    )

    # 2. Preparar confianzas de campos
    field_confs = {}
    for f_name, f_val in scan_res.fields.items():
        if hasattr(f_val, 'model_dump'):
            field_confs[f_name] = f_val.model_dump()
        elif hasattr(f_val, 'dict'):
            field_confs[f_name] = f_val.dict()
        elif isinstance(f_val, dict):
            field_confs[f_name] = f_val

    record_in = RecordCreate(
        doc_type=scan_res.doc_type,
        paternal_surname=scan_res.paternal_surname,
        maternal_surname=scan_res.maternal_surname,
        first_names=scan_res.first_names,
        doc_number=scan_res.doc_number,
        nationality=scan_res.nationality,
        birth_date=scan_res.birth_date,
        sex=scan_res.sex,
        address=scan_res.address,
        ubigeo=scan_res.ubigeo,
        issue_date=scan_res.issue_date,
        expiry_date=scan_res.expiry_date,
        blood_type=scan_res.blood_type,
        civil_status=scan_res.civil_status,
        migratory_status=scan_res.migratory_status,
        phone=scan_res.phone or "999999999",
        email=scan_res.email or "sincorreo@gmail.com",
        pension_system=scan_res.pension_system or "",
        pension_commission=scan_res.pension_commission or "",
        cuspp=scan_res.cuspp or "",
        observations=scan_res.observations,
        front_image_orig=scan_res.front_image_orig,
        front_image_enhanced=scan_res.front_image_enhanced,
        back_image_orig=scan_res.back_image_orig,
        back_image_enhanced=scan_res.back_image_enhanced,
        quality_score_front=scan_res.quality_front.laplacian_var if scan_res.quality_front else None,
        quality_score_back=scan_res.quality_back.laplacian_var if scan_res.quality_back else None,
        is_blurry_front=scan_res.quality_front.is_blurry if scan_res.quality_front else False,
        is_blurry_back=scan_res.quality_back.is_blurry if scan_res.quality_back else False,
        field_confidences=field_confs,
    )

    created_record = create_record(record_in=record_in, db=db)
    record_dict = created_record.model_dump() if hasattr(created_record, 'model_dump') else created_record.dict()
    scan_dict = scan_res.model_dump() if hasattr(scan_res, 'model_dump') else scan_res.dict()

    return {
        "success": True,
        "record": record_dict,
        "scan_data": scan_dict,
    }



@app.post("/api/ocr/diagnostic")
async def get_ocr_diagnostic(
    image: UploadFile = File(...),
    doc_type: str = Form("DNI"),
):
    """
    Panel técnico/diagnóstico: ejecuta el pipeline multi-variante y retorna
    la inspección visual de las 6 variantes, resultados de cada pasada OCR y consenso.
    """
    img_bytes = await image.read()
    if not img_bytes:
        raise HTTPException(status_code=400, detail="Imagen inválida")

    var_res = generate_multi_variants(img_bytes)
    ocr_engine = get_ocr_engine()
    consensus_engine = ConsensusEngine(ocr_engine)
    cons_res = consensus_engine.run_multi_attempt_ocr(var_res)

    classif = classify_document(
        image_bgr=var_res.original_bgr,
        ocr_text=cons_res.primary_ocr.full_text,
        declared_type=doc_type,
    )

    passes_summary = []
    for p in cons_res.passes:
        # Save temporary thumbnail of variant
        fn = save_image_matrix(p.ocr_result.raw_data if hasattr(p, 'image') else var_res.variants[p.variant_name].image, f"diag_{p.variant_name}")
        passes_summary.append({
            "variant_name": p.variant_name,
            "description": p.description,
            "image_url": f"/uploads/{fn}",
            "quality_score": p.quality_score,
            "line_count": p.line_count,
            "word_count": p.word_count,
            "avg_confidence": p.avg_confidence,
            "full_text_sample": p.ocr_result.full_text[:300],
            "mrz_detected": bool(p.mrz_text),
        })

    return {
        "success": True,
        "classification": {
            "doc_type": classif.doc_type,
            "doc_subtype": classif.doc_subtype,
            "side": classif.side,
            "confidence": classif.confidence,
            "detected_features": classif.detected_features,
            "has_mrz": classif.has_mrz,
            "has_photo": classif.has_photo,
        },
        "quality_metrics": {
            "laplacian_variance": var_res.laplacian_variance,
            "is_blurry": var_res.is_blurry,
            "has_shadows": var_res.has_shadows,
            "has_glare": var_res.has_glare,
            "perspective_corrected": var_res.perspective_corrected,
            "quality_message": var_res.quality_message,
        },
        "consensus": {
            "total_variants_run": cons_res.total_variants_run,
            "best_variant_name": cons_res.best_variant_name,
            "summary": cons_res.consensus_summary,
            "candidate_pools": cons_res.candidate_pools,
            "passes": passes_summary,
        }
    }


@app.get("/api/ocr/learning-stats")
def get_ocr_learning_stats(db: Session = Depends(get_db)):
    """Retorna métricas de aprendizaje continuo y campos más corregidos por operadores."""
    return LearningService.get_learning_stats(db)


@app.get("/api/records", response_model=PaginatedRecordsResponse)
def list_records(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    doc_type: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Lists scanned records with search, filter, and pagination."""
    query = db.query(ScannedRecord)

    if doc_type and doc_type in ["DNI", "Carnet de Extranjería"]:
        query = query.filter(ScannedRecord.doc_type == doc_type)

    if search:
        s = f"%{search.strip()}%"
        query = query.filter(
            or_(
                ScannedRecord.doc_number.ilike(s),
                ScannedRecord.paternal_surname.ilike(s),
                ScannedRecord.maternal_surname.ilike(s),
                ScannedRecord.first_names.ilike(s),
                ScannedRecord.address.ilike(s),
            )
        )

    if start_date:
        try:
            dt_start = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.filter(ScannedRecord.scan_date >= dt_start)
        except ValueError:
            pass

    if end_date:
        try:
            dt_end = datetime.strptime(f"{end_date} 23:59:59", "%Y-%m-%d %H:%M:%S")
            query = query.filter(ScannedRecord.scan_date <= dt_end)
        except ValueError:
            pass

    total = query.count()
    items = (
        query.order_by(desc(ScannedRecord.scan_date))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return PaginatedRecordsResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[RecordResponse(**item.to_dict()) for item in items],
    )


@app.get("/api/records/stats", response_model=StatsResponse)
def get_stats(db: Session = Depends(get_db)):
    """Summary metrics for the dashboard."""
    total = db.query(ScannedRecord).count()
    dni_cnt = db.query(ScannedRecord).filter(ScannedRecord.doc_type == "DNI").count()
    ce_cnt = db.query(ScannedRecord).filter(ScannedRecord.doc_type == "Carnet de Extranjería").count()
    
    today_start = datetime.combine(date.today(), datetime.min.time())
    today_cnt = db.query(ScannedRecord).filter(ScannedRecord.scan_date >= today_start).count()

    return StatsResponse(
        total_records=total,
        dni_count=dni_cnt,
        ce_count=ce_cnt,
        scanned_today=today_cnt,
    )


@app.get("/api/records/{record_id}", response_model=RecordResponse)
def get_record(record_id: int, db: Session = Depends(get_db)):
    """Retrieves a single record by ID."""
    rec = db.query(ScannedRecord).filter(ScannedRecord.id == record_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    return RecordResponse(**rec.to_dict())


@app.delete("/api/records/{record_id}")
def delete_record(record_id: int, db: Session = Depends(get_db)):
    """Deletes a record from SQLite database."""
    rec = db.query(ScannedRecord).filter(ScannedRecord.id == record_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    db.delete(rec)
    db.commit()
    return {"success": True, "message": f"Registro #{record_id} eliminado exitosamente."}


@app.get("/api/export-excel")
def export_excel(
    search: Optional[str] = Query(None),
    doc_type: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Downloads either the full master Registros.xlsx or a dynamically filtered export.
    """
    query = db.query(ScannedRecord)

    is_filtered = bool(search or doc_type or start_date or end_date)

    if doc_type and doc_type in ["DNI", "Carnet de Extranjería"]:
        query = query.filter(ScannedRecord.doc_type == doc_type)

    if search:
        s = f"%{search.strip()}%"
        query = query.filter(
            or_(
                ScannedRecord.doc_number.ilike(s),
                ScannedRecord.paternal_surname.ilike(s),
                ScannedRecord.maternal_surname.ilike(s),
                ScannedRecord.first_names.ilike(s),
            )
        )

    if start_date:
        try:
            dt_start = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.filter(ScannedRecord.scan_date >= dt_start)
        except ValueError:
            pass

    if end_date:
        try:
            dt_end = datetime.strptime(f"{end_date} 23:59:59", "%Y-%m-%d %H:%M:%S")
            query = query.filter(ScannedRecord.scan_date <= dt_end)
        except ValueError:
            pass

    records = query.order_by(desc(ScannedRecord.scan_date)).all()
    records_data = [r.to_dict() for r in records]

    timestamp_str = get_peru_now().strftime("%Y%m%d_%H%M%S")
    temp_filename = f"Export_Registros_{timestamp_str}.xlsx"
    temp_path = EXPORTS_DIR / temp_filename

    # If no filters and master excel exists with all records, we can also generate a clean copy
    generate_filtered_excel(records_data, temp_path)

    return FileResponse(
        path=str(temp_path),
        filename=f"Registros_Documentos_Peruanos_{timestamp_str}.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


# =========================================================================
# Servicios de Inteligencia de Excel, Consolidación y Generación de Contratos
# =========================================================================

excel_analyzer = ExcelAnalyzer(MASTER_EXCEL_PATH)
worker_consolidator = WorkerConsolidator(MASTER_EXCEL_PATH)
contract_generator = ContractGenerator(TEMPLATES_DIR, CONTRACTS_DIR)


@app.get("/api/worker/search/{dni}", response_model=WorkerProfileResponse)
def search_and_consolidate_worker(dni: str, db: Session = Depends(get_db)):
    """
    Busca al trabajador por DNI en el Excel (hojas visibles/ocultas, comentarios y notas)
    y en la base de datos de escaneos previos, retornando su ficha consolidada con procedencia de datos.
    """
    clean_dni = re.sub(r"\D", "", dni).strip()
    if not clean_dni:
        raise HTTPException(status_code=400, detail="DNI inválido")

    # Verificar si existe algún escaneo previo en BD para enriquecer
    latest_scan = (
        db.query(ScannedRecord)
        .filter(ScannedRecord.doc_number.ilike(f"%{clean_dni}%"))
        .order_by(desc(ScannedRecord.scan_date))
        .first()
    )
    ocr_data = latest_scan.to_dict() if latest_scan else {}

    profile = worker_consolidator.consolidate_worker_profile(clean_dni, ocr_data=ocr_data)
    return profile


@app.post("/api/worker/consolidate", response_model=WorkerProfileResponse)
def consolidate_worker_from_scan(payload: Dict[str, Any]):
    """
    Fusiona los datos extraídos en tiempo real por el OCR con la búsqueda profunda en Excel.
    """
    dni = payload.get("dni") or payload.get("doc_number", "")
    ocr_data = payload.get("ocr_data") or payload
    clean_dni = re.sub(r"\D", "", str(dni)).strip()

    if not clean_dni:
        raise HTTPException(status_code=400, detail="Número de DNI no detectado")

    profile = worker_consolidator.consolidate_worker_profile(clean_dni, ocr_data=ocr_data)
    return profile


@app.post("/api/contracts/calculate-dates")
def calculate_contract_dates(req: CalculateDatesRequest):
    """
    Calcula automáticamente la fecha de término del contrato laboral según la norma peruana.
    Ejemplo: Inicio 08/09/2026, 3 meses -> Fin 07/12/2026.
    """
    return worker_consolidator.calculate_contract_dates(req.start_date, req.duration_months)


@app.get("/api/contracts/templates")
def list_contract_templates():
    """Lista las plantillas .docx disponibles."""
    return {"templates": contract_generator.list_templates()}


@app.post("/api/contracts/generate")
def generate_single_contract(req: ContractGenerateRequest, db: Session = Depends(get_db)):
    """
    Genera el contrato laboral .docx para un trabajador conservando el 100% de la plantilla original.
    Registra el contrato en la base de datos para auditoría e historial.
    """
    dates_calc = worker_consolidator.calculate_contract_dates(req.start_date, req.duration_months)
    
    try:
        gen_result = contract_generator.generate_contract(
            worker_data=req.worker_data,
            contract_dates=dates_calc,
            template_name=req.template_name,
            empresa_nombre=req.empresa_nombre or "SERVICIOS INDUSTRIALES DEL PERÚ S.A.C.",
            empresa_ruc=req.empresa_ruc or "20601234567",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando el documento .docx: {str(e)}")

    # Guardar registro en base de datos
    contract_log = GeneratedContractLog(
        dni=gen_result["dni"],
        worker_name=gen_result["worker_name"],
        contract_type=req.worker_data.get("fields", {}).get("tipo_contrato", {}).get("value", "SUJETO A MODALIDAD"),
        start_date=gen_result["start_date"],
        end_date=gen_result["end_date"],
        duration=gen_result["duration"],
        file_name=gen_result["file_name"],
        file_path=gen_result["file_path"],
        file_size_kb=gen_result["size_kb"],
        status="GENERADO",
        provenance_summary=json.dumps({
            k: v.get("origin") for k, v in req.worker_data.get("fields", {}).items() if isinstance(v, dict)
        }),
    )
    db.add(contract_log)
    db.commit()
    db.refresh(contract_log)

    return {
        "success": True,
        "contract": contract_log.to_dict(),
        "download_url": f"/api/contracts/download/{gen_result['file_name']}",
        "file_details": gen_result,
    }


@app.post("/api/contracts/generate-batch")
def generate_batch_contracts(req: BatchContractGenerateRequest, db: Session = Depends(get_db)):
    """
    Generación masiva de contratos para múltiples trabajadores seleccionados o todos los del Excel.
    Empaqueta los archivos .docx generados en un archivo comprimido .zip.
    """
    if not req.workers:
        raise HTTPException(status_code=400, detail="Debe seleccionar al menos un trabajador para la generación masiva.")

    dates_calc = worker_consolidator.calculate_contract_dates(req.start_date, req.duration_months)
    generated_logs = []
    generated_files = []
    errors = []

    for w in req.workers:
        dni = w.get("dni", "")
        try:
            profile = worker_consolidator.consolidate_worker_profile(dni)
            gen_res = contract_generator.generate_contract(
                worker_data=profile,
                contract_dates=dates_calc,
                template_name=req.template_name,
            )
            
            # Guardar log en BD
            contract_log = GeneratedContractLog(
                dni=gen_res["dni"],
                worker_name=gen_res["worker_name"],
                contract_type="SUJETO A MODALIDAD",
                start_date=gen_res["start_date"],
                end_date=gen_res["end_date"],
                duration=gen_res["duration"],
                file_name=gen_res["file_name"],
                file_path=gen_res["file_path"],
                file_size_kb=gen_res["size_kb"],
                status="GENERADO",
            )
            db.add(contract_log)
            generated_logs.append(contract_log)
            generated_files.append(Path(gen_res["file_path"]))
        except Exception as e:
            errors.append({"dni": dni, "name": w.get("full_name", ""), "error": str(e)})

    db.commit()

    # Crear ZIP si hay más de 1 archivo
    zip_filename = None
    zip_download_url = None
    if generated_files:
        timestamp_str = get_peru_now().strftime("%Y%m%d_%H%M%S")
        zip_filename = f"Lote_Contratos_{timestamp_str}.zip"
        zip_path = CONTRACTS_DIR / zip_filename
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for f in generated_files:
                if f.exists():
                    zipf.write(f, arcname=f.name)

        zip_download_url = f"/api/contracts/download/{zip_filename}"

    return {
        "success": True,
        "total_requested": len(req.workers),
        "total_generated": len(generated_files),
        "total_errors": len(errors),
        "zip_file_name": zip_filename,
        "zip_download_url": zip_download_url,
        "generated_items": [l.to_dict() for l in generated_logs],
        "errors": errors,
    }


@app.get("/api/contracts/history")
def get_contracts_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Retorna el historial paginado de contratos generados con buscador por DNI o Nombre."""
    query = db.query(GeneratedContractLog)
    if search:
        s = f"%{search.strip()}%"
        query = query.filter(
            or_(
                GeneratedContractLog.dni.ilike(s),
                GeneratedContractLog.worker_name.ilike(s),
                GeneratedContractLog.file_name.ilike(s),
            )
        )

    total = query.count()
    items = (
        query.order_by(desc(GeneratedContractLog.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [item.to_dict() for item in items],
    }


@app.get("/api/contracts/download/{filename}")
def download_generated_file(filename: str):
    """Descarga segura de un contrato .docx o archivo .zip generado."""
    clean_name = Path(filename).name
    file_path = CONTRACTS_DIR / clean_name
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Archivo no encontrado: {clean_name}")

    media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    if clean_name.endswith(".zip"):
        media_type = "application/zip"

    return FileResponse(
        path=str(file_path),
        filename=clean_name,
        media_type=media_type,
    )


@app.get("/api/excel/diagnostic")
def get_excel_diagnostic():
    """Retorna el reporte de inspección profunda del archivo Excel (hojas, comentarios, celdas ocultas)."""
    return excel_analyzer.inspect_excel_file()


@app.get("/api/excel/workers")
def list_excel_workers():
    """Retorna la lista de todos los trabajadores identificados en el archivo Excel."""
    workers = excel_analyzer.list_all_workers()
    return {"total": len(workers), "workers": workers}


# ==========================================
# Excel Templates Endpoints (Gestión de Plantillas)
# ==========================================

@app.get("/api/excel-templates")
def list_excel_templates():
    """Retorna todas las plantillas Excel registradas con sus hojas y mapeos de columnas."""
    return {"templates": excel_template_service.list_templates()}


@app.post("/api/excel-templates/upload")
def upload_excel_template(file: UploadFile = File(...)):
    """Sube una nueva plantilla Excel y analiza automáticamente sus columnas."""
    if not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Solo se permiten archivos Excel en formato .xlsx.")
    contents = file.file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="El archivo subido está vacío.")
    analysis = excel_template_service.save_uploaded_template(contents, file.filename)
    return {"message": "Plantilla subida y analizada con éxito.", "template": analysis}


@app.post("/api/excel-templates/fill")
def fill_excel_template(payload: dict):
    """
    Rellena los datos extraídos del DNI en la plantilla Excel seleccionada
    manteniendo exactamente el formato, colores y estilos originales.
    """
    template_name = payload.get("template_name")
    if not template_name:
        raise HTTPException(status_code=400, detail="Debe especificar 'template_name'.")
    dni_data = payload.get("data", {})
    sheet_name = payload.get("sheet_name")

    try:
        out_filename, out_path = excel_template_service.fill_template(
            template_name=template_name,
            data=dni_data,
            sheet_name=sheet_name
        )
        return {
            "success": True,
            "filename": out_filename,
            "download_url": f"/api/exports/download/{out_filename}",
            "message": f"Datos completados con éxito en la plantilla '{template_name}'."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al completar plantilla: {str(e)}")


@app.post("/api/excel-templates/generate-batch")
def generate_batch_excel(payload: dict, db: Session = Depends(get_db)):
    """
    Genera una copia de la plantilla Excel seleccionada llenando únicamente
    las celdas amarillas con los trabajadores seleccionados por fecha/hora.
    """
    template_name = payload.get("template_name")
    if not template_name:
        raise HTTPException(status_code=400, detail="Debe seleccionar una plantilla Excel.")

    record_ids = payload.get("record_ids", [])
    records_data = payload.get("records")
    sheet_name = payload.get("sheet_name")

    if record_ids:
        queried = db.query(ScannedRecord).filter(ScannedRecord.id.in_(record_ids)).all()
        id_map = {r.id: r.to_dict() for r in queried}
        records = [id_map[rid] for rid in record_ids if rid in id_map]
    elif records_data:
        records = records_data
    else:
        raise HTTPException(status_code=400, detail="Debe seleccionar al menos un trabajador escaneado.")

    if not records:
        raise HTTPException(status_code=400, detail="No se encontraron datos para los trabajadores seleccionados.")

    try:
        out_filename, out_path, num_workers, yellow_cols = excel_template_service.fill_template_batch(
            template_name=template_name,
            records=records,
            sheet_name=sheet_name
        )
        return {
            "success": True,
            "filename": out_filename,
            "download_url": f"/api/exports/download/{out_filename}",
            "total_workers": num_workers,
            "yellow_columns_filled": yellow_cols,
            "message": f"Excel generado con éxito con {num_workers} trabajadores en la plantilla '{template_name}'."
        }
    except FileNotFoundError as fnf:
        raise HTTPException(status_code=404, detail=str(fnf))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al generar archivo Excel: {str(e)}")


@app.get("/api/scanned-records/dates")
def get_scanned_dates(db: Session = Depends(get_db)):
    """
    Retorna la lista de fechas únicas en que se han realizado escaneos de DNI con su cantidad de registros.
    """
    records = db.query(ScannedRecord.scan_date).all()
    date_counts = {}
    for r in records:
        if r[0]:
            d_str = r[0].strftime("%Y-%m-%d")
            date_counts[d_str] = date_counts.get(d_str, 0) + 1

    sorted_dates = sorted(date_counts.keys(), reverse=True)
    results = []
    for d in sorted_dates:
        try:
            dt = datetime.strptime(d, "%Y-%m-%d")
            formatted = dt.strftime("%d/%m/%Y")
        except Exception:
            formatted = d
        results.append({
            "date": d,
            "formatted": formatted,
            "count": date_counts[d]
        })
    return {"dates": results}


@app.get("/api/scanned-records/by-date-time")
def get_scanned_records_by_date_time(
    date_val: Optional[str] = Query(None, alias="date"),
    start_time: Optional[str] = Query(None),
    end_time: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Filtra los escaneos de DNI por fecha y rango de horas para selección y generación de Excel.
    """
    query = db.query(ScannedRecord)

    if date_val and date_val.strip() and date_val != "all":
        try:
            d_start = datetime.strptime(f"{date_val.strip()} 00:00:00", "%Y-%m-%d %H:%M:%S")
            d_end = datetime.strptime(f"{date_val.strip()} 23:59:59", "%Y-%m-%d %H:%M:%S")
            query = query.filter(ScannedRecord.scan_date >= d_start, ScannedRecord.scan_date <= d_end)
        except Exception:
            pass

    if search and search.strip():
        s = f"%{search.strip()}%"
        query = query.filter(
            or_(
                ScannedRecord.doc_number.ilike(s),
                ScannedRecord.paternal_surname.ilike(s),
                ScannedRecord.maternal_surname.ilike(s),
                ScannedRecord.first_names.ilike(s),
                ScannedRecord.address.ilike(s),
            )
        )

    all_records = query.order_by(desc(ScannedRecord.scan_date)).all()

    filtered = []
    for rec in all_records:
        rec_dict = rec.to_dict()
        if rec.scan_date:
            rec_time = rec.scan_date.strftime("%H:%M")
            rec_date_str = rec.scan_date.strftime("%d/%m/%Y")
            rec_dict["formatted_time"] = rec_time
            rec_dict["formatted_date"] = rec_date_str
            rec_dict["display_datetime"] = f"{rec_date_str} {rec_time}"

            if start_time and start_time.strip():
                if rec_time < start_time.strip():
                    continue
            if end_time and end_time.strip():
                if rec_time > end_time.strip():
                    continue
        else:
            rec_dict["formatted_time"] = ""
            rec_dict["formatted_date"] = ""
            rec_dict["display_datetime"] = ""

        filtered.append(rec_dict)

    return {
        "total": len(filtered),
        "items": filtered
    }


@app.delete("/api/excel-templates/{filename:path}")
def delete_excel_template(filename: str):
    """Elimina una plantilla Excel registrada."""
    try:
        excel_template_service.delete_template(filename)
        return {"success": True, "message": f"Plantilla '{filename}' eliminada correctamente."}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Plantilla '{filename}' no encontrada.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al eliminar plantilla: {str(e)}")


@app.put("/api/excel-templates/{filename:path}/rename")
def rename_excel_template(filename: str, payload: dict):
    """Renombra una plantilla Excel registrada."""
    new_name = payload.get("new_name")
    if not new_name:
        raise HTTPException(status_code=400, detail="Debe especificar 'new_name'.")
    try:
        updated = excel_template_service.rename_template(filename, new_name)
        return {"success": True, "message": f"Plantilla renombrada a '{new_name}'.", "template": updated}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Plantilla '{filename}' no encontrada.")
    except FileExistsError as fe:
        raise HTTPException(status_code=400, detail=str(fe))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al renombrar plantilla: {str(e)}")


@app.get("/api/excel-templates/download/{filename:path}")
def download_excel_template(filename: str):
    """Descarga el archivo original de la plantilla Excel."""
    try:
        file_path = excel_template_service.get_template_path(filename)
        return FileResponse(
            path=str(file_path),
            filename=file_path.name,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Plantilla '{filename}' no encontrada.")


@app.post("/api/excel-templates/{filename:path}/mapping")
def save_template_mapping(filename: str, payload: dict):
    """Guarda mapeos personalizados de columnas para una hoja específica de la plantilla."""
    sheet_name = payload.get("sheet_name")
    mappings = payload.get("mappings", {})
    if not sheet_name:
        raise HTTPException(status_code=400, detail="Debe especificar 'sheet_name'.")
    try:
        updated = excel_template_service.save_template_mapping(filename, sheet_name, mappings)
        return {"success": True, "message": "Mapeo guardado con éxito.", "template": updated}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Plantilla '{filename}' no encontrada.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al guardar mapeo: {str(e)}")


@app.get("/api/exports/download/{filename}")
def download_export_file(filename: str):
    """Descarga de archivos Excel generados."""
    clean_name = Path(filename).name
    file_path = EXPORTS_DIR / clean_name
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Archivo no encontrado: {clean_name}")
    return FileResponse(
        path=str(file_path),
        filename=clean_name,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


# =============================================================================
# Módulo Supabase: Gestión de Plantillas en la Nube (Storage + Database)
# =============================================================================

@app.get("/api/supabase/config")
def get_supabase_config():
    """Retorna la configuración actual de Supabase y el estado de conexión."""
    return {
        "config": supabase_template_service.get_config(),
        "status": supabase_template_service.check_connection(),
    }


@app.post("/api/supabase/config")
def save_supabase_config(payload: dict):
    """Guarda y valida las credenciales de conexión con Supabase."""
    url = payload.get("supabase_url", "")
    key = payload.get("supabase_key", "")
    bucket = payload.get("bucket_name", "templates")
    if not url or not key:
        raise HTTPException(status_code=400, detail="Debe ingresar la URL y la API Key de Supabase.")
    res = supabase_template_service.save_config(url, key, bucket)
    return res


@app.post("/api/supabase/test-connection")
def test_supabase_connection():
    """Prueba la conexión a la base de datos y al bucket de Supabase."""
    return supabase_template_service.check_connection()


@app.get("/api/supabase-templates")
def list_supabase_templates():
    """Retorna todas las plantillas registradas en la base de datos de Supabase."""
    templates = supabase_template_service.list_templates()
    return {"templates": templates, "total": len(templates)}


@app.post("/api/supabase-templates/upload")
def upload_supabase_template(
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    template_type: str = Form("EXCEL_CARGA_MASIVA"),
    version: str = Form("1.0"),
    user_name: str = Form("Flavio Monzón"),
):
    """
    Sube un nuevo archivo Excel a Supabase Storage y registra sus metadatos
    (nombre, tipo, versión, fecha, usuario, celdas amarillas) en Supabase Database.
    """
    if not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Solo se permiten archivos Excel en formato .xlsx.")

    file_bytes = file.file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="El archivo subido está vacío.")

    try:
        res = supabase_template_service.upload_template(
            file_bytes=file_bytes,
            filename=file.filename,
            name=name,
            template_type=template_type,
            version=version,
            user_name=user_name,
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/supabase-templates/{template_id}/download")
def download_supabase_template(template_id: str):
    """Descarga el archivo físico original de la plantilla desde Supabase Storage."""
    try:
        file_bytes, filename = supabase_template_service.download_template_file(template_id)
        return FileResponse(
            path=str(supabase_template_service.get_template_path_for_processing(template_id)),
            filename=filename,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Error al descargar plantilla de Supabase: {str(e)}")


@app.post("/api/supabase-templates/{template_id}/replace")
def replace_supabase_template_file(
    template_id: str,
    file: UploadFile = File(...),
    user_name: str = Form("Flavio Monzón"),
):
    """
    Reemplaza el archivo físico en Supabase Storage, recalcula las celdas amarillas
    e incrementa automáticamente la versión en Supabase Database.
    """
    if not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Solo se permiten archivos Excel .xlsx.")

    file_bytes = file.file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="El archivo está vacío.")

    try:
        res = supabase_template_service.replace_template_file(
            template_id=template_id,
            file_bytes=file_bytes,
            filename=file.filename,
            user_name=user_name,
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/supabase-templates/{template_id}")
def update_supabase_template_metadata(template_id: str, payload: dict):
    """Actualiza metadatos (nombre descriptivo, tipo, versión) en Supabase Database."""
    try:
        res = supabase_template_service.update_template_metadata(
            template_id=template_id,
            name=payload.get("name"),
            template_type=payload.get("template_type"),
            version=payload.get("version"),
            sheets_metadata=payload.get("sheets_metadata"),
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/supabase-templates/{template_id}")
def delete_supabase_template(template_id: str):
    """Elimina la plantilla tanto de Supabase Storage como de Supabase Database."""
    try:
        res = supabase_template_service.delete_template(template_id)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/supabase-templates/{template_id}/mapping")
def save_supabase_template_mapping(template_id: str, payload: dict):
    """Guarda mapeos personalizados de columnas en los metadatos de Supabase Database."""
    sheet_name = payload.get("sheet_name")
    mappings = payload.get("mappings", {})
    if not sheet_name:
        raise HTTPException(status_code=400, detail="Debe especificar 'sheet_name'.")

    tpl = supabase_template_service.get_template(template_id)
    if not tpl:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada en Supabase.")

    sheets = tpl.get("sheets", [])
    for sh in sheets:
        if sh.get("sheet_name") == sheet_name:
            sh["custom_mappings"] = mappings
            break

    try:
        supabase_template_service.update_template_metadata(template_id, sheets_metadata=sheets)
        return {"success": True, "message": "Mapeo guardado en Supabase exitosamente."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/supabase-templates/generate-batch")
def generate_batch_excel_supabase(payload: dict, db: Session = Depends(get_db)):
    """
    Genera un archivo Excel llenando únicamente las celdas amarillas a partir de una
    plantilla almacenada en Supabase Storage con los trabajadores seleccionados.
    """
    template_id = payload.get("template_id")
    if not template_id:
        raise HTTPException(status_code=400, detail="Debe especificar 'template_id' de Supabase.")

    record_ids = payload.get("record_ids", [])
    records_data = payload.get("records")
    sheet_name = payload.get("sheet_name")

    if record_ids:
        queried = db.query(ScannedRecord).filter(ScannedRecord.id.in_(record_ids)).all()
        id_map = {r.id: r.to_dict() for r in queried}
        records = [id_map[rid] for rid in record_ids if rid in id_map]
    elif records_data:
        records = records_data
    else:
        raise HTTPException(status_code=400, detail="Debe seleccionar al menos un trabajador escaneado.")

    if not records:
        raise HTTPException(status_code=400, detail="No se encontraron datos para los trabajadores seleccionados.")

    # 1. Obtener la plantilla desde Supabase y garantizar que esté en caché local
    try:
        template_file_path = supabase_template_service.get_template_path_for_processing(template_id)
        tpl_metadata = supabase_template_service.get_template(template_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"No se pudo descargar la plantilla de Supabase: {str(e)}")

    # 2. Utilizar el motor de llenado de celdas amarillas con el archivo de Supabase
    try:
        out_filename, out_path, num_workers, yellow_cols = excel_template_service.fill_template_batch_from_file(
            source_file_path=template_file_path,
            template_display_name=tpl_metadata.get("name", template_file_path.name) if tpl_metadata else template_file_path.name,
            records=records,
            sheet_name=sheet_name
        )
        return {
            "success": True,
            "filename": out_filename,
            "download_url": f"/api/exports/download/{out_filename}",
            "total_workers": num_workers,
            "yellow_columns_filled": yellow_cols,
            "template_name": tpl_metadata.get("name") if tpl_metadata else template_file_path.name,
            "template_version": tpl_metadata.get("version", "1.0") if tpl_metadata else "1.0",
            "message": f"Excel generado con éxito con {num_workers} trabajadores desde la plantilla Supabase."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al generar archivo Excel: {str(e)}")


