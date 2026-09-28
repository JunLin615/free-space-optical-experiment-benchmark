# Baseline run 2026-09-28-gpt-6-luna-variants-release

Execution class: **real**. Records: 3 / 3 declared.

Verified-case scores and development diagnostics are reported separately. Unknown resource values remain null.

| Track | Runs | Scored | Mean | Median | Success rate | Unresolved rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Verified | 1 | 1 | 1.0000 | 1.0000 | 1.0000 | 0.0000 |
| Development | 0 | 0 | null | null | null | null |
| Variants | 2 | 2 | 1.0000 | 1.0000 | 1.0000 | 0.0000 |

## Verified cases by protocol

| Protocol | Scored | Mean score | Successes | Input tokens | Tool calls | Wall seconds | Cost |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| closed_book | 1 | 1.0000 | 1 | 12561 | 0 | 16.5780 | null |

Verified score distribution: `[1.0]`.
Verified tokens, tool calls, wall seconds, and monetary cost per successful case: `{"tokens_per_success": 12756, "tool_calls_per_success": 0, "wall_seconds_per_success": 16.57799999997951, "cost_per_success": null}`.

## Paired protocol differences

| Case | Assisted | Baseline | Score delta | Input-token delta | Output-token delta | Cost delta | Tool-call delta |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |

## Variant robustness

| Parent case | Variant | Protocol | Canonical score | Variant score | Delta |
| --- | --- | --- | ---: | ---: | ---: |
| SEED-1-1 | VAR-SEED-1-1-P-c8828a9799d3 | closed_book | 1.0 | 1.0 | 0.0 |
| SEED-1-1 | VAR-SEED-1-1-U-613088edc5d1 | closed_book | 1.0 | 1.0 | 0.0 |

## Limits

Observed results for this model and run only. Public variants are development probes, not hidden generalization evidence. Unknown cost or usage remains null.
