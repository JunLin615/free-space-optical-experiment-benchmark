# Autonomous evaluation design

Status: proposal, 2026-09-28. Normal runs are fully machine-operated. A human can audit benchmark construction but is never the default grader, tie-breaker, or per-run reviewer.

## Evaluation pipeline

1. **Resolve a manifest.** Pin benchmark, case, generator, instance seed, protocol, schema, validator, judge, agent scaffold, model, library snapshot, tool set, budget, and environment versions. Hash the resolved manifest.
2. **Instantiate and preflight.** Generate the question and private gold specification. Run oracle self-tests before exposing the question. Invalid instances are excluded with a recorded generator defect, not counted as agent failures.
3. **Run the agent.** Supply the same question and contract in every matched protocol. Capture complete tool/retrieval traces, provider usage, timestamps, final prose, and result object. Isolate evaluator code and private gold from the agent.
4. **Parse without inference.** Validate syntax, types, units, required fields, and cardinality. Report malformed output explicitly. A separately versioned text-extraction track can make a best-effort object from prose; native and extracted results remain separate.
5. **Score in layers.** Run deterministic math and graph checks, independent physics checks, constraint checks, then bounded semantic judges only for criteria left unresolved by executable checks.
6. **Aggregate and publish.** Keep per-criterion evidence and statuses, not merely an overall mark. Retain raw response and score provenance so a new scorer can rescore without rerunning the agent.

## Scoring layers and precedence

| Layer | Suitable claims | Mechanism | Important boundary |
| --- | --- | --- | --- |
| Typed deterministic | Numbers, units, equations, route endpoints, exact discrete choices | Parse quantities; dimensional check; compare to reference with absolute/relative tolerance; evaluate equivalent expressions on admissible samples | Reject unit mismatches and sign errors; tolerance is specified *before* seeing submissions. |
| Executable physics | Gaussian q/ABCD propagation, Jones/Mueller states, ray paths, Fourier-plane relations, path delay, conservation relations | Evaluator-owned reference implementation with randomized/property tests and independent cross-checks | State regime of validity, coordinate convention, uncertainties, and numerical precision. |
| Constraint graph | Open-ended designs and calibration logic | Parse components/functions, ordered beam-path edges, state at nodes, rejection paths, observables and tests; evaluate hard predicates plus weighted soft criteria | Do not require one named topology when different graphs implement the same transfer. |
| Bounded model judge | Explanation quality, whether a proposed diagnostic observation supports a hypothesis, nuanced trade-off reasoning | Reference-guided criterion-level judging over only the claims still requiring semantics | Never override a verified physical contradiction; no unbounded “overall quality” opinion. |

**Hard physical constraints gate success.** For example, a design that violates an explicitly required output direction, wavelength route, or conservation law cannot pass because its prose sounds persuasive. Partial credit remains per criterion. A model judge may mark a subtle engineering trade-off, but it cannot make a false numeric result true. A case is release-eligible only if all required criteria have an autonomous scoring path and the oracle passes adversarial tests. If judges cannot reliably decide a criterion, narrow the output contract or make the criterion non-scored exploratory material; do not defer routine runs to experts.

Numeric tolerances include a dimension, reference value, `abs_tol`, `rel_tol`, and rounding policy. A pass can be defined as `|x-x_ref| <= max(abs_tol, rel_tol*|x_ref|)` only where that rule matches the measurement/approximation semantics. Interval, angular wraparound, complex phase, and inequality checks need dedicated comparators. For approximate estimates, test multiple physical relations rather than string matching a formula.

## Open-ended optical designs

Represent candidate hardware as a typed directed graph. Nodes describe source, optical element class and parameters, detector, dump, reference plane, or transform; edges describe propagation with wavelength, polarization basis/state, beam size/axis, and direction. Scoring predicates can ask whether the primary output satisfies the required transform, whether an unwanted branch is terminated, whether conjugate planes or time delays match, and whether calibration measurements discriminate the expected failure. The evaluator may normalize graph-equivalent layouts and test a candidate in a bounded parameter domain. It should reject unspecified parameters needed for a claim; it should not reject a novel but verifiably correct topology because it is absent from an example list.

For cases where full hardware simulation would be too costly, require a **minimal sufficient certificate**: a set of transfer relations and observable node states. Validators check these mathematically and check that the stated component sequence can realize them under the case's idealized model. For real component limits, provide ranges for aperture, wavelength, power, damage threshold, and uncertainty. If the prompt omits critical parameters, score whether the agent identifies the underdetermination and proposes a discriminating measurement, rather than rewarding invented precise values.

## Model judging and calibration

Use independent grader models or distinct model families where available, fixed criterion rubrics, blinded candidate identity, randomized answer order in pairwise calibration, and a held-out set of known positive, negative, borderline, and adversarial answers. Track false-pass and false-fail rates by criterion and case family. Require an explicit, parseable verdict with short cited evidence from the submitted answer. Consensus must have a predeclared rule; ties or parse failures produce `judge_unresolved`. They must not silently become pass, fail, or a call for human review. A published benchmark can report a bounded score interval for unresolved semantic criteria and a separate resolution rate. Repeated judge runs estimate instability. Pin prompts, model IDs, sampling parameters, and judge versions. [Inspect AI supports model graders and scorer aggregation](https://inspect.aisi.org.uk/scoring.html), but its availability does not establish that a rubric is calibrated for optics.

Treat candidate responses and retrieved text as untrusted judge input. The grader sees only the relevant claim and criterion, with explicit instruction/data separation; test prompt-injection examples. Re-judge a fixed calibration set after judge upgrades. Do not compare scores across judge versions without a bridge study.

## Failure handling and reproducibility

Separate `agent_timeout`, `agent_error`, `no_answer`, `invalid_contract`, `physics_fail`, `constraint_fail`, `judge_unresolved`, `validator_error`, and `invalid_instance`. Agent failures count against success under a declared budget; evaluator defects and invalid instances do not. Preserve retry count and first-attempt output. A solver can voluntarily abstain; report coverage and conditional accuracy as separate metrics. Validators run in a sandbox with bounded CPU/memory and no access to agent secrets; executable submissions use stricter isolation. Save seeds, container/library digests, code commit, dependency lock, locale, unit conventions, and numerical backend. Deterministic scorers must be regression tested on positive, near-miss, boundary, and adversarial answers.

## Metrics and comparisons

The primary publication should be a **metric vector**: per-domain and per-task success, physical-validity rate, constraint-satisfaction rate, schema compliance, criterion-level scores, judge resolution/instability, and calibration quality. Report macro averages across case families so a cluster of similar easy questions cannot dominate. Include uncertainty intervals and paired comparisons for protocol ablations. Record model/provider/version, scaffold, prompts/protocol IDs, context and library IDs, tools available/used, tool-call count, input/output/cached tokens when supplied, total tokens, time, cost and price schedule, retries, raw response, structured result, validator outputs, and failure mode. Missing provider usage is `unknown`, never zero. Report token-, cost-, and tool-calls-per-success with denominators and censoring stated; report first-attempt success and recovery efficiency separately. Cost is time-sensitive and provider-specific, so raw usage remains the durable measure.

The architecture follows the general lesson of executable agent environments such as [AgentBench](https://github.com/THUDM/AgentBench/blob/main/docs/Introduction_en.md) and the separated scoring in [Inspect AI](https://inspect.aisi.org.uk/tasks.html). The optical predicates and confidence gates above are **recommendations for this project**, not claimed features of those systems.
