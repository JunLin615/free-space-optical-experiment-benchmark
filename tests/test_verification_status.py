"""Lifecycle labels require executable evidence and pinned release assets."""

from __future__ import annotations

import copy
import unittest
from unittest.mock import patch

from tools import check_verification_status as status_gate


class VerificationStatusTests(unittest.TestCase):
    def test_current_challenged_cases_meet_development_gate(self) -> None:
        self.assertEqual(status_gate.check(), [])

    def test_label_alone_cannot_promote_a_case(self) -> None:
        original = status_gate.load_scored_case
        def changed(case_id):
            case = original(case_id)
            if case_id == "SEED-1-5":
                case = copy.deepcopy(case)
                case["validation_status"] = "release_verified"
                case["benchmark_release"] = "nonexistent-release"
            return case
        with patch.object(status_gate, "load_scored_case", side_effect=changed):
            issues = status_gate.check()
        self.assertTrue(any("missing pinned release manifest" in issue for issue in issues))
        self.assertTrue(any("public development split" in issue for issue in issues))


if __name__ == "__main__":
    unittest.main()
