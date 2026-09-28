# `0.2.0-rc1`: broader verified optics families

`0.2.0-rc1` is a technical release candidate, not a leaderboard or a new
measured model baseline. It contains nine release-verified cases in nine
distinct concept families. Five inherit their unchanged rc1 case bytes;
four use versioned case revisions under `benchmark/cases_vnext/`. The
original `0.1.0-rc1` manifest, scorer interpretation, and all historical
baseline artifacts remain fixed.

## Changes from rc1

| Case | Family | Release decision | Scientific contract |
| --- | --- | --- | --- |
| SEED-2-1 | Gaussian focus | Newly verified, revision 0.3.0 | q1 asks for a numerical waist to one significant figure; q2 separately asks for the nearest offered order scale. The 20% q1 reporting tolerance admits 20 µm near the 16.93 µm reference but rejects a mere 10 µm decade label for the canonical givens. |
| SEED-3-1 | Thin-lens conjugates | Newly verified, revision 0.3.0 | Numerical image distance and signed magnification retain the paraxial equation; neutral image type and orientation enums cover the conceptual task. |
| SEED-3-7 | Diffraction resolution | Newly verified, revision 0.3.0 | Rayleigh's 0.61 λ/NA convention and fixed-wavelength depth trend are scored separately. |
| SEED-5-5 | Heterodyne detection | Newly verified, revision 0.3.0 | Beat frequency, square-law interference origin, and no-projector orthogonal limit use neutral typed fields. |

SEED-1-1, SEED-1-5, SEED-1-7, SEED-2-2, and SEED-4-2 are inherited rc1
cases. All nine are rechecked by the versioned vNext runtime and pinned in
[`0.2.0-rc1.json`](../benchmark/releases/0.2.0-rc1.json). The manifest pins
case bytes, scorer/evaluator fingerprints, schema, exact Python environment,
fixture challenges, independent test evidence, variant generator, and hidden
policy tooling. [`qualification_report_vnext.md`](qualification_report_vnext.md)
summarizes the 120 release fixtures, zero unresolved release fixtures, and
zero mandatory semantic judges. The old rc1 qualification remains a separate
required check.

The vNext evaluator adds a finite, explicit [unit normalization](unit_contract_vnext.md)
table. It accepts standard equivalent spellings such as `dimensionless` for
`1`, but does not repair a wrong physical dimension or a malformed claim.
The three affected SEED-2-2 historical answers would score 1.00 under this
new evaluator; their recorded rc1 scores remain 0.65. This is a labeled
retrospective interpretation, not a rewrite or a new model run.

## Variants and hidden evaluation

Four newly verified families have bounded, deterministic parameter and unit
representation generators: Gaussian focus, thin-lens conjugates, diffraction
resolution, and heterodyne detection. Generation recomputes gold from typed
givens, checks nondegenerate ranges, verifies the new scorer, and records
release compatibility. These four hidden-eligible families are disjoint from
the five families behind the ten committed rc1 public-development variants.
The first external private bundle has eight instances across four families.
Its prepared mock runner run completed and audited all eight, with no model
API or private data committed. A separate one-instance `gpt-6-luna` real smoke
run completed and linked to the same private bundle; the observed score was
1.0, with no cost estimate. It is an infrastructure probe, not a broad model
comparison. See [hidden evaluation](hidden_evaluation.md).

All 64 canonical questions remain public. A private variant is therefore
resistant to exact-instance memorization and obvious public-variant sibling
leakage, not contamination-proof. The public family map and checker enforce
the stated split; the exact private choices and seed stay external.
The inherited SEED-2-2 typed field names still encode its architecture-specific
focus claim. That rc1 answer-contract weakness is documented and the family is
excluded from hidden generation; changing the inherited contract would require
a separate versioned case and scorer challenge.

## Development cases and limits

SEED-2-4 remains unverified: its application-specific disadvantage question
admits plausible tradeoffs beyond the bounded typed vocabulary. Prospective
structured scorers cover SEED-1-4, 3-2, 3-3, 7-5, and 7-6, but arbitrary
valid optical layouts or representations are not yet proved by their typed
oracles. SEED-7-6 additionally needs a tighter single-mode scope. Versioned
diagnostic/constraint scorers for SEED-7-1 and 8-6 test causal discrimination,
alternative architectures, observability, and hard physics failures; novel
plausible methods abstain and neither case is release verified. Other cases
retain the exact blockers in the rc1 [qualification report](qualification_report.md)
and [vNext readiness inventory](scoring_readiness_vnext.md).

No normal release score requires human adjudication or a live semantic judge.
Development diagnostics and hidden dry-run outcomes are reported separately
from the nine release-verified scores. No broad model comparison or public
ranking was run.
