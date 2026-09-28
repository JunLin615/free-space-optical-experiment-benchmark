"""Independent checks for the text-only Chinese public localization."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

import yaml

from tools.render_cases import DEFAULT_CASES, load_cases
from tools.render_zh_cn import (
    OVERLAY, load_localized_cases, public_fingerprint, render_html, render_markdown,
)


class LocalizationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.case = {
            "case_id": "TEST-1", "title": "Test 1 nm", "language": "en",
            "task": {
                "statement": "Beam wavelength is 1 nm.",
                "questions": [{"id": "q1", "request": "Measure at 2 mm."}],
                "givens": [{"symbol": "wavelength", "value": 1, "unit": "nm"}],
            },
            "gold": {"reference": "SECRET_GOLD"},
            "scoring": {"rubric": "SECRET_SCORING"},
        }
        self.overlay = {
            "schema_version": 1, "locale": "zh-CN",
            "canonical_public_sha256": public_fingerprint([self.case]),
            "cases": {"TEST-1": {
                "title": "测试 1 nm", "statement": "波长为 {{wavelength}}。",
                "questions": {"q1": "在 2 mm 处测量。"},
                "assumptions": [], "apparatus_constraints": [],
            }},
        }

    def load(self) -> list[dict]:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "zh.yaml"
            path.write_text(yaml.safe_dump(self.overlay, allow_unicode=True, sort_keys=False), encoding="utf-8")
            return load_localized_cases([self.case], path, expected_count=1)

    def test_public_render_inherits_givens_without_gold_leakage(self) -> None:
        localized = self.load()
        self.assertEqual(localized[0]["givens"], self.case["task"]["givens"])
        for result in (render_markdown(localized), render_html(localized)):
            self.assertIn("1 nm", result)
            self.assertIn("2 mm", result)
            self.assertNotIn("SECRET_GOLD", result)
            self.assertNotIn("SECRET_SCORING", result)

    def test_rejects_missing_question_and_extra_case(self) -> None:
        self.overlay["cases"]["TEST-1"]["questions"] = {}
        with self.assertRaisesRegex(ValueError, "question IDs/order"):
            self.load()
        self.overlay["cases"]["TEST-1"]["questions"] = {"q1": "在 2 mm 处测量。"}
        self.overlay["cases"]["EXTRA"] = self.overlay["cases"]["TEST-1"]
        with self.assertRaisesRegex(ValueError, "case IDs or order"):
            self.load()

    def test_rejects_stale_source_and_numeric_translation_error(self) -> None:
        self.case["task"]["questions"][0]["request"] = "Measure at 3 mm."
        with self.assertRaisesRegex(ValueError, "stale"):
            self.load()
        self.overlay["canonical_public_sha256"] = public_fingerprint([self.case])
        with self.assertRaisesRegex(ValueError, "numeric literal parity"):
            self.load()

    def test_actual_64_case_parity(self) -> None:
        english = load_cases(DEFAULT_CASES)
        chinese = load_localized_cases(english, OVERLAY)
        self.assertEqual(len(english), len(chinese), 64)
        self.assertEqual([case["case_id"] for case in english], [case["case_id"] for case in chinese])
        self.assertEqual(
            sum(len(case["task"]["questions"]) for case in english),
            sum(len(case["questions"]) for case in chinese),
        )


if __name__ == "__main__":
    unittest.main()
