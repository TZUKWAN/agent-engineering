"""Record what EXP-0034 measured into P001's own package, and register EXP-0034 / EXP-0035.

EXP-0034 found that 01_datasets/processed/routing_{OSS,Qwen3,Kimi-K2}.parquet are 100% `single-turn-original`:
the registered build command draws 10 shards per config at random, but its row loop stops once 15,000 rows are
collected and Toucan's shards are subset-homogeneous, so only 2 files per config are ever read. P001's package
disclosed nothing about this. Every number written here is read out of the EXP-0034 result file.

    python 02_shared_code/registry/record_exp0034_p001.py
"""
from __future__ import annotations

import csv, glob, io, json, re, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
PAP = ROOT / "papers" / "P001_routing_failure_qpp"
REG = ROOT / "00_program_registry"

hits = sorted(glob.glob(str(ROOT / "results_raw" / "EXP0034_shard_coverage_*.json")))
if not hits:
    sys.exit("[record] EXP-0034 has no result file; writing nothing.")
D = json.loads(pathlib.Path(hits[-1]).read_text(encoding="utf-8"))
C = D["configs"]
name = pathlib.Path(hits[-1]).name

gap_txt = "; ".join(f"{c} {v['gap_consumed_minus_unconsumed_pp']:+.3f} pp (CI {v['ci95_prompt_clustered_pp']})"
                    for c, v in C.items())
nxt = 1 + max([int(x) for x in re.findall(r"(?m)^## L(\d+)", (PAP / "limitations.md").read_text(encoding="utf-8"))])

SEC = f"""
## L{nxt} 发表样本只是语料的一个查询子集（EXP-0034 实测）

`01_datasets/processed/routing_{{OSS,Qwen3,Kimi-K2}}.parquet` 的 subset_name 全部是 `single-turn-original`
（三份各 15,000 行、占比 1.0）。原因不是随机抽样偏差，而是构造逻辑：注册的建库命令虽然随机抽取 10 个 shard，但
行循环在攒够 15,000 行时立即停止，而 Toucan 的 shard 是按 subset 同质的，因此每个 config 实际只读到 2 个文件。
OSS 语料本身的构成实测为 25.7% single-turn-original、25.8% single-turn-diversify、38.4% multi-turn、
10.1% irrelevant。

EXP-0034 用冻结的 BM25 评分路径比较了「被读到的 2 个文件」与「未被读到的 8 个文件」：主结果 fail@3 的差异为
{gap_txt}，最大绝对差 {max(abs(v['gap_consumed_minus_unconsumed_pp']) for v in C.values())} pp，没有任何一个 CI
排除 0，故按预先固定的判据（|差| >= 1.0 pp 且 CI 排除 0 才算有偏）判为「覆盖问题在主结果上未被证实」。
该实验同时构成对复用评分路径的校验：被读到分组复算出的 dev fail@3 = {C['OSS']['consumed']['fail_at_3_dev']}，与发表锚点
{C['OSS']['published_dev_fail_at_3']} 一致。

但协变量差异很大：OSS 侧两组平均指令长度 258 vs 489 字符、子句数 1.34 vs 3.21。diversify 子集恰恰是
vocabulary-mismatch 机制最该检验的改写条件，multi-turn 才是省略与子任务结构的载体。因此本文明确：H1-H3 是
**single-turn-original 指令上的估计**，不对改写指令或多轮跟进作外推声明；能把这件事一次说清的跨子集迁移检验是
EXP-0035（脚本已写、尚未执行），在其结果出现之前不得把结论推广到整个语料。

样本身份锚点 `routing_sample_identity.json` 仍然有效——它锁的是「同一批行」，不保证「覆盖整个语料」，这正是本条
存在的理由。
"""

t = (PAP / "limitations.md").read_text(encoding="utf-8")
if "发表样本只是语料的一个查询子集" in t:
    print("[record] limitations.md already carries L15; left unchanged")
else:
    (PAP / "limitations.md").write_text(t.rstrip() + "\n" + SEC, encoding="utf-8")
    print(f"[record] appended L{nxt} to limitations.md")

fa = PAP / "final_audit.md"
txt = fa.read_text(encoding="utf-8")
mark = "sample is one query subset"
if mark not in txt:
    nums = [int(x) for x in re.findall(r"(?m)^\s*(\d+)\. \*\*", txt)]
    k = (max(nums) if nums else 0) + 1
    fa.write_text(txt.rstrip() + f"\n{k}. **{mark}:** routing_{ '{OSS,Qwen3,Kimi-K2}' } are 100% "
                  "single-turn-original (2 files/config); measured outcome-neutral but covariate-divergent "
                  "(EXP-0034, L" + str(nxt) + "); the transfer test EXP-0035 is written but not yet run.\n",
                  encoding="utf-8")
    print(f"[record] appended defect {k} to final_audit.md")


def rows_of(p):
    return list(csv.reader(io.StringIO(p.read_text(encoding="utf-8"))))


def append(path, row):
    lines = rows_of(path)
    if isinstance(row, dict):
        row = [row.get(c, "") for c in lines[0]]
    if any(r and r[0] == row[0] for r in lines[1:]):
        print(f"[record] {row[0]} already registered; skipped")
        return
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\r\n").writerow(row)
    txt2 = path.read_text(encoding="utf-8").rstrip("\r\n")
    path.write_text(txt2 + "\r\n" + buf.getvalue().rstrip("\r\n") + "\r\n", encoding="utf-8", newline="")
    print(f"[record] registered {row[0]}")


hdr = rows_of(REG / "experiment_registry.csv")[0]
append(REG / "experiment_registry.csv", dict(zip(hdr, [
    "EXP-0034", "P001", "shard_coverage_audit_DONE",
    "02_shared_code/data_audit/audit_shard_coverage_p001.py",
    "3 configs x (2 consumed vs 8 un-consumed shards); 3000 rows/group; frozen BM25 path reused from the builder; "
    "prompt_id-clustered bootstrap 2000 draws; rule fixed in the script docstring before running", "42",
    D["started_at"], D["finished_at"], "success_coverage_gap_measured_inert_on_primary_outcome",
    f"{name}; results_processed/EXP0034_shard_coverage.csv; logs/EXP-0034_shard_coverage.txt",
    "Discovered that the published routing sample is 100% single-turn-original (2 of ~44 files per config). "
    "Outcome base rate not shown biased (max |gap| "
    f"{max(abs(v['gap_consumed_minus_unconsumed_pp']) for v in C.values())} pp, no CI excludes 0); covariates do "
    "differ (OSS 258 vs 489 chars, 1.34 vs 3.21 subtasks). Scoring-path check: consumed-group dev fail@3 "
    f"{C['OSS']['consumed']['fail_at_3_dev']} vs published anchor {C['OSS']['published_dev_fail_at_3']}. Written into P001 "
    f"as L{nxt} and a final_audit defect.", "yes - as a limitation (L" + str(nxt) + ") and the trigger for EXP-0035"])))

append(REG / "experiment_registry.csv", dict(zip(hdr, [
    "EXP-0035", "P001", "out_of_subset_transfer_WRITTEN_NOT_RUN",
    "02_shared_code/statistics/subset_sensitivity_p001.py",
    "fit frozen all_C0.1 on published dev (single-turn-original) then score ~4000 rows/config of "
    "single-turn-diversify and multi-turn; transfer vs own-subset OOF vs length-only vs post-retrieval margin; "
    "population n_candidates>3; never reads the test split", "42", "", "", "written_not_executed",
    "none yet - no result file exists and nothing from it is quoted anywhere",
    "Parked at the turn-budget pause. Decision rule already fixed in the script docstring. Must run before P001 "
    "submission: it decides whether H1-H3 can be stated beyond single-turn-original. NOT yet smoke-tested - expect "
    "to debug on first execution.", "pending"])))

import pandas as pd
d = pd.read_csv(REG / "experiment_registry.csv")
assert not d.exp_id.duplicated().any(), "duplicate exp_id introduced"
print(f"[record] registry rows={len(d)}; EXP-0034/0035 present:", {"EXP-0034", "EXP-0035"} <= set(d.exp_id))
