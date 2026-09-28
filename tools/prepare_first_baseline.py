"""Create the three immutable input manifests for the first small real baseline."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from tools.baseline.runner import validate_manifest


ROOT = Path(__file__).resolve().parents[1]
PROTOCOLS = ["closed_book", "case_assisted", "tool_assisted", "case_and_tool_assisted"]
VERIFIED = ["SEED-1-1", "SEED-1-5", "SEED-1-7", "SEED-2-2", "SEED-4-2"]
DEVELOPMENT = ["SEED-2-4", "SEED-3-1"]
VARIANTS = [
    "VAR-SEED-1-1-P-c8828a9799d3.json",
    "VAR-SEED-1-1-U-613088edc5d1.json",
]


def selection(case_id: str, track: str, variant_path: str | None = None) -> dict:
    return {"case_id": case_id, "track": track, "variant_path": variant_path}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=ROOT / "runs")
    parser.add_argument("--suffix", default="", help="new immutable run suffix for a repeated experiment")
    args = parser.parse_args()
    output_root = args.output_root.resolve()
    suites = {
        "verified": ([selection(case_id, "verified") for case_id in VERIFIED], PROTOCOLS),
        "development": ([selection(case_id, "development") for case_id in DEVELOPMENT], ["closed_book"]),
        "variants": ([selection("SEED-1-1", "verified")] + [
            selection("SEED-1-1", "public_variant", (Path("benchmark/variants/public_dev") / name).as_posix())
            for name in VARIANTS], ["closed_book"]),
    }
    manifest_dir = output_root / "input_manifests"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    for suite, (selections, protocols) in suites.items():
        run_id = f"2026-09-28-gpt-6-luna-{suite}{args.suffix}"
        manifest = {
            "schema_version": "0.1.0", "run_id": run_id,
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "execution_class": "real", "release_id": "0.1.0-rc1",
            "selections": selections, "protocol_ids": protocols,
            "agent": {"adapter_type": "codex_cli", "provider": "openai", "model_id": "gpt-6-luna",
                      "model_version": None, "framework": "codex-cli-0.158.0",
                      "scaffold_id": "neutral_optics_v1", "command": None,
                      "command_prefix": ["npx", "-y", "@openai/codex@0.158.0"],
                      "mock_script": None},
            "runner_version": "0.1.0", "system_prompt_version": "neutral_optics_v1",
            "retrieval_config": {"max_items": 3},
            "tool_config": {"profile_id": "generic_computation_v0.1", "max_calls": 6},
            "retry_policy": {"transport_max_retries": 0, "malformed_answer_max_retries": 0,
                             "self_correction_max_retries": 0},
            "timeout_seconds": 300, "concurrency": 1, "seed": 20260928,
            "output_directory": run_id, "pricing_snapshot": None,
        }
        validate_manifest(manifest)
        path = manifest_dir / (run_id + ".json")
        if path.exists():
            raise FileExistsError(f"input manifest is immutable: {path}")
        path.write_text(json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                        encoding="utf-8")
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
