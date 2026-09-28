# vNext scoring readiness

The generated [rc1 scoring readiness](scoring_readiness.md) remains fixed with
the original 64-case corpus and `0.1.0-rc1` qualification. This versioned
inventory describes the additional vNext path without rewriting those
historical generated artifacts.

| Group | Case IDs | Current decision |
| --- | --- | --- |
| Inherited release verified | SEED-1-1, 1-5, 1-7, 2-2, 4-2 | Requalified with the vNext evaluator; source case bytes unchanged. |
| Newly release verified | SEED-2-1, 3-1, 3-7, 5-5 | Versioned 0.3.0 cases with independent physical challenges and no unresolved release fixtures. |
| Deterministic reviewed, still development | SEED-2-4 | Open application tradeoffs still produce a credible unsupported alternative. |
| New structured development oracles | SEED-1-4, 3-2, 3-3, 7-5, 7-6 | All scored public tasks have bounded typed checks; unfamiliar valid approaches abstain. SEED-7-6 needs output-mode scope clarification. |
| New causal/constraint development oracles | SEED-7-1, 8-6 | Typed cause/test/outcome and routing/observability checks; alternatives beyond tested registries abstain. |

The current release total is **9 verified cases and 9 concept families**.
The five rc1 public-variant families and four vNext hidden-eligible families
are disjoint under the [machine-checked hidden policy](hidden_evaluation.md).
There are no mandatory semantic judges in the release. Prospective scorers
are development diagnostics and do not contribute to the verified headline.
