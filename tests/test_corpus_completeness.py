"""The original seed is immutable and every legacy ID has one canonical case."""

from __future__ import annotations

import copy
from pathlib import Path
import unittest

from tools.check_corpus import check, record_issues
from tools.scoring_runtime import load_scored_case


class CorpusCompletenessTests(unittest.TestCase):
    def test_complete_seed_lineage(self) -> None:
        self.assertEqual(check(), [])

    def test_mismatched_lineage_and_missing_notes_fail(self) -> None:
        case = copy.deepcopy(load_scored_case("SEED-1-5"))
        case["provenance"]["source_hash"] = "wrong"
        case["provenance"]["seed_relationship"] = "unrelated"
        case["provenance"]["derivation"] = ""
        issues = record_issues(case, Path("SEED-1-5.yaml"))
        self.assertTrue(any("SHA-256" in issue for issue in issues))
        self.assertTrue(any("seed relationship" in issue for issue in issues))
        self.assertTrue(any("translation or clarification" in issue for issue in issues))


if __name__ == "__main__":
    unittest.main()
