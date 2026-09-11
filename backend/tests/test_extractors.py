import unittest
from backend.ocr.base import OCRResult, OCRLine, OCRWord
from backend.extractors.dni_extractor import extract_dni_data, parse_icao_td1_mrz
from backend.extractors.ce_extractor import extract_ce_data


class TestExtractors(unittest.TestCase):
    def test_mrz_icao_td1_parsing(self):
        mrz_raw = (
            "I<PER458923140<<<<<<<<<<<<<<<\n"
            "9205146M3205144PER<<<<<<<<<<<4\n"
            "MENDOZA<QUISPE<<JUAN<CARLOS<<\n"
        )
        parsed = parse_icao_td1_mrz(mrz_raw)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["dni"], "45892314")
        self.assertEqual(parsed["paternal_surname"], "MENDOZA")
        self.assertEqual(parsed["maternal_surname"], "QUISPE")
        self.assertEqual(parsed["first_names"], "JUAN CARLOS")
        self.assertEqual(parsed["sex"], "M")
        self.assertEqual(parsed["birth_date"], "14/05/1992")
        self.assertEqual(parsed["expiry_date"], "14/05/2032")

    def test_dni_extraction_with_ocr_lines(self):
        front_lines = [
            OCRLine(text="REPÚBLICA DEL PERÚ", confidence=95.0),
            OCRLine(text="DOCUMENTO NACIONAL DE IDENTIDAD", confidence=92.0),
            OCRLine(text="DNI 45892314", confidence=96.0),
            OCRLine(text="PRIMER APELLIDO: MENDOZA", confidence=90.0),
            OCRLine(text="SEGUNDO APELLIDO: QUISPE", confidence=88.0),
            OCRLine(text="PRENOMBRES: JUAN CARLOS", confidence=91.0),
            OCRLine(text="SEXO: M", confidence=95.0),
            OCRLine(text="FECHA DE NACIMIENTO: 14/05/1992", confidence=94.0),
        ]
        back_lines = [
            OCRLine(text="DOMICILIO: AV. AREQUIPA 1234 DPTO 502", confidence=87.0),
            OCRLine(text="UBIGEO: LIMA - LIMA - MIRAFLORES", confidence=89.0),
            OCRLine(text="FECHA DE EMISION: 10/06/2022", confidence=92.0),
            OCRLine(text="FECHA DE CADUCIDAD: 10/06/2030", confidence=91.0),
            OCRLine(text="GRUPO SANGUINEO: O+", confidence=85.0),
            OCRLine(text="ESTADO CIVIL: SOLTERO", confidence=88.0),
        ]
        front_ocr = OCRResult(lines=front_lines, full_text="\n".join([l.text for l in front_lines]))
        back_ocr = OCRResult(lines=back_lines, full_text="\n".join([l.text for l in back_lines]))

        data, fields, warnings = extract_dni_data(front_ocr, back_ocr)

        self.assertEqual(data["doc_number"], "45892314")
        self.assertEqual(data["paternal_surname"], "MENDOZA")
        self.assertEqual(data["maternal_surname"], "QUISPE")
        self.assertEqual(data["first_names"], "JUAN CARLOS")
        self.assertEqual(data["sex"], "M")
        self.assertEqual(data["birth_date"], "14/05/1992")
        self.assertIn("AV. AREQUIPA", data["address"])
        self.assertEqual(data["blood_type"], "O+")
        self.assertEqual(data["civil_status"], "SOLTERO")
        self.assertTrue(fields["doc_number"].is_valid)

    def test_ce_extraction(self):
        front_lines = [
            OCRLine(text="SUPERINTENDENCIA NACIONAL DE MIGRACIONES", confidence=95.0),
            OCRLine(text="CARNET DE EXTRANJERIA N° 001458963", confidence=94.0),
            OCRLine(text="PRIMER APELLIDO: RODRIGUEZ", confidence=90.0),
            OCRLine(text="SEGUNDO APELLIDO: PEREZ", confidence=89.0),
            OCRLine(text="NOMBRES: MARIA ALEJANDRA", confidence=92.0),
            OCRLine(text="NACIONALIDAD: VENEZOLANA", confidence=95.0),
            OCRLine(text="FECHA DE NACIMIENTO: 25/11/1988", confidence=93.0),
            OCRLine(text="SEXO: F", confidence=96.0),
        ]
        back_lines = [
            OCRLine(text="CALIDAD MIGRATORIA: TRABAJADOR RESIDENTE", confidence=90.0),
            OCRLine(text="FECHA DE EMISION: 01/03/2021", confidence=92.0),
            OCRLine(text="FECHA DE VENCIMIENTO: 01/03/2026", confidence=91.0),
        ]
        front_ocr = OCRResult(lines=front_lines, full_text="\n".join([l.text for l in front_lines]))
        back_ocr = OCRResult(lines=back_lines, full_text="\n".join([l.text for l in back_lines]))

        data, fields, warnings = extract_ce_data(front_ocr, back_ocr)

        self.assertEqual(data["doc_number"], "001458963")
        self.assertEqual(data["paternal_surname"], "RODRIGUEZ")
        self.assertEqual(data["maternal_surname"], "PEREZ")
        self.assertEqual(data["first_names"], "MARIA ALEJANDRA")
        self.assertEqual(data["nationality"], "VENEZOLANA")
        self.assertEqual(data["migratory_status"], "TRABAJADOR RESIDENTE")
        self.assertTrue(fields["doc_number"].is_valid)

    def test_user_dni_mrz_extraction(self):
        """Test exact MRZ highlighted in user's image (HERRERA HILDEBRANDO, 02763215, 11/05/1963, NO CADUCA)."""
        mrz_raw = (
            "I<PER02763215<8<<<<<<<<<<<<<<<\n"
            "6305110M0001018PER<<<<<<<<<<<0\n"
            "HERRERA<<HILDEBRANDO<<<<<<<<<\n"
        )
        parsed = parse_icao_td1_mrz(mrz_raw)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["dni"], "02763215")
        self.assertEqual(parsed["birth_date"], "11/05/1963")
        self.assertEqual(parsed["sex"], "M")
        self.assertEqual(parsed["expiry_date"], "NO CADUCA")
        self.assertEqual(parsed["paternal_surname"], "HERRERA")
        self.assertEqual(parsed["first_names"], "HILDEBRANDO")

    def test_noisy_mrz_ocr_substitutions(self):
        """Test MRZ with common OCR substitutions (O->0, 1->I, spaces, missing delimiters)."""
        mrz_noisy = (
            "1<PERO2763215<8 < < < < < < < < < < < < < < <\n"
            "63O511 0 M 000101 8 PER < < < < < < < < < < < 0\n"
            "HERRERA < < HILDEBRANDO < < < < < < < < <\n"
        )
        parsed = parse_icao_td1_mrz(mrz_noisy)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["dni"], "02763215")
        self.assertEqual(parsed["birth_date"], "11/05/1963")
        self.assertEqual(parsed["sex"], "M")
        self.assertEqual(parsed["expiry_date"], "NO CADUCA")

    def test_visual_fecha_y_ubigeo_extraction(self):
        """Test visual card with 'Nacimiento: Fecha y Ubigeo' followed by date and ubigeo code."""
        front_lines = [
            OCRLine(text="REPÚBLICA DEL PERÚ", confidence=95.0),
            OCRLine(text="DOCUMENTO NACIONAL DE IDENTIDAD DNI 02763215-2", confidence=92.0),
            OCRLine(text="Primer Apellido: HERRERA", confidence=90.0),
            OCRLine(text="Segundo Apellido: NIMA", confidence=88.0),
            OCRLine(text="Pre Nombres: HILDEBRANDO", confidence=91.0),
            OCRLine(text="Nacimiento: Fecha y Ubigeo", confidence=89.0),
            OCRLine(text="11 05 1963    190109", confidence=90.0),
            OCRLine(text="Sexo: M    Estado Civil: S", confidence=93.0),
            OCRLine(text="Fecha Emision: 08 07 2025", confidence=88.0),
            OCRLine(text="Fecha Caducidad: NO CADUCA", confidence=95.0),
        ]
        front_ocr = OCRResult(lines=front_lines, full_text="\n".join([l.text for l in front_lines]))
        data, fields, warnings = extract_dni_data(front_ocr)

        self.assertEqual(data["doc_number"], "02763215")
        self.assertEqual(data["paternal_surname"], "HERRERA")
        self.assertEqual(data["maternal_surname"], "NIMA")
        self.assertEqual(data["first_names"], "HILDEBRANDO")
        self.assertEqual(data["birth_date"], "11/05/1963")
        self.assertEqual(data["sex"], "M")
        self.assertEqual(data["civil_status"], "SOLTERO")
        self.assertEqual(data["expiry_date"], "NO CADUCA")
        self.assertTrue(fields["doc_number"].is_valid)
        self.assertTrue(fields["birth_date"].is_valid)


if __name__ == "__main__":
    unittest.main()
