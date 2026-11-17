"""Correct the environment claim repeated across P001: a GPU exists, but it is unusable for
dense encoders as installed. Verified by probing the interpreter, not by assumption.

Measured on 2026-09-18: system_info.json reports "NVIDIA GeForce RTX 3060, 12288 MiB", while
torch 2.5.1 is a CPU-only build (torch.cuda.is_available() -> False), sentence_transformers /
transformers / faiss are not installed, the HF hub cache is empty, and pretrained weights cannot be
downloaded here (EXP-0022). So the blocker is weights + build, not the absence of a GPU.
"""

from __future__ import annotations

import sys
from pathlib import Path

PAP = Path(__file__).resolve().parents[1]
FIX = {
    "final_audit.md": [
        ("Python 3.11.7, 16 logical CPUs, 31.9 GB RAM, GPU \"none, analysis is CPU-only\"",
         "Python 3.11.7, 16 logical CPUs, 31.9 GB RAM, GPU RTX 3060 12 GB present but the installed "
         "torch 2.5.1 is a CPU-only build, so the analysis is CPU-only in practice (corrected 2026-09-18; "
         "this row previously said \"GPU none\", which was wrong)"),
        ("during analysis) plus no GPU on this machine; it needs an explicit feasibility note, not silence.",
         "during analysis), an unusable GPU for this purpose (RTX 3060 present, torch is a CPU-only build, "
         "encoder libraries absent) and no downloadable pretrained weights. The corrected note with the "
         "feasible alternative (a from-scratch two-tower dense baseline, E03b) is in L6."),
    ],
    "appendix.md": [
        ("CPU-only; no GPU, no API calls, no token spend by construction.",
         "CPU-only in practice: an RTX 3060 is present but the installed torch is a CPU-only build and no "
         "encoder library or pretrained weights are available offline. No API calls, no token spend."),
    ],
    "sota_audit.md": [
        ("✕ 我们无 GPU 训练", "✕ 我们的环境无可用稠密编码器（torch 为 CPU-only 构建、无权重可下载）"),
        ("✕ 我们无 LLM、无稠密编码器、无 GPU 训练",
         "✕ 我们无 LLM、无稠密编码器（GPU 存在但 torch 为 CPU-only 构建，且预训练权重不可下载）"),
        ("✕ **无法运行**：禁 API 且无 GPU。已明确记为缺失项",
         "✕ **无法按同等条件运行**：禁调用推理 API；本机虽有 RTX 3060 但 torch 为 CPU-only 构建、"
         "无 sentence_transformers/faiss，且预训练权重不可下载。已明确记为缺失项（L6 给出可行的替代路线 E03b）"),
    ],
    "research_plan.md": [
        ("CPU only（无 GPU、无 API）", "CPU only（无 API；GPU 存在但 torch 为 CPU-only 构建，实际仍只能 CPU 运行）"),
    ],
}
for fname, pairs in FIX.items():
    p = PAP / fname
    t = p.read_text(encoding="utf-8")
    for old, new in pairs:
        if old in t:
            t = t.replace(old, new)
            print(f"fixed in {fname}: {old[:40]}...")
        elif new[:30] not in t:
            print(f"MISS in {fname}: {old[:60]}")
    p.write_text(t, encoding="utf-8")
print("environment claims corrected")
