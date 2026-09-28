# Example-library and variant contamination audit

The optional v1 library contains five synthetic auxiliary examples. The
automated audit compared each one against all 64 canonical scientific tasks,
their stored answer-key passages and numeric references, and ten public
development variant tasks. A separate local dry run also supplied two
temporary private-variant tasks to the same audit without copying those tasks
or their seeds into the repository. All screens returned **zero findings** for
exact text copies, high lexical overlap, trivial numeric renamings, repeated
given tuples, long verbatim answer-key passages, and exact numeric answer keys.

Concept-family overlap is intentional and visible in
`benchmark/case_library/index.v1.json`: the examples relate broadly to
SEED-1 alignment, SEED-2 beam delivery, SEED-3 diffraction, and SEED-5
measurement/detection. The ten public variants explicitly share their
parent's concept family and much of its task structure; two were used as
public robustness probes. They are never described as hidden generalization
tests. Private seed material and generated private records stayed outside the
repository for the dry run; both private instances reproduced and their
internally reconstructed reference answers scored 1.0.

These lexical checks cannot rule out paraphrased solutions, prior model
training exposure, or semantic contamination. The current private-seed
interface can derive a private instance from a family with public siblings;
future truly hidden evaluations need a family-disjoint holdout policy and
additional scored families. Until then, hidden-seed infrastructure is a
portability and accidental-leakage demonstration, not an uncontaminated
generalization benchmark.
