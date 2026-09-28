"""Render the public question bank from canonical YAML cases.

The generated files are publication artifacts. Edit benchmark/cases/*.yaml,
then run this script, rather than editing the Markdown or HTML by hand.
"""

from __future__ import annotations

import argparse
from html import escape
from pathlib import Path
import re
import sys

import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASES = ROOT / "benchmark" / "cases"
DEFAULT_OUTPUT = ROOT / "benchmark" / "generated"
TITLE = "Free-Space Optical Experimental Reasoning — Question Bank"


def _sort_key(path: Path) -> list[tuple[int, object]]:
    """Give numeric ID segments their expected order (2 before 10)."""
    return [
        (1, int(part)) if part.isdigit() else (0, part.casefold())
        for part in re.split(r"(\d+)", path.as_posix())
    ]


def load_cases(case_dir: Path) -> list[dict]:
    paths = sorted(case_dir.rglob("*.yaml"), key=_sort_key)
    paths += sorted(case_dir.rglob("*.yml"), key=_sort_key)
    if not paths:
        raise ValueError(f"No YAML cases found under {case_dir}")
    cases = []
    seen_ids: set[str] = set()
    for path in paths:
        with path.open("r", encoding="utf-8") as stream:
            case = yaml.safe_load(stream)
        if not isinstance(case, dict):
            raise ValueError(f"{path}: expected a case object")
        if case.get("language") != "en":
            raise ValueError(f"{path}: the English question renderer requires language: en")
        for key in ("case_id", "title", "task"):
            if key not in case:
                raise ValueError(f"{path}: missing {key}")
        if case["case_id"] in seen_ids:
            raise ValueError(f"{path}: duplicate case ID {case['case_id']}")
        seen_ids.add(case["case_id"])
        cases.append(case)
    return sorted(cases, key=lambda case: _sort_key(Path(str(case["case_id"]))))


def _public_parts(case: dict) -> tuple[str, list[str], list[str], list[str], list[str]]:
    task = case["task"]
    if not isinstance(task, dict) or not task.get("statement"):
        raise ValueError(f"{case['case_id']}: missing task.statement")
    questions = [item["request"] for item in task.get("questions", [])]
    givens = []
    for given in task.get("givens", []):
        if isinstance(given, dict):
            symbol = given.get("symbol")
            value = given.get("value")
            unit = given.get("unit")
            if symbol is not None and value is not None and unit is not None:
                label = str(symbol).replace("_", " ")
                unit_suffix = "" if str(unit) in {"1", "dimensionless"} else f" {unit}"
                givens.append(f"{label} = {value}{unit_suffix}")
    return (
        str(task["statement"]).strip(),
        questions,
        givens,
        list(task.get("assumptions", [])),
        list(task.get("apparatus_constraints", [])),
    )


def _markdown_text(value: object) -> str:
    # Prevent raw HTML in a question from becoming executable page markup.
    return escape(str(value), quote=False).replace("\n", "  \n")


def render_markdown(cases: list[dict]) -> str:
    lines = [f"# {TITLE}", "", "Question bank generated from canonical case files.", ""]
    for case in cases:
        statement, questions, givens, assumptions, apparatus_constraints = _public_parts(case)
        lines.extend(
            [f"## {_markdown_text(case['case_id'])} — {_markdown_text(case['title'])}", "", _markdown_text(statement), ""]
        )
        if givens:
            lines.extend(["**Given quantities**", ""])
            lines.extend(f"- {_markdown_text(given)}" for given in givens)
            lines.append("")
        if assumptions:
            lines.extend(["**Assumptions**", ""])
            lines.extend(f"- {_markdown_text(item)}" for item in assumptions)
            lines.append("")
        if questions:
            lines.extend(["**Questions**", ""])
            lines.extend(f"{index}. {_markdown_text(question)}" for index, question in enumerate(questions, 1))
            lines.append("")
        if apparatus_constraints:
            lines.extend(["**Experimental constraints**", ""])
            lines.extend(f"- {_markdown_text(item)}" for item in apparatus_constraints)
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _html_paragraphs(value: str) -> str:
    return "\n".join(
        f"      <p>{escape(paragraph.strip()).replace(chr(10), '<br>')}</p>"
        for paragraph in re.split(r"\n\s*\n", value)
        if paragraph.strip()
    )


def render_html(cases: list[dict]) -> str:
    sections = []
    for case in cases:
        statement, questions, givens, assumptions, apparatus_constraints = _public_parts(case)
        case_id = escape(str(case["case_id"]), quote=True)
        title = escape(str(case["title"]))
        block = [f'    <section class="case" id="{case_id}">', f"      <h2>{case_id} — {title}</h2>"]
        block.append(_html_paragraphs(statement))
        if givens:
            block.extend(["      <h3>Given quantities</h3>", "      <ul>"])
            block.extend(f"        <li>{escape(given)}</li>" for given in givens)
            block.append("      </ul>")
        if assumptions:
            block.extend(["      <h3>Assumptions</h3>", "      <ul>"])
            block.extend(f"        <li>{escape(str(item))}</li>" for item in assumptions)
            block.append("      </ul>")
        if questions:
            block.extend(["      <h3>Questions</h3>", "      <ol>"])
            block.extend(f"        <li>{escape(str(question))}</li>" for question in questions)
            block.append("      </ol>")
        if apparatus_constraints:
            block.extend(["      <h3>Experimental constraints</h3>", "      <ul>"])
            block.extend(f"        <li>{escape(str(item))}</li>" for item in apparatus_constraints)
            block.append("      </ul>")
        block.append("    </section>")
        sections.append("\n".join(block))
    body = "\n".join(sections)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(TITLE)}</title>
  <style>
    body {{ max-width: 52rem; margin: 2rem auto; padding: 0 1.25rem; font: 1rem/1.6 system-ui, sans-serif; color: #1c2630; }}
    h1, h2, h3 {{ line-height: 1.25; }}
    .case {{ border-top: 1px solid #cad3dc; margin-top: 2.5rem; padding-top: 1rem; }}
    li {{ margin: .35rem 0; }}
  </style>
</head>
<body>
  <main>
    <h1>{escape(TITLE)}</h1>
    <p>Question bank generated from canonical case files.</p>
{body}
  </main>
</body>
</html>
"""


def generate(case_dir: Path, output_dir: Path, check: bool = False) -> int:
    cases = load_cases(case_dir)
    outputs = {
        output_dir / "questions.md": render_markdown(cases),
        output_dir / "questions.html": render_html(cases),
    }
    if check:
        stale = [str(path) for path, content in outputs.items() if not path.exists() or path.read_text(encoding="utf-8") != content]
        if stale:
            print("Generated artifacts are missing or stale:\n" + "\n".join(stale), file=sys.stderr)
            return 1
        print(f"Generated artifacts are current ({len(cases)} cases).")
        return 0
    output_dir.mkdir(parents=True, exist_ok=True)
    for path, content in outputs.items():
        path.write_text(content, encoding="utf-8", newline="\n")
        print(f"Wrote {path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES, help="Directory of canonical YAML cases")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Directory for generated Markdown and HTML")
    parser.add_argument("--check", action="store_true", help="Fail when generated files differ from current cases")
    args = parser.parse_args()
    try:
        return generate(args.cases, args.output, args.check)
    except (KeyError, TypeError, ValueError, OSError, yaml.YAMLError) as exc:
        print(f"Render failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
