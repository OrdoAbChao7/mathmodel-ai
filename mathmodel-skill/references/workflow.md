# Workflow

1. Preserve original statements and raw attachments; record every input path in `mathmodel.json`.
2. Run `inspect PROJECT --json`; read the data audit and run manifest before choosing a model.
3. Map every question to an objective, inputs, output, assumptions, candidate method, chosen method, validation, and paper section.
4. Implement problem-specific analysis under `analysis/`; use argument arrays, fixed seeds where randomness applies, and generated outputs only.
5. Populate registries before drafting strong conclusions. Run `build PROJECT --json` after analysis or LaTeX changes.
6. Read the quality report, logs, and page metrics; repair root causes, then run `audit PROJECT --json` after editorial revisions.
7. Preserve failed logs and manifests. Do not overwrite raw inputs, invent missing data, or treat an old report as current evidence.

Use `init` only for a new project and `adopt` only to add framework metadata to an existing project. Resolve a missing dependency, failed analysis, broken contract, or failed LaTeX pass before advancing dependent stages.
