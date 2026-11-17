"""Run the full Paper 03 analysis pipeline in order."""
import subprocess
import sys
from pathlib import Path

scripts = [
    "01_lca.py",
    "02_profiles.py",
    "03_distribution.py",
    "04_outcomes.py",
    "05_controlled.py",
    "06_interaction.py",
    "07_paths.py",
    "08_report.py",
]


def main():
    here = Path(__file__).resolve().parent
    for script in scripts:
        print(f"\n{'='*60}\nRunning {script}\n{'='*60}")
        result = subprocess.run(
            [sys.executable, str(here / script)],
            cwd=here.parent.parent,
        )
        if result.returncode != 0:
            print(f"ERROR: {script} failed with exit code {result.returncode}")
            sys.exit(result.returncode)
    print("\nAll Paper 03 scripts completed successfully.")


if __name__ == "__main__":
    main()
