# Real-case Training Protocol

This protocol is for the next agent and does not execute training or contain private case data.

## Private layout

Create local-only data outside the public skill and fixture trees:

```text
benchmarks-private/
└── cases/
    ├── case-01/
    │   ├── case.json
    │   ├── problem/
    │   └── oracle/
    └── ...

benchmark-workspaces/
└── <run-id>/
```

`benchmarks-private/` and `benchmark-workspaces/` are ignored by Git. Do not copy historical statements, attachments, reference papers, known solutions, or generated private outputs into `mathmodel-skill/`, `tests/fixtures/`, or the public `benchmarks/cases/` tree.

## Initial case contract

Use `benchmarks/templates/real-case/case.example.json` as the smallest stable metadata contract. Keep raw statements and official attachments under `problem/`; keep all evaluator-only material under `oracle/`.

## Stratified split

For approximately ten cases, begin with:

```text
6 TRAIN
2 VALIDATION
2 LOCKED HOLDOUT
```

Do not assign by random order alone. Stratify by problem type, year, data modality, difficulty, and whether the problem is single-stage or hybrid. Record the split in a private, versioned manifest before inspecting generated results. Once a split is fixed and results have been viewed, do not change it to improve a score.

## Isolation rules

The Solver may access only the problem statement, official attachments, and official data. Before candidate freeze it must not access:

- reference winning papers;
- known solutions or judge notes;
- award metadata;
- human failure analysis;
- previous generated solutions;
- holdout oracle, detailed evaluation, or candidate-vs-baseline comparison.

The Evaluator/Judge may access oracle material. If holdout results are viewed and the system is then changed, that case is no longer a valid locked holdout and must be reclassified.

## Future training loop

Do not implement this loop as part of handoff preparation. The incoming agent should eventually execute:

```text
real problem
↓
isolated solver workspace
↓
complete generated project/paper
↓
deterministic evaluation
↓
blind judge
↓
failure registry
↓
generalized fix
↓
regression test
↓
rerun train
↓
validation
↓
locked holdout
```

The first training object is the MathModel-AI system and its prompts/contracts/workflow, not bottom-level LLM parameters. With roughly ten cases, do not start a fine-tuning pipeline.

## Initial failure taxonomy

Future evaluator records should classify failures using one or more of:

```text
FRAMING
MODEL_SELECTION
DATA
MATH
VALIDATION
UNCERTAINTY
INNOVATION
EVIDENCE
WRITING
FIGURE
CITATION
ORCHESTRATION
TIME
```

No failure registry implementation is included in this handoff.
