"""Verify that the preserved seed has exactly one traced English case per ID."""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path
import yaml

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.validate_cases import ROOT, load_case


SEED = ROOT / "自由空间光学实验推理试题集_初版.html"
CASES = ROOT / "benchmark" / "cases"
SOURCE_SHA256 = "077DB14D2A5C67A3123C82AF1D571F8FFA73D3C79501C7C9D8C99E021C2318A8"
EXPECTED = {f"{section}.{number}" for section in range(1, 9) for number in range(1, 9)}
SEED_ID = re.compile(r"<span class='qid'>([1-8]\.[1-8])</span>")
QUESTION_ID = re.compile(r"q[1-9][0-9]*\Z")


def record_issues(case: dict, path: Path) -> list[str]:
    """Check lineage fields that the generic authoring schema cannot know."""
    issues = []
    legacy = case.get("legacy_id")
    expected_id = f"SEED-{str(legacy).replace('.', '-')}"
    if legacy not in EXPECTED or case.get("case_id") != expected_id or path.stem != expected_id:
        issues.append(f"{path}: case ID, filename, or legacy ID does not match the 64-case seed")
    provenance = case.get("provenance", {})
    if provenance.get("origin") != "user_supplied_chinese_html_seed":
        issues.append(f"{path}: missing seed origin")
    if provenance.get("source_hash", "").upper() != SOURCE_SHA256:
        issues.append(f"{path}: missing or incorrect original seed SHA-256")
    if not isinstance(provenance.get("seed_relationship"), str) or str(legacy) not in provenance["seed_relationship"]:
        issues.append(f"{path}: missing legacy-specific seed relationship")
    if not isinstance(provenance.get("derivation"), str) or len(provenance["derivation"].strip()) < 20:
        issues.append(f"{path}: missing translation or clarification notes")
    if case.get("case_revision") != "0.1.0":
        notes = (str(provenance.get("derivation", "")) + " " + str(case.get("validation", {}).get("notes", ""))).lower()
        if "revision" not in notes:
            issues.append(f"{path}: revised case lacks a revision note")
    return issues


def check(seed_path: Path = SEED, case_dir: Path = CASES) -> list[str]:
    issues: list[str] = []
    seed_task_counts: dict[str, int] = {}
    try:
        source = seed_path.read_bytes()
        actual = hashlib.sha256(source).hexdigest().upper()
        if actual != SOURCE_SHA256:
            issues.append(f"original seed SHA-256 changed: {actual}")
        source_ids = SEED_ID.findall(source.decode("utf-8"))
        if len(source_ids) != 64 or set(source_ids) != EXPECTED:
            issues.append("original seed does not contain exactly the expected 64 legacy IDs")
        for article in re.findall(r"<article>(.*?)</article>", source.decode("utf-8"), re.DOTALL):
            identity = SEED_ID.search(article)
            tasks = re.search(r"<ol>(.*?)</ol>", article, re.DOTALL)
            if identity and tasks:
                seed_task_counts[identity.group(1)] = len(re.findall(r"<li>", tasks.group(1)))
        if len(seed_task_counts) != 64 or sum(seed_task_counts.values()) != 199:
            issues.append("original seed task inventory differs from the audited 199 tasks in 64 cases")
    except (OSError, UnicodeError) as exc:
        issues.append(f"cannot read original seed: {exc}")
    seen_ids: list[str] = []
    for path in sorted(case_dir.glob("*.yaml")):
        try:
            case = load_case(path)
        except (OSError, ValueError, yaml.YAMLError) as exc:
            issues.append(f"{path}: cannot read case: {exc}")
            continue
        if case.get("case_id", "").startswith("SEED-"):
            seen_ids.append(case.get("legacy_id"))
            issues.extend(record_issues(case, path))
            legacy = case.get("legacy_id")
            if legacy in seed_task_counts and len(case.get("task", {}).get("questions", [])) != seed_task_counts[legacy]:
                issues.append(f"{path}: question count differs from original seed case {legacy}")
    if len(seen_ids) != 64 or set(seen_ids) != EXPECTED or len(set(seen_ids)) != len(seen_ids):
        missing = sorted(EXPECTED - set(seen_ids), key=lambda x: tuple(map(int, x.split("."))))
        issues.append(f"expected exactly 64 unique seed-derived cases; found {len(seen_ids)}, missing {missing}")
    return issues


def main() -> int:
    issues = check()
    for issue in issues:
        print(issue, file=sys.stderr)
    print(f"Corpus completeness: {64 if not issues else 'invalid'} seed cases, {len(issues)} issue(s)")
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
