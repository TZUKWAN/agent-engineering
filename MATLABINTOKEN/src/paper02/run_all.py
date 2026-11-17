"""Run the full Paper 02 analysis pipeline."""
import subprocess
import sys
from pathlib import Path

scripts = [
    "01_classify_constraints.py",
    "02_quadratic.py",
    "03_subtype.py",
    "04_moderation.py",
    "05_robustness.py",
    "06_report.py",
]


def main():
    here = Path(__file__).parent
    for script in scripts:
        print(f"\n=== Running {script} ===")
        result = subprocess.run(
            [sys.executable, str(here / script)],
            cwd=here.parent.parent,
        )
        if result.returncode != 0:
            print(f"ERROR in {script} (exit {result.returncode})")
            sys.exit(result.returncode)
    print("\n=== Paper 02 pipeline complete ===")


if __name__ == "__main__":
    main()
