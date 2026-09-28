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
result. The normal runner needs a version-dispatch integration for new
generators before a real hidden run.

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

SHA-256 commitments make a later reveal auditable; they do not prove a seed was
secret before creation, prevent a privileged evaluator from leaking content,
or detect semantic overlap with model training data. Public CI uses synthetic
policies and temporary private bundles only. It needs no secret or model API.
