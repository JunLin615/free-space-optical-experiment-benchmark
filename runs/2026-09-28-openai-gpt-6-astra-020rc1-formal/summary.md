# Baseline run 2026-09-28-openai-gpt-6-astra-020rc1-formal

Execution class: **real**. Records: 36 / 36 declared.

Verified-case scores and development diagnostics are reported separately. Unknown resource values remain null.

| Track | Runs | Scored | Mean | Median | Success rate | Unresolved rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Verified | 36 | 36 | 1.0000 | 1.0000 | 1.0000 | 0.0000 |
| Development | 0 | 0 | null | null | null | null |
| Variants | 0 | 0 | null | null | null | null |

## Verified cases by protocol

| Protocol | Scored | Mean score | Successes | Input tokens | Tool calls | Wall seconds | Cost |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| closed_book | 9 | 1.0000 | 9 | 118292 | 0 | 153.0460 | null |
| case_assisted | 9 | 1.0000 | 9 | 122792 | 0 | 149.7830 | null |
| tool_assisted | 9 | 1.0000 | 9 | 118693 | 0 | 159.1390 | null |
| case_and_tool_assisted | 9 | 1.0000 | 9 | 123197 | 0 | 140.5000 | null |

Verified score distribution: `[1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]`.
Verified tokens, tool calls, wall seconds, and monetary cost per successful case: `{"tokens_per_success": 13612.472222222223, "tool_calls_per_success": 0, "wall_seconds_per_success": 16.73522222223174, "cost_per_success": null}`.

## Paired protocol differences

| Case | Assisted | Baseline | Score delta | Input-token delta | Output-token delta | Cost delta | Tool-call delta |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| SEED-1-1 | case_assisted | closed_book | 0.0 | 542 | -50 | None | 0 |
| SEED-1-1 | tool_assisted | closed_book | 0.0 | 41 | 8 | None | 0 |
| SEED-1-1 | case_and_tool_assisted | closed_book | 0.0 | 587 | -5 | None | 0 |
| SEED-1-1 | case_and_tool_assisted | tool_assisted | 0.0 | 546 | -13 | None | 0 |
| SEED-1-1 | case_and_tool_assisted | case_assisted | 0.0 | 45 | 45 | None | 0 |
| SEED-1-5 | case_assisted | closed_book | 0.0 | 542 | -4 | None | 0 |
| SEED-1-5 | tool_assisted | closed_book | 0.0 | 49 | -18 | None | 0 |
| SEED-1-5 | case_and_tool_assisted | closed_book | 0.0 | 587 | -32 | None | 0 |
| SEED-1-5 | case_and_tool_assisted | tool_assisted | 0.0 | 538 | -14 | None | 0 |
| SEED-1-5 | case_and_tool_assisted | case_assisted | 0.0 | 45 | -28 | None | 0 |
| SEED-1-7 | case_assisted | closed_book | 0.0 | 562 | -1 | None | 0 |
| SEED-1-7 | tool_assisted | closed_book | 0.0 | 47 | -16 | None | 0 |
| SEED-1-7 | case_and_tool_assisted | closed_book | 0.0 | 607 | -38 | None | 0 |
| SEED-1-7 | case_and_tool_assisted | tool_assisted | 0.0 | 560 | -22 | None | 0 |
| SEED-1-7 | case_and_tool_assisted | case_assisted | 0.0 | 45 | -37 | None | 0 |
| SEED-2-1 | case_assisted | closed_book | 0.0 | 538 | -18 | None | 0 |
| SEED-2-1 | tool_assisted | closed_book | 0.0 | 41 | -22 | None | 0 |
| SEED-2-1 | case_and_tool_assisted | closed_book | 0.0 | 581 | -34 | None | 0 |
| SEED-2-1 | case_and_tool_assisted | tool_assisted | 0.0 | 540 | -12 | None | 0 |
| SEED-2-1 | case_and_tool_assisted | case_assisted | 0.0 | 43 | -16 | None | 0 |
| SEED-2-2 | case_assisted | closed_book | 0.0 | 533 | -33 | None | 0 |
| SEED-2-2 | tool_assisted | closed_book | 0.0 | 45 | 8 | None | 0 |
| SEED-2-2 | case_and_tool_assisted | closed_book | 0.0 | 578 | -46 | None | 0 |
| SEED-2-2 | case_and_tool_assisted | tool_assisted | 0.0 | 533 | -54 | None | 0 |
| SEED-2-2 | case_and_tool_assisted | case_assisted | 0.0 | 45 | -13 | None | 0 |
| SEED-3-1 | case_assisted | closed_book | 0.0 | 365 | -76 | None | 0 |
| SEED-3-1 | tool_assisted | closed_book | 0.0 | 45 | -48 | None | 0 |
| SEED-3-1 | case_and_tool_assisted | closed_book | 0.0 | 408 | -26 | None | 0 |
| SEED-3-1 | case_and_tool_assisted | tool_assisted | 0.0 | 363 | 22 | None | 0 |
| SEED-3-1 | case_and_tool_assisted | case_assisted | 0.0 | 43 | 50 | None | 0 |
| SEED-3-7 | case_assisted | closed_book | 0.0 | 338 | -28 | None | 0 |
| SEED-3-7 | tool_assisted | closed_book | 0.0 | 49 | -45 | None | 0 |
| SEED-3-7 | case_and_tool_assisted | closed_book | 0.0 | 385 | -52 | None | 0 |
| SEED-3-7 | case_and_tool_assisted | tool_assisted | 0.0 | 336 | -7 | None | 0 |
| SEED-3-7 | case_and_tool_assisted | case_assisted | 0.0 | 47 | -24 | None | 0 |
| SEED-4-2 | case_assisted | closed_book | 0.0 | 540 | -16 | None | 0 |
| SEED-4-2 | tool_assisted | closed_book | 0.0 | 41 | -24 | None | 0 |
| SEED-4-2 | case_and_tool_assisted | closed_book | 0.0 | 587 | -15 | None | 0 |
| SEED-4-2 | case_and_tool_assisted | tool_assisted | 0.0 | 546 | 9 | None | 0 |
| SEED-4-2 | case_and_tool_assisted | case_assisted | 0.0 | 47 | 1 | None | 0 |
| SEED-5-5 | case_assisted | closed_book | 0.0 | 540 | -10 | None | 0 |
| SEED-5-5 | tool_assisted | closed_book | 0.0 | 43 | 56 | None | 0 |
| SEED-5-5 | case_and_tool_assisted | closed_book | 0.0 | 585 | 8 | None | 0 |
| SEED-5-5 | case_and_tool_assisted | tool_assisted | 0.0 | 542 | -48 | None | 0 |
| SEED-5-5 | case_and_tool_assisted | case_assisted | 0.0 | 45 | 18 | None | 0 |

## Variant robustness

| Parent case | Variant | Protocol | Canonical score | Variant score | Delta |
| --- | --- | --- | ---: | ---: | ---: |

## Limits

Observed results for this model and run only. Public variants are development probes, not hidden generalization evidence. Unknown cost or usage remains null.
