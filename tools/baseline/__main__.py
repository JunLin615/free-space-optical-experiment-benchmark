"""Run or validate one frozen baseline manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.baseline.runner import run_manifest, validate_manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="JSON manifest to freeze in its output_directory")
    parser.add_argument("--check", action="store_true", help="validate manifest without executing")
    parser.add_argument("--retry-failed", action="store_true", help="append attempts for failed items")
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    validate_manifest(manifest)
    if args.check:
        print("Valid baseline manifest")
        return 0
    print(json.dumps(run_manifest(args.manifest, retry_failed=args.retry_failed), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
