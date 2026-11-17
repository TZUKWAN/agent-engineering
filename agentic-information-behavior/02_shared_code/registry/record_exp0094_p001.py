"""EXP-0094 recorder: the external test that EXP-0086 said was the only one left, and what it returned.

EXP-0086 could not claim anything because two of the frozen model's inputs are functions of catalogue size and the
ToolRet pool was 1,000x the dev pool. EXP-0094 keeps the queries, the golds, the model, the features, the bands and
the support gate unchanged and resamples each row's candidate pool from the empirical dev size distribution. The
support gate then passes (0.9514 in support, 51 positives / 693 negatives) and the frozen model scores 0.8028
(CI 0.7254-0.868) against a 0.65 transfer band and a 0.7137 length-only baseline.

The claim that can be carried is narrower than "the model transfers to ToolRet", and it is written that way: the
construct transfers on external queries and gold labels at dev-comparable pool scale; the native 44,452-document
task remains untested and is untestable with this feature set. Both sentences go in together.

    python record_exp0094_p001.py
"""
from __future__ import annotations

import csv, io, json, pathlib, re, sys, time

ROOT = next(a for a in [pathlib.Path(__file__).resolve().parent, *pathlib.Path(__file__).resolve().parents]
            if (a / "00_program_registry").is_dir())
P = ROOT / "papers" / "P001_routing_failure_qpp"
NOW = time.strftime("%Y-%m-%dT%H:%M:%S")


def line(r):
    b = io.StringIO(); csv.writer(b, lineterminator="\r\n").writerows([r]); return b.getvalue()


def sub1(text, pat, repl, tag, marker=None, flags=re.S):
    if marker and marker in text:
        print(f"  [{tag}] already applied - skipped")
        return text
    n = len(re.findall(pat, text, flags))
    if n != 1:
        raise SystemExit(f"ABORT [{tag}]: matched {n}x: {pat[:70]!r}")
    print(f"  [{tag}] applied")
    return re.sub(pat, repl, text, count=1, flags=flags)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    f = sorted((ROOT / "results_raw").glob("EXP0094_size_matched_external_*.json"))[-1]
    d = json.loads(f.read_text(encoding="utf-8"))
    S, A = d["support"], {a["arm"]: a for a in d["arms"]}
    import pandas as pd
    n_feat = len(pd.read_csv(ROOT / "results_processed" / "EXP0094_per_feature_support.csv"))
    f86 = sorted((ROOT / "results_raw").glob("EXP0086_support_respecting_external_*.json"))[-1]
    E86 = json.loads(f86.read_text(encoding="utf-8"))
    NATIVE_POOL = int(round(E86["sample"]["mean_n_candidates"]))
    NATIVE_ROWS = int(E86["support"]["rows"])
    NATIVE_INSUPPORT = int(E86["support"]["in_support_rows"])
    pf86 = pd.read_csv(ROOT / "results_processed" / "EXP0086_per_feature_support.csv")
    NATIVE_OUTSIDE = int((pf86.share_rows_outside >= 0.999).sum())
    frozen, base = A["frozen probability"], A["length-only baseline"]
    band = max((k for k, v in d["bands"].items() if frozen["auroc_in_support"] >= v),
               key=lambda k: d["bands"][k], default=None)
    if frozen["auroc_in_support"] is None:
        raise SystemExit("ABORT: the support gate did not pass on the matched rows - there is no verdict to record")
    if frozen["auroc_in_support"] <= base["auroc_in_support"]:
        raise SystemExit("ABORT: the model does not beat the length-only baseline, so 'transfers' cannot be written")

    doc = f"""# The external test at dev-comparable pool scale (EXP-0094): it transfers, within a stated scope

Artefact `{f.name}`; code `02_shared_code/statistics/toolret_size_matched_external_p001.py`; seed {d['seed']};
{d['wallclock_sec']}s; {d['sample']['rows_built']} ToolRet eval queries. Pre-declared rule in the module docstring,
support gate reused verbatim from EXP-0086.

## What was changed, and what was not

Only the candidate pool. Queries, gold labels, the union tool corpus, the frozen model, the {n_feat}
frozen features, the bands (0.55 / 0.65) and the support gate ({d['pre_declared_rule'].split('(')[0].strip()}) are
unchanged, and nothing is refitted on external data. Each row's pool is drawn from the empirical dev
`n_candidates` distribution (dev median {d['dev_pool_size_median']}, range
{d['dev_pool_size_range'][0]}-{d['dev_pool_size_range'][1]}), always including that query's golds; external pool
sizes came out with median {d['external_pool_size_median']}. BM25 statistics are computed inside each pool, which is
how the dev rows were built, so the retrieval construct is matched as well as the size.

## Result

| quantity | value |
|---|---|
| rows | {S['rows']} (positives in support {S['positives_in_support']}, negatives {S['negatives_in_support']}) |
| in-support fraction | **{S['in_support_fraction']}** (EXP-0086 at native pool size: 0.0) |
| fail@3 prevalence, external vs dev | {d['sample']['fail_at_3_prevalence_external']} vs {d['sample']['fail_at_3_prevalence_dev']} |
| mean chance hit@3 in these pools | {d['sample']['chance_hit_3_mean']} |
| frozen model AUROC (in-support) | **{frozen['auroc_in_support']}** (CI {frozen['ci95_in_support']}) |
| same weights, link removed | {A['linear predictor (no link)']['auroc_in_support']} (CI {A['linear predictor (no link)']['ci95_in_support']}) |
| length-only baseline | {base['auroc_in_support']} (CI {base['ci95_in_support']}) |
| frozen band | {d['bands']} |
| verdict on the pre-declared rule | band `{band}`, and above the length-only baseline by {round(frozen['auroc_in_support'] - base['auroc_in_support'], 4)} |

The CI lower bound ({frozen['ci95_in_support'][0]}) is above the 0.65 transfer band, so the band is met at the
interval level and not only at the point estimate - the failure mode that demoted EXP-0082's 0.6536.

## What this does and does not establish

1. **Established:** the frozen pre-retrieval construct predicts BM25 failure on an *independent* benchmark -
   different queries, different tool pool, different release - when the candidate set is the size the model was
   trained to see. It is not a within-Toucan number: the queries and gold labels are ToolRet's.
2. **Not established:** transfer at ToolRet's native scale. On the full 44,452-document pool the model's inputs are
   out of support (EXP-0086), so no statement either way is admissible there, and the positive result here must
   never be quoted as if it covered that regime.
3. **Regime check passed and is reported as a condition, not a footnote:** external fail@3 prevalence
   {d['sample']['fail_at_3_prevalence_external']} against dev {d['sample']['fail_at_3_prevalence_dev']} means the
   matched pools reproduce the difficulty the model was fitted on. Chance hit@3 in these pools is
   {d['sample']['chance_hit_3_mean']}, so the base rate is high and the AUROC, not accuracy, is the quantity.
4. **The positives are {S['positives_in_support']}**, which is why the interval is {frozen['ci95_in_support']} wide;
   the criterion is a lower bound on that interval and it clears 0.65, but a reviewer should read this as a
   first positive external test rather than a precise effect size.
5. Nothing here touches P001's single-use test evaluation; every number is from dev rows and the external release.

## How the programme got here

EXP-0081 probed which acquisition channels work; EXP-0082 measured transfer on the mined-negative training
partition; EXP-0083 ingested the eval release; EXP-0084 scored it and read below-chance; EXP-0085 showed the
probability had saturated so that reading was invalid; EXP-0086 replaced the verdict with a support measurement and
found 0 of 419 rows in support, naming the size-matched design as the only remaining test; EXP-0094 ran it. The
gate moves from OPEN to PASS-with-scope on the strength of the last step, and the native-scale gap stays written down
in limitations as an open scope limit rather than a resolved one.
"""
    (P / "external_size_matched_exp0094.md").write_text(doc, encoding="utf-8", newline="")
    if re.search(r"\bNone\b|\bnan\b|\{[a-z_]+\}", doc):
        raise SystemExit("ABORT: generated document carries an unresolved value")
    print(f"  wrote external_size_matched_exp0094.md ({len(doc.split())} words)")

    cp = P / "claims_evidence_matrix.csv"
    rows = [r for r in csv.reader(io.StringIO(cp.read_text(encoding="utf-8"))) if r]
    hdr, body = rows[0], rows[1:]
    if "C29" not in {r[0] for r in body}:
        body.append(["C29",
                     "在把候选池规模匹配到 dev 分布后，冻结模型在 ToolRet 的独立查询与金标注上给出 in-support AUROC "
                     f"{frozen['auroc_in_support']}（CI {frozen['ci95_in_support']}），高于 0.65 迁移带下界且优于长度基线 "
                     f"{base['auroc_in_support']}：该构造在同等池规模下迁移；原生 44,452 文档池仍不可测（EXP-0086），"
                     "本结论不外推到原生规模",
                     "外部效度（E08 第四次尝试）", "EXP-0094", "supports (within stated scope)",
                     f"rows={S['rows']} pos_in_support={S['positives_in_support']} in_support_fraction="
                     f"{S['in_support_fraction']} auroc={frozen['auroc_in_support']} ci={frozen['ci95_in_support']} "
                     f"length_only={base['auroc_in_support']} prev_ext={d['sample']['fail_at_3_prevalence_external']} "
                     f"prev_dev={d['sample']['fail_at_3_prevalence_dev']} chance_hit3={d['sample']['chance_hit_3_mean']}",
                     "results_processed/EXP0094_per_feature_support.csv",
                     "papers/P001_routing_failure_qpp/external_size_matched_exp0094.md",
                     "prompt_id 聚类自助 2000 次；支持域判据与 0.55/0.65 带在算 AUROC 前固定且未放宽",
                     f"results_raw/{f.name}", "6.4; limitations L24; final_audit 外部验证行", "supported"])
        assert all(len(r) == len(hdr) for r in body), "claims row width"
        cp.write_text("".join(line(x) for x in [hdr] + body), encoding="utf-8", newline="")
        print(f"  claims matrix: now {len(body)} rows")

    fa = P / "final_audit.md"
    t = fa.read_text(encoding="utf-8")
    t = sub1(t, r"\| cross-dataset external validation \|[^\n]*\n",
             "| cross-dataset external validation | **PASS at dev-comparable pool scale (EXP-0094); native scale "
             "untestable (EXP-0086)** | on ToolRet queries and gold labels with pools drawn from the dev size "
             f"distribution, the frozen model reaches in-support AUROC {frozen['auroc_in_support']} "
             f"(CI {frozen['ci95_in_support']}) against a 0.65 band and a {base['auroc_in_support']} length-only "
             f"baseline, with prevalence {d['sample']['fail_at_3_prevalence_external']} vs dev "
             f"{d['sample']['fail_at_3_prevalence_dev']}; at the native 44,452-document pool two frozen inputs are "
             "out of support on every row, so that regime is reported as untested, not as failure. "
             "`external_size_matched_exp0094.md`, C29, C27, L24 |\n",
             "external gate row", marker="PASS at dev-comparable pool scale")
    fa.write_text(t, encoding="utf-8", newline="")

    lim = P / "limitations.md"
    t = lim.read_text(encoding="utf-8")
    if "Resolved in part by EXP-0094" in t:
        print("  [L24 resolution] already applied - skipped")
    else:
        # L24 is the last section, so the resolution is appended under it rather than pattern-matched into the middle:
        # four headings in this file begin with 外部验证 and a `## L\d+ 外部验证` regex is ambiguous by construction.
        last = re.findall(r"^## (L\d+) ", t, re.M)[-1]   # the section this note is appended to
        t = t.rstrip() + "\n\n" + (
            "**Resolved in part by EXP-0094, and the scope limit is now stated precisely.** Re-drawing "
            f"each row's candidate pool from the dev size distribution puts {S['in_support_fraction']} of rows in "
            f"support ({S['positives_in_support']} positives, {S['negatives_in_support']} negatives) and the frozen "
            f"model scores in-support AUROC {frozen['auroc_in_support']} (CI {frozen['ci95_in_support']}) against the "
            f"0.65 band, above the length-only baseline ({base['auroc_in_support']}), with external prevalence "
            f"{d['sample']['fail_at_3_prevalence_external']} against dev {d['sample']['fail_at_3_prevalence_dev']}. "
            "So the construct transfers at the scale the model was fitted to; it remains untested - not failed, "
            "untestable with this feature set - at ToolRet's native 44,452-document scale. `external_size_matched_"
            "exp0094.md`, C29.\n")
        lim.write_text(t, encoding="utf-8", newline="")
        print(f"  [L24 resolution] appended under {last}")

    # ---- paper.md: the §7.6 clause "no external benchmark host was reachable" is now false, and §7.6 must point at
    # what the acquired benchmark actually said. P001's manuscript is patched by recorders with exact-text anchors
    # (the established pattern for this paper), so both edits are count-guarded and marker-keyed.
    pm = P / "paper.md"
    t = pm.read_text(encoding="utf-8")
    if "EXP-0094" not in t:
        t = sub1(t, r"and no external benchmark host was reachable from the analysis environment",
                 "and no external benchmark host was reachable when that run was written - ToolRet has since been "
                 "acquired over the channel EXP-0081 verified, and §7.6a reports what it says about transfer",
                 "paper 7.6 reachability clause")
        anchor = "## 7.7 E03b"
        t = sub1(t, re.escape(anchor) + r"[^\n]*\n",
                 f"""### 7.6a External benchmark, at matched and at native pool scale (EXP-0086, EXP-0094)

ToolRet's eval release gives {d['sample']['rows_built']} external queries whose gold tools resolve inside a
{NATIVE_POOL:,}-document union catalogue.
Scored on that native pool the frozen model's inputs are **outside the development support on every row** - {NATIVE_OUTSIDE} of the
{n_feat} features are functions of catalogue size, and the dev catalogues hold {int(d['dev_pool_size_range'][0])}-
{int(d['dev_pool_size_range'][1])} tools against {NATIVE_POOL:,} - so the
pre-registered rule (in-support fraction >= 0.25 with >= 30 positives) returns *not testable* - {NATIVE_ROWS} rows,
{NATIVE_INSUPPORT} in support - and neither transfer nor non-transfer may be claimed there (EXP-0086). Re-drawing each row's candidate pool from the empirical dev size
distribution, with the queries, golds, model, features, bands and support rule unchanged, puts
**{S['in_support_fraction']}** of rows in support ({S['positives_in_support']} positives,
{S['negatives_in_support']} negatives) and the frozen model reaches AUROC **{frozen['auroc_in_support']}**
(clustered CI {frozen['ci95_in_support']}), above the {base['auroc_in_support']} length-only baseline and above the
0.65 transfer band at the interval level, with external fail@3 prevalence
{d['sample']['fail_at_3_prevalence_external']} against {d['sample']['fail_at_3_prevalence_dev']} in dev (EXP-0094).
So the construct does transfer to an independent benchmark - but only at the candidate-set scale it was fitted for,
and the native-scale question is open, not answered negatively ({NATIVE_OUTSIDE} pool-size features are exactly why).
{S['positives_in_support']} positives is why the
interval is {frozen['ci95_in_support'][1] - frozen['ci95_in_support'][0]:.3f} wide; this is a first positive external
test, not a precise effect size.

""" + anchor + "\n",
                 "paper 7.6a insertion")
        pm.write_text(t, encoding="utf-8", newline="")
        print("  paper.md: reachability clause corrected and section 7.6a added")

    dv = P / "deviations.md"
    t = dv.read_text(encoding="utf-8")
    if "EXP-0094" not in t:
        used = {int(x) for x in re.findall(r"^\| D(\d+) \|", t, re.M)}
        for g in (ROOT / "papers").glob("*/deviations.md"):
            if g != dv:
                used |= {int(x) for x in re.findall(r"^\| D(\d+) \|", g.read_text(encoding="utf-8"), re.M)}
        did = max(used | {0}) + 1
        t = t.rstrip() + "\n" + (
            f"| D{did} | {NOW} | 外部验证改在「池规模匹配 dev 分布」的候选池上重做（EXP-0094），并把结论限定在该规模 | "
            f"EXP-0086 显示原生池下 {S['rows']} 行全部越出支持域，因两个池规模特征使然；不重做就永远停在「不可测」。"
            f"匹配后 in-support {S['in_support_fraction']}，AUROC {frozen['auroc_in_support']}"
            f"（CI {frozen['ci95_in_support']}）>0.65 且高于长度基线 {base['auroc_in_support']} | "
            "是（新增 C29；外部门槛行改为「同等规模 PASS、原生规模不可测」；L24 补记） | "
            "未改判据、模型、特征、带值，未在外部数据上重拟合；原生规模的空缺保留为范围限制而非已解决 |\n")
        dv.write_text(t, encoding="utf-8", newline="")
        print(f"  deviations: appended D{did}")

    rp = ROOT / "00_program_registry" / "experiment_registry.csv"
    rrows = [r for r in csv.reader(io.StringIO(rp.read_text(encoding="utf-8"))) if r]
    rhdr, rbody = rrows[0], rrows[1:]
    if "EXP-0094" not in {r[0] for r in rbody}:
        rec = dict.fromkeys(rhdr, "")
        rec.update({"exp_id": "EXP-0094", "paper_id": "P001", "topic_id": "T001",
                    "stage": "e08_size_matched_external_test",
                    "script": "02_shared_code/statistics/toolret_size_matched_external_p001.py",
                    "config": "ToolRet eval queries and gold labels unchanged; each row's candidate pool resampled "
                              f"from the empirical dev n_candidates distribution (dev median "
                              f"{d['dev_pool_size_median']}, range {d['dev_pool_size_range'][0]}-"
                              f"{d['dev_pool_size_range'][1]}), golds always included, BM25 statistics computed "
                              "inside each pool as in dev; identical dev-fitted frozen model and feature list, "
                              "nothing refitted; support gate and 0.55/0.65 bands reused verbatim from EXP-0086",
                    "seed": str(d["seed"]), "started_at": d["started_at"], "finished_at": NOW,
                    "status": f"TRANSFERS within scope: in-support {S['in_support_fraction']}, AUROC "
                              f"{frozen['auroc_in_support']} CI {frozen['ci95_in_support']} vs length-only "
                              f"{base['auroc_in_support']}; native scale still untestable (EXP-0086)",
                    "outputs": f"results_raw/{f.name}; results_processed/EXP0094_per_feature_support.csv; "
                               "papers/P001_routing_failure_qpp/external_size_matched_exp0094.md",
                    "notes": "the follow-up experiment EXP-0086 named; prevalence external "
                             f"{d['sample']['fail_at_3_prevalence_external']} vs dev "
                             f"{d['sample']['fail_at_3_prevalence_dev']}; the claim is bounded to dev-comparable "
                             "pool scale and must not be quoted for ToolRet's native pool",
                    "enters_paper": "yes - claim C29, limitations L24, final_audit external-validation row"})
        rbody.append([rec[x] for x in rhdr])
        rp.write_text("".join(line(x) for x in [rhdr] + rbody), encoding="utf-8", newline="")
        print("  registry: EXP-0094 added")
    chk = [r for r in csv.reader(io.StringIO(rp.read_text(encoding="utf-8"))) if r]
    print(f"  registry rows={len(chk) - 1} ragged={sum(1 for r in chk[1:] if len(r) != len(chk[0]))}")

    sh = P / "reproduce.sh"
    s = sh.read_text(encoding="utf-8")
    if "EXP-0094" not in s:
        anchor = '  echo "[repro] 14 SKIPPED: no feature cache. Build it with the same command (it writes the cache itself)."\nfi\n'
        if s.count(anchor) != 1:
            raise SystemExit(f"ABORT: reproduce.sh anchor matched {s.count(anchor)}x")
        s = s.replace(anchor, anchor + '''
echo "[repro] 15/15 E08 size-matched external test (EXP-0094): the transfer result, and the reason it is scoped"
# Needs the ToolRet eval release and the 44,452-document union corpus on disk; the pool sizes are resampled from the
# dev rows, so no other input changes. Without the corpus the step says SKIPPED rather than reusing a stale verdict.
if [ -d "${AIB_TOOLRET_DIR:-01_datasets/raw/mangopy}" ] || [ -n "${AIB_TOOLRET_DIR:-}" ]; then
  "$PY" 02_shared_code/statistics/toolret_size_matched_external_p001.py --rows 800
  "$PY" 02_shared_code/registry/record_exp0094_p001.py
else
  echo "[repro] 15 SKIPPED: set AIB_TOOLRET_DIR to the local ToolRet release directory to rebuild EXP-0094"
fi
''')
        sh.write_text(s, encoding="utf-8", newline="")
        print("  reproduce.sh: EXP-0094 step added")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
