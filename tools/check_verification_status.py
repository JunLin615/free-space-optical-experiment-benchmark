"""Enforce evidence gates for cases above the specified state."""

from __future__ import annotations

import json
import hashlib
import sys
from collections import defaultdict
from pathlib import Path, PurePosixPath

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.scoring_runtime import CASES, ROOT, SCORERS, evaluate_case, load_scored_case
from tools.validate_cases import load_case
from tools.fixture_evidence import fixture_kind_issues
from tools.calibrate_judge import SET as CALIBRATION_SET, measure
from tools.semantic_judge import CONFIG_PATH as JUDGE_CONFIG, load_config


FIXTURES = ROOT / "benchmark" / "fixtures"
RELEASES = ROOT / "benchmark" / "releases"


def _repo_file(relative: str) -> Path:
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise ValueError("evidence path must be a repository-relative POSIX path")
    parsed = PurePosixPath(relative)
    if parsed.is_absolute() or ".." in parsed.parts:
        raise ValueError("evidence path escapes repository")
    source = (ROOT / relative).resolve()
    if not source.is_relative_to(ROOT.resolve()) or not source.is_file():
        raise ValueError(f"evidence file missing or outside repository: {relative}")
    return source


def _judge_evidence_issues(case: dict, manifest: dict) -> tuple[set[str], list[str]]:
    """Return judge files that must be hashed and any missing live evidence."""
    case_id = case["case_id"]
    criteria = case["validation"].get("semantic_criteria", [])
    required = bool(criteria or case["answer_contract"].get("permit_additional_explanation")
                    or case["gold"].get("judge_rubrics"))
    judge = manifest.get("judge")
    if not isinstance(judge, dict) or judge.get("mode") not in {"required", "disabled"}:
        return set(), [f"{case_id}: release manifest must declare judge mode"]
    if not required:
        if judge["mode"] != "disabled":
            return set(), [f"{case_id}: judge mode is required without case semantic criteria"]
        return set(), []
    if judge["mode"] != "required":
        return set(), [f"{case_id}: semantic scoring path requires judge mode"]
    if case["answer_contract"].get("permit_additional_explanation") and "explanation_consistency" not in criteria:
        return set(), [f"{case_id}: explanation_consistency must be inventoried as a semantic criterion"]
    declared = judge.get("criteria")
    if not criteria or not isinstance(declared, list) or not all(isinstance(x, str) for x in declared) or set(declared) != set(criteria):
        return set(), [f"{case_id}: manifest judge criteria differ from case evidence inventory"]
    config_path = JUDGE_CONFIG.relative_to(ROOT).as_posix()
    set_path = CALIBRATION_SET.relative_to(ROOT).as_posix()
    if judge.get("config") != config_path or judge.get("calibration_set") != set_path:
        return set(), [f"{case_id}: manifest judge config or calibration set differs from evaluator path"]
    required_files = {config_path, set_path}
    live_path = judge.get("live_calibration_results")
    try:
        source = _repo_file(live_path)
        required_files.add(live_path)
        live = json.loads(source.read_text(encoding="utf-8"))
        config = load_config()
        if live.get("evidence_type") != "live_calibration":
            raise ValueError("live calibration evidence type is missing")
        if live.get("judge_version") != config["judge_version"] or live.get("prompt_version") != config["prompt_version"]:
            raise ValueError("live calibration judge/prompt version differs from evaluator")
        if not isinstance(live.get("model_id"), str) or not live["model_id"]:
            raise ValueError("live calibration model identity is missing")
        responses = live["responses"]
        run_ids = live["run_ids"]
        if not isinstance(run_ids, dict) or set(run_ids) != set(responses):
            raise ValueError("live run IDs do not cover calibration responses")
        all_ids = []
        for item_id, verdicts in responses.items():
            ids = run_ids[item_id]
            if not isinstance(ids, list) or len(ids) != len(verdicts) or not all(isinstance(x, str) and x for x in ids):
                raise ValueError(f"live run IDs mismatch for {item_id}")
            all_ids.extend(ids)
        if len(all_ids) != len(set(all_ids)):
            raise ValueError("live run IDs are not unique")
        metrics = measure(responses)
        for criterion in criteria:
            if criterion not in metrics or not metrics[criterion]["release_ready"]:
                raise ValueError(f"live judge calibration threshold not met for {criterion}")
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        return required_files, [f"{case_id}: invalid live calibration evidence: {exc}"]
    return required_files, []


def _manifest_issues(case_id: str, release: str, fixture_names: list[str]) -> list[str]:
    path = RELEASES / f"{release}.json"
    if not path.is_file():
        return [f"{case_id}: missing pinned release manifest"]
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
        files = manifest["files"]
        pinned = manifest["cases"][case_id]
        case = load_scored_case(case_id)
        if pinned["case_revision"] != case["case_revision"]:
            raise ValueError("case revision differs from release manifest")
        if not isinstance(files, dict) or not files:
            raise ValueError("manifest has no file hashes")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return [f"{case_id}: invalid release manifest: {exc}"]
    required = {
        f"benchmark/cases/{case_id}.yaml", "benchmark/schema/case_v0.1.schema.json",
        "benchmark/schema/pilot_answer_v0.1.schema.json", "benchmark/schema/result.schema.json",
        "benchmark/generated/questions.md", "benchmark/generated/questions.html",
        "tools/scoring_runtime.py", "tools/semantic_judge.py", "tools/validate_cases.py",
        "tools/render_cases.py", "tools/run_case_fixtures.py", "tools/fixture_evidence.py",
        "tools/check_verification_status.py", "requirements.txt",
    }
    required.update(f"benchmark/fixtures/{case_id}/{name}" for name in fixture_names)
    required.update(case["validation"].get("evidence_files", []))
    module = SCORERS[case_id]
    required.add(f"tools/scorers/{module}.py")
    if module == "numerical":
        required.add("tools/physics_checks.py")
    if case_id == "SEED-1-1":
        required.add("tools/scorers/geometry.py")
    judge_files, issues = _judge_evidence_issues(case, manifest)
    required.update(judge_files)
    if judge_files:
        required.add("tools/calibrate_judge.py")
    for relative in sorted(required):
        if relative not in files:
            issues.append(f"{case_id}: release manifest does not pin {relative}")
            continue
        try:
            source = _repo_file(relative)
        except ValueError as exc:
            issues.append(f"{case_id}: {exc}")
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
            evidence_files = evidence.get("evidence_files", [])
            if not evidence_files or not any(
                path.startswith("tests/") and PurePosixPath(path).name.startswith("test_") and path.endswith(".py")
                for path in evidence_files
            ):
                issues.append(f"{case_id}: {status} lacks executable derivation evidence inventory")
            for relative in evidence_files:
                try:
                    _repo_file(relative)
                except ValueError as exc:
                    issues.append(f"{case_id}: {exc}")
        for name, fixture in case_fixtures:
            result = evaluate_case(case, fixture["answer"])
            issues.extend(
                f"{case_id}/{name}: {issue}"
                for issue in fixture_kind_issues(fixture, result, release_verified=status == "release_verified")
            )
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
