import copy
import unittest
from unittest.mock import patch

from tools.case_library import audit_leakage, load_items
from tools.retrieval import retrieve


class CaseLibraryTests(unittest.TestCase):
    def test_index_hashes_and_no_obvious_corpus_leakage(self):
        self.assertGreaterEqual(len(load_items()), 4)
        self.assertEqual(audit_leakage(), [])

    def test_retrieval_is_stable_and_records_exact_supplied_bytes(self):
        query = "align laser beam with two irises"
        first = retrieve(query)
        second = retrieve(query)
        self.assertEqual(first["retrieved_ids"], second["retrieved_ids"])
        self.assertEqual(first["scores"], second["scores"])
        self.assertEqual(first["library_index_sha256"], second["library_index_sha256"])
        self.assertEqual(first["retrieved_ids"][0], "EX-ALIGN-01")
        self.assertEqual(first["item_count"], len(first["items"]))
        self.assertEqual(first["total_retrieved_tokens"],
                         sum(item["estimated_tokens"] for item in first["items"]))
        self.assertTrue(all(item["text"] and len(item["content_sha256"]) == 64
                            for item in first["items"]))

    def test_protocol_without_library_cannot_retrieve(self):
        for protocol_id in ("closed_book", "tool_assisted"):
            with self.assertRaisesRegex(ValueError, "forbids"):
                retrieve("beam", protocol_id=protocol_id)
        with self.assertRaisesRegex(ValueError, "cap"):
            retrieve("beam", max_items=4)

    def test_library_hash_tampering_is_detected(self):
        from tools import case_library
        original = case_library.INDEX_PATH
        import json
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as temporary:
            index = json.loads(original.read_text(encoding="utf-8"))
            index["items"][0]["content_sha256"] = "0" * 64
            temp_index = Path(temporary) / "index.json"
            temp_index.write_text(json.dumps(index), encoding="utf-8")
            with patch.object(case_library, "INDEX_PATH", temp_index):
                with self.assertRaisesRegex(ValueError, "hash mismatch"):
                    load_items()

    def test_near_copy_variant_is_flagged(self):
        item = copy.deepcopy(load_items()[0])
        text = item["text"]
        variant = {"item_id": "TEST-NEAR-COPY", "task":
                   {"statement": text, "questions": [], "givens": []}}
        self.assertTrue(any("EX-ALIGN-01" in issue and "TEST-NEAR-COPY" in issue
                            for issue in audit_leakage([variant])))

    def test_direct_numerical_answer_key_overlap_is_flagged(self):
        from tools import case_library
        altered = copy.deepcopy(load_items())
        altered[0]["text"] += "\nReported final value: 34.91 mm.\n"
        with patch.object(case_library, "load_items", return_value=altered):
            issues = audit_leakage([])
        self.assertTrue(any("SEED-1-1 numerical answer key" in issue for issue in issues))


if __name__ == "__main__":
    unittest.main()
