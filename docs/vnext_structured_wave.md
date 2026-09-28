# Prospective bounded structured optics checks

`tools/scorers/structured_vnext.py` is a post-rc1 development oracle. It is not
registered in the frozen rc1 evaluator, and no case or release status is
promoted by this change. `tests/test_structured_vnext.py` supplies positive,
alternative-valid, negative, boundary, and adversarial typed-answer fixtures
for each of the five cases below. The shared pilot-answer JSON schema validates
these fixtures. Unknown representations abstain; absent typed claims fail only
their own criterion. The scorer reads the case ID and, for the periscope, the
authored heights. It reads no vendor, tool, adapter, or framework identifiers.

| Case | Scored public tasks covered by typed checks | Remaining boundary |
| --- | --- | --- |
| SEED-1-4 | q1 two reflections, lift, forward-parallel output; q2 possible geometric/polarization change; q3 calibrated two-plane or independent angular test | A declared topology is not a ray trace of arbitrary mirror poses. Other valid parallelism metrology abstains. |
| SEED-3-2 | q1 positive equal-focal-length 4f distances in convertible length units; q2 shared focal stop; q3 spatial-frequency rather than ordinary-image interpretation | Equivalent relay architectures and aberration/finite-aperture performance are outside this bounded oracle. |
| SEED-3-3 | q1 conditional broad-structure/edge effect; q2 high-pass-like class; q3 Fourier-plane rejection mechanism | It does not infer the appearance of a particular coherent image, stop size, ringing, or phase-dependent sign. |
| SEED-7-5 | q1 rejects full-range claim; q2 ideal half-wave helicity reversal and half-power linear-analyzer output; q3 either quarter-wave linearization followed by rotatable half-wave plate and fixed analyzer, or a rotatable quarter-wave plate with fixed analyzer | Other polarization converters and nonideal retardance/input purity abstain. |
| SEED-7-6 | q1 rejects ideal passive lossless single-mode purification; q2 rank/two-component constraint; q3 ideal polarizer or selected PBS port and half-power discard | Temporal, spectral, or ancillary-mode conversions need an explicit task-scope decision before promotion. |

The q1 `SEED-3-2` fixture uses one possible focal length; the oracle evaluates
the relations between supplied lengths, not that particular value. In
`SEED-7-5`, the half-power result assumes pure circular input, an ideal
lossless plate, and a fixed ideal linear analyzer. In `SEED-7-6`, the rank
argument concerns ordinary passive linear polarization optics acting on a
single output mode. These assumptions come from the public case text and gold
constraints; the fixture vocabulary is one typed representation of them.

This is development evidence for **five executable candidates**, not a claim
of release verification. Before promoting any candidate, register a versioned
runtime path, independently review the physical assumptions and public task
wording, pin evaluator and case fingerprints, and run the release qualification
suite. `SEED-7-6` in particular should remain specified until the permissible
output mode definition is tightened or the scope is explicitly accepted.
