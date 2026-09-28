# First measured baseline: 2026-09-28

This is a small infrastructure experiment, not a model ranking or a claim about
general optics competence. One legitimately accessible model, OpenAI
`gpt-6-luna` through Codex CLI `0.158.0`, ran with the neutral scaffold and
zero automatic retries. The model version/date was not exposed and is recorded
as `null`. Each run used the same committed source at `5f6d97f` and the same
source SHA-256 recorded in its result files. The three immutable run directories
contain manifests, frozen prompts/protocols, raw answers, scorer records,
normalized adapter events, usage, and machine-generated analyses:

- [`verified-release`](../runs/2026-09-28-gpt-6-luna-verified-release/summary.md): five rc1 release-verified cases × four matched protocols (20 records).
- [`development-release`](../runs/2026-09-28-gpt-6-luna-development-release/summary.md): two challenged development cases under closed-book (2 records).
- [`variants-release`](../runs/2026-09-28-gpt-6-luna-variants-release/summary.md): canonical SEED-1-1 plus its parameter and unit public variants under closed-book (3 records).

All 25 declared model calls completed. There were zero transport retries,
timeouts, tool runtime failures, scorer failures, or invalid benchmark
instances. Candidate answers can still fail individual criteria. Earlier
preflight runs exposed Windows UTF-8 input and answer-shape issues; their
artifacts were excluded from this frozen result set.

## Verified slice

| Case | Closed | Case-assisted | Tool-assisted | Case + tool |
| --- | ---: | ---: | ---: | ---: |
| SEED-1-1 | 1.00 | 1.00 | 1.00 | 1.00 |
| SEED-1-5 | 1.00 | 1.00 | 1.00 | 1.00 |
| SEED-1-7 | 1.00 | 1.00 | 1.00 | 1.00 |
| SEED-2-2 | 0.60 | 0.65 | 0.65 | 0.65 |
| SEED-4-2 | 1.00 | 1.00 | 1.00 | 1.00 |

The 20 scores average **0.9275** (median **1.0**); 16/20 are full successes.
The first-attempt full-success rate is 80%, unresolved rate 0%, invalid-contract
rate 15%, and physics-failure rate 5%. The only nonfull case is SEED-2-2.
Closed-book used the supported dimensionless unit but supplied a Galilean
focal-length pair with the wrong magnitude ratio, losing the example criterion.
The other three conditions supplied valid lens pairs but used the unsupported
unit string `dimensionless` instead of `1` for the expansion ratio. The scorer
recorded those as invalid contracts. The case-assistance score delta of +0.05
on this one case is therefore a change in failure type, not demonstrated
case-library benefit. All other per-case score deltas are zero.

The five paired comparisons are present per case in `summary.json`. Mean
score deltas versus closed-book are +0.01 for each assisted condition, and
case + tool versus either single-resource condition is 0. The sample is too
small for a statistical improvement claim.

| Protocol | Mean score | Full successes | Total tokens | Wall time sum | Observed tool calls |
| --- | ---: | ---: | ---: | ---: | ---: |
| Closed-book | 0.92 | 4/5 | 63,984 | 92.33 s | 0 |
| Case-assisted | 0.93 | 4/5 | 67,024 | 94.52 s | 0 |
| Tool-assisted | 0.93 | 4/5 | 65,421 | 151.20 s | 0 |
| Case + tool | 0.93 | 4/5 | 67,510 | 141.20 s | 0 |

Across verified runs, the provider reported 256,822 input, 7,117 output,
184,832 cached input, and 3,967 reasoning tokens (263,939 input + output
tokens). Total observed wall time was 479.25 s; median run wall time was
20.10 s. Successful calls averaged 13,093.31 total tokens and 19.49 s of
wall time. A monetary cost and cost per success are `null`
because no dated, verifiable pricing snapshot was supplied for this
account-backed CLI execution. Cached and reasoning tokens are reported
separately and are not added a second time to input + output.

Case-assisted retrieval supplied 15 items and 1,131 estimated lexical tokens
across five cases; case + tool supplied the same counts. Retrieval itself took
0.021 s and 0.024 s respectively in aggregate. These estimates are not billed
provider tokens. Case-assisted input was 2,829 tokens above closed-book across
the five paired cases; there was no observed full-success or unresolved-rate
gain. The model made **zero runner-observed tool calls**, including in both
tool-enabled conditions. Thus this run measures the effect of offering the
tool profile, not the benefit of actual calculation with it. There were no
tool failures. Latency differences include provider variability and must not
be attributed causally to resource permissions from one sample.

## Development cases and public variants

SEED-2-4 returned an `oracle_unresolved` aggregate because the bounded
tradeoff criterion abstained; its two numerical criteria failed. SEED-3-1
scored 0.60 with an invalid-contract failure on image distance, while its
other two criteria passed. These two calls used 25,378 total tokens and 33.69 s
of wall time. They are **not** included in the verified mean or success rate.

For SEED-1-1, the canonical closed-book replicate and both public development
variants each scored 1.0. The parameter and unit variants therefore have
observed score delta 0 against their canonical run. The two variant calls used
25,574 total tokens. This is a formatting and parameter-sensitivity probe,
not evidence of hidden generalization. The ten public variants are reproducible
and available for broader future testing, but only these two were run on the
real model in this round.

## Reproduction and limits

Run `python tools/analyze_baseline.py runs/<run-id> --check` to validate each
stored analysis against its result records. The initial manifests live in
`runs/input_manifests/`; every run directory freezes its exact input bytes.
Those executed manifests retain their original Windows paths. Use the
[cross-machine replay command](baseline_runner.md#cross-machine-replay) to
derive a separate portable run and choose a new local output root.
Running the model again can produce different answers or usage. The runner
does not hand-repair raw answers. The Codex CLI adapter disallows its built-in
shell and web tools, rejects observed built-in tool events, and exposes only
the bounded runner calculator and unit converter when a protocol permits them.

The published scores are conditional on one model, one run per case/protocol,
five verified cases, and the current typed contracts. In particular, the
SEED-2-2 `dimensionless` formatting failures show that a physically meaningful
claim may still be rejected by the existing unit vocabulary. This result does
not authorize changing rc1 gold or scorer bytes. Future work should test a
versioned answer-contract clarification and repeated runs before drawing
resource-effect conclusions.
