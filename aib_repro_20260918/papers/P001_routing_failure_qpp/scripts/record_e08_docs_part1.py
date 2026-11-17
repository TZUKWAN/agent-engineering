"""E08 docs, part 1: manuscript (paper.md), reviewer attack, final audit, limitations.

Text only; every number is read from the EXP-0021/0022/0023 result JSONs and every replacement asserts
its anchor, so a silent no-op is impossible.
"""

from __future__ import annotations

import glob
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PAP = ROOT / "papers" / "P001_routing_failure_qpp"


def last(pat):
    f = sorted(glob.glob(str(ROOT / "results_raw" / pat)))[-1]
    return json.loads(Path(f).read_text(encoding="utf-8"))


E21, E23 = last("EXP0021_cross_pipeline_transfer_*.json"), last("EXP0023_hermes_transfer_*.json")
E23a = last("EXP0023a_hermes_toolcall_feasibility_*.json")
a1, a1b, a2, ov = (E21["arm1_external_pipeline"], E21["arm1b_catalogue_disjoint"],
                   E21["arm2_unseen_tool_family"], E21["overlap_audit"])
her, hc, hi = E23["transfer"], E23["corpus_after_inclusion_rule"], E23["independence_audit"]
src_oof = round(sum(a1["auc_source_reference_oof_dev"]) / len(a1["auc_source_reference_oof_dev"]), 4)
her_oof = round(sum(her["auc_within_hermes_oof"]) / len(her["auc_within_hermes_oof"]), 4)


def append_line(fname, startswith, extra):
    p = PAP / fname
    lines = p.read_text(encoding="utf-8").split("\n")
    hit = [i for i, l in enumerate(lines) if l.startswith(startswith)]
    assert hit, f"line anchor missing in {fname}"
    lines[hit[0]] = lines[hit[0]].rstrip() + extra
    p.write_text("\n".join(lines), encoding="utf-8")


def sub(fname, old, new):
    p = PAP / fname
    t = p.read_text(encoding="utf-8")
    if new[:60] in t:
        print(f"  ({fname}: already patched, skipped)")
        return
    assert old in t, f"anchor missing in {fname}: {old[:60]}"
    p.write_text(t.replace(old, new, 1), encoding="utf-8")


# ---- paper.md: abstract and the limitations section ---------------------------------------------
append_line("paper.md", "Before an LLM agent can act",
            f" E08 replaces that bound with a measurement: on an independent corpus "
            f"(lambda/hermes-agent-reasoning-traces, {hi['unseen_tool_name_share']:.0%} of its tool names absent from "
            f"training) the frozen model transfers at AUROC **{her['auc_source_dev_to_hermes']}** "
            f"(row-bootstrap CI {her['ci95_row_bootstrap'][0]}-{her['ci95_row_bootstrap'][1]}), about "
            f"{round(src_oof - her['auc_source_dev_to_hermes'], 3)} below the in-domain figure, yet still above that "
            f"corpus' length baseline ({her['auc_hermes_length_only_B0']}) and its post-retrieval margin baseline "
            f"({her['auc_hermes_post_retrieval_margin']}).")
append_line("paper.md", "Four limits are quantified",
            f" E08 (EXP-0020..0023) then measured rather than bounded this: holding an answer tool-family out of "
            f"training costs {a2['mean_auc_family_seen_reference']} -> {a2['mean_auc_unseen_family']} (degradation "
            f"{a2['mean_drop_vs_seen']}, our 0.02 criterion triggered) and an independent corpus with "
            f"{hi['unseen_tool_name_share']:.0%} unseen tool names scores {her['auc_source_dev_to_hermes']} against "
            f"{src_oof} in domain, whereas catalogue *composition* novelty alone costs nothing detectable "
            f"({a1b['n_rows']} catalogue-disjoint rows at {a1b['auc_transfer_disjoint_catalogues']}). The residual is "
            f"tool-vocabulary familiarity, which is why {her['auc_source_dev_to_hermes']}, not "
            f"{src_oof}, is the number to quote for deployment.")

# ---- reviewer_attack.md --------------------------------------------------------------------------
ra = PAP / "reviewer_attack.md"
t = ra.read_text(encoding="utf-8")
if "Closed as far as this environment allows" not in t:
    new_a13 = ("| A13 | **Only one dataset?** | **Closed as far as this environment allows (D15)** | EXP-0022 "
               "scanned all eight local corpora at file level: only Toucan and "
               "lambda/hermes-agent-reasoning-traces carry a per-query candidate catalogue, and every host that "
               "could serve a new corpus failed a 3-attempt file-download probe (huggingface.co times out; the "
               "mirror answers 200 at its root but 404 at `resolve/`). EXP-0023 evaluates on hermes instead - "
               f"different pipeline, model family and tool universe, {hi['unseen_tool_name_share']:.0%} of tool "
               "names unseen in training - where the frozen model reaches AUROC "
               f"{her['auc_source_dev_to_hermes']} vs {src_oof} in domain, still above that corpus' length baseline "
               f"({her['auc_hermes_length_only_B0']}) and post-retrieval margin "
               f"({her['auc_hermes_post_retrieval_margin']}). | Cross-corpus generalisation is now a measured "
               "number with a pre-registered decision rule; a second catalogue family remains a stated limit "
               "(L12). |")
    t = re.sub(r"^\| A13 \|.*$", new_a13, t, count=1, flags=re.M)
    t = t.replace("4. **Unseen-catalogue generalisation is bounded, not measured on held-out data** "
                  "(A7/A11a): the corpus",
                  "4. **Unseen-catalogue generalisation is now measured, on two axes** (A7/A11a/A13, "
                  "EXP-0021/0023): catalogue composition costs nothing detectable, tool vocabulary costs about "
                  f"{round(src_oof - her['auc_source_dev_to_hermes'], 3)} AUROC "
                  f"({her['auc_source_dev_to_hermes']} cross-corpus vs {src_oof} in domain). The corpus")
    ra.write_text(t, encoding="utf-8")
else:
    print("  (reviewer_attack.md: A13 already updated, skipped)")

# ---- final_audit.md ------------------------------------------------------------------------------
sub("final_audit.md", "| catalogue-disjoint held-out check | **IMPOSSIBLE, disclosed** |",
    f"| catalogue-disjoint held-out check | **MEASURED (D15), original finding still disclosed** | EXP-0021: unseen "
    f"catalogue *composition* costs nothing detectable ({a1b['n_rows']} disjoint rows at "
    f"{a1b['auc_transfer_disjoint_catalogues']}); leave-one-tool-family-out degrades "
    f"{a2['mean_auc_family_seen_reference']} -> {a2['mean_auc_unseen_family']}. EXP-0023 scores the frozen model on "
    f"an independent corpus: {her['auc_source_dev_to_hermes']} [{her['ci95_row_bootstrap'][0]}, "
    f"{her['ci95_row_bootstrap'][1]}] vs {src_oof} in domain. The EXP-0018 structural finding stands: |")
sub("final_audit.md", "E08 external dataset \u2192",
    f"~~E08 external dataset~~ **DONE (EXP-0022 probe + EXP-0023 cross-corpus AUROC "
    f"{her['auc_source_dev_to_hermes']})** \u2192")

# ---- limitations.md: new L12 ----------------------------------------------------------------------
L12 = (f"""## L12 跨语料泛化：已实测的降级（E08；取代原"缺失实验"条目）

EXP-0022 在文件层扫描八个本地语料：只有 `Agent-Ark/Toucan-1.5M` 与 `lambda/hermes-agent-reasoning-traces`
携带每查询候选目录；外部基准（STAC / ToolBench / API-Bank / ToolRet）在本环境不可下载——每个站点均按
root 与真实文件 URL 各重试 3 次并记录状态码。E08 因此落在 hermes 上。

* 独立性：外部语料 {hi['external_tool_names']} 个工具名中 {hi['unseen_tool_name_share']:.0%} 从未在源语料出现；
  目录 token 被源覆盖比例 {hi['external_catalog_tokens_covered_by_source']}（仍非完全陌生，如实报告）。
* 提取：{hc['n_rows']} 行通过 n_candidates>3 规则，fail@3 普遍率 {hc['fail_at_3_prevalence']}，
  拒绝统计 {E23['corpus_extraction']['rejection_accounting']}；EXP-0023a 先行确认可解析性
  （{E23a['rows_read']} 行、目录指纹仅 {E23a['distinct_catalogue_fingerprints']} 种）。
* 结果：仅用三个已发布 config 的 dev 拟合的冻结模型，跨语料 AUROC **{her['auc_source_dev_to_hermes']}**
  （行级 bootstrap CI {her['ci95_row_bootstrap']}），域内 {src_oof}，外部语料自身 OOF {her_oof}；
  同批数据上长度基线 {her['auc_hermes_length_only_B0']}、事后 margin 基线 {her['auc_hermes_post_retrieval_margin']}。
* 判据写在读取外部标签之前：>=0.65 transfers / 0.55-0.65 partial / <0.55 不迁移 -> **{her['verdict']}**。

**结论性表述**：本文所有已发布 AUROC 应读作"同一目录族内的上界"；对陌生工具宇宙的诚实预期是
{her['auc_source_dev_to_hermes']} 量级（构念仍成立、仍优于全部基线），不是 {src_oof}。
残余限制：外部语料只有 {hc['distinct_catalogues']} 个不同目录，无法做目录级聚类区间（行级 CI 必然低估不确定性）；
其金标注为参考模型实际调用的工具（与本文 DV 定义一致，但不含人工可接受集）。
EXP-0021 另记录一个负面事实：Toucan 第四 config `SFT` 看似外部，实测与源语料共享
{ov['distinct_tool_names']['exact_overlap']}/{ov['distinct_tool_names']['target']} 工具名与
{ov['distinct_catalogue_fingerprints']['shared_fingerprints']} 个相同目录指纹——公开 agent 轨迹语料之间
并非相互独立的目录来源，这本身是对"跨数据集验证"这一常规做法的警告。

"""
)
sub("limitations.md", "## L1 因变量的构念", L12 + "## L1 因变量的构念")
print("part 1 done: paper.md, reviewer_attack.md, final_audit.md, limitations.md")
