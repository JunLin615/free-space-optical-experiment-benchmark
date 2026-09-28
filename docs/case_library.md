# Optional case/example library v1

The English example library is separate from canonical benchmark cases, gold,
fixtures, release evidence, and public development variants. Its index is
`benchmark/case_library/index.v1.json`, snapshot `optics-examples-v1`. Five
project-authored synthetic examples cover two-iris alignment, detector
linearity, reference-channel drift control, grating-order feasibility, and
spatial-filter alignment. They illustrate auxiliary reasoning rather than
copying benchmark answers. Each item has a stable ID, version, concept family,
optical domain, reasoning mode, difficulty, provenance/source type, relationship
to benchmark families, leakage-risk note, permitted protocols, path, and
content SHA-256. Content hashes make supplied examples auditable.

`tools.retrieval.retrieve` implements local `lexical_v1.0.0` retrieval. It
lowercases and tokenizes the query and examples, removes a fixed stop-word set,
scores query-term matches with a fixed document-frequency formula, and breaks
ties by item ID. It returns at most three examples and at most 900 estimated
tokens. The estimate counts lexical tokens, not provider-billed tokens. The
retrieval record contains the exact query and query hash, item IDs, scores,
item text and content hashes, count, estimated retrieved tokens, snapshot ID and
index hash,
retrieval version, and measured latency. The runner should persist the entire
record, including exact supplied text. A protocol without library access
cannot call retrieval. No model or paid embedding service is needed.

`python -m tools.case_library` verifies indexed paths and hashes and screens
for obvious leakage against canonical task text and public variant tasks. It
flags exact copies, high-overlap wording, trivial numeric renamings, reused
givens tuples, long verbatim answer-key passages, and exact numerical reference
quantities. The checker reads gold
only as an internal audit target; retrieval never reads or supplies gold.
This is a lexical safeguard, not a semantic-contamination proof. Related
concepts can legitimately occur in both collections, and paraphrased answer
keys could evade a simple lexical screen. Human review remains useful before
adding new library items, while normal evaluation and scoring require no
expert in the loop.

Version a changed example or retrieval rule, update the index hash and
snapshot/retrieval version, and preserve the old snapshot with any completed
run that used it. Do not silently overwrite completed baseline evidence.
