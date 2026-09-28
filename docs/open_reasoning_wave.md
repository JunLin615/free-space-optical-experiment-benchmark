# Open reasoning development wave

This branch advances Issue #3 with three **development-only** case revisions. The
question text in each case remains the same as its English canonical source. The
new typed contracts and scorer live outside the frozen `0.1.0-rc1` and
`0.2.0-rc1` evaluators. `tools/dev_scoring.py` registers only these development
revisions and returns criterion verdicts without claiming a release aggregate.

| Case | Reasoning pattern | Executable evidence | Known limit |
| --- | --- | --- | --- |
| SEED-8-1 | Constraint-based weak-absorption design | Free-space sample observable, drift control faster than source drift, detector current below linear limit, declared measured fractional floor below `10^-4`, blank/dark/linearity/known-step checks, and three physically distinct complete implementations | Typed numbers and check flags are declarations, not proof that an instrument achieved precision. A novel architecture abstains. |
| SEED-5-7 | Causal noise diagnosis | Distinct plateau causes with matching controls; ideal shot-noise absolute `P^0.5` and fractional `P^-0.5` scaling; multiple high-power limits | The bounded registry does not exhaust thermal, electronic, or sample processes. New credible causes abstain. |
| SEED-2-8 | Passive invariant and impossibility | Existing beam-product invariant verdict plus two explicit reciprocal same-beam ratio scenarios, each requiring size ratio times divergence ratio at least one | Novel phase-space formulations abstain. This contract does not analyze lossy spatial filtering, active devices, or different source modes. |

The 30 committed fixtures include conventional and alternative valid approaches,
polished invalid claims, missing controls, duplicated architecture or cause
families, hard physical contradictions, and unfamiliar plausible representations.
The design alternatives are (1) simultaneous sample/reference detection, (2)
sample-state modulation with synchronous comparison, and (3) independently
monitored active source stabilization with sequential readings. Ratio and
balanced difference on the same split-beam layout count as one family. The noise
diagnoses distinguish residual source intensity noise, gain imbalance, detector
nonlinearity, and bandwidth change. The invariant tests accept both beam-parameter
product and étendue terminology.

The scorer uses no model judge, external optics package, vendor identifier, or
human at evaluation time. It reports `unresolved` when a plausible method falls
outside the bounded contract. This prevents a new topology or causal process
from being counted as physically wrong merely because it is not registered.
Absence of a required typed claim is a criterion-local failure. A polished
explanation never overrides a contradictory numeric or functional claim.

All three cases remain `specified`. They are not release verified because
asserted detector noise floors are not measured evidence, the fixtures cannot
cover arbitrary complete architectures or plateau mechanisms, and no bounded
semantic judge has been calibrated for remaining free-form reasoning. A future
wave should challenge the contracts with independent optical designs and real
measurement data before any promotion decision.
