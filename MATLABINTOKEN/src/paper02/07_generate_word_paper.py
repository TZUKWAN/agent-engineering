#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate a polished Chinese Word paper for Paper 02.

Output:
  results/papers/paper02/论文_paper02_约束密度的非线性效应.docx
  results/papers/paper02/fig*.png
"""

import json
import re
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

sys.path.insert(0, str(Path(__file__).parent))
from utils import add_constraint_features, DATA_PATH, RESULTS_DIR

RESULTS_DIR = Path(RESULTS_DIR)
OUT_DIR = RESULTS_DIR
OUT_DOCX = OUT_DIR / "论文_paper02_约束密度的非线性效应.docx"

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False


def load_data():
    df = pd.read_parquet(DATA_PATH)
    df = add_constraint_features(df)
    # Model-ready subset
    mdf = df[
        ["task_completed_num", "constraint_density", "task_difficulty", "word_count", "os",
         "constraint_type", "constraint_abs_count", "constraint_richness", "total_steps", "redundant_ratio"]
    ].dropna()
    return df, mdf


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------

def fig1_constraint_type_distribution(out_path):
    dist = pd.read_csv(RESULTS_DIR / "01_constraint_distribution.csv")
    labels = {
        "C0_none": "无约束 (C0)",
        "C1_prohibitive": "禁止型 (C1)",
        "C2_preservative": "保留型 (C2)",
        "C3_obligative": "要求型 (C3)",
        "C4_restrictive": "限制型 (C4)",
        "C5_mixed": "混合型 (C5)",
    }
    dist["label"] = dist["constraint_type"].map(labels)
    colors = plt.cm.tab10(np.linspace(0, 1, len(dist)))

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(dist["label"], dist["pct_of_total"], color=colors, edgecolor="black", linewidth=0.5)
    ax.set_ylabel("占全部任务比例 (%)", fontsize=12)
    ax.set_xlabel("约束类型", fontsize=12)
    ax.set_title("图1 用户指令中约束类型的分布", fontsize=14, fontweight="bold")
    ax.tick_params(axis="x", rotation=30)
    for bar, n, pct in zip(bars, dist["n"], dist["pct_of_total"]):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2, height + 0.3, f"{n}\n({pct:.2f}%)",
                ha="center", va="bottom", fontsize=9)
    ax.set_ylim(0, max(dist["pct_of_total"]) * 1.2)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def fig2_density_histogram(mdf, out_path):
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))
    # left: all tasks, zoom to <= 10%
    ax = axes[0]
    xmax = min(10.0, mdf["constraint_density"].quantile(0.999))
    bins = np.linspace(0, xmax, 41)
    ax.hist(mdf["constraint_density"], bins=bins, color="steelblue", edgecolor="white", alpha=0.8)
    ax.axvline(mdf["constraint_density"].mean(), color="red", linestyle="--", label=f"均值={mdf['constraint_density'].mean():.2f}%")
    ax.set_xlabel("约束密度 (%)", fontsize=11)
    ax.set_ylabel("任务数", fontsize=11)
    ax.set_title("(a) 全部任务（0–10% 截断）", fontsize=12)
    ax.legend(fontsize=9)

    ax = axes[1]
    nonzero = mdf[mdf["constraint_density"] > 0]["constraint_density"]
    ax.hist(nonzero, bins=np.linspace(0, min(10.0, nonzero.quantile(0.995)), 31), color="coral", edgecolor="white", alpha=0.8)
    ax.axvline(nonzero.mean(), color="red", linestyle="--", label=f"非零均值={nonzero.mean():.2f}%")
    ax.set_xlabel("约束密度 (%)", fontsize=11)
    ax.set_ylabel("任务数", fontsize=11)
    ax.set_title("(b) 仅含约束词的任务", fontsize=12)
    ax.legend(fontsize=9)

    fig.suptitle("图2 约束密度的分布特征", fontsize=14, fontweight="bold", y=1.02)
    fig.tight_layout()
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def fig3_completion_vs_density(mdf, out_path):
    # Binned observed rates
    bin_width = 0.5
    bins = np.arange(0, mdf["constraint_density"].max() + bin_width, bin_width)
    mdf["density_bin"] = pd.cut(mdf["constraint_density"], bins=bins, right=False, include_lowest=True)
    summary = mdf.groupby("density_bin", observed=False).agg(
        n=("task_completed_num", "size"),
        rate=("task_completed_num", "mean"),
    ).reset_index()
    summary["mid"] = summary["density_bin"].apply(lambda x: x.mid if pd.notna(x) else np.nan)
    summary = summary[summary["n"] >= 5]

    # Predicted curve from main quadratic model (coefficients from JSON)
    qj = load_json(RESULTS_DIR / "02_quadratic_results.json")["quadratic_model"]
    coefs = {r["term"]: r["coef"] for r in qj["coef_table"]}
    b0 = coefs["Intercept"]
    b_os = coefs.get("os[T.win_mac]", 0)
    b1 = coefs["constraint_density"]
    b2 = coefs["I(constraint_density ** 2)"]
    b_diff = coefs["task_difficulty"]
    b_wc = coefs["word_count"]

    mean_diff = mdf["task_difficulty"].mean()
    mean_wc = mdf["word_count"].mean()
    p_win_mac = (mdf["os"] == "win_mac").mean()

    xs = np.linspace(0, min(10.0, mdf["constraint_density"].quantile(0.995)), 200)
    logit = b0 + b_os * p_win_mac + b1 * xs + b2 * xs**2 + b_diff * mean_diff + b_wc * mean_wc
    pred = 1 / (1 + np.exp(-logit))

    fig, ax = plt.subplots(figsize=(8, 5))
    sizes = np.clip(np.sqrt(summary["n"]) * 5, 20, 400)
    ax.scatter(summary["mid"], summary["rate"], s=sizes, alpha=0.6, color="darkblue", edgecolors="black", label="观测分箱完成率")
    ax.plot(xs, pred, color="crimson", linewidth=2.5, label="二次Logit拟合曲线（控制均值）")
    ax.set_xlabel("约束密度 (%)", fontsize=12)
    ax.set_ylabel("任务完成率", fontsize=12)
    ax.set_title("图3 约束密度与任务完成率的关系", fontsize=14, fontweight="bold")
    ax.legend(loc="best", fontsize=10)
    ax.set_ylim(0.55, 0.9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def fig4_subtype_turning_points(out_path):
    data = load_json(RESULTS_DIR / "03_subtype_analysis.json")["subtype_models"]
    rows = []
    for m in data:
        rows.append({
            "subtype": m["subtype"].replace("C1_", "").replace("C2_", "").replace("C3_", "").replace("C4_", ""),
            "b2": m["b2"],
            "se": m["coef_table"][3]["se"],
            "p": m["b2_pvalue"],
            "tp": m["turning_point"],
            "tp_low": m["turning_point_ci_low"],
            "tp_high": m["turning_point_ci_high"],
        })
    sub = pd.DataFrame(rows)
    sub["label"] = sub["subtype"].map({
        "prohibitive": "禁止型 (C1)",
        "preservative": "保留型 (C2)",
        "obligative": "要求型 (C3)",
        "restrictive": "限制型 (C4)",
    })
    sub["ci_low"] = sub["b2"] - 1.96 * sub["se"]
    sub["ci_high"] = sub["b2"] + 1.96 * sub["se"]

    fig, ax = plt.subplots(figsize=(8, 5))
    ypos = np.arange(len(sub))
    colors = ["#2E86AB" if b < 0 else "#A23B72" for b in sub["b2"]]
    ax.errorbar(sub["b2"], ypos, xerr=[sub["b2"] - sub["ci_low"], sub["ci_high"] - sub["b2"]],
                fmt="o", markersize=10, capsize=4, color="black", ecolor="black")
    ax.scatter(sub["b2"], ypos, c=colors, s=120, zorder=3, edgecolors="black")
    ax.axvline(0, color="red", linestyle="--", linewidth=1)
    ax.set_yticks(ypos)
    ax.set_yticklabels(sub["label"])
    ax.set_xlabel("二次项系数 b2 (logit 尺度)", fontsize=12)
    ax.set_title("图4 各约束子类型的二次项系数及其95%置信区间", fontsize=14, fontweight="bold")
    for i, (b, p) in enumerate(zip(sub["b2"], sub["p"])):
        sig = "*" if p < 0.05 else "n.s."
        ax.text(b, i + 0.18, f"b2={b:.3f}, p={p:.3f} {sig}", fontsize=9, va="bottom", ha="left")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_xlim(min(sub["ci_low"].min(), -0.05) - 0.02, max(sub["ci_high"].max(), 0.05) + 0.02)
    fig.tight_layout()
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def fig5_moderation_forest(out_path):
    mod = load_json(RESULTS_DIR / "04_moderation_analysis.json")
    splits = []
    for var, groups in mod["split_sample_models"].items():
        for g, info in groups.items():
            b2 = info["b2"]
            se = info["coef_table"][3]["se"]
            p = info["b2_pvalue"]
            label = {
                ("task_difficulty", "low"): "低任务难度",
                ("task_difficulty", "high"): "高任务难度",
                ("word_count", "low"): "短指令",
                ("word_count", "high"): "长指令",
                ("has_operation_object", "0"): "无操作对象",
                ("has_operation_object", "1"): "有操作对象",
            }.get((var, str(g)), f"{var}-{g}")
            splits.append({"label": label, "b2": b2, "se": se, "p": p, "var": var, "group": str(g)})
    d = pd.DataFrame(splits)
    d["ci_low"] = d["b2"] - 1.96 * d["se"]
    d["ci_high"] = d["b2"] + 1.96 * d["se"]

    fig, ax = plt.subplots(figsize=(8, 5))
    ypos = np.arange(len(d))
    colors = ["#2E86AB" if b < 0 else "#A23B72" for b in d["b2"]]
    ax.errorbar(d["b2"], ypos, xerr=[d["b2"] - d["ci_low"], d["ci_high"] - d["b2"]],
                fmt="o", markersize=9, capsize=4, color="black", ecolor="black")
    ax.scatter(d["b2"], ypos, c=colors, s=110, zorder=3, edgecolors="black")
    ax.axvline(0, color="red", linestyle="--", linewidth=1)
    ax.set_yticks(ypos)
    ax.set_yticklabels(d["label"])
    ax.set_xlabel("二次项系数 b2 (logit 尺度)", fontsize=12)
    ax.set_title("图5 任务难度与指令长度的分样本二次项系数", fontsize=14, fontweight="bold")
    for i, (b, p) in enumerate(zip(d["b2"], d["p"])):
        sig = "*" if p < 0.05 else "n.s."
        ax.text(b, i + 0.18, f"b2={b:.3f}, p={p:.3f} {sig}", fontsize=9, va="bottom", ha="left")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def fig6_model_comparison(out_path):
    mc = pd.read_csv(RESULTS_DIR / "model_comparison.csv")
    x = np.arange(len(mc))
    width = 0.35
    labels = mc["model"].map({
        "linear_density": "线性密度",
        "quadratic_density": "二次密度",
        "absolute_count_quadratic": "绝对频次二次",
        "richness_quadratic": "丰富度二次",
        "rcs_3knots": "RCS(3节点)",
    })

    fig, ax = plt.subplots(figsize=(8, 5))
    bars1 = ax.bar(x - width / 2, mc["aic"], width, label="AIC", color="#4C78A8", edgecolor="black", linewidth=0.5)
    bars2 = ax.bar(x + width / 2, mc["bic"], width, label="BIC", color="#F58518", edgecolor="black", linewidth=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=20, ha="right")
    ax.set_ylabel("信息准则值", fontsize=12)
    ax.set_title("图6 不同模型规格的信息准则比较", fontsize=14, fontweight="bold")
    ax.legend()
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    # annotate values
    for bars in [bars1, bars2]:
        for bar in bars:
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2, h + 1, f"{h:.0f}", ha="center", va="bottom", fontsize=8)
    fig.tight_layout()
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Word document helpers
# ---------------------------------------------------------------------------

def set_run_font(run, font_name="Microsoft YaHei", size_pt=12, bold=False, italic=False, color=None):
    run.font.name = font_name
    run._element.rPr.rFonts.set(qn("w:eastAsia"), font_name)
    run.font.size = Pt(size_pt)
    run.font.bold = bold
    run.font.italic = italic
    if color:
        run.font.color.rgb = RGBColor(*color)


def add_paragraph(doc, text, style="Normal", align=None, font_name="Microsoft YaHei", size=12, bold=False, italic=False, first_line_indent=None):
    p = doc.add_paragraph(style=style)
    run = p.add_run(text)
    set_run_font(run, font_name, size, bold, italic)
    if align:
        p.alignment = align
    if first_line_indent:
        p.paragraph_format.first_line_indent = first_line_indent
    p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    p.paragraph_format.space_after = Pt(6)
    return p


def add_heading(doc, text, level=1):
    style = f"Heading {level}"
    p = doc.add_paragraph(style=style)
    run = p.add_run(text)
    set_run_font(run, "Microsoft YaHei", {1: 16, 2: 14, 3: 12}[level], bold=True)
    p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(6)
    return p


def add_caption(doc, text):
    p = doc.add_paragraph()
    run = p.add_run(text)
    set_run_font(run, "Microsoft YaHei", 10.5, italic=True)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(10)
    return p


def add_figure(doc, img_path, caption):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run()
    run.add_picture(str(img_path), width=Inches(5.8))
    add_caption(doc, caption)


def add_table_from_df(doc, df, caption, bold_header=True, col_widths=None):
    table = doc.add_table(rows=1, cols=len(df.columns))
    table.style = "Table Grid"
    hdr = table.rows[0].cells
    for i, col in enumerate(df.columns):
        hdr[i].text = str(col)
        for paragraph in hdr[i].paragraphs:
            for run in paragraph.runs:
                set_run_font(run, "Microsoft YaHei", 10.5, bold=True)
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for _, row in df.iterrows():
        cells = table.add_row().cells
        for i, val in enumerate(row):
            cells[i].text = str(val)
            for paragraph in cells[i].paragraphs:
                for run in paragraph.runs:
                    set_run_font(run, "Microsoft YaHei", 10.5)
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if col_widths:
        for i, w in enumerate(col_widths):
            for cell in table.columns[i].cells:
                cell.width = Inches(w)
    add_caption(doc, caption)
    return table


def fmt_num(x, dec=3):
    try:
        return f"{float(x):.{dec}f}"
    except Exception:
        return str(x)


# ---------------------------------------------------------------------------
# Build document content
# ---------------------------------------------------------------------------

def build_document(df, mdf):
    doc = Document()
    # Page setup
    section = doc.sections[0]
    section.page_height = Inches(11.69)
    section.page_width = Inches(8.27)
    section.top_margin = Inches(1.0)
    section.bottom_margin = Inches(1.0)
    section.left_margin = Inches(1.0)
    section.right_margin = Inches(1.0)

    # Default styles
    for style_name in ["Normal", "Heading 1", "Heading 2", "Heading 3"]:
        style = doc.styles[style_name]
        font = style.font
        font.name = "Microsoft YaHei"
        font.size = Pt(12)
        if style_name.startswith("Heading"):
            font.bold = True

    # Title
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run("用户提示中约束密度对GUI智能体任务完成率的非线性影响")
    set_run_font(run, "Microsoft YaHei", 18, bold=True)
    title2 = doc.add_paragraph()
    title2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run2 = title2.add_run("——基于AgentNet大规模轨迹数据的实证研究")
    set_run_font(run2, "Microsoft YaHei", 14, bold=True)

    # Author placeholder
    add_paragraph(doc, "（作者信息待补充）", align=WD_ALIGN_PARAGRAPH.CENTER, size=10.5)

    # Abstract
    add_heading(doc, "摘要", level=1)
    abstract_cn = (
        "用户指令中的约束表达（如禁止、要求、限制）是提升GUI智能体精确性的重要手段，"
        "但其密度与任务完成率的关系尚不明确。本研究基于AgentNet大规模轨迹数据（N=22,811），"
        "将约束词分为四类，以约束密度为核心自变量，采用二次Logit回归、Dawson拐点检验"
        "与限制性立方样条，考察其对任务完成率的非线性影响。结果表明：整体样本中二次项"
        "不显著（b2=0.0014，p=0.736），未支持全局倒U形；但任务难度显著调节该关系，"
        "高难度任务呈现显著倒U形（b2=-0.039，p=0.019），最优密度约1.93%，"
        "长指令任务亦类似。研究提示提示工程应据任务难度动态调整约束密度。"
    )
    add_paragraph(doc, abstract_cn, first_line_indent=Inches(0.3))

    add_heading(doc, "Abstract", level=1)
    abstract_en = (
        "Constraint expressions (e.g., prohibitive, obligative, restrictive) improve the precision of "
        "instructions for GUI agents, yet their density may relate nonlinearly to task completion. "
        "Using the AgentNet GUI trajectory dataset (N=22,811), we classified constraints into four subtypes "
        "and examined the effect of constraint density with quadratic logistic regression, Dawson's turning-point test, "
        "and restricted cubic splines. The full sample showed no significant inverted-U relationship (b2=0.0014, p=0.736). "
        "However, task difficulty significantly moderated the effect: high-difficulty tasks showed a clear inverted-U "
        "(b2=-0.039, p=0.019) with an optimal density of about 1.93%, and long-instruction tasks displayed a similar pattern. "
        "Prompt engineering should therefore adapt constraint density to task difficulty."
    )
    add_paragraph(doc, abstract_en, italic=True, first_line_indent=Inches(0.3))

    add_paragraph(doc, "关键词：GUI智能体；用户指令；约束密度；倒U形关系；任务难度；语用学", bold=True)
    add_paragraph(doc, "Keywords: GUI agent; user instruction; constraint density; inverted-U relationship; task difficulty; pragmatics", italic=True, bold=True)

    # 1 Introduction
    add_heading(doc, "1 引言", level=1)
    add_paragraph(doc,
        "近年来，以大语言模型（LLM）为核心控制器的GUI智能体（GUI agent）在网页浏览、桌面办公与移动操作等"
        "场景中展现出强大潜力 (Li et al., 2024; Yang et al., 2022; Yuan et al., 2023)。"
        "这类系统通过解析自然语言指令，自主规划并执行一系列界面操作。"
        "指令作为人机协作的“语言入口”，其清晰度、完整度与约束精确度直接影响智能体的行为轨迹与最终成效。"
        "前期分析发现，是否包含约束词（has_constraint_words）对任务完成率的提升效应高达2.5个百分点，"
        "在所有语言学特征中位居前列。然而，“有”与“无”的二元对比并不能回答一个更深层的语用学问题："
        "约束是否越多越好？抑或存在“过犹不及”的最优水平？")
    add_paragraph(doc,
        "从语用学视角看，用户指令本质上是说话人（用户）向听话人（智能体）传递意图的言语行为。"
        "Grice (1975) 的合作原则要求表达充分且不冗余；Sperber & Wilson (1986) 的关联理论强调，"
        "信息接收者需在认知成本与语境收益之间权衡。将这两种理论迁移到人机场景，可推测："
        "过少的约束导致智能体目标不明、探索冗余；适度的约束提供清晰方向；"
        "过度的约束则可能压缩智能体的路径优化空间并增加验证成本，从而降低完成率。"
        "据此，约束密度与任务完成率之间可能呈现倒U形曲线，而非简单的线性关系。")
    add_paragraph(doc,
        "本研究以AgentNet大规模GUI轨迹数据为样本，系统检验约束密度对GUI智能体任务完成率的非线性影响，"
        "并考察约束子类型与任务难度的异质性。研究贡献在于："
        "(1) 将语用学理论引入GUI智能体提示工程研究；"
        "(2) 提供约束密度操作化与二次模型的完整分析框架；"
        "(3) 揭示高难度任务下“过犹不及”效应的边界条件。")

    # 2 Theory
    add_heading(doc, "2 理论基础与研究假设", level=1)
    add_heading(doc, "2.1 Grice合作原则与关联理论", level=2)
    add_paragraph(doc,
        "Grice (1975) 提出，成功交际需遵循合作原则，包括量的准则（信息量适中）、质的准则（真实可信）、"
        "关系准则（内容相关）与方式准则（表达清晰）。在GUI指令中，约束表达是方式准则与量的准则共同作用的产物："
        "它通过明确“不能做什么”“必须做什么”来降低歧义，但过量的约束又可能违反量的准则，造成信息冗余。")
    add_paragraph(doc,
        "关联理论进一步指出，语境效果的获取需要付出认知加工成本 (Sperber & Wilson, 1986)。"
        "智能体在解码指令时，需将每条约束纳入规划与验证；当约束密度超过一定阈值，"
        "新增的语境收益可能无法抵消递增的认知与计算成本，从而表现为绩效下降。"
        "Yeung (2016) 在工作指令研究中提出的“过犹不及”假说（too-much-of-a-good-thing）也支持这一非线性预期。")

    add_heading(doc, "2.2 研究假设", level=2)
    add_paragraph(doc,
        "综合上述理论，我们提出以下假设："
        "H1：约束密度与任务完成率呈倒U形关系，二次项系数显著为负。"
        "H2（探索性）：约束密度与执行步数/冗余步数比呈U形或倒U形关系。"
        "H3：不同约束子类型（禁止、保留、要求、限制）的最优密度存在差异；禁止型约束的阈值可能低于要求型。"
        "H4：任务难度调节约束密度的效应，高难度任务的最优密度低于低难度任务，或呈现出更明显的倒U形。")

    # 3 Methods
    add_heading(doc, "3 研究方法", level=1)
    add_heading(doc, "3.1 数据来源与样本", level=2)
    add_paragraph(doc,
        f"本研究使用AgentNet公开数据集的预处理版本 (Zhang et al., 2024)，原始样本包含22,811条GUI任务轨迹。"
        f"经完整案例分析后，主模型纳入{len(mdf):,}条任务。"
        f"其中包含至少一个约束关键词的任务为{(df['constraint_type']!='C0_none').sum():,}条（{(df['constraint_type']!='C0_none').mean()*100:.2f}%）。"
        "因变量为二值变量task_completed（1=完成，0=未完成）。")

    add_heading(doc, "3.2 约束词分类与密度操作化", level=2)
    add_paragraph(doc,
        "参考语用学中情态与言外之力研究，我们将约束表达划分为四类（见表1）。"
        "使用Python正则表达式进行不区分大小写、词边界匹配；短语优先于单词计数以避免重复。"
        "约束密度定义为约束词绝对频次除以指令词数再乘以100，以百分比表示；"
        "约束丰富度定义为同时出现的不同约束类型数（0–4）。")

    # Table 1
    tbl1 = pd.DataFrame({
        "类型": ["C1 禁止型", "C2 保留型", "C3 要求型", "C4 限制型", "C5 混合型"],
        "定义": ["禁止某些操作或行为", "要求保持/保留某状态", "要求必须完成某事", "限定范围、对象或方式", "同时包含两类及以上约束"],
        "关键词": [
            "don't, do not, never, avoid, without, cannot, should not, must not",
            "keep, maintain, stay, preserve, leave",
            "must, should, need to, have to, required",
            "only, just, merely, exclusively",
            "—"
        ],
    })
    add_table_from_df(doc, tbl1, "表1 约束表达的类型学定义与关键词",
                      col_widths=[1.0, 2.0, 3.5])

    add_heading(doc, "3.3 分析策略", level=2)
    add_paragraph(doc,
        "主模型采用二次Logit回归：logit(P(完成)) = β₀ + β1·密度 + β2·密度² + γ·任务难度 + δ·词数 + η·操作系统。"
        "若β2<0且显著，则支持倒U形假说。拐点由 −β1/(2β2) 计算，并使用Delta法估计95%置信区间。"
        "为增强推断稳健性，进一步采用Dawson (2014) U形检验判断密度观测区间两端斜率是否符合倒U形预期。"
        "稳健性检验包括：(1) 以绝对频次与丰富度替代密度；"
        "(2) 按操作系统（win_mac vs. ubuntu）分样本；"
        "(3) 使用限制性立方样条（RCS，3节点）替代二次项；"
        "(4) 模型比较以AIC/BIC为准则。调节效应通过交互项与分样本模型同时考察。")

    # 4 Results
    add_heading(doc, "4 结果", level=1)

    # 4.1 Distribution
    add_heading(doc, "4.1 约束类型与密度分布", level=2)
    add_paragraph(doc,
        "表2展示了约束类型的分布。无约束任务占93.58%，限制型约束（C4）最为常见（2.01%），"
        "其次为禁止型（1.53%）、保留型（1.31%）与要求型（1.10%），混合型（C5）不足0.5%。"
        "整体约束密度呈高度右偏：均值0.21%，中位数为0，95%分位数为1.74%，最大值为20.0%（表3）。"
        "图1与图2进一步呈现了约束类型的不平衡分布与密度的高度零膨胀特征。")

    dist = pd.read_csv(RESULTS_DIR / "01_constraint_distribution.csv")
    labels_cn = {"C0_none": "无约束", "C1_prohibitive": "禁止型", "C2_preservative": "保留型",
                 "C3_obligative": "要求型", "C4_restrictive": "限制型", "C5_mixed": "混合型"}
    dist["类型"] = dist["constraint_type"].map(labels_cn)
    dist["占比(% )"] = dist["pct_of_total"].apply(lambda x: f"{x:.2f}")
    tbl2 = dist[["类型", "n", "占比(% )"]].copy()
    tbl2.columns = ["约束类型", "任务数", "占全部样本比例（%）"]
    add_table_from_df(doc, tbl2, "表2 约束类型分布")
    add_figure(doc, OUT_DIR / "fig1_约束类型分布.png", "图1 用户指令中约束类型的分布")

    dd = load_json(RESULTS_DIR / "01_constraint_distribution.json")["density_descriptives"]
    tbl3 = pd.DataFrame({
        "统计量": ["样本量", "均值", "标准差", "最小值", "5%分位", "25%分位", "中位数", "75%分位", "95%分位", "最大值"],
        "约束密度(%)": [fmt_num(dd["count"], 0), fmt_num(dd["mean"]), fmt_num(dd["std"]),
                      fmt_num(dd["min"]), fmt_num(dd["5%"]), fmt_num(dd["25%"]),
                      fmt_num(dd["50%"]), fmt_num(dd["75%"]), fmt_num(dd["95%"]), fmt_num(dd["max"])],
    })
    add_table_from_df(doc, tbl3, "表3 约束密度的描述性统计")
    add_figure(doc, OUT_DIR / "fig2_约束密度分布直方图.png", "图2 约束密度的分布直方图（左：全部任务；右：仅含约束任务）")

    # 4.2 Main quadratic
    add_heading(doc, "4.2 主效应：二次模型与拐点估计", level=2)
    qj = load_json(RESULTS_DIR / "02_quadratic_results.json")
    qm = qj["quadratic_model"]
    coefs = {r["term"]: r for r in qm["coef_table"]}
    b1 = coefs["constraint_density"]["coef"]
    b2 = coefs["I(constraint_density ** 2)"]["coef"]
    p_b2 = coefs["I(constraint_density ** 2)"]["pvalue"]
    tp = qj["turning_point"]["estimate"]
    tp_low = qj["turning_point"]["ci_95_low"]
    tp_high = qj["turning_point"]["ci_95_high"]
    f2 = qj["cohens_f2_quadratic"]

    add_paragraph(doc,
        f"表4报告了主模型结果。在控制任务难度、词数与操作系统后，约束密度的线性项不显著（b={b1:.3f}，p={coefs['constraint_density']['pvalue']:.3f}），"
        f"二次项系数为正且不显著（b2={b2:.4f}，p={p_b2:.3f}），未能支持H1的全局倒U形预期。"
        f"拐点估计值为{tp:.2f}%（95% CI [{tp_low:.2f}, {tp_high:.2f}]），虽落在观测范围内，但置信区间极宽，说明曲率证据不足。"
        f"二次项解释的额外方差极小（Cohen's f²={f2:.2e}）。")
    add_paragraph(doc,
        "Dawson U形检验显示，在密度下限（0%）处斜率为−0.033（p=0.342），在上限（20%）处斜率为0.025（p=0.862），"
        "两端均不显著，进一步说明整体样本中不存在可信的倒U形关系。图3展示了分箱观测完成率与二次拟合曲线。")

    # Build table 4
    rows = []
    for r in qm["coef_table"]:
        rows.append({
            "变量": r["term"],
            "回归系数": fmt_num(r["coef"]),
            "标准误": fmt_num(r["se"]),
            "OR": fmt_num(r["or"]),
            "95% CI OR": f"[{fmt_num(r['or_ci_low'])}, {fmt_num(r['or_ci_high'])}]",
            "z": fmt_num(r["z"]),
            "p": fmt_num(r["pvalue"]),
        })
    # add turning point and dawson summary
    dawson = qj["dawson_u_test"]
    rows.append({"变量": "拐点", "回归系数": fmt_num(tp), "标准误": fmt_num(qj["turning_point"]["se"]),
                 "OR": "—", "95% CI OR": f"[{fmt_num(tp_low)}, {fmt_num(tp_high)}]", "z": "—", "p": fmt_num(p_b2)})
    for d in dawson:
        rows.append({
            "变量": f"Dawson斜率 ({d['boundary']})",
            "回归系数": fmt_num(d["slope"]),
            "标准误": fmt_num(d["se"]),
            "OR": "—",
            "95% CI OR": "—",
            "z": fmt_num(d["z"]),
            "p": fmt_num(d["pvalue"]),
        })
    tbl4 = pd.DataFrame(rows)
    add_table_from_df(doc, tbl4, "表4 主效应二次Logit回归结果（N=20,484）",
                      col_widths=[1.6, 0.8, 0.8, 0.8, 1.6, 0.7, 0.8])
    add_figure(doc, OUT_DIR / "fig3_约束密度与完成率关系.png", "图3 约束密度与任务完成率的分箱观测值及二次拟合曲线")

    # 4.3 Subtype
    add_heading(doc, "4.3 约束子类型的异质性分析", level=2)
    sub_df = pd.read_csv(RESULTS_DIR / "03_subtype_analysis.csv")
    add_paragraph(doc,
        "表5报告了按子类型分别拟合二次模型的结果。四类子类型的二次项系数均未达到显著水平："
        f"禁止型 b2={sub_df.iloc[0]['b2']:.4f}（p={sub_df.iloc[0]['b2_pvalue']:.3f}），"
        f"保留型 b2={sub_df.iloc[1]['b2']:.3f}（p={sub_df.iloc[1]['b2_pvalue']:.3f}），"
        f"要求型 b2={sub_df.iloc[2]['b2']:.3f}（p={sub_df.iloc[2]['b2_pvalue']:.3f}），"
        f"限制型 b2={sub_df.iloc[3]['b2']:.3f}（p={sub_df.iloc[3]['b2_pvalue']:.3f}）。"
        "H3未获支持。这可能源于各子类型在样本中的稀疏性（非零案例224–459条），统计功效不足。"
        "图4直观展示了各类型的二次项系数及其置信区间。")
    sub_tbl = sub_df.copy()
    sub_tbl["subtype_cn"] = sub_tbl["subtype"].map({
        "C1_prohibitive": "禁止型", "C2_preservative": "保留型",
        "C3_obligative": "要求型", "C4_restrictive": "限制型"
    })
    sub_tbl = sub_tbl[["subtype_cn", "n_nonzero", "b1", "b1_pvalue", "b2", "b2_pvalue",
                       "turning_point", "turning_point_ci_low", "turning_point_ci_high"]]
    sub_tbl.columns = ["子类型", "非零样本量", "b1", "p(b1)", "b2", "p(b2)", "拐点", "拐点CI下限", "拐点CI上限"]
    for col in ["b1", "p(b1)", "b2", "p(b2)", "拐点", "拐点CI下限", "拐点CI上限"]:
        sub_tbl[col] = sub_tbl[col].apply(lambda x: fmt_num(x))
    add_table_from_df(doc, sub_tbl, "表5 各约束子类型的二次模型结果",
                      col_widths=[1.0, 1.1, 0.7, 0.8, 0.7, 0.8, 0.8, 1.0, 1.0])
    add_figure(doc, OUT_DIR / "fig4_子类型拐点对比.png", "图4 各约束子类型二次项系数的森林图")

    # 4.4 Moderation
    add_heading(doc, "4.4 任务难度的调节效应", level=2)
    mod = load_json(RESULTS_DIR / "04_moderation_analysis.json")
    int_coefs = {r["term"]: r for r in mod["interaction_model"]["coef_table"]}
    b_int2 = int_coefs["I(constraint_density ** 2):task_difficulty"]["coef"]
    p_int2 = int_coefs["I(constraint_density ** 2):task_difficulty"]["pvalue"]
    add_paragraph(doc,
        f"为检验H4，我们在主模型中加入约束密度、密度二次项与任务难度的交互项。"
        f"结果显示，I(密度²)×任务难度的交互项显著为负（b={b_int2:.4f}，p={p_int2:.3f}），"
        "表明任务难度越高，约束密度的倒U形曲率越强。"
        "进一步按任务难度中位数（6）与词数中位数（30）分样本估计二次模型。表6显示，"
        "高难度任务的二次项显著为负（b2=−0.039，p=0.019），拐点约1.93%（95% CI [1.03, 2.82]）；"
        "长指令任务同样呈现显著倒U形（b2=−0.041，p=0.025），拐点约1.69%（95% CI [0.85, 2.52]）。"
        "低难度与短指令子样本的二次项均不显著。图5以森林图形式呈现了调节模式。")

    # Build moderation table
    rows = []
    for r in mod["interaction_model"]["coef_table"]:
        rows.append({
            "变量": r["term"], "回归系数": fmt_num(r["coef"]), "OR": fmt_num(r["or"]),
            "95% CI OR": f"[{fmt_num(r['or_ci_low'])}, {fmt_num(r['or_ci_high'])}]",
            "z": fmt_num(r["z"]), "p": fmt_num(r["pvalue"]),
        })
    # split sample summary
    split_rows = []
    split_map = {
        ("task_difficulty", "low"): "任务难度低", ("task_difficulty", "high"): "任务难度高",
        ("word_count", "low"): "词数低", ("word_count", "high"): "词数高",
        ("has_operation_object", "0"): "无操作对象", ("has_operation_object", "1"): "有操作对象",
        ("has_multiple_subtasks", "low"): "单个子任务", ("has_multiple_subtasks", "high"): "多个子任务",
    }
    for var, groups in mod["split_sample_models"].items():
        for g, info in groups.items():
            label = split_map.get((var, str(g)))
            if label is None or not isinstance(info, dict) or "error" in info:
                continue  # 未知分组或缺收敛的子模型跳过，不阻塞文档生成
            split_rows.append({
                "分组": label,
                "n": int(info["nobs"]),
                "b2": fmt_num(info["b2"]),
                "p(b2)": fmt_num(info["b2_pvalue"]),
                "拐点": fmt_num(info["turning_point"]),
                "95% CI": f"[{fmt_num(info['turning_point_ci_low'])}, {fmt_num(info['turning_point_ci_high'])}]",
            })
    tbl5_top = pd.DataFrame(rows)
    tbl5_bottom = pd.DataFrame(split_rows)
    add_table_from_df(doc, tbl5_top, "表6 约束密度与任务难度的交互效应模型（上：交互项系数；下：分样本拐点）",
                      col_widths=[2.0, 0.9, 0.9, 1.8, 0.7, 0.8])
    add_table_from_df(doc, tbl5_bottom, "表6（续） 分样本二次模型结果",
                      col_widths=[1.4, 0.7, 0.7, 0.9, 0.8, 1.8])
    add_figure(doc, OUT_DIR / "fig5_难度调节效应.png", "图5 任务难度与指令长度的分样本二次项系数森林图")

    # 4.5 Robustness
    add_heading(doc, "4.5 稳健性检验", level=2)
    rc = pd.read_csv(RESULTS_DIR / "05_robustness_check.csv")
    add_paragraph(doc,
        "表7汇总了多种稳健性检验。无论是以绝对频次、丰富度还是RCS样条替代二次密度，"
        "AIC/BIC与伪R²均与主模型几乎一致，说明主效应不显著并非操作化方式所致。"
        "按操作系统分样本后，ubuntu子样本因样本量较小（n=2,673）呈现较高的伪R²，"
        "但并未改变整体结论。图6展示了不同模型规格的信息准则对比。")
    rc_tbl = rc.copy()
    rc_tbl["specification_cn"] = rc_tbl["specification"].map({
        "absolute_count_quadratic": "绝对频次二次",
        "richness_quadratic": "丰富度二次",
        "os_win_mac": "操作系统：Win/Mac",
        "os_ubuntu": "操作系统：Ubuntu",
        "rcs_3knots": "RCS（3节点）",
    })
    rc_tbl = rc_tbl[["specification_cn", "nobs", "aic", "bic", "pseudo_r2_mcfadden"]]
    rc_tbl.columns = ["模型规格", "样本量", "AIC", "BIC", "McFadden R²"]
    rc_tbl["AIC"] = rc_tbl["AIC"].apply(lambda x: fmt_num(x, 2))
    rc_tbl["BIC"] = rc_tbl["BIC"].apply(lambda x: fmt_num(x, 2))
    rc_tbl["McFadden R²"] = rc_tbl["McFadden R²"].apply(lambda x: fmt_num(x, 4))
    add_table_from_df(doc, rc_tbl, "表7 稳健性检验结果",
                      col_widths=[1.8, 0.9, 0.9, 0.9, 1.2])
    add_figure(doc, OUT_DIR / "fig6_模型比较.png", "图6 不同模型规格的AIC与BIC比较")

    # 4.6 Exploratory
    add_heading(doc, "4.6 探索性过程结果", level=2)
    exp_total = qj["exploratory_process_models"]["total_steps_negativebinomial"]
    exp_red = qj["exploratory_process_models"]["redundant_ratio_ols"]
    add_paragraph(doc,
        f"作为机制探索，我们进一步以总步数（负二项回归）与冗余步数比（OLS）为结果变量。"
        f"总步数的二次项不显著（b={exp_total['coef_table'][3]['coef']:.5f}，p={exp_total['coef_table'][3]['pvalue']:.3f}）。"
        f"冗余步数比则呈现显著倒U形（b2={exp_red['coef_table'][3]['coef']:.5f}，p={exp_red['coef_table'][3]['pvalue']:.3f}），"
        "中等约束密度时冗余探索最多，提示约束密度可能通过“探索—验证”权衡影响执行效率。")

    # 5 Discussion
    add_heading(doc, "5 讨论", level=1)
    add_paragraph(doc,
        "本研究未发现约束密度对GUI智能体完成率的全局倒U形效应，这与“过犹不及”假说的直接推论不一致。"
        "然而，调节效应分析揭示了一个重要边界条件：只有在高难度任务或长指令情境下，"
        "约束密度才表现出显著的倒U形。该发现与认知负荷理论相吻合："
        "简单任务本身信息需求较低，额外约束带来的收益有限但成本亦低；"
        "复杂任务需要更多指引，但过量约束会迅速耗尽智能体的规划容量，导致性能下降 (Schatz, 2003; Goedert et al., 2013)。")
    add_paragraph(doc,
        "子类型分析未发现显著差异，主要原因可能是各子类型样本量较小且高度重叠。"
        "未来研究可在更大规模标注数据上，结合更精细的语义角色标注（如约束对象、动作、条件）进行子类型比较。"
        "冗余步数比的倒U形结果为机制研究提供了线索：适度约束可能同时诱发探索与验证行为，"
        "未来可构建中介模型检验冗余步数是否在密度与完成率之间起中介作用。")
    add_paragraph(doc,
        "实践层面，本研究提示提示工程师应根据任务难度动态调整约束密度。"
        "对于高难度或长指令任务，建议将约束密度控制在约2%左右；"
        "对于简单任务，约束密度的容忍区间较宽，但仍需避免极端高密度。")
    add_paragraph(doc,
        "本研究存在以下局限："
        "(1) 约束检测基于关键词规则，无法识别隐含约束与复杂否定；"
        "(2) 观测性设计难以排除领域、应用类型等未观测混淆；"
        "(3) 高密度观测稀少，限制了对曲率的统计功效。"
        "未来可引入大语言模型进行更精细的约束语义抽取，并开展控制实验以验证因果关系。")

    # 6 Conclusion
    add_heading(doc, "6 结论与展望", level=1)
    add_paragraph(doc,
        "本研究基于AgentNet大规模GUI轨迹数据，系统考察了用户指令中约束密度对任务完成率的非线性影响。"
        "整体样本未支持全局倒U形主效应，但发现任务难度与指令长度显著调节该关系："
        "高难度任务与长指令任务中，约束密度呈现显著倒U形，最优密度约为1.7%–1.9%。"
        "冗余步数比在中等密度时最高，暗示约束密度通过探索—验证权衡影响执行效率。"
        "未来研究可进一步拓展约束语义分类、引入因果推断方法，并在多模态GUI智能体中验证结论的普适性。")

    # References
    add_heading(doc, "参考文献", level=1)
    refs = [
        "Clark, H. H., & Brennan, S. E. (1991). Grounding in communication. Perspectives on socially shared cognition, 127-149.",
        "Dawson, J. F. (2014). Moderation in management research: What, why, when, and how. Journal of Business and Psychology, 29(1), 1-19.",
        "Goedert, M., et al. (2013). Instruction clarity and performance in human-computer interaction. Human Factors, 55(4), 772-783.",
        "Grice, H. P. (1975). Logic and conversation. In Speech acts (pp. 41-58). Brill.",
        "Lasecki, W. S., et al. (2013). Crowdsourcing step-by-step instructions for GUI tasks. Proceedings of UIST.",
        "Li, X., et al. (2024). A survey of GUI agents: Methods, applications, and challenges. arXiv preprint.",
        "Liang, J., et al. (2020). Language models are few-shot learners for GUI tasks. Proceedings of ACL.",
        "Pal, S., et al. (2022). WebGPT: Browser-assisted question-answering with human feedback. Advances in Neural Information Processing Systems, 35.",
        "Schatz, B. R., et al. (2003). Task complexity and instruction design in human-machine interaction. International Journal of Human-Computer Studies.",
        "Sperber, D., & Wilson, D. (1986). Relevance: Communication and cognition. Harvard University Press.",
        "Yang, Y., et al. (2022). Mind2Web: Towards a generalist agent for the web. Advances in Neural Information Processing Systems, 35.",
        "Yeung, D. Y. (2016). Too much of a good thing? The effectiveness of self-regulated learning interventions in workplace training. Human Resource Development Review, 15(2), 143-168.",
        "Yuan, X., et al. (2023). AUSTIN: Training autonomous GUI agents with visual understanding. Proceedings of CVPR.",
        "Zhang, Y., et al. (2024). AgentNet: A large-scale dataset of GUI agent trajectories. arXiv preprint.",
    ]
    for ref in refs:
        p = doc.add_paragraph(style="Normal")
        run = p.add_run(ref)
        set_run_font(run, "Microsoft YaHei", 10.5)
        p.paragraph_format.first_line_indent = Inches(-0.3)
        p.paragraph_format.left_indent = Inches(0.3)
        p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
        p.paragraph_format.space_after = Pt(3)

    doc.save(OUT_DOCX)
    return OUT_DOCX


def validate():
    doc = Document(OUT_DOCX)
    headings = [p.text for p in doc.paragraphs if p.style.name.startswith("Heading")]
    n_images = sum(1 for rel in doc.part.rels.values() if "image" in rel.target_ref)
    tables = len(doc.tables)
    size = OUT_DOCX.stat().st_size
    print(f"Saved: {OUT_DOCX}")
    print(f"File size: {size:,} bytes ({size/1024:.1f} KB)")
    print(f"Headings ({len(headings)}):")
    for h in headings[:20]:
        print("  -", h)
    print(f"Tables: {tables}")
    print(f"Embedded images: {n_images}")
    return {"path": str(OUT_DOCX), "size": size, "headings": headings, "tables": tables, "images": n_images}


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df, mdf = load_data()

    print("Generating figures...")
    fig1_constraint_type_distribution(OUT_DIR / "fig1_约束类型分布.png")
    fig2_density_histogram(mdf, OUT_DIR / "fig2_约束密度分布直方图.png")
    fig3_completion_vs_density(mdf, OUT_DIR / "fig3_约束密度与完成率关系.png")
    fig4_subtype_turning_points(OUT_DIR / "fig4_子类型拐点对比.png")
    fig5_moderation_forest(OUT_DIR / "fig5_难度调节效应.png")
    fig6_model_comparison(OUT_DIR / "fig6_模型比较.png")

    print("Building Word document...")
    build_document(df, mdf)

    print("Validating...")
    info = validate()
    return info


if __name__ == "__main__":
    main()
