# Task 5 pdfinfo decoding fix report

## Change

`measure_pdf()` now invokes `pdfinfo` with UTF-8 decoding and `errors="replace"`. It also normalizes byte, string, and `None` stdout/stderr values before parsing, and converts a residual `UnicodeDecodeError` into the structured pending `PDFINFO-001` result.

This prevents locale-dependent subprocess decoding from escaping the metrics contract while preserving ASCII `Pages:` and `Page size:` parsing.

## TDD evidence

RED command:

```powershell
python -m unittest mathmodel-skill.tests.test_latex_metrics -v
```

Initial result: failed with the expected unhandled cases:

```text
TypeError: cannot use a string pattern on a bytes-like object
UnicodeDecodeError: 'utf-8' codec can't decode byte 0xff ...
```

Added regression coverage for:

- byte output containing undecodable bytes, which is decoded with replacement while valid page evidence remains usable;
- `None` stdout/stderr, which returns a structured `FAILED`/`PDFINFO-003` result rather than raising;
- a direct `UnicodeDecodeError`, which returns a structured `PENDING`/`PDFINFO-001` result.

## Focused verification

Command:

```powershell
python -m unittest mathmodel-skill.tests.test_latex_metrics -v
```

Result: `Ran 25 tests ... OK`.

## Historical and complete verification

Commands:

```powershell
python -c "import json,sys; from pathlib import Path; sys.path.insert(0, 'mathmodel-skill/scripts'); from mmcore.pdfmetrics import measure_pdf; root=Path('traning1/paper'); print(json.dumps({'main': measure_pdf(root/'main.pdf', root/'main.aux'), 'main38': measure_pdf(root/'main38.pdf', root/'main38.aux')}, ensure_ascii=False, indent=2))"
python -m unittest discover -s mathmodel-skill/tests -v
```

Historical probe result:

- `main.pdf`: structured `FAILED` with `total_pages: 49`, `a4_status: PASS`, and `PDF-LABEL-001` for the absent six boundary labels.
- `main38.pdf`: structured `FAILED` with `total_pages: 38`, `a4_status: PASS`, and the same missing-label failure.

The decoding crash no longer occurs.

Complete suite result: `Ran 66 tests ... OK (skipped=1)`. The only skip is the known Windows symlink-permission case (`WinError 1314`).

No Git commit was created because this workspace is not a Git repository.
