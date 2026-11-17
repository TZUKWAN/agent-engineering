"""Scratch: how recoverable are the tool names and the think/body split in the Hermes traces?

The wave-4 premise census must not report a prevalence it failed to measure, so this counts what the parser can and
cannot resolve before any gate is evaluated.
"""
import collections
import glob
import json
import pathlib
import re

import pandas as pd

C = pathlib.Path(r"G:\刘俊琦\AGENT ENGINEERING\MATLABINTOKEN\datasets\lambda\hermes-agent-reasoning-traces")
TOK_IN = re.compile("<<""tool_call>>""(.*?)<<" + "/tool_call>>", re.S)
THINK = re.compile("<<""think>>""(.*?)<<" + "/think>>", re.S)

df = pd.read_parquet(sorted(glob.glob(str(C / "data" / "*.parquet")))[0], columns=["conversations"]).head(400)
names = collections.Counter()
name_by_json = 0
obs_blocks = unparsed = 0
bodies = []
for row in df["conversations"]:
    for m in [dict(x) for x in row]:
        role = m.get("from")
        v = str(m.get("value"))
        if role == "tool":
            blocks = TOK_IN.findall(v)
            obs_blocks += len(blocks)
            for b in blocks:
                try:
                    names[str(json.loads(b).get("name"))] += 1
                    name_by_json += 1
                except Exception:                                  # noqa: BLE001 - record, do not guess
                    unparsed += 1
        elif role == "gpt":
            bodies.append(len(THINK.sub("", v).strip()))
print("observation blocks:", obs_blocks, "named:", sum(names.values()), "unparsed:", unparsed)
print("coverage of named calls:", round(name_by_json / max(1, obs_blocks), 4))
print("top tools:", names.most_common(10))
print("gpt messages:", len(bodies), "mean body chars:", round(sum(bodies) / max(1, len(bodies)), 1))
for thr in (5, 20, 60):
    n = sum(1 for b in bodies if b < thr)
    print(f"  bodies under {thr} chars: {n} ({n / max(1, len(bodies)):.3f})")
