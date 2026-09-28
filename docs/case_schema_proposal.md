# Canonical case schema proposal

**Status:** design proposal, not a frozen data contract. **Language of this proposal and example:** English. The illustrative case below is newly constructed for this document; it is **not** a translation, replacement, or addition to the 64-case seed.

## Design choice

Use **one UTF-8 YAML file per case** as the authoring format, with a versioned JSON Schema for structural validation. YAML keeps a long problem statement and author notes readable in review; JSON Schema gives precise types, required fields, and controlled vocabulary. Build reproducible JSON/JSONL releases from the YAML files for runners and data hosting. Generated Markdown and HTML question banks must come from the same source. A JSONL release is an interchange artifact, not an editing surface; TOML is less suitable for nested scoring expressions. The runner may map these records into Inspect AI or another harness, but the source format and evaluator IDs must not depend on a particular harness or optical design program.

This is a recommendation, not a claim that YAML itself verifies optical physics. A schema validator checks structure; separately versioned physics validators and case fixtures check semantics. Keep an explicit `schema_version` independent of the benchmark release. Reject unknown fields except in a designated extension namespace, to catch misspellings. Parse YAML as data only: prohibit custom tags, aliases that create cycles, and executable expressions. Numeric values use unit-bearing quantity objects; normalize to SI before comparison. Angle and phase conventions must be declared, since silent degree/radian and sign errors are common.

The proposed separation is:

1. **Public task**: facts, assumptions, subquestions, requested result schema, and allowed resources. No reference values or hidden grading logic.
2. **Gold specification**: equations, quantitative reference values, accepted constraints and alternatives, forbidden contradictions, and weighted criteria. This is a specification of physical validity, not an answer paragraph.
3. **Validator package**: named, sandboxed, versioned implementations of the checks, with positive and negative fixtures. Neither the case nor the candidate submits executable code to the grader by default.
4. **Run record**: a separate immutable record of candidate answer, tool use, validator results, evaluator versions, and resource use. Run-specific metadata does not belong in the case file.

The reference evaluator should grade the **declared physical outcome**, not the vendor, program, or incidental optical component nomenclature. A candidate can choose any viable measurement method within the stated resources. The public prompt should avoid embedding a preferred topology. Validity checks must cover claimed measured quantities and calibration logic; a model judge may assess residual semantic claims, but cannot override a failed deterministic physical check without an explicit, versioned rule.

## Proposed top-level fields

| Field | Purpose and validation |
| --- | --- |
| `schema_version` | Version of the case data contract, e.g. `0.1.0`; validate before other fields. |
| `case_id` | Stable opaque ID; never reuse after retirement. Seed IDs may be retained as `legacy_id` during migration. |
| `case_revision` | Monotonic revision of this case's scientific content and scoring semantics. Editorial changes may also record a patch revision. |
| `benchmark_release` | First release containing this revision. A release manifest pins exact case revisions and hashes. |
| `validation_status` | Evidence stage: `seed`, `specified`, `executable`, `challenged`, `release_verified`, or `quarantined`, as defined in [automated validation design](automated_validation_design.md). Only `release_verified` is eligible for a scored release. |
| `split` | Assignment independent of evidence stage: `unassigned`, `public_dev`, `public_eval`, or `hidden_eval`. The release manifest determines actual publication. A `quarantined` case retains its split for traceability but cannot be released. |
| `title`, `language`, `taxonomy` | Display title; language tag; controlled optical domain, task type, difficulty evidence, and modality labels. Difficulty labels are hypotheses until calibrated on baseline results. |
| `provenance` | Origin, source references, derivation notes, authoring or generation method, creation date, source hash, and source/license status. Never present an invented scenario as a sourced real experiment. |
| `task` | Public statement, subquestions, given quantities and assumptions, requested observable and convention, exclusions, and resource policy. Every criterion should trace to a public requirement. |
| `answer_contract` | Required machine-readable fields plus human-readable explanation. A versioned JSON Schema validates the candidate block. Permit equivalent methods and extra explanatory claims without requiring a single component list. |
| `gold` | Machine-readable numerical checks, physical constraints, alternative solution families, forbidden claims, optional model-judge rubric, and expected error cases. Private for held-out cases. |
| `scoring` | Criterion weights, check IDs, gate/cap rules, aggregation, uncertainty handling, and unscorable behavior. Weights sum to one within each scored question. |
| `validation` | Case-level checks and fixtures that must pass before inclusion; records independent derivation and adversarial-test evidence. |

### Field rules that matter scientifically

- Each quantity has `value` and `unit`, with an optional `definition` (for example, beam radius at (1/e^2) intensity), uncertainty, and coordinate frame. Tolerances are separate from physical uncertainty. A tolerance is a grading acceptance interval justified by rounding, measurement resolution, and equivalent methods; it should never silently change the physical model.
- A numerical check states the formula or validator ID, its inputs, reference value, unit, `absolute_tolerance` and/or `relative_tolerance`, and boundary policy. A simple default is `abs(candidate-reference) <= max(abs_tol, rel_tol*abs(reference))`; specify a different policy explicitly for periodic quantities, intervals, or asymmetric bounds. `relative_tolerance` alone is unsuitable when the reference is zero.
- For open designs, define **requirements** and **families** separately. Required functions apply to every accepted solution; a family describes one known way to meet them and can provide family-specific checks. The list of families should not act as a closed whitelist. An unlisted topology can pass if a topology-neutral physical validator establishes the same mandatory invariants. If no such validator exists, the case is not ready for scored release.
- Constraint IDs identify atomic predicates and their evidence paths. `hard` constraints are mandatory. `scored` constraints earn bounded partial credit. `forbidden` constraints express physical contradictions. An evaluator should preserve the full per-criterion vector and apply any cap only afterward.
- A requirement that can only be checked by a model judge must declare its rubric, examples of pass and fail, judge version, threshold, and calibrated reliability. If the residual judgement changes the pass/fail outcome and calibration is inadequate, retain the case as a development case rather than route it to a human during normal runs.
- A candidate's structured result is the scoring input; the prose is retained for audit and contradiction detection. Missing structured fields receive zero for their dependent criteria. Invalid JSON or unsupported units have a deterministic parse result and a specified score effect. The evaluator should never guess values from prose after a schema failure.
- Hidden cases may publish a schema and a subset of development examples without revealing reference values, private seeds, or validator fixtures. Release manifests should pin case content hashes, schema, validator versions, judge model/prompt version, and rounding policy.

## Illustrative complete case record

This invented example tests whether an agent can distinguish beam position from propagation angle using free-space measurements. It deliberately leaves the optical measurement implementation open. The values are exact within the stated paraxial model. Its evidence stage is `specified`: the contract and oracle plan exist, but no executable validator has been implemented. The example is sufficiently specified to turn into a fixture, but the validator IDs below are **proposed interface names**, not implemented code. It is ineligible for scored release.

```yaml
schema_version: "0.1.0"
case_id: "ILLUSTRATIVE-BEAM-STATE-001"
case_revision: "0.1.0"
benchmark_release: null
validation_status: "specified"
split: "unassigned"
title: "Recover beam offset and angle from two transverse measurements"
language: "en"
taxonomy:
  optical_domain: "free_space_beam_geometry"
  task_types: ["quantitative_inference", "experimental_design", "calibration"]
  difficulty_hypothesis: "intermediate"
  modality: "text"
provenance:
  origin: "new_synthetic_schema_illustration"
  seed_relationship: "not_derived_from_seed_case"
  created_utc: "2026-09-28"
  source_references: []
  derivation: "Paraxial straight-line propagation x(z) = x0 + theta_x*z."
  license_status: "original_example_pending_project_license"
task:
  statement: >-
    A collimated beam travels in air along a nominal free-space optical axis.
    Its horizontal centroid is +0.40 mm at z = 0.00 m and +1.60 mm at
    z = 1.20 m, measured from the same fixed reference axis. Positive x
    is to the right when viewed along +z. Treat propagation as paraxial
    and straight between the planes. Determine its horizontal offset at
    z = 0, its horizontal propagation angle, and its predicted centroid
    at z = 3.00 m. Propose a practical measurement and correction procedure
    that can independently bring both offset and angle to zero. State
    how the result would be verified.
  givens:
    - {symbol: "z_a", value: 0.0, unit: "m"}
    - {symbol: "x_a", value: 0.40, unit: "mm"}
    - {symbol: "z_b", value: 1.20, unit: "m"}
    - {symbol: "x_b", value: 1.60, unit: "mm"}
    - {symbol: "z_predict", value: 3.00, unit: "m"}
  assumptions:
    - "All x values use one fixed reference axis and one signed coordinate convention."
    - "Beam centroid is measured; spot size does not substitute for centroid."
    - "The beam is stable during the measurement procedure."
    - "No refracting or steering element lies between the stated planes."
  questions:
    - {id: "q1", request: "Report x at z = 0, signed angle, and x at z = 3.00 m."}
    - {id: "q2", request: "Give a two-degree-of-freedom correction and verification procedure."}
  allowed_resources: "Any scientific or optical tool; no named product required."
answer_contract:
  format: "human_explanation_plus_json_object"
  schema_id: "beam_state_answer_v0.1"
  required_result_paths:
    - "results.offset_at_zero"
    - "results.angle_x"
    - "results.predicted_x_at_3m"
    - "method.measurement_planes"
    - "method.independent_offset_angle_correction"
    - "verification.two_plane_residuals"
  quantity_shape: {value: "number", unit: "string"}
  method_shape:
    measurement_planes: "array of at least two distinct z positions"
    independent_offset_angle_correction: "structured functions and ordered steps"
  permit_additional_explanation: true
gold:
  reference_model:
    equation: "x(z) = x_a + (x_b - x_a)*(z - z_a)/(z_b - z_a)"
    valid_if: "z_b != z_a and the stated straight-line assumptions hold"
  numerical_checks:
    - id: "n_offset"
      answer_path: "results.offset_at_zero"
      reference: {value: 0.40, unit: "mm"}
      absolute_tolerance: {value: 0.02, unit: "mm"}
      relative_tolerance: 0.0
      comparator: "max_abs_or_relative_inclusive"
    - id: "n_angle"
      answer_path: "results.angle_x"
      reference: {value: 1.00, unit: "mrad"}
      absolute_tolerance: {value: 0.02, unit: "mrad"}
      relative_tolerance: 0.0
      comparator: "max_abs_or_relative_inclusive"
    - id: "n_prediction"
      answer_path: "results.predicted_x_at_3m"
      reference: {value: 3.40, unit: "mm"}
      absolute_tolerance: {value: 0.04, unit: "mm"}
      relative_tolerance: 0.0
      comparator: "max_abs_or_relative_inclusive"
  universal_constraints:
    - id: "c_two_positions"
      severity: "hard"
      predicate: "at_least_two_distinct_longitudinal_centroid_measurements"
      evidence_path: "method.measurement_planes"
    - id: "c_two_dof"
      severity: "hard"
      predicate: "procedure_controls_offset_and_angle_independently"
      evidence_path: "method.independent_offset_angle_correction"
    - id: "c_verify"
      severity: "scored"
      predicate: "verify_centroid_residual_at_two_separated_planes"
      evidence_path: "verification.two_plane_residuals"
    - id: "c_fixed_reference"
      severity: "scored"
      predicate: "measurements_share_a_fixed_coordinate_reference"
      evidence_path: "method.reference_axis"
  accepted_solution_families:
    - id: "simultaneous_two_sensor"
      example: "Two calibrated cameras or position sensors at distinct z planes."
      family_checks: ["sensor_centroid_calibration", "common_reference"]
    - id: "sequential_movable_sensor"
      example: "One calibrated camera translated between known planes while beam stability is checked."
      family_checks: ["position_registration", "beam_stability_check"]
    - id: "two_aperture_with_centroid_readout"
      example: "Near and far apertures plus a calibrated centroid readout at each plane."
      family_checks: ["aperture_center_registration", "signed_centroid_readout"]
  accepted_correction_families:
    - id: "separated_steering_mirrors"
      example: "Two independently adjustable steering mirrors separated along the beam path."
      family_checks: ["nondegenerate_position_angle_response", "iterative_two_plane_readout"]
    - id: "translation_and_angle_actuators"
      example: "An independent transverse translation and angular steering control."
      family_checks: ["nondegenerate_position_angle_response", "iterative_two_plane_readout"]
  other_valid_families_policy: >-
    Accept any other apparatus if the universal predicates and equivalent
    calibration checks pass; do not match component names as a whitelist.
  forbidden_claims:
    - {id: "f_one_plane", predicate: "one_plane_uniquely_determines_offset_and_angle"}
    - {id: "f_wrong_sign", predicate: "positive_x_slope_is_negative_angle"}
  known_failure_modes:
    - "Confusing 1 mm/m with 1 degree instead of 1 mrad."
    - "Using a moving reference axis for the second measurement."
    - "Centering the beam at only one plane and declaring both degrees of freedom corrected."
scoring:
  criteria:
    - {id: "offset", weight: 0.15, check: "n_offset"}
    - {id: "angle", weight: 0.20, check: "n_angle"}
    - {id: "prediction", weight: 0.15, check: "n_prediction"}
    - {id: "measurement", weight: 0.15, check: "c_two_positions"}
    - {id: "correction", weight: 0.20, check: "c_two_dof"}
    - {id: "verification", weight: 0.10, check: "c_verify"}
    - {id: "reference_calibration", weight: 0.05, check: "c_fixed_reference"}
  hard_rule: >-
    If c_two_positions or c_two_dof fails, cap the case score at 0.50;
    if f_one_plane is asserted, cap at 0.35; if f_wrong_sign is asserted,
    cap at 0.50. Apply the lowest applicable cap. Report raw and capped score.
  malformed_answer_rule: >-
    Missing or invalid structured paths score zero for dependent criteria;
    preserve the raw response and parse error in the run record.
  aggregation: "weighted_sum_then_hard_cap"
validation:
  planned_checks:
    - "yaml_and_json_schema_valid"
    - "all_scoring_ids_resolve_and_weights_sum_to_one"
    - "quantities_convert_to_SI_and_are_dimensionally_consistent"
    - "independent_numeric_derivation_agrees"
    - "positive_and_adversarial_answer_fixtures_pass"
  implemented_checks: []
  draft_positive_fixture:
    results:
      offset_at_zero: {value: 0.40, unit: "mm"}
      angle_x: {value: 1.00, unit: "mrad"}
      predicted_x_at_3m: {value: 3.40, unit: "mm"}
    method:
      measurement_planes: ["z=0.00 m", "z=1.20 m"]
      reference_axis: "fixed, calibrated datum"
      independent_offset_angle_correction:
        functions: ["control transverse position", "control propagation angle"]
        steps: ["adjust near-plane offset", "adjust far-plane residual", "iterate"]
    verification:
      two_plane_residuals:
        planes: ["z=0.00 m", "z=1.20 m"]
        maximum_absolute_centroid_residual: {value: 0.05, unit: "mm"}
```

The numerical result follows directly: `(1.60 − 0.40) mm / 1.20 m = +1.00 mrad`; at `3.00 m`, `x = 0.40 mm + (1.00 mrad)(3.00 m) = 3.40 mm`. The draft fixture's `0.05 mm` alignment limit is an illustrative acceptance criterion for the proposed procedure, separate from the numerical-answer tolerances. The named semantic predicates still need executable definitions or calibrated judge rules before this example could enter a scored release. These are intentional draft gaps, not an invitation for a human grader to decide each run.

## Candidate output contract and evaluator boundary

The benchmark instruction can request a concise explanation followed by one JSON object. The JSON schema should specify quantity objects, enums for broad physical functions, and arrays for beam-path or measurement nodes when applicable. A candidate may attach additional fields for a novel topology. The evaluator should process stages in order: parse and validate; normalize units; run numerical and physics checks; evaluate universal constraints; run family-specific checks only if relevant; apply calibrated semantic checks to residual claims; then aggregate and record every result. All accepted alternatives must satisfy the same public physical goal. A failed parse, missing datum, invalid unit, or timeout has a predetermined result rather than a manual adjudication queue.

The example's family labels illustrate authoring and fixture coverage. They are not a closed set of acceptable answers. For harder design cases, a reliable topology-neutral verifier may require an optical graph, declared states at named nodes, and a small executable model. If that verifier cannot distinguish correct alternatives from contradictions, the case should remain unscored development material until the output contract is sharpened. This is preferable to a nominal benchmark score that depends on expert interpretation.

## Versioning and provenance rules

- **Case ID:** permanent identity for the scientific task. A changed physical objective or assumptions may require a new ID with `supersedes`; a typo correction keeps the ID and increments `case_revision`.
- **Schema version:** increments when field meaning or validation rules change. Migration scripts must be deterministic and preserve old releases.
- **Benchmark release:** immutable manifest of case IDs, case revisions, split assignment, hashes, validator versions, and judge configuration. Score comparisons across releases require a disclosed mapping or rerun.
- **Gold and validator changes:** increment evaluator version even if the public question is unchanged. Record score deltas on fixed baseline responses and adversarial fixtures.
- **Provenance:** cite real sources with URLs/DOIs and licenses when a case is adapted from literature; state `synthetic` for invented laboratory setups. Preserve source date and hash. Keep private generation seeds out of public releases.
- **Answer and run records:** store the raw candidate output, parsed block, errors, per-check outcomes, model and scaffold identity, allowed and used tools, retrieval mode, tokens, cost if available, and elapsed time separately from canonical case data.

## Evidence behind the format recommendation

The [JSON Schema specification](https://github.com/json-schema-org/json-schema-spec/blob/main/specs/jsonschema-validation.md) supports typed properties, required fields, and numeric constraints; it motivates the machine-checkable data contract, while optical validity remains a separate verifier. [Inspect AI's dataset documentation](https://inspect.aisi.org.uk/datasets.html) separates sample input, target, ID, and metadata, and its [scorer documentation](https://inspect.aisi.org.uk/standard-scorers.html) separates output scoring from the dataset. That separation is useful, although this project should not adopt Inspect's API as its canonical format. [ScienceAgentBench](https://github.com/OSU-NLP-Group/ScienceAgentBench) shows why executable scientific artifacts and multiple evaluation metrics can be useful; its program-file target should not be imposed on every optics question. [NIST's SI guidance](https://www.nist.gov/pml/special-publication-811/nist-guide-si-chapter-7-rules-and-style-conventions-expressing-values) supports explicit quantity and unit conventions; the tolerance policy above is this project's design recommendation, not a rule claimed from NIST.
