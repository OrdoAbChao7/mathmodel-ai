# Task 1 Fix Review — Round 1

## Scope

This re-review covers only finding S1 from `task-1-review.md`: `main(["--help"])` must return integer `0` rather than raising `SystemExit`, and a focused regression test must cover that behavior. I also checked for Critical or Important regressions in the changed fix lines.

## Verdict

- S1: **ADDRESSED**
- New Critical/Important issue in fix scope: **None found**

## Evidence

`mathmodel-skill/scripts/mathmodel.py` now constructs `ArgumentParser` with `add_help=False`, registers an explicit `--help`/`-h` boolean option, prints help when requested, and returns `0`. This prevents argparse's automatic help action from terminating the direct function call with `SystemExit`.

`mathmodel-skill/tests/test_config.py` adds the focused regression test:

```python
def test_main_help_returns_zero(self):
    self.assertEqual(main(["--help"]), 0)
```

The test is meaningful because it exercises the exact previously failing direct-call contract and asserts the integer result.

## Fresh verification

Focused command:

```powershell
python -m unittest discover -s mathmodel-skill/tests -p 'test_config.py' -v
```

Result:

```text
Ran 4 tests in 0.013s
OK
TEST_EXIT_CODE=0
```

The four passing tests include `test_main_help_returns_zero` and the three original configuration/path tests.

Direct behavior probe:

```text
HELP_RESULT_TYPE=int
HELP_RESULT=0
UNKNOWN_RESULT=2
PROBE_EXIT_CODE=0
```

This confirms no `SystemExit` is raised for the direct help call and that the existing unimplemented-command error path still returns `2`.

Complete discovered suite:

```powershell
python -m unittest discover -s mathmodel-skill/tests -v
```

Result:

```text
Ran 4 tests in 0.012s
OK
TEST_EXIT_CODE=0
```

## Regression assessment

The changed parser setup preserves the intended `--help` and `-h` behavior, keeps no-command help returning `0`, and leaves unknown commands returning `2`. No new Critical or Important issue was found within the fix scope.

## Review conclusion

S1 is addressed. The implementer report's appended fix evidence is consistent with the current source and tests.
