# Family-disjoint hidden evaluation

The source questions for all 64 canonical cases are public. A private variant
therefore cannot be called contamination-proof. This workflow avoids exact
instance memorization and the easiest public-variant sibling leakage while
testing changed physical parameters and safe structural forms.

## Eligibility and disjointness

[`family_map.v1.json`](../benchmark/hidden_eval/family_map.v1.json) maps every
canonical case to a concept family, scorer family, release status, public
variant eligibility, hidden variant eligibility, and optional generator
metadata. A hidden source must be release-verified in the named release, have
an explicitly registered and tested variant generator, an approved variant
type, and be marked hidden-eligible. Eligibility defaults to false. The
generated instance remains a development-derived variant; its verified parent
does not automatically make that instance release-verified.
In `0.2.0-rc1`, SEED-2-1, SEED-3-1, SEED-3-7, and SEED-5-5 are the four
approved hidden sources. They share no concept family with the five rc1
public-variant sources.

The hidden policy checker rejects a hidden source if **any** public-development
variant in the committed plan has (1) the same canonical parent, (2) the same
`concept_family`, or (3) the same generator template. It also rejects duplicate
hidden source/type selections, duplicate generated IDs or instance hashes,
unregistered generator/release combinations, and mismatches with release pins.
An additional screen rejects exact scientific payloads, normalized task
structure, and complete typed parameter tuples shared with public variants.
The concept-family labels are deliberately finer than broad domains such as
`polarization` or `interferometry`; reviewers should inspect borderline sibling
relationships before enabling a source. This rule separates *generated*
public-development variants from generated hidden-evaluation variants. Public
canonical questions and general physical principles remain visible.

## Private policy and bundle

Keep the private policy and output outside the repository. The policy uses
[`private_policy.v1.schema.json`](../benchmark/hidden_eval/private_policy.v1.schema.json):

```json
{
  "schema_version": "1.0.0",
  "release_id": "0.2.0-rc1",
  "generator_version": "0.2.0",
  "seed": "<at least 32 random hexadecimal characters>",
  "family_count": 1,
  "selections": [
    {"parent_case_id": "<approved case ID>", "variant_type": "<approved type>", "instance_index": 0}
  ]
}
```

The example is a shape, not an approved selection. Use a newly generated,
high-entropy seed; a long predictable string is insufficient. The first hidden
bundle should contain a modest number of independently qualified families,
with several separately validated instances only if the generator supports
them. `instance_index` defaults to zero; positive indices derive separate
generator seeds from the private master seed, source, type, and index. Duplicate
source/type/index selections or duplicate generated instance contents fail.
No private policy or bundle is committed.

```sh
python -m tools.hidden_eval check-map
python -m tools.hidden_eval generate --policy /external/private-policy.json --output-dir /external/hidden-bundle
python -m tools.hidden_eval audit --bundle-dir /external/hidden-bundle
python -m tools.hidden_eval dry-run --bundle-dir /external/hidden-bundle
```

`generate` refuses an existing destination, so a previous bundle is never
overwritten. It writes the private policy, private gold-free variant records,
and `commitment.json` under that destination. The evaluator reconstructs gold
only in memory through the registered generator. The dry run sends the public
payload to the same mock adapter envelope used by the baseline runner, parses
its scripted response, and scores it. It is labeled `dry_run`, not a model
result. The baseline runner now dispatches `0.2.0-rc1` to its versioned
generator, neutral public answer hints, and scorer. To prepare a resumable
private run, supply an external baseline agent JSON config and use a fresh
run ID:

```sh
python -m tools.hidden_eval prepare-run --bundle-dir /external/hidden-bundle --output-root /external/runs --run-id hidden-run-001 --agent-json /external/agent.json
python -m tools.baseline /external/runs/input_manifests/hidden-run-001.json --output-root /external/runs
python -m tools.hidden_eval audit-results --bundle-dir /external/hidden-bundle --run-dir /external/runs/hidden-run-001
python -m tools.hidden_eval attest-run --bundle-dir /external/hidden-bundle --run-dir /external/runs/hidden-run-001 --attestation /public/real-run-attestation.json
python -m tools.hidden_eval audit-attestation --bundle-dir /external/hidden-bundle --run-dir /external/runs/hidden-run-001 --attestation /public/real-run-attestation.json
```

`prepare-run` validates the bundle, creates a new private input manifest, and
rejects an existing run ID. A mock agent config makes a dry run; a configured
command or Codex CLI adapter is recorded as a real run. The runner keeps raw
responses, task instances, and per-attempt results outside the repository.
Do not publish a real run without reviewing its response disclosure risk.
`attest-run` derives model/protocol identity, score, usage, cost, and failure
counts from the linked private result records. It refuses dry-run evidence;
write its public output outside the frozen private run directory.

The first private pilot used four families and two variants per family. The
external bundle reproduced all eight instances. A prepared mock runner run
completed eight of eight, and `audit-results` linked all eight records. No
model API was called. Its public-safe commitment and dry-run counts are in
[`first_private_dry_run.v1.json`](../benchmark/hidden_eval/attestations/first_private_dry_run.v1.json).

One additional real smoke call used an already accessible `gpt-6-luna` Codex
CLI adapter on a single private diffraction-resolution variant, under
closed-book. The private runner completed one record; bundle/result linkage
passed; its score was 1.0 with 12,784 reported input-plus-output tokens and
no priced cost estimate. This is one infrastructure probe, not a model
benchmark or a generalization estimate. The public
[`first_real_smoke.v1.json`](../benchmark/hidden_eval/attestations/first_real_smoke.v1.json)
contains only the bundle commitment, identity, aggregate score, usage, failure
summary, and private-run evidence hashes. The private task and raw response
remain outside the repo.

## Commitment and audit

The public-safe [`commitment.v1.schema.json`](../benchmark/hidden_eval/commitment.v1.schema.json)
contains a bundle ID, release and generator versions, policy schema version,
instance and family counts, SHA-256 commitments to the canonical private
policy, seed bytes, and individual private records, plus creation time. It
contains no seed, hidden task text, parent list, raw model response, or gold.
Publish only the commitment after examining whether counts or identifiers
themselves reveal a sensitive selection. Do not publish the full bundle.

An authorized auditor can supply the private bundle and public code to
`audit`. This rechecks disjointness and release eligibility, regenerates every
instance from the private seed, validates scorer compatibility, compares each
record and commitment hash, and rejects missing or extra instances. Store any
real run's private records and raw responses with the bundle. A public result
attestation may include the bundle commitment and aggregate outcomes after
disclosure review, while private evaluator evidence may contain full tasks,
seeds, answers, and raw responses. These are separate publication levels.

For a completed private runner run, `python -m tools.hidden_eval audit-results
--bundle-dir /external/hidden-bundle --run-dir /external/hidden-run` checks
that every selected and scored instance belongs to the bundle, and that its
science, generator, instance, and scorer fingerprints match. It returns counts
and IDs only; raw responses remain in the private run directory.

`attest-run` first audits that linkage, then hashes every regular file in the
frozen run directory, including the exact manifest, result, log, protocol,
environment, and system-prompt bytes. The tree digest uses the
`hidden-run-evidence-tree-v1` domain, sorted relative UTF-8 paths, and
8-byte big-endian lengths before each path and its raw file bytes. The public
attestation contains the tree digest, manifest digest, and file count, never
private file paths or content. `audit-attestation` regenerates the bundle,
recomputes the run summary and digests, and compares the entire public object.
Changing a score, usage field, manifest field, log byte, or published claim
invalidates the audit. An auditor needs the retained private bundle and run
directory; the hashes alone cannot prove honest execution or prevent a
privileged operator from replacing both private evidence and attestation.

SHA-256 commitments make a later reveal auditable; they do not prove a seed was
secret before creation, prevent a privileged evaluator from leaking content,
or detect semantic overlap with model training data. Public CI uses synthetic
policies and temporary private bundles only. It needs no secret or model API.
