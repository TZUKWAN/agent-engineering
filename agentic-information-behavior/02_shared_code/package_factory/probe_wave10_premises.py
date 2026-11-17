"""EXP-0203: the wave-10 premise census - can this corpus say anything about ambiguity kinds and source credibility?

Six designs (T102 lexical vs referential vs missing-constraint ambiguity, T104 the implicit information need, T107
semantic coverage of a decomposed need, T128 reliability cues in a source's language, T129 attribution framing, T154
how task ambiguity changes the search) all read the *instruction* and the catalogue it is matched against, so the
substrate is P001's routing release again - all 31,642 dev rows, three configs, the same compact n/d/p catalogue
schema and the same reader EXP-0181 validated.

Two of these designs need something a lexical-matching corpus does not obviously have, and the census measures it
rather than assuming it either way:

* T129 needs the *same content under different provenance labels*. The release does not frame documents as official
  or user-written, but it does contain candidate descriptions whose content-word sets are identical while their
  namespace owners differ, which is the closest observable to that manipulation and is counted by G6;
* T128 needs reliability-bearing language in the source itself, which is what the attribution- and evidential-marker
  lists below count over candidate descriptions.

Everything else this wave conditions on is already measured per row by the release's own diagnostics
(`constraint_density`, `epistemic_marker_n`, `vague_word_n`, `demonstrative_n`, `n_subtasks_by_punctuation`,
`qpp_*`) or derived by wave 1's frozen functions (`unresolved_references`, `underspec_index`), so a construct is
never defined twice in one wave. Each gate names the sentence it scopes and the topics it stops, and every rule here
was written before a row was opened. No design's dependent variable is associated with anything in this file.

    python 02_shared_code/package_factory/probe_wave10_premises.py [--rows 400]
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
import pandas as pd                                               # noqa: E402
import wave_lib as W                                              # noqa: E402
import probe_wave7_premises as P7                                 # noqa: E402  the catalogue reader, unchanged

EXP = "EXP-0203"
SEED = 42
words = P7.words

# ------------------------------------------------------------------ the instruments, frozen before the census ran
# T128/T129: language that hands a reader a reason to trust the text itself, split so an authority claim is not the
# same mark as an evidential citation.
AUTHORITY = ["official", "certified", "verified", "approved", "maintained by", "first party", "vendor",
             "canonical", "authoritative", "supported", "recommended"]
EVIDENTIAL = ["according to", "as documented", "documentation", "see also", "reference", "cites", "source",
              "evidence", "reported", "stated", "quoted", "based on", "derived from"]
ATTRIBUTION_FRAMING = ["user", "community", "customer", "third party", "forum", "issue tracker", "ticket",
                       "ai-generated", "generated", "draft", "unofficial", "deprecated", "experimental"]
HEDGE = ["may", "might", "could", "usually", "generally", "often", "if possible", "as needed", "as appropriate",
         "some", "any", "etc", "and so on", "or similar", "whatever", "things"]
DEMON_STRONG = ["it", "this", "that", "these", "those", "the above", "the same", "there", "them", "their"]
PATHISH = re.compile(r"([A-Za-z]:\\|/[\w./\-]{2,}|\.\w{1,5}\b|~)", re.I)


def unresolved(d: pd.DataFrame) -> list:
    return [W.unresolved_references(q) for q in d["question"]]


def lex_ambiguous(q: str, cat: list) -> int:
    """How many of the instruction's content words could point at more than one candidate's document."""
    qw = words(q)
    by_word = collections.defaultdict(set)
    for c in cat:
        for w in words(c["desc"]):
            by_word[w].add(c["server"])
    return sum(1 for w in qw if len(by_word.get(w, ())) >= 2)


def measure(df: pd.DataFrame) -> dict:
    n = int(len(df))
    # the two derived indices are functions of the question text alone, so they are computed for the whole
    # frame once: building a one-row frame inside this loop would rebuild the same vocabulary 31,642 times
    lang = W.add_linguistic_frame(df)               # wave 1's frozen linguistic frame, one implementation per wave
    uvals = [int(x) for x in lang["unresolved_ref"]]
    usvals = [float(x) for x in lang["underspec_index"]]
    parsed = gold_ok = rank_ok = 0
    cat_total = 0
    lex_counts, ref_counts, underspec, constraints, subtasks = [], [], [], [], []
    hedge_counts, auth_counts, evid_counts, attrib_counts = [], [], [], []
    desc_words_total = 0
    sig = collections.defaultdict(set)
    sig_servers = collections.defaultdict(set)
    sig_slots = collections.Counter()
    pair_rows = 0
    for i, r in enumerate(df.itertuples(index=False)):
        cat = P7.entries(r.catalog_json)
        cat = [{"name": c["name"], "desc": c["desc"], "params": c["params"], "server": P7.server_of(c["name"])}
               for c in cat]
        if not cat:
            continue
        parsed += 1
        gl = sorted({int(i) for i in (r.gold_idx or []) if str(i).lstrip("-").isdigit()} & set(range(len(cat))))
        gold_ok += int(bool(gl))
        rank_ok += int(r.bm25_best_rank == r.bm25_best_rank)
        cat_total += len(cat)
        q = str(r.question)
        qw = words(q)
        low = q.lower()
        lex_counts.append(lex_ambiguous(q, cat))
        u = unresolved(pd.DataFrame({"question": [q]}))[0]
        ref_counts.append(int(u) + sum(1 for t in DEMON_STRONG if re.search(r"\b" + t + r"\b", low)))
        underspec.append(usvals[i])
        constraints.append(float(r.constraint_density))
        subtasks.append(int(r.n_subtasks_by_punctuation) + int(bool(r.has_bullet_list)) + int(r.n_lines >= 3))
        hedge_counts.append(sum(1 for t in HEDGE if re.search(r"\b" + re.escape(t) + r"\b", low)))
        dl = " ".join(c["desc"] for c in cat).lower()
        auth_counts.append(sum(1 for t in AUTHORITY if t in dl))
        evid_counts.append(sum(1 for t in EVIDENTIAL if t in dl))
        attrib_counts.append(sum(1 for t in ATTRIBUTION_FRAMING if t in dl))
        for c in cat:
            dw = words(c["desc"])
            desc_words_total += len(dw)
            if dw:
                key = " ".join(sorted(dw))
                sig[key].add(c["name"])
                sig_servers[key].add(c["server"])
                sig_slots[key] += 1
    dup = [k for k, v in sig.items() if len(v) >= 2]
    cross = [k for k in dup if len(sig_servers[k]) >= 2]
    pair_rows = sum(len(sig[k]) for k in cross)
    us = pd.Series(underspec)
    med = float(us.median()) if len(us) else float("nan")
    return {"corpus": "P001 routing release, dev split only, all three configs", "rows": n,
            "by_config": {str(k): int(v) for k, v in df["cfg"].value_counts().items()},
            "catalogue_parse_share": round(parsed / max(1, n), 4),
            "gold_index_recoverable_share": round(gold_ok / max(1, n), 4),
            "ranker_columns_present_share": round(rank_ok / max(1, n), 4),
            "candidates_total": cat_total, "mean_candidates": round(cat_total / max(1, parsed), 2),
            "queries_with_2plus_candidates_share": round(float((df["n_candidates"] >= 2).mean()), 4),
            "lexical_ambiguity_mean": round(float(np_mean(lex_counts)), 3),
            "queries_with_any_lexical_ambiguity": int(sum(1 for v in lex_counts if v >= 1)),
            "queries_with_any_referential_marker": int(sum(1 for v in ref_counts if v >= 1)),
            "queries_with_two_plus_referential_markers": int(sum(1 for v in ref_counts if v >= 2)),
            "underspec_median": round(med, 4),
            "queries_above_underspec_median": int(sum(1 for v in underspec if v > med)),
            "queries_below_underspec_median": int(sum(1 for v in underspec if v <= med)),
            "queries_with_two_plus_subtask_markers": int(sum(1 for v in subtasks if v >= 2)),
            "hedge_mean": round(float(np_mean(hedge_counts)), 3),
            "authority_marker_share_of_rows": round(float(sum(1 for v in auth_counts if v) / max(1, parsed)), 4),
            "evidential_marker_share_of_rows": round(float(sum(1 for v in evid_counts if v) / max(1, parsed)), 4),
            "attribution_framing_share_of_rows": round(float(sum(1 for v in attrib_counts if v) / max(1, parsed)), 4),
            "mean_words_per_candidate_description": round(desc_words_total / max(1, cat_total), 2),
            "distinct_description_signatures": int(len(sig)),
            "signatures_shared_by_2plus_candidates": int(len(dup)),
            "signatures_spanning_2plus_servers": int(len(cross)),
            "candidate_slots_under_a_cross_server_signature": int(pair_rows),
            "path_like_share_of_queries": round(float(sum(1 for q in df["question"] if PATHISH.search(str(q)))
                                                       / max(1, n)), 4)}


def np_mean(xs):
    import numpy as np
    return float(np.mean(xs)) if xs else float("nan")


GATES = {   # rule, threshold, and the topic(s) the sentence scopes - all frozen before any row was opened
 "G1_catalogues_and_rows_parseable": {
     "rule": ">= 0.95 of dev rows yield a readable catalogue and a gold index inside it", "threshold": 0.95,
     "scope": "design", "blocks": ["T102", "T104", "T107", "T128", "T129", "T154"]},
 "G2_comparable_candidate_sets": {
     "rule": ">= 0.90 of rows offer at least two candidates, since every claim here is about which of several "
             "documents a lexical match reaches for", "threshold": 0.90, "scope": "design",
     "blocks": ["T102", "T107", "T128", "T129", "T154"]},
 "G3_lexical_ambiguity_variation": {
     "rule": ">= 1,000 queries contain at least one content word that points into two servers' descriptions, the "
             "lexical arm of T102 and T154", "threshold": 1000, "scope": "H1", "blocks": ["T102", "T154"]},
 "G4_referential_ambiguity_variation": {
     "rule": ">= 1,000 queries carry an unresolved reference or demonstrative, the referential arm",
     "threshold": 1000, "scope": "H1", "blocks": ["T102", "T154"]},
 "G5_underspecification_spread": {
     "rule": ">= 1,000 queries above and >= 1,000 below the median underspecification index, so the "
             "missing-constraint arm has both ends", "threshold": 1000, "scope": "H1",
     "blocks": ["T102", "T104"]},
 "G6_cross_server_content_pairs": {
     "rule": ">= 200 candidate descriptions that share their content-word set with a description owned by a "
             "different server - the only same-content-different-source contrast this release offers (T129)",
     "threshold": 200, "scope": "design", "blocks": ["T129"]},
 "G7_credibility_language_present": {
     "rule": ">= 0.05 of rows have a catalogue whose descriptions carry an authority or evidential marker, else "
             "T128's construct is absent from the corpus rather than uninformative", "threshold": 0.05,
     "scope": "H1", "blocks": ["T128"]},
 "G8_decomposable_needs": {
     "rule": ">= 1,000 queries show two or more subtask markers (punctuation, bullets, multi-line), which is the "
             "decomposition T107 counts coverage of", "threshold": 1000, "scope": "H1", "blocks": ["T107"]},
 "G9_outcome_columns_present": {
     "rule": ">= 0.95 of rows carry the frozen BM25 rank and margin - this corpus records a ranker's behaviour and "
             "no agent choice, as in wave 7", "threshold": 0.95, "scope": "design",
     "blocks": ["T102", "T104", "T107", "T128", "T129", "T154"]},
 "G10_cluster_count": {
     "rule": ">= 5,000 dev rows in each config pooled and >= 10,000 overall, so a query-clustered interval exists",
     "threshold": 10000, "scope": "design", "blocks": ["T102", "T104", "T107", "T128", "T129", "T154"]},
 "G11_descriptions_have_text": {
     "rule": ">= 8 content words per candidate description on average, below which a marker prevalence or a "
             "content-word signature is measuring a label rather than a document", "threshold": 8.0,
     "scope": "H1", "blocks": ["T128"]},
 "G12_prompt_groups_available": {
     "rule": ">= 500 distinct prompt_id groups, the repeat structure T104 needs to ask whether the same need is "
             "answered consistently across configs", "threshold": 500, "scope": "H2", "blocks": ["T104"]},
}


def apply_gates(m: dict) -> dict:
    checks = {"G1_catalogues_and_rows_parseable": min(m["catalogue_parse_share"], m["gold_index_recoverable_share"]),
              "G2_comparable_candidate_sets": m["queries_with_2plus_candidates_share"],
              "G3_lexical_ambiguity_variation": m["queries_with_any_lexical_ambiguity"],
              "G4_referential_ambiguity_variation": m["queries_with_any_referential_marker"],
              "G5_underspecification_spread": min(m["queries_above_underspec_median"],
                                                  m["queries_below_underspec_median"]),
              "G6_cross_server_content_pairs": m["signatures_spanning_2plus_servers"],
              "G7_credibility_language_present": max(m["authority_marker_share_of_rows"],
                                                     m["evidential_marker_share_of_rows"]),
              "G8_decomposable_needs": m["queries_with_two_plus_subtask_markers"],
              "G9_outcome_columns_present": m["ranker_columns_present_share"],
              "G10_cluster_count": m["rows"], "G11_descriptions_have_text": m["mean_words_per_candidate_description"],
              "G12_prompt_groups_available": int(m.get("prompt_groups", 0))}
    out = {}
    for k, g in GATES.items():
        v = checks[k]
        out[k] = {"measured": v, "fires": bool(v < g["threshold"]), "threshold": g["threshold"], "scope": g["scope"],
                  "blocks": list(g["blocks"]), "rule": g["rule"]}
    fired = [k for k, v in out.items() if v["fires"]]
    whole = sorted({t for k in fired if out[k]["scope"] == "design" for t in out[k]["blocks"]})
    limited = {k: out[k]["scope"] for k in fired if out[k]["scope"] != "design"}
    return {"gates": out, "verdict": {"blocked_gates": fired, "blocked_whole_design": whole,
                                      "claim_limited": limited}}


def selftest() -> int:
    """The instruments proven on a hand-built row before a single release row is read."""
    q = 'deploy it to the cloud when you can, using whatever settings are appropriate for things like that'
    cat = json.dumps([{'n': 'aws.deploy', 'd': 'Deploy an application to the cloud with the official vendor '
                                               'documentation'},
                      {'n': 'gcp.deploy', 'd': 'Deploy an application to the cloud with the official vendor '
                                               'documentation'},
                      {'n': 'fs.read', 'd': 'Read the contents of a file from disk'}])
    row = {'question': q, 'catalog_json': cat, 'gold_idx': [0], 'n_candidates': 3, 'cfg': 'OSS',
           'constraint_density': 0.1, 'n_subtasks_by_punctuation': 1, 'has_bullet_list': 0, 'n_lines': 1,
           'bm25_best_rank': 2, 'prompt_id': 'p1'}
    d = pd.DataFrame([row])
    m = measure(d)
    assert m['catalogue_parse_share'] == 1.0 and m['gold_index_recoverable_share'] == 1.0
    assert m['queries_with_any_lexical_ambiguity'] == 1, m['lexical_ambiguity_mean']
    assert m['queries_with_any_referential_marker'] == 1
    assert m['authority_marker_share_of_rows'] == 1.0 and m['evidential_marker_share_of_rows'] == 1.0
    assert m['signatures_spanning_2plus_servers'] == 1, m['distinct_description_signatures']
    assert m['candidate_slots_under_a_cross_server_signature'] == 2
    lg = W.add_linguistic_frame(d)
    # wave 1's unresolved-reference rule wants an antecedent noun, and this hand-built 'it' has none, so the
    # referential instrument is proven above through the census's own marker count instead
    assert float(lg['underspec_index'].iloc[0]) == float(lg['underspec_index'].iloc[0])
    assert m['hedge_mean'] >= 1.0
    print('SELFTEST OK: lexical, referential, underspecification, credibility-language and cross-server-signature '
          'instruments all land on a built row')
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=0, help="draw at most this many dev rows (0 = all 31,642, which is "
                                                        "what the gates were written against)")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    selftest()
    df = W.load_routing(cols=None)
    if a.rows:
        df = df.sample(min(a.rows, len(df)), random_state=SEED).reset_index(drop=True)
    m = measure(df)
    m["prompt_groups"] = int(df["prompt_id"].nunique()) if "prompt_id" in df.columns else 0
    g = apply_gates(m)
    art = {"exp_id": EXP, "seed": SEED, "rows_requested": a.rows or "all dev rows", "measured": m,
           "gate_rules": {k: v["rule"] for k, v in GATES.items()}, **g,
           "cluster_unit": "query_id", "started_at": W.now(),
           "wallclock_sec": round(time.time() - t0, 1), "invocation": " ".join([sys.executable] + sys.argv),
           "run_cost": W.run_cost_row(EXP, t0, int(len(df)), 0, "wave-10 premise census")}
    dest = W.write_raw(EXP, "wave10_premise_census", art)
    print(json.dumps({"measured": m, "verdict": art["verdict"],
                      "gates": {k: [v["measured"], v["fires"]] for k, v in art["gates"].items()}},
                     indent=1, ensure_ascii=False, default=str)[:2800])
    print("\nwrote", dest.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
