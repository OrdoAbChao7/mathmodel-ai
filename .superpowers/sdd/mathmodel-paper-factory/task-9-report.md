# Task 9 report — blocked before production implementation

## Scope and source inspection

- Read `task-9-brief.md`, the approved plan and design, the current MathModel Skill/references, and the CLI contracts.
- Kept the existing solver, enhancer, numerical outputs, and `traning1/paper/main.tex` unchanged.
- The selected `traning1/paper/main38.tex` is an existing 38-page A4 PDF source.
- `main38.tex` enters `\begin{appendices}` directly after its references. Its existing AUX records the first appendix table (`tab:daily`, defined in `contents/appendix/a1.tex`) on page 17. The body material therefore ends no later than page 16.

## RED

Added `mathmodel-skill/tests/test_training1.py` before production changes. It executes the real CLI build against `traning1` and requires a PASS status, body pages >= 26, appendix/body ratio <= 0.25, question `q3`, all required figure roles, and no hard evidence failures.

Command:

```powershell
python -m unittest mathmodel-skill.tests.test_training1 -v
```

Result: expected failure (1 failure): `BUILD-CONFIG-001` reports the missing `traning1/mathmodel.json`.

## Blocking constraint

Adding a config, adapter, registries, and boundary labels cannot truthfully make this paper meet the required `body_pages >= 26`. Any label-only workaround would count appendix pages as body pages, contradicting the Task 9 brief, the Skill, and the page-boundary contract. Moving the appendix material into the body or rewriting the paper sections is required, but those files are outside the explicitly allowed ownership (`main38.tex` may only receive labels and registry references).

## Environment observations

- Real `xelatex`, `pdfinfo`, and `pdftoppm` are available.
- The default `python` lacks `scipy`; the bundled workspace Python has `scipy`, `openpyxl`, and `matplotlib`. This can support a real solver adapter if the paper-scope blocker is lifted.

## GREEN / verification

Not performed: proceeding would require either a fabricated body measurement or an out-of-scope rewrite. No controlled fake compiler is needed because a real XeLaTeX installation is available.
