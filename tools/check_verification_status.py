"""Enforce evidence gates for cases above the specified state."""

from __future__ import annotations

import json
import hashlib
import sys
from collections import defaultdict

if __package__ in (None, ""):
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.scoring_runtime import CASES, ROOT, SCORERS, evaluate_case, load_scored_case
from tools.validate_cases import load_case


FIXTURES = ROOT / "benchmark" / "fixtures"
RELEASES = ROOT / "benchmark" / "releases"


def _manifest_issues(case_id: str, release: str, fixture_names: list[str]) -> list[str]:
    path = RELEASES / f"{release}.json"
    if not path.is_file():
        return [f"{case_id}: missing pinned release manifest"]
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
        files = manifest["files"]
        pinned = manifest["cases"][case_id]
        if pinned["case_revision"] != load_scored_case(case_id)["case_revision"]:
            raise ValueError("case revision differs from release manifest")
        if not isinstance(files, dict) or not files:
            raise ValueError("manifest has no file hashes")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return [f"{case_id}: invalid release manifest: {exc}"]
    required = {
        f"benchmark/cases/{case_id}.yaml", "benchmark/schema/case_v0.1.schema.json",
        "benchmark/schema/pilot_answer_v0.1.schema.json", "benchmark/schema/result.schema.json",
        "benchmark/generated/questions.md", "benchmark/generated/questions.html",
        "tools/scoring_runtime.py", "tools/semantic_judge.py", "requirements.txt",
    }
    required.update(f"benchmark/fixtures/{case_id}/{name}" for name in fixture_names)
    module = SCORERS[case_id]
    required.add(f"tools/scorers/{module}.py")
    if module == "numerical":
        required.add("tools/physics_checks.py")
    if case_id == "SEED-1-1":
        required.add("tools/scorers/geometry.py")
    issues = []
    for relative in sorted(required):
        if relative not in files:
            issues.append(f"{case_id}: release manifest does not pin {relative}")
            continue
        source = (ROOT / relative).resolve()
        if not source.is_file() or not source.is_relative_to(ROOT.resolve()):
            issues.append(f"{case_id}: release file missing or outside repository: {relative}")
            continue
        actual = hashlib.sha256(source.read_bytes()).hexdigest()
        if actual != files[relative]:
            issues.append(f"{case_id}: release hash mismatch: {relative}")
    return issues


def check() -> list[str]:
    issues: list[str] = []
    fixtures: dict[str, list[tuple[str, dict]]] = defaultdict(list)
    for path in sorted(FIXTURES.rglob("*.json")):
        try:
            fixture = json.loads(path.read_text(encoding="utf-8"))
            fixtures[fixture["case_id"]].append((path.name, fixture))
        except (OSError, ValueError, KeyError) as exc:
            issues.append(f"{path}: invalid fixture: {exc}")
    for case_path in sorted(CASES.glob("*.yaml")):
        candidate = load_case(case_path)
        case_id = candidate["case_id"]
        case = load_scored_case(case_id) if case_id in SCORERS else candidate
        status = case["validation_status"]
        if status not in {"executable", "challenged", "release_verified"}:
            continue
        if case_id not in SCORERS:
            issues.append(f"{case_id}: {status} has no registered autonomous scorer")
            continue
        case_fixtures = fixtures[case_id]
        kinds = {fixture.get("kind") for _, fixture in case_fixtures}
        evidence = case["validation"]
        if not evidence.get("implemented_checks"):
            issues.append(f"{case_id}: {status} lacks implemented checks")
        if not {"positive", "negative"} <= kinds:
            issues.append(f"{case_id}: {status} lacks positive or negative fixture")
        if status in {"challenged", "release_verified"}:
            if not {"boundary", "alternative_valid", "adversarial"} <= kinds:
                issues.append(f"{case_id}: {status} lacks boundary, alternative-valid, or adversarial fixture")
            for field in ("independent_derivation", "adversarial_evidence"):
                if not evidence.get(field):
                    issues.append(f"{case_id}: {status} lacks {field}")
        for name, fixture in case_fixtures:
            if fixture.get("kind") in {"positive", "alternative_valid"}:
                result = evaluate_case(case, fixture["answer"])
                if result["scores"]["capped_total"] != 1:
                    issues.append(f"{case_id}/{name}: valid fixture does not score 1")
        if status == "release_verified":
            release = case.get("benchmark_release")
            if release:
                issues.extend(_manifest_issues(case_id, release, [name for name, _ in case_fixtures]))
            else:
                issues.append(f"{case_id}: missing benchmark_release")
            if not evidence.get("positive_fixtures") or not evidence.get("negative_fixtures"):
                issues.append(f"{case_id}: missing fixture inventory in case validation")
            if case["split"] == "public_dev":
                issues.append(f"{case_id}: public development split is not a scored release split")
            for name, fixture in case_fixtures:
                result = evaluate_case(case, fixture["answer"])
                if result["scores"]["capped_total"] is None:
                    issues.append(f"{case_id}/{name}: unresolved fixture blocks release")
    return issues


def main() -> int:
    issues = check()
    for issue in issues:
        print(issue, file=sys.stderr)
    print(f"Verification status gate: {len(issues)} issue(s)")
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
