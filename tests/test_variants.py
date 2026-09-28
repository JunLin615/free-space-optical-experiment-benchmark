"""Reproducibility, physics, scorer, and private-seed boundaries for variants."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import secrets
import tempfile
import unittest

from tools.physics_checks import check_numeric_claim, to_si
from tools.scoring_runtime import _content_hash, evaluate_case
from tools.variants import (
    PUBLIC_DIR, PUBLIC_PLAN, ROOT, SUPPORTED, _expected_answer, _parent,
    generate_private, generate_variant, load_variant, public_check_or_write,
    validate_variant, verify_private,
)


class VariantTests(unittest.TestCase):
    def test_public_set_reproducible_and_gold_free(self) -> None:
        public_check_or_write(check=True)
        plan = json.loads(PUBLIC_PLAN.read_text(encoding="utf-8"))["variants"]
        paths = list(PUBLIC_DIR.glob("*.json"))
        self.assertEqual(len(plan), 10)
        self.assertEqual(len(paths), 10)
        self.assertEqual({p["parent_case_id"] for p in plan}, set(SUPPORTED))
        for path in paths:
            stored = json.loads(path.read_text(encoding="utf-8"))
            self.assertNotIn("gold", stored)
            self.assertNotIn("case", stored)
            self.assertNotIn("reference", stored)
            self.assertEqual(stored["seed_classification"], "public_dev")
            self.assertEqual(stored, generate_variant(stored["parent_case_id"], stored["public_seed"], stored["variant_type"]))
            loaded = load_variant(path)
            self.assertEqual(loaded["case"]["case_id"], stored["parent_case_id"])
            self.assertEqual(loaded["case"]["case_revision"], stored["parent_case_revision"])
            self.assertNotEqual(_content_hash(loaded["case"]), stored["parent_case_content_sha256"])
            result = evaluate_case(loaded["case"], _expected_answer(loaded["case"]))
            self.assertEqual(result["scores"]["capped_total"], 1.0)
            self.assertEqual(result["failure_mode"], "none")

    def test_variants_change_scientific_parameters_and_contract_hints(self) -> None:
        for path in PUBLIC_DIR.glob("*.json"):
            record = load_variant(path)
            parent, _ = _parent(record["parent_case_id"])
            self.assertNotEqual(record["task"]["givens"], parent["task"]["givens"])
            self.assertNotEqual(record["scientific_payload_sha256"], _content_hash(parent["task"]))
            if record["parent_case_id"] == "SEED-1-1":
                self.assertNotIn("quarter", str(record["answer_contract"].get("method_shape", {})).lower())
            if record["parent_case_id"] == "SEED-1-7":
                self.assertNotIn("false", str(record["answer_contract"].get("method_shape", {})).lower())
            if record["parent_case_id"] == "SEED-4-2":
                givens = {g["symbol"]: g for g in record["task"]["givens"]}
                self.assertEqual(to_si(givens["quarter_mirror_displacement_wavelengths"]), 0.25)

    def test_corrupt_gold_and_task_hash_are_rejected(self) -> None:
        record = generate_variant("SEED-1-1", "audit-corruption", "parameter")
        case = validate_variant(record)
        bad_case = copy.deepcopy(case)
        bad_case["gold"]["numerical_checks"][0]["reference"]["value"] = 999
        check = bad_case["gold"]["numerical_checks"][0]
        self.assertNotEqual(check_numeric_claim(bad_case, check, check["reference"])["status"], "pass")
        result = evaluate_case(bad_case, _expected_answer(case))
        self.assertIsNone(result["scores"]["capped_total"])
        tampered = copy.deepcopy(record)
        tampered["task"]["givens"][0]["value"] = -1
        with self.assertRaises(ValueError):
            validate_variant(tampered)

    def test_private_seed_external_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self.assertFalse(base.resolve().is_relative_to(ROOT.resolve()))
            secret = secrets.token_hex(32)
            seed_file = base / "private-seed.json"
            seed_file.write_text(json.dumps({"seed": secret, "selections": [
                {"parent_case_id": "SEED-1-5", "variant_type": "parameter"},
                {"parent_case_id": "SEED-2-2", "variant_type": "structural_unit"},
            ]}), encoding="utf-8")
            paths = generate_private(seed_file, base / "instances")
            self.assertEqual(len(paths), 2)
            for path in paths:
                content = path.read_text(encoding="utf-8")
                self.assertNotIn(secret, content)
                self.assertNotIn("public_seed", content)
                loaded = verify_private(path, seed_file)
                self.assertEqual(loaded["seed_classification"], "private")
                self.assertEqual(loaded["case"]["split"], "hidden_eval")
                self.assertEqual(evaluate_case(loaded["case"], _expected_answer(loaded["case"]))["scores"]["capped_total"], 1.0)
            with self.assertRaises(FileExistsError):
                generate_private(seed_file, base / "instances")
            with self.assertRaises(ValueError):
                generate_private(ROOT / "benchmark/variants/public_plan.json", base / "other")


if __name__ == "__main__":
    unittest.main()
