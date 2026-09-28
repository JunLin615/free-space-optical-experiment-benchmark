"""Build and verify the independent, evidence-pinned stable 0.2.0 release.

Historical release candidates are qualified by their own commands. This module
only reads their case revisions and never regenerates either historical manifest.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.check_release_environment import SNAPSHOT, environment_issues, load_snapshot
from tools.fixture_evidence import fixture_kind_issues
from tools.scoring_runtime import ROOT, _content_hash
from tools.validate_cases import semantic_issues
from tools.stable.scoring_runtime import (
    RUNTIME_VERSION, SCORERS, _evaluator_fingerprint, evaluate_case, load_scored_case,
)


RELEASE = "0.2.0"
INHERITED_RC1 = ("SEED-1-1", "SEED-1-5", "SEED-1-7", "SEED-2-2", "SEED-4-2")
INHERITED_VNEXT = ("SEED-2-1", "SEED-3-7", "SEED-5-5")
CORRECTED = "SEED-3-1"
CASE_IDS = INHERITED_RC1 + ("SEED-2-1", CORRECTED, "SEED-3-7", "SEED-5-5")
MANIFEST = ROOT / "benchmark" / "releases" / f"{RELEASE}.json"
QUALIFICATION = ROOT / "benchmark" / "qualification" / f"{RELEASE}.json"

# These files define the stable scoring path and its independent qualification.
# No historical candidate manifest is rewritten to include new files.
RELEASE_FILES = (
    ".github/workflows/ci.yml",
    ".github/workflows/evaluation.yml",
    ".github/workflows/campaign.yml",
    ".github/workflows/release-freeze.yml",
    "benchmark/releases/0.1.0-rc1.json",
    "benchmark/releases/0.2.0-rc1.json",
    "benchmark/releases/0.1.0-rc1-environment.json",
    "benchmark/locales/zh-CN.v1.yaml",
    "benchmark/generated/questions.md",
    "benchmark/generated/questions.html",
    "benchmark/generated/questions.zh-CN.md",
    "benchmark/generated/questions.zh-CN.html",
    "benchmark/hidden_eval/family_map.v1.json",
    "benchmark/results/campaigns/2026-09-28-multimodel-020rc1/campaign.json",
    "benchmark/schema/case_v0.1.schema.json",
    "benchmark/schema/pilot_answer_v0.1.schema.json",
    "benchmark/schema/result.schema.json",
    "tools/check_release_environment.py",
    "tools/check_frozen_history.py",
    "tools/check_localization.py",
    "tools/render_cases.py",
    "tools/render_zh_cn.py",
    "tools/analyze_campaign.py",
    "tools/hidden_eval.py",
    "tools/fixture_evidence.py",
    "tools/validate_cases.py",
    "tools/scoring_runtime.py",
    "tools/vnext/scoring_runtime.py",
    "tools/vnext/units.py",
    "tools/stable/scoring_runtime.py",
    "tools/scorers/numerical.py",
    "tools/scorers/closed_vnext.py",
    "tools/scorers/closed_stable.py",
    "tools/scorers/geometry.py",
    "tools/physics_checks.py",
    "tools/qualify_stable.py",
    "tools/score_stable.py",
    "tools/protocols.py",
    "tools/vnext/protocols.py",
    "tools/case_library.py",
    "tools/retrieval.py",
    "tests/test_stable_release.py",
    "tests/test_localization.py",
    "requirements.txt",
)


def _hash_file(relative: str) -> str:
    path = ROOT / relative
    if not path.is_file():
        raise ValueError(f"missing stable release evidence: {relative}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source(case_id: str) -> tuple[str, str, str]:
    if case_id == CORRECTED:
        return "0.2.0", f"benchmark/cases_stable/{case_id}.yaml", "benchmark/fixtures_stable"
    if case_id in INHERITED_VNEXT:
        return "0.2.0-rc1", f"benchmark/cases_vnext/{case_id}.yaml", "benchmark/fixtures_vnext"
    return "0.1.0-rc1", f"benchmark/cases/{case_id}.yaml", "benchmark/fixtures"


def _fixture_rows(case_id: str, folder: str) -> tuple[list[dict], set[str]]:
    fixture_paths = sorted((ROOT / folder / case_id).glob("*.json"))
    if not fixture_paths:
        raise ValueError(f"release fixtures missing: {case_id}")
    case = load_scored_case(case_id)
    rows = []
    files = set()
    for path in fixture_paths:
        relative = path.relative_to(ROOT).as_posix()
        files.add(relative)
        fixture = json.loads(path.read_text(encoding="utf-8"))
        if fixture.get("case_id") != case_id:
            raise ValueError(f"fixture case ID mismatch: {relative}")
        result = evaluate_case(case, fixture["answer"])
        issues = fixture_kind_issues(fixture, result, release_verified=True)
        expected = fixture.get("expected", {})
        actual = {item["check_id"]: item["status"] for item in result["validator_results"]}
        for criterion, claim in expected.items():
            if actual.get(criterion) != claim.get("status"):
                issues.append(f"{criterion}: expected {claim.get('status')}, got {actual.get(criterion)}")
        if result["scores"]["capped_total"] is None:
            issues.append("unresolved aggregate release fixture")
        if issues:
            raise ValueError(f"{relative}: {'; '.join(issues)}")
        rows.append({"name": path.name, "kind": fixture["kind"],
                     "failure_family": fixture.get("failure_family"),
                     "score": result["scores"]["capped_total"]})
    if case_id == CORRECTED:
        counts = Counter(row["kind"] for row in rows)
        for kind, minimum in (("positive", 2), ("alternative_valid", 2),
                              ("boundary", 2), ("negative", 4), ("adversarial", 2)):
            if counts[kind] < minimum:
                raise ValueError(f"{case_id}: insufficient {kind} challenges: {counts[kind]}")
        for kind, minimum in (("negative", 4), ("adversarial", 2)):
            families = {row["failure_family"] for row in rows if row["kind"] == kind}
            if None in families or len(families) < minimum:
                raise ValueError(f"{case_id}: insufficient named {kind} error families")
    return rows, files


def build() -> tuple[dict, dict]:
    snapshot = load_snapshot()
    environment = {"snapshot": SNAPSHOT.relative_to(ROOT).as_posix(),
                   "python_implementation": snapshot["python_implementation"],
                   "python_version": snapshot["python_version"]}
    files = set(RELEASE_FILES)
    for folder in ("benchmark/protocols", "benchmark/case_library", "benchmark/system_prompts"):
        files.update(path.relative_to(ROOT).as_posix()
                     for path in (ROOT / folder).rglob("*") if path.is_file())
    pinned = {}
    rows = []
    from tools.hidden_eval import validate_family_map
    families = validate_family_map()["cases"]
    for case_id in CASE_IDS:
        source_release, case_relative, fixture_folder = _source(case_id)
        case = load_scored_case(case_id)
        if case.get("validation_status") != "release_verified":
            raise ValueError(f"{case_id}: case is not release verified")
        if case.get("benchmark_release") != source_release:
            raise ValueError(f"{case_id}: source release lineage mismatch")
        if case_id == CORRECTED and case.get("split") != "public_eval":
            raise ValueError(f"{case_id}: corrected source must be public_eval")
        if case["validation"].get("semantic_criteria"):
            raise ValueError(f"{case_id}: mandatory semantic judging blocks stable release")
        issues = semantic_issues(case)
        if issues:
            raise ValueError(f"{case_id}: {'; '.join(issues)}")
        fixture_rows, fixture_files = _fixture_rows(case_id, fixture_folder)
        files.add(case_relative)
        files.update(fixture_files)
        evidence_files = case["validation"].get("evidence_files", [])
        if not any(item.startswith("tests/test_") for item in evidence_files):
            raise ValueError(f"{case_id}: independent executable evidence is absent")
        files.update(evidence_files)
        pinned[case_id] = {
            "status": "release_verified", "source_release": source_release,
            "case_path": case_relative, "case_revision": case["case_revision"],
            "case_content_sha256": _content_hash(case), "scorer": SCORERS[case_id],
            "evaluator_version": RUNTIME_VERSION,
            "evaluator_fingerprint": _evaluator_fingerprint(case),
        }
        rows.append({
            "case_id": case_id, "source_release": source_release,
            "concept_family": families[case_id]["concept_family"],
            "scorer": SCORERS[case_id], "fixture_count": len(fixture_rows),
            "fixture_kinds": dict(Counter(item["kind"] for item in fixture_rows)),
            "unresolved_release_fixtures": 0, "semantic_judge_dependency": False,
            "independent_evidence": evidence_files,
        })
    manifest = {
        "release": RELEASE,
        "purpose": "Immutable initial public benchmark release with autonomous typed scoring.",
        "cases": pinned, "judge": {"mode": "disabled"},
        "environment": environment,
        "files": {relative: _hash_file(relative) for relative in sorted(files)},
    }
    qualification = {
        "release": RELEASE, "release_verified_ids": list(pinned),
        "case_count": len(pinned),
        "concept_family_count": len({row["concept_family"] for row in rows}),
        "fixture_count": sum(row["fixture_count"] for row in rows),
        "unresolved_release_fixture_count": 0,
        "cases": rows,
    }
    return manifest, qualification


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--write", action="store_true", help="write stable release assets after all evidence is final")
    action.add_argument("--check", action="store_true", help="verify stable release assets and pinned environment")
    args = parser.parse_args(argv)
    try:
        if args.check:
            issues = environment_issues(load_snapshot())
            if issues:
                raise ValueError("release environment mismatch: " + "; ".join(issues))
        manifest, qualification = build()
        outputs = ((MANIFEST, json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"),
                   (QUALIFICATION, json.dumps(qualification, indent=2, ensure_ascii=False) + "\n"))
        if args.check:
            for path, content in outputs:
                if not path.is_file() or path.read_text(encoding="utf-8") != content:
                    raise ValueError(f"stale stable release asset: {path.relative_to(ROOT)}")
        elif args.write:
            for path, content in outputs:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8", newline="\n")
        print(f"Qualification: {qualification['case_count']} release-verified; "
              f"{qualification['concept_family_count']} families; {qualification['fixture_count']} fixtures")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Qualification failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
