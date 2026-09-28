"""The rc1 environment is an enforceable release asset, not a version hint."""

from __future__ import annotations

from contextlib import redirect_stderr
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import check_release_environment as release_environment
from tools import check_verification_status as status_gate
from tools import qualify_release


class ReleaseEnvironmentTests(unittest.TestCase):
    def test_lock_emits_exact_direct_and_transitive_requirements(self) -> None:
        snapshot = release_environment.load_snapshot()
        lines = release_environment.exact_requirements(snapshot).splitlines()
        self.assertEqual(len(lines), 9)
        self.assertEqual({line.split("==")[0] for line in lines}, release_environment.EXPECTED_PACKAGES)
        self.assertTrue(all(line.count("==") == 1 for line in lines))

    def test_python_or_dependency_mismatch_blocks_qualification(self) -> None:
        snapshot = release_environment.load_snapshot()
        versions = snapshot["packages"]
        issues = release_environment.environment_issues(
            snapshot, python_version="3.11.15", implementation="CPython",
            version_lookup=lambda name: "0.0.0" if name == "jsonschema" else versions[name],
        )
        self.assertTrue(any("release Python mismatch" in issue for issue in issues))
        self.assertTrue(any("release dependency mismatch: jsonschema" in issue for issue in issues))
        with patch.object(qualify_release, "environment_issues", return_value=issues), redirect_stderr(io.StringIO()):
            self.assertEqual(qualify_release.main(["--check"]), 1)

    def test_missing_environment_asset_invalidates_released_case(self) -> None:
        source = status_gate.RELEASES / "0.1.0-rc1.json"
        manifest = json.loads(source.read_text(encoding="utf-8"))
        relative = release_environment.SNAPSHOT.relative_to(status_gate.ROOT).as_posix()
        manifest["files"].pop(relative)
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / source.name
            target.write_text(json.dumps(manifest), encoding="utf-8")
            with patch.object(status_gate, "RELEASES", Path(temporary)):
                issues = status_gate._manifest_issues("SEED-1-1", "0.1.0-rc1", ["reference.json"])
        self.assertTrue(any(f"release manifest does not pin {relative}" in issue for issue in issues))

    def test_missing_environment_file_blocks_qualification(self) -> None:
        with patch.object(qualify_release, "load_snapshot", side_effect=FileNotFoundError("rc1 environment missing")), redirect_stderr(io.StringIO()):
            self.assertEqual(qualify_release.main(["--check"]), 1)


if __name__ == "__main__":
    unittest.main()
