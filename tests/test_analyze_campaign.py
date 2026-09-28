"""Campaign validation protects frozen comparisons and public evidence."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools.analyze_campaign import CASES, PROTOCOLS, ROOT, _efficiency, _formal, evidence_commitment
from tests.test_analyze_baseline import record


def _release() -> dict:
    return json.loads((ROOT / "benchmark" / "releases" / "0.2.0-rc1.json").read_text(encoding="utf-8"))


def _matrix() -> tuple[dict, list[dict]]:
    release = _release()
    manifest = {"run_id": "formal-test", "release_id": "0.2.0-rc1",
                "agent": {"provider": "test", "model_id": "test-model", "model_version": None,
                          "framework": "test-framework", "scaffold_id": None,
                          "adapter_type": "codex_cli"},
                "system_prompt_version": "neutral_optics_v1",
                "retry_policy": {"transport_max_retries": 0, "malformed_answer_max_retries": 0,
                                 "self_correction_max_retries": 0},
                "selections": [{"case_id": case_id, "track": "verified", "variant_path": None}
                               for case_id in CASES],
                "protocol_ids": list(PROTOCOLS)}
    records = []
    for case_id in CASES:
        pin = release["cases"][case_id]
        for protocol in PROTOCOLS:
            item = record(case_id, "verified", protocol, 1.0)
            item["selection"]["case_revision"] = pin["case_revision"]
            item["selection"]["case_content_sha256"] = pin["case_content_sha256"]
            item["score_result"]["case_revision"] = pin["case_revision"]
            item["score_result"]["case_content_sha256"] = pin["case_content_sha256"]
            item["score_result"]["evaluator_version"] = pin["evaluator_version"]
            item["score_result"]["evaluator_fingerprint"] = pin["evaluator_fingerprint"]
            item["agent_identity"] = {"provider": "test", "model_id": "test-model",
                                      "model_version": None, "framework": "test-framework",
                                      "scaffold_id": None, "adapter_type": "codex_cli",
                                      "system_prompt_version": "neutral_optics_v1"}
            records.append(item)
    return manifest, records


class CampaignAnalysisTests(unittest.TestCase):
    def test_complete_formal_matrix_has_all_five_paired_contrasts(self) -> None:
        manifest, records = _matrix()
        systems = _formal(_release(), [(manifest, records)])
        self.assertEqual(systems[0]["record_count"], 36)
        self.assertEqual(len(systems[0]["paired"]["per_case"]), 45)
        self.assertEqual(systems[0]["efficiency"]["tokens_per_successful_case"], 120)

    def test_missing_case_or_changed_frozen_pin_fails(self) -> None:
        manifest, records = _matrix()
        with self.assertRaisesRegex(ValueError, "exactly nine cases"):
            _formal(_release(), [(manifest, records[:-1])])
        records[0]["score_result"]["evaluator_fingerprint"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "frozen evaluator pin"):
            _formal(_release(), [(manifest, records)])

    def test_unknown_cost_and_tokens_remain_null(self) -> None:
        _, records = _matrix()
        records[0]["usage"]["total"] = None
        resource = _efficiency(records)
        self.assertIsNone(resource["tokens_total"])
        self.assertIsNone(resource["tokens_per_successful_case"])
        self.assertIsNone(resource["cost_total"])
        self.assertIsNone(resource["cost_per_attempted_case"])

    def test_evidence_tree_detects_file_mutation_and_rejects_partial(self) -> None:
        with TemporaryDirectory() as directory:
            run = Path(directory)
            (run / "manifest.json").write_text("{}", encoding="utf-8")
            (run / "results").mkdir()
            result = run / "results" / "one.json"
            result.write_text("one", encoding="utf-8")
            first = evidence_commitment(run)
            result.write_text("two", encoding="utf-8")
            self.assertNotEqual(first["evidence_tree_sha256"], evidence_commitment(run)["evidence_tree_sha256"])
            (run / "results" / "two.json.partial").write_text("partial", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "partial"):
                evidence_commitment(run)


if __name__ == "__main__":
    unittest.main()
