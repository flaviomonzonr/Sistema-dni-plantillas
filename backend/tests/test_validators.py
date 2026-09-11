import unittest
from backend.extractors.validators import (
    validate_dni,
    validate_ce,
    normalize_and_validate_date,
    normalize_sex,
    clean_text,
)


class TestValidators(unittest.TestCase):
    def test_dni_valid(self):
        ok, norm, err = validate_dni("72345678")
        self.assertTrue(ok)
        self.assertEqual(norm, "72345678")
        self.assertIsNone(err)

    def test_dni_invalid_length(self):
        ok, norm, err = validate_dni("7234567")
        self.assertFalse(ok)
        self.assertIn("8 dígitos", err)

    def test_ce_valid(self):
        ok, norm, err = validate_ce("001234567")
        self.assertTrue(ok)
        self.assertEqual(norm, "001234567")

    def test_date_slash_format(self):
        ok, fmt, err = normalize_and_validate_date("15/08/1995")
        self.assertTrue(ok)
        self.assertEqual(fmt, "15/08/1995")

    def test_date_words_format(self):
        ok, fmt, err = normalize_and_validate_date("12 OCT 1990")
        self.assertTrue(ok)
        self.assertEqual(fmt, "12/10/1990")

    def test_date_invalid_calendar(self):
        ok, fmt, err = normalize_and_validate_date("31/02/1990")
        self.assertFalse(ok)

    def test_sex_normalization(self):
        self.assertEqual(normalize_sex("M")[1], "M")
        self.assertEqual(normalize_sex("FEMENINO")[1], "F")
        self.assertEqual(normalize_sex("F")[1], "F")


if __name__ == "__main__":
    unittest.main()
