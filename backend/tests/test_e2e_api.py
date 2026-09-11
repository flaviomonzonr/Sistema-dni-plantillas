import unittest
import io
import cv2
import numpy as np
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import init_db
from backend.config import MASTER_EXCEL_PATH

client = TestClient(app)


class TestAPIEndToEnd(unittest.TestCase):
    def setUp(self):
        init_db()

    def create_synthetic_image_bytes(self, text_lines):
        img = np.full((640, 1014, 3), 245, dtype=np.uint8)
        # Draw border
        cv2.rectangle(img, (20, 20), (994, 620), (200, 50, 50), 4)
        y = 80
        for line in text_lines:
            cv2.putText(img, line, (50, y), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
            y += 50
        _, buf = cv2.imencode(".jpg", img)
        return io.BytesIO(buf.tobytes())

    def test_health_endpoint(self):
        res = client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "healthy")

    def test_scan_and_save_flow(self):
        front_lines = [
            "REPUBLICA DEL PERU",
            "DNI 87654321",
            "PRIMER APELLIDO: QUISPE",
            "SEGUNDO APELLIDO: MAMANI",
            "PRENOMBRES: JORGE LUIS",
            "SEXO: M",
            "FECHA DE NACIMIENTO: 20/08/1990",
        ]
        back_lines = [
            "DOMICILIO: JR. DE LA UNION 450",
            "UBIGEO: LIMA - LIMA - LIMA",
            "FECHA DE EMISION: 01/01/2021",
            "FECHA DE CADUCIDAD: 01/01/2029",
            "GRUPO SANGUINEO: O+",
            "ESTADO CIVIL: CASADO",
        ]

        front_file = self.create_synthetic_image_bytes(front_lines)
        back_file = self.create_synthetic_image_bytes(back_lines)

        # 1. Scan document
        scan_res = client.post(
            "/api/scan",
            data={"doc_type": "DNI"},
            files={
                "front_image": ("front.jpg", front_file, "image/jpeg"),
                "back_image": ("back.jpg", back_file, "image/jpeg"),
            },
        )
        self.assertEqual(scan_res.status_code, 200)
        scan_data = scan_res.json()
        self.assertTrue(scan_data["success"])
        self.assertIn("quality_front", scan_data)
        self.assertIn("quality_back", scan_data)

        # 2. Save record to DB and Excel
        record_payload = {
            "doc_type": "DNI",
            "doc_number": "87654321",
            "paternal_surname": "QUISPE",
            "maternal_surname": "MAMANI",
            "first_names": "JORGE LUIS",
            "nationality": "PERUANA",
            "birth_date": "20/08/1990",
            "sex": "M",
            "address": "JR. DE LA UNION 450",
            "ubigeo": "LIMA / LIMA / LIMA",
            "issue_date": "01/01/2021",
            "expiry_date": "01/01/2029",
            "blood_type": "O+",
            "civil_status": "CASADO",
            "observations": "Test de integracion",
            "front_image_orig": scan_data["front_image_orig"],
            "front_image_enhanced": scan_data["front_image_enhanced"],
            "back_image_orig": scan_data["back_image_orig"],
            "back_image_enhanced": scan_data["back_image_enhanced"],
            "quality_score_front": scan_data["quality_front"]["laplacian_var"],
            "quality_score_back": scan_data["quality_back"]["laplacian_var"],
        }

        save_res = client.post("/api/records", json=record_payload)
        self.assertEqual(save_res.status_code, 200)
        saved_data = save_res.json()
        record_id = saved_data["id"]
        self.assertEqual(saved_data["doc_number"], "87654321")

        # 3. List records
        list_res = client.get("/api/records?search=87654321")
        self.assertEqual(list_res.status_code, 200)
        list_data = list_res.json()
        self.assertGreaterEqual(list_data["total"], 1)

        # 4. Get stats
        stats_res = client.get("/api/records/stats")
        self.assertEqual(stats_res.status_code, 200)
        stats_data = stats_res.json()
        self.assertGreaterEqual(stats_data["total_records"], 1)

        # 5. Export Excel
        export_res = client.get("/api/export-excel")
        self.assertEqual(export_res.status_code, 200)
        self.assertIn("application/vnd.openxmlformats", export_res.headers["content-type"])

        # 6. Delete test record
        del_res = client.delete(f"/api/records/{record_id}")
        self.assertEqual(del_res.status_code, 200)

    def test_scan_and_save_atomic_endpoint(self):
        front_lines = [
            "REPUBLICA DEL PERU",
            "DNI 99887766",
            "PRIMER APELLIDO: BATCH",
            "SEGUNDO APELLIDO: TESTER",
            "PRENOMBRES: LUIS ALBERTO",
            "FECHA DE NACIMIENTO: 12/03/1992",
        ]
        back_lines = [
            "DOMICILIO: CALLE LAS FLORES 123",
            "UBIGEO: 150101",
            "ESTADO CIVIL: SOLTERO",
            "FECHA DE EMISION: 05/05/2020",
        ]

        front_file = self.create_synthetic_image_bytes(front_lines)
        back_file = self.create_synthetic_image_bytes(back_lines)

        res = client.post(
            "/api/scan-and-save",
            data={"doc_type": "DNI"},
            files={
                "front_image": ("1.A.jpg", front_file, "image/jpeg"),
                "back_image": ("1.R.jpg", back_file, "image/jpeg"),
            },
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertIn("record", data)
        self.assertIn("id", data["record"])
        record_id = data["record"]["id"]

        # Clean up
        client.delete(f"/api/records/{record_id}")


if __name__ == "__main__":
    unittest.main()

