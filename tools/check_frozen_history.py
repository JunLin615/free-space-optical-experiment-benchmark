"""Protect published release candidates and measured campaign evidence.

These commitments are intentionally independent of the stable release manifest.
New release work cannot update the expected digests to reinterpret old evidence.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
import sys

from tools.analyze_campaign import analyze_campaign


ROOT = Path(__file__).resolve().parents[1]
FROZEN_SHA256 = {
    "benchmark/releases/0.1.0-rc1.json": "2a7f04298dbe27db549ab5307e9cd4e314a8a4e4e83aa503206410c993867516",
    "benchmark/releases/0.1.0-rc1-environment.json": "3e1b2b0161c63383c6d1132f49eb08c35c1369dfe24ebd45a507d8c3620ffd45",
    "benchmark/releases/0.2.0-rc1.json": "0d2950e9ecac3e49094c6a5e02cee49ea937d0bad2f00cc82c140c687cc192f7",
    "benchmark/results/campaigns/2026-09-28-multimodel-020rc1/campaign.json": "7721372a7bf46d4ad1769cd8bfe078607d775a0522b95ce1b63982491b4d770c",
    "自由空间光学实验推理试题集_初版.html": "077db14d2a5c67a3123c82af1d571f8ffa73d3c79501c7c9d8c99e021c2318a8",
}


def check() -> dict[str, int]:
    for relative, expected in FROZEN_SHA256.items():
        actual = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f"historical bytes changed: {relative}")
    index = ROOT / "benchmark/results/campaigns/2026-09-28-multimodel-020rc1/campaign.json"
    summary = analyze_campaign(index)
    if (summary["formal_record_count"] != 108 or summary["formal_system_count"] != 3 or
            len(summary["public_variant_probe"]) != 3 or
            len(summary["hidden_family_disjoint"]) != 3):
        raise ValueError("historical campaign structure changed")
    return {"frozen_files": len(FROZEN_SHA256), "formal_records": 108,
            "formal_systems": 3, "public_variant_runs": 3, "hidden_attestations": 3}


if __name__ == "__main__":
    try:
        print("Frozen history:", check())
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Frozen history check failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
