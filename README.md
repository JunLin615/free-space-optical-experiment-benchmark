# Free-Space Optical Experiment Benchmark

A public benchmark for autonomous reasoning about **free-space optical experiments**. It covers quantitative prediction, beam paths, diagnosis, calibration, and constrained design. Scientific cases and scoring are independent of OpenSci, agent frameworks, vendors, and optical-design products. Normal scoring requires no human grader.

## What is released

The repository contains **64 canonical English cases** derived from the preserved Chinese seed. They form a public scientific case bank with explicit development status; inclusion in that bank does not mean a case has a qualified autonomous scorer. The initial stable **v0.2.0 release contains nine `release_verified` cases** in nine concept families, with an [immutable manifest](benchmark/releases/0.2.0.json) and executable qualification. Other cases remain specified, executable, challenged, or development material according to their evidence. The original Chinese HTML remains byte-identical provenance.

Public question-only views are generated in [English](benchmark/generated/questions.md) and [Chinese](benchmark/generated/questions.zh-CN.md), with HTML counterparts. Both present the same 64 case identities and scientific quantities. Gold answers, scoring rules, and evaluator logic remain in shared canonical data and code; the Chinese layer supplies public-facing text.

The frozen historical releases [`0.1.0-rc1`](benchmark/releases/0.1.0-rc1.json) and [`0.2.0-rc1`](benchmark/releases/0.2.0-rc1.json) remain independently reproducible. The [three-model `0.2.0-rc1` campaign](docs/results/2026-09-28-multimodel-020rc1.md) records **108 real public formal results** from nine cases under four matched protocols. It also retains separate public development-variant evidence and public-safe attestations for a family-disjoint hidden pilot. These are historical rc1 results; the stable `SEED-3-1` contract repair does not change their scores. Nine public verified cases support descriptive paired comparisons, not universal model rankings.

## Evaluation components

- [Four matched protocols](docs/protocols.md): `closed_book`, `case_assisted`, `tool_assisted`, and `case_and_tool_assisted`, with identical scientific question bytes.
- [Versioned case/example library](docs/case_library.md) and deterministic retrieval, separate from case prompts and gold.
- [Provider-neutral resumable runner](docs/baseline_runner.md) with raw responses, parsed answers, scoring results, usage, retrieval, tool events, logs, and source provenance.
- [Public development variants](docs/variants.md) for robustness work and a [family-disjoint hidden-evaluation policy](docs/hidden_evaluation.md) with external private bundles and evidence-derived public attestations.
- Unit-aware numerical and structured physics scorers, release fixtures, and independent tests. Open-design and diagnosis scorers remain conservative development work; unknown plausible designs can return `unresolved`.

The benchmark supplies a bounded generic computation-tool profile. Formal campaign models were offered this profile, but made zero observed tool calls. Monetary cost was unavailable through that CLI interface and remains `null` in the evidence.

## Verify the release locally

Release qualification uses the pinned **CPython 3.11.16** environment in [`0.1.0-rc1-environment.json`](benchmark/releases/0.1.0-rc1-environment.json). Obtain its exact package requirements with `python tools/check_release_environment.py --requirements`, install them in a fresh 3.11.16 environment, then run:

```sh
python tools/check_release_environment.py --check
python tools/validate_cases.py
python tools/check_corpus.py
python -m unittest discover -s tests
python tools/run_case_fixtures.py
python tools/check_verification_status.py
python tools/render_cases.py --check
python tools/generate_coverage.py --check
python tools/qualify_release.py --check
python tools/qualify_vnext.py --check
python tools/qualify_stable.py --check
python -m tools.check_frozen_history
python -m tools.analyze_campaign benchmark/results/campaigns/2026-09-28-multimodel-020rc1/campaign.json --check
```

The renderer also verifies the English/Chinese public-view parity. All release and campaign checks run offline; no model API call or human adjudication is needed. The [release notes](docs/release_v0.2.0.md) describe the stable lineage and validation gates.

## Repository map and limits

`benchmark/cases/` holds the 64 canonical English case identities. Versioned release case revisions, manifests, schemas, fixtures, and generated views live under `benchmark/`. `tools/` contains validation, qualification, scoring, rendering, and runner code; `tests/` contains regression and challenge tests. `runs/` holds public measured evidence. `docs/` explains the [design](docs/benchmark_design.md), [campaign findings](docs/results/2026-09-28-multimodel-020rc1-findings.md), and [current freeze status](docs/project_status.md).

The nine-case release is an initial, bounded benchmark. It does not establish performance across every optical laboratory task. Open-ended experimental design and diagnosis still lack qualified coverage of all credible architectures; [Issue #3](https://github.com/JunLin615/free-space-optical-experiment-benchmark/issues/3) tracks that research boundary. Additional cases or broader semantic scoring require a future version and independent challenge evidence. The original [roadmap](docs/project_roadmap.md) remains a historical planning document.

Source code, schemas, tests, and tooling are MIT licensed under [LICENSE](LICENSE). Benchmark content, seed, public question views, and research documents are CC BY 4.0 under [LICENSE-CONTENT](LICENSE-CONTENT). Cite the exact release and evaluator version used; [CITATION.cff](CITATION.cff) provides repository metadata. Contributions use focused pull requests and [Issues](https://github.com/JunLin615/free-space-optical-experiment-benchmark/issues); see [CONTRIBUTING.md](CONTRIBUTING.md) and [AGENTS.md](AGENTS.md).
