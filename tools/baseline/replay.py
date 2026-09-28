"""Derive a portable, new-run manifest from immutable historical evidence."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from tools.baseline.runner import MANIFEST_SCHEMA, _validate, validate_manifest


SUFFIX = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,31}$")


def build_replay_manifest(source_path: Path, suffix: str) -> dict[str, Any]:
    """Preserve scientific/model fields while replacing host-bound run location.

    Schema validation does not interpret the source host's path with the local
    host's pathlib flavor. The derived manifest is validated on this host.
    """
    source = json.loads(source_path.read_text(encoding="utf-8"))
    _validate(source, MANIFEST_SCHEMA)
    if source["output_directory"].replace("\\", "/").rstrip("/").rsplit("/", 1)[-1] != source["run_id"]:
        raise ValueError("source output_directory does not end in its run_id")
    if not SUFFIX.fullmatch(suffix):
        raise ValueError("replay suffix must be a short alphanumeric slug")
    run_id = source["run_id"] + "-" + suffix
    if len(run_id) > 80:
        raise ValueError("replay run_id exceeds the manifest limit")
    canonical = json.dumps(source, sort_keys=True, ensure_ascii=False,
                           separators=(",", ":")).encode("utf-8")
    replay = copy.deepcopy(source)
    replay["run_id"] = run_id
    replay["output_directory"] = run_id
    replay["replay_of"] = {"run_id": source["run_id"],
                           "manifest_canonical_sha256": hashlib.sha256(canonical).hexdigest()}
    validate_manifest(replay)
    return replay


def write_replay_manifest(source_path: Path, output_root: Path, suffix: str) -> Path:
    """Create or reuse an identical portable input manifest outside the source run."""
    root = Path(output_root)
    if not root.is_absolute():
        raise ValueError("output_root must be absolute on the current host")
    replay = build_replay_manifest(source_path, suffix)
    target = root / "input_manifests" / (replay["run_id"] + ".json")
    content = (json.dumps(replay, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if target.read_bytes() != content:
            raise ValueError(f"existing replay manifest differs: {target}")
    else:
        with target.open("xb") as stream:
            stream.write(content)
    return target
