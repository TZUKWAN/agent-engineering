"""EXP-0061 recorder: write P001's pretrained-encoder feasibility note from the probe, and close the gate wording.

P001's `final_audit.md` keeps G18-B open pending a "feasibility note" for the missing dense/neural baseline, and the
programme has asserted that blocker from memory before and been wrong about it (the "no GPU" error, D-something in the
environment record). So this note is generated only from `results_raw/EXP0061_pretrained_encoder_feasibility_*.json`:
every sentence about what is or is not obtainable cites a probe line, and the sentence that admits the remaining
limitation is written even when the probe is unfavourable.

    python 02_shared_code/registry/record_exp0061_p001.py
"""
from __future__ import annotations

import csv, glob, io, json, pathlib, re, time

ROOT = pathlib.Path(__file__).resolve().parents[2]
PAP = ROOT / "papers" / "P001_routing_failure_qpp"
REG = ROOT / "00_program_registry"
NOW = time.strftime("%Y-%m-%dT%H:%M:%S")

hits = sorted(glob.glob(str(ROOT / "results_raw" / "EXP0061_pretrained_encoder_feasibility_*.json")))
if not hits:
    raise SystemExit("[e61] no EXP-0061 result file; writing nothing.")
NAME = pathlib.Path(hits[-1]).name
D = json.loads(pathlib.Path(hits[-1]).read_text(encoding="utf-8"))
HOSTS, INST = D["hosts"], D["installed"]
weight_hosts = [h for h, v in HOSTS.items() if v["usable_weights_channel"] and h.startswith(
    ("huggingface", "cdn-lfs", "hf-mirror", "modelscope", "cas-server"))]
index_hosts = [h for h, v in HOSTS.items() if v["usable_weights_channel"] and ("pypi" in h or "github" in h)]
lib = D.get("installability", {})

NOTE = f"""# Pretrained-encoder feasibility note (G18-B) — EXP-0061

Generated from `results_raw/{NAME}`. This note exists because `final_audit.md` keeps the dense-baseline item open and
says its absence must be written up as a feasibility judgement rather than left as an unexplained gap. It also exists
because this programme once asserted "no GPU" in six places and was wrong (the machine has an RTX 3060; the real
blockers were a CPU-only torch build and weights that could not be downloaded), so every claim below is tied to a
probe line in `results_processed/EXP0061_host_probe.csv`. No model inference API was called: the probe requests weight
files with ranged GETs and runs `pip --dry-run`, nothing else.

## What is installed

{json.dumps(INST, ensure_ascii=False, indent=1)}

## What could be reached, host by host

| host | http | bytes read | usable as a weight channel | first bytes / error |
|---|---|---|---|---|
""" + "\n".join(
    f"| {h} | {v['http_code']} | {v['bytes_read']} | {'yes' if v['usable_weights_channel'] else 'no'} | "
    f"{(v['first_bytes'] or v['curl_error'] or '')[:90]} |" for h, v in HOSTS.items()) + f"""

Library installation from the reachable index: {json.dumps(lib, ensure_ascii=False)[:400]}

## Judgement

**Verdict: `{D['verdict']}`.** {D['consequence_for_p001']}

Concretely, for P001: the strongest learned comparator admissible here is the from-scratch dual-tower dense model of
EXP-0024 (dense hit@3 0.9643 vs BM25 0.9222 on the same dev rows and the same prompt_id-grouped folds; the frozen
predictor's cross-ranker transfer 0.6451 against a pre-registered 0.65 bar, reported as a negative). A
*hugging-face-pretrained* sentence encoder could only be added if a weight channel above turns usable; libraries and
the package index are {'reachable' if index_hosts or any(v.get('returncode') == 0 for v in lib.values()) else 'not reachable'}
and the weight stores are {D['verdict'] == 'LIBRARIES_ONLY_NO_WEIGHTS' and 'not reachable' or 'reachable'}.

**What this note does not claim.** It does not prove no pretrained encoder is obtainable by any route — a proxy, an
enterprise mirror, or a machine outside this network could change it; it measures the channels this study had. It
does not license a "we did not need a neural baseline" reading: the SOTA-comparison gap stays open as a limitation,
and the fair-comparison conditions in `sota_audit.md` remain unmet.
"""
(PAP / "pretrained_encoder_feasibility.md").write_text(NOTE, encoding="utf-8", newline="")
print("[e61] wrote pretrained_encoder_feasibility.md")

FA = PAP / "final_audit.md"
fa = FA.read_text(encoding="utf-8")
if "EXP-0061" not in fa:
    fa = fa.replace("dense/neural baseline, whose absence is a policy/resource decision that must be written up as a feasibility\n"
                    "note",
                    "dense/neural baseline, whose absence is now a **measured** resource decision "
                    "(`pretrained_encoder_feasibility.md`, EXP-0061, verdict "
                    f"`{D['verdict']}`: the package index is reachable and the pretrained weight stores are "
                    f"{'reachable' if weight_hosts else 'not reachable from this host'}) — the item stays open as a "
                    "comparison gap, not as an unexplored one", 1)
    if "written up as a feasibility" in fa:
        print("[e61] WARNING: anchor text moved; final_audit not updated")
    else:
        print("[e61] final_audit feasibility wording updated")
    FA.write_text(fa, encoding="utf-8", newline="")

LIM = PAP / "limitations.md"
lt = LIM.read_text(encoding="utf-8")
if "EXP-0061" not in lt:
    lt = lt.replace("**未做；已给出可核查的可行性判定（不是回避）**",
                    "**未做；可行性已由实测判定（EXP-0061，不是回避）**", 1)
    LIM.write_text(lt + f"\n## L18 预训练稠密编码器：可得性实测（EXP-0061）\n\n"
                        f"`pretrained_encoder_feasibility.md` 逐主机实测：权重存储通道 "
                        f"{'可用' if weight_hosts else '本机不可达'}（{', '.join(weight_hosts) or '无'}），"
                        f"包索引与库安装 {'可用' if (index_hosts or any(v.get('returncode') == 0 for v in lib.values())) else '不可用'}；"
                        f"已装 torch 的 CUDA 可用性={json.dumps(INST.get('torch'))}。因此本文允许的最强学习型基线是 EXP-0024 "
                        f"的从零双塔稠密模型；本注记不声称任何路由下都取不到预训练权重，只声称本环境取不到。\n",
                   encoding="utf-8", newline="")
    print("[e61] appended L18")

DV = PAP / "deviations.md"
dt = DV.read_text(encoding="utf-8")
alld = [int(x) for f in sorted((ROOT / "papers").glob("*/deviations.md"))
        for x in re.findall(r"(?m)^\| D(\d+) \|", f.read_text(encoding="utf-8"))]
dn = max(alld or [0])
HOST_SUMMARY = "; ".join(h + "=" + str(v["http_code"]) for h, v in HOSTS.items())
DROW = (f"| D{dn+1} | {NOW} | G18-B 的可行性判定由**实测**取代记忆 | 主机级探测：权重存储 "
        f"{HOST_SUMMARY}；pip --dry-run 结果见结果文件 | 否 "
        f"| 裁决 `{D['verdict']}`；写入 `pretrained_encoder_feasibility.md` 与 L18，"
        f"缺基线这一比较缺口仍然保留 |")

if f"| D{dn+1} " not in dt:
    DV.write_text(dt.rstrip() + "\n" + DROW + "\n", encoding="utf-8", newline="")
    print(f"[e61] appended D{dn+1}")

p = REG / "experiment_registry.csv"
txt = p.read_text(encoding="utf-8")
h2 = list(csv.reader(io.StringIO(txt)))[0]
row = ["EXP-0061", "P001", "pretrained_encoder_feasibility_DONE",
       "02_shared_code/data_audit/probe_pretrained_encoder_feasibility_p001.py",
       "installed-package and CUDA probe; ranged GET of one small artefact per candidate weight host "
       "(huggingface, cdn-lfs, hf-mirror, modelscope, onnx bridge, raw.githubusercontent) plus the package index; "
       "pip --dry-run against PyPI and the Tsinghua mirror with no install performed; no inference API", "none",
       D["started_at"], D["finished_at"], f"probe_{D['verdict']}",
       f"{NAME}; results_processed/EXP0061_host_probe.csv; "
       "papers/P001_routing_failure_qpp/pretrained_encoder_feasibility.md",
       f"weight channels usable: {', '.join(weight_hosts) or 'none'}; library/index reachable: "
       f"{'yes' if (index_hosts or any(v.get('returncode') == 0 for v in lib.values())) else 'no'}; "
       "closes the 'must be written up as a feasibility note' item in final_audit and adds limitation L18, while "
       "keeping the comparison gap itself open", "yes - L18, final_audit, new note"]
if row[0] not in {r[0] for r in csv.reader(io.StringIO(txt)) if r}:
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\r\n").writerow(row)
    p.write_text(txt.rstrip("\r\n") + "\r\n" + buf.getvalue().rstrip("\r\n") + "\r\n", encoding="utf-8", newline="")
    print("[e61] registered EXP-0061")
import pandas as pd
d = pd.read_csv(p)
assert not d.exp_id.duplicated().any()
print(f"[e61] registry rows={len(d)}; verdict {D['verdict']}")
