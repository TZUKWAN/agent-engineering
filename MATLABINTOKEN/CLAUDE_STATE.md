# CLAUDE_STATE.md — 三篇论文重写与交叉审校项目

## 当前目标
完成三篇学术论文（Paper 01/02/03）的全面重写与交叉审校，并合并为一份完整研究报告Word文档。**全部DOCX已交付。**
**✅ 统一编号 LaTeX PDF 已交付（2026-06-22）。**

## 任务清单
- [x] Paper 01 重写 → `revised/paper01_rewritten.md` (390行)
- [x] Paper 02 重写 → `revised/paper02_rewritten.md` (~470行)
- [x] Paper 03 重写 → `revised/paper03_rewritten.md` (~490行)
- [x] 三篇交叉审校 (四个维度全部通过)
- [x] Paper 02 补全：fig5_难度调节效应.png 嵌入为图5，后续图编号全部顺延
- [x] Paper 03 补全：用 matplotlib 生成 fig5_conceptual_framework.png 概念框架图并嵌入 §5.3
- [x] **单篇DOCX导出**：pandoc 将三篇 Markdown 转为 Word 格式，图片全部嵌入
  - `paper01_rewritten.docx` (851KB, 7 images)
  - `paper02_rewritten.docx` (921KB, 9 images)
  - `paper03_rewritten.docx` (932KB, 5 images)
- [x] **合并研究报告DOCX**：三篇论文合并为一个完整Word文档
  - `研究报告_AgentNet语用特征三部曲.docx` (2674KB, 21 images, 1326行源文件)
  - 字体：宋体 + Times New Roman ✓
  - 页面：A4，标准页边距 ✓
  - 合并文件：`merged_report.md` (124KB)
  - 转换脚本：`merge_and_convert.py`
  - 定制参考文档：`reference_custom.docx`（由 `customize_reference.py` 生成）
- [x] 添加综合摘要（三层次递进框架概述）
- [x] 添加综合讨论与展望（理论贡献、实践启示、局限与未来方向）
- [x] 合并并去重参考文献
- [x] 添加统一附录（补充数据文件索引）
- [ ] (可选) Paper 01 图编号重排序 (当前非顺序: 1→2→5→6→7→3→4)
- [ ] (可选) 清理生成脚本

## 交付物

### 主要交付物（最终版）
- **`D:\MATLABINTOKEN\revised\研究报告_AgentNet语用特征三部曲.docx`** (2674KB, 21 images)
  - 第1部分：完成标准作为终止判准 (7图)
  - 第2部分：约束何时成为负荷 (9图)
  - 第3部分：语用结构类型学 (5图)
  - 综合讨论与展望 + 参考文献 + 附录

### Word 文档（单篇版）
- `D:\MATLABINTOKEN\revised\paper01_rewritten.docx`
- `D:\MATLABINTOKEN\revised\paper02_rewritten.docx`
- `D:\MATLABINTOKEN\revised\paper03_rewritten.docx`

### Markdown 源文件
- `D:\MATLABINTOKEN\revised\paper01_rewritten.md` (390行, 7图5表)
- `D:\MATLABINTOKEN\revised\paper02_rewritten.md` (~470行, 9图10表)
- `D:\MATLABINTOKEN\revised\paper03_rewritten.md` (~490行, 5图+表)
- `D:\MATLABINTOKEN\revised\merged_report.md` (1326行, 21图, 124KB)

### 生成脚本
- `D:\MATLABINTOKEN\revised\customize_reference.py` — 定制pandoc reference docx字体样式
- `D:\MATLABINTOKEN\revised\merge_and_convert.py` — 合并三篇Markdown并转换为DOCX
- `D:\MATLABINTOKEN\revised\generate_concept_figure.py` — Paper 03 图5概念框架图
- `D:\MATLABINTOKEN\revised\verify_merged.py` — 验证合并markdown结构

### 图表资源
- `D:\MATLABINTOKEN\revised\paper01_figures/`: 7 PNGs
- `D:\MATLABINTOKEN\revised\paper02_figures/`: 9 PNGs
- `D:\MATLABINTOKEN\revised\paper03_figures/`: 5 PNGs
- `D:\MATLABINTOKEN\revised\paper01_tables/`: 3 CSV files
- `D:\MATLABINTOKEN\revised\paper02_tables/`: 11 files
- `D:\MATLABINTOKEN\revised\paper03_tables/`: 4 files

## LaTeX 学术排版子项目 ✅ 已完成

### 目标
将 `merged_report.md` 转换为符合学术排版规范的 LaTeX PDF。

### 交付物
- **`D:\MATLABINTOKEN\revised\merged_report.pdf`** (3,620,928 bytes, **61页**) — 最终PDF
- **`D:\MATLABINTOKEN\revised\merged_report.tex`** (1996行, 74KB) — 生成的LaTeX源文件
- **`D:\MATLABINTOKEN\revised\md2latex.py`** (~650行) — Markdown→LaTeX 转换脚本
- **`D:\MATLABINTOKEN\revised\merged_report.log`** — 编译日志

### 编译状态（最终）
| 指标 | 结果 |
|------|------|
| 编译错误 | **0** ✅ |
| 缺失字符 | **0** ✅ |
| Overfull hbox (表格) | **0** ✅ (adjustbox 全部消除) |
| Overfull hbox (段落文本) | **9** (长文件路径/变量名，LaTeX无法断词，可接受) |
| Bookmark层级警告 | **6** (源文档 subsubsection 直接出现在 section 下) |
| SimSun粗体/斜体回退 | 字体本身限制，无实际影响 |
| 总页数 | **61** |

### 结构统计（最终 .tex）
| 元素 | 数量 |
|------|------|
| `\chapter{}` | 5 |
| `\chapter*{}` | 1 |
| `\section{}` | 10 |
| `\subsection{}` | 23 |
| `\subsubsection{}` | 68 |
| `\begin{figure}` | 21 |
| `\begin{table}` | 25 |
| 表格标题 `\caption{表...}` | 25/25 ✅ |
| 图片标题 `\caption{图...}` | 21/21 ✅ |
| `\bibitem{}` | 15 |
| `\begin{enumerate}` | 14 |
| `\begin{itemize}` | 11 |
| `\adjustbox{}` 包裹表格 | 25/25 ✅ |
| 三线表 (`\toprule`/`\midrule`/`\bottomrule`) | 25/25 ✅ |

### 排版规范落实
| 规范 | 状态 |
|------|------|
| 中文宋体 + 英文 Times New Roman | ✅ fontspec 配置 |
| A4页面 (上下2.54cm, 左右3.18cm) | ✅ geometry |
| 1.5倍行距 | ✅ setspace |
| 三线表 (booktabs) | ✅ 25/25 |
| 浮动图 (figure [htbp]) | ✅ 21/21 |
| 自动目录 (TOC) | ✅ (两次 xelatex) |
| 页眉页脚 (fancyhdr) | ✅ headheight=27pt |
| XeLaTeX 编译 | ✅ TeX Live 2026 |

### 修复历程
1. headheight 警告 → 27pt + topmargin -12pt
2. 24 overfull hbox (表格极端溢出) → adjustbox{max width=\textwidth} 全部消除
3. 25个表格全部缺少 caption → pending_caption 状态机 + 正则捕获 `**表 X：...**`
4. 9个段落文本 overfull → 确认均为长路径/变量名，LaTeX无法断词，可接受

### 残余风险
1. Paper 01 图编号非顺序(1→2→5→6→7→3→4)，不影响理解
2. generate_concept_figure.py 等脚本可保留或删除
3. merged_report.md 中图片路径仍引用子目录（paper01_figures/ 等），但DOCX已通过pandoc正确嵌入，不影响最终交付
4. **LaTeX PDF**: 9个段落文本 overfull（长文件路径，可接受）
5. **LaTeX PDF**: 6个 bookmark 层级跳跃（源文档 subsubsection 结构问题）
6. **LaTeX PDF**: SimSun 无原生粗体/斜体（字体限制，LaTeX自动替代）

## LaTeX 统一编号重构子项目 ✅ 已完成 (2026-06-22)

### 目标
重构 `merged_report.md`：删除所有原文编号，按顺序重新编号标题和图表，融合为统一研究报告，生成 LaTeX PDF。

### 核心改造
1. **三部分→五章统一结构**：
   - 第一章 导论（新增）
   - 第二章 完成标准与执行终止（原Paper01）
   - 第三章 约束密度的条件性效应（原Paper02）
   - 第四章 语用结构类型学（原Paper03）
   - 第五章 综合讨论与展望

2. **图表统一连续编号**：21图（图1-21）+ 30表（表1-29数据表 + 表30文件索引）

3. **占位符两步法**：Phase 1 用唯一占位符（`__FIGREF_ch2_7__`等）替换旧编号；Phase 2 解析为实际新编号，彻底避免级联替换bug

4. **章节过渡段落**：每章开头添加逻辑递进过渡，体现"成分→剂量→结构→整合"三层次框架

### 修复的关键bug
- 级联替换bug（置换映射导致新编号被二次匹配）
- 附录表跨key引用未更新（appendix_p02→ch3, appendix_p03→ch4）
- "Paper 01/02"→"第二章/02"残留（组合引用模式）
- 字母数字混合键排序（A1, A2）
- Ch5无过渡段落 + `---`/`\newpage`重复

### 交付物
- **`merged_report_unified.pdf`** (3.47 MB, **65页**) — 最终PDF
- **`merged_report_unified.tex`** (2057行) — LaTeX源文件
- **`merged_report_unified.md`** (1375行) — Markdown中间文件
- **`restructure_report.py`** (~400行) — 重构脚本（占位符两步法）
- **`renumbering_map.txt`** — 图21+表30映射日志

### 编译状态
| 指标 | 结果 |
|------|------|
| 编译错误 | **0** ✅ |
| Overfull hbox | **10**（长文件路径/变量名，可接受）|
| Bookmark层级警告 | **6**（同原始版）|
| 三线表 (booktabs) | 29/29 ✅ |
| adjustbox 包裹表格 | 29/29 ✅ |
| 浮动图 (figure [htbp]) | 21/21 ✅ |
| 总页数 | **65** |

### 残余风险
1. 10个 overfull hbox（长文件路径，与原始版同类问题，可接受）
2. 6个 bookmark 层级跳跃（源文档结构问题）
3. SimSun 无原生粗体/斜体（字体限制）
