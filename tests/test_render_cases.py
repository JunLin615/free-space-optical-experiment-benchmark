"""Focused tests for the public, reproducible question rendering."""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
import tempfile
import unittest

import yaml

from tools.render_cases import generate, load_cases, render_html, render_markdown


class RenderCasesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.case = {
            "case_id": "SEED-2.1",
            "title": "Beam <alignment>",
            "language": "en",
            "task": {
                "statement": "Measure <x> at two planes.",
                "givens": [{"symbol": "z", "value": 2, "unit": "m"}],
                "assumptions": ["Paraxial propagation."],
                "questions": [{"id": "q1", "request": "Find the signed angle."}],
                "allowed_resources": "Any scientific tool.",
            },
            "gold": {"reference": "SECRET_REFERENCE_SENTINEL"},
            "scoring": {"rubric": "SECRET_RUBRIC_SENTINEL"},
        }

    def test_public_rendering_excludes_evaluator_material(self) -> None:
        markdown = render_markdown([self.case])
        html = render_html([self.case])
        for rendered in (markdown, html):
            self.assertIn("Find the signed angle.", rendered)
            self.assertIn("z = 2 m", rendered)
            self.assertNotIn("SECRET_REFERENCE_SENTINEL", rendered)
            self.assertNotIn("SECRET_RUBRIC_SENTINEL", rendered)
        self.assertIn("&lt;alignment&gt;", html)
        self.assertIn("&lt;x&gt;", html)

    def test_generation_check_detects_drift_and_case_order_is_numeric(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            cases = root / "cases"
            output = root / "out"
            cases.mkdir()
            for case_id in ("SEED-10.1", "SEED-2.1"):
                case = {**self.case, "case_id": case_id}
                (cases / f"{case_id}.yaml").write_text(yaml.safe_dump(case), encoding="utf-8")
            self.assertEqual([case["case_id"] for case in load_cases(cases)], ["SEED-2.1", "SEED-10.1"])
            with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                self.assertEqual(generate(cases, output), 0)
                self.assertEqual(generate(cases, output, check=True), 0)
            rendered = output / "questions.md"
            self.assertLess(rendered.read_text(encoding="utf-8").index("SEED-2.1"), rendered.read_text(encoding="utf-8").index("SEED-10.1"))
            rendered.write_text("stale", encoding="utf-8")
            with redirect_stderr(StringIO()):
                self.assertEqual(generate(cases, output, check=True), 1)


if __name__ == "__main__":
    unittest.main()
