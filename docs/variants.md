# Deterministic development variants

The first variant generator covers the five cases in `0.1.0-rc1`: `SEED-1-1`, `SEED-1-5`, `SEED-1-7`, `SEED-2-2`, and `SEED-4-2`. Each source has one parameter variant and one equivalent-unit or symbolic-representation variant in the [public development set](../benchmark/variants/public_questions.md). These ten instances are public examples, not hidden evaluation evidence.

## Generate and use

```sh
python tools/variants.py generate-public
python tools/variants.py check-public
```

The plan in `benchmark/variants/public_plan.json` pins the source case, variant type, public seed, and generator version. A record in `benchmark/variants/public_dev/` contains its task, answer format, parent case revision and SHA-256 content hash, generator version, parameter constraints, public or private seed classification, seed commitment, instance and scientific-payload hashes, and rc1 scorer version and fingerprint. It lists compatibility with the four protocol IDs at version `1.0.0`. Public JSON records and the question view contain **no gold or reference answers**. `tools.variants.load_variant(path)` reconstructs an internal case with recomputed gold; pass `loaded["case"]` to `tools.scoring_runtime.evaluate_case`. Preserve `loaded["variant_id"]` and `scientific_payload_sha256` separately in run metadata. The internal case retains its parent's case ID and revision because the released scorer dispatches on that ID; the variant ID distinguishes the instance. A variant's case hash intentionally differs from its pinned parent hash.

The public answer contract describes fields and units. The generated contract removes two answer-bearing method hints inherited from rc1 while keeping the same required result paths. A runner must send only the task and public answer contract to the agent; never send the internal reconstructed case or its gold.

## Physical scope

The generator changes mirror rotation and screen distance, double-pass delay travel and target delay, half-wave plate angles, afocal input/output diameter and expansion ratio, and Michelson mirror displacement. Unit variants express equivalent types of input using radians, micrometers, meters, or symbolic wavelength fractions. It does not vary optical regimes, introduce clipping, vary beam quality, or change the number of reflections. For the Michelson case, the secondary movement remains one-quarter wavelength so its typed given symbol retains its meaning; the primary movement is an integer number of complete fringe periods. The afocal variant recomputes the focal-ratio gold and example pairs when its expansion ratio changes.

Each variant is rejected if the parent or scorer differs from the rc1 pin; inputs are nonfinite, negative, degenerate, or outside family-specific ranges; a numerical reference disagrees with the physical equation; a tolerance exceeds 10% of the expected magnitude; the case schema or semantic checks fail; the scientific payload or instance hash changes; or an independently assembled correct answer does not earn a full, resolved score. The release case/scorer files and rc1 manifest are never changed by generation. This validation is targeted to these five families and is not a general optics theorem prover.

## Private seed interface

Keep a private JSON seed file and generated private output **outside the repository**. The CLI rejects in-repository paths. The seed must be at least 128 bits encoded as hexadecimal. For example, create an external file with this shape, substituting a new random secret value:

```json
{
  "seed": "<at least 32 random hexadecimal characters>",
  "selections": [
    {"parent_case_id": "SEED-1-1", "variant_type": "parameter"},
    {"parent_case_id": "SEED-2-2", "variant_type": "structural_unit"}
  ]
}
```

```sh
python tools/variants.py generate-private --seed-file /external/private-seed.json --output-dir /external/private-instances
python tools/variants.py verify-private --seed-file /external/private-seed.json --variant /external/private-instances/VAR-....json
```

The private record contains a one-way seed commitment and generated givens, but not the seed. An evaluator can score it using `load_variant`; a custodian can later reproduce it with the external seed using `verify-private`. The instance and scorer hashes allow audit of which task and oracle were used without publishing that seed. A hash commitment does not make a low-entropy seed safe: the interface checks hexadecimal length, while the custodian must supply actual randomness and protect the file. Generated givens necessarily reveal the specific problem to an agent during evaluation. This mechanism controls accidental repository leakage, not a malicious host or all forms of semantic contamination.

## Contamination and interpretation

Public variants retain the same concept family and often task phrasing as their parents. They test sensitivity to changed numbers, units, and representations, not hidden generalization. A structural unit variant may share a physical numeric tuple with a parameter sibling while changing its representation; that relation is intentional and must be tracked in lineage. The separate case-library leakage audit checks exact text, near text, numeric tuples, and direct answer overlap against public variants. It does not certify that a model has never seen a related concept elsewhere.
