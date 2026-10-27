#!/usr/bin/env python3
"""The tools' tests: python3 run_tests.py"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
failed = [t.name for t in sorted(ROOT.glob("tests/test_*.py"))
          if subprocess.run([sys.executable, str(t)], cwd=ROOT).returncode]
print(f"{len(failed)} failed", *failed)
sys.exit(1 if failed else 0)
