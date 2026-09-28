# Evaluation protocols v1

Four machine-readable manifests in `benchmark/protocols/` define the environment
for matched runs. Their scientific source is `tools.protocols.public_payload(case)`.
The runner computes the payload before adding examples or tools, records its
SHA-256, and supplies identical task bytes for every protocol in a matched set.
Only the resource environment changes.

| Protocol | Example library | Computational tools | External network |
| --- | --- | --- | --- |
| `closed_book` | no | no | no |
| `case_assisted` | yes | no | no |
| `tool_assisted` | no | `calculator`, `unit_convert` | no |
| `case_and_tool_assisted` | yes | `calculator`, `unit_convert` | no |

Each manifest has version `1.0.0`, a fixed scientific prompt source, an explicit
library snapshot or `null`, bounded retrieval, tool profile, network and file
policy, context cap, timeouts, zero default retries, answer-format rule, neutral
system scaffold, and mandatory logging fields. File access means content
explicitly supplied by the runner; arbitrary local files are not part of v1.
The generic computation profile is `generic_computation_v0.1`. These policies
do not alter case-level apparatus constraints.

## Scientific payload and answer-contract projection

The payload contains case identity/revision, the unchanged canonical `task`,
and a projection of structural answer-contract fields: format,
required result paths, quantity syntax, optional explanation permission, and
approved answer-object shapes for the pilot cases. It excludes scoring gold,
validation, and the original `method_shape` text. Some rc1 `method_shape`
strings disclose solution choices, including a correct Boolean value in
SEED-1-7 and accepted q3 alternatives in SEED-1-1. The approved shapes state
field types without those answers, so a physically correct response can use
the autonomous scorer's JSON contract. This projection changes no immutable
rc1 case bytes. Required path names remain visible; their leakage risk should be
revisited if a future case revision makes a path itself reveal a scored value.
The scorer still sees the original full case internally.

For a matched comparison, `tools.protocols.check_matched_runs` checks case ID,
revision, optional variant ID, scientific payload hash, scorer ID and optional
fingerprint, result schema version, and agent identity. It rejects absent
protocol versions, duplicate protocols, and mismatched versions. Changing a
model or variant intentionally creates a separate comparison group. A run
manifest should also pin the protocol manifest bytes and system-prompt version.

The same neutral system scaffold may state the role, resource availability,
and output format. It must not give case-specific physics hints or expose gold.
Normal grading remains autonomous. The local comparison tool is a guardrail
against accidentally comparing different scientific questions; it does not
establish the scientific equivalence of separately generated variants.

Validate manifests with `python -m tools.protocols`. The protocol schema is
`benchmark/protocols/protocol.schema.json`.
