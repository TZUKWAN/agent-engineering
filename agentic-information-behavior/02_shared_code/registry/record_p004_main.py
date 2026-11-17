"""Write P004's deviation record and register EXP-0041/0042/0043. Kept as a script so the bookkeeping is
reproducible and the numbers come from the result files rather than from my memory of the run."""
from __future__ import annotations

import csv, glob, io, json, pathlib, time

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
PAP = ROOT / "papers" / "P004_shipped_quality_score_validity"
R = ROOT / "00_program_registry"


def latest(pat):
    return pathlib.Path(sorted(glob.glob(str(ROOT / "results_raw" / pat)))[-1])


f41, f42, f43 = latest("EXP0041_*.json"), latest("EXP0042_*.json"), latest("EXP0043_*.json")
e41, e42, e43 = (json.loads(p.read_text(encoding="utf-8")) for p in (f41, f42, f43))
s43 = e43["configs"]["OSS"]["sample"]
now = time.strftime("%Y-%m-%d %H:%M")

(PAP / "deviations.md").write_text(f"""# P004 Deviations

| id | time | change | trigger | changed a claim? | effect |
|---|---|---|---|---|---|
| D31 | {now} | the objective criteria are computed inside P004 from the rows it reads - frozen BM25 (k1=1.4, b=0.4) and the published gold-resolution path, imported from `build_toucan_routing_dataset.py` - instead of joining the published routing dataset | the first main run (`{f42.name}`) inherited that table, so the sample collapsed to {e42['configs']['OSS']['sample']['published_dev_rows'] if 'published_dev_rows' in e42['configs']['OSS']['sample'] else 'a few thousand'} dev rows against the 20,000-per-config target **and** silently inherited P001's 2-of-10-shard, single-turn-original coverage defect (measured in EXP-0034) | no - nothing had been written yet; the flawed run is kept and never quoted | `{f43.name}`: {s43['dev_rows']:,} dev rows in OSS ({e43['configs']['Qwen3']['sample']['dev_rows']:,} / {e43['configs']['Kimi-K2']['sample']['dev_rows']:,} in the others), {sum(e43['configs'][c]['sample']['dev_rows'] for c in e43['configs']):,} pooled, {s43['score_json_parse_failures']} score-JSON parse failures, gold resolution {s43['gold_resolution_rate']:.0%}. The flawed join had also corrupted RQ1 itself: alpha went from -0.038/-0.063/0.045 to 0.179/0.184/0.191, so the earlier numbers were not merely small-n, they were the wrong statistic on the wrong rows |
| D32 | {now} | P004 restricts rows to the published dev bucket (`md5(prompt_id) % 1000 < 700`) | once the criterion stopped arriving pre-split with the routing table, the freeze did not say how to stay clear of another paper's single-use test split | none | drops {s43['rows_dropped_outside_dev_bucket']:,} OSS rows; every P004 statistic is now computed on rows that belong to no test set in this series |

Both raw runs (`{f42.name}`, `{f43.name}`) are kept in `results_raw/`. Only the second is quoted.
""", encoding="utf-8")

reg = R / "experiment_registry.csv"
rows = list(csv.reader(io.StringIO(reg.read_text(encoding="utf-8"))))
h = rows[0]
recs = [
 dict(exp_id="EXP-0041", paper_id="P004", stage="E1_presence_scan_DONE",
      script="02_shared_code/data_audit/quality_presence_scan_p004.py",
      config="8 releases; parquet schema plus <=2,000 sampled rows; quality-shaped column names and a structural "
             "test for score-like JSON objects; qualifies at >=5% non-null",
      status="success_only_Toucan_ships_scores", outputs=f"results_raw/{f41.name}",
      notes=f"measured: {e41['verdict']['releases_shipping_quality_scores']}. Six of eight releases have no "
            "quality-shaped column at all (recorded as scanned_without_candidates, which is not the same as zero "
            "scores) and Toucan's SFT config lacks it too. So no cross-corpus replication axis exists: P004 "
            "replicates across three teacher configs instead, and states that limit.",
      enters_paper="yes - RQ5 and limitations"),
 dict(exp_id="EXP-0042", paper_id="P004", stage="E2-E5_SUPERSEDED_BY_D31",
      script="02_shared_code/statistics/p004_validity_main.py",
      config="first execution; objective criteria inherited from the published routing dataset",
      started_at=e42["started_at"], finished_at=e42["finished_at"], status="failed_sample_construction",
      outputs=f"results_raw/{f42.name}",
      notes="4,322 dev rows instead of the ~60k target, and it inherited P001's shard-coverage defect. Its RQ1 "
            "alphas (-0.038/-0.063/0.045) were artefacts of the collapsed join - that is how D31 was caught. "
            "Kept, never quoted.", enters_paper="no - superseded by EXP-0043"),
 dict(exp_id="EXP-0043", paper_id="P004", stage="E2-E5_main_DONE",
      script="02_shared_code/statistics/p004_validity_main.py",
      config="3 configs x 10 random shards x <=2,000 rows; dev bucket only; criteria computed in-pipeline with the "
             "frozen BM25; prompt_id-clustered bootstrap CIs; Holm across RQ2's 12 tests; decision bands frozen "
             "in protocol_freeze.md section 3 before the run",
      seed=str(e43["seed"]), started_at=e43["started_at"], finished_at=e43["finished_at"],
      status="success_instrument_NOT_COHERENT_and_gating_distorts",
      outputs=f"results_raw/{f43.name}; results_processed/EXP0043_criterion_validity.csv",
      notes=f"RQ1 alpha 0.179/0.184/0.191, pooled {e43['RQ1']['pooled']['alpha']} -> NOT_COHERENT in every "
            "config. RQ2: 7 of 12 dimensions NOT_VALID, 1 VALID (completeness against the rule-extracted "
            "executed-tool agreement), 4 INCONCLUSIVE. RQ3: difficulty rho 0.103 falls to 0.003 once catalogue "
            "size and question length are conditioned on. RQ4: gating at overall_score>=4 keeps ~55% of rows and "
            "GATING_DISTORTS in all three configs.", enters_paper="yes - P004 main result")]
have = {r[0] for r in rows[1:] if r}
for rec in recs:
    if rec["exp_id"] not in have:
        rows.append([rec.get(k, "") for k in h])
buf = io.StringIO()
csv.writer(buf, lineterminator="\r\n").writerows(rows)
reg.write_text(buf.getvalue(), encoding="utf-8", newline="")

tp = R / "topic_registry.csv"
tl = list(csv.reader(io.StringIO(tp.read_text(encoding="utf-8"))))
th = tl[0]
for r in tl[1:]:
    if r and r[0] == "T024":
        r[th.index("status")] = "w5_main_done_instrument_not_valid"
        r[th.index("blocking_issue")] = ("EXP-0043 complete. Alpha 0.179-0.191 across configs; 7 of 12 "
                                         "dimensions NOT_VALID against objective criteria; the difficulty score's "
                                         "apparent validity is catalogue size (0.103 -> 0.003); gating on "
                                         "overall_score>=4 distorts measured failure prevalence in all three "
                                         "configs. Remaining: the paper package.")
buf = io.StringIO()
csv.writer(buf, lineterminator="\r\n").writerows(tl)
tp.write_text(buf.getvalue(), encoding="utf-8", newline="")

d = pd.read_csv(reg)
d2 = pd.read_csv(tp)
assert d.exp_id.is_unique and not (d.exp_id == "exp_id").any(), "registry integrity"
assert len(d2) == 37 and d2.topic_id.is_unique, "topic registry integrity"
print("experiments:", len(d), "| topics:", len(d2), "| T024:", d2[d2.topic_id == "T024"].status.iloc[0])
print("pooled dev rows:", sum(e43["configs"][c]["sample"]["dev_rows"] for c in e43["configs"]))
