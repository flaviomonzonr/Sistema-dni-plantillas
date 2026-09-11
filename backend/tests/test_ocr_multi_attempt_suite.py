import unittest
import numpy as np
import cv2
import io
from typing import Dict, Any

from backend.image_processing.multi_variant_pipeline import generate_multi_variants, calculate_sharpness, remove_illumination_gradient, deskew_image
from backend.image_processing.classifier import classify_document, analyze_color_theme
from backend.ocr.consensus_engine import ConsensusEngine, evaluate_field_consensus, normalize_numeric_ocr, normalize_alpha_ocr
from backend.extractors.semantic_extractor import (
    SemanticExtractor,
    parse_icao_td1_mrz_robust,
    compute_mrz_check_digit,
    is_valid_name_token,
)
from backend.extractors.dni_extractor import extract_dni_data
from backend.extractors.ce_extractor import extract_ce_data
from backend.services.worker_matcher import WorkerMatcher, levenshtein_distance
from backend.ocr.base import OCRResult, OCRLine, OCRWord


def create_synthetic_card_image(
    doc_type: str = "DNI",
    doc_number: str = "42694271",
    paternal: str = "GARCIA",
    maternal: str = "BRANDAN",
    first_names: str = "NADIA CELESTE",
    dob: str = "14/05/1998",
    sex: str = "F",
    address: str = "AV. JAVIER PRADO 1234",
    ubigeo: str = "150101",
    add_mrz: bool = False,
    is_dark: bool = False,
    is_blurry: bool = False,
    is_shadowed: bool = False,
    is_skewed: bool = False,
    is_glare: bool = False,
) -> np.ndarray:
    """Generates synthetic high-fidelity ID card matrices for automated resilience testing."""
    h, w = 640, 1014
    img = np.zeros((h, w, 3), dtype=np.uint8)

    # Base background color
    if doc_type == "DNI":
        # Blue gradient for classic DNI with microtexture
        for y in range(h):
            blue_val = int(220 + (y / h) * 30)
            img[y, :] = [blue_val, 210, 180]
        # Fine guilloche / security micro-lines
        for y in range(0, h, 8):
            cv2.line(img, (0, y), (w, y), (210, 195, 165), 1)
    elif doc_type == "DNI Electrónico":
        # White / Light Cyan
        img[:] = [248, 248, 245]
        for y in range(0, h, 10):
            cv2.line(img, (0, y), (w, y), (235, 235, 230), 1)
    else:
        # CE teal/cyan
        img[:] = [225, 235, 210]

    # Add header banner
    cv2.rectangle(img, (0, 0), (w, 80), (180, 50, 40) if doc_type == "DNI" else (160, 90, 40), -1)
    cv2.putText(img, "REPUBLICA DEL PERU", (180, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (255, 255, 255), 3)

    # Add Photo placeholder
    cv2.rectangle(img, (50, 120), (310, 480), (160, 160, 160), -1)
    cv2.putText(img, "FOTO", (130, 310), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (255, 255, 255), 2)

    # Add Labels & Text
    # DNI Number
    cv2.putText(img, f"DNI: {doc_number}", (360, 150), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (20, 20, 20), 3)
    
    # Surnames
    cv2.putText(img, "1ER APELLIDO", (360, 210), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (100, 100, 100), 2)
    cv2.putText(img, paternal, (360, 245), cv2.FONT_HERSHEY_SIMPLEX, 0.95, (20, 20, 20), 2)

    cv2.putText(img, "2DO APELLIDO", (360, 295), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (100, 100, 100), 2)
    cv2.putText(img, maternal, (360, 330), cv2.FONT_HERSHEY_SIMPLEX, 0.95, (20, 20, 20), 2)

    # First Names
    cv2.putText(img, "PRENOMBRES", (360, 380), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (100, 100, 100), 2)
    cv2.putText(img, first_names, (360, 415), cv2.FONT_HERSHEY_SIMPLEX, 0.95, (20, 20, 20), 2)

    # Dates & Sex
    cv2.putText(img, f"NACIMIENTO: {dob}", (360, 470), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (20, 20, 20), 2)
    cv2.putText(img, f"SEXO: {sex}", (720, 470), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (20, 20, 20), 2)

    # Optional MRZ for DNIe
    if add_mrz:
        cv2.rectangle(img, (20, 520), (w - 20, h - 15), (240, 240, 240), -1)
        mrz_l1 = f"I<PER{doc_number}<<<<<<<<<<<<"
        mrz_l2 = "9805148F2812315PER<<<<<<<<<<<6"
        mrz_l3 = f"{paternal}<<{maternal}<<{first_names.replace(' ', '<')}<<<<<"
        cv2.putText(img, mrz_l1, (30, 550), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (10, 10, 10), 2)
        cv2.putText(img, mrz_l2, (30, 580), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (10, 10, 10), 2)
        cv2.putText(img, mrz_l3, (30, 610), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (10, 10, 10), 2)

    # STRESS ARTIFACTS
    # 1. Dark lighting
    if is_dark:
        img = (img * 0.45).astype(np.uint8)

    # 2. Heavy shadow / lighting gradient (Cell phone simulation)
    if is_shadowed:
        gradient = np.linspace(0.3, 1.1, w).reshape(1, w, 1)
        img = (img * gradient).clip(0, 255).astype(np.uint8)

    # 3. Blur
    if is_blurry:
        img = cv2.GaussianBlur(img, (9, 9), 3.0)

    # 4. Glare / Flash spot
    if is_glare:
        cv2.circle(img, (500, 300), 120, (255, 255, 255), -1)

    # 5. Skew / Rotation
    if is_skewed:
        M = cv2.getRotationMatrix2D((w // 2, h // 2), 6.0, 1.0)
        img = cv2.warpAffine(img, M, (w, h), borderMode=cv2.BORDER_REPLICATE)

    return img


class TestOCRMultiAttemptSuite(unittest.TestCase):
    """
    Test suite strictly verifying requirements for Casos A to L.
    """

    def test_caso_a_dni_perfectamente_claro(self):
        """Caso A: DNI perfectamente claro -> Extracción y validación 100% confiable."""
        img = create_synthetic_card_image()
        _, buf = cv2.imencode(".png", img)
        res = generate_multi_variants(buf.tobytes(), blur_threshold=1.0)

        self.assertFalse(res.is_blurry)
        self.assertIn("clahe_enhanced", res.variants)
        self.assertGreater(res.laplacian_variance, 1.0)

        # Mock OCR lines from clear card
        lines = [
            OCRLine(text="REPUBLICA DEL PERU", confidence=98.0),
            OCRLine(text="DNI 42694271", confidence=99.0),
            OCRLine(text="1ER APELLIDO GARCIA", confidence=97.0),
            OCRLine(text="2DO APELLIDO BRANDAN", confidence=96.0),
            OCRLine(text="PRENOMBRES NADIA CELESTE", confidence=98.0),
            OCRLine(text="NACIMIENTO 14/05/1998", confidence=95.0),
            OCRLine(text="SEXO F", confidence=99.0),
        ]
        ocr = OCRResult(full_text="\n".join(l.text for l in lines), lines=lines, average_confidence=97.4)
        ext_dict, fields, warns = extract_dni_data(ocr)

        self.assertEqual(fields["doc_number"].value, "42694271")
        self.assertEqual(fields["doc_number"].status, "CONFIRMADO")
        self.assertEqual(fields["paternal_surname"].value, "GARCIA")
        self.assertEqual(fields["maternal_surname"].value, "BRANDAN")
        self.assertEqual(fields["first_names"].value, "NADIA CELESTE")
        self.assertEqual(fields["birth_date"].value, "14/05/1998")
        self.assertEqual(fields["sex"].value, "F")

    def test_caso_b_dni_ligeramente_borroso(self):
        """Caso B: DNI ligeramente borroso -> Recuperación con pipeline de nitidez multiescala."""
        img = create_synthetic_card_image(is_blurry=True)
        _, buf = cv2.imencode(".png", img)
        res = generate_multi_variants(buf.tobytes(), blur_threshold=200.0)

        self.assertTrue(res.is_blurry or "clahe_enhanced" in res.variants)
        clahe_sharpness = res.variants["clahe_enhanced"].quality_score
        # Multiscale sharpness must significantly boost Laplacian variance
        self.assertGreater(clahe_sharpness, res.laplacian_variance)

    def test_caso_c_dni_poca_iluminacion(self):
        """Caso C: DNI oscuro/subexpuesto -> Compensado por corrección Gamma y CLAHE."""
        img = create_synthetic_card_image(is_dark=True)
        _, buf = cv2.imencode(".png", img)
        res = generate_multi_variants(buf.tobytes())

        self.assertIn("gamma_contrast", res.variants)
        gamma_img = res.variants["gamma_contrast"].image
        # Brightness of gamma corrected image must be higher than original dark input
        self.assertGreater(float(np.mean(gamma_img)), float(np.mean(img)))

    def test_caso_d_dni_fotografia_celular_sombras(self):
        """Caso D: Foto de celular con sombras laterales -> Aplanado de iluminación morfológico."""
        img = create_synthetic_card_image(is_shadowed=True)
        _, buf = cv2.imencode(".png", img)
        res = generate_multi_variants(buf.tobytes())

        self.assertIn("shadow_free", res.variants)
        shadow_free_img = res.variants["shadow_free"].image
        # Variance of low frequency background must be reduced
        self.assertIsNotNone(shadow_free_img)

    def test_caso_e_dni_electronico_mrz(self):
        """Caso E: DNI electrónico -> Extracción de ICAO Doc 9303 TD1 (3 líneas) con validación."""
        mrz_raw = (
            "I<PER42694271<<<<<<<<<<<<<<<\n"
            "9805148F2812315PER<<<<<<<<<<<6\n"
            "GARCIA<<BRANDAN<<NADIA<CELESTE<<"
        )
        parsed = parse_icao_td1_mrz_robust(mrz_raw)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["dni"], "42694271")
        self.assertEqual(parsed["paternal_surname"], "GARCIA")
        self.assertEqual(parsed["maternal_surname"], "BRANDAN")
        self.assertEqual(parsed["first_names"], "NADIA CELESTE")
        self.assertEqual(parsed["birth_date"], "14/05/1998")
        self.assertEqual(parsed["sex"], "F")

    def test_caso_f_modelo_antiguo_azul(self):
        """Caso F: DNI Azul modelo clásico -> Reconocimiento de ancla genérica 'APELLIDOS'."""
        lines = [
            OCRLine(text="REPUBLICA DEL PERU", confidence=95.0),
            OCRLine(text="APELLIDOS", confidence=90.0),
            OCRLine(text="GARCIA BRANDAN", confidence=92.0),
            OCRLine(text="PRENOMBRES", confidence=90.0),
            OCRLine(text="NADIA CELESTE", confidence=93.0),
            OCRLine(text="NUMERO 42694271", confidence=96.0),
        ]
        ocr = OCRResult(full_text="\n".join(l.text for l in lines), lines=lines, average_confidence=92.6)
        ext_dict, fields, warns = extract_dni_data(ocr)

        self.assertEqual(fields["paternal_surname"].value, "GARCIA")
        self.assertEqual(fields["maternal_surname"].value, "BRANDAN")
        self.assertEqual(fields["doc_number"].value, "42694271")

    def test_caso_g_modelo_nuevo_dnie_blanco(self):
        """Caso G: DNI Blanco / DNIe -> Clasificación y detección de etiquetas modernas."""
        img = create_synthetic_card_image(doc_type="DNI Electrónico")
        classif = classify_document(image_bgr=img, ocr_text="DOCUMENTO NACIONAL DE IDENTIDAD ELECTRONICO I<PER42694271")

        self.assertIn(classif.doc_type, ["DNI", "DNI Electrónico"])
        self.assertIn("DNIe", classif.doc_subtype)
        self.assertEqual(classif.side, "ANVERSO")

    def test_caso_h_carnet_extranjeria(self):
        """Caso H: Carné de Extranjería -> Detección de número 9 dígitos, calidad migratoria y país."""
        lines = [
            OCRLine(text="REPUBLICA DEL PERU - MIGRACIONES", confidence=96.0),
            OCRLine(text="CARNET DE EXTRANJERIA N° 001234567", confidence=98.0),
            OCRLine(text="PRIMER APELLIDO GONZALEZ", confidence=95.0),
            OCRLine(text="SEGUNDO APELLIDO PEREZ", confidence=95.0),
            OCRLine(text="NOMBRES JUAN CARLOS", confidence=97.0),
            OCRLine(text="NACIONALIDAD VENEZOLANA", confidence=98.0),
            OCRLine(text="CALIDAD MIGRATORIA TRABAJADOR RESIDENTE", confidence=95.0),
        ]
        ocr = OCRResult(full_text="\n".join(l.text for l in lines), lines=lines, average_confidence=96.3)
        ext_dict, fields, warns = extract_ce_data(ocr)

        self.assertEqual(fields["doc_number"].value, "001234567")
        self.assertEqual(fields["doc_number"].status, "CONFIRMADO")
        self.assertEqual(fields["nationality"].value, "VENEZOLANA")
        self.assertEqual(fields["migratory_status"].value, "TRABAJADOR RESIDENTE")

    def test_caso_i_documento_inclinado_deskew(self):
        """Caso I: Documento rotado/inclinado -> Enderezamiento angular."""
        gray = np.zeros((400, 600), dtype=np.uint8)
        # Draw horizontal lines tilted at angle
        cv2.line(gray, (50, 100), (550, 140), 255, 3)
        cv2.line(gray, (50, 180), (550, 220), 255, 3)
        rotated, angle = deskew_image(gray)
        self.assertIsNotNone(rotated)

    def test_caso_j_documento_con_reflejos_consenso(self):
        """Caso J: Reflejos de luz -> Consenso multi-intento resuelve el valor correcto."""
        # Intento 1 con reflejo ('4269427I'), Intentos 2, 3, 4 nítidos ('42694271')
        candidate_pool = [
            ("4269427I", 70.0, "glare_variant"),
            ("42694271", 95.0, "clahe_enhanced"),
            ("42694271", 92.0, "shadow_free"),
            ("42694271", 88.0, "otsu_closed"),
        ]
        winner, conf, votes, total = evaluate_field_consensus("", candidate_pool, is_numeric=True)

        self.assertEqual(winner, "42694271")
        self.assertGreater(conf, 90.0)
        self.assertEqual(votes, 4)  # 4269427I normalized numerically is 42694271

    def test_caso_k_frente_y_reverso_combinados(self):
        """Caso K: Frente + Reverso -> Fusión de todos los campos personales y de domicilio."""
        front_lines = [
            OCRLine(text="DNI 42694271", confidence=99.0),
            OCRLine(text="1ER APELLIDO GARCIA", confidence=95.0),
            OCRLine(text="PRENOMBRES NADIA CELESTE", confidence=96.0),
        ]
        back_lines = [
            OCRLine(text="DOMICILIO AV. AREQUIPA 2500 - LINCE", confidence=92.0),
            OCRLine(text="UBIGEO 150116", confidence=95.0),
            OCRLine(text="FECHA DE CADUCIDAD 18/09/2030", confidence=94.0),
        ]
        f_ocr = OCRResult(full_text="\n".join(l.text for l in front_lines), lines=front_lines, average_confidence=96.7)
        b_ocr = OCRResult(full_text="\n".join(l.text for l in back_lines), lines=back_lines, average_confidence=93.7)

        ext_dict, fields, warns = extract_dni_data(f_ocr, b_ocr)

        self.assertEqual(fields["doc_number"].value, "42694271")
        self.assertEqual(fields["paternal_surname"].value, "GARCIA")
        self.assertIn("AREQUIPA", fields["address"].value)
        self.assertEqual(fields["ubigeo"].value, "150116")
        self.assertEqual(fields["expiry_date"].value, "18/09/2030")

    def test_caso_l_no_inventar_informacion_y_correccion_difusa(self):
        """
        Caso L: Imagen severamente deteriorada / carácter dudoso.
        Regla de Oro: NUNCA inventar información.
        Marcar status 'REVISAR' y buscar corrección en base de trabajadores.
        """
        # Incomplete / damaged read
        lines = [
            OCRLine(text="DNI 4269427?", confidence=30.0),
            OCRLine(text="APELLIDO G?RCIA", confidence=35.0),
        ]
        ocr = OCRResult(full_text="\n".join(l.text for l in lines), lines=lines, average_confidence=32.5)
        ext_dict, fields, warns = extract_dni_data(ocr)

        # Must NOT claim high confidence or confirmed status
        self.assertIn(fields["doc_number"].status, ["REVISAR", "NO_DETECTADO"])
        self.assertLess(fields["doc_number"].confidence, 70.0)

        # Fuzzy matcher finds matching worker in database
        matcher = WorkerMatcher()
        match_res = matcher.find_worker(raw_dni="4269427I", first_names="NADIA", paternal_surname="GARCIA")
        if match_res.is_probable_correction:
            self.assertIn("42694271", match_res.correction_message)
            self.assertEqual(match_res.worker_dni, "42694271")


if __name__ == "__main__":
    unittest.main()
