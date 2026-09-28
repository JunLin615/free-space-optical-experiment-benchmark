"""Build/check the independent 0.2.0-rc1 evidence-pinned release lineage."""

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
from tools.vnext.scoring_runtime import SCORERS, RUNTIME_VERSION, _evaluator_fingerprint, evaluate_case, load_scored_case


RELEASE = "0.2.0-rc1"
INHERITED = ("SEED-1-1", "SEED-1-5", "SEED-1-7", "SEED-2-2", "SEED-4-2")
NEW = ("SEED-2-1", "SEED-3-1", "SEED-3-7", "SEED-5-5")
MANIFEST = ROOT / "benchmark" / "releases" / f"{RELEASE}.json"
QUALIFICATION = ROOT / "benchmark" / "qualification" / f"{RELEASE}.json"
REPORT = ROOT / "docs" / "qualification_report_vnext.md"
SCORING_FILES = (
    "tools/vnext/scoring_runtime.py", "tools/vnext/units.py", "tools/vnext/protocols.py",
    "tools/scoring_runtime.py", "tools/scorers/numerical.py", "tools/scorers/closed_vnext.py",
    "tools/scorers/geometry.py", "tools/physics_checks.py", "tools/validate_cases.py",
    "benchmark/schema/case_v0.1.schema.json", "benchmark/schema/pilot_answer_v0.1.schema.json",
    "benchmark/schema/result.schema.json", "tools/fixture_evidence.py",
    "tools/qualify_vnext.py", "tools/variants_vnext.py", "tools/hidden_eval.py",
    "tools/protocols.py", "tools/baseline/runner.py",
    ".github/workflows/ci.yml", ".github/workflows/evaluation.yml",
    "tests/test_variants_vnext.py", "tests/test_hidden_eval.py", "tests/test_vnext_compatibility.py",
    "benchmark/hidden_eval/attestations/first_private_dry_run.v1.json",
    "benchmark/hidden_eval/attestations/first_real_smoke.v1.json",
    "benchmark/hidden_eval/family_map.v1.json",
    "benchmark/hidden_eval/private_policy.v1.schema.json",
    "benchmark/hidden_eval/commitment.v1.schema.json",
    "benchmark/releases/0.1.0-rc1-environment.json",
)


def _hash_file(relative: str) -> str:
    path = ROOT / relative
    if not path.is_file():
        raise ValueError(f"missing release evidence: {relative}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture_rows(case_id: str, *, new: bool) -> tuple[list[dict], set[str]]:
    folder = ROOT / "benchmark" / ("fixtures_vnext" if new else "fixtures") / case_id
    paths = sorted(folder.glob("*.json"))
    if not paths:
        raise ValueError(f"release fixtures missing: {case_id}")
    case = load_scored_case(case_id)
    rows: list[dict] = []
    files: set[str] = set()
    for path in paths:
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
    if new:
        counts = Counter(row["kind"] for row in rows)
        for kind, minimum in (("positive", 2), ("alternative_valid", 2), ("boundary", 2),
                              ("negative", 4), ("adversarial", 2)):
            if counts[kind] < minimum:
                raise ValueError(f"{case_id}: insufficient {kind} challenges: {counts[kind]}")
        for kind, minimum in (("negative", 4), ("adversarial", 2)):
            families = {row["failure_family"] for row in rows if row["kind"] == kind}
            if None in families or len(families) < minimum:
                raise ValueError(f"{case_id}: insufficient named {kind} physics-error families")
    return rows, files


def build() -> tuple[dict, dict, str]:
    snapshot = load_snapshot()
    environment = {"snapshot": SNAPSHOT.relative_to(ROOT).as_posix(),
                   "python_implementation": snapshot["python_implementation"],
                   "python_version": snapshot["python_version"]}
    files = set(SCORING_FILES)
    pinned = {}
    rows = []
    for case_id in INHERITED + NEW:
        case = load_scored_case(case_id)
        is_new = case_id in NEW
        expected_release = RELEASE if is_new else "0.1.0-rc1"
        if case["validation_status"] != "release_verified" or case.get("benchmark_release") != expected_release:
            raise ValueError(f"{case_id}: release status/lineage mismatch")
        if is_new and case["split"] != "public_eval":
            raise ValueError(f"{case_id}: new release source must be public_eval")
        if case["validation"].get("semantic_criteria"):
            raise ValueError(f"{case_id}: mandatory semantic judge is uncalibrated")
        issues = semantic_issues(case)
        if issues:
            raise ValueError(f"{case_id}: {'; '.join(issues)}")
        fixture_rows, fixture_files = _fixture_rows(case_id, new=is_new)
        files.update(fixture_files)
        case_relative = f"benchmark/{'cases_vnext' if is_new else 'cases'}/{case_id}.yaml"
        files.add(case_relative)
        for evidence in case["validation"].get("evidence_files", []):
            files.add(evidence)
        if is_new and not any(item.startswith("tests/test_") for item in case["validation"].get("evidence_files", [])):
            raise ValueError(f"{case_id}: independent executable evidence is absent")
        pinned[case_id] = {"status": "release_verified", "source_release": expected_release,
                           "case_path": case_relative, "case_revision": case["case_revision"],
                           "case_content_sha256": _content_hash(case), "scorer": SCORERS[case_id],
                           "evaluator_version": RUNTIME_VERSION,
                           "evaluator_fingerprint": _evaluator_fingerprint(case)}
        rows.append({"case_id": case_id, "source_release": expected_release,
                     "concept_family": None, "scorer": SCORERS[case_id],
                     "fixture_count": len(fixture_rows),
                     "fixture_kinds": dict(Counter(item["kind"] for item in fixture_rows)),
                     "unresolved_release_fixtures": 0,
                     "semantic_judge_dependency": False,
                     "independent_evidence": case["validation"].get("evidence_files", [])})
    from tools.hidden_eval import validate_family_map
    mapping = validate_family_map()["cases"]
    for row in rows:
        row["concept_family"] = mapping[row["case_id"]]["concept_family"]
    manifest = {"release_candidate": RELEASE,
                "purpose": "Evidence-pinned technical release; rc1 artifacts remain independent and immutable.",
                "cases": pinned, "judge": {"mode": "disabled"}, "environment": environment,
                "files": {relative: _hash_file(relative) for relative in sorted(files)}}
    qualification = {"release_candidate": RELEASE, "release_verified_ids": list(pinned),
                     "case_count": len(pinned),
                     "concept_family_count": len({row["concept_family"] for row in rows}),
                     "fixture_count": sum(row["fixture_count"] for row in rows),
                     "unresolved_release_fixture_count": 0,
                     "cases": rows}
    lines = [f"# Qualification report: {RELEASE}", "",
             "Generated by `python tools/qualify_vnext.py --write`; checked by CI with `--check`.", "",
             f"**Release-verified:** {len(pinned)} cases across {qualification['concept_family_count']} concept families.", "",
             f"**Fixtures:** {qualification['fixture_count']}; unresolved release fixtures: 0. Semantic judge dependencies: 0.", "",
             "The original five rc1 cases are inherited without changing their bytes. Four versioned case revisions use the vNext evaluator; rc1 remains separately qualified.", "",
             "| Case | Concept family | Source release | Scorer | Fixtures |",
             "| --- | --- | --- | --- | ---: |"]
    lines += [f"| {row['case_id']} | {row['concept_family']} | {row['source_release']} | {row['scorer']} | {row['fixture_count']} |" for row in rows]
    lines += ["", "Qualification applies to the tested typed answer region. Unknown plausible architectures must abstain where a development oracle cannot prove their validity; they are not silently promoted into this release.", ""]
    return manifest, qualification, "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--write", action="store_true")
    action.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.check:
            issues = environment_issues(load_snapshot())
            if issues:
                raise ValueError("release environment mismatch: " + "; ".join(issues))
        manifest, qualification, report = build()
        outputs = ((MANIFEST, json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"),
                   (QUALIFICATION, json.dumps(qualification, indent=2, ensure_ascii=False) + "\n"),
                   (REPORT, report))
        if args.check:
            for path, content in outputs:
                if not path.is_file() or path.read_text(encoding="utf-8") != content:
                    raise ValueError(f"stale vNext release asset: {path.relative_to(ROOT)}")
        elif args.write:
            for path, content in outputs:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8", newline="\n")
        print(f"Qualification: {len(manifest['cases'])} release-verified; {qualification['concept_family_count']} families; {qualification['fixture_count']} fixtures")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Qualification failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
