"""Render the zh-CN public view from a text-only overlay and canonical English cases.

The English case YAML remains the sole source of scientific values, identity,
question lineage, and scoring. This module does not change the frozen English
renderer or any historical release artifact.
"""

from __future__ import annotations

import argparse
from decimal import Decimal
import hashlib
from html import escape
import json
from pathlib import Path
import re
import sys

import yaml

try:
    from tools.render_cases import DEFAULT_CASES, DEFAULT_OUTPUT, load_cases
except ModuleNotFoundError:  # direct `python tools/render_zh_cn.py` invocation
    from render_cases import DEFAULT_CASES, DEFAULT_OUTPUT, load_cases


ROOT = Path(__file__).resolve().parents[1]
OVERLAY = ROOT / "benchmark" / "locales" / "zh-CN.v1.yaml"
TITLE = "自由空间光学实验推理题库"
TOKEN = re.compile(r"\{\{([a-z][a-z0-9_]*)\}\}")
NUMERIC_LITERAL = re.compile(r"(?<![A-Za-z0-9])(?:10\^-?\d+|[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)")

GIVEN_LABELS = {
    "mirror_rotation": "反射镜转角", "screen_distance": "屏幕距离",
    "lateral_offset": "横向位移", "input_height": "输入高度", "output_height": "输出高度",
    "stage_displacement": "位移台行程", "target_delay": "目标延迟",
    "reflected_wavelength": "反射波长", "transmitted_wavelength": "透射波长",
    "input_to_fast_axis_angle": "入射偏振与快轴夹角", "plate_rotation": "波片附加转角",
    "wavelength": "波长", "focal_length": "焦距", "incident_radius": "入射光束半径",
    "input_diameter": "输入光束直径", "output_diameter": "输出光束直径",
    "pulse_duration": "脉冲持续时间", "pulse_energy": "脉冲能量",
    "expansion_factor": "扩束倍率", "initial_waist_radius": "初始束腰半径",
    "final_waist_radius": "最终束腰半径",
    "horizontal_to_vertical_diameter_ratio": "水平与竖直光束直径比",
    "beam_radius": "光束半径", "clear_aperture_radius": "通光孔径半径",
    "target_geometric_loss": "目标几何截光比例", "target_reduction_factor": "目标缩小倍数",
    "object_distance_in_focal_lengths": "物距对应焦距倍数",
    "numerical_aperture": "数值孔径",
    "mirror_displacement_wavelengths": "反射镜位移对应波长倍数",
    "quarter_mirror_displacement_wavelengths": "较小位移对应波长倍数",
    "relative_transmission_change": "相对透射率变化",
    "lo_frequency_offset": "本振频率偏移", "target_line": "目标谱线波长",
    "excitation_wavelength": "激发波长", "central_wavelength": "中心波长",
    "delay_start": "扫描起始延迟", "delay_end": "扫描终止延迟",
    "target_resolution": "目标时间分辨率",
    "fundamental_wavelength": "基频波长", "second_harmonic_wavelength": "二次谐波波长",
}

UNIT_SYMBOLS = {"deg": "°", "um": "μm", "percent": "%"}


def _quantity_text(given: dict) -> str:
    """Format only a canonical value and its canonically stored physical unit."""
    unit = str(given["unit"])
    if unit in {"1", "dimensionless"}:
        return str(given["value"])
    display = UNIT_SYMBOLS.get(unit, unit)
    spacer = "" if display in {"°", "%"} else " "
    return f"{given['value']}{spacer}{display}"


def public_fingerprint(cases: list[dict]) -> str:
    """Fingerprint public EN content only; gold/scoring are intentionally absent."""
    public = [
        {
            "case_id": case["case_id"],
            "title": case["title"],
            "task": {key: case["task"].get(key, []) for key in (
                "statement", "questions", "givens", "assumptions", "apparatus_constraints"
            )},
        }
        for case in cases
    ]
    data = json.dumps(public, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _numeric_literals(text: str) -> set[Decimal]:
    """Bounded literal check: Arabic numerals and 10^n notation, not prose numbers.

    This guards against a changed wavelength, distance, multiplier, or power in
    translation. It is set-based and does not replace scientific human review of
    context, repeated values, or numbers written as words.
    """
    literals = set()
    for token in NUMERIC_LITERAL.findall(text.replace("−", "-")):
        literals.add(Decimal(10) ** int(token[3:]) if token.startswith("10^") else Decimal(token))
    return literals


def load_localized_cases(cases: list[dict], overlay_path: Path, expected_count: int = 64) -> list[dict]:
    """Enforce identity, order, question, and canonical-value parity."""
    overlay = yaml.safe_load(overlay_path.read_text(encoding="utf-8"))
    if not isinstance(overlay, dict) or overlay.get("schema_version") != 1 or overlay.get("locale") != "zh-CN":
        raise ValueError("Invalid zh-CN overlay header")
    if len(cases) != expected_count:
        raise ValueError(f"Expected {expected_count} canonical English cases, found {len(cases)}")
    if overlay.get("canonical_public_sha256") != public_fingerprint(cases):
        raise ValueError("zh-CN overlay is stale relative to current English public content")
    entries = overlay.get("cases")
    ids = [case["case_id"] for case in cases]
    if not isinstance(entries, dict) or list(entries) != ids:
        raise ValueError("zh-CN case IDs or order differ from English canonical cases")

    localized = []
    for case in cases:
        case_id = case["case_id"]
        entry = entries[case_id]
        if not isinstance(entry, dict) or set(entry) != {"title", "statement", "questions", "assumptions", "apparatus_constraints"}:
            raise ValueError(f"{case_id}: overlay must contain public text fields only")
        task = case["task"]
        en_questions = task.get("questions", [])
        question_ids = [q["id"] for q in en_questions]
        if not isinstance(entry["questions"], dict) or list(entry["questions"]) != question_ids:
            raise ValueError(f"{case_id}: question IDs/order differ from English")
        for field in ("assumptions", "apparatus_constraints"):
            if not isinstance(entry[field], list) or len(entry[field]) != len(task.get(field, [])):
                raise ValueError(f"{case_id}: {field} count differs from English")
        givens = {g["symbol"]: g for g in task.get("givens", [])}
        used = set()

        def substitute(value: str) -> str:
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{case_id}: blank or non-text translation")

            def replacement(match: re.Match[str]) -> str:
                symbol = match.group(1)
                if symbol not in givens:
                    raise ValueError(f"{case_id}: unknown canonical given {symbol}")
                used.add(symbol)
                return _quantity_text(givens[symbol])

            return TOKEN.sub(replacement, value)

        translated = {
            "case_id": case_id,
            "title": substitute(entry["title"]),
            "statement": substitute(entry["statement"]),
            "questions": [substitute(entry["questions"][qid]) for qid in question_ids],
            "assumptions": [substitute(item) for item in entry["assumptions"]],
            "apparatus_constraints": [substitute(item) for item in entry["apparatus_constraints"]],
            "givens": task.get("givens", []),
        }
        if set(givens) - used:
            raise ValueError(f"{case_id}: missing canonical given references: {sorted(set(givens) - used)}")
        english_public = " ".join([
            case["title"], task["statement"],
            *(q["request"] for q in en_questions),
            *task.get("assumptions", []), *task.get("apparatus_constraints", []),
        ])
        chinese_public = " ".join([
            translated["title"], translated["statement"], *translated["questions"],
            *translated["assumptions"], *translated["apparatus_constraints"],
        ])
        en_numbers = _numeric_literals(english_public)
        zh_numbers = _numeric_literals(chinese_public)
        given_numbers = {Decimal(str(g["value"])) for g in givens.values()}
        if en_numbers - zh_numbers or zh_numbers - en_numbers - given_numbers:
            raise ValueError(f"{case_id}: numeric literal parity failed: "
                             f"EN-only={sorted(en_numbers - zh_numbers)}, "
                             f"ZH-only={sorted(zh_numbers - en_numbers - given_numbers)}")
        localized.append(translated)
    if [c["case_id"] for c in localized] != ids:
        raise ValueError("zh-CN identity parity failed")
    if any(zh["givens"] != en["task"].get("givens", []) for en, zh in zip(cases, localized)):
        raise ValueError("zh-CN scientific givens differ from English")
    return localized


def _given_line(given: dict) -> str:
    symbol = given["symbol"]
    if symbol not in GIVEN_LABELS:
        raise ValueError(f"Missing zh-CN given label for {symbol}")
    return f"{GIVEN_LABELS[symbol]} = {_quantity_text(given)}"


def render_markdown(cases: list[dict]) -> str:
    lines = [f"# {TITLE}", ""]
    for case in cases:
        lines.extend([f"## {escape(case['case_id'])} — {escape(case['title'])}", "", escape(case["statement"]), ""])
        if case["givens"]:
            lines.extend(["**已知量**", ""])
            lines.extend(f"- {escape(_given_line(given))}" for given in case["givens"])
            lines.append("")
        for label, field in (("假设", "assumptions"), ("问题", "questions"), ("实验约束", "apparatus_constraints")):
            if case[field]:
                lines.extend([f"**{label}**", ""])
                lines.extend(f"{i}. {escape(item)}" if field == "questions" else f"- {escape(item)}"
                             for i, item in enumerate(case[field], 1))
                lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_html(cases: list[dict]) -> str:
    sections = []
    for case in cases:
        case_id = escape(case["case_id"], quote=True)
        parts = [f'<section class="case" id="{case_id}">',
                 f"<h2>{case_id} — {escape(case['title'])}</h2>",
                 f"<p>{escape(case['statement'])}</p>"]
        if case["givens"]:
            parts.append("<h3>已知量</h3><ul>")
            parts.extend(f"<li>{escape(_given_line(given))}</li>" for given in case["givens"])
            parts.append("</ul>")
        for label, field, tag in (("假设", "assumptions", "ul"), ("问题", "questions", "ol"),
                                  ("实验约束", "apparatus_constraints", "ul")):
            if case[field]:
                parts.append(f"<h3>{label}</h3><{tag}>")
                parts.extend(f"<li>{escape(item)}</li>" for item in case[field])
                parts.append(f"</{tag}>")
        parts.append("</section>")
        sections.append("\n    ".join(parts))
    body = "\n    ".join(sections)
    return f'''<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{TITLE}</title>
  <style>
    body {{ max-width: 52rem; margin: 2rem auto; padding: 0 1.25rem; font: 1rem/1.6 system-ui, sans-serif; color: #1c2630; }}
    h1, h2, h3 {{ line-height: 1.25; }}
    .case {{ border-top: 1px solid #cad3dc; margin-top: 2.5rem; padding-top: 1rem; }}
    li {{ margin: .35rem 0; }}
  </style>
</head>
<body>
  <main>
    <h1>{TITLE}</h1>
    {body}
  </main>
</body>
</html>
'''


def generate(case_dir: Path = DEFAULT_CASES, output_dir: Path = DEFAULT_OUTPUT,
             overlay_path: Path = OVERLAY, check: bool = False) -> int:
    localized = load_localized_cases(load_cases(case_dir), overlay_path)
    outputs = {
        output_dir / "questions.zh-CN.md": render_markdown(localized),
        output_dir / "questions.zh-CN.html": render_html(localized),
    }
    if check:
        stale = [str(path) for path, content in outputs.items()
                 if not path.exists() or path.read_text(encoding="utf-8") != content]
        if stale:
            print("Missing or stale zh-CN artifacts:\n" + "\n".join(stale), file=sys.stderr)
            return 1
        print(f"zh-CN question bank current ({len(localized)} cases; IDs/questions/givens in parity).")
        return 0
    output_dir.mkdir(parents=True, exist_ok=True)
    for path, content in outputs.items():
        path.write_text(content, encoding="utf-8", newline="\n")
        print(f"Wrote {path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--overlay", type=Path, default=OVERLAY)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        return generate(args.cases, args.output, args.overlay, args.check)
    except (OSError, TypeError, ValueError, KeyError, yaml.YAMLError) as exc:
        print(f"zh-CN render failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
