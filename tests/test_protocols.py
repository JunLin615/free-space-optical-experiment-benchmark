import copy
import unittest

from tools.protocols import (PROTOCOL_IDS, check_matched_runs, load_protocol,
                             payload_sha256, public_payload, validate_all,
                             validate_protocol)
from tools.scoring_runtime import load_scored_case


class ProtocolTests(unittest.TestCase):
    def test_four_permission_combinations_and_common_scaffold(self):
        self.assertEqual(validate_all(), [])
        combinations = set()
        for protocol_id in PROTOCOL_IDS:
            manifest = load_protocol(protocol_id)
            combinations.add((manifest["case_library_access"]["enabled"],
                              bool(manifest["tool_policy"]["allowed_tools"])))
            self.assertFalse(manifest["network_policy"]["external_access"])
        self.assertEqual(combinations, {(False, False), (True, False),
                                        (False, True), (True, True)})

    def test_permission_mismatch_rejected(self):
        manifest = copy.deepcopy(load_protocol("closed_book"))
        manifest["tool_policy"]["allowed_tools"] = ["calculator"]
        with self.assertRaisesRegex(ValueError, "permissions"):
            validate_protocol(manifest)

    def test_public_payload_excludes_gold_and_solution_shaped_contract(self):
        case = load_scored_case("SEED-1-1")
        payload = public_payload(case)
        self.assertEqual(payload["task"], case["task"])
        self.assertNotIn("gold", payload)
        self.assertNotIn("scoring", payload)
        self.assertNotIn("schema_id", payload["answer_contract"])
        self.assertIn("geometry_change", payload["answer_contract"]["method_shape"]["q3"])
        self.assertIn("unit: '1'", payload["answer_contract"]["method_shape"]["q3"])
        self.assertNotIn("distance-quarter", str(payload))
        self.assertNotIn("rotation-quarter", str(payload))
        first = payload_sha256(case)
        case["gold"]["reference_model"]["equation"] = "tampered"
        self.assertEqual(payload_sha256(case), first)
        case["task"]["statement"] += " modified"
        self.assertNotEqual(payload_sha256(case), first)
        waveplate = load_scored_case("SEED-1-7")
        exposed = str(public_payload(waveplate))
        self.assertNotIn("linear_rotation_rule_applies: false", exposed)
        self.assertNotIn("reversed handedness", exposed)

    def test_matched_runs_reject_scientific_prompt_change(self):
        base = {"case_id": "SEED-1-1", "case_revision": "0.1.5",
                "scientific_payload_sha256": "a" * 64,
                "scorer_id": "numerical", "scorer_fingerprint": "b" * 64,
                "result_schema_version": "0.1.0", "agent_identity": "provider/model/scaffold",
                "variant_id": None, "protocol_id": "closed_book", "protocol_version": "1.0.0"}
        assisted = {**base, "protocol_id": "case_assisted"}
        self.assertEqual(check_matched_runs([base, assisted]), [])
        assisted["scientific_payload_sha256"] = "c" * 64
        self.assertTrue(any("scientific_payload_sha256" in issue
                            for issue in check_matched_runs([base, assisted])))
        assisted["scientific_payload_sha256"] = base["scientific_payload_sha256"]
        assisted["agent_identity"] = "different"
        self.assertTrue(any("agent_identity" in issue
                            for issue in check_matched_runs([base, assisted])))


if __name__ == "__main__":
    unittest.main()
