# Autonomous scoring runtime (development slice)

The registered slice covers `SEED-1-1`, `SEED-1-5`, `SEED-2-8`, `SEED-5-3`, and `SEED-7-2`. It scores submitted JSON; it does not execute a candidate model. `python tools/evaluate_answer.py --case SEED-1-5 --show-contract` prints the case-local answer contract. `--answer response.json --output result.json` produces a result-schema record and a short summary on stderr. Ordinary wrong answers exit 0; invalid case or evaluator/oracle failure exits 2. `python tools/run_case_fixtures.py` runs the regression challenge set.

Reproducible local example: `python tools/evaluate_answer.py --case SEED-1-5 --answer examples/SEED-1-5-answer.json --output result.json`. The example is a known correct answer, so its aggregate is `1.0`. The output records unknown model execution usage as `null`, not as measured zero.

`SEED-1-1` and `SEED-1-5` reach `challenged` with independent geometry/path constructions and boundary, alternative-unit, and adversarial fixtures. `SEED-2-8`, `SEED-5-3`, and `SEED-7-2` remain `specified`: the typed checks handle declared fields but do not certify arbitrary equivalent prose or experimental sensitivity. The diagnostic contract currently points to scorer source for some code values, which is acceptable only for this development interface. None of the five is `release_verified`.

The numeric prompts do not specify mirror-rotation or stage-motion sense. Their requested direction/path/time *changes* are therefore scored as magnitudes; signed reports in the opposite coordinate convention pass when their absolute value is correct. Mechanical travel remains nonnegative. The case files record this convention and the preexisting inclusive tolerances with rationale.

## Pipeline

1. Load canonical YAML and validate the case schema and cross-field invariants. A corrupt case or authored gold is an evaluator failure; its aggregate score is `null`.
2. Parse JSON and validate the shared `pilot_answer_v0.1` envelope. Invalid JSON or a malformed envelope produces `invalid_contract` and score zero. Case-specific required paths and typed shapes are disclosed in each case's `answer_contract`.
3. Dispatch to the registered evaluator-owned scorer. Numerical checks derive expected values from prompt givens in SI units and compare authored gold independently before the candidate. Structural checks inspect typed functions, mechanisms, observables, and controlled tests. Unknown plausible alternatives are `unresolved`; they are not silently scored false.
4. Preserve every criterion verdict, evidence, failure class, and scorer version in `validator_results` and `criterion_scores`. An external runner may pass `judge_criteria` and `judge_backend` to `evaluate_case` for a residual, non-numeric criterion. The bounded judge sees one criterion, and its separate verdict is recorded in `judge_results`; it cannot override a deterministic or hard-constraint failure. No live judge is required by this slice, and a mock judge response is not calibration evidence.
5. Sum criterion weights only when all criteria resolve. A failed hard constraint caps the aggregate at `0.49`, preserving partial-credit evidence while preventing a passing aggregate. Any unresolved criterion leaves both aggregate totals `null`. This cap is an interim development policy, not a released benchmark threshold.
6. Validate the generated record against `result.schema.json`. The record includes case-content SHA-256, evaluator version, and a fingerprint of runtime/scorer/judge source files. The scorer accepts model identity, protocol, tool availability/use and invocation count, token counts, provider usage, cost with pricing provenance, wall time, and retry count. Unknown measurements remain `null`; measured zero remains zero.

## Failure classes

`wrong_value`, `wrong_unit`, `missing_claim`, and `malformed_answer` describe candidate faults in criterion details. `validator_error` means oracle code or authored gold failed; `invalid_instance` means the case itself failed structural or consistency checks. Neither may be counted as a candidate failure. `oracle_unresolved` means a supported scoring path cannot settle one or more claims; it produces a null aggregate. `invalid_contract` covers parse/envelope failures and required structured claims that are absent or dimensionally invalid. The result record also preserves the raw candidate answer for audit.

## Scope of evidence

The public fixtures are interface and adversarial regression evidence, not contamination-resistant model evaluation. A typed field that merely asserts a physical property is weaker evidence than a measurement or executable topology; open-design and diagnostic cases remain below `release_verified` until challenge coverage and any semantic calibration meet the gates in [release verification](release_verification.md). No per-run expert review is part of normal scoring.
