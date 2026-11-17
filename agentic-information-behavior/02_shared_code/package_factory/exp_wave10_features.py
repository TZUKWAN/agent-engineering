"""EXP-0205: wave 10's requirement frame - what an instruction asks for, and what the catalogue surfaced.

One row per dev instruction of P001's routing release. The columns are the ones T104's three hypotheses name, plus the
ambiguity instruments the census measured, so a coefficient in `exp_wave10_designs.py` reads the same definition the
freeze wrote:

* a **requirement** is an executable clause of the instruction: a segment split on clause boundaries (comma,
  semicolon, ' and ', ' then ', sentence end, one item of a bullet or numbered list) that opens with an imperative
  verb from the frozen action list or carries a constraint marker from wave 1's table, and holds at least two content
  words. Requirement count is the denominator of coverage;
* **coverage_any** is the share of those requirements with at least one content word in at least one candidate
  description, and **coverage_half** the stricter reading where at least half of them appear in the *same* candidate.
  The two are the instrument-invariance pair this wave owes: a single definition of 'the need was surfaced' is as
  fragile here as a single modality lexicon was in wave 4;
* the ambiguity kinds are the census's, imported from it rather than restated, so a lexical-ambiguity count means the
  same thing in EXP-0203 and here.

The frame cross-checks every aggregate it shares with EXP-0203 and refuses to write when a pair diverges.

    python 02_shared_code/package_factory/exp_wave10_features.py
"""
from __future__ import annotations

import argparse
import collections
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
import probe_wave7_premises as P7                                 # noqa: E402  catalogue reader, content words
import probe_wave10_premises as P10                                # noqa: E402  the ambiguity instruments, one place

EXP = "EXP-0205"
TD10 = __import__("topic_designs_wave10")
SEED = TD10.SEED
ACTION_VERB = sorted(set(P7.AFFORDANCE) | {"deploy", "configure", "install", "remove", "rename", "append",
                                           "prepend", "collect", "emit", "serialize", "normalise", "normalize",
                                           "validate", "compare", "report", "return", "output", "store", "load"})
CONSTRAINT_MARK = ["must", "should not", "must not", "only", "exactly", "at least", "no more than", "required",
                   "without", "keep", "avoid", "ensure", "preserve", "not", "never", "always", "each", "every"]
SPLIT = re.compile(r"[,;:]|\band\b|\bthen\b|\bbut\b|\.|\?|!|\n|\)|\(", re.I)
LIST_ITEM = re.compile(r"^\s*(?:[-*]|\d+[.)])\s+(.+)$", re.M)
GENERIC = set("the a an of and or to in on for with is are was were be it this that i you we they my your their "
              "will would can could should there here from as at by not no all any please also them its use using"
              .split())


def requirements(q: str) -> list:
    """The instruction's executable clauses, as lists of content words."""
    segs = [s for s in re.split(r"[,;]|\band\b|\bthen\b|\bbut\b|\.|\?|!|\n", str(q)) if s.strip()]
    items = [m.group(1) for m in LIST_ITEM.finditer(str(q))]
    segs = [s for s in segs if s not in items] + items
    out = []
    for s in segs:
        low = s.lower()
        cw = {w for w in P7.words(s) if w not in GENERIC}
        if len(cw) < 2:
            continue
        imperative = any(re.search(r"\b" + re.escape(v) + r"\b", low) for v in ACTION_VERB)
        constrained = any(re.search(r"\b" + re.escape(c) + r"\b", low) for c in CONSTRAINT_MARK)
        if imperative or constrained:
            out.append(cw)
    seen, uniq = set(), []
    for cw in out:
        key = frozenset(cw)
        if key not in seen:
            seen.add(key)
            uniq.append(cw)
    return uniq


def coverage(reqs: list, cat_words: list) -> tuple:
    """(any-reading, strict-reading) coverage of the requirement set by the candidate descriptions."""
    if not reqs:
        return float("nan"), float("nan")
    any_hit = strict = 0
    for cw in reqs:
        if any(cw & w for w in cat_words):
            any_hit += 1
        if any(len(cw & w) >= max(1, int(np.ceil(len(cw) / 2.0))) for w in cat_words):
            strict += 1
    return round(any_hit / len(reqs), 4), round(strict / len(reqs), 4)


def rows_for(df: pd.DataFrame) -> list:
    lang = W.add_linguistic_frame(df)              # wave 1's indices, one implementation across the estate
    out = []
    for i, r in enumerate(lang.itertuples(index=False)):
        cat = P7.entries(r.catalog_json)
        if not cat:
            continue
        gold = sorted({int(k) for k in (r.gold_idx or []) if str(k).lstrip("-").isdigit()} & set(range(len(cat))))
        if not gold:
            continue
        reqs = requirements(r.question)
        cw = [P7.words(c["desc"]) for c in cat]
        cov_any, cov_strict = coverage(reqs, cw)
        by_word = collections.defaultdict(set)
        for c, w in zip(cat, cw):
            for x in w:
                by_word[x].add(P7.server_of(c["name"]))
        low = str(r.question).lower()
        refs = int(lang["unresolved_ref"].iloc[i]) + sum(1 for t in P10.DEMON_STRONG
                                                         if re.search(r"\b" + t + r"\b", low))
        out.append({"query_id": f"{r.cfg}|{r.uuid}", "cfg": str(r.cfg), "uuid": str(r.uuid),
                    "prompt_id": str(r.prompt_id), "n_candidates": int(len(cat)), "n_gold": int(len(gold)),
                    "bm25_best_rank": int(r.bm25_best_rank), "fail_at_1": int(r.fail_at_1),
                    "bm25_margin": float(r.bm25_margin), "candidates_before_gold": int(r.bm25_best_rank - 1),
                    "requirement_n": int(len(reqs)),
                    "requirement_words": int(sum(len(x) for x in reqs)),
                    "coverage_any": cov_any, "coverage_half": cov_strict,
                    "underspec_index": float(lang["underspec_index"].iloc[i]),
                    "constraint_total": float(lang["constraint_total"].iloc[i]),
                    "constraint_types": float(lang["constraint_types"].iloc[i]),
                    "unresolved_ref": int(lang["unresolved_ref"].iloc[i]), "ellipsis_n": int(lang["ellipsis_n"].iloc[i]),
                    "entity_density": float(lang["entity_density"].iloc[i]),
                    "question_words": int(len(P7.words(r.question))),
                    "lexical_ambiguity": int(sum(1 for w in P7.words(r.question) if len(by_word.get(w, ())) >= 2)),
                    "referential_markers": int(refs),
                    "authority_marker": int(any(any(t in c["desc"].lower() for t in P10.AUTHORITY) for c in cat)),
                    "evidential_marker": int(any(any(t in c["desc"].lower() for t in P10.EVIDENTIAL) for c in cat))})
    return out


def census() -> dict:
    for f in sorted(W.RAWRES.glob("EXP0203_wave10_premise_census_*.json"), reverse=True):
        a = json.loads(f.read_text(encoding="utf-8"))
        if "--rows" in str(a.get("invocation", "")):
            continue
        return {"file": f.name, "measured": a["measured"]}
    raise SystemExit("ABORT: no whole-release EXP-0203 census exists, so this frame has nothing to check itself "
                     "against")


def selftest() -> int:
    """The requirement extraction and both coverage readings proven on a hand-built instruction."""
    q = ("Read the CSV file in /data/orders.csv, remove the duplicate rows, "
         "then write the cleaned file to /data/out.csv")
    cat = json.dumps([{"n": "fs.read", "d": "Read the contents of a file from disk"},
                      {"n": "fs.dedupe", "d": "Remove duplicate rows from a CSV file"},
                      {"n": "fs.write", "d": "Write the contents of a file to disk, cleaned"}])
    cat_words = [P7.words(c["desc"]) for c in P7.entries(cat)]
    reqs = requirements(q)
    assert len(reqs) >= 3, [sorted(r) for r in reqs]
    assert any("duplicate" in r or "rows" in r for r in reqs)
    any_c, half_c = coverage(reqs, cat_words)
    assert any_c >= half_c and 0.0 <= half_c <= 1.0, (any_c, half_c)
    assert any_c > 0.6, any_c
    bare = coverage(reqs, [{"zebra", "quark"}])
    assert bare == (0.0, 0.0), bare
    print("SELFTEST OK: requirement clauses, both coverage readings and the empty-catalogue case land on a built row")
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
    df = W.load_routing(cols=None)
    F = pd.DataFrame(rows_for(df))
    if F.empty:
        raise SystemExit("ABORT: no instruction produced a readable catalogue with a gold index")
    F["log_candidates"] = np.log1p(F["n_candidates"].astype(float))
    F["question_words_log"] = np.log1p(F["question_words"].astype(float))
    F["coverage_any_z"] = (F["coverage_any"] - F["coverage_any"].mean()) / (F["coverage_any"].std(ddof=0) or 1.0)
    F["underspec_z"] = (F["underspec_index"] - F["underspec_index"].mean()) / \
                       (F["underspec_index"].std(ddof=0) or 1.0)
    F["lex_amb_z"] = (F["lexical_ambiguity"] - F["lexical_ambiguity"].mean()) / \
                     (F["lexical_ambiguity"].std(ddof=0) or 1.0)
    F["ref_mark_z"] = (F["referential_markers"] - F["referential_markers"].mean()) / \
                      (F["referential_markers"].std(ddof=0) or 1.0)
    F["constraint_total_z"] = (F["constraint_total"] - F["constraint_total"].mean()) / \
                              (F["constraint_total"].std(ddof=0) or 1.0)
    F["has_2plus_candidates"] = (F["n_candidates"] >= 2).astype(int)
    F["cand_quartile"] = pd.qcut(F["n_candidates"].rank(method="first"), 4,
                                  labels=["q1_smallest", "q2", "q3", "q4_largest"]).astype(str)
    F["req_band"] = pd.cut(F["requirement_n"], [-0.5, 0.5, 1.5, 2.5, 1e9],
                           labels=["none", "1", "2", "3plus"]).astype(str)
    cen, cm = census()["file"], census()["measured"]
    x = {"rows": (int(len(F)), int(cm["rows"])),
         "candidates_total": (int(F["n_candidates"].sum()), int(cm["candidates_total"])),
         "comparable_share": (round(float(F["has_2plus_candidates"].mean()), 4),
                              float(cm["queries_with_2plus_candidates_share"])),
         "rows_with_lexical_ambiguity": (int((F["lexical_ambiguity"] >= 1).sum()),
                                         int(cm["queries_with_any_lexical_ambiguity"])),
         "rows_with_referential_marker": (int((F["referential_markers"] >= 1).sum()),
                                          int(cm["queries_with_any_referential_marker"])),
         "mean_candidates": (round(float(F["n_candidates"].mean()), 2), float(cm["mean_candidates"])),
         "prompt_groups": (int(F["prompt_id"].nunique()), int(cm["prompt_groups"])),
         "authority_share": (round(float(F["authority_marker"].mean()), 4), float(cm["authority_marker_share_of_rows"])),
         "evidential_share": (round(float(F["evidential_marker"].mean()), 4),
                              float(cm["evidential_marker_share_of_rows"])),
         "underspec_median": (round(float(F["underspec_index"].median()), 4),
                               float(cm["underspec_median"]))}
    def too_far(v):
        a, b = float(v[0]), float(v[1])
        tol = 0.005 if abs(b) <= 1.0 else max(1.0, 0.02 * abs(b))   # shares to three decimals, counts to two percent
        return abs(a - b) > tol
    off = {k: v for k, v in x.items() if too_far(v)}
    if off:
        raise SystemExit(f"ABORT: the frame and {cen} disagree on {off} as (frame, census) - one reader with one rule "
                         f"set, so a definition changed in only one of them. Nothing was written.")
    dest_f = W.OUT / "EXP0205_wave10_requirement_features.csv.gz"
    F.to_csv(dest_f, compression="gzip", index=False, encoding="utf-8")
    art = {"exp_id": EXP, "corpus": TD10.SUBSTRATE_LABEL, "seed": SEED, "rows": int(len(F)),
           "census_artefact": cen, "census_cross_check": {k: [v[0], v[1]] for k, v in x.items()},
           "cross_check_verdict": "every shared aggregate reproduced",
           "cluster_unit": TD10.COMMON["sample"]["cluster_unit"],
           "mean_requirements": round(float(F["requirement_n"].mean()), 3),
           "rows_with_any_requirement": int((F["requirement_n"] >= 1).sum()),
           "mean_coverage_any": round(float(F["coverage_any"].mean()), 4),
           "mean_coverage_half": round(float(F["coverage_half"].mean()), 4),
           "coverage_any_share_at_least_half": round(float((F["coverage_any"] >= 0.5).mean()), 4),
           "requirement_count_distribution": {str(int(k)): int(v) for k, v in
                                              F["requirement_n"].value_counts().sort_index().head(12).items()},
           "by_config": {str(k): int(v) for k, v in F["cfg"].value_counts().items()},
           "frames": [dest_f.name], "started_at": W.now(), "wallclock_sec": round(time.time() - t0, 1),
           "invocation": " ".join([sys.executable] + sys.argv),
           "run_cost": W.run_cost_row(EXP, t0, int(len(F)), int(F.shape[1]), "wave-10 requirement frame")}
    dest = W.write_raw(EXP, "wave10_requirement_matrix", art)
    print(json.dumps({k: v for k, v in art.items() if k != "requirement_count_distribution"},
                     indent=1, ensure_ascii=False, default=str)[:1400])
    print(f"\n{EXP}: wrote {dest_f.name} ({len(F)} instructions) and {dest.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
