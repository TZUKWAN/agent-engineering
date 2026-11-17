"""
helpers.py - Paper 01 公共工具函数
"""
import os
import re
import json
from typing import Dict, Any
import numpy as np
import pandas as pd

SEED = 42
np.random.seed(SEED)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA_PATH = os.path.join(PROJECT_ROOT, "data", "processed", "analysis_data.parquet")
STEPS_PATH = os.path.join(PROJECT_ROOT, "data", "interim", "steps.parquet")
RESULT_DIR = os.path.join(PROJECT_ROOT, "results", "papers", "paper01")

# 验证相关关键词（不区分大小写，尽量整词匹配）
V1_PATTERNS = {
    "check": re.compile(r"\bcheck(?:s|ing|ed)?\b", re.IGNORECASE),
    "verify": re.compile(r"\bverify(?:ing|ied)?\b", re.IGNORECASE),
    "confirm": re.compile(r"\bconfirm(?:ing|ed)?\b", re.IGNORECASE),
    "validate": re.compile(r"\bvalidat(?:e|ing|ed|ion)?\b", re.IGNORECASE),
    "ensure": re.compile(r"\bensure(?:s|d)?\b", re.IGNORECASE),
    "make sure": re.compile(r"\bmake sure\b", re.IGNORECASE),
}

V2_PATTERNS = {
    "done": re.compile(r"\bdone\b", re.IGNORECASE),
    "complete": re.compile(r"\bcomplet(?:e|ed|ion|ely)?\b", re.IGNORECASE),
    "correct": re.compile(r"\bcorrect(?:ly|ness)?\b", re.IGNORECASE),
    "proper": re.compile(r"\bproper(?:ly)?\b", re.IGNORECASE),
    "finished": re.compile(r"\bfinish(?:ed|ing|es)?\b", re.IGNORECASE),
    "ready": re.compile(r"\bready\b", re.IGNORECASE),
}

# V3 关键词：until/when/once/after
V3_PATTERNS = {
    "until": re.compile(r"\buntil\b", re.IGNORECASE),
    "when": re.compile(r"\bwhen\b", re.IGNORECASE),
    "once": re.compile(r"\bonce\b", re.IGNORECASE),
    "after": re.compile(r"\bafter\b", re.IGNORECASE),
}

ALL_VERIFICATION_PATTERNS = {**V1_PATTERNS, **V2_PATTERNS, **V3_PATTERNS}


def ensure_result_dir() -> None:
    os.makedirs(RESULT_DIR, exist_ok=True)


def load_main_data() -> pd.DataFrame:
    df = pd.read_parquet(DATA_PATH)
    df["task_completed_bool"] = df["task_completed"].map(
        {True: True, False: False, None: np.nan}
    )
    return df


def load_steps_data() -> pd.DataFrame:
    steps = pd.read_parquet(STEPS_PATH)
    steps["last_step_correct_bool"] = steps["last_step_correct"].map(
        {True: True, False: False, None: np.nan}
    )
    steps["last_step_redundant_bool"] = steps["last_step_redundant"].map(
        {True: True, False: False, None: np.nan}
    )
    return steps


def count_pattern_matches(text: str, patterns: Dict[str, re.Pattern]) -> int:
    if not isinstance(text, str):
        return 0
    count = 0
    for pat in patterns.values():
        count += len(pat.findall(text))
    return count


def get_match_positions(text: str, patterns: Dict[str, re.Pattern]):
    """返回所有匹配的起始位置列表"""
    if not isinstance(text, str):
        return []
    positions = []
    for pat in patterns.values():
        for m in pat.finditer(text):
            positions.append((m.start(), m.end()))
    positions.sort()
    return positions


def v3_present_heuristic(text: str) -> bool:
    """
    V3 条件验证式判定启发式：
    1. 出现 until 直接视为完成条件（until 天然带有终止含义）。
    2. 出现 when/once/after 时，仅当其前后 15 个词窗口内同时出现 V1 或 V2 关键词时，
       才视为“完成条件”；否则视为普通的时间/顺序状语，不计入 V3。
    """
    if not isinstance(text, str):
        return False
    tokens = text.split()

    def window_has_v1v2(start_idx):
        lo = max(0, start_idx - 15)
        hi = min(len(tokens), start_idx + 16)
        window_text = " ".join(tokens[lo:hi])
        return (
            count_pattern_matches(window_text, V1_PATTERNS) > 0
            or count_pattern_matches(window_text, V2_PATTERNS) > 0
        )

    for keyword, pat in V3_PATTERNS.items():
        for m in pat.finditer(text):
            if keyword == "until":
                return True
            # 找到 token 索引
            start_char = m.start()
            prefix = text[:start_char]
            token_idx = len(prefix.split())
            if window_has_v1v2(token_idx):
                return True
    return False


def classify_verification(text: str) -> Dict[str, Any]:
    """
    返回单条指令的验证特征字典：
    - v1_present, v2_present, v3_present
    - v1_count, v2_count, v3_count（用于 density 的原始频次）
    """
    v1_count = count_pattern_matches(text, V1_PATTERNS)
    v2_count = count_pattern_matches(text, V2_PATTERNS)
    v3_count = count_pattern_matches(text, V3_PATTERNS)
    v1_present = v1_count > 0
    v2_present = v2_count > 0
    v3_present = v3_present_heuristic(text)
    return {
        "v1_count": v1_count,
        "v2_count": v2_count,
        "v3_count": v3_count,
        "v1_present": bool(v1_present),
        "v2_present": bool(v2_present),
        "v3_present": bool(v3_present),
    }


def assign_verification_type(row: pd.Series) -> str:
    """
    根据 has_completion_criteria 与关键词存在情况分配 V0-V4：
    - V4：至少同时出现 V1/V2/V3 中的两类
    - V1/V2/V3：仅出现对应类别
    - V0：has_completion_criteria==1 但没有任何验证关键词（伪阳性或不可分类）
    """
    has_criteria = row.get("has_completion_criteria", 0)
    n_present = sum(
        [
            row.get("v1_present", False),
            row.get("v2_present", False),
            row.get("v3_present", False),
        ]
    )
    if n_present >= 2:
        return "V4"
    if row.get("v1_present", False):
        return "V1"
    if row.get("v2_present", False):
        return "V2"
    if row.get("v3_present", False):
        return "V3"
    if has_criteria == 1:
        return "V0"
    return "V0"


def compute_verification_density(row: pd.Series) -> float:
    """验证密度 = 验证相关关键词出现次数 / 总词数"""
    wc = row.get("word_count", 0)
    if pd.isna(wc) or wc <= 0:
        return 0.0
    total_matches = row.get("v1_count", 0) + row.get("v2_count", 0) + row.get("v3_count", 0)
    return float(total_matches) / float(wc)


def locate_first_verification_position(text: str) -> Dict[str, Any]:
    """
    定位第一条验证关键词在指令字符序列中的相对位置，并按 25%/50%/25% 分段。
    返回：relative_position（0-1）, position_region（start/middle/end/no_keyword）
    """
    if not isinstance(text, str) or len(text) == 0:
        return {"relative_position": np.nan, "position_region": "no_keyword"}
    positions = get_match_positions(text, ALL_VERIFICATION_PATTERNS)
    if not positions:
        return {"relative_position": np.nan, "position_region": "no_keyword"}
    rel = positions[0][0] / len(text)
    if rel < 0.25:
        region = "start"
    elif rel < 0.75:
        region = "middle"
    else:
        region = "end"
    return {"relative_position": float(rel), "position_region": region}


def make_analysis_subset(df: pd.DataFrame, y_col: str) -> pd.DataFrame:
    """通用分析子集：删除核心变量缺失的行"""
    cols = [y_col, "has_completion_criteria", "task_difficulty", "word_count", "os"]
    return df.dropna(subset=cols).copy()


def serialize(obj: Any) -> Any:
    """将 numpy/pandas 类型转为原生 Python 类型，便于 JSON 序列化"""
    if isinstance(obj, (np.integer, np.floating, np.bool_)):
        return obj.item()
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, pd.Series):
        return obj.to_dict()
    if isinstance(obj, dict):
        return {k: serialize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [serialize(v) for v in obj]
    if pd.isna(obj):
        return None
    return obj


def save_json_csv(results: Dict[str, Any], json_path: str, csv_path: str = None) -> None:
    ensure_result_dir()
    if csv_path is None:
        csv_path = json_path.replace(".json", ".csv")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(serialize(results), f, ensure_ascii=False, indent=2)
    # CSV 保存：如果 results 包含顶层表格列表则直接写；否则转置为 DataFrame
    if isinstance(results, dict) and "rows" in results:
        pd.DataFrame(results["rows"]).to_csv(csv_path, index=False, encoding="utf-8-sig")
    elif isinstance(results, list):
        pd.DataFrame(results).to_csv(csv_path, index=False, encoding="utf-8-sig")
    elif isinstance(results, dict):
        # 尝试把最可能的表格字段提取出来；否则按 key-value 写
        candidate_keys = [k for k in results.keys() if isinstance(results[k], list) and len(results[k]) > 0]
        if candidate_keys:
            pd.DataFrame(results[candidate_keys[0]]).to_csv(csv_path, index=False, encoding="utf-8-sig")
        else:
            pd.DataFrame([{"key": k, "value": v} for k, v in results.items()]).to_csv(
                csv_path, index=False, encoding="utf-8-sig"
            )
    print(f"Saved: {json_path} and {csv_path}")


def extract_model_table(result, exponentiate: bool = False) -> pd.DataFrame:
    """从 statsmodels 结果对象提取系数表"""
    params = result.params
    conf = result.conf_int(alpha=0.05)
    conf.columns = ["ci_low", "ci_high"]
    pvalues = result.pvalues
    table = pd.DataFrame(
        {
            "term": params.index,
            "coef": params.values,
            "std_err": result.bse.values,
            "z": result.tvalues.values,
            "p_value": pvalues.values,
            "ci_low": conf["ci_low"].values,
            "ci_high": conf["ci_high"].values,
        }
    )
    if exponentiate:
        table["or"] = np.exp(table["coef"])
        table["ci_low_or"] = np.exp(table["ci_low"])
        table["ci_high_or"] = np.exp(table["ci_high"])
    return table
