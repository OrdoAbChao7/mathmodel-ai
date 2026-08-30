# Task 2 implementation report

## Scope

Implemented only the Task 2 files:

- `mathmodel-skill/scripts/mmcore/scaffold.py`
- `mathmodel-skill/scripts/mathmodel.py`
- `mathmodel-skill/assets/project-template/paper/main.tex`
- `mathmodel-skill/assets/project-template/mathmodel.json`
- `mathmodel-skill/tests/test_scaffold.py`

The implementation provides non-overwriting `init_project` and `adopt_project` scaffolding, the `init` and `adopt` CLI commands, a valid Task 1 configuration template, a minimal boundary-labelled paper template, and a non-solving analysis adapter placeholder.

## RED — required first test run

Command:

```text
python -m unittest discover -s mathmodel-skill/tests -p 'test_scaffold.py' -v
```

Exact output:

```text
test_scaffold (unittest.loader._FailedTest.test_scaffold) ... ERROR

======================================================================
ERROR: test_scaffold (unittest.loader._FailedTest.test_scaffold)
----------------------------------------------------------------------
ImportError: Failed to import test module: test_scaffold
Traceback (most recent call last):
  File "C:\Users\32583\AppData\Local\Programs\Python\Python313\Lib\unittest\loader.py", line 396, in _find_test_path
    module = self._get_module_from_name(name)
  File "C:\Users\32583\AppData\Local\Programs\Python\Python313\Lib\unittest\loader.py", line 339, in _find_test_path
    __import__(name)
  File "E:\Projects\school\mathmodel\mathmodel-skill\tests\test_scaffold.py", line 14, in <module>
    from mmcore.scaffold import adopt_project, init_project
ModuleNotFoundError: No module named 'mmcore.scaffold'

----------------------------------------------------------------------
Ran 1 test in 0.000s

FAILED (errors=1)
```

## GREEN — focused suite

Command:

```text
python -m unittest discover -s mathmodel-skill/tests -p 'test_scaffold.py' -v
```

Exact output:

```text
test_adopt_does_not_replace_existing_configuration (test_scaffold.ScaffoldTests.test_adopt_does_not_replace_existing_configuration) ... ok
test_adopt_preserves_existing_paper_and_solver (test_scaffold.ScaffoldTests.test_adopt_preserves_existing_paper_and_solver) ... ok
test_cli_dispatches_init_and_adopt (test_scaffold.ScaffoldTests.test_cli_dispatches_init_and_adopt) ... ok
test_init_creates_contract_and_required_directories (test_scaffold.ScaffoldTests.test_init_creates_contract_and_required_directories) ... ok
test_init_never_overwrites_existing_file (test_scaffold.ScaffoldTests.test_init_never_overwrites_existing_file) ... ok

----------------------------------------------------------------------
Ran 5 tests in 0.115s

OK
```

## GREEN — complete suite

Command:

```text
python -m unittest discover -s mathmodel-skill/tests -v
```

Exact output:

```text
test_load_config_accepts_minimal_valid_contract (test_config.ConfigTests.test_load_config_accepts_minimal_valid_contract) ... ok
test_main_help_returns_zero (test_config.ConfigTests.test_main_help_returns_zero) ... ok
test_rejects_appendix_ratio_above_one (test_config.ConfigTests.test_rejects_appendix_ratio_above_one) ... ok
test_rejects_path_escape (test_config.ConfigTests.test_rejects_path_escape) ... ok
test_adopt_does_not_replace_existing_configuration (test_scaffold.ScaffoldTests.test_adopt_does_not_replace_existing_configuration) ... ok
test_adopt_preserves_existing_paper_and_solver (test_scaffold.ScaffoldTests.test_adopt_preserves_existing_paper_and_solver) ... ok
test_cli_dispatches_init_and_adopt (test_scaffold.ScaffoldTests.test_cli_dispatches_init_and_adopt) ... ok
test_init_creates_contract_and_required_directories (test_scaffold.ScaffoldTests.test_init_creates_contract_and_required_directories) ... ok
test_init_never_overwrites_existing_file (test_scaffold.ScaffoldTests.test_init_never_overwrites_existing_file) ... ok

----------------------------------------------------------------------
Ran 9 tests in 0.125s

OK
usage: mathmodel [-h] {init,adopt} ...

positional arguments:
  {init,adopt}

options:
  -h, --help    show this help message and exit
```

## Commit status

No Git repository exists at `E:\Projects\school\mathmodel` or its parents; no commit was created.

## Concerns

None blocking Task 2. The analysis adapter intentionally exits with a clear message and does not fabricate results, as required.

## Fix round 1 report

### RED — review-fix tests before implementation

Command:

```text
python -m unittest discover -s mathmodel-skill/tests -p 'test_scaffold.py' -v
```

Exact output:

```text
test_adopt_does_not_replace_existing_configuration (test_scaffold.ScaffoldTests.test_adopt_does_not_replace_existing_configuration) ... ok
test_adopt_preserves_existing_paper_and_solver (test_scaffold.ScaffoldTests.test_adopt_preserves_existing_paper_and_solver) ... ok
test_adoption_report_categorizes_files_and_lists_framework_conflicts (test_scaffold.ScaffoldTests.test_adoption_report_categorizes_files_and_lists_framework_conflicts) ... ERROR
test_cli_dispatches_init_and_adopt (test_scaffold.ScaffoldTests.test_cli_dispatches_init_and_adopt) ... ok
test_cli_rejects_invalid_problem_type_cleanly (test_scaffold.ScaffoldTests.test_cli_rejects_invalid_problem_type_cleanly) ... ERROR
test_init_creates_contract_and_required_directories (test_scaffold.ScaffoldTests.test_init_creates_contract_and_required_directories) ... ok
test_init_never_overwrites_existing_file (test_scaffold.ScaffoldTests.test_init_never_overwrites_existing_file) ... ok
test_paper_template_has_executable_boundary_labels_and_clearpages (test_scaffold.ScaffoldTests.test_paper_template_has_executable_boundary_labels_and_clearpages) ... FAIL

======================================================================
ERROR: test_adoption_report_categorizes_files_and_lists_framework_conflicts (test_scaffold.ScaffoldTests.test_adoption_report_categorizes_files_and_lists_framework_conflicts)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "E:\Projects\school\mathmodel\mathmodel-skill\tests\test_scaffold.py", line 82, in test_adoption_report_categorizes_files_and_lists_framework_conflicts
    self.assertEqual(report["statements"], ["problem/statement.pdf"])
                     ~~~~~~^^^^^^^^^^^^^^
KeyError: 'statements'

======================================================================
ERROR: test_cli_rejects_invalid_problem_type_cleanly (test_scaffold.ScaffoldTests.test_cli_rejects_invalid_problem_type_cleanly)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "E:\Projects\school\mathmodel\mathmodel-skill\tests\test_scaffold.py", line 107, in test_cli_rejects_invalid_problem_type_cleanly
    main(["init", str(self.root), "--id", "bad-001", "--title", "Bad", "--type", "unknown"]),
    ~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "E:\Projects\school\mathmodel\mathmodel-skill\scripts\mathmodel.py", line 26, in main
    init_project(args.target, args.id, args.title, args.problem_type)
    ~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "E:\Projects\school\mathmodel\mathmodel-skill\scripts\mmcore\scaffold.py", line 73, in init_project
    raise ValueError(f"unsupported problem type: {problem_type}")
ValueError: unsupported problem type: unknown

======================================================================
FAIL: test_paper_template_has_executable_boundary_labels_and_clearpages (test_scaffold.ScaffoldTests.test_paper_template_has_executable_boundary_labels_and_clearpages)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "E:\Projects\school\mathmodel\mathmodel-skill\tests\test_scaffold.py", line 59, in test_paper_template_has_executable_boundary_labels_and_clearpages
    self.assertIn(rf"\\label{{{label}}}", template)
    ~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: '\\label{mm:body-start}' not found in '\\documentclass[UTF8,a4paper]{ctexart}\\n\\usepackage{geometry}\\n\\geometry{margin=2.5cm}\\n\\title{��ѧ��ģ����}\\n\\author{��ģС��}\\n\\date{}\\n\\n\\begin{document}\\n\\maketitle\\n\\begin{abstract}\\n���ĸ�������Ľ�ģ����������֤���̡�ժҪ���ݽ��ں��������в��䡣\\n\\end{abstract}\\n\\n% mm:body-start\\n\\section{��������}\\n�����䡣\\n\\section{ģ�ͽ��������}\\n�����䡣\\n\\section{ģ�ͷ�������֤}\\n�����䡣\\n% mm:body-end\\n\\n% mm:appendix-start\\n\\appendix\\n\\section{��¼}\\n�����䡣\\n% mm:appendix-end\\n\\end{document}\\n'

----------------------------------------------------------------------
Ran 8 tests in 0.153s

FAILED (failures=1, errors=2)
```

### GREEN — focused suite after fixes

Command:

```text
python -m unittest discover -s mathmodel-skill/tests -p 'test_scaffold.py' -v
```

Exact output:

```text
test_adopt_does_not_replace_existing_configuration (test_scaffold.ScaffoldTests.test_adopt_does_not_replace_existing_configuration) ... ok
test_adopt_preserves_existing_paper_and_solver (test_scaffold.ScaffoldTests.test_adopt_preserves_existing_paper_and_solver) ... ok
test_adoption_report_categorizes_files_and_lists_framework_conflicts (test_scaffold.ScaffoldTests.test_adoption_report_categorizes_files_and_lists_framework_conflicts) ... ok
test_cli_dispatches_init_and_adopt (test_scaffold.ScaffoldTests.test_cli_dispatches_init_and_adopt) ... ok
test_cli_rejects_invalid_problem_type_cleanly (test_scaffold.ScaffoldTests.test_cli_rejects_invalid_problem_type_cleanly) ... error: unsupported problem type: unknown
ok
test_init_creates_contract_and_required_directories (test_scaffold.ScaffoldTests.test_init_creates_contract_and_required_directories) ... ok
test_init_never_overwrites_existing_file (test_scaffold.ScaffoldTests.test_init_never_overwrites_existing_file) ... ok
test_paper_template_has_executable_boundary_labels_and_clearpages (test_scaffold.ScaffoldTests.test_paper_template_has_executable_boundary_labels_and_clearpages) ... ok

----------------------------------------------------------------------
Ran 8 tests in 0.155s

OK
```

### GREEN — complete suite after fixes

Command:

```text
python -m unittest discover -s mathmodel-skill/tests -v
```

Exact output:

```text
test_load_config_accepts_minimal_valid_contract (test_config.ConfigTests.test_load_config_accepts_minimal_valid_contract) ... ok
test_main_help_returns_zero (test_config.ConfigTests.test_main_help_returns_zero) ... ok
test_rejects_appendix_ratio_above_one (test_config.ConfigTests.test_rejects_appendix_ratio_above_one) ... ok
test_rejects_path_escape (test_config.ConfigTests.test_rejects_path_escape) ... ok
test_adopt_does_not_replace_existing_configuration (test_scaffold.ScaffoldTests.test_adopt_does_not_replace_existing_configuration) ... ok
test_adopt_preserves_existing_paper_and_solver (test_scaffold.ScaffoldTests.test_adopt_preserves_existing_paper_and_solver) ... ok
test_adoption_report_categorizes_files_and_lists_framework_conflicts (test_scaffold.ScaffoldTests.test_adoption_report_categorizes_files_and_lists_framework_conflicts) ... ok
test_cli_dispatches_init_and_adopt (test_scaffold.ScaffoldTests.test_cli_dispatches_init_and_adopt) ... ok
test_cli_rejects_invalid_problem_type_cleanly (test_scaffold.ScaffoldTests.test_cli_rejects_invalid_problem_type_cleanly) ... error: unsupported problem type: unknown
ok
test_init_creates_contract_and_required_directories (test_scaffold.ScaffoldTests.test_init_creates_contract_and_required_directories) ... ok
test_init_never_overwrites_existing_file (test_scaffold.ScaffoldTests.test_init_never_overwrites_existing_file) ... ok
test_paper_template_has_executable_boundary_labels_and_clearpages (test_scaffold.ScaffoldTests.test_paper_template_has_executable_boundary_labels_and_clearpages) ... ok

----------------------------------------------------------------------
Ran 12 tests in 0.161s

OK
usage: mathmodel [-h] {init,adopt} ...

positional arguments:
  {init,adopt}

options:
  -h, --help    show this help message and exit
```

Fix-round concerns: none blocking. The report now contains `statements`, `attachments`, `papers`, `scripts`, and `conflicts` as project-relative lists; adoption snapshots pre-existing framework paths for conflicts and preserves all existing files. The paper template emits executable labels with clear-page boundaries.
