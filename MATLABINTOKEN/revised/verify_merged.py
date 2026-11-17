#!/usr/bin/env python
"""Verify merged_report.md structure."""
import os, re

path = 'merged_report.md'
size_kb = os.path.getsize(path) // 1024
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

lines = content.split('\n')
print(f'Total lines: {len(lines)}')
print(f'File size: {size_kb}KB')
print()

# Count heading levels
for level in range(1, 5):
    pattern = '#' * level + ' '
    count = len([l for l in lines if l.startswith(pattern)])
    print(f'  h{level} ({"#" * level} ): {count}')

# Count images
img_count = len(re.findall(r'!\[.*?\]\(.*?\.png\)', content))
print(f'Image references: {img_count}')

# Show first 35 lines
print()
print('=== First 35 lines ===')
for i, line in enumerate(lines[:35]):
    print(f'{i+1:3d}: {line[:120]}')

# Show chapter headings (h1)
print()
print('=== Chapter Headings (h1) ===')
for i, line in enumerate(lines):
    if line.startswith('# ') and not line.startswith('## '):
        print(f'  Line {i+1}: {line}')

# Check for residual issues
issues = []
if 'paper01_figures/' in content:
    issues.append('paper01_figures/ path still present')
if 'paper02_figures/' in content:
    issues.append('paper02_figures/ path still present')
if 'paper03_figures/' in content:
    issues.append('paper03_figures/ path still present')
if issues:
    print()
    print('=== Residual Issues ===')
    for iss in issues:
        print(f'  WARNING: {iss}')
else:
    print()
    print('No residual path issues found.')
