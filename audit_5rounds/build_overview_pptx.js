// 单页白底总览：工作空间 75 篇论文
const pptxgen = require("pptxgenjs");
const path = require("path");

const BASE = "G:/刘俊琦/AGENT ENGINEERING/agentic-information-behavior/papers";
const OUT = "G:/刘俊琦/AGENT ENGINEERING/智能体信息行为研究总览.pptx";

const P = "#1a5276";      // 主色（与系列图一致的深蓝）
const TXT = "#1f2937";    // 正文
const MUT = "#64748b";    // 弱化
const CAP = "#334155";    // 图注

let pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.33 x 7.5
pres.author = "Agent Information Behavior Lab";
pres.title = "智能体信息行为研究总览";

let s = pres.addSlide();
s.background = { color: "FFFFFF" };

const M = 0.35, W = 13.33;
const CW = W - 2 * M;

// ---------- 标题 ----------
s.addText([
  { text: "智能体信息行为的全谱系测量", options: { color: P, bold: true, fontSize: 23 } },
  { text: "    70 个研究包 · 12 个数据波（wave-2 → wave-12）· 75 篇论文全部交付", options: { color: MUT, fontSize: 12.5 } },
], { x: M, y: 0.14, w: CW, h: 0.52, fontFace: "微软雅黑", margin: 0, valign: "middle" });

// ---------- 总结段（主题/方法/发现） ----------
const summary = [
  { text: "研究主题　", options: { bold: true, color: P, fontSize: 9.5 } },
  { text: "以信息行为学经典理论（需求→寻求→评价→利用→停止）为框架，对 LLM 智能体在真实工具检索任务中的信息搜寻行为做全谱系、预注册式测量：从任务指令的语言学形态（欠明确性、约束密度、歧义），到工具目录元数据（命名一致性、描述粒度、MCP 生态），到单轨迹的话语与自省语言、多 rollout 的序列语法与依赖网络，再到记忆压缩与组织知识复用——约 31 万行指令-候选数据、20 万条轨迹回合、14,000 次视觉推理步。", options: { color: TXT, fontSize: 9 } },
  { text: "  主要方法　", options: { bold: true, color: P, fontSize: 9.5 } },
  { text: "70 个包走同一套冻结纪律：协议与阈值在读数之前冻结；前提普查先行，kill gate 诚实拦截了 12 个量尺无变异或基底缺失的设计；query/turn/trajectory/instance 级聚类稳健推断与 cluster bootstrap、Holm 校正；判定词（supported / null / opposite / partial / not_testable / 准分离扣留）由冻结句机械产出，负结果照档不掩盖，全部数字可由包内 results_raw 工件复算。", options: { color: TXT, fontSize: 9 } },
  { text: "  主要发现　", options: { bold: true, color: P, fontSize: 9.5 } },
  { text: "行为可预测性的大头是共享结构而非任务特异：动作词频 64% + 跨任务共享顺序 29%，任务方言仅 7%；语言-结局呈「窄门」格局——轨迹长度与任务难度主导结局，真正穿透的是话语功能（结果话语在成功轨迹中出现率 89% 对 38%，β=3.11），而计划枚举、语言具体性要么无效要么反向；自省语言分层诚实——「重新考虑」必兑现（仪式率 0%）而「我错了」与机器错误仪表几乎不重叠（κ≈0.002）；治理机会明确——知识入库按成本排序（86.8% 的成功实例存在更便宜教材）、记忆压缩必须保尾部（头截断最先灭掉结果话语）；生态短板量化——8 个语料库中带结局标签者仅 3 个，来源归属与努力预算构念各仅 1/8 可测。", options: { color: TXT, fontSize: 9 } },
];
s.addText(summary, { x: M, y: 0.70, w: CW, h: 1.72, fontFace: "微软雅黑", margin: 0, valign: "top", lineSpacingMultiple: 1.12, align: "left" });

// ---------- 分隔细线 ----------
s.addShape(pres.shapes.LINE, { x: M, y: 2.52, w: CW, h: 0, line: { color: "CBD5E1", width: 0.75 } });

// ---------- 图网格 2 行 × 5 列 ----------
const GAP = 0.10;
const cellW = (CW - GAP * 4) / 5;
const IMG_H = 1.74;
const rows = [
  { y: 2.64 },
  { y: 4.76 },
];
const figs = [
  ["P050_a_cross_task_grammar_of_agent_search/fig1_ladder.png", "跨任务语法似然阶梯：词频 64% · 顺序 29% · 方言 7%"],
  ["P062_discourse_structure_of_successful_and_failed_searches/fig1_discourse.png", "成功 vs 失败的话语落差：结果话语 89% vs 38%"],
  ["P051_early_signals_of_agent_search_failure/fig1_auc_ladder.png", "早期信号：行为特征 0.686 输给长度基线 0.860"],
  ["P056_the_implicit_information_need/fig2_specificity.png", "覆盖的特异性检验：词汇歧义以 340 倍主导"],
  ["P044_tool_dependency_network/fig1_network.png", "工具依赖网络：高频对重叠 12 倍于随机"],
  ["P065_what_a_compression_loses_first/fig1_survival.png", "记忆压缩损耗：头截断先灭结果话语（3.4%）"],
  ["P053_which_rollouts_deserve_reuse/fig1_selection.png", "知识挑选：两规则 τ=0.04，86.8% 有更便宜成功"],
  ["P068_corrective_and_ritual_reflection/fig1_reflection.png", "反思审计：标记后想法重合 3.1%（换血），零仪式"],
  ["P069_case_based_reuse_of_historical_trajectories/fig2_bands.png", "案例复用三连否定：相似带完成率 21 倍梯度"],
  ["P070_agent_trajectory_corpora_as_intelligence_sources/fig2_matrix.png", "收官：8 语料 × 8 构念支持矩阵"],
];
figs.forEach((f, i) => {
  const row = Math.floor(i / 5), col = i % 5;
  const x = M + col * (cellW + GAP);
  const y = rows[row].y;
  s.addImage({
    path: path.join(BASE, f[0]),
    x: x, y: y,
    sizing: { type: "contain", w: cellW, h: IMG_H },
  });
  s.addText(f[1], {
    x: x, y: y + IMG_H + 0.03, w: cellW, h: 0.32,
    fontFace: "微软雅黑", fontSize: 8, color: CAP, align: "left", valign: "top", margin: 0,
  });
});

// ---------- 页脚 ----------
s.addText("图均由各研究包 results_raw 工件直接生成、可复算（判定词由冻结句机械产出）　|　论文交付：papers/<包名>/paper_cn.docx（53 篇中文 ≥9,000 字 + 5 篇英文 + 12 份封锁状态报告）+ MATLAB 5 篇", {
  x: M, y: 7.12, w: CW, h: 0.26, fontFace: "微软雅黑", fontSize: 8.5, color: MUT, margin: 0,
});

pres.writeFile({ fileName: OUT }).then(() => console.log("written:", OUT));
