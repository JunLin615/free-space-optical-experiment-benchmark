# Baseline run 2026-09-28-openai-gpt-6-sol-020rc1-formal

Execution class: **real**. Records: 36 / 36 declared.

Verified-case scores and development diagnostics are reported separately. Unknown resource values remain null.

| Track | Runs | Scored | Mean | Median | Success rate | Unresolved rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Verified | 36 | 36 | 0.9889 | 1.0000 | 0.9722 | 0.0000 |
| Development | 0 | 0 | null | null | null | null |
| Variants | 0 | 0 | null | null | null | null |

## Verified cases by protocol

| Protocol | Scored | Mean score | Successes | Input tokens | Tool calls | Wall seconds | Cost |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| closed_book | 9 | 0.9556 | 8 | 114247 | 0 | 130.3460 | null |
| case_assisted | 9 | 1.0000 | 9 | 118743 | 0 | 125.1260 | null |
| tool_assisted | 9 | 1.0000 | 9 | 114665 | 0 | 133.2050 | null |
| case_and_tool_assisted | 9 | 1.0000 | 9 | 119142 | 0 | 140.2170 | null |

Verified score distribution: `[0.6, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]`.
Verified tokens, tool calls, wall seconds, and monetary cost per successful case: `{"tokens_per_success": 13177.114285714286, "tool_calls_per_success": 0, "wall_seconds_per_success": 14.725085714291449, "cost_per_success": null}`.

## Paired protocol differences

| Case | Assisted | Baseline | Score delta | Input-token delta | Output-token delta | Cost delta | Tool-call delta |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| SEED-1-1 | case_assisted | closed_book | 0.0 | 540 | -8 | None | 0 |
| SEED-1-1 | tool_assisted | closed_book | 0.0 | 43 | -19 | None | 0 |
| SEED-1-1 | case_and_tool_assisted | closed_book | 0.0 | 583 | 2 | None | 0 |
| SEED-1-1 | case_and_tool_assisted | tool_assisted | 0.0 | 540 | 21 | None | 0 |
| SEED-1-1 | case_and_tool_assisted | case_assisted | 0.0 | 43 | 10 | None | 0 |
| SEED-1-5 | case_assisted | closed_book | 0.0 | 544 | 13 | None | 0 |
| SEED-1-5 | tool_assisted | closed_book | 0.0 | 43 | 15 | None | 0 |
| SEED-1-5 | case_and_tool_assisted | closed_book | 0.0 | 583 | 92 | None | 0 |
| SEED-1-5 | case_and_tool_assisted | tool_assisted | 0.0 | 540 | 77 | None | 0 |
| SEED-1-5 | case_and_tool_assisted | case_assisted | 0.0 | 39 | 79 | None | 0 |
| SEED-1-7 | case_assisted | closed_book | 0.0 | 556 | 13 | None | 0 |
| SEED-1-7 | tool_assisted | closed_book | 0.0 | 45 | 25 | None | 0 |
| SEED-1-7 | case_and_tool_assisted | closed_book | 0.0 | 601 | 35 | None | 0 |
| SEED-1-7 | case_and_tool_assisted | tool_assisted | 0.0 | 556 | 10 | None | 0 |
| SEED-1-7 | case_and_tool_assisted | case_assisted | 0.0 | 45 | 22 | None | 0 |
| SEED-2-1 | case_assisted | closed_book | 0.0 | 536 | -76 | None | 0 |
| SEED-2-1 | tool_assisted | closed_book | 0.0 | 45 | 22 | None | 0 |
| SEED-2-1 | case_and_tool_assisted | closed_book | 0.0 | 581 | -78 | None | 0 |
| SEED-2-1 | case_and_tool_assisted | tool_assisted | 0.0 | 536 | -100 | None | 0 |
| SEED-2-1 | case_and_tool_assisted | case_assisted | 0.0 | 45 | -2 | None | 0 |
| SEED-2-2 | case_assisted | closed_book | 0.0 | 533 | -33 | None | 0 |
| SEED-2-2 | tool_assisted | closed_book | 0.0 | 47 | -10 | None | 0 |
| SEED-2-2 | case_and_tool_assisted | closed_book | 0.0 | 580 | -15 | None | 0 |
| SEED-2-2 | case_and_tool_assisted | tool_assisted | 0.0 | 533 | -5 | None | 0 |
| SEED-2-2 | case_and_tool_assisted | case_assisted | 0.0 | 47 | 18 | None | 0 |
| SEED-3-1 | case_assisted | closed_book | 0.4 | 359 | 62 | None | 0 |
| SEED-3-1 | tool_assisted | closed_book | 0.4 | 45 | 152 | None | 0 |
| SEED-3-1 | case_and_tool_assisted | closed_book | 0.4 | 406 | 99 | None | 0 |
| SEED-3-1 | case_and_tool_assisted | tool_assisted | 0.0 | 361 | -53 | None | 0 |
| SEED-3-1 | case_and_tool_assisted | case_assisted | 0.0 | 47 | 37 | None | 0 |
| SEED-3-7 | case_assisted | closed_book | 0.0 | 340 | -3 | None | 0 |
| SEED-3-7 | tool_assisted | closed_book | 0.0 | 43 | -15 | None | 0 |
| SEED-3-7 | case_and_tool_assisted | closed_book | 0.0 | 383 | 11 | None | 0 |
| SEED-3-7 | case_and_tool_assisted | tool_assisted | 0.0 | 340 | 26 | None | 0 |
| SEED-3-7 | case_and_tool_assisted | case_assisted | 0.0 | 43 | 14 | None | 0 |
| SEED-4-2 | case_assisted | closed_book | 0.0 | 546 | 36 | None | 0 |
| SEED-4-2 | tool_assisted | closed_book | 0.0 | 51 | 41 | None | 0 |
| SEED-4-2 | case_and_tool_assisted | closed_book | 0.0 | 589 | 41 | None | 0 |
| SEED-4-2 | case_and_tool_assisted | tool_assisted | 0.0 | 538 | 0 | None | 0 |
| SEED-4-2 | case_and_tool_assisted | case_assisted | 0.0 | 43 | 5 | None | 0 |
| SEED-5-5 | case_assisted | closed_book | 0.0 | 542 | 4 | None | 0 |
| SEED-5-5 | tool_assisted | closed_book | 0.0 | 56 | 20 | None | 0 |
| SEED-5-5 | case_and_tool_assisted | closed_book | 0.0 | 589 | 56 | None | 0 |
| SEED-5-5 | case_and_tool_assisted | tool_assisted | 0.0 | 533 | 36 | None | 0 |
| SEED-5-5 | case_and_tool_assisted | case_assisted | 0.0 | 47 | 52 | None | 0 |

## Variant robustness

| Parent case | Variant | Protocol | Canonical score | Variant score | Delta |
| --- | --- | --- | ---: | ---: | ---: |

## Limits

Observed results for this model and run only. Public variants are development probes, not hidden generalization evidence. Unknown cost or usage remains null.
