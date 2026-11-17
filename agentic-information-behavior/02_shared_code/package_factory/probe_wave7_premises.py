"""EXP-0181: the wave-7 premise census - does the routing release carry a lexical ecosystem to measure?

Wave 7 measures the *candidate set* an agent chooses from: near-synonym decoys (T161), the affordance language of a
tool description (T162), whether a tool namespace reduces overload (T164), what the catalogue population looks like
as an ecosystem of sources (T165), how many irrelevant candidates contaminate the ranking (T166), and which tools
are needed together (T169). Every one of those is a claim about structure inside `catalog_json` and about the frozen
ranker's behaviour on it, so the census measures whether the release carries that structure at all - how many
candidates per query, whether names have namespace separators, whether a non-gold candidate is lexically close to a
gold one, how many queries need two tools - before any of it is associated with an outcome.

The instrument facts are reported rather than assumed: P001's shipped catalogue parser returns nothing for these rows
(it expects `name`/`description` keys, and the release stores `n`/`d`/`p`), so this census brings its own reader and
prints the coverage of both. The dependent variables available anywhere in this corpus are the frozen BM25 rank,
margin and fail-at-k columns of the released selection; there is no recorded agent choice here, and no design in this
wave claims one.

The sample rule is frozen before the first row is read: `W.load_routing` with its own dev-only split assertion, all
three configs, every dev row, and `query_id` (config + uuid) as the cluster - the same unit every earlier wave that
scored this release used.

    python 02_shared_code/package_factory/probe_wave7_premises.py [--rows 40000]
"""
from __future__ import annotations

import argparse
import collections
from itertools import combinations
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

EXP = "EXP-0181"
SEED = 42
STOP = set("the a an of and or to in on for with is are was were be it this that i you we they my your their "
           "will would can could should there here from as at by not no all any using use new create".split())
NS_SEP = re.compile(r"[._]|__|::")
AFFORDANCE = ["create", "build", "search", "fetch", "read", "write", "list", "get", "set", "update", "delete",
              "upload", "download", "run", "execute", "query", "filter", "sort", "convert", "parse", "render",
              "deploy", "send", "receive", "schedule", "monitor", "validate", "compute", "extract", "generate",
              "translate", "summarise", "summarize", "retrieve", "browse", "open", "close", "export", "import"]
# The same frozen list in word-boundary form, for the places that need a *count* rather than the gate's presence test.
# A bare substring counts "get" inside "target" and a leading space misses "Read the contents of ..." at position 0,
# so neither is a counter; this is. G5 below was measured with the substring test and is reported as it was measured.
AFFORD_RX = re.compile(r"\b(" + "|".join(sorted(AFFORDANCE, key=len, reverse=True)) + r")")
PARAM_HINT = re.compile(r"\b(param|argument|field|input|option|required|accepts|takes)\b", re.I)


def words(s) -> set:
    return {w for w in re.findall(r"[a-z0-9_./:-]{3,}", str(s).lower()) if w not in STOP and not w.isdigit()}


def entries(catalog_json: str) -> list:
    """The release's own compact schema: {"n": name, "d": description, "p": [parameter names]}."""
    try:
        raw = json.loads(catalog_json)
    except Exception:                                            # noqa: BLE001 - an unparseable catalogue is counted
        return []
    out = []
    for e in raw if isinstance(raw, list) else []:
        if not isinstance(e, dict):
            continue
        out.append({"name": str(e.get("n") or e.get("name") or ""),
                    "desc": str(e.get("d") or e.get("description") or ""),
                    "params": [str(x) for x in (e.get("p") or e.get("parameters") or [])]})
    return out


def server_of(name: str) -> str:
    """The namespace prefix of a tool name, or `ungrouped` when it has none - the unit T164 and T165 count in."""
    s = re.split(r"[._]|::", str(name), maxsplit=1)[0].strip().lower()
    return s or "ungrouped"


GATES = {   # rule, threshold, and the topic(s) the sentence scopes - all frozen before any row was opened
 "G1_catalogues_parseable": {
     "rule": ">= 0.95 of dev rows yield a catalogue with at least one named candidate under the release's own "
             "n/d/p schema (the wave's subject has to be readable)", "threshold": 0.95, "scope": "design",
     "blocks": ["T161", "T162", "T164", "T165", "T166", "T169"]},
 "G2_gold_indices_recoverable": {
     "rule": ">= 0.95 of rows carry a non-empty gold index list that is inside the candidate range, else there is no "
             "ground truth to rank against", "threshold": 0.95, "scope": "design",
     "blocks": ["T161", "T162", "T164", "T165", "T166", "T169"]},
 "G3_namespace_separators_present": {
     "rule": ">= 0.05 of candidate names carry a namespace separator, else T164's grouped-versus-flat contrast has "
             "no grouped arm", "threshold": 0.05, "scope": "H1", "blocks": ["T164"]},
 "G4_near_synonym_queries": {
     "rule": ">= 200 queries contain a non-gold candidate whose description shares >= 0.5 of its content words with "
             "a gold candidate - a decoy has to exist for the misselection claim (T161)", "threshold": 200,
     "scope": "H1", "blocks": ["T161"]},
 "G5_affordance_language_present": {
     "rule": ">= 0.30 of candidate descriptions contain at least one affordance verb from the frozen list, else "
             "T162's construct is absent from the corpus rather than uninformative", "threshold": 0.30,
     "scope": "design", "blocks": ["T162"]},
 "G6_multi_gold_queries": {
     "rule": ">= 200 queries need >= 2 gold tools, which is the only source of a co-occurrence pair (T169)",
     "threshold": 200, "scope": "H1", "blocks": ["T169"]},
 "G7_distinct_gold_pairs": {
     "rule": ">= 200 distinct unordered gold-tool pairs across those queries, else the dependency network is a list, "
             "not a network (T169)", "threshold": 200, "scope": "H2", "blocks": ["T169"]},
 "G8_contaminated_rankings": {
     "rule": ">= 0.10 of queries have a candidate with no content-word overlap with the question ranked above every "
             "gold one by the frozen ranker, else 'contamination' describes nothing (T166)", "threshold": 0.10,
     "scope": "H1", "blocks": ["T166"]},
 "G9_distinct_servers": {
     "rule": ">= 30 distinct namespace prefixes across the dev rows, the floor below which an ecosystem description "
             "is a list of a few catalogues (T165)", "threshold": 30, "scope": "design", "blocks": ["T165"]},
 "G10_cluster_count_per_config": {
     "rule": ">= 500 queries in each of the three configs, so a cluster-robust interval exists inside every config and "
             "a pooled coefficient cannot hide a config (every design in the wave)", "threshold": 500, "scope": "design",
     "blocks": ["T161", "T162", "T164", "T165", "T166", "T169"]},
 "G11_ranker_columns_present": {
     "rule": ">= 0.95 of rows carry the frozen BM25 rank and margin columns, which are this corpus's only measured "
             "selection outcome - there is no recorded agent choice", "threshold": 0.95, "scope": "design",
     "blocks": ["T161", "T162", "T164", "T165", "T166", "T169"]},
 "G12_parameter_lists_present": {
     "rule": ">= 0.30 of candidates carry a parameter list, else the specificity arm of T162's construct is empty",
     "threshold": 0.30, "scope": "H3", "blocks": ["T162"]},
}


def selftest() -> int:
    """The reader and the two structural rules are proved on a hand-built catalogue before any row is read."""
    cat = json.dumps([{"n": "fs.read_file", "d": "Read a file from disk and return its contents", "p": ["path"]},
                      {"n": "fs_write", "d": "Write contents to a file on disk", "p": ["path", "content"]},
                      {"n": "weather", "d": "Fetch the forecast for a city", "p": []}])
    e = entries(cat)
    assert [x["name"] for x in e] == ["fs.read_file", "fs_write", "weather"], e
    assert e[1]["params"] == ["path", "content"]
    assert server_of("fs.read_file") == "fs" and server_of("weather") == "weather"
    assert NS_SEP.search("fs_write") and not NS_SEP.search("weather")
    assert entries("[not json") == [] and entries(json.dumps({"n": "x"})) == []
    a, b = words(e[0]["desc"]), words(e[1]["desc"])
    assert 0.0 < len(a & b) / max(1, len(b)) < 1.0, (a, b)     # near-synonym, not identical
    assert sum(1 for x in e if any(v in x["desc"].lower() for v in AFFORDANCE)) == 3
    print("SELFTEST OK: the n/d/p catalogue, namespace split, separator, overlap and affordance rules all land")
    return 0


def measure(df: pd.DataFrame) -> dict:
    n = int(len(df))
    parsed = 0
    gold_ok = 0
    names = []
    descs = 0
    descs_with_verb = 0
    with_params = 0
    sep_names = 0
    servers = collections.Counter()
    decoy_queries = 0
    contaminated = 0
    multi_gold_rows = 0
    pairs = set()
    no_overlap_above_gold = 0
    for r in df.itertuples(index=False):
        cat = entries(r.catalog_json)
        if not cat:
            continue
        parsed += 1
        gold = set(int(i) for i in (r.gold_idx or []))
        gold = {i for i in gold if 0 <= i < len(cat)}
        if not gold:
            continue
        gold_ok += 1
        gw = [words(cat[i]["desc"]) for i in sorted(gold)]
        has_decoy = False
        for i, c in enumerate(cat):
            nm = c["name"]
            names.append(nm)
            servers[server_of(nm)] += 1
            if NS_SEP.search(nm):
                sep_names += 1
            w = words(c["desc"])
            if w:
                descs += 1
                if any(v in c["desc"].lower() for v in AFFORDANCE):
                    descs_with_verb += 1
            if c["params"]:
                with_params += 1
            if i not in gold and w and any(len(w & g) / max(1, len(w)) >= 0.5 for g in gw):
                has_decoy = True
        if has_decoy:
            decoy_queries += 1
        qw = words(r.question)
        if len(gold) >= 2:
            multi_gold_rows += 1
            ordered = sorted(gold)
            for x, y in combinations(ordered, 2):        # every pair, not just neighbours: a 3-gold query has 3
                pairs.add(tuple(sorted((cat[x]["name"], cat[y]["name"]))))
        gold_rank = min(int(r.bm25_best_rank or 10_000), 10_000)
        if gold_rank > 1 and any(not (words(c["desc"]) & qw) for k, c in enumerate(cat) if k < gold_rank):
            no_overlap_above_gold += 1
    cand_total = len(names)
    per_cfg = df["cfg"].value_counts().to_dict()
    return {"corpus": "P001 routing release, dev split only", "rows": n, "by_config": {str(k): int(v) for k, v in
                                                                                       per_cfg.items()},
            "min_config_rows": int(min(per_cfg.values())) if per_cfg else 0,
            "catalogue_parse_share": round(parsed / max(1, n), 4),
            "shipped_parser_entries_recovered": sum(len(x or []) for x in W.catalog_entries(df.head(500))),
            "gold_index_recoverable_share": round(gold_ok / max(1, n), 4),
            "median_candidates": float(df["n_candidates"].median()), "candidates": cand_total,
            "mean_candidates": round(float(df["n_candidates"].mean()), 2),
            "names_with_separator_share": round(sep_names / max(1, cand_total), 4),
            "distinct_tools": len(set(names)), "distinct_servers": len(servers),
            "server_hhi": round(sum((v / max(1, cand_total)) ** 2 for v in servers.values()), 4),
            "top_servers": {str(k): int(v) for k, v in servers.most_common(12)},
            "descriptions_with_affordance_verb_share": round(descs_with_verb / max(1, descs), 4),
            "candidates_with_parameters_share": round(with_params / max(1, cand_total), 4),
            "queries_with_near_synonym_decoy": int(decoy_queries),
            "queries_needing_2plus_gold": int(multi_gold_rows),
            "distinct_gold_pairs": int(len(pairs)),
            "queries_with_irrelevant_candidate_above_gold": int(no_overlap_above_gold),
            "fail_at_1_share": round(float(df["fail_at_1"].mean()), 4) if "fail_at_1" in df else None,
            "ranker_columns_present_share": round(float(df["bm25_best_rank"].notna().mean()), 4),
            "n_gold_distribution": {str(int(k)): int(v) for k, v in
                                    df["n_gold"].value_counts().sort_index().head(8).items()}}


def apply_gates(m: dict) -> dict:
    checks = {"G1_catalogues_parseable": m["catalogue_parse_share"],
              "G2_gold_indices_recoverable": m["gold_index_recoverable_share"],
              "G3_namespace_separators_present": m["names_with_separator_share"],
              "G4_near_synonym_queries": m["queries_with_near_synonym_decoy"],
              "G5_affordance_language_present": m["descriptions_with_affordance_verb_share"],
              "G6_multi_gold_queries": m["queries_needing_2plus_gold"],
              "G7_distinct_gold_pairs": m["distinct_gold_pairs"],
              "G8_contaminated_rankings": m["queries_with_irrelevant_candidate_above_gold"] / max(1, m["rows"]),
              "G9_distinct_servers": m["distinct_servers"],
              "G10_cluster_count_per_config": m["min_config_rows"],
              "G11_ranker_columns_present": m["ranker_columns_present_share"],
              "G12_parameter_lists_present": m["candidates_with_parameters_share"]}
    fired, scopes = [], {}
    for g, v in checks.items():
        th = GATES[g]["threshold"]
        GATES[g]["measured"] = round(float(v), 4) if v is not None else None
        GATES[g]["fires"] = bool((v is None) or (float(v) < float(th)))
        if not GATES[g].get("blocks"):
            raise SystemExit(f"ABORT: gate {g} names no topic, so a fired gate would stop nothing while the record "
                             f"claims a scope")
        if GATES[g]["fires"]:
            fired.append(g)
        scopes[g] = {"scope": GATES[g]["scope"], "blocks": GATES[g]["blocks"], "measured": GATES[g]["measured"],
                     "fires": GATES[g]["fires"]}
    stopped = []
    for g in fired:
        if GATES[g]["scope"] == "design":
            stopped += [x for x in GATES[g]["blocks"] if x not in stopped]
    return {"blocked_gates": fired, "blocked_whole_design": stopped,
            "claim_limited": {g: GATES[g]["scope"] for g in fired if GATES[g]["scope"] != "design"},
            "gate_scopes": scopes, "gate_rules": {k: GATES[k]["rule"] for k in GATES},
            "note": "a fired gate stops exactly what its frozen sentence scopes, and the measurement it fired on is "
                    "printed with it"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=0, help="cap the dev rows read; 0 reads every dev row")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    if a.selftest:
        return selftest()
    t0 = time.time()
    selftest()
    df = W.load_routing(cols=None)
    audit = df.attrs.get("load_routing_audit") or {}
    if a.rows:
        df = df.sample(min(a.rows, len(df)), random_state=SEED).reset_index(drop=True)
    m = measure(df)
    verdict = apply_gates(m)
    out = {"exp_id": EXP, "measured": m,
           "gates": {g: {"measured": s["measured"], "fires": s["fires"], "scope": s["scope"], "blocks": s["blocks"]}
                     for g, s in verdict["gate_scopes"].items()},
           "gate_rules": verdict["gate_rules"],
           "verdict": {k: verdict[k] for k in ("blocked_gates", "blocked_whole_design", "claim_limited")},
           "split_audit": {k: {"rows_total": v["rows_total"], "rows_kept": v["rows_kept"],
                               "splits": v["split_counts"]} for k, v in audit.items()},
           "seed": SEED, "rows_requested": a.rows or "all dev rows", "started_at": W.now(),
           "invocation": " ".join([sys.executable] + sys.argv),
           "wallclock_sec": round(time.time() - t0, 1)}
    dest = W.write_raw(EXP, "wave7_premise_census", out)
    print(json.dumps({"measured": {k: v for k, v in m.items() if k not in ("top_servers",)},
                      "gates": {k: (v["measured"], v["fires"]) for k, v in verdict["gate_scopes"].items()},
                      "stopped": verdict["blocked_whole_design"],
                      "claim_limited": verdict["claim_limited"]}, indent=1, ensure_ascii=False, default=str)[:2400])
    print(f"{EXP}: wrote {dest.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
