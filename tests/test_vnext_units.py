"""Versioned unit equivalence and dimensional-failure regressions."""

from __future__ import annotations

import unittest

from tools.physics_checks import PhysicsCheckError, to_si
from tools.vnext.units import normalize_answer_units


class VNextUnitTests(unittest.TestCase):
    def test_approved_dimensionless_aliases(self) -> None:
        for unit, value in (("1", 0.7), ("dimensionless", 0.7), ("unitless", 0.7), ("%", 70), ("percent", 70)):
            with self.subTest(unit=unit):
                original = {"answers": {"q1": {"value": value, "unit": unit}}}
                normalized = normalize_answer_units(original)
                self.assertAlmostEqual(to_si(normalized["answers"]["q1"], "dimensionless"), 0.7)
                self.assertEqual(original["answers"]["q1"]["unit"], unit)

    def test_explicit_length_time_frequency_and_angle_aliases(self) -> None:
        examples = (("cm", 3, "length", 0.03), ("μm", 3, "length", 3e-6),
                    ("ns", 3, "time", 3e-9), ("THz", 3, "frequency", 3e12),
                    ("degrees", 180, "angle", 3.141592653589793))
        for unit, value, dimension, expected in examples:
            with self.subTest(unit=unit):
                quantity = normalize_answer_units({"value": value, "unit": unit})
                self.assertAlmostEqual(to_si(quantity, dimension), expected)

    def test_wrong_dimensions_and_unsupported_wavelength_unit(self) -> None:
        for unit, expected in (("mm", "dimensionless"), ("Hz", "time"), ("dimensionless", "length"), ("wavelength", "length")):
            with self.subTest(unit=unit):
                quantity = normalize_answer_units({"value": 3, "unit": unit})
                with self.assertRaises(PhysicsCheckError):
                    to_si(quantity, expected)

    def test_malformed_quantity_is_not_repaired(self) -> None:
        answer = {"value": True, "unit": "percent"}
        self.assertEqual(normalize_answer_units(answer), answer)
        with self.assertRaises(PhysicsCheckError):
            to_si(answer, "dimensionless")


if __name__ == "__main__":
    unittest.main()
