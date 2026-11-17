"""Register EXP-0044 (criterion sensitivity) and mark P004's package state in the topic registry.

The run happened before its registry row existed, which is precisely the kind of gap the experiment register is for;
this script closes it from the result file and records that ordering honestly.
"""
from __future__ import annotations

import csv, glob, io, json, pathlib, time

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
R = ROOT / "00_program_registry"
f44 = pathlib.Path(sorted(glob.glob(str(ROOT / "results_raw/EXP0044_*.json")))[-1])
e44 = json.loads(f44.read_text(encoding="utf-8"))
v44 = e44["verdict"]

reg = R / "experiment_registry.csv"
rows = list(csv.reader(io.StringIO(reg.read_text(encoding="utf-8"))))
h = rows[0]
rec = dict(zip(h, [
    "EXP-0044", "P004", "E6_criterion_sensitivity_DONE",
    "02_shared_code/statistics/p004_criterion_sensitivity.py",
    "three pre-declared executed-tool extraction rules (loose structured+text / structured-only local names / "
    "structured-only full qualified names); same frozen sample: 3 configs x 10 random shards x <=2,000 rows, dev "
    "bucket only; Spearman rho with prompt_id-clustered bootstrap CI (1,000 draws)",
    str(e44["seed"]), e44["started_at"], e44["finished_at"], "success_RULE_DEPENDENT_positive_finding",
    f"results_raw/{f44.name}; results_processed/EXP0044_criterion_sensitivity.csv; "
    "papers/P004_shipped_quality_score_validity/tables/table_criterion_sensitivity.csv",
    "Stress-tests P004's only VALID verdict before it is published. agreement means "
    f"{v44['agreement_mean_by_variant']}, rho(completeness, agreement) {v44['rho_by_variant']}: the finding holds "
    "under prefix-normalised name matching and fails under exact qualified names, so it is reported as provisional "
    "(K6) rather than as support. Registered after execution - the row is created here, which is itself noted so "
    "the ordering is not lost.",
    "yes - K6, limitations 2, reviewer attack 4"]))
if not any(r and r[0] == "EXP-0044" for r in rows[1:]):
    rows.append([rec[k] for k in h])
buf = io.StringIO()
csv.writer(buf, lineterminator="\r\n").writerows(rows)
reg.write_text(buf.getvalue(), encoding="utf-8", newline="")

tp = R / "topic_registry.csv"
tl = list(csv.reader(io.StringIO(tp.read_text(encoding="utf-8"))))
th = tl[0]
for r in tl[1:]:
    if r and r[0] == "T024":
        r[th.index("status")] = "w5_package_complete_pre_submission_checks_open"
        r[th.index("blocking_issue")] = ("EXP-0043 main + EXP-0044 sensitivity complete; P004 package generated "
                                         "from result files and audit-clean. Open before submission: no second "
                                         "corpus ships the object (EXP-0041), the executed-tool criterion needs "
                                         "human validation, and the only positive finding is RULE_DEPENDENT.")
buf = io.StringIO()
csv.writer(buf, lineterminator="\r\n").writerows(tl)
tp.write_text(buf.getvalue(), encoding="utf-8", newline="")

d = pd.read_csv(reg)
d2 = pd.read_csv(tp)
assert d.exp_id.is_unique and not (d.exp_id == "exp_id").any()
assert len(d2) == 37 and d2.topic_id.is_unique
print(f"experiments={len(d)} EXP-0044 present={'EXP-0044' in set(d.exp_id)}")
print("T024 ->", d2[d2.topic_id == "T024"].status.iloc[0])
print("paper statuses:", d2[d2.status.str.startswith('w5')][["topic_id", "status"]].to_dict("records"))
