"""Check the 64-case English/Chinese public question-bank parity and outputs."""

from __future__ import annotations

import sys

try:
    from tools.render_cases import DEFAULT_CASES, DEFAULT_OUTPUT, load_cases, render_html as render_en_html, render_markdown as render_en_markdown
    from tools.render_zh_cn import OVERLAY, load_localized_cases, render_html as render_zh_html, render_markdown as render_zh_markdown
except ModuleNotFoundError:  # direct `python tools/check_localization.py` invocation
    from render_cases import DEFAULT_CASES, DEFAULT_OUTPUT, load_cases, render_html as render_en_html, render_markdown as render_en_markdown
    from render_zh_cn import OVERLAY, load_localized_cases, render_html as render_zh_html, render_markdown as render_zh_markdown


def check() -> None:
    english = load_cases(DEFAULT_CASES)
    chinese = load_localized_cases(english, OVERLAY, expected_count=64)
    outputs = {
        "questions.md": render_en_markdown(english),
        "questions.html": render_en_html(english),
        "questions.zh-CN.md": render_zh_markdown(chinese),
        "questions.zh-CN.html": render_zh_html(chinese),
    }
    for filename, expected in outputs.items():
        path = DEFAULT_OUTPUT / filename
        if not path.exists() or path.read_text(encoding="utf-8") != expected:
            raise ValueError(f"Missing or stale public question bank: {path}")
    ids = [case["case_id"] for case in english]
    if ids != [case["case_id"] for case in chinese]:
        raise ValueError("Case ID/order parity failed")
    questions = sum(len(case["task"]["questions"]) for case in english)
    if questions != sum(len(case["questions"]) for case in chinese):
        raise ValueError("Question count parity failed")
    print(f"EN/ZH parity passed: {len(ids)} identical case IDs, {questions} paired questions, "
          "canonical givens and bounded numeric literals; four current public artifacts.")


def main() -> int:
    try:
        check()
        return 0
    except (OSError, TypeError, ValueError, KeyError) as exc:
        print(f"Localization check failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
