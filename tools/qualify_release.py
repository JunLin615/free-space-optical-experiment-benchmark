"""Build and verify the first evidence-pinned benchmark release candidate.

Run ``python tools/qualify_release.py`` to inspect qualification, ``--write``
after case evidence is final, or ``--check`` in CI. No model API is used.
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

from tools.check_verification_status import (
    _manifest_issues, _repo_file, check as status_check, required_release_files,
)
from tools.fixture_evidence import fixture_kind_issues
from tools.scoring_runtime import (
    CASES, ROOT, RUNTIME_VERSION, SCORERS, _content_hash,
    _evaluator_fingerprint, evaluate_case,
)
from tools.validate_cases import load_case
from tools.check_release_environment import (
    SNAPSHOT as RELEASE_ENVIRONMENT, environment_issues, load_snapshot,
)


RELEASE = "0.1.0-rc1"
MANIFEST = ROOT / "benchmark" / "releases" / f"{RELEASE}.json"
QUALIFICATION = ROOT / "benchmark" / "qualification" / "qualification.json"
REPORT = ROOT / "docs" / "qualification_report.md"
FIXTURES = ROOT / "benchmark" / "fixtures"
DETERMINISTIC_READY = {
    "SEED-1-1", "SEED-1-5", "SEED-1-7", "SEED-2-1", "SEED-2-2",
    "SEED-2-4", "SEED-3-1", "SEED-3-7", "SEED-4-2", "SEED-5-5",
}
SELECTED_OTHER = {
    "SEED-1-3", "SEED-1-6", "SEED-2-8", "SEED-4-1", "SEED-4-8",
    "SEED-5-3", "SEED-7-2", "SEED-7-8",
}
SELECTED = DETERMINISTIC_READY | SELECTED_OTHER
MIXED_QUANTITATIVE_REVIEW = {"SEED-2-7", "SEED-6-2", "SEED-6-6"}

# These reviewed limits add scientific specificity to machine-observed failures.
# Update them after scorer/challenge review; a status label alone is not a reason.
SCIENTIFIC_BLOCKERS: dict[str, list[str]] = {
    "SEED-1-3": ["typed dogleg claims do not independently ray-trace an arbitrary mirror pose"],
    "SEED-1-6": ["coating-specific angle and polarization responses lack a supplied transfer function"],
    "SEED-2-1": ["the public order-of-magnitude request has no sharp scientific acceptance interval"],
    "SEED-2-4": ["a physically plausible application tradeoff outside the typed cost set still abstains"],
    "SEED-2-8": ["the scorer still covers only bounded typed directionality and divergence vocabularies"],
    "SEED-3-1": ["an equivalent real-image description outside the typed terms still abstains"],
    "SEED-3-7": ["an equivalent depth-of-focus trend outside the typed terms still abstains"],
    "SEED-4-1": ["equivalent Jones or Stokes answer representations are not yet parsed"],
    "SEED-4-8": ["a declared analyzer transfer is checked, but arbitrary prose layouts and multipass designs are not physically verified"],
    "SEED-5-3": ["the typed common-mode input and reference relations do not cover every valid architecture"],
    "SEED-5-5": ["an equivalent heterodyne-mechanism description outside the typed terms still abstains"],
    "SEED-7-2": ["free-form diagnostic methods and explanations are not interpreted beyond typed cause-test links"],
    "SEED-7-8": ["free-form equivalent Gaussian invariant expressions are not yet parsed"],
}


def _hash_portable_asset(relative: str) -> str:
    data = _repo_file(relative).read_bytes()
    if b"\r\n" in data:
        raise ValueError(f"pinned text asset has CRLF bytes: {relative}; normalize to LF before writing manifest")
    return hashlib.sha256(data).hexdigest()


def _fixture_evidence(case: dict) -> tuple[dict, list[str], int]:
    case_id = case["case_id"]
    paths = sorted((FIXTURES / case_id).glob("*.json"))
    counts: Counter[str] = Counter()
    families: dict[str, set[str]] = {"negative": set(), "adversarial": set()}
    issues: list[str] = []
    unresolved = 0
    for path in paths:
        try:
            item = json.loads(path.read_text(encoding="utf-8"))
            if item["case_id"] != case_id:
                raise ValueError("fixture case_id does not match directory")
            kind = item["kind"]
            counts[kind] += 1
            if kind in families and isinstance(item.get("failure_family"), str):
                families[kind].add(item["failure_family"])
            if case_id in SCORERS:
                result = evaluate_case(case, item["answer"])
                issues.extend(f"{path.name}: {problem}" for problem in
                              fixture_kind_issues(item, result, release_verified=case["validation_status"] == "release_verified"))
                unresolved += result["scores"]["capped_total"] is None
        except (OSError, ValueError, KeyError, TypeError, RuntimeError) as exc:
            issues.append(f"{path.name}: invalid fixture: {exc}")
    return {
        "total": len(paths),
        "by_kind": {kind: counts[kind] for kind in
                    ("positive", "alternative_valid", "boundary", "negative", "adversarial")},
        "negative_failure_families": sorted(families["negative"]),
        "adversarial_failure_families": sorted(families["adversarial"]),
    }, issues, unresolved


def _row(case: dict) -> dict:
    case_id = case["case_id"]
    selected = case_id in SELECTED
    status = case["validation_status"]
    scorer = SCORERS.get(case_id)
    fixture, fixture_issues, unresolved = _fixture_evidence(case)
    evidence_paths = case["validation"].get("evidence_files", [])
    missing_evidence = [path for path in evidence_paths if not (ROOT / path).is_file()]
    test_evidence = [path for path in evidence_paths if path.startswith("tests/") and path.endswith(".py")]
    semantic = case["validation"].get("semantic_criteria", [])
    criteria = case["scoring"]["criteria"]
    numerical_ids = {check["id"] for check in case["gold"].get("numerical_checks", [])}
    numerical_scored = sum(item["check"] in numerical_ids for item in criteria)
    failures: list[str] = []
    if selected:
        if scorer is None:
            failures.append("no registered autonomous scorer")
        if status not in {"challenged", "release_verified"}:
            failures.append(f"validation status {status} has not passed challenged evidence gate")
        if not case["validation"].get("independent_derivation") or not test_evidence or missing_evidence:
            failures.append("independent executable derivation evidence is absent or missing")
        if fixture_issues:
            failures.extend(fixture_issues)
        if unresolved:
            failures.append(f"{unresolved} fixture(s) produce unresolved aggregate scores")
        if semantic:
            failures.append("scored semantic criteria require verified live judge calibration")
        if status == "release_verified" and case.get("benchmark_release") != RELEASE:
            failures.append(f"benchmark_release must pin {RELEASE}")
        if status == "release_verified" and case["split"] == "public_dev":
            failures.append("public_dev split is not a scored release split")
        if case_id in DETERMINISTIC_READY:
            counts = fixture["by_kind"]
            for kind, minimum in (("positive", 2), ("alternative_valid", 2), ("boundary", 2)):
                if counts[kind] < minimum:
                    failures.append(f"only {counts[kind]} {kind} fixture(s); need {minimum} diverse forms")
            for kind, minimum in (("negative", 4), ("adversarial", 2)):
                actual = len(fixture[f"{kind}_failure_families"])
                if actual < minimum:
                    failures.append(f"only {actual} documented {kind} failure families; need {minimum}")
        failures.extend(SCIENTIFIC_BLOCKERS.get(case_id, []))
        if status != "release_verified":
            failures.append(f"case remains {status}; release evidence has not been approved for promotion")
    decision = ("not_selected_this_round" if not selected else
                "release_verified" if status == "release_verified" and not failures else
                "selected_failed_qualification")
    return {
        "case_id": case_id,
        "selected_this_round": selected,
        "selection_outcome": decision,
        "reviewed_mixed_quantitative_subproblem": case_id in MIXED_QUANTITATIVE_REVIEW,
        "validation_status": status,
        "scorer_family": scorer,
        "deterministic_coverage": {"numerical_scored_criteria": numerical_scored,
                                   "total_scored_criteria": len(criteria)},
        "fixture_challenge_coverage": fixture,
        "independent_derivation_evidence": {"files": evidence_paths, "missing_files": missing_evidence,
                                            "executable_test_files": test_evidence},
        "unresolved_fixture_count": unresolved,
        "semantic_judge_dependency": semantic,
        "release_gate_failures": failures,
        "promotion_decision": decision,
    }


def build() -> tuple[dict, dict, str]:
    release_environment = load_snapshot()
    cases = [load_case(path) for path in sorted(CASES.glob("*.yaml"))]
    by_id = {case["case_id"]: case for case in cases}
    if len(cases) != 64 or len(by_id) != 64 or not SELECTED <= set(by_id):
        raise ValueError("qualification requires the complete 64-case corpus and known selected IDs")
    missing_deterministic = DETERMINISTIC_READY - set(SCORERS)
    if missing_deterministic:
        raise ValueError(f"deterministic-ready cases lack autonomous scorers: {sorted(missing_deterministic)}")
    rows = [_row(case) for case in sorted(cases, key=lambda item: tuple(map(int, item["legacy_id"].split("."))))]
    released = [row for row in rows if row["promotion_decision"] == "release_verified"]
    invalid_promotions = [row["case_id"] for row in rows
                          if row["validation_status"] == "release_verified" and row not in released]
    if invalid_promotions:
        raise ValueError(f"release_verified label lacks qualification: {invalid_promotions}")
    files: set[str] = set()
    pinned_cases: dict[str, dict] = {}
    for row in released:
        case_id = row["case_id"]
        case = by_id[case_id]
        names = [path.name for path in sorted((FIXTURES / case_id).glob("*.json"))]
        files.update(required_release_files(case, names))
        pinned_cases[case_id] = {
            "status": "release_verified",
            "case_revision": case["case_revision"],
            "case_content_sha256": _content_hash(case),
            "scorer": SCORERS[case_id],
            "evaluator_version": RUNTIME_VERSION,
            "evaluator_fingerprint": _evaluator_fingerprint(case),
        }
    manifest = {
        "release_candidate": RELEASE,
        "purpose": "Technical release candidate; no GitHub release or model baseline is implied.",
        "cases": pinned_cases,
        "exclusions": {row["case_id"]: row["release_gate_failures"] for row in rows
                       if row["selected_this_round"] and row["promotion_decision"] != "release_verified"},
        "judge": {"mode": "disabled"},
        "environment": {
            "snapshot": RELEASE_ENVIRONMENT.relative_to(ROOT).as_posix(),
            "python_implementation": release_environment["python_implementation"],
            "python_version": release_environment["python_version"],
        },
        "files": {relative: _hash_portable_asset(relative)
                  for relative in sorted(files)},
    }
    qualification = {
        "release_candidate": RELEASE,
        "case_count": len(rows),
        "release_environment": manifest["environment"],
        "selected_count": sum(row["selected_this_round"] for row in rows),
        "release_verified_ids": [row["case_id"] for row in released],
        "method": "Static case evidence, autonomous fixture outcomes, documented failure families, executable derivation files, and pinned release asset hashes. No human grading or live model judgment is inferred.",
        "cases": rows,
    }
    lines = [
        f"# Release qualification for {RELEASE}", "",
        "Generated by `python tools/qualify_release.py --write`; CI checks it with `--check`. This is a technical release candidate, not a public GitHub release.", "",
        f"**Included:** {', '.join(qualification['release_verified_ids']) or 'None'}.", "",
        f"**Pinned runtime:** {release_environment['python_implementation']} {release_environment['python_version']} and {len(release_environment['packages'])} exact direct/transitive packages in `{manifest['environment']['snapshot']}`.", "",
        f"**Selected:** {qualification['selected_count']} cases. **Not selected:** {64 - qualification['selected_count']} cases.", "",
        "| Case | Status | Scorer | Fixtures | Unresolved | Decision | Exact blockers |",
        "| --- | --- | --- | ---: | ---: | --- | --- |",
    ]
    for row in rows:
        if not row["selected_this_round"]:
            continue
        blockers = "; ".join(row["release_gate_failures"]) or "None"
        lines.append(f"| {row['case_id']} | {row['validation_status']} | {row['scorer_family'] or 'none'} | "
                     f"{row['fixture_challenge_coverage']['total']} | {row['unresolved_fixture_count']} | "
                     f"{row['promotion_decision']} | {blockers} |")
    lines += [
        "", "## Scope and remaining risk", "",
        "The JSON inventory records every seed case. Cases marked `not_selected_this_round` were outside this qualification batch; they are not failed release candidates. SEED-2-7, SEED-6-2, and SEED-6-6 were reviewed for numeric subproblems but retain broader qualitative task requirements. No partial numeric check promotes a whole mixed case.", "",
        "Failure-family counts use explicit `failure_family` fixture metadata. Fixture passes and source hashes are reproducible evidence for the declared answer region; they do not establish empirical model difficulty or validate an untested novel architecture. Semantic-judge cases need live calibration before release.", "",
    ]
    return manifest, qualification, "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--write", action="store_true", help="write manifest and reports after evidence is final")
    action.add_argument("--check", action="store_true", help="verify manifest/report bytes and release gates")
    args = parser.parse_args(argv)
    try:
        if args.check:
            environment_failures = environment_issues(load_snapshot())
            if environment_failures:
                raise ValueError("release environment mismatch: " + "; ".join(environment_failures))
        manifest, qualification, report = build()
        outputs = {
            MANIFEST: json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
            QUALIFICATION: json.dumps(qualification, indent=2, ensure_ascii=False) + "\n",
            REPORT: report,
        }
        if args.write:
            for path, content in outputs.items():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8", newline="\n")
        if args.check:
            stale = [str(path.relative_to(ROOT)) for path, content in outputs.items()
                     if not path.is_file() or path.read_text(encoding="utf-8") != content]
            if stale:
                raise ValueError("stale qualification or release outputs: " + ", ".join(stale))
            issues = status_check()
            for case_id in qualification["release_verified_ids"]:
                names = [path.name for path in sorted((FIXTURES / case_id).glob("*.json"))]
                issues.extend(_manifest_issues(case_id, RELEASE, names))
            if issues:
                raise ValueError("release verification issues: " + "; ".join(sorted(set(issues))))
            if not qualification["release_verified_ids"]:
                raise ValueError("release candidate contains no qualified case")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Qualification failed: {exc}", file=sys.stderr)
        return 1
    print(f"Qualification: {len(qualification['release_verified_ids'])} release-verified; "
          f"{qualification['selected_count']} selected; {64 - qualification['selected_count']} not selected")
    if not (args.write or args.check):
        for row in qualification["cases"]:
            if row["selected_this_round"] and row["release_gate_failures"]:
                print(f"{row['case_id']}: " + "; ".join(row["release_gate_failures"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
