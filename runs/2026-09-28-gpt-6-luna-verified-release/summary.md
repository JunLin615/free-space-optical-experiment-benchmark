# Baseline run 2026-09-28-gpt-6-luna-verified-release

Execution class: **real**. Records: 20 / 20 declared.

Verified-case scores and development diagnostics are reported separately. Unknown resource values remain null.

| Track | Runs | Scored | Mean | Median | Success rate | Unresolved rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Verified | 20 | 20 | 0.9275 | 1.0000 | 0.8000 | 0.0000 |
| Development | 0 | 0 | null | null | null | null |
| Variants | 0 | 0 | null | null | null | null |

## Verified cases by protocol

| Protocol | Scored | Mean score | Successes | Input tokens | Tool calls | Wall seconds | Cost |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| closed_book | 5 | 0.9200 | 4 | 62703 | 0 | 92.3270 | null |
| case_assisted | 5 | 0.9300 | 4 | 65532 | 0 | 94.5170 | null |
| tool_assisted | 5 | 0.9300 | 4 | 62938 | 0 | 151.2050 | null |
| case_and_tool_assisted | 5 | 0.9300 | 4 | 65649 | 0 | 141.2040 | null |

Verified score distribution: `[0.6, 0.65, 0.65, 0.65, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]`.
Verified tokens, tool calls, wall seconds, and monetary cost per successful case: `{"tokens_per_success": 13093.3125, "tool_calls_per_success": 0, "wall_seconds_per_success": 19.489437499989435, "cost_per_success": null}`.

## Paired protocol differences

| Case | Assisted | Baseline | Score delta | Input-token delta | Output-token delta | Cost delta | Tool-call delta |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| SEED-1-1 | case_assisted | closed_book | 0.0 | 542 | 77 | None | 0 |
| SEED-1-1 | tool_assisted | closed_book | 0.0 | 45 | 153 | None | 0 |
| SEED-1-1 | case_and_tool_assisted | closed_book | 0.0 | 587 | 197 | None | 0 |
| SEED-1-1 | case_and_tool_assisted | tool_assisted | 0.0 | 542 | 44 | None | 0 |
| SEED-1-1 | case_and_tool_assisted | case_assisted | 0.0 | 45 | 120 | None | 0 |
| SEED-1-5 | case_assisted | closed_book | 0.0 | 546 | 136 | None | 0 |
| SEED-1-5 | tool_assisted | closed_book | 0.0 | 49 | 176 | None | 0 |
| SEED-1-5 | case_and_tool_assisted | closed_book | 0.0 | 589 | 199 | None | 0 |
| SEED-1-5 | case_and_tool_assisted | tool_assisted | 0.0 | 540 | 23 | None | 0 |
| SEED-1-5 | case_and_tool_assisted | case_assisted | 0.0 | 43 | 63 | None | 0 |
| SEED-1-7 | case_assisted | closed_book | 0.0 | 560 | 58 | None | 0 |
| SEED-1-7 | tool_assisted | closed_book | 0.0 | 47 | 10 | None | 0 |
| SEED-1-7 | case_and_tool_assisted | closed_book | 0.0 | 603 | 91 | None | 0 |
| SEED-1-7 | case_and_tool_assisted | tool_assisted | 0.0 | 556 | 81 | None | 0 |
| SEED-1-7 | case_and_tool_assisted | case_assisted | 0.0 | 43 | 33 | None | 0 |
| SEED-2-2 | case_assisted | closed_book | 0.050000000000000044 | 635 | -57 | None | 0 |
| SEED-2-2 | tool_assisted | closed_book | 0.050000000000000044 | 43 | 812 | None | 0 |
| SEED-2-2 | case_and_tool_assisted | closed_book | 0.050000000000000044 | 578 | 111 | None | 0 |
| SEED-2-2 | case_and_tool_assisted | tool_assisted | 0.0 | 535 | -701 | None | 0 |
| SEED-2-2 | case_and_tool_assisted | case_assisted | 0.0 | -57 | 168 | None | 0 |
| SEED-4-2 | case_assisted | closed_book | 0.0 | 546 | -3 | None | 0 |
| SEED-4-2 | tool_assisted | closed_book | 0.0 | 51 | 51 | None | 0 |
| SEED-4-2 | case_and_tool_assisted | closed_book | 0.0 | 589 | -18 | None | 0 |
| SEED-4-2 | case_and_tool_assisted | tool_assisted | 0.0 | 538 | -69 | None | 0 |
| SEED-4-2 | case_and_tool_assisted | case_assisted | 0.0 | 43 | -15 | None | 0 |

## Variant robustness

| Parent case | Variant | Protocol | Canonical score | Variant score | Delta |
| --- | --- | --- | ---: | ---: | ---: |

## Limits

Observed results for this model and run only. Public variants are development probes, not hidden generalization evidence. Unknown cost or usage remains null.
