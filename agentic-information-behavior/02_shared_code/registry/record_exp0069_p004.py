"""EXP-0069 recorder: add the anchored P004 collisions to its matrix, and register the amendment that made them visible.

The frozen EXP-0057 screen gave P004 167 L2+ hits, of which a read sample contained none. The model-produced-text
anchor cut that to 9, and every one of the 7 readable survivors that was sampled is an LLM-as-a-judge study. Those 9
are what this recorder appends; the 158 demoted records stay in the anchored file with both levels recorded, so the
narrowing is auditable rather than a filtered-away inconvenience.

    python 02_shared_code/registry/record_exp0069_p004.py
"""
from __future__ import annotations

import csv, glob, io, json, pathlib, re, time

ROOT = pathlib.Path(__file__).resolve().parents[2]
PAP = ROOT / "papers" / "P004_shipped_quality_score_validity"
REG = ROOT / "00_program_registry"
NOW = time.strftime("%Y-%m-%dT%H:%M:%S")
hits = sorted(glob.glob(str(ROOT / "results_raw" / "EXP0069_p004_anchored_screen_*.json")))
if not hits:
    raise SystemExit("[e69] no EXP-0069 summary; writing nothing.")
S = json.loads(pathlib.Path(hits[-1]).read_text(encoding="utf-8"))
ANCH = REG / S["out"]
rows = list(csv.DictReader(io.StringIO(ANCH.read_text(encoding="utf-8"))))
survivors = [r for r in rows if r["passes_anchor"] == "1"]

MTX = PAP / "literature_matrix.csv"
m = list(csv.reader(io.StringIO(MTX.read_text(encoding="utf-8"))))
hdr, body = m[0], [r for r in m[1:] if r]
have = {re.sub(r"\s+", " ", (r[3] or "").lower()).strip() for r in body}
added = []
for r in sorted(survivors, key=lambda x: (x["level_frozen_rule"] != "L3", x["title"])):
    t = re.sub(r"\s+", " ", r["title"].lower()).strip()
    if t in have:
        continue
    matched = json.loads(r["matched"])
    hit_txt = "; ".join(f"{k}:{','.join(v[:3])}" for k, v in matched.items() if v)
    ck = (r["doi"] or r["url"]).split("/")[-1][:34] + "|" + re.sub(r"[^A-Za-z]", "", r["title"].split()[0])[:12]
    body.append([ck, r["year"], r["venue"][:60], r["title"][:160],
                 "LLM-as-a-judge evaluation study surfaced by the EXP-0069 anchored screen; not yet read for this paper",
                 "", "", "", "", f"{hit_txt} | anchors: {r['anchor_hits'][:120]}",
                 r["level_frozen_rule"] + " (frozen rule + model-produced-text anchor, unverified)", "", r["url"],
                 time.strftime("%Y-%m-%d"), "pending_hand_check", "P004",
                 "empty on purpose: differentiation is written after the abstract is read, not from a screen"])
    added.append(r)
buf = io.StringIO()
w = csv.writer(buf, lineterminator="\r\n")
w.writerow(hdr)
w.writerows(body)
MTX.write_text(buf.getvalue(), encoding="utf-8", newline="")
print(f"[e69] matrix {len(body)} rows; {len(added)} anchored collisions appended")

NB = PAP / "novelty_audit.md"
nb = NB.read_text(encoding="utf-8")
BG = PAP / "literature_background.md"
if BG.exists() and "EXP-0069" not in BG.read_text(encoding="utf-8"):
    BG.write_text(BG.read_text(encoding="utf-8").rstrip() + f"""

## Superseded in part by EXP-0069

The "NOT met" line above describes the **frozen** screen alone. EXP-0069 added a strictly narrower, demote-only
model-produced-text anchor on top of it, which cut {S['frozen_L2plus']} L2+ hits to {S['survived_anchor']} and produced
a sample whose readable members were all on-topic; {len(added)} records were appended to the matrix on that basis. See
`novelty_audit.md` (anchored collision screen) and the registered deviation for the amendment and its direction.
""", encoding="utf-8", newline="")
    print("[e69] literature_background.md annotated")
if "EXP-0069" not in nb:
    NB.write_text(nb.rstrip() + f"""

## Anchored collision screen (EXP-0068 + EXP-0069, {time.strftime('%Y-%m-%d')})

A query battery generated from this paper's own term families surfaced {S['records']} new records. The frozen EXP-0057
rule placed {S['frozen_L2plus']} of them at L2+, but reading a random sample of 12 found **none** of them about an
automatic score attached to model-produced text: they were clinical, psychometric, educational and engineering
scale-validation studies, matched because this paper's object family contains the bare words `rating`, `score`, `label`
and `judge`. That count was therefore not usable as a directly-relevant tally, and it was not used.

A second, strictly narrower criterion was then added: a candidate must also mention a model-produced-text anchor (one of
{len(S['anchor_terms'])} phrases listed in `02_shared_code/literature/anchor_screen_p004.py`). It cut
{S['frozen_L2plus']} to **{S['survived_anchor']}**, removing {S['removed_by_anchor']} records, and a read sample of
{S['survivors_readable']} readable survivors found every one of them to be an LLM-as-a-judge or model-evaluation study.
The {len(added)} new records were appended to `literature_matrix.csv` marked `pending_hand_check` with empty
`differentiation` cells; the demoted records remain in `{ANCH.name}` with both levels stored, so nothing was deleted.

**Why this is an amendment and not a repair.** The anchor is a new criterion introduced after the false-positive rate
was seen, so it is registered as a deviation rather than folded silently into the method. It can only demote a frozen
grade, never promote one, and `grade_collisions.py` was left byte-identical so every earlier grade and `level_final`
still means what it meant when it was written. Its effect on this paper's novelty position is to make the claim
*narrower*: the directly relevant set is larger than the pre-expansion count and each addition is a study this paper
must differentiate itself from.
""", encoding="utf-8", newline="")
    print("[e69] novelty_audit anchored-screen section appended")

DV = PAP / "deviations.md"
dt = DV.read_text(encoding="utf-8")
alld = [int(x) for f in sorted((ROOT / "papers").glob("*/deviations.md"))
        for x in re.findall(r"(?m)^\| D(\d+) \|", f.read_text(encoding="utf-8"))]
dn = max(alld or [0])
SUBJ = "P004 撞题筛选加入「模型生成文本」锚点：在看过假阳性率之后新增的更严判据"
if SUBJ not in dt:
    DV.write_text(dt.rstrip() + f"""
| D{dn+1} | {NOW} | {SUBJ} | 冻结规则给出 {S['frozen_L2plus']} 条 L2+，随机抽 12 条读后 0 条与本文对象相关（多为临床/心理量表效度研究）；加入锚点后剩 {S['survived_anchor']} 条，可读的 {S['survivors_readable']} 条抽样全部为 LLM 评审研究；锚点只能降级不能升级，`grade_collisions.py` 保持逐字不变，被降级的 {S['removed_by_anchor']} 条连同两个等级一并保留 | 是（新增判据，且在看到结果之后） | 已写入 novelty_audit 的锚点筛选小节；本文直接相关文献数由 17 增至 {17 + len(added)}，且每条都需在阅读后补写差异声明；未据此改动任何统计判据或主结果 |""",
                    encoding="utf-8", newline="")
    print(f"[e69] D{dn+1} appended")

p = REG / "experiment_registry.csv"
t = p.read_text(encoding="utf-8")
have_ids = {r[0] for r in csv.reader(io.StringIO(t)) if r}
if "EXP-0069" not in have_ids:
    row = ["EXP-0069", "P004", "success_ANCHORED_SCREEN_167_TO_9_PRECISION_7_OF_7",
           "02_shared_code/literature/anchor_screen_p004.py",
           "model-produced-text anchor applied AFTER the frozen EXP-0057 grade (demote-only); 20 anchor phrases fixed "
           "in the script; both levels stored per record; seed-11 sample of readable survivors read in full",
           "seed 11 (precision sample)", S["at"], S["at"],
           f"frozen L2+ {S['frozen_L2plus']} -> anchored survivors {S['survived_anchor']} "
           f"(removed {S['removed_by_anchor']}); sampled readable {S['survivors_readable']} all on-topic",
           f"{ANCH.name}; {pathlib.Path(hits[-1]).name}; papers/P004_shipped_quality_score_validity/novelty_audit.md",
           f"{len(added)} records appended to the curated matrix as pending_hand_check; registered as a post-hoc "
           "amendment (deviation) because the criterion was added after the false-positive rate was observed",
           "yes - novelty_audit, deviations, matrix"]
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\r\n").writerow(row)
    p.write_text(t.rstrip("\r\n") + "\r\n" + buf.getvalue().rstrip("\r\n") + "\r\n", encoding="utf-8", newline="")
    print("[e69] registered EXP-0069")
import pandas as pd
d = pd.read_csv(p)
assert not d.exp_id.duplicated().any()
print(f"[e69] registry rows={len(d)}; appended={len(added)}; survivors={len(survivors)}")
