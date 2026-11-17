"""Register EXP-0115 and EXP-0116, the two funnel steps that screened the 86 topics registered on 2026-09-23.

Both wrote their raw artefact and decided topic statuses, but neither added a row to `experiment_registry.csv`, so the
registry would have shown 114 experiments while the funnel had run two more. The rows are emitted by column name from
the artefacts themselves, and the step refuses to write if either artefact is missing - a registry row that describes a
run nobody can open is worse than no row.

    python 02_shared_code/registry/register_exp0115_0116_funnel.py
"""
from __future__ import annotations

import csv, io, json, pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = next(a for a in (HERE, *HERE.parents) if (a / "00_program_registry").is_dir())
REG = ROOT / "00_program_registry" / "experiment_registry.csv"


def artefact(pat: str) -> pathlib.Path:
    hits = sorted((ROOT / "results_raw").glob(pat))
    if not hits:
        sys.exit(f"ABORT: no artefact matches {pat} - nothing is registered")
    return hits[-1]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    a115, a116 = artefact("EXP0115_funnel_screen_round5_*.json"), artefact("EXP0116_funnel_retriage_*.json")
    d115 = json.loads(a115.read_text(encoding="utf-8", errors="replace"))
    d116 = json.loads(a116.read_text(encoding="utf-8", errors="replace"))
    from collections import Counter
    c115 = Counter(t["status"] for t in d115["topics"])
    c116 = Counter("fold" if k.startswith("w3_fold") else "advance" for k in d116["decided"])
    rows = list(csv.reader(io.StringIO(REG.read_text(encoding="utf-8"))))
    hdr = rows[0]
    body = rows[1:]
    have = {r[0] for r in body}
    new = [
        dict(exp_id="EXP-0115", paper_id="programme", stage="funnel_screen_round5_intake",
             script="02_shared_code/registry/funnel_audit_round5.py",
             config=f"waves of {[len(x) for x in [d115['topics'][:50], d115['topics'][50:]] if x]} over "
                    f"{d115['n_decided']} topics; 3 literature channels per topic",
             seed="n/a (deterministic screen; queries recorded per channel)",
             started_at=d115.get("started_at", ""), finished_at=d115.get("finished_at", ""),
             status="success_" + "_".join(f"{k}:{v}" for k, v in sorted(c115.items())),
             outputs=f"results_raw/{a115.name}; 00_program_registry/topic_registry.csv",
             notes="screens the 86 topics registered on 2026-09-23 (42 from the message, 44 from the attachment) for "
                   "local-data presence, measured column coverage, in-programme duplication and literature crowding; "
                   "a topic whose collision query got no answer from any channel is left incomplete rather than "
                   "advanced",
             enters_paper="no - funnel management (spec §20)", topic_id="programme"),
        dict(exp_id="EXP-0116", paper_id="programme", stage="funnel_retriage_construct_level",
             script="02_shared_code/registry/funnel_retriage_round5.py",
             config=f"{d116['live_before']} live topics re-read at construct level; folds adjudicated by hand",
             seed="n/a (deterministic)", started_at="", finished_at=d116.get("finished_at", ""),
             status="success_" + "_".join(f"{k}:{v}" for k, v in sorted(c116.items())),
             outputs=f"results_raw/{a116.name}; 00_program_registry/topic_registry.csv",
             notes="EXP-0115's own output showed two of its legs were under-powered (a duplicate rule that could not "
                   "see paraphrase, and a field rule that looked for column names in prose). This step measures "
                   "construct overlap and a concept-to-column census, and records the ranked pair evidence; the fold "
                   "decisions are authored with a reason per pair rather than taken from a token count",
             enters_paper="no - funnel management (spec §20)", topic_id="programme"),
    ]
    added = 0
    for r in new:
        if r["exp_id"] in have:
            print(f"  {r['exp_id']} already registered"); continue
        if len(r) != len(hdr):
            sys.exit(f"ABORT: {r['exp_id']} has {len(r)} fields against a {len(hdr)}-column header")
        body.append([r[c] for c in hdr])
        added += 1
    if added:
        with open(REG, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh, lineterminator="\n")
            w.writerow(hdr)
            w.writerows(body)
    back = list(csv.reader(io.StringIO(REG.read_text(encoding="utf-8"))))
    assert back[0] == hdr and all(len(x) == len(hdr) for x in back[1:] if x), "registry integrity check failed"
    print(f"  registered {added} experiment(s); registry now {len(back) - 1} rows x {len(hdr)} columns")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
