"""Minimal debug: convert first N lines only, with progress tracking."""
import sys, os, re

BASE = os.path.dirname(os.path.abspath(__file__))
INPUT = os.path.join(BASE, 'merged_report.md')

# Import all helpers from md2latex
sys.path.insert(0, BASE)
from md2latex import (
    convert_inline, is_table_sep, is_table_row,
    is_numbered_item, is_bullet_item, looks_like_ref, ref_key,
)

# Run convert function directly with progress
md = open(INPUT, encoding='utf-8').read()
lines = md.split('\n')
n = len(lines)
print(f"Total lines: {n}")

# Track every 100 lines
for i in range(0, n, 100):
    s = lines[i].strip()[:80]
    print(f"  Line {i}: {s}")

print("File scan complete — no hang during iteration")

# Now actually call convert in chunks to find where it hangs
print("\nNow testing convert()...")
sys.stdout.flush()

# Actually just import and call the main
from md2latex import convert, postprocess

try:
    print("Calling convert...")
    sys.stdout.flush()
    body = convert(md)
    print(f"Convert done: {len(body)} chars, {len(body.splitlines())} lines")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
