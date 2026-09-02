"""Cross-platform controlled fake compiler: forwards to analysis/run.py --compile."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

if __name__ == "__main__":
    completed = subprocess.run(
        [sys.executable, str(ROOT / "analysis" / "run.py"), "--compile", *sys.argv[1:]],
        cwd=str(ROOT),
    )
    raise SystemExit(completed.returncode)
