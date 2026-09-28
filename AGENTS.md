# Instructions for coding agents

- Build an autonomous-agent benchmark for **free-space optical experimental reasoning**. Physics correctness and testable experimental requirements outrank implementation convenience.
- Keep scientific cases and gold specifications independent of OpenSci, optical-design packages, agent frameworks, vendor identifiers, and supplier SKUs. Tool adapters belong outside the canonical benchmark.
- Exclude purely on-chip and purely fiber-only systems from the core. A fiber interface can appear in an otherwise free-space experiment.
- Author new pilot and design content in **English first**, per the current project instruction. The original 64-case Chinese HTML is preserved, unchanged, as source provenance. Add Chinese only after English content is finalized.
- Canonical machine-readable case files are the source of truth. Generate clean question-bank HTML and Markdown; never hand-edit generated artifacts or turn them into tutorials or conversations. Keep gold material out of the default public question view.
- Normal benchmark execution and grading must never require an expert in the loop. Use unit-aware numerical checks, executable physics, structured constraints, and calibrated bounded semantic judging as appropriate. Do not mark a case release-verified until its autonomous oracle is tested against valid alternatives and adversarial invalid answers.
- Run `python tools/validate_cases.py`, `python -m unittest discover -s tests`, and `python tools/render_cases.py --check` before a PR. Keep the original HTML seed unchanged.
- Use GitHub Issues for design problems and focused PRs against `main` for changes. Explain scientific assumptions, case lineage, accepted alternatives, validator evidence, and limitations. Do not expand the case bank merely to increase its size.
