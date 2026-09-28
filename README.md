# Free-Space Optical Experiment Benchmark

An open benchmark under development for evaluating autonomous agents on **free-space optical experimental reasoning**: quantitative prediction, beam-path design, diagnosis, calibration, and defensible engineering trade-offs. The scientific questions are independent of OpenSci, any agent framework, vendor, and optical-design software. Planned protocols compare closed-book, case-assisted, tool-assisted, and combined access to the *same* cases.

**Status:** the original 64-case seed has been canonically migrated into English case YAML, but scoring support remains partial and no case is `release_verified`. The original Chinese HTML is preserved byte for byte as provenance. The [generated Markdown](benchmark/generated/questions.md) and [HTML](benchmark/generated/questions.html) show questions only; gold specifications stay in the canonical case files. The [migration report](docs/migration_report.md), [coverage report](docs/coverage_report.md), and [scoring-readiness plan](docs/scoring_readiness.md) document corpus scope and remaining oracle work.

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
```

`tools/validate_cases.py` checks schema structure, IDs, taxonomy, cross-field references, tolerances, and registered physics references. `tools/check_corpus.py` verifies all 64 legacy IDs and the original seed hash. `tools/render_cases.py` regenerates public question views from canonical YAML. CI also runs unit tests, scoring fixtures, and verification-status gates without a paid model API. Most cases have a specification and proposed oracle only; a YAML record alone does not mean a case can be scored autonomously.

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
