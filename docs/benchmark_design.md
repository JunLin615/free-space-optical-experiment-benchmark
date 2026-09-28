# Benchmark design proposal

Status: research proposal, 2026-09-28. This document defines scientific and protocol boundaries; it does not change the 64 seed questions. The current seed is an input to be audited, not an automatically accepted release.

## Purpose and scientific scope

Evaluate autonomous systems on **free-space optical experimental reasoning**: predict observable behavior, design a physically workable beam path, diagnose a fault, choose measurements, and make defensible engineering trade-offs. The benchmark must be independent of OpenSci, any agent framework, and any optical-design package. A valid solution may use pencil-and-paper reasoning, code, retrieval, optical software, or simulation according to the declared protocol.

Core cases require a meaningful free-space beam path and experimental context. Purely guided-wave, on-chip, and fiber-only photonics are outside the core; a fiber launcher or detector may be a boundary component in an otherwise free-space experiment. Include geometrical optics, Gaussian beams, imaging/Fourier optics, polarization, interference, spectroscopy and wavelength routing, ultrafast timing, alignment, diagnostics, calibration, and laboratory constraints. A proposed task must state assumptions, observables, and conditions under which its answer can be tested. Safety claims should be specific to the physical mechanism and given parameters.

## Taxonomy, with orthogonal labels

| Axis | Proposed values | Rule |
| --- | --- | --- |
| Optical domain | geometry/alignment; Gaussian propagation; imaging/Fourier; polarization; interference/coherence; wavelength routing/spectroscopy; ultrafast/time; detection/metrology; multi-domain | Multi-label where necessary; choose one primary domain for stratification. |
| Task operation | predict/compute; design/synthesize; diagnose; calibrate/verify; critique/impossibility; optimize/trade off | Label each subtask, not merely the whole prompt. |
| Evidence mode | numeric; symbolic; path/state graph; executable artifact; observable/measurement plan; semantic claim | A case can require several modes. |
| Interaction | one-shot; iterative tool use; feedback-driven recovery | Do not infer this from case difficulty. |
| Source | seed-derived; new authored; parameterized variant; structural variant | Preserve lineage and prevent split leakage. |

The seed's three-level difficulty tags are useful orientation, but difficulty should ultimately be empirical. Provisional tiers: **D1** single-principle direct application with supplied parameters; **D2** multi-step reasoning or a standard arrangement with checks; **D3** coupled constraints, competing failure modes, or quantitative design; **D4** genuinely underdetermined or high-dimensional synthesis with adversarial alternatives. Record prerequisite concepts, number of coupled constraints, uncertainty, and baseline success alongside the tier. Recalibrate tiers after pilot runs; avoid treating length or vocabulary as difficulty.

## Task eligibility and answer contract

Every scored subtask must have an observable target and an autonomous oracle. The oracle may be deterministic calculation, a typed optical graph plus constraints, independent simulation, or a calibrated model judge for bounded semantic criteria. A broad prompt such as “propose a good setup” is ineligible until its requirements, admissible design space, and checks are specified. Alternative topologies must be accepted by **behavior** (node states, transfer relations, observables, hard constraints), with named topology families serving only as test fixtures and not an exhaustive whitelist.

The recommended response has (1) a concise human-readable answer and (2) a typed result object containing only case-requested fields. It is a *claim interface*, not a forced reasoning style. Numeric values carry units and uncertainty/tolerance where appropriate; beam paths use typed nodes and edges; diagnostics provide hypothesis, discriminating test, expected outcomes, and corrective action. An agent may report multiple valid designs, but one declared primary design is scored. To keep the protocol fair to text-only models, a separate **text-extraction track** may parse prose into the same contract, with extraction version and error rate reported. Its scores must not be silently pooled with native-contract scores.

## Four controlled protocols

| Protocol | Case-library retrieval | Scientific/optical tools |
| --- | --- | --- |
| Closed-book | No | No, except evaluator-side validators after submission |
| Case-assisted | Versioned, allowed library snapshot | No |
| Tool-assisted | No | Declared tool set |
| Case-and-tool-assisted | Versioned library snapshot | Declared tool set |

The **question bytes, instance parameters, output contract, time/token budget, and scorer** must be identical for a matched comparison. Track access *available* separately from retrieval/tool calls *actually made*. Normal model-side inference/runtime facilities are declared, not smuggled into an apparently closed-book result. Compare within a protocol first; paired differences across protocols estimate retrieval and tool benefit. Agent scaffolds and model versions remain separate factors.

## Benchmark and case-library separation

The benchmark owns prompts, generated instances, private gold specifications, validators, split manifests, and immutable evaluation IDs. The optional case library owns instructive optical examples and retrieval metadata. It may contain explanations, but must exclude benchmark answers, near-duplicates, hidden instance parameters, and generated siblings crossing splits. Freeze and hash the library snapshot for each run; retrieval indexes may be rebuilt only from that snapshot. For the case-assisted condition, log returned document IDs and passages. Library content is never used as the benchmark's source of truth.

## Public and hidden evaluation

Start with a **public development set** for interface testing and reproducibility and a **public scored set** with stable, inspectable graders. Add a private scored set only when there is infrastructure to keep instance seeds, generated values, and answer keys confidential. Publish generator code, distributions, constraints, and validation protocol; keep private seeds and instantiated cases outside the open repository. This distinguishes openness of method from publication of every test answer. Record generator and validator versions with each instance. Release parameterized variants only after checking the allowed parameter range preserves solvability and scoring invariants. Structural/compositional variants need independent oracle tests; simple number changes alone do not establish new reasoning difficulty. Group seed cases and all derivatives by concept family before splitting.

Benchmark contamination cannot be eliminated by secrecy alone. Report exposure status, release dates, and similarity of public cases to private instances. Refresh private seeds and periodically introduce genuinely new optical structures. A dynamic benchmark design should be evaluated for whether it changes the scientific construct as well as whether it reduces memorization risk; see the [dynamic-benchmark survey](https://arxiv.org/abs/2502.17521).

## Tool independence and comparability

Express success in SI-compatible physical quantities, optical relations, and measurable outcomes. Do not require a software-specific file format or named proprietary component. If a solver submits a simulation, use an evaluator-owned independent model or measurement rule to check it; reproducing the same solver's output is not independent evidence. Version the physics assumptions (paraxial, ideal elements, damage thresholds, noise model) explicitly. Distinguish scientific correctness, schema compliance, and resource use. Never convert token or cost efficiency into an undeclared single score.

## Proposed repository boundary

```text
cases/public/             # future canonical public case sources
generators/               # future parameter and structural variants
schema/                   # versioned input, answer, and gold schemas
validators/               # isolated physics and constraint checkers
protocols/                # mode manifests and budgets
case_library/             # optional retrieval corpus, separately versioned
docs/                     # design decisions and research
results/README.md         # result format; raw runs stored separately
```

This is a boundary proposal, not a reason to create empty packages now. Before implementation, prove a small vertical slice across numeric, design, and diagnostic cases. [Inspect AI's task decomposition](https://inspect.aisi.org.uk/tasks.html) is a useful harness reference: datasets, solver behavior, and scorers are separable. The optical case format and validators should remain usable without Inspect AI.
