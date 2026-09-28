# Canonical case contract

`case_v0.1.schema.json` validates one UTF-8 YAML file per case. Run
`python tools/validate_cases.py` from the repository root to validate all files
under `benchmark/cases`; paths may also be passed explicitly. Python dependencies
are `PyYAML` and `jsonschema` (see the root `requirements.txt`).

The schema validates structure and controlled vocabularies. The CLI additionally
checks cross-record ID uniqueness, scoring weights and references, answer paths,
numerical tolerance consistency, registered validator IDs, and authored numerical
gold against implemented independent equations. These checks cover only the
implemented models; adversarial fixtures remain necessary before release.
`python tools/check_corpus.py` additionally checks the preserved HTML hash,
all 64 legacy IDs, per-case lineage, and the original question counts.

`result.schema.json` describes a separate per-case run record. Run records are
outputs of the evaluator and are not embedded in canonical case YAML.
The record distinguishes distinct `tools_used` identifiers from the measured
`tool_call_count`, retains extensible raw `provider_usage`, and stores measured
`cost` with currency and a dated pricing reference. Unknown counts, usage, and
cost are `null`, never inferred as zero.
The development scorer also records a canonical case-content SHA-256,
evaluator version, and evaluator source fingerprint; these supplement the
case revision when reproducing a verdict. `oracle_unresolved` is separate from
candidate failures and from an unavailable semantic judge.
`pilot_answer_v0.1.schema.json` is the shared JSON block shape named by the canonical
cases' `answer_contract.schema_id`: it permits case-specific prose and structured
design claims while requiring physical numerical leaves to have `value` and
`unit`. Each case's `required_result_paths` and physics checks narrow that broad
shape; passing this shared answer schema alone never earns a score.
Optional `answer.explanation` is kept for audit and has no scoring effect. A
required explanation must instead have a scored judge rubric whose
`evidence_path` appears in `required_result_paths`, with its criterion listed
in `validation.semantic_criteria`.
Cases at `challenged` or above inventory executable derivation files in
`validation.evidence_files`. A release manifest hashes that inventory and,
when semantic scoring is used, the actual judge configuration, challenge set,
and live calibration results.

The canonical authoring record contains both public `task` and private `gold`.
Normal tool and case-library access is set by the evaluation protocol, not the
scientific task. `task.apparatus_constraints` is reserved for intrinsic limits
of the optical experiment, such as available components, and may appear in the
public question. It does not specify an agent's tool permissions.
Any public renderer or release exporter must select public fields explicitly;
it must never serialize the whole canonical record and then attempt to redact
selected keys. For `hidden_eval`, `gold` and scoring details remain private even
when a public question is rendered. `gold.visibility` marks authoring intent but
does not itself control access. A future release manifest will pin public and
private content hashes, case revisions, evaluator versions, and split assignment.

Unknown top-level and controlled nested fields fail validation; experiments may
use the top-level `extensions` mapping until the contract is revised. Schema
version `0.1.0` is an authoring contract, not a release claim. The full seed
fits this version; corpus completion did not require a schema change.
