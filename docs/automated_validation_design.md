# Automated validation of benchmark cases

Status: proposal, 2026-09-28. The purpose is to validate the *case and its oracle* before release. This is distinct from scoring an agent's answer. Human inspection can improve a release, but no mandatory expert-review gate or manual per-run decision is part of the architecture.

## Validation unit and invariants

Each versioned case package contains a prompt, assumptions, required answer contract, private gold specification, validator implementation, positive/negative solution fixtures, provenance, and a versioned generation recipe if it has variants. A case is eligible for scored release only when all scored criteria have a working automated oracle. Each package is tested for:

- **Well-posedness:** values, units, coordinate conventions, allowable approximations, missing information, and observables are explicit. If the physically correct response is “insufficient information,” that is encoded as an answer class with required missing variables and a discriminating measurement.
- **Solvability and alternatives:** at least one independently constructed answer passes; deliberately different physically valid designs pass where applicable. An impossibility question has a checked invariant or counterexample search.
- **Discrimination:** plausible wrong answers fail for the intended reason, including sign/unit mistakes, swapped paths, incorrect conjugates, incorrect polarization basis, spurious numerical precision, and omitted dump/calibration paths.
- **Stability:** small numerical perturbations within an allowed input region do not flip the oracle unexpectedly; boundary behavior and tolerances are explicit.
- **Leakage control:** prompt and retrieval corpus do not expose gold, and concept-related variants do not cross a public/private split.
- **Reproducibility:** fixed seeds and validator versions reproduce instances and verdicts.

## Validation passes

1. **Static lint.** Schema and ID uniqueness; required fields; SI units; criterion weights; answer-field references; provenance URL syntax; split lineage; forbidden secrets in public artifacts; no unsupported validator IDs.
2. **Independent derivation.** Generate at least two solution attempts using different prompts and, when practical, different model families or symbolic tools. Compare *structured claims* rather than prose agreement. Disagreement creates a case defect ticket automatically. Agreement is evidence, not proof.
3. **Executable cross-check.** Check equations with symbolic algebra, dimensional analysis, high-precision numerical evaluation, and an independently implemented physical model. Example: delay-line factors via optical path geometry and `Δt=ΔL/c`; Gaussian propagation via both q-parameter and ABCD form; polarization via Jones matrices and selected Stokes invariants. Verify reference uncertainty and tolerances over sampled parameter regions.
4. **Simulation/fixture tests.** Validate at least one passing solution and multiple failing solutions. For design graphs, mutate or remove a component, reroute a wavelength, invert a polarization axis, perturb a focal length, or break calibration. The resulting failure should map to the expected criterion. Test alternative valid graphs, not only mutations of a single reference topology.
5. **Adversarial challenge.** Ask automated solvers to find a valid answer that the oracle rejects or an invalid answer that it accepts. Use property-based generation of parameter edge cases and graph rewrites. Found counterexamples become regression fixtures. This step explicitly probes topology lock-in and judge susceptibility to polished but physically false prose.
6. **Judge audit.** For semantic criteria, evaluate graders on a machine-maintained challenge set with known labels derived from physics fixtures and contradiction injections. Measure false-pass, false-fail, abstention, and order sensitivity. A grader change reruns the challenge set and increments judge version.
7. **Release preflight.** Run the entire case bundle under the exact published manifest. Record validator test results, derivation disagreement, counterexamples resolved, and hashes. No case silently changes after release.

These passes are design recommendations. The use of programmatic verification in [ScienceAgentBench](https://github.com/OSU-NLP-Group/ScienceAgentBench) and the scoring separation in [Inspect AI](https://inspect.aisi.org.uk/scoring.html) motivate the approach; neither source proves an optical oracle correct. In this project, confidence must come from independent physics checks and adversarial fixtures.

## Status model

| Status | Meaning | Eligible for scored release? |
| --- | --- | --- |
| `seed` | Imported prompt and human-written gold notes; no validated contract | No |
| `specified` | Prompt, assumptions, answer contract, criteria, and oracle plan exist | No |
| `executable` | Oracle runs and positive/negative fixtures pass | No |
| `challenged` | Independent derivation and adversarial checks completed; discrepancies resolved | Candidate |
| `release_verified` | All mandatory gates pass under pinned versions; evidence bundle archived | Yes |
| `quarantined` | Contradiction, ambiguity, validator defect, or judge instability found | No, until repaired and reversioned |

Status is based on evidence, not a model's confidence score. A critical unresolved physical contradiction or false pass blocks promotion regardless of aggregate agreement. If a criterion needs an unreliable model judge, redesign its requested output or move it to a clearly labeled, unscored exploratory field. The case can remain in the development set while its scoring is repaired. The released benchmark must never depend on a human to resolve a tie during ordinary operation.

## Automated disagreement routing

Use typed discrepancy codes: `missing_assumption`, `reference_disagreement`, `unit_or_sign`, `oracle_false_pass`, `oracle_false_fail`, `topology_exclusion`, `judge_instability`, `generator_invalid_region`, and `provenance_conflict`. Each code points to a repair path, such as narrowing parameter bounds, replacing a prose criterion with an observable, adding an alternative solution family, or revising the physics model. Stop promotion until the automated challenge suite passes. Optional human audit can review the evidence after the fact, but cannot be the routine mechanism that makes an otherwise unscorable case usable.

## Release and versioning rule

An immutable benchmark release pins prompt text, gold specification, case/generator versions, validator source and environment, and judge configuration. Fixing a scientifically incorrect question or changing a score threshold creates a new case revision and benchmark release, with a migration note and old results preserved. Editorial changes that cannot affect scoring still create a content hash change and require a comparability check. Maintain a changelog of additions, quarantines, and score-affecting changes.
