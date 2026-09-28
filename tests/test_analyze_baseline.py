"""Analysis keeps scientific comparability and release status visible."""

from __future__ import annotations

import unittest

from tools.analyze_baseline import analyze, paired_differences


def record(case_id: str, track: str, protocol: str, score: float | None,
           *, payload_hash: str = "a" * 64, variant_id: str | None = None) -> dict:
    failure = "none" if score is not None else "oracle_unresolved"
    return {
        "run_id": "sample", "execution_class": "real", "status": "completed",
        "selection": {"case_id": case_id, "case_revision": "0.1.5", "variant_id": variant_id,
                      "track": track, "case_content_sha256": "c" * 64},
        "protocol": {"id": protocol, "version": "1.0.0", "scientific_payload_sha256": payload_hash},
        "agent_identity": {"provider": "sample", "model_id": "same-model"},
        "failure_class": None, "first_attempt_success": score == 1.0,
        "retrieval": None, "tool_calls": [],
        "usage": {"input": 100, "output": 20, "total": 120, "cached_input": None, "reasoning": None},
        "cost": None, "wall_time_seconds": 2.0,
        "score_result": {"case_id": case_id, "case_revision": "0.1.5",
                         "case_content_sha256": "c" * 64, "evaluator_version": "0.1.1",
                         "evaluator_fingerprint": "d" * 64, "result_schema_version": "0.1.0",
                         "scores": {"capped_total": score}, "failure_mode": failure},
    }


class BaselineAnalysisTests(unittest.TestCase):
    def test_verified_development_and_variants_never_share_headline_score(self) -> None:
        records = [
            record("SEED-1-1", "verified", "closed_book", 0.0),
            record("SEED-1-1", "verified", "case_assisted", 1.0),
            record("SEED-7-2", "development", "closed_book", None),
            record("SEED-1-1", "public_variant", "closed_book", 1.0, variant_id="VAR-1"),
        ]
        summary = analyze({"run_id": "sample", "execution_class": "real",
                           "protocol_ids": ["closed_book", "case_assisted"], "selections": [{}, {}]}, records)
        self.assertEqual(summary["verified"]["overall"]["mean_score"], 0.5)
        self.assertEqual(summary["development"]["unresolved_rate"], 1.0)
        self.assertEqual(summary["variants"]["mean_score"], 1.0)
        pair = summary["paired"]["per_case"]
        self.assertEqual(len(pair), 1)
        self.assertEqual(pair[0]["score_delta"], 1.0)
        self.assertIsNone(summary["verified"]["overall"]["cost"]["amount"])

    def test_different_scientific_payload_blocks_paired_comparison(self) -> None:
        records = [record("SEED-1-1", "verified", "closed_book", 1.0),
                   record("SEED-1-1", "verified", "tool_assisted", 1.0, payload_hash="b" * 64)]
        with self.assertRaisesRegex(ValueError, "matched scientific payload differs"):
            paired_differences(records)

    def test_unknown_usage_is_not_reported_as_zero(self) -> None:
        one = record("SEED-1-1", "verified", "closed_book", 1.0)
        one["usage"]["total"] = None
        summary = analyze({"run_id": "sample", "execution_class": "real",
                           "protocol_ids": ["closed_book"], "selections": [{}]}, [one])
        self.assertIsNone(summary["verified"]["overall"]["usage"]["total"]["total"])
        self.assertIsNone(summary["verified"]["overall"]["tokens_per_success"])

    def test_scorer_mismatch_or_invalid_instance_cannot_skew_candidate_rate(self) -> None:
        first = record("SEED-1-1", "verified", "closed_book", 1.0)
        second = record("SEED-1-1", "verified", "tool_assisted", None)
        second["score_result"]["failure_mode"] = "invalid_instance"
        summary = analyze({"run_id": "sample", "execution_class": "real",
                           "protocol_ids": ["closed_book", "tool_assisted"], "selections": [{}]}, [first, second])
        self.assertEqual(summary["verified"]["overall"]["candidate_outcomes"], 1)
        self.assertEqual(summary["verified"]["overall"]["task_success_rate"], 1.0)
        second["score_result"]["evaluator_fingerprint"] = "e" * 64
        with self.assertRaisesRegex(ValueError, "matched case/scorer/schema/protocol version differs"):
            paired_differences([first, second])


if __name__ == "__main__":
    unittest.main()
