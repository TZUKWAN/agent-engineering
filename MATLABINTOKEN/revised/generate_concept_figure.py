import os
#!/usr/bin/env python3
"""生成 Paper 03 图5：三篇论文理论整合概念框架图"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

fig, ax = plt.subplots(1, 1, figsize=(16, 10))
ax.set_xlim(0, 16)
ax.set_ylim(0, 10)
ax.axis('off')
ax.set_facecolor('#FAFAFA')
fig.patch.set_facecolor('#FAFAFA')

# ── Color palette ──
C_PAPER01 = '#2E86AB'    # blue
C_PAPER02 = '#A23B72'    # purple
C_PAPER03 = '#F18F01'    # orange
C_MODERATOR = '#C73E1D'  # red
C_OUTCOME = '#3A7D44'    # green
C_BG = '#F0F0F0'
C_ARROW = '#555555'
C_TEXT = '#222222'

# ── Helper functions ──
def draw_box(ax, x, y, w, h, color, alpha=0.15, lw=2, ls='-'):
    """Draw a rounded box."""
    box = FancyBboxPatch((x, y), w, h,
                         boxstyle="round,pad=0.15",
                         facecolor=color, edgecolor=color,
                         alpha=alpha, linewidth=lw, linestyle=ls)
    ax.add_patch(box)

def draw_solid_box(ax, x, y, w, h, color, text='', fontsize=9, text_color='white', bold=True):
    """Draw a solid colored box with text."""
    box = FancyBboxPatch((x, y), w, h,
                         boxstyle="round,pad=0.12",
                         facecolor=color, edgecolor=color,
                         alpha=0.9, linewidth=1.5)
    ax.add_patch(box)
    weight = 'bold' if bold else 'normal'
    ax.text(x + w/2, y + h/2, text, ha='center', va='center',
            fontsize=fontsize, color=text_color, fontweight=weight)

def draw_arrow(ax, x1, y1, x2, y2, color=C_ARROW, lw=1.5, style='->'):
    """Draw an arrow."""
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle=style, color=color,
                               lw=lw, connectionstyle='arc3,rad=0'))

def draw_label(ax, x, y, text, fontsize=10, color=C_TEXT, ha='center', va='center',
               bold=False, style='normal'):
    weight = 'bold' if bold else 'normal'
    ax.text(x, y, text, ha=ha, va=va, fontsize=fontsize, color=color,
            fontweight=weight, fontstyle=style)

# ============================================================
# TITLE
# ============================================================
draw_label(ax, 8, 9.55, '图 5　三篇论文的理论整合框架', fontsize=14, bold=True, color='#111111')
draw_label(ax, 8, 9.15, '用户指令语用特征 → 智能体执行效果的三个分析层次', fontsize=9, color='#666666', style='italic')

# ============================================================
# LEVEL 3 — 整体语用结构 (PAPER 03) — TOP
# ============================================================
draw_box(ax, 0.3, 7.5, 15.4, 1.4, C_PAPER03, alpha=0.08, lw=2.5)
draw_label(ax, 8, 8.75, '层次三：整体语用结构类型', fontsize=12, bold=True, color=C_PAPER03)
draw_label(ax, 8, 8.45, 'Paper 03 — 潜类别分析 (LCA, k=5)', fontsize=8, color=C_PAPER03, style='italic')

# Five class boxes
classes = [
    ('动作导向型\n48.15%', '完成率最低\n路径稳定性中'),
    ('动作约束型\n9.03%', '路径最稳健\n完成率中等'),
    ('约束验证型\n4.19%', '完成率最高\n样本量最小'),
    ('对象/文件丰富型\n7.96%', '描述最充分\n效率中等'),
    ('极简型\n30.67%', '信息最少\n依赖智能体先验'),
]
class_colors = ['#E8A87C', '#F4A261', '#E76F51', '#2A9D8F', '#95A5A6']
for i, (name, desc) in enumerate(classes):
    cx = 1.5 + i * 2.85
    draw_solid_box(ax, cx - 1.15, 7.55, 2.3, 0.55, class_colors[i], name, fontsize=7.5)
    draw_label(ax, cx, 7.32, desc, fontsize=6.5, color='#555555')

# ============================================================
# LEVEL 2 — 语用成分密度 (PAPER 02) — MIDDLE
# ============================================================
draw_box(ax, 0.3, 5.2, 15.4, 1.7, C_PAPER02, alpha=0.08, lw=2.5)
draw_label(ax, 8, 6.75, '层次二：语用成分的密度 / 剂量效应', fontsize=12, bold=True, color=C_PAPER02)
draw_label(ax, 8, 6.45, 'Paper 02 — 约束密度的非线性效应（三阶段递进建模）', fontsize=8, color=C_PAPER02, style='italic')

# Stage boxes
draw_solid_box(ax, 1.5, 5.35, 3.5, 0.55, '#A23B72', 'Stage 1: 约束有无\nOR = 1.165***', fontsize=7.5)
draw_solid_box(ax, 6.25, 5.35, 3.5, 0.55, '#C77DB0', 'Stage 2: 全局密度\nb2 不显著 (p=.083)', fontsize=7.5)
draw_solid_box(ax, 11.0, 5.35, 3.5, 0.55, '#D4A0C0', 'Stage 3: 条件效应\n高难度拐点 ~1.9%', fontsize=7.5)
# Arrows between stages
draw_arrow(ax, 5.0, 5.62, 6.2, 5.62)
draw_arrow(ax, 9.75, 5.62, 10.95, 5.62)
draw_label(ax, 5.6, 5.78, '递进', fontsize=7, color=C_PAPER02)
draw_label(ax, 10.35, 5.78, '递进', fontsize=7, color=C_PAPER02)

# ============================================================
# LEVEL 1 — 单一语用成分 (PAPER 01 & PAPER 02) — BOTTOM
# ============================================================
draw_box(ax, 0.3, 2.9, 15.4, 1.7, C_PAPER01, alpha=0.08, lw=2.5)
draw_label(ax, 8, 4.45, '层次一：单一语用成分的存在 / 缺失', fontsize=12, bold=True, color=C_PAPER01)
draw_label(ax, 8, 4.15, 'Paper 01 — 验证信息（完成标准）　　Paper 02 (Stage 1) — 约束信息', fontsize=8, color=C_PAPER01, style='italic')

# Two component boxes
draw_solid_box(ax, 1.5, 3.05, 5.8, 0.55, '#2E86AB', '验证信息 (Paper 01)\nOR=1.255*** | IRR=0.883*** | 终止判准', fontsize=7.5)
draw_solid_box(ax, 8.7, 3.05, 5.8, 0.55, '#2E86AB', '约束信息 (Paper 02 Stage 1)\nOR=1.165*** | 边界资源', fontsize=7.5)

# ============================================================
# MODERATOR — right side
# ============================================================
draw_box(ax, 12.0, 3.2, 3.5, 5.5, C_MODERATOR, alpha=0.12, lw=2.5, ls='--')
draw_label(ax, 13.75, 8.5, '调节变量', fontsize=10, bold=True, color=C_MODERATOR)
draw_solid_box(ax, 12.3, 5.5, 2.9, 2.5, C_MODERATOR,
               '任务复杂度\n\n· 任务难度\n· 指令长度\n· 子任务数量\n\n约束效应在\n高复杂度下\n显著倒U形', fontsize=7.5)

# Moderator arrows
draw_arrow(ax, 12.0, 6.7, 8.7, 6.4, color=C_MODERATOR, lw=1.2, style='->')
draw_arrow(ax, 12.0, 6.2, 8.7, 5.62, color=C_MODERATOR, lw=1.2, style='->')
draw_arrow(ax, 12.0, 5.5, 8.7, 3.32, color=C_MODERATOR, lw=1.2, style='->')

# ============================================================
# UPWARD ARROWS — from Level 1 to Level 3
# ============================================================
# Level 1 → Level 2
draw_arrow(ax, 5.0, 4.6, 5.6, 5.2, color=C_ARROW, lw=2, style='->')
draw_arrow(ax, 11.0, 4.6, 10.4, 5.2, color=C_ARROW, lw=2, style='->')
draw_label(ax, 4.6, 4.9, '剂量化', fontsize=7.5, color=C_ARROW)
draw_label(ax, 11.4, 4.9, '剂量化', fontsize=7.5, color=C_ARROW)

# Level 2 → Level 3
draw_arrow(ax, 5.0, 6.9, 5.6, 7.5, color=C_ARROW, lw=2, style='->')
draw_arrow(ax, 11.0, 6.9, 10.4, 7.5, color=C_ARROW, lw=2, style='->')
draw_label(ax, 4.6, 7.2, '类型化', fontsize=7.5, color=C_ARROW)
draw_label(ax, 11.4, 7.2, '类型化', fontsize=7.5, color=C_ARROW)

# ============================================================
# OUTCOME — bottom
# ============================================================
draw_box(ax, 0.3, 1.5, 15.4, 0.9, C_OUTCOME, alpha=0.1, lw=2.5)
draw_label(ax, 8, 2.15, '执行效果（多维度评估）', fontsize=11, bold=True, color=C_OUTCOME)

outcome_items = [
    ('完成率', C_PAPER01),
    ('执行步数', C_PAPER01),
    ('路径稳定性', C_PAPER03),
    ('冗余步数比', C_PAPER02),
    ('错误模式', C_PAPER03),
]
for i, (name, col) in enumerate(outcome_items):
    ox = 2.5 + i * 2.7
    draw_solid_box(ax, ox - 1.0, 1.58, 2.0, 0.4, col, name, fontsize=7.5)

# Downward arrows from analysis levels
draw_arrow(ax, 2.5, 2.9, 2.5, 2.1, color=C_ARROW, lw=1.2)
draw_arrow(ax, 5.2, 2.9, 5.2, 2.1, color=C_ARROW, lw=1.2)
draw_arrow(ax, 8.0, 2.9, 8.0, 2.1, color=C_ARROW, lw=1.2)
draw_arrow(ax, 10.7, 2.9, 10.7, 2.1, color=C_ARROW, lw=1.2)
draw_arrow(ax, 13.5, 2.9, 13.5, 2.1, color=C_ARROW, lw=1.2)

# ============================================================
# BOTTOM NOTE
# ============================================================
draw_label(ax, 8, 1.0, '核心推论：指令效果 = f (语用成分剂量, 语用结构类型, 任务复杂度)',
           fontsize=9.5, bold=True, color='#333333', style='italic')

# ============================================================
# LEGEND (top right)
# ============================================================
draw_label(ax, 0.8, 9.3, '分析层次递进：单一成分存在 → 成分密度 → 结构类型',
           fontsize=7.5, color='#888888')

# Save
plt.tight_layout(pad=0.5)
fig.savefig(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'paper03_figures', 'fig5_conceptual_framework.png'),
            dpi=200, bbox_inches='tight', facecolor='#FAFAFA', edgecolor='none')
plt.close()
print("Concept figure saved to paper03_figures/fig5_conceptual_framework.png")
