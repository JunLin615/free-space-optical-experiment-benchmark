# Migration of the original 64-case seed

The preserved Chinese HTML contains 64 cases, numbered `1.1` through `8.8`. Before this round, 11 had canonical English YAML records. This round adds the 53 records listed below, so each seed case now has one English canonical file. The original HTML remains unchanged, with SHA-256 `077DB14D2A5C67A3123C82AF1D571F8FFA73D3C79501C7C9D8C99E021C2318A8`. Each new file records its legacy ID, source hash, seed relationship, revision, and a derivation note. `python tools/check_corpus.py` verifies the one-to-one lineage in CI.

| Seed section | Newly migrated legacy IDs | Count |
| --- | --- | ---: |
| 1 — beam geometry and components | 1.2, 1.3, 1.4, 1.8 | 4 |
| 2 — Gaussian beams | 2.2, 2.3, 2.4, 2.5, 2.6, 2.7 | 6 |
| 3 — imaging and Fourier optics | 3.1, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8 | 7 |
| 4 — polarization and interference | 4.1, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8 | 7 |
| 5 — weak-signal detection | 5.1, 5.2, 5.4, 5.5, 5.6, 5.7, 5.8 | 7 |
| 6 — integrated experimental systems | 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8 | 8 |
| 7 — diagnosis and physical boundaries | 7.1, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8 | 7 |
| 8 — open design | 8.1, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8 | 7 |
| **Total** | **53 individual records** | **53** |

The previously present records remain `1.1`, `1.5`, `1.6`, `1.7`, `2.1`, `2.8`, `3.2`, `4.2`, `5.3`, `7.2`, and `8.2`. Their identities and source lineage were retained. All 64 render into the English question bank; gold and evaluator metadata remain outside the public view.

## Scientific normalization

Material clarifications are recorded in the corresponding `provenance.derivation` fields. The main changes are:

| Case | Clarification and reason |
| --- | --- |
| 1.2, 1.4 | Alignment is iterative and depends on reachable mirror geometry; proving output parallelism needs a reference tied to the input axis, not arbitrary downstream apertures. |
| 2.3, 2.4 | Damage and nonlinear limits depend on pulse and component data; Gaussian waist/Rayleigh scaling assumes a stated, fixed beam quality. |
| 2.7 | A centered 4 mm Gaussian radius through a 5 mm radius aperture loses about 4.4% ideally. A stated 1% geometric-loss sizing target yields about 6.1 mm minimum radius, before diffraction and alignment margins. |
| 3.3, 3.5 | A Fourier-plane central stop suppresses low spatial frequencies but does not prescribe one exact coherent image; slit throughput and resolution do not obey a universal fourfold rule without an instrument model. |
| 4.3, 4.5, 4.7, 4.8 | Interferometer noise and white-light visibility depend on path and bandwidth assumptions; a cavity reflection dip alone does not certify mode overlap; balanced polarization readout needs an equal-power operating point and gain calibration. |
| 5.7 | At fixed bandwidth, absolute shot-noise current grows as the square root of power while fractional noise falls as its inverse square root. A fractional-noise plateau needs another limiting mechanism. |
| 6.2 | The full −2 to +500 ps interval spans 502 ps. A double-pass folded stage needs about 75.25 mm of mechanical scan before margin; detector bandwidth is distinct from optical cross-correlation resolution. |
| 7.1, 7.4, 7.8 | Two aperture centers always define a line; the actual fault may be a wrong reference axis or unreachable path. Expander magnification needs propagation-aware measurement. Gaussian focus and depth-of-focus scaling state the width and beam-quality conventions. |
| 8.1, 8.3, 8.6 | A `10^-4` transmission target needs a drift/noise/linearity argument and genuinely distinct alternatives. Polarimetric inversion requires a stated sample model and treatment of degeneracy. Wavelength routing uses a measurable leakage or isolation requirement in place of impossible literal complete separation. |

Other migrated cases retain open architectures and describe accepted physical families as examples. A novel valid layout must not fail merely because its name is absent from a list. The canonical records state proposed criteria, but no new record is promoted simply by being translated.

## Remaining limits

No case was quarantined during migration. Most new records are `specified`: their answer contracts and scoring plans need executable validators, valid-alternative challenges, and adversarial fixtures before status promotion. Open designs in sections 6–8 need particularly careful validation of causal predictions, system sensitivity, and calibrated residual semantic judging. The source lacks numerical tolerances, bandwidths, detector specifications, and apparatus limits for many engineering tasks; the case files call out these missing inputs or ask the solver to state assumptions instead of inventing fixed vendor-specific constraints.

The existing schema version remains `0.1.0`; no structural change was needed to represent the complete seed. Validation now also checks the complete legacy-ID set, unchanged seed hash, case-specific lineage, revision notes, and question-ID format. The [coverage report](coverage_report.md) and [scoring-readiness plan](scoring_readiness.md) give the per-case classification and future oracle priorities. Chinese localization and a hidden evaluation split remain future work after English review; neither is part of this migration.
