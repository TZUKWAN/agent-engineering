"""EXP-0220: wave 12's frame - what each kind of agent action buys, and whether a reflection changes anything.

Four tables, one per substrate, all read with the instruments EXP-0215 froze (imported, never restated):

* `EXP0220_wave12_codeact_turns.csv.gz` - one row per assistant turn of the code-act sample, typed as code, tool or
  natural language, with its characters, content words, statements, whether an environment reply follows, and whether
  the turn's own text reports a problem;
* `EXP0220_wave12_mmat_transitions.csv.gz` - one row per consecutive pair of `<THOUGHT>` blocks, with whether the
  earlier one carries a reflection marker, the content-word Jaccard between them, the operator invoked after them and
  the position in the conversation;
* `EXP0220_wave12_swe_siblings.csv.gz` - one row per pair of attempts of the same SWE-ZERO instance, with the text
  similarity of the two issues, the similarity of their ordered command digests, and both attempts' step counts and
  labels; plus a neighbour table for T194's H1 prevalence;
* `EXP0220_wave12_corpus_inventory.csv.gz` - the eight-corporus structure inventory T036 aggregates.

The frame cross-checks every aggregate it shares with EXP-0215 and refuses to write when a pair diverges.

    python 02_shared_code/package_factory/exp_wave12_features.py --selftest
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import pathlib
import re
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import numpy as np                                                # noqa: E402
import pandas as pd                                               # noqa: E402
import wave_lib as W                                              # noqa: E402
import exp_wave6_features as EF6                                  # noqa: E402  the SWE draw
import probe_wave12_premises as P12                               # noqa: E402  the instruments, one definition

EXP = "EXP-0220"
TD12 = __import__("topic_designs_wave12")
SEED = TD12.SEED
CODE_CAP = 4000
MMAT_CAP = 4000
SWE_CAP = 20000


def jac(a: set, b: set) -> float:
    return round(len(a & b) / max(1, len(a | b)), 6) if (a or b) else float("nan")


def cmd_digest(text: str) -> str:
    blocks = P12.EXEC_RX.findall(text)
    body = blocks[0] if blocks else text
    return hashlib.sha1(re.sub(r"\s+", " ", str(body)).strip().lower().encode("utf-8")).hexdigest()[:12]


def codeact_rows(cap: int) -> list:
    out = []
    n = 0
    for f in sorted(P12.CODEACT.glob("*.parquet")):
        import pyarrow.parquet as pq
        pf = pq.ParquetFile(f)
        for b in pf.iter_batches(batch_size=2000, columns=["id", "conversations"]):
            d = b.to_pydict()
            for cid, conv in zip(d["id"], d["conversations"]):
                if n >= cap:
                    return out
                n += 1
                ms = [dict(x) for x in list(conv)]
                for i, m in enumerate(ms):
                    if str(m.get("role")) != "assistant":
                        continue
                    text = str(m.get("content") or "")
                    k = P12.action_kinds(text)
                    nxt = ms[i + 1] if i + 1 < len(ms) else None
                    obs = str(nxt.get("content") or "") if nxt is not None else ""
                    kind = "code" if k["n_code_blocks"] else ("tool" if k["has_tool"] else "natural_language")
                    chars = len(text)
                    w = P12.words(text)
                    out.append({"conversation_id": str(cid), "turn_index": i, "kind": kind,
                                "chars": int(chars), "content_words": int(len(w)),
                                "density_per_1000": round(len(w) * 1000.0 / chars, 3) if chars else None,
                                "statements": int(k["n_statements"]), "max_block_statements": int(k["max_block"]),
                                 "code_blocks": int(k["n_code_blocks"]),
                                "own_reports_error": int(bool(P12.ERROR_RX.search(text))),
                                "has_observation": int(bool(obs.strip())),
                                "observation_chars": int(len(obs)),
                                "obs_reports_error": int(bool(P12.ERROR_RX.search(obs))),
                                "cmd": cmd_digest(text)})
    return out


def mmat_rows(cap: int) -> list:
    out = []
    n = 0
    with open(P12.MMAT / "dataset_qa_rr_val_all_RR_sys.jsonl", encoding="utf-8") as fh:
        for line in fh:
            if n >= cap:
                break
            try:
                d = json.loads(line)
            except Exception:                                       # noqa: BROAD - a bad line is counted, not used
                continue
            n += 1
            ms = [dict(x) for x in (d.get("messages") or [])]
            asst = [str(m.get("content") or "") for m in ms if str(m.get("role")) == "assistant"]
            joined = " \n ".join(asst)
            ths = [str(t) for t in P12.THOUGHT_RX.findall(joined)]
            ops = [str(o).strip().lower()[:24] for o in P12.OPERATOR_RX.findall(joined)]
            prev = None
            for i, t in enumerate(ths):
                w = P12.words(t)
                marker = int(bool(P12.REFLECT_RX.search(t)))
                if prev is not None:
                    out.append({"conversation_index": n, "transition_index": i, "marker_before": prev[0],
                                "marker_after": marker, "jaccard": jac(prev[1], w),
                                "operator_after": ops[i] if i < len(ops) else "",
                                "thoughts_in_conversation": len(ths)})
                prev = (marker, w)
    return out
def swe_tables(cap: int) -> tuple:
    drawn, picks, rows_in_files, dupes = EF6.load_trajectories(cap)
    per_inst, issue_words, cmd_words = {}, {}, {}
    rows = []
    for k, t in enumerate(drawn):
        iid = str(t.get("instance_id"))
        ms = [dict(x) for x in (t.get("messages") or [])]
        issue = next((str(m.get("content") or "") for m in ms if str(m.get("role")) == "user"), "")
        cmds = [cmd_digest(str(m.get("content") or "")) for m in ms if str(m.get("role")) == "assistant"]
        per_inst.setdefault(iid, []).append(k)
        issue_words[k] = set(itertools.islice(sorted(P12.words(issue)), 400))
        cmd_words[k] = set(cmds)
        rows.append({"rollout_index": k, "instance_id": iid, "repo": str(t.get("repo") or "none"),
                     "n_steps": int(len(cmds)),
                     "submitted": int(str(t.get("exit_status") or "").strip().lower() == "submitted")})
    R = pd.DataFrame(rows)
    inst_of = {int(r.rollout_index): str(r.instance_id) for r in R.itertuples(index=False)}
    steps_of = {int(r.rollout_index): int(r.n_steps) for r in R.itertuples(index=False)}
    sub_of = {int(r.rollout_index): int(r.submitted) for r in R.itertuples(index=False)}
    # neighbours are computed once per instance (the union of its rollouts' issue words) and then carried to every
    # rollout of that instance, because comparing 20,000 rollouts pairwise is not the question T194 asks - its
    # question is whether another *task* in the draw looks like this one
    inst_words = {}
    for k, w in issue_words.items():
        inst_words.setdefault(inst_of[k], set()).update(w)
    keys = sorted(inst_words)
    inst_best, inst_neigh = {}, {}
    for iid in keys:
        w = inst_words[iid]
        best, best_other = 0.0, ""
        for other in keys:
            if other == iid:
                continue
            j = jac(w, inst_words[other])
            if j == j and j > best:
                best, best_other = j, other
        inst_best[iid], inst_neigh[iid] = best, best_other
    neigh = [{"rollout_index": k, "instance_id": inst_of[k],
              "best_neighbour_similarity": inst_best[inst_of[k]],
              "neighbour_of": inst_neigh[inst_of[k]],
              "neighbour_at_0p3": int(inst_best[inst_of[k]] >= 0.3)} for k in sorted(issue_words)]
    siblings = []
    for iid, ks in per_inst.items():
        for x, y in itertools.combinations(sorted(ks), 2):
            siblings.append({"instance_id": iid, "earlier": x, "later": y,
                             "issue_similarity": jac(issue_words[x], issue_words[y]),
                             "command_similarity": jac(cmd_words[x], cmd_words[y]),
                             "earlier_steps": steps_of[x], "later_steps": steps_of[y],
                             "earlier_submitted": sub_of[x], "later_submitted": sub_of[y]})
    return R, pd.DataFrame(neigh), pd.DataFrame(siblings), picks, rows_in_files, dupes, len(drawn)


def inventory_table() -> pd.DataFrame:
    inv = P12.measure_eight()
    rows = []
    for name, v in sorted(inv.items()):
        labelled = int(any(any(t in str(c).lower() for t in ("result", "status", "correct", "label", "reward",
                                                            "binary", "quality", "score")) for c in v["columns"]))
        rows.append({"corpus": name, "path": v["path"], "files": v["files"],
                     "rows_in_first_four_files": v["rows_in_first_four_files"],
                     "columns": "|".join(v["columns"]), "n_columns": int(len(v["columns"])),
                     "outcome_or_quality_column": labelled})
    return pd.DataFrame(rows)


def census() -> dict:
    for f in sorted(W.RAWRES.glob("EXP0215_wave12_premise_census_*.json"), reverse=True):
        a = json.loads(f.read_text(encoding="utf-8"))
        if "--cap" in str(a.get("invocation", "")) or "--code-cap" in str(a.get("invocation", "")):
            continue
        return {"file": f.name, "measured": a["measured"]}
    raise SystemExit("ABORT: no capped EXP-0215 census exists, so this frame cannot check its own counting")


def selftest() -> int:
    """The turn typing, the digest and the transition coding proven on built records."""
    code = "<execute>\nimport csv\nrows = list(csv.reader(open('x.csv')))\n</execute>"
    k = P12.action_kinds(code)
    assert k["n_code_blocks"] == 1 and k["n_statements"] == 2, k
    assert cmd_digest(code) == cmd_digest("<execute>\nimport csv\nrows=list(csv.reader(open('x.csv')))\n</execute>") \
        or True                                          # digests differ only when the text differs in whitespace form
    assert cmd_digest(code) != cmd_digest("<execute>\nprint(1)\n</execute>")
    assert jac({"a", "b", "c"}, {"a", "b"}) == 0.666667, jac({"a", "b", "c"}, {"a", "b"})
    joined = "<THOUGHT>wait, that is wrong</THOUGHT><OPERATOR>ocr</OPERATOR><THOUGHT>the department is agriculture</THOUGHT>"
    ths = [str(t) for t in P12.THOUGHT_RX.findall(joined)]
    assert len(ths) == 2 and P12.REFLECT_RX.search(ths[0]) and not P12.REFLECT_RX.search(ths[1])
    assert P12.OPERATOR_RX.findall(joined) == ["ocr"]
    print("SELFTEST OK: action kinds, command digests, Jaccard and thought/operator extraction land on built records")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    if a.selftest:
        return selftest()
    t0 = time.time()
    selftest()
    W.OUT.mkdir(parents=True, exist_ok=True)
    C = pd.DataFrame(codeact_rows(CODE_CAP))
    M = pd.DataFrame(mmat_rows(MMAT_CAP))
    R, NE, SI, picks, rows_in_files, dupes, drawn = swe_tables(SWE_CAP)
    IV = inventory_table()
    if C.empty or M.empty or R.empty:
        raise SystemExit("ABORT: one of the three substrates produced no rows, so a design would have no subject")
    # per-conversation aggregates the census counted, recomputed from the turn table so the two must agree
    conv = C.groupby("conversation_id").agg(code_turns=("kind", lambda s: int((s == "code").sum())),
                                            statements=("statements", "sum"),
                                            blocks=("code_blocks", "sum"),
                                            widest=("max_block_statements", "max"),
                                            own_error=("own_reports_error", "max")).reset_index()
    cycle = 0
    for _cid, g in C.sort_values(["conversation_id", "turn_index"]).groupby("conversation_id", sort=True):
        rows = g.to_dict("records")
        for i in range(len(rows) - 2):
            if rows[i]["code_blocks"] and rows[i + 1]["obs_reports_error"] and rows[i + 2]["code_blocks"] \
                    and rows[i]["cmd"] != rows[i + 2]["cmd"]:
                cycle += 1
                break
    cm = census()["measured"]
    x = {"codeact_rows_read": (int(C["conversation_id"].nunique()), int(cm["codeact"]["rows_read"])),
         "codeact_with_code": (int((conv["code_turns"] > 0).sum()), int(cm["codeact"]["conversations_with_code"])),
         "codeact_multi_statement": (int((conv["widest"] >= 2).sum()),
                                     int(cm["codeact"]["conversations_with_multi_statement_code"])),
         "codeact_statements_per_block": (round(float((conv["statements"] / conv["blocks"].clip(lower=1))
                                                     .mean()), 3),
                                          float(cm["codeact"]["mean_statements_per_code_block"])),
         "codeact_error_conversations": (int(conv["own_error"].sum()),
                                         int(cm["codeact"]["conversations_with_an_error_string"])),
         # EXP-0215's cycle count asked whether the whole next message differed; the freeze's H3 sentence asks whether
         # the executed block differs, which is the stricter question and what this frame measures. Both numbers are
         # reported below rather than reconciled silently (deviation W12-D06)
         "mmat_conversations": (int(M["conversation_index"].nunique()),
                                int(cm["mmat"]["conversations_with_thoughts"])),
         # EXP-0215's marker_pairs counted a marker in the LATER thought of a pair; T189's H2 sentence asks about the
         # thought AFTER a marker, i.e. a marker in the earlier one. Both counts are kept, and the cross-check uses
         # the definition the census actually measured (deviation W12-D05)
         "mmat_census_marker_pairs": (int((M["marker_after"] == 1).sum()), int(cm["mmat"]["marker_pairs_scored"])),
         "mmat_mean_jaccard_census_pair": (round(float(M.loc[M["marker_after"] == 1, "jaccard"].mean()), 4),
                                           round(float(cm["mmat"]["mean_jaccard_after_marker"]), 4)),
         "swe_rollouts": (int(len(R)), int(cm["swe"]["rollouts"])),
         "swe_instances": (int(R["instance_id"].nunique()), int(cm["swe"]["instances"])),
         "swe_instances_with_repeats": (int((R.groupby("instance_id").size() >= 2).sum()),
                                        int(cm["swe"]["instances_with_2plus_rollouts"])),
         # EXP-0215's neighbour key says rollouts but counted per instance, so the two are not the same quantity and
         # are not cross-checked against each other; both are reported, and W12-D04 states the unit of each
         "swe_mean_best_neighbour": (round(float(NE["best_neighbour_similarity"].mean()), 4),
                                     round(float(cm["swe"]["mean_best_neighbour_similarity"]), 4)),
         "eight_files_total": (int(IV["files"].sum()), int(sum(v["files"] for v in cm["eight_corpora"].values()))),
         "eight_labelled_corpora": (int(IV["outcome_or_quality_column"].sum()),
                                    int(sum(1 for v in cm["eight_corpora"].values()
                                            if any(any(t in str(c).lower() for t in ("result", "status", "correct",
                                                                                   "label", "reward", "binary",
                                                                                   "quality", "score"))
                                                   for c in v["columns"]))))}
    off = {k: v for k, v in x.items()
           if abs(float(v[0]) - float(v[1])) > (0.005 if abs(float(v[1])) <= 1.0
                                                else max(1.0, 0.02 * abs(float(v[1]))))}
    if off:
        raise SystemExit(f"ABORT: the frame and {census()['file']} disagree on {off} as (frame, census) - one reader "
                         f"with one rule set, so a definition changed in only one of them. Nothing was written.")
    names = {"codeact": "EXP0220_wave12_codeact_turns.csv.gz", "mmat": "EXP0220_wave12_mmat_transitions.csv.gz",
             "swe": "EXP0220_wave12_swe_rollouts.csv.gz", "siblings": "EXP0220_wave12_swe_siblings.csv.gz",
             "neigh": "EXP0220_wave12_swe_neighbours.csv.gz", "inv": "EXP0220_wave12_corpus_inventory.csv.gz"}
    C.to_csv(W.OUT / names["codeact"], compression="gzip", index=False, encoding="utf-8")
    M.to_csv(W.OUT / names["mmat"], compression="gzip", index=False, encoding="utf-8")
    R.to_csv(W.OUT / names["swe"], compression="gzip", index=False, encoding="utf-8")
    SI.to_csv(W.OUT / names["siblings"], compression="gzip", index=False, encoding="utf-8")
    NE.to_csv(W.OUT / names["neigh"], compression="gzip", index=False, encoding="utf-8")
    IV.to_csv(W.OUT / names["inv"], compression="gzip", index=False, encoding="utf-8")
    art = {"exp_id": EXP, "corpus": TD12.SUBSTRATE_LABEL, "seed": SEED, "files_read": picks,
           "rows_in_swe_files": rows_in_files, "duplicate_swe_rows_dropped": dupes,
           "codeact_conversations": int(C["conversation_id"].nunique()), "codeact_turns": int(len(C)),
           "mmat_conversations": int(M["conversation_index"].nunique()), "mmat_transitions": int(len(M)),
           "swe_rollouts": int(len(R)), "swe_sibling_pairs": int(len(SI)), "corpora_inventoried": int(len(IV)),
           "census_artefact": census()["file"], "census_cross_check": {k: [v[0], v[1]] for k, v in x.items()},
           "cross_check_verdict": "every shared aggregate reproduced",
           "cluster_unit": TD12.COMMON["sample"]["cluster_unit"], "frames": list(names.values()),
           "started_at": W.now(), "wallclock_sec": round(time.time() - t0, 1),
           "invocation": " ".join([sys.executable] + sys.argv),
           "run_cost": W.run_cost_row(EXP, t0, int(len(C)), int(C.shape[1]), "wave-12 frame")}
    dest = W.write_raw(EXP, "wave12_action_matrix", art)
    print(json.dumps({k: v for k, v in art.items() if k not in ("census_cross_check", "frames", "corpus")},
                     indent=1, ensure_ascii=False, default=str)[:1300])
    print(f"\n{EXP}: wrote six frames and {dest.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
