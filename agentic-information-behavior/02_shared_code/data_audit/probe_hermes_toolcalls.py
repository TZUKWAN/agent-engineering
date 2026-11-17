"""EXP-0023a: can lambda/hermes-agent-reasoning-traces supply a routing outcome at all?

EXP-0022 found a `tools` column in the hermes corpus - the only catalogue outside Toucan among the
eight local corpora - but a column name is not evidence that the corpus is usable (spec 05.04: a
README claim is never a data fact). This probe reads real rows and answers the three questions that
decide whether it can serve as E08's independent catalogue:

  1. is the candidate set per row or one global fixed list, and how large is it;
  2. is the tool the reference model actually invoked recoverable from `conversations`, and in what
     encoding (a dedicated role, a JSON block inside the assistant text, an XML-ish tag);
  3. what fraction of rows therefore yield a gold tool that exists in that row's own catalogue.

Read-only; writes results_raw/EXP0023a_hermes_toolcall_feasibility_*.json.
"""

from __future__ import annotations

import glob
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(r"G:/刘俊琦/AGENT ENGINEERING/MATLABINTOKEN/datasets/lambda/hermes-agent-reasoning-traces")
ROWS = 3000
CALL_MARKERS = {
    "role_function_call": lambda m: m["from"] == "function_call",
    "json_block_in_gpt": lambda m: m["from"] == "gpt" and '"name"' in str(m["value"]),
    "xml_tool_call_tag": lambda m: re.search(r"<(?:tool_call|function_call|assistant_call)", str(m["value"])),
}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    files = [f for f in sorted(glob.glob(str(DATA / "**/*.parquet"), recursive=True)) if ".cache" not in f]
    res = {"exp_id": "EXP-0023a", "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "shards": len(files)}
    roles, cat_sizes, fps, parsed = Counter(), Counter(), Counter(), Counter()
    gold_examples, first_call, human_len = [], Counter(), []
    rows_read = 0
    for f in files:
        if rows_read >= ROWS:
            break
        t = pq.read_table(f, columns=["id", "conversations", "tools", "category", "task"])
        take = min(t.num_rows, ROWS - rows_read)
        for r in t.slice(0, take).to_pylist():
            rows_read += 1
            cat = json.loads(r["tools"]) if isinstance(r["tools"], str) else r["tools"]
            names = [d.get("name") for d in cat if isinstance(d, dict)]
            cat_sizes[len(names)] += 1
            fps[hash(tuple(sorted(names)))] += 1
            for m in r["conversations"]:
                roles[m["from"]] += 1
            for label, test in CALL_MARKERS.items():
                hits = [m for m in r["conversations"] if test(m)]
                if hits:
                    parsed[label] += 1
            calls = []
            for m in r["conversations"]:
                if m["from"] != "gpt":
                    continue
                v = str(m["value"])
                try:
                    obj = json.loads(v)
                    if isinstance(obj, dict) and obj.get("name"):
                        calls.append(str(obj["name"]))
                        continue
                except Exception:
                    pass
                mm = re.search(r"<function=([A-Za-z0-9_\-]+)>|<tool_call[^>]*>\s*([A-Za-z0-9_\-]+)", v)
                if mm:
                    calls.append(mm.group(1) or mm.group(2))
            if calls:
                parsed["resolved_json_or_tag_call"] += 1
                first_call[calls[0]] += 1
                if not gold_examples:
                    gold_examples = calls[:3]
            if r.get("task"):
                human_len.append(len(str(r["task"]).split()))
        if rows_read >= ROWS:
            break
    res["rows_read"] = rows_read
    res["message_roles"] = dict(roles)
    res["catalogue_size_distribution"] = dict(cat_sizes)
    res["distinct_catalogue_fingerprints"] = len(fps)
    res["call_marker_row_counts"] = dict(parsed)
    res["first_called_tool_distribution"] = dict(first_call.most_common(12))
    res["example_resolved_calls"] = gold_examples
    res["task_field_length_words_p50"] = int(sorted(human_len)[len(human_len) // 2]) if human_len else None
    res["decision"] = ("usable as an unseen-tool-universe transfer set" if first_call
                       else "NOT USABLE: no tool invocation recoverable from conversations")
    if not first_call:
        res["raw_gpt_message_sample"] = [str(m["value"])[:600] for m in
                                         pq.read_table(files[0], columns=["conversations"])
                                         .slice(0, 1).to_pylist()[0]["conversations"][:6]]
    out = ROOT / "results_raw" / f"EXP0023a_hermes_toolcall_feasibility_{time.strftime('%Y%m%dT%H%M%S')}.json"
    out.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "raw_gpt_message_sample"},
                     indent=1, ensure_ascii=False)[:2500])
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
