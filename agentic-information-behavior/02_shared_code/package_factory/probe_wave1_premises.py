"""EXP-0118: structural census of the columns wave 1's designs assume, run before any dependent variable is read.

The six wave-1 designs (T101, T103, T106, T108, T109, T110) take trajectory behaviour as a dependent variable - search
depth, clarification turns, wrong-tool selection, reformulation count. That assumes Toucan's `messages` column holds an
agent trajectory with tool calls and observations. If it holds only the synthetic user/assistant dialogue that produced
the query, four of the six designs have no DV and must be re-scoped *now*, before a protocol is frozen on a false
premise - the mistake this programme has already made and logged once (an environment claim asserted from a README).

This is a schema and structure census only: role inventories, turn counts, marker shares. It computes no relationship
between any feature and any outcome, so it cannot inform a threshold; every threshold in
`topic_designs_wave1.py` was written before this file ran.

    python 02_shared_code/package_factory/probe_wave1_premises.py
"""
from __future__ import annotations

import collections, datetime, json, pathlib, re, sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = next(a for a in (HERE, *HERE.parents) if (a / "00_program_registry").is_dir())
sys.path.insert(0, str(ROOT / "02_shared_code"))
import pandas as pd  # noqa: E402

DATASETS = ROOT.parent / "MATLABINTOKEN" / "datasets"
_cand = [d for d in DATASETS.rglob("*") if d.is_dir() and "toucan" in d.name.lower()] if DATASETS.is_dir() else []
TOUCAN = next((d for d in _cand if any(d.rglob("*.parquet"))), None)

CALL_MARK = re.compile(r"<tool_call|tool_call\s*:|function=|def \w+\(|```python|execute\(|action\s*[:=]", re.I)
OBS_MARK = re.compile(r"<observation|<result|tool response|stdout|exit code", re.I)
CLAR_MARK = re.compile(r"\b(could you|can you clarify|which one|do you mean|need more information|unclear)\b", re.I)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    if TOUCAN is None:
        sys.exit("ABORT: the Toucan release directory is not where the estate audit says it is")
    files = sorted(TOUCAN.rglob("*.parquet"))
    out = {"exp_id": "EXP-0118", "release": str(TOUCAN), "n_parquet_files": len(files),
           "started_at": datetime.datetime.now().isoformat(timespec="seconds"), "configs": {}}
    for cfg in ("OSS", "Qwen3", "Kimi-K2"):
        # the configs are directories in this release (Toucan-1.5M/{OSS,Qwen3,Kimi-K2,SFT}/train-*.parquet), and the
        # first probe looked inside file names only, so it found nothing and - because all() over an empty list is
        # True - reported every premise as satisfied
        f = next((x for x in files if x.parent.name.lower() == cfg.lower()
                  or f"routing_{cfg}" in x.name.lower()), None)
        if f is None:
            out["configs"][cfg] = {"error": "no shard found for this config"}
            continue
        df = pd.read_parquet(f)
        df = df[df.get("subset_name", "").astype(str).str.contains("single-turn-original", na=False)] \
            if "subset_name" in df else df
        df = df.head(4000)
        roles, turns, has_call, has_obs, has_clar, nonempty_q, gold_present = (collections.Counter(), [], 0, 0, 0, 0, 0)
        for m in df["messages"].astype(str):
            try:
                obj = json.loads(m)
            except Exception:
                obj = None
            if isinstance(obj, list):
                for t in obj:
                    roles[str((t or {}).get("role") or (t or {}).get("from") or "?")] += 1
                turns.append(len(obj))
                blob = " ".join(str((t or {}).get("content") or (t or {}).get("value") or "") for t in obj)
            else:
                turns.append(1)
                blob = m
            has_call += bool(CALL_MARK.search(blob))
            has_obs += bool(OBS_MARK.search(blob))
            has_clar += bool(CLAR_MARK.search(blob))
        n = max(1, len(df))
        out["configs"][cfg] = {
            "rows_sampled": int(n), "columns": sorted(df.columns.tolist()),
            "role_inventory": dict(roles.most_common(12)),
            "turns_per_row": {"mean": round(sum(turns) / len(turns), 3), "max": max(turns),
                              "share_rows_gt_2": round(sum(1 for x in turns if x > 2) / n, 4)},
            "share_with_tool_call_marker": round(has_call / n, 4),
            "share_with_observation_marker": round(has_obs / n, 4),
            "share_with_clarification_marker": round(has_clar / n, 4),
            "question_non_empty": round(float((df["question"].astype(str).str.len() > 0).mean()), 4)
            if "question" in df else None,
            "target_tools_non_empty": round(float((df["target_tools"].astype(str).str.len() > 2).mean()), 4)
            if "target_tools" in df else None,
            "available_tools_non_empty": round(float((df["available_tools"].astype(str).str.len() > 2).mean()), 4)
            if "available_tools" in df else None,
            "shard": f.name,
        }
    got = [c for c in out["configs"].values() if "error" not in c]
    if not got:
        # a census that measured nothing must say so, not print a clean verdict
        out["verdict"] = {"trajectory_dvs_measurable": "not_measured", "clarification_dv_measurable": "not_measured",
                          "retrieval_dvs_measurable": "not_measured",
                          "note": "no shard was read, so no premise of wave 1 is confirmed or refuted by this run"}
        print("  verdict: NOT MEASURED - no shard matched", {k: v.get("error") for k, v in out["configs"].items()})
        (ROOT / "results_raw" / f"EXP0118_wave1_premise_census_{datetime.datetime.now():%Y%m%dT%H%M%S}.json").write_text(
            json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
        return 1
    verdict = {
        "trajectory_dvs_measurable": all(c.get("share_with_tool_call_marker", 0) > 0.3 for c in
                                         out["configs"].values() if "error" not in c),
        "clarification_dv_measurable": all(c.get("share_with_clarification_marker", 0) > 0.02 for c in
                                           out["configs"].values() if "error" not in c),
        "retrieval_dvs_measurable": all(c.get("target_tools_non_empty", 0) > 0.9 and c.get("available_tools_non_empty", 0) > 0.9
                                        for c in out["configs"].values() if "error" not in c),
        "n_configs_measured": len(got),
    }
    out["verdict"] = verdict
    dest = ROOT / "results_raw" / f"EXP0118_wave1_premise_census_{datetime.datetime.now():%Y%m%dT%H%M%S}.json"
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    for cfg, c in out["configs"].items():
        print(f"  {cfg}: rows={c.get('rows_sampled')} call_marker={c.get('share_with_tool_call_marker')} "
              f"obs={c.get('share_with_observation_marker')} clar={c.get('share_with_clarification_marker')} "
              f"turns>2={c.get('turns_per_row', {}).get('share_rows_gt_2')} roles={list(c.get('role_inventory', {}))[:6]}")
    print("  verdict:", verdict)
    print(f"  wrote {dest.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
