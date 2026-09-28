# Automated case verification gates

Case state changes follow `seed → specified → executable → challenged → release_verified`; a discovered defect can move any state to `quarantined`. Status is based on case-specific evidence, not on a target count.

| State | Required automated evidence |
| --- | --- |
| `specified` | Versioned prompt, assumptions, disclosed answer contract, criteria, oracle plan, and provenance pass static schema/consistency checks. |
| `executable` | Every scored criterion resolves on canonical correct and clear wrong fixtures; generated public question is reproducible; normal scoring needs no human; failures distinguish candidate, instance, and oracle faults. |
| `challenged` | Independent physical derivation or formulation check; alternative-valid, rounded, boundary, and realistic adversarial fixtures; no known false pass or false fail in the declared supported answer region. |
| `release_verified` | All above, plus pinned case revision, benchmark manifest, validator source/environment, fixture hashes, semantic-judge version if used, and full CI preflight. All scored criteria resolve; open scientific alternatives are accepted or safely and explicitly excluded by the published task. A semantic criterion meets the live calibration threshold in [judge calibration](judge_calibration.md). No unresolved contradiction or known exploit remains. |

At every transition, the case schema and scorer registry must agree, criterion weights sum to one, referenced answer paths resolve, and public question rendering matches the canonical task. Fixture expectations are machine-readable and CI must fail on drift. A passed fixture suite proves only behavior on its challenge set. Mocked judge outputs test software plumbing and do not establish semantic reliability.

`python tools/check_verification_status.py` enforces fixture coverage and valid-answer resolution for cases marked `executable` or above. At `challenged` it also requires independent-derivation and adversarial-evidence fields. At `release_verified` it additionally rejects public development split, unresolved fixture results, absent fixture inventories, and a missing or mismatched release manifest. The manifest must pin SHA-256 hashes of the case, fixtures, schemas, generated question views, scorer/runtime sources, and dependency requirements. CI runs this gate after the fixture challenge command.

To quarantine a case after a defect, set `validation_status: quarantined`, record the defect and affected revisions, stop using its score in releases, add a failing regression fixture, repair the prompt/oracle in a new case revision, and rerun all gates. Preserve old result records and compare revisions explicitly; never silently rescore historical runs with a changed oracle. The unchanged seed remains provenance.
