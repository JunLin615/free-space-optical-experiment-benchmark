"""Emit exact rc1 requirements or verify the active validation environment."""

from __future__ import annotations

import argparse
from importlib import metadata
import json
from pathlib import Path
import platform
import re
import sys
from typing import Callable


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "benchmark" / "releases" / "0.1.0-rc1-environment.json"
EXPECTED_PACKAGES = {
    "PyYAML", "attrs", "jsonschema", "jsonschema-specifications",
    "referencing", "rfc3339-validator", "rpds-py", "six", "typing-extensions",
}
VERSION = re.compile(r"^[0-9][A-Za-z0-9.!+_-]*$")


def load_snapshot(path: Path = SNAPSHOT) -> dict:
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    if snapshot.get("release_candidate") != "0.1.0-rc1":
        raise ValueError("environment snapshot release candidate differs from rc1")
    if snapshot.get("python_implementation") != "CPython" or not isinstance(snapshot.get("python_version"), str) or not VERSION.fullmatch(snapshot["python_version"]):
        raise ValueError("environment snapshot needs an exact CPython version")
    packages = snapshot.get("packages")
    if not isinstance(packages, dict) or set(packages) != EXPECTED_PACKAGES:
        raise ValueError("environment snapshot package set is incomplete or unexpected")
    if any(not isinstance(version, str) or not VERSION.fullmatch(version) for version in packages.values()):
        raise ValueError("environment snapshot contains a non-exact package version")
    return snapshot


def exact_requirements(snapshot: dict) -> str:
    """Return pip input from the one machine-readable lock source."""
    return "".join(f"{name}=={version}\n" for name, version in sorted(snapshot["packages"].items(), key=lambda item: item[0].lower()))


def environment_issues(
    snapshot: dict,
    *,
    python_version: str | None = None,
    implementation: str | None = None,
    version_lookup: Callable[[str], str] | None = None,
) -> list[str]:
    """Compare the active interpreter and every direct/transitive lock entry."""
    python_version = python_version or platform.python_version()
    implementation = implementation or platform.python_implementation()
    version_lookup = version_lookup or metadata.version
    issues = []
    if implementation != snapshot["python_implementation"] or python_version != snapshot["python_version"]:
        issues.append(f"release Python mismatch: expected {snapshot['python_implementation']} {snapshot['python_version']}, got {implementation} {python_version}")
    for name, expected in sorted(snapshot["packages"].items()):
        try:
            actual = version_lookup(name)
        except metadata.PackageNotFoundError:
            issues.append(f"release dependency missing: {name}=={expected}")
            continue
        if actual != expected:
            issues.append(f"release dependency mismatch: {name} expected {expected}, got {actual}")
    return issues


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--requirements", action="store_true", help="emit exact pip requirements from the rc1 snapshot")
    mode.add_argument("--check", action="store_true", help="verify active Python and installed package versions")
    args = parser.parse_args(argv)
    try:
        snapshot = load_snapshot()
        if args.requirements:
            print(exact_requirements(snapshot), end="")
            return 0
        issues = environment_issues(snapshot)
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"Release environment invalid: {exc}", file=sys.stderr)
        return 1
    for issue in issues:
        print(issue, file=sys.stderr)
    print(f"Release environment: {len(issues)} issue(s)")
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
