# Free-Space Optical Experiment Reasoning Benchmark (working title)

This project is being designed as an **autonomous-agent benchmark** for free-space optical experimental reasoning: prediction, design, diagnosis, calibration, and physically justified trade-offs. It is intended to compare language-model agents, retrieval-assisted agents, tool-using agents, optical-design agents, and future scientific systems against the same scientific questions. It is independent of any particular agent or optical software.

**Current status: research and design, not a released benchmark.** The repository contains an untouched 64-case HTML seed and English-first design documents. The seed is not yet a machine-scoreable test set. We are not adding or translating cases in this round.

The design goal is that a normal run can be executed and scored **without human expert grading**. Proposed scoring combines unit-aware numeric checks, executable optical physics, structured constraints for alternative valid designs, and calibrated model judges for bounded semantic claims. Cases without reliable autonomous evaluation will be redesigned or held outside the scored release.

Start with [the benchmark design](docs/benchmark_design.md), [evaluation design](docs/evaluation_design.md), [case schema proposal](docs/case_schema_proposal.md), [automated case validation](docs/automated_validation_design.md), [research landscape](docs/research/benchmark_landscape.md), [seed audit](docs/research/seed_audit.md), and [roadmap](docs/project_roadmap.md).

The optional optical case/example library is separate from benchmark questions and gold specifications. Planned protocols compare closed-book, case-assisted, tool-assisted, and combined access under declared budgets and frozen versions.

Project name, license, scored case set, and public release version are still open decisions. See the roadmap for release gates.
