# v0.2.0 stable release notes

Status: prepared for integrator review and tagging. This document does not claim that a tag or GitHub release has already been published.

## Scientific scope

The stable release qualifies **nine** autonomous-scoring cases across nine concept families. The remaining 55 canonical English cases stay visible with their actual development or verification status. The public English and `zh-CN` question-bank views map to the same 64 case identities and shared scientific data. Normal scoring uses executable, unit-aware and structured constraints without human adjudication.

The release keeps four matched evaluation protocols, the separately versioned example library, public development variants, a provider-neutral runner, and the family-disjoint hidden-evaluation policy. These components do not add new scored cases to `0.2.0`.

## `SEED-3-1` stable correction

The frozen `0.2.0-rc1` campaign exposed a repeated answer-contract ambiguity: a physically correct image distance of `2 f` was encoded with unit `f`, while the rc1 field accepted only the dimensionless ratio with unit `1`. The stable release advances `SEED-3-1` to a new versioned case and narrowly scoped evaluator that accepts both unambiguous representations and rejects wrong values or dimensions. The change has positive, equivalent, boundary, malformed, adversarial, and cross-version regression evidence. [Issue #14](https://github.com/JunLin615/free-space-optical-experiment-benchmark/issues/14) records the finding.

The [`0.2.0-rc1` campaign](results/2026-09-28-multimodel-020rc1.md), its 108 formal public records, public variants, hidden attestations, raw responses, scores, and failure modes retain their original bytes and interpretation. A future model baseline against stable `0.2.0` would be a new experiment.

## Reproducibility and boundaries

The stable manifest pins exact case revisions and content, evaluator versions/fingerprints, fixtures, independent tests, schemas, environment, qualification logic, and required evidence. The pinned CPython 3.11.16 package environment is reused where exact. Separate qualification commands verify `0.1.0-rc1`, `0.2.0-rc1`, and `0.2.0`. An independent frozen-history check commits to the two rc manifests, their environment snapshot, original Chinese seed, and campaign index; the campaign analyzer checks every indexed public run tree and public hidden attestation.

Nine verified cases permit descriptive paired comparisons. They do not support broad model rankings. Open-ended designs and diagnoses remain research material under [Issue #3](https://github.com/JunLin615/free-space-optical-experiment-benchmark/issues/3); further qualified scoring needs independent challenges and, where appropriate, calibration evidence. No OpenSci integration, vendor optical software, paid rerun, or human grading path is part of this release.
