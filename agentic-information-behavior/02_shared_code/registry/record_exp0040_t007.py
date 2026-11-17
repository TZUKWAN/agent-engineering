"""Record EXP-0040's negative identifiability result: T007 cannot be a tool-taxonomy paper.

The pilot measured the three things a scheme-induction study needs and found they never co-occur in this corpus
estate. The result is written into the ranked queue document and the topic registry, and the topic is closed
rather than re-scoped (spec section 3: weak topics are killed by pilots, and a topic must not be rescued by
narrowing its question after the fact).
"""
from __future__ import annotations

import csv, glob, io, json, pathlib, time

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
f40 = pathlib.Path(sorted(glob.glob(str(ROOT / "results_raw/EXP0040_taxonomy_label_pilot_*.json")))[-1])
e40 = json.loads(f40.read_text(encoding="utf-8"))
c = e40["corpora"]
her, tc, ab = c["hermes-agent-reasoning-traces"], c["Toucan-1.5M"], c["AgentBank"]

BLOCK = f"""
## Superseded by a pilot: T007 is killed by measurement (EXP-0040, {time.strftime('%Y-%m-%d %H:%M')})

The ranking above put T007 first because nothing collided with it. Its real constraint is identifiability, and
EXP-0040 measured it: a scheme-induction study needs many items to cluster, a human category scheme to validate
against, and both on the SAME unit. In this corpus estate the three conditions never co-occur.

| corpus | what it offers | what it lacks |
|---|---|---|
| Toucan-1.5M | {tc['distinct_tools_seen']:,} distinct tool names, per-item catalogue on {tc['per_item_catalogue_present_share']:.0%} of rows | any human category scheme - its only label column is `subset_name` (cardinality {max([v['cardinality'] for v in tc['labels'].values()])}), i.e. provenance, not a taxonomy |
| hermes traces | human labels: category={her['labels']['category']['cardinality']}, subcategory={her['labels']['subcategory']['cardinality']} over {her['rows_read']:,} items | tool universe: only {her['distinct_tools_seen']} distinct tool names, so a {her['labels']['subcategory']['cardinality']}-way scheme over {her['distinct_tools_seen']} tools is degenerate |
| AgentBank | a 19-way human task scheme (the environment directory split) over {ab['rows_total']:,} items | a tool catalogue - the shards carry {sorted(ab['columns_present'])} only, so there is nothing to induce a tool taxonomy from |

**Decision recorded by the pre-registered rule:** `{e40['verdict']['decision']}`
(qualifying corpora = {e40['verdict']['qualifying_corpora']}, needed 2).

T007 is therefore killed as a standalone paper rather than re-scoped into something smaller. The hermes finding
({her['distinct_tools_seen']} distinct tool names across {her['rows_read']:,} items) is a second independent
measurement of the same catalogue-poverty that P001's EXP-0020/0023 reported, and is worth citing there.
The AgentBank 19-environment split remains usable as a *task-level* stratifier, which is how P001 already uses it.
"""
doc = ROOT / "docs/top10_screening_20260919.md"
t = doc.read_text(encoding="utf-8")
if "T007 is killed by measurement" not in t:
    doc.write_text(t.rstrip() + "\n" + BLOCK + "\n", encoding="utf-8")
    print("appended the measured T007 closure to docs/top10_screening_20260919.md")

reg = ROOT / "00_program_registry/experiment_registry.csv"
rows = list(csv.reader(io.StringIO(reg.read_text(encoding="utf-8"))))
h = rows[0]
rec = dict(zip(h, ["EXP-0040", "T007", "pilot_DONE_NO_GO",
                   "02_shared_code/data_audit/taxonomy_label_pilot_t007.py",
                   "hermes (category/subcategory + tools), Toucan OSS (subset_name + target_tools + "
                   "available_tools), AgentBank (19 environment dirs as the human label); 20,000 rows per corpus, "
                   "label cardinality, labelled coverage, distinct tool names, per-item catalogue share",
                   "", e40["started_at"], e40["finished_at"], "failed_pilot_NO_GO_topic_killed",
                   f"results_raw/{f40.name}",
                   "Pre-registered GO needed 2 corpora with label cardinality>=8, >=300 distinct labelled tools and "
                   f"a per-item catalogue; measured qualifying corpora = {e40['verdict']['qualifying_corpora']}. "
                   f"Toucan has {tc['distinct_tools_seen']} tools but no human categories (subset_name only); "
                   f"hermes has a 9/26-way human scheme but only {her['distinct_tools_seen']} distinct tool names; "
                   f"AgentBank has 19 environments but no tool column. Topic killed, not re-scoped. First run "
                   "reported rows=0 for AgentBank because the label lives in the directory name, and 0 tools for "
                   "hermes because the tool column was not passed - both were fixed before the decisive run, and "
                   "the intermediate JSON is kept in results_raw/ alongside this one.",
                   "no - topic killed; one measurement reused as corroboration in P001"]))
if not any(r and r[0] == "EXP-0040" for r in rows[1:]):
    rows.append([rec[k] for k in h])
buf = io.StringIO()
csv.writer(buf, lineterminator="\r\n").writerows(rows)
reg.write_text(buf.getvalue(), encoding="utf-8", newline="")

tp = ROOT / "00_program_registry/topic_registry.csv"
tl = list(csv.reader(io.StringIO(tp.read_text(encoding="utf-8"))))
th = tl[0]
for r in tl[1:]:
    if r and r[0] == "T007":
        r[th.index("status")] = "killed_pilot_no_identifiability"
        r[th.index("blocking_issue")] = (
            "EXP-0040 pilot: the three requirements never co-occur (Toucan has "
            f"{tc['distinct_tools_seen']} tools but only subset_name labels; hermes has a 9/26-way human scheme "
            f"but just {her['distinct_tools_seen']} distinct tool names; AgentBank has 19 environments and no tool "
            "catalogue). Killed as a standalone paper rather than re-scoped. Novelty was never the obstacle "
            "(EXP-0038 found no collision).")
buf = io.StringIO()
csv.writer(buf, lineterminator="\r\n").writerows(tl)
tp.write_text(buf.getvalue(), encoding="utf-8", newline="")
d = pd.read_csv(tp)
print("T007 ->", d[d.topic_id == "T007"].status.iloc[0])
print("experiments:", len(pd.read_csv(reg)), "| topics left needing a literature pass:",
      int((d.status == "w1_audit_done").sum()))
print("remaining pilot candidates:", list(d[d.status.str.startswith("w2_pilot")].topic_id))
