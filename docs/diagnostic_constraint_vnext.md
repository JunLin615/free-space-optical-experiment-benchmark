# Versioned diagnostic and routing development scorers

This wave adds development contracts for `SEED-7-1` and `SEED-8-6` under `benchmark/cases_vnext/`. Their public scientific questions are unchanged. The original canonical cases and rc1 release bytes remain intact. These cases remain `specified`; neither is promoted to `release_verified` by this wave.

## Two-aperture alignment (`SEED-7-1`)

The scorer counts distinct fault mechanisms, each linked to a physical process, a discriminating test, and a predicted observation. It distinguishes a recoverable near/far mirror-iteration procedure from reference geometry, mirror reach, obstruction, source-height, and stability limits. Merely repeating synonyms of one fault cannot meet the four-cause requirement. The reference-axis check is deliberate: two arbitrary aperture centers always define a line, so two-point "non-collinearity" alone is not a diagnosis.

The sequence check accepts different noninvasive checks for physical reach, then asks for controlled near/far convergence. A test must state contrasting outcomes and typed cause conclusions. Unknown credible processes and methods abstain (`unresolved`). The supported fault registry is bounded and is not a claim that it exhausts optical alignment failures.

## Dual-wavelength routing (`SEED-8-6`)

The routing scorer checks a passive two-source/two-detector power-fraction matrix with a finite leakage requirement. Each wavelength must be dominant in its assigned detector, and total output fractions cannot exceed input. Separate-source centroid measurements at two distinct planes establish both position and direction; the derived angular difference uses millimetres per metre, numerically milliradians. Four distinct wavelength-dependent properties need matched tests. A dark-corrected one-source-at-a-time leakage measurement must satisfy both directions of the declared limit.

The fixtures include dichroic and dispersive terminal separation, as well as a dispersive recombiner alternative. These are distinct optical methods, not just different labels for the same arithmetic. A plausible unfamiliar method or property yields `unresolved` after the executable constraints. Literal perfect extinction, energy creation, one-plane collinearity claims, wrong-channel routing, and excess leakage fail.

## Qualification limits

Both contracts are typed and deliberately bounded. They do not infer physics from free-form prose, verify that a proposed instrument really realizes its claimed routing matrix, or calibrate arbitrary novel architectures. A release decision requires independent scientific review, a broader challenge corpus, and integration with the versioned evaluator. No semantic judge or human expert is needed to run these development scorers, but an `unresolved` result is not a pass.
