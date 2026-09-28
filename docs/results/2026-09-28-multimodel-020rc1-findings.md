# Interpretation of the 2026-09-28 frozen multi-model campaign

The [campaign index](../../benchmark/results/campaigns/2026-09-28-multimodel-020rc1/campaign.json) commits to six public run trees and three public hidden attestations. The [generated report](2026-09-28-multimodel-020rc1.md) contains every case score, five paired protocol contrasts per case, and resource metrics. All 108 formal records use the unchanged `0.2.0-rc1` release and its nine verified cases. The three real systems use `codex_cli`, `@openai/codex@0.158.0`, and the `neutral_optics_v1` scaffold; their advertised model IDs are `gpt-6-luna`, `gpt-6-sol`, and `gpt-6-astra`. Model version/date was not exposed by this interface. There were no infrastructure failures, automatic retries, or manual answer repairs.

| System | Closed book | Case assisted | Tool assisted | Case and tool assisted | Total tokens | Total wall time | First-attempt full successes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `gpt-6-luna` | 7/9 | 8/9 | 7/9 | 7/9 | 472,230 | 640.161 s | 29/36 |
| `gpt-6-sol` | 8/9 | 9/9 | 9/9 | 9/9 | 473,935 | 528.894 s | 35/36 |
| `gpt-6-astra` | 9/9 | 9/9 | 9/9 | 9/9 | 490,049 | 602.468 s | 36/36 |

These are exact full-success counts, not mean scores. Partial credit is retained in the generated report. Cost is `null` throughout: this CLI run supplied usage but no auditable per-call price or charge. The model names alone do not establish a measured cost ordering.

## Matched assistance effects

For Luna, case assistance changed the mean score from 0.9000 to 0.9556 and full successes from 7/9 to 8/9. It consumed 5,019 additional tokens and 28.734 additional wall seconds over those nine cases. The combined condition scored 0.9222 (7/9), below case assistance alone. For Sol, the closed-book mean was 0.9556 (8/9), and each assisted condition was 1.0000 (9/9); the affected case was the structured unit contract in `SEED-3-1`. Astra achieved 1.0000 in all four conditions, so assistance added tokens without increasing this release's score. Its case-assisted condition used 4,264 more tokens than closed book over nine cases.

The frozen tool profile was available in the tool-assisted and combined conditions, but the observed tool-call count was **zero for every model and protocol**. Thus the tool-assisted score differences cannot be attributed to actual computation-tool use. Availability, prompt context, and run variation remain possible explanations. Case retrieval was deterministic and matched: each assisted protocol retrieved 1,852 tokens per model across nine cases (3,704 per model across the two case-assisted conditions). The generated summary preserves per-record retrieval IDs, scores, tokens, and latency in the raw run evidence and reports the aggregates.

## Separate robustness tracks

The public development probe used five parameter or unit variants per model, all under `closed_book`. Their parent release is `0.1.0-rc1`, because those pre-existing variant records cannot be replayed as `0.2.0-rc1` cases. They never enter the 108-record formal score. Luna and Sol earned 5/5 full successes; Astra earned 4/5, with a 0.65 partial score on the `SEED-2-2` variant from a structured unit-contract failure.

All three models then received the **same** external, family-disjoint, eight-instance hidden bundle under `closed_book` at `0.2.0-rc1`. Evidence-derived public attestations report Luna mean 0.825 (five full successes; two physics failures and one invalid contract), Sol mean 1.000, and Astra mean 1.000. The bundle and raw hidden responses remain outside the repository; public attestations carry the common bundle commitment, evidence-tree hashes, usage, and aggregate outcomes. A public reader can check those published commitments but cannot independently inspect private task content.

## Interpretation limits

Nine canonical cases, five public variants, eight hidden instances, and one attempt per condition permit descriptive, paired observations only. A 1/9 change is substantial in the displayed rate but weak evidence of broad model superiority. The open-design work in PR-B is excluded from this campaign. This campaign did not estimate repeatability, cross-provider effects, or monetary efficiency. The [anomaly report](2026-09-28-multimodel-020rc1-anomalies.md) records contract and metadata observations without changing the frozen evaluator.
