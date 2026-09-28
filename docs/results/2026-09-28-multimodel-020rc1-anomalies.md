# Frozen-campaign anomalies and classification

These observations leave all `0.2.0-rc1` case bytes, scoring semantics, fixtures, and raw run evidence unchanged. No model answer was repaired or rescored.

## Repeated `SEED-3-1` structured-unit failure

Luna in all four protocols and Sol in `closed_book` returned the numerically and physically correct image location as `{"value": 2, "unit": "f"}` for `answers.q1.image_distance_in_focal_lengths`. The frozen contract expects the dimensionless ratio `{"value": 2, "unit": "1"}`. The task wording says “express its distance behind the lens in units of f,” which plausibly invites `2 f`; the typed field name and gold instead mean “number of focal lengths.” Each affected record scored 0.6 with `invalid_contract`, while the image-type and magnification fields were correct. Astra used `unit: "1"` and scored 1.0. This is a reproducible contract-interpretation ambiguity, not evidence that the thin-lens physics was wrong. [Issue #14](https://github.com/JunLin615/free-space-optical-experiment-benchmark/issues/14) tracks a future-release clarification and fixtures. The frozen campaign retains the original outcomes.

## Runner source-revision metadata discrepancy

For the `0.2.0-rc1` public runs, `environment.json` and individual result records record the same Git commit (`caebd4b`) but different source-digest suffixes. The environment capture uses release-aware source hashing, while the result-record path uses the runner's default release in `_source_revision()`. For example, the Luna formal run reports environment suffix `e71b8ce2...` and record suffix `7ef29715...`. The immutable manifest and evidence-tree hashes still bind the actual files, and the frozen evaluator fingerprints match the release pins. This is a provenance-metadata inconsistency; it is not a score discrepancy. A later runner version can align these fields without rewriting this campaign.

## Public development variant contract failure

Astra's `SEED-2-2` public variant received 0.65 under the older `0.1.0-rc1` parent release. The parsed expansion factor used the textual unit `dimensionless`, while that frozen typed contract expects its canonical unit symbol. It is recorded as an invalid-contract outcome in the variant probe. The other four Astra variants and all five Luna and Sol variants achieved full success. Because this probe is development evidence on a different parent release, it is not included in the formal `0.2.0-rc1` aggregate.
