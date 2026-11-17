"""Record EXP-0036 into P003, and register the first (buggy) execution as superseded.

First execution facts, kept rather than deleted: EXP0036_..._20260919T024357.json was produced by a parsing bug in
this script (it looked for the published cells under `coverage`/`concepts` instead of `cells`, so the published
side parsed to an empty mapping and `all()` over it returned True for every concept - reporting "12 of 12
alignable", the opposite of the paper's headline, while simultaneously reporting zero state changes). That output
is invalid and is now listed in SUPERSEDED_ARTIFACTS.json; it is not quoted anywhere. The second execution parses
8x12 on both sides, with a guard that aborts instead of deciding on a partial matrix.
"""
from __future__ import annotations

import csv, glob, io, json, pathlib, re, sys, time

ROOT = pathlib.Path(__file__).resolve().parents[2]
PAP = ROOT / "papers" / "P003_metadata_interoperability"
REG = ROOT / "00_program_registry"
RAW = ROOT / "results_raw"

good_f = sorted(RAW.glob("EXP0036_randomised_resample_*.json"))
if not good_f:
    sys.exit("[e36r] no EXP-0036 result; writing nothing")
bad = [p for p in good_f if json.loads(p.read_text(encoding="utf-8"))["verdict"]["decision"] == "SAMPLING_SENSITIVE"]
D = json.loads(good_f[-1].read_text(encoding="utf-8"))
V = D["verdict"]
assert len(D["randomised_matrix"]) == 8, "expected eight corpora"

sup = RAW / "SUPERSEDED_ARTIFACTS.json"
s = json.loads(sup.read_text(encoding="utf-8")) if sup.exists() else {"purpose": "artefacts kept but not citable"}
s.setdefault("superseded", [])
for b in bad:
    if not any(b.name == e.get("file") for e in s["superseded"]):
        s["superseded"].append({"file": b.name, "exp_id": "EXP-0036", "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                                "reason": "published-side cells parsed from the wrong key, so the comparison ran "
                                          "against an empty matrix; `all()` over it reported 12/12 alignable and "
                                          "0 changes - mutually contradictory. Replaced by " + good_f[-1].name,
                                "was_it_quoted": "no - caught before any paper text used it"})
        print(f"[e36r] marked {b.name} superseded")
sup.write_text(json.dumps(s, indent=1, ensure_ascii=False), encoding="utf-8")

lm = PAP / "limitations.md"
t = lm.read_text(encoding="utf-8")
old3 = "3. **Sampling is row-head, not uniform.**"
if "EXP-0036" not in t and old3 in t:
    i = t.index(old3)
    j = t.index("\n", i)
    k = t.find("\n\n", j)
    k = len(t) if k < 0 else k
    t = t[:i] + ("3. **Sampling was row-head, not uniform - now tested (EXP-0036).** Per shard we read the first "
                 "rows, so a release sorted by task could bias the matrix. EXP-0036 re-ran the identical frozen "
                 "judgement over uniformly randomised row positions on all eight corpora: **all 96 cells agree "
                 "with the published matrix, zero state changes, and the same 2 of 12 concepts remain recoverable "
                 "everywhere** - so the headline is not a sampling artefact. What remains untested is the *concept "
                 "list itself* (a second, independently derived list) and the human re-derivation of the 30 "
                 "self-audit cells.") + t[i + (k - i):]
    lm.write_text(t, encoding="utf-8")
    print("[e36r] limitation 3 rewritten as tested-and-stable")

ra = PAP / "reviewer_attack.md"
rt = ra.read_text(encoding="utf-8")
if "row-head sampling artefact" not in rt:
    n = max([int(x) for x in re.findall(r"^\| A(\d+) \|", rt, re.M)] or [0]) + 1
    rt = rt.rstrip() + (f"\n| A{n} | row-head sampling artefact: your coverage matrix could just be what the first "
                        f"rows of each shard happen to contain | Tested. EXP-0036 re-ran the frozen instrument over "
                        f"randomised row positions for all 8 corpora: {V['all_state_changes']} state changes out of "
                        f"96 cells, and the all-corpus alignable set is identical "
                        f"({V['alignable_randomised'][0]} concepts: "
                        f"{', '.join(V['alignable_randomised'][1])}) | results_raw/{good_f[-1].name} |")
    ra.write_text(rt + "\n", encoding="utf-8")
    print(f"[e36r] added reviewer-attack A{n}")

cm = PAP / "claims_evidence_matrix.csv"
rows = list(csv.DictReader(io.StringIO(cm.read_text(encoding="utf-8"))))
if not any("EXP-0036" in (r.get("experiment_id") or "") for r in rows):
    d = dict(zip(rows[0].keys(), [""] * len(rows[0])))
    d.update({"claim_id": f"K{len(rows) + 1}",
              "claim": ("The interchange-level coverage matrix is not an artefact of row-head sampling: randomising "
                        "row positions leaves all 96 corpus x concept cells unchanged and the same 2 of 12 concepts "
                        "alignable across all eight corpora"),
              "claim_type": "robustness / measurement", "experiment_id": "EXP-0036", "direction": "supports",
              "table": "-", "figure": "-",
              "statistical_test": "full matrix re-derivation under randomised sampling, cell-by-cell diff",
              "raw_result_file": f"results_raw/{good_f[-1].name}", "where_in_paper": "limitations 3; reviewer attack",
              "status": "supported"})
    with open(cm, "a", newline="", encoding="utf-8") as fh:
        csv.DictWriter(fh, fieldnames=list(rows[0].keys())).writerow(d)
    print(f"[e36r] added claim {d['claim_id']}")

hdr_lines = list(csv.reader(io.StringIO((REG / "experiment_registry.csv").read_text(encoding="utf-8"))))
h = hdr_lines[0]
i = next(n for n, r in enumerate(hdr_lines) if r and r[0] == "EXP-0036") if any(
    r and r[0] == "EXP-0036" for r in hdr_lines) else None
row = dict(zip(h, ["EXP-0036", "P003", "randomised_resample_DONE",
                   "02_shared_code/data_audit/randomised_resample_p003.py",
                   "8 corpora x 12 concepts; same frozen SPEC/parsers/thresholds and the EXP-0030 nested probes; only "
                   "within-file row positions randomised (parquet: random take inside each row group; MMAT jsonl: "
                   "uniform byte-offset sampling); per-corpus seed from crc32 so it is process-stable", "42",
                   D["started_at"], D["finished_at"], "success_MATRIX_STABLE",
                   f"{good_f[-1].name}; {bad[0].name} (superseded, see SUPERSEDED_ARTIFACTS.json); "
                   "logs/EXP-0036_randomised_resample_v2.txt",
                   "Closes P003's 'randomised sampling' pre-submission item: 0 state changes across 96 cells and the "
                   f"same {V['alignable_randomised'][0]}/12 alignable everywhere. First execution produced the "
                   "opposite verdict through a vacuous-truth parsing bug and is registered as superseded rather than "
                   "deleted; the script now aborts unless both matrices parse to 8x12.",
                   "yes - limitations 3, one claims row, one reviewer-attack answer"]))
row_vals = [row[k] for k in h]
if i is None:
    hdr_lines.append(row_vals)
    print("[e36r] EXP-0036 was not registered yet; appended a new row")
else:
    hdr_lines[i] = row_vals
buf = io.StringIO()
csv.writer(buf, lineterminator="\r\n").writerows(hdr_lines)
(REG / "experiment_registry.csv").write_text(buf.getvalue(), encoding="utf-8", newline="")
import pandas as pd
d2 = pd.read_csv(REG / "experiment_registry.csv")
print(f"[e36r] registry rows={len(d2)}; EXP-0036 -> {d2[d2.exp_id == 'EXP-0036'].status.iloc[0]}")
