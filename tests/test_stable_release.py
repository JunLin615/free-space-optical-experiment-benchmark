"""Stable release lineage and its autonomous scoring entry point."""

from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from tools.qualify_stable import CASE_IDS, CORRECTED, MANIFEST, ROOT, _source, build
from tools.score_stable import score


class StableReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.expected_manifest, cls.qualification = build()

    def test_nine_cases_and_corrected_lineage(self) -> None:
        self.assertEqual(len(CASE_IDS), 9)
        self.assertEqual(set(CASE_IDS), set(self.expected_manifest["cases"]))
        self.assertEqual(self.expected_manifest["cases"][CORRECTED]["source_release"], "0.2.0")
        self.assertEqual(self.expected_manifest["cases"][CORRECTED]["case_path"],
                         "benchmark/cases_stable/SEED-3-1.yaml")
        self.assertEqual(self.qualification["unresolved_release_fixture_count"], 0)
        self.assertEqual(self.expected_manifest["judge"], {"mode": "disabled"})

    def test_autonomous_scoring_accepts_reference_for_each_released_case(self) -> None:
        saved = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(saved, self.expected_manifest)
        with patch("tools.score_stable.build", return_value=(self.expected_manifest, self.qualification)):
            for case_id in CASE_IDS:
                with self.subTest(case_id=case_id):
                    _, _, fixture_folder = _source(case_id)
                    paths = sorted((ROOT / fixture_folder / case_id).glob("*.json"))
                    reference = next(
                        json.loads(path.read_text(encoding="utf-8")) for path in paths
                        if json.loads(path.read_text(encoding="utf-8"))["kind"] == "positive"
                    )
                    result = score(case_id, reference["answer"])
                    self.assertEqual(result["scores"]["capped_total"], 1)
                    self.assertEqual(result["failure_mode"], "none")
                    self.assertEqual(result["benchmark_version"], "0.2.0")

    def test_entry_point_rejects_case_outside_release(self) -> None:
        with patch("tools.score_stable.build", return_value=(self.expected_manifest, self.qualification)):
            with self.assertRaisesRegex(ValueError, "not in stable release"):
                score("SEED-8-1", {})


if __name__ == "__main__":
    unittest.main()
