# Roadmap to a public autonomous-agent benchmark

Status: planning proposal, 2026-09-28. The 64-case HTML is an intact seed, not a ready-to-score benchmark. New documentation is English first; Chinese can be added after the English design and content stabilize. This round does not translate or expand the question bank.

## Current round: research foundation

- Preserve the seed unchanged; inventory all 64 cases and identify incorrect, ambiguous, duplicate, or weakly scorable requirements.
- Survey adjacent optics, physics, scientific-agent, tool-use, and executable-evaluation projects; record verified facts and recommendations separately.
- Propose scope, structured case/answer contract, autonomous scorers, case validation, split strategy, and evaluation metadata.
- Initialize local Git and work on `research/benchmark-foundation`. Draft a README. Do not publish a repository merely because GitHub authentication works.

## Next three implementation rounds

### Round 1 — vertical slice and scientific correction

Select a *small, diverse* subset of existing cases: at least one numeric, one open design, one diagnostic/calibration, and one impossibility/trade-off case. Correct identified physics or wording defects in **new versioned sources**, with the original HTML retained as provenance. Agree on coordinate, units, tolerance, and underdetermination conventions. Implement a minimal case schema, answer validator, two independent physics checkers, a constraint-graph validator, and fixtures including an alternative valid topology and an adversarial invalid answer. Render clean HTML/Markdown questions from canonical data, without exposing gold in the question bank. A vertical slice passes only when it scores with no human intervention.

### Round 2 — seed migration and oracle hardening

Migrate the 64 seed cases individually into canonical data while preserving lineage and recording repairs. Do **not** assume all 64 should enter the scored release: quarantine or revise cases whose observables, assumptions, or graders are inadequate. Run static lint, independent derivations, numerical/symbolic checks, adversarial mutations, and semantic-judge calibration. Add concept-family grouping to prevent sibling leakage. Produce an automated coverage report by domain, task type, difficulty, and scoring layer. Freeze a public development set and a candidate public scored set.

### Round 3 — evaluation harness and pilot baselines

Build a model/agent adapter interface, protocol manifests for closed-book and assisted modes, isolated gold/validator execution, trace capture, cost/token/tool accounting, and reproducible result bundles. Run initial automated baselines as soon as the vertical slice is stable, then rerun on the larger candidate set; include at least a simple direct model, an autonomous agent, and a tool-enabled condition under matched budgets where feasible. Report per-criterion scores, failures, judge instability, and paired protocol differences, not only an aggregate. Use pilots to revise empirical difficulty and identify oracle false positives/negatives. Do not use test results to tune a hidden set after its release.

## Minimum credible v0.1 release

v0.1 should have a validated, nontrivial scored subset spanning several optical domains and task operations; an immutable manifest; canonical cases; an answer contract; functioning autonomous graders; adversarial fixtures; a generated clean question view; documented limitations; reproducible baseline runs; and a machine-readable result format. Every included case must reach `release_verified` status. A smaller robust set is preferable to nominally including all 64 with unreliable grading. The full 64-case migration can remain visible as development material with explicit statuses.

Before GitHub publication, decide a distinctive name after another collision search, choose a license compatible with the seed's provenance, confirm rights to publish it, and publish the research limitations clearly. **Do not use `OpticsBench`**: that name already denotes an [optical-aberration robustness benchmark](https://arxiv.org/abs/2308.15499) and an [optical ray-tracing product](https://opticsbench.com/). `FSO` alone is ambiguous with free-space optical communications. A descriptive working title, “Free-Space Optical Experiment Reasoning Benchmark,” can remain provisional; the repository slug should be chosen after the architecture and licensing decisions. GitHub publication is recommended after Round 1's executable slice and these decisions, with v0.1 release after Round 3. GitHub can host an early research repository, but it should not imply benchmark readiness.

An initial GitHub repository-name search on 28 September 2026 returned no exact repository matches for `FreeSpaceOpticalExperimentBench`, `OpticalExperimentReasoningBench`, or `OpticalAgentBench`; these are **candidates**, not reserved names or evidence that a broader project name is unused. An `OpticsBench` search returned several repositories, consistent with the published naming collisions above. Recheck names, domains, trademarks, and the scientific fit immediately before publication. The longer descriptive candidates communicate scope more clearly than `OpticalAgentBench`, which could also describe device control or integrated photonics.

## Later ambitions

- Private seeded instances and externally run hidden evaluations, while publishing generator logic and distributional rules; ensure private seeds and gold never enter the public repository.
- Structural and compositional variants that preserve laboratory plausibility, plus empirical tests for contamination and overfitting.
- Versioned optical case library and paired case-assisted ablations to test whether retrieval improves weaker or cheaper agents at fixed budgets.
- More independent simulations, uncertainty models, realistic component constraints, and feedback-driven experimental-control tasks, only when the verifier can establish validity autonomously.
- Community submissions of cases and validators, with automated challenge suites and optional expert audit of the benchmark itself.

## Decision gates

| Decision | Evidence required |
| --- | --- |
| Promote a case | All scored criteria have autonomous oracles; alternative solutions and adversarial wrong answers tested. |
| Set a difficulty label | Predeclared complexity features plus pilot success data. |
| Add model judging | Criterion-level calibration meets a published error/stability threshold; physical contradictions remain executable gates. |
| Create hidden split | Secure storage/run service and concept-family isolation exist. |
| Publish repository | Name/license/provenance and executable vertical slice are defensible. |
| Publish v0.1 results | Frozen manifest, baseline configurations, raw usage accounting, limitations, and replayable scoring evidence exist. |
