"""Run or validate one frozen baseline manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.baseline.replay import build_replay_manifest, write_replay_manifest
from tools.baseline.runner import output_path, run_manifest, validate_manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="JSON manifest to freeze in a new or resumed run directory")
    parser.add_argument("--check", action="store_true", help="validate manifest without executing")
    parser.add_argument("--retry-failed", action="store_true", help="append attempts for failed items")
    parser.add_argument("--output-root", type=Path, help="host-local absolute root for a logical run directory")
    parser.add_argument("--replay-suffix", help="derive a new portable run ID from a historical manifest")
    args = parser.parse_args(argv)
    if args.replay_suffix and args.output_root is None:
        parser.error("--replay-suffix requires --output-root")
    if args.replay_suffix:
        manifest = build_replay_manifest(args.manifest, args.replay_suffix)
        destination = output_path(manifest, args.output_root)
        if args.check:
            print(f"Valid portable replay: {manifest['run_id']} -> {destination}")
            return 0
        manifest_path = write_replay_manifest(args.manifest, args.output_root, args.replay_suffix)
    else:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        validate_manifest(manifest)
        destination = output_path(manifest, args.output_root)
        if args.check:
            print(f"Valid baseline manifest: {manifest['run_id']} -> {destination}")
            return 0
        manifest_path = args.manifest
    print(json.dumps(run_manifest(manifest_path, retry_failed=args.retry_failed,
                                  output_root=args.output_root), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
