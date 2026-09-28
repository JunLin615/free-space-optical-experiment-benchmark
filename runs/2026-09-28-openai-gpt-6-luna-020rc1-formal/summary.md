# Baseline run 2026-09-28-openai-gpt-6-luna-020rc1-formal

Execution class: **real**. Records: 36 / 36 declared.

Verified-case scores and development diagnostics are reported separately. Unknown resource values remain null.

| Track | Runs | Scored | Mean | Median | Success rate | Unresolved rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Verified | 36 | 36 | 0.9222 | 1.0000 | 0.8056 | 0.0000 |
| Development | 0 | 0 | null | null | null | null |
| Variants | 0 | 0 | null | null | null | null |

## Verified cases by protocol

| Protocol | Scored | Mean score | Successes | Input tokens | Tool calls | Wall seconds | Cost |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| closed_book | 9 | 0.9000 | 7 | 112742 | 0 | 147.7670 | null |
| case_assisted | 9 | 0.9556 | 8 | 117142 | 0 | 176.5010 | null |
| tool_assisted | 9 | 0.9111 | 7 | 113143 | 0 | 155.4390 | null |
| case_and_tool_assisted | 9 | 0.9222 | 7 | 117539 | 0 | 160.4540 | null |

Verified score distribution: `[0.5, 0.6, 0.6, 0.6, 0.6, 0.6, 0.7, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]`.
Verified tokens, tool calls, wall seconds, and monetary cost per successful case: `{"tokens_per_success": 13142.827586206897, "tool_calls_per_success": 0, "wall_seconds_per_success": 17.80613793103739, "cost_per_success": null}`.

## Paired protocol differences

| Case | Assisted | Baseline | Score delta | Input-token delta | Output-token delta | Cost delta | Tool-call delta |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| SEED-1-1 | case_assisted | closed_book | 0.0 | 438 | 3 | None | 0 |
| SEED-1-1 | tool_assisted | closed_book | 0.0 | -59 | -55 | None | 0 |
| SEED-1-1 | case_and_tool_assisted | closed_book | -0.30000000000000004 | 485 | 118 | None | 0 |
| SEED-1-1 | case_and_tool_assisted | tool_assisted | -0.30000000000000004 | 544 | 173 | None | 0 |
| SEED-1-1 | case_and_tool_assisted | case_assisted | -0.30000000000000004 | 47 | 115 | None | 0 |
| SEED-1-5 | case_assisted | closed_book | 0.0 | 540 | 54 | None | 0 |
| SEED-1-5 | tool_assisted | closed_book | 0.0 | 43 | 9 | None | 0 |
| SEED-1-5 | case_and_tool_assisted | closed_book | 0.0 | 583 | 131 | None | 0 |
| SEED-1-5 | case_and_tool_assisted | tool_assisted | 0.0 | 540 | 122 | None | 0 |
| SEED-1-5 | case_and_tool_assisted | case_assisted | 0.0 | 43 | 77 | None | 0 |
| SEED-1-7 | case_assisted | closed_book | 0.0 | 558 | 84 | None | 0 |
| SEED-1-7 | tool_assisted | closed_book | 0.0 | 45 | -9 | None | 0 |
| SEED-1-7 | case_and_tool_assisted | closed_book | 0.0 | 601 | -8 | None | 0 |
| SEED-1-7 | case_and_tool_assisted | tool_assisted | 0.0 | 556 | 1 | None | 0 |
| SEED-1-7 | case_and_tool_assisted | case_assisted | 0.0 | 43 | -92 | None | 0 |
| SEED-2-1 | case_assisted | closed_book | 0.5 | 536 | 77 | None | 0 |
| SEED-2-1 | tool_assisted | closed_book | 0.5 | 43 | 129 | None | 0 |
| SEED-2-1 | case_and_tool_assisted | closed_book | 0.5 | 579 | 71 | None | 0 |
| SEED-2-1 | case_and_tool_assisted | tool_assisted | 0.0 | 536 | -58 | None | 0 |
| SEED-2-1 | case_and_tool_assisted | case_assisted | 0.0 | 43 | -6 | None | 0 |
| SEED-2-2 | case_assisted | closed_book | 0.0 | 527 | 391 | None | 0 |
| SEED-2-2 | tool_assisted | closed_book | -0.4 | 147 | -194 | None | 0 |
| SEED-2-2 | case_and_tool_assisted | closed_book | 0.0 | 574 | -263 | None | 0 |
| SEED-2-2 | case_and_tool_assisted | tool_assisted | 0.4 | 427 | -69 | None | 0 |
| SEED-2-2 | case_and_tool_assisted | case_assisted | 0.0 | 47 | -654 | None | 0 |
| SEED-3-1 | case_assisted | closed_book | 0.0 | 367 | -13 | None | 0 |
| SEED-3-1 | tool_assisted | closed_book | 0.0 | 47 | 38 | None | 0 |
| SEED-3-1 | case_and_tool_assisted | closed_book | 0.0 | 412 | -30 | None | 0 |
| SEED-3-1 | case_and_tool_assisted | tool_assisted | 0.0 | 365 | -68 | None | 0 |
| SEED-3-1 | case_and_tool_assisted | case_assisted | 0.0 | 45 | -17 | None | 0 |
| SEED-3-7 | case_assisted | closed_book | 0.0 | 342 | 9 | None | 0 |
| SEED-3-7 | tool_assisted | closed_book | 0.0 | 45 | 29 | None | 0 |
| SEED-3-7 | case_and_tool_assisted | closed_book | 0.0 | 387 | 71 | None | 0 |
| SEED-3-7 | case_and_tool_assisted | tool_assisted | 0.0 | 342 | 42 | None | 0 |
| SEED-3-7 | case_and_tool_assisted | case_assisted | 0.0 | 45 | 62 | None | 0 |
| SEED-4-2 | case_assisted | closed_book | 0.0 | 548 | -8 | None | 0 |
| SEED-4-2 | tool_assisted | closed_book | 0.0 | 43 | 9 | None | 0 |
| SEED-4-2 | case_and_tool_assisted | closed_book | 0.0 | 587 | 5 | None | 0 |
| SEED-4-2 | case_and_tool_assisted | tool_assisted | 0.0 | 544 | -4 | None | 0 |
| SEED-4-2 | case_and_tool_assisted | case_assisted | 0.0 | 39 | 13 | None | 0 |
| SEED-5-5 | case_assisted | closed_book | 0.0 | 544 | 22 | None | 0 |
| SEED-5-5 | tool_assisted | closed_book | 0.0 | 47 | -29 | None | 0 |
| SEED-5-5 | case_and_tool_assisted | closed_book | 0.0 | 589 | 15 | None | 0 |
| SEED-5-5 | case_and_tool_assisted | tool_assisted | 0.0 | 542 | 44 | None | 0 |
| SEED-5-5 | case_and_tool_assisted | case_assisted | 0.0 | 45 | -7 | None | 0 |

## Variant robustness

| Parent case | Variant | Protocol | Canonical score | Variant score | Delta |
| --- | --- | --- | ---: | ---: | ---: |

## Limits

Observed results for this model and run only. Public variants are development probes, not hidden generalization evidence. Unknown cost or usage remains null.
