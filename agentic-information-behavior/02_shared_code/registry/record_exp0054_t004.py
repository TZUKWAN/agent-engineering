"""Record EXP-0054 (T004 feasibility) as a funnel decision: the construct is declared in exactly one release.

Two rules of the programme decide the topic, and both are stated with the numbers behind them: external validity
needs more than one corpus that declares the label, and the anti-repetition rule forbids re-slicing P001's Toucan
covariates. The pilot's own sampling filter also dropped the human-written subset, so the central contrast is left
explicitly untested rather than being reported as a null.

    python 02_shared_code/registry/record_exp0054_t004.py
"""
from __future__ import annotations

import csv, glob, io, json, pathlib, time

ROOT = pathlib.Path(__file__).resolve().parents[2]
REG = ROOT / "00_program_registry"
DOC = ROOT / "docs" / "funnel_decision_T004_20260920.md"
hits = sorted(glob.glob(str(ROOT / "results_raw" / "EXP0054_provenance_label_feasibility_*.json")))
if not hits:
    raise SystemExit("[e54] no EXP-0054 result file; writing nothing.")
NAME = pathlib.Path(hits[-1]).name
D = json.loads(pathlib.Path(hits[-1]).read_text(encoding="utf-8"))
C = D["contrasts"]
census = {r["corpus"]: r for r in D["label_census"]}
prov_rel = sorted({c["corpus"] for c in C} | {k for k, v in census.items()
                                              if set(v["label_columns"]) - {"category", "subcategory", "task"}})
tax = D.get("taxonomy_labels_reported_only", [])
now = time.strftime("%Y-%m-%d %H:%M")

L = [f"# Funnel decision — T004 (Real Human vs Synthetic Agent Instructions), {now}", "",
     f"Probe: `02_shared_code/data_audit/provenance_label_feasibility_t004.py` → `results_raw/{NAME}`.", "",
     "## What the topic needed, and what the data has", "",
     "T004 was registered against an AgentNet file of 22,811 human instructions. Listing the tree shows AgentNet is "
     "not on this machine: the eight releases under `MATLABINTOKEN/datasets` are all there is. The re-scoped question "
     "was therefore whether any of those eight **declares** instruction provenance (human-written vs model-generated "
     "or model-rewritten) in a column usable as a label.", "",
     f"Exactly one release does: **Toucan-1.5M**, whose `subset_name` carries `single-turn-original` "
     f"(human-authored), `single-turn-diversify` (LLM-rewritten), `multi-turn` and `irrelevant`. "
     f"Releases with any categorical column at all: {', '.join(sorted(k for k, v in census.items() if v['label_columns']))}. "
     "The others' columns are task taxonomies or generator identities, not provenance statements:", ""]
for k, v in census.items():
    if v["label_columns"]:
        obs = {c: list(vals)[:6] for c, vals in v["observed_values"].items()}
        L.append(f"- **{k}**: {v['label_columns']} → {obs}")
L += ["", "## The separability numbers", ""]
for c in C:
    L.append(f"- **{c['corpus']} / `{c['label_col']}`** comparing {c['kept']}: n={c['n']}, AUC={c['auc_all_features']}, "
             f"length-only={c['auc_length_only']}, permutation null={c['permutation_null_mean_auc']} "
             f"(max over 10 shuffles {c['permutation_null_max_auc']}), longer group **{c['longer_group']}**, "
             f"mean tokens {c['mean_tokens']}, dependence key `{c['dependence_key']}`.")
if tax:
    L += ["", "Reported but excluded from the GO count by the (repaired) rule — these are task taxonomies, and the "
          "first version of the rule let one clear the bar:"]
    for t in tax:
        L.append(f"- {t['corpus']} / `{t['label_col']}`: {t['values']}")
L += ["", "## Why the topic is not promoted", "",
      "1. **One corpus only.** The construct is declared in a single release, so any claim would rest on n=1 corpus "
      "with no external-validity check available. That is the same wall T007 hit from the other side.",
      "2. **It would re-slice P001.** Toucan's `subset_name` is precisely the covariate P001 had to scope its H1–H3 "
      "claims to after EXP-0034/0035 showed the published sample is one subset and the predictor does not transfer to "
      "`single-turn-diversify`. A register study on those same subsets would be a second paper over P001's own "
      "controls, which the anti-repetition rule forbids.",
      "3. **The central contrast was never tested.** The probe's pair filter (`n >= 60` among the four most common "
      f"values) dropped `single-turn-original` from the pairs it scored, so the {len(C)} contrasts above are "
      "diversify/multi-turn/irrelevant against each other. The AUCs are high (0.85–1.00) and every one of them beats "
      "its permutation null, but they do **not** answer human-vs-synthetic. Recorded as an outstanding gap; the topic "
      "is not killed on a null it never measured.",
      "4. **What the rule defects taught.** Two fixes belong to the next pilot, both recorded here rather than "
      "silently applied: a label allowlist (provenance statements only — a task taxonomy cleared the original bar), "
      "and stratified sampling over config directories (the first version read the first three files' first row "
      "groups and concluded Toucan declared one subset value, which is false).", "",
      "**Status: `not_promoted_single_corpus_and_p001_overlap`.** Reversible by obtaining a second release that "
      "declares human-authored instructions (the blocked-data class of T015), or by a register study that is "
      "explicitly *not* built on Toucan.", ""]
DOC.write_text("\n".join(L), encoding="utf-8", newline="")
print(f"[e54] wrote {DOC.relative_to(ROOT)}")

TP = REG / "topic_registry.csv"
hdr = list(csv.reader(io.StringIO(TP.read_text(encoding="utf-8"))))[0]
rows = list(csv.DictReader(open(TP, encoding="utf-8")))
before = {r["topic_id"]: dict(r) for r in rows}
for r in rows:
    if r["topic_id"] == "T004":
        r["status"] = "not_promoted_single_corpus_and_p001_overlap"
        r["blocking_issue"] = ("only Toucan declares instruction provenance (EXP-0054); AgentNet absent; a Toucan "
                               "register study would re-slice P001's subset covariates")
with open(TP, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=hdr)
    w.writeheader()
    w.writerows(rows)
after = {r["topic_id"]: dict(r) for r in csv.DictReader(open(TP, encoding="utf-8"))}
assert set(after) == set(before)
for tid in after:
    for k in hdr:
        if (tid, k) not in (("T004", "status"), ("T004", "blocking_issue")):
            assert after[tid][k] == before[tid][k], f"{tid}.{k} changed unintentionally"
print("[e54] T004 status updated (status + blocking_issue only)")

p = REG / "experiment_registry.csv"
txt = p.read_text(encoding="utf-8")
if "EXP-0054" not in txt:
    h2 = list(csv.reader(io.StringIO(txt)))[0]
    buf = io.StringIO()
    _row = dict(zip(h2, [
        "EXP-0054", "T004 (funnel)", "provenance_label_feasibility_DONE",
        "02_shared_code/data_audit/provenance_label_feasibility_t004.py",
        "8 releases censused for declared label columns (stratified over config dirs, one random row group per "
        "sampled file); per provenance label every pair among the four most common values; logistic predictor scored "
        "GroupKFold where a dependence key exists, length-only baseline + 10-shuffle permutation null; <=60 random "
        "parquet files and <=6,000 rows per release; GO rule fixed in the docstring and repaired mid-pilot "
        "(task taxonomies excluded from the count)", "42", D["started_at"], D["finished_at"],
        "pilot_T004_NOT_PROMOTED_construct_in_one_corpus_only",
        f"{NAME}; results_processed/EXP0054_label_contrasts.csv; docs/funnel_decision_T004_20260920.md",
        f"Toucan is the only release declaring instruction provenance (subset_name: original/diversify/multi-turn/"
        f"irrelevant); {len(C)} contrasts scored, AUC "
        f"{', '.join(str(c['auc_all_features']) for c in C)} against length-only "
        f"{', '.join(str(c['auc_length_only']) for c in C)} and permutation nulls ~0.50. Not promoted: one corpus "
        "cannot support external validity and a Toucan register study would re-slice P001's subset covariates. Two "
        "instrument defects found by looking (unstratified census; construct-blind rule accepting hermes/category at "
        "AUC 1.0), and the human-vs-diversify pair was dropped by the pair filter - recorded as untested, not null.",
        "yes - as the funnel decision record"]))
    csv.writer(buf, lineterminator="\r\n").writerow([_row[c] for c in h2])
    p.write_text(txt.rstrip("\r\n") + "\r\n" + buf.getvalue().rstrip("\r\n") + "\r\n", encoding="utf-8", newline="")
    print("[e54] registered EXP-0054")
import pandas as pd
d = pd.read_csv(p)
assert not d.exp_id.duplicated().any()
tr = pd.read_csv(REG / "topic_registry.csv", dtype=str).fillna("")
print(f"[e54] registry rows={len(d)}; topics now not_promoted/killed: "
      f"{int(tr.status.str.startswith(('killed', 'not_promoted', 'demoted')).sum())}/{len(tr)}")
print("[e54] OK")
