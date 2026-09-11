import unittest
import cv2
import numpy as np
from backend.image_processing.pipeline import process_id_image, calculate_sharpness


class TestImagePipeline(unittest.TestCase):
    def test_sharp_synthetic_image(self):
        # Create a synthetic sharp image with high-contrast text lines
        img = np.full((600, 900, 3), 240, dtype=np.uint8)
        cv2.putText(img, "REPUBLICA DEL PERU", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 3)
        cv2.putText(img, "DNI 72345678", (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 3)
        
        _, img_encoded = cv2.imencode(".jpg", img)
        result = process_id_image(img_encoded.tobytes(), blur_threshold=50.0)

        self.assertIsNotNone(result)
        self.assertFalse(result.is_blurry)
        self.assertGreater(result.laplacian_variance, 50.0)
        self.assertEqual(result.clahe_enhanced.shape[0], result.warped_bgr.shape[0])

    def test_blurry_synthetic_image(self):
        # Create a heavily blurred image
        img = np.full((600, 900, 3), 200, dtype=np.uint8)
        cv2.putText(img, "Faded Text", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (150, 150, 150), 1)
        blurred = cv2.GaussianBlur(img, (51, 51), 30)

        _, img_encoded = cv2.imencode(".jpg", blurred)
        result = process_id_image(img_encoded.tobytes(), blur_threshold=100.0)

        self.assertIsNotNone(result)
        self.assertTrue(result.is_blurry)
        self.assertIn("borrosa", result.quality_message)


if __name__ == "__main__":
    unittest.main()
