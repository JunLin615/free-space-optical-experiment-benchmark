# Free-Space Optical Experiment Benchmark

An open benchmark under development for evaluating autonomous agents on **free-space optical experimental reasoning**: quantitative prediction, beam-path design, diagnosis, calibration, and defensible engineering trade-offs. The scientific questions are independent of OpenSci, any agent framework, vendor, and optical-design software. Planned protocols compare closed-book, case-assisted, tool-assisted, and combined access to the *same* cases.

**Status:** all 64 seed cases are canonical English YAML. Eighteen cases have registered autonomous scorers, including all ten deterministic-ready cases. Five typed-answer cases form the first evidence-pinned `0.1.0-rc1` release candidate; the [manifest](benchmark/releases/0.1.0-rc1.json) and [qualification report](docs/qualification_report.md) state its exact scope and exclusions. The original Chinese HTML remains byte for byte unchanged. The [generated Markdown](benchmark/generated/questions.md) and [HTML](benchmark/generated/questions.html) show questions only; gold specifications remain in canonical case files.

## Run the local checks

Use Python 3.11 or later:

```sh
python -m pip install -r requirements.txt
python tools/validate_cases.py
python tools/check_corpus.py
python -m unittest discover -s tests
python tools/run_case_fixtures.py
python tools/check_verification_status.py
python tools/render_cases.py --check
python tools/generate_coverage.py --check
python tools/qualify_release.py --check
```

`tools/validate_cases.py` checks schema structure, IDs, taxonomy, cross-field references, tolerances, and registered physics references. `tools/check_corpus.py` verifies all 64 legacy IDs and the original seed hash. `tools/render_cases.py` regenerates public question views from canonical YAML. CI also runs unit tests, scoring fixtures, and verification-status gates without a paid model API. Most cases have a specification and proposed oracle only; a YAML record alone does not mean a case can be scored autonomously.

The rc1 qualification check requires the [locked release environment](benchmark/releases/0.1.0-rc1-environment.json): CPython 3.11.16 and its listed exact package versions. Run `python tools/check_release_environment.py --requirements` to obtain the pip requirements for that environment, and `python tools/check_release_environment.py --check` to verify it. Other development Python versions can run the case and fixture checks, but cannot certify rc1 qualification.

Run `python tools/qualify_release.py` to inspect each selected case's evidence and exact blockers. The release candidate scores only the required typed claims. Optional explanation prose is retained for audit and does not change a deterministic score. Unfamiliar plausible structured answers may return `unresolved`; no expert grades normal runs. The manifest pins case, evaluator, fixture, derivation, generated-view, dependency, and gate files by SHA-256. It is a technical release candidate, with no model-baseline or empirical-difficulty claim.

## Repository map

- `benchmark/cases/`: canonical English seed cases, one YAML file per case.
- `benchmark/coverage/`: complete-corpus classifications, concept families, and migration status.
- `benchmark/schema/`: versioned case and future run-result JSON Schemas.
- `benchmark/generated/`: generated question-only Markdown and HTML.
- `tools/` and `tests/`: schema validation, rendering, physics checks, and tests.
- `docs/`: [Round 2 decisions](docs/round2_decisions.md), [benchmark design](docs/benchmark_design.md), [case schema proposal](docs/case_schema_proposal.md), [evaluation design](docs/evaluation_design.md), [automated validation design](docs/automated_validation_design.md), [seed audit](docs/research/seed_audit.md), [benchmark landscape](docs/research/benchmark_landscape.md), and [roadmap](docs/project_roadmap.md).

The long-term scoring design combines unit-aware calculations, independent optical physics, constraints that admit multiple valid designs, and calibrated semantic judges for bounded residual claims. Normal evaluation must run **without human expert grading**. Open-ended pilot cases are not promoted to a scored release until their autonomous oracles have been challenged with valid alternatives and plausible wrong answers. The optional optical case/example library will be versioned separately from benchmark prompts and gold specifications.

Use [Issues](https://github.com/JunLin615/free-space-optical-experiment-benchmark/issues) to propose or correct a case or discuss infrastructure. Contributions use focused pull requests to `main`; see [CONTRIBUTING.md](CONTRIBUTING.md) and [AGENTS.md](AGENTS.md).

Source code, schemas, tests, and tooling are MIT licensed under [LICENSE](LICENSE). Benchmark content, the seed, generated question views, and research/design documents are CC BY 4.0 under [LICENSE-CONTENT](LICENSE-CONTENT). Cite the exact case and evaluator release used; [CITATION.cff](CITATION.cff) provides repository metadata.
