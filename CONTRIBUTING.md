# Contributing

Use [GitHub Issues](https://github.com/JunLin615/free-space-optical-experiment-benchmark/issues) for case proposals, physics corrections, ambiguities, scoring problems, and tooling changes. Open a focused pull request against `main` for implementation; do not push changes directly to `main`.

For a benchmark case, describe the free-space experimental objective, assumptions, given quantities and units, requested observables, plausible valid alternatives, known failure modes, and an autonomous way to verify each scored claim. Cite sources or label synthetic scenarios accurately. Keep benchmark science independent of any agent framework, tool, vendor, or component SKU. Purely on-chip and fiber-only problems are outside the core scope. New cases start as drafts and need executable or calibrated autonomous scoring before entering a scored release. Do not copy third-party question text without permission.

Canonical case YAML is the source of truth. Rendered HTML and Markdown are generated artifacts. The original 64-case HTML seed is preserved as provenance and must not be edited. Pilot content is authored in English first; a Chinese version can follow once the English cases are finalized.

Before opening a PR, run `python tools/validate_cases.py`, `python -m unittest discover -s tests`, and `python tools/render_cases.py --check`. Include the case IDs or files changed, scientific justification, validator evidence, accepted alternative answers tested, and any unresolved limitations. A case with uncertain physics or unreliable automatic scoring should remain in development or be quarantined, rather than enter a scored release.

The code is MIT licensed under [LICENSE](LICENSE). Benchmark questions, gold specifications, the preserved seed, generated question-bank views, and narrative documentation are CC BY 4.0 under [LICENSE-CONTENT](LICENSE-CONTENT). Contributions to each category are made under its stated license. Declare any third-party material separately; its original license continues to apply.
