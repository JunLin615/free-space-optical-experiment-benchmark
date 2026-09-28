# Baseline runner v0.1

Run one frozen manifest with `python -m tools.baseline path/to/manifest.json`. Use
`--check` to validate without execution. The runner crosses each selected case
or variant with each listed protocol. It loads scientific content through
`tools.protocols.public_payload` for every protocol, records that payload's
SHA-256, and checks matched descriptors before invoking an agent. It never
sends gold or validation evidence. The public payload includes only
gold-free structural answer hints, rather than the case file's full
`method_shape` text, which can reveal a solution.

## Manifest and identity

The schema is `benchmark/run_schema/run_manifest_v0.1.schema.json`. A manifest
freezes `run_id`, release, selected case IDs and tracks, protocol IDs, provider
and model identity, adapter, neutral system prompt version, retrieval and tool
configuration, timeout, retry policy, concurrency, seed, output directory, and
optional dated pricing snapshot. New manifests set `output_directory` to the
logical `run_id`; `--output-root` supplies a host-local absolute root at
execution. Historical absolute paths remain valid on the originating host
and are preserved as evidence. The initial protocols cap an agent turn at
300 seconds and allow no automatic retries. `concurrency` is one in v0.1 so
result ordering and logs are
deterministic. The system prompt is `benchmark/system_prompts/neutral_optics_v1.txt`;
it contains no case-specific physics hints.

For a verified canonical selection, the runner checks the case revision, case
content hash, and evaluator fingerprint against `0.1.0-rc1` before execution.
Development cases and public/private variants have separate `track` values.
Variant records are loaded through `tools.variants.load_variant`, which
materializes scorer-ready gold only in memory. A variant never enters the
verified canonical score track.

## Adapters and bounded tools

- `mock` is for offline dry runs and tests. A manifest with `adapter_type=mock`
  must set `execution_class=dry_run`; its scores are never real baseline data.
- `command` accepts a JSON request on stdin and returns one JSON envelope on
  stdout. It can return `{"type":"final","raw_response":"{...}"}` or
  `{"type":"tool_call","tool_name":"calculator","arguments":{"expression":"2*pi"}}`.
  The runner sends a later request with prior tool exchanges. A generic
  command may have unobservable internal tools; its result marks
  `protocol_compliance_verified=false` and `tool_call_count=null`. Do not use
  such a run as matched protocol evidence without external permission controls.
- `codex_cli` runs a configurable command prefix (for example
  `npx -y @openai/codex@0.158.0`) in a fresh temporary directory with
  read-only sandbox, shell tool disabled, and web search disabled. The model
  sees only public payload, allowed retrieved items, and prior runner tool
  exchanges. The runner captures normalized JSONL event order and reported
  token usage; any built-in tool event invalidates the run. A successful
  no-tool probe on this host returned only an agent-message event. Credentials
  remain outside the manifest.

The first tool profile, `generic_computation_v0.1`, permits only a bounded
arithmetic calculator and a same-dimension unit converter. It has no arbitrary
Python execution, shell, file, or network tool. Each runner-mediated call logs
its index, safe arguments, status, duration, and nullable token/cost fields.
Malformed calls and tool-policy violations become infrastructure failures,
never candidate scores of zero. Codex JSONL events are normalized before
persistence to avoid saving arbitrary tool output.

## Results and resume

The runner copies the input manifest byte-for-byte to
`runs/<run_id>/manifest.json` and never changes it on resume. It also creates
`system_prompt.txt`, frozen protocol JSON files, `environment.json`,
`results/<case-or-variant>__<protocol>.json`, and matching
JSONL logs. A result is written through a `.partial` file and atomic replace;
partial files are not completed results. Completed records are skipped on
resume. Failed records are also skipped by default; `--retry-failed` appends a
numbered attempt while retaining the original failure record. A new declared
baseline should use a new run ID.

## Cross-machine replay

The three committed measured manifests retain the Windows output paths that
were actually used. To validate a **new** replay on a POSIX host without
calling the model, run:

```sh
python -m tools.baseline runs/2026-09-28-gpt-6-luna-verified-release/manifest.json \
  --output-root /tmp/optics-replay --replay-suffix linux-01 --check
```

To execute that replay later, omit `--check` with the same arguments. This
creates a portable input manifest under
`/tmp/optics-replay/input_manifests/` and freezes it in a new
`/tmp/optics-replay/<original-run-id>-linux-01/` directory. The replay gets a
new run ID and a `replay_of` reference with the original run ID and canonical
JSON SHA-256. All selected cases, protocols, model/scaffold identity, budgets,
retrieval and tool settings, prompt version, seed, and pricing fields are copied
unchanged. The output root is operational and is never inserted into the
portable replay manifest. Its `created_utc` remains the source manifest's
historical configuration timestamp. The original manifest and results are
never rewritten or copied into the replay. Repeating the command with the
same suffix resumes that new run; choose another suffix for another independent
run. A real replay may yield different model answers and usage.

For a new logical manifest, use `python -m tools.baseline path/to/input.json
--output-root /absolute/local/root`. Omitting `--output-root` uses the
repository's `runs/` directory. An absolute historical manifest cannot be
redirected merely by adding `--output-root`; a replay suffix is required to
prevent accidental reuse of its immutable result files.
`python -m tools.prepare_first_baseline` now writes logical output locations;
its `--output-root` selects where input manifests are created, and the runner's
`--output-root` selects where their result directories are created.

The wrapper schema is `benchmark/run_schema/run_record_v0.1.schema.json`.
Successful scoring embeds the unchanged `benchmark/schema/result.schema.json`
record as `score_result`. The wrapper also records variant lineage, protocol
and payload hash, full agent identity, retrieval IDs/text hashes/scores/token
estimate/latency, observed tool calls, raw and parsed responses, attempts,
usage, wall time, cost, source revision, and failure class. Unknown usage and
cost remain `null`. The retrieval token estimate is kept separate from provider
input tokens. A dated pricing snapshot is required before monetary cost is
calculated; historical runs are never repriced automatically.

The default retry policy is zero. If a future protocol version permits retry,
transport retries, malformed-JSON retries, and agent self-correction are
separate manifest fields. V0.1 implements only transport and malformed-JSON
retry paths under explicit caps; it never retries a scientifically wrong answer
until it passes. Raw malformed responses are preserved and scored as invalid
contracts when retries are exhausted. Model API errors, timeout, malformed
tool calls, tool runtime/policy failures, invalid benchmark instances, and
scorer failures remain distinguishable from candidate physics failures.

## Reproducibility limits

The manifest and records freeze observable configuration, case/variant hashes,
retrieved content, evaluator fingerprint, usage, and exact adapter command
prefix. Stochastic model APIs may not replay byte-for-byte. The generic
command adapter cannot prove that its own process used no internal tools; use
the constrained Codex CLI adapter or an externally enforced sandbox for
matched real protocol comparisons. Mock records must be excluded from empirical
baseline summaries.
