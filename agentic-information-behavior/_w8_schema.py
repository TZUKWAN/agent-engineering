"""Scratch: what does the hermes release actually carry, and what does wave 4's turn matrix already give wave 8?

Wave 8's five designs need four things from this substrate: a hypothesis statement early in a trajectory, a turn that
ends the search, a plan whose specificity can be counted, and an explicit self-correction. Whether a task *outcome*
exists at all decides whether the premature-versus-over-search design can be measured or has to be reported as
blocked, so that is what this looks for first. Nothing here measures an association.
"""
import glob
import pathlib

import pandas as pd

import sys

sys.path.insert(0, "02_shared_code/package_factory")
import wave_lib as W                                              # noqa: E402
import exp_wave4_features as EF                                   # noqa: E402

C = pathlib.Path(str(W.ROOT.parent) + "/MATLABINTOKEN/datasets/lambda/hermes-agent-reasoning-traces")
files = sorted(glob.glob(str(C / "data" / "**" / "*.parquet"), recursive=True))
print("parquet files:", len(files))
for f in files[:4]:
    print("   ", pathlib.Path(f).relative_to(C), pathlib.Path(f).stat().st_size)

d = pd.read_parquet(files[0])
print("\ncolumns:", list(d.columns), d.shape)
r = d.iloc[0]
for c in d.columns:
    print("  ", c, "=", str(r[c])[:150].replace("\n", " "))

cand = [c for c in d.columns if any(k in c.lower() for k in
                                    ("solv", "succ", "correct", "reward", "fail", "result", "exit", "label",
                                     "score", "pass", "termin", "finish", "status"))]
print("\ncolumns that could carry an outcome:", cand)
for c in cand:
    print("   ", c, "nunique", d[c].nunique(), "values", list(pd.Series(d[c]).dropna().unique())[:6])

msgs = list(r["conversations"]) if r["conversations"] is not None else []
print("\nconversation length:", len(msgs), "item keys:", list(dict(msgs[0]).keys()) if msgs else None)
print("roles in order:", [str(m["from"]) for m in msgs][:16])
for m in msgs[:6]:
    print("   ", str(m["from"]), "|", str(m["value"])[:170].replace("\n", " "))

print("\n--- wave-4 turn matrix ---")
import gzip
p = W.ROOT / "results_processed" / "EXP0153_wave4_step_features.csv.gz"
if not p.is_file():
    hits = sorted((W.ROOT / "results_processed").glob("EXP015*_wave4*.csv.gz"))
    p = hits[0] if hits else None
print("matrix file:", p)
if p:
    M = pd.read_csv(gzip.open(p, "rt", encoding="utf-8"), nrows=5)
    print("columns:", list(M.columns))
    print("rows:", sum(1 for _ in gzip.open(p, "rt")) - 1)
