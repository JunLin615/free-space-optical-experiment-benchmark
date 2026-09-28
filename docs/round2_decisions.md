# Round 2 foundation decisions

This record documents the choices needed to publish and test a machine-readable pilot. It supplements, rather than replaces, the Round 1 research proposals. No pilot case is presented as a fully verified scored item.

## Publication and name

The repository is public at [JunLin615/free-space-optical-experiment-benchmark](https://github.com/JunLin615/free-space-optical-experiment-benchmark). The name spells out the optical regime and experimental focus. The Round 1 search found collisions for `OpticsBench` and warned that `FSO` is often read as free-space optical communications; neither is used here. A fresh GitHub search found no exact repository match for this name when it was created. The user expressly requested publication in this round, superseding Round 1's suggested timing. Publication of the *repository* does not confer `release_verified` status on the pilot cases or announce a benchmark v0.1 release.

The stable `main` branch contains the Round 1 research baseline. Work proceeds on `feat/benchmark-foundation-v0.1` through a pull request. `main` requires a PR and disallows force pushes and deletions. Issues are enabled.

## Language and provenance

The pasted Round 2 brief described the current benchmark language as Chinese. A subsequent user clarification established **English-first development** for the pilot cases and generated question bank. The original Chinese HTML remains untouched as seed provenance, with its hash recorded in each derived pilot case. A corresponding Chinese page should follow once the English content is close to stable, using the same case identities and scientific lineage rather than becoming a separate benchmark. Each English pilot preserves the seed's physical question and subquestions; ambiguities are documented rather than silently converted into new physics.

## Format and boundaries

One YAML file per case is the canonical authoring format. JSON Schema 2020-12 checks its structure; the generated HTML/Markdown are question-only views. Development gold currently lives with each public pilot YAML, so these 11 cases are suitable for interface and scorer development rather than a hidden test. Future private instances must keep gold and seeds outside the public repository. The generic run-result schema is separate from the case schema. Tool adapters and an optional retrieval library are separate from scientific case content.

Generic access to tools and the example library belongs to a protocol manifest, not `task`. The pilot cases no longer contain or render the former generic `allowed_resources` line. An optional `task.apparatus_constraints` field is reserved for restrictions intrinsic to the optical experiment, such as a fixed set of available components; it cannot grant evaluation tool access. The result contract records explicit tool-call count, provider usage, and measured cost with currency and pricing provenance, preserving unavailable values as `null`.

The schema supports optional numerical checks, physical constraints, alternative solution families, forbidden claims, and semantic rubrics. These are available when relevant, not forced onto every case. The pilot statuses remain `specified` until positive and adversarial fixtures, independent checks, and any semantic judges meet the evidence gates in [automated validation design](automated_validation_design.md). The deterministic physics module verifies only selected numerical claims; the open design and diagnosis criteria are deliberately not awarded a benchmark score yet.

## Licensing

The Round 1 documents did not select a license. MIT covers code, schemas, tests, and tooling; CC BY 4.0 covers benchmark cases, gold, the original seed, generated question views, and narrative research/design documents. The separate scope statements in [LICENSE](../LICENSE) and [LICENSE-CONTENT](../LICENSE-CONTENT) keep reuse terms explicit. The original seed is user supplied; no third-party benchmark question content was copied. Future outside contributions must identify source rights and licenses. This is a project licensing choice, not a claim that all future imported material automatically inherits it.

## Deferred

The remaining 53 seed cases, complete scoring of open designs, a model runner, case-library retrieval, hidden evaluation, parameterized instances, and leaderboard policies await subsequent rounds. CI uses no paid model judge. Baseline agent runs should start once a small subset reaches `release_verified` with reliable autonomous scoring; reports must distinguish those scores from pilot-development checks.
