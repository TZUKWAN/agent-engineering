"""EXP-0182: wave 7's frames - one row per query, one per server, one per gold tool pair.

The query frame is the wave's measurement surface: for each dev instruction, the candidate catalogue reduced to the
quantities the six freezes name (decoys, affordance language, namespace structure, contamination) beside the frozen
ranker's own columns (gold rank, score margin, fail-at-1). Nothing in this file estimates an association; it turns a
catalogue into columns so that a coefficient in `exp_wave7_designs.py` reads the same definition as the sentence that
promised it.

Two further frames exist because two hypotheses are not about a query at all. `wave7_server_pairs` carries, for each
namespace prefix, the mean description overlap among its own tools and among tools of it and another server - the
within-versus-across comparison T165's H1 bootstraps over servers. `wave7_gold_pairs` carries, for each unordered
pair of tools some query needed together, how often that pair recurs and how similar its descriptions are beside a
seeded random partner - the comparison T169's H2 bootstraps over pairs. A third, `wave7_tool_roster`, is the name
population itself, because T165's H2 and H3 are statements about how many tools each server publishes and about how
many local names more than one server publishes, which no per-query row can answer. A fourth, `wave7_overlap_pairs`,
re-draws the same within-versus-across comparison at the tool's own scale (20 partners of each kind around each of
the 4,161 named tools), because 184 usable servers are below the row floor every other wave's regression had to clear
and a specialisation claim is better carried by two readings than by one.

The reader for the release's compact catalogue schema is the one the census validated (EXP-0181 measured 1.0 coverage
for it and 0 entries recovered by P001's shipped parser on these rows), and the self-test proves every rule on a
hand-built catalogue before a row of the release is read.

    python 02_shared_code/package_factory/exp_wave7_features.py
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import itertools
import json
import pathlib
import random
import re
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import numpy as np                                                # noqa: E402
import pandas as pd                                               # noqa: E402
import wave_lib as W                                              # noqa: E402
import probe_wave7_premises as P7                                 # noqa: E402  one reader, one rule set

EXP = "EXP-0182"
TD7 = __import__("topic_designs_wave7")
SEED = TD7.SEED
PAIR_DRAWS = 40                        # sampled description pairs per server and per tool pair, fixed before reading
TOOL_PAIR_DRAWS = 20                   # same-server and different-server partners sampled around each tool
DECOY_THRESHOLD = 0.5                  # the share of a candidate's own words that a gold description must contain


def jac(a: set, b: set) -> float:
    return float(len(a & b) / len(a | b)) if (a or b) else float("nan")


def containment(a: set, b: set) -> float:
    """Share of `a`'s words that appear in `b` - the asymmetric form the decoy rule is stated in."""
    return float(len(a & b) / len(a)) if a else float("nan")


def num(v, default=float("nan")) -> float:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return default
    return f if np.isfinite(f) else default


def gold_of(row_cat: list, gold_idx) -> list:
    return sorted({int(i) for i in (gold_idx or []) if str(i).lstrip("-").isdigit()} & set(range(len(row_cat))))


def query_row(r) -> dict:
    """One dev row -> the query's measured columns, or {} when the catalogue or its gold list cannot be read."""
    cat = P7.entries(r.catalog_json)
    gold = gold_of(cat, r.gold_idx)
    if not cat or not gold:
        return {}
    qw = P7.words(r.question)
    gw = [P7.words(cat[i]["desc"]) for i in gold]
    gset = set(gold)
    # "shares >= 0.5 of its words with A gold candidate" - EXP-0181's rule is an any(), so the best-matching gold wins.
    sims = [max((containment(P7.words(c["desc"]), g) for g in gw), default=float("nan"))
            for k, c in enumerate(cat) if k not in gset]
    sims = [s for s in sims if s == s]
    best = max(sims) if sims else float("nan")
    rng = random.Random(f"{SEED}|{r.uuid}")
    non_gold = [k for k in range(len(cat)) if k not in gset]
    ctrl = float("nan")
    if non_gold and gw:
        k = rng.choice(non_gold)
        ctrl = max((containment(P7.words(cat[k]["desc"]), g) for g in gw), default=float("nan"))
    names = [c["name"] for c in cat]
    servers = [P7.server_of(n) for n in names]
    desc = " ".join(cat[i]["desc"] for i in gold)
    dw = P7.words(desc)
    gr = num(r.bm25_best_rank)
    rank = int(gr) if gr == gr and gr >= 1 else 10_000            # EXP-0181's own fallback: a rank we cannot read
    irr_above = sum(1 for k, c in enumerate(cat)                    # is not a gold row sitting anywhere above it
                    if rank > 1 and k < rank and not (P7.words(c["desc"]) & qw))
    f = num(getattr(r, "fail_at_1", float("nan")))                 # the release's outcome column wins when present
    params = [p for i in gold for p in cat[i]["params"]]
    return {"query_id": f"{r.cfg}|{r.uuid}", "cfg": str(r.cfg), "uuid": str(r.uuid),
            "n_candidates": int(len(cat)), "n_gold": int(len(gold)), "gold_idx": "|".join(map(str, gold)),
            "question_words": int(len(qw)), "desc_words": int(len(dw)),
            "bm25_best_rank": rank, "fail_at_1": int(f) if f == f else int(rank != 1),
            "bm25_margin": num(r.bm25_margin), "bm25_top1_score": num(r.bm25_top1_score),
            "max_similarity": num(best), "control_similarity": num(ctrl),
            "decoy_present": int(best == best and best >= DECOY_THRESHOLD),
            "decoy_count": int(sum(1 for s in sims if s >= DECOY_THRESHOLD)),
            "affordance_verbs": int(len(set(P7.AFFORD_RX.findall(desc.lower())))),
            "affordance_density": round(float(len(set(P7.AFFORD_RX.findall(desc.lower()))) / max(1, len(dw))), 4),
            "gold_has_params": int(bool(params)), "gold_param_words": int(len(set().union(*[set(P7.words(p))
                                                                                           for p in params]) or set())),
            "namespaced_share": round(float(sum(1 for n in names if P7.NS_SEP.search(n)) / len(names)), 4),
            "distinct_servers": int(len(set(servers))),
            "server_concentration": round(float(1 - len(set(servers)) / len(names)), 4),
            "irrelevant_share": round(float(sum(1 for c in cat if not (P7.words(c["desc"]) & qw)) / len(names)), 4),
            "irrelevant_above_gold": int(irr_above), "contaminated": int(irr_above > 0),
            "gold_names": "|".join(cat[i]["name"] for i in gold),
            "gold_pairs": [frozenset((cat[a]["name"], cat[b]["name"])) for a, b in itertools.combinations(gold, 2)],
            }


def server_frame(rows: list) -> pd.DataFrame:
    """Within-server versus across-server description overlap, one row per server with >= 3 tools.

    The word sets live in a dict keyed by tool name rather than a set of tuples: `frozenset.__lt__` is the subset
    order, which is only partial, so sorting a set of (name, words) tuples compares word sets through an
    inconsistent comparator and the draw order changes with the process hash seed. Sorted dict keys give a total
    order, so the same seed always draws the same pairs.
    """
    rng = random.Random(SEED)
    by_server = collections.defaultdict(dict)
    for r in rows:
        for nm, d in zip(r["_names"], r["_descs"]):
            w = P7.words(d)
            if w:
                by_server[P7.server_of(nm)].setdefault(nm, frozenset(w))
    cats = {s: sorted(v.items()) for s, v in by_server.items()}
    out = []
    for s in sorted(cats):
        items = cats[s]
        if len(items) < 3:
            continue
        ws = [w for _, w in items]
        within = []
        for _ in range(PAIR_DRAWS):
            i, j = rng.randrange(len(ws)), rng.randrange(len(ws))
            if i != j:
                within.append(jac(set(ws[i]), set(ws[j])))
        other = [w for o in sorted(cats) if o != s for _, w in cats[o]]
        across = [jac(set(rng.choice(ws)), set(rng.choice(other))) for _ in range(PAIR_DRAWS)] if other else []
        within = [x for x in within if x == x]
        across = [x for x in across if x == x]
        if not within or not across:
            continue
        out.append({"server": s, "tools": len(items), "within_overlap": round(float(np.mean(within)), 4),
                    "across_overlap": round(float(np.mean(across)), 4), "diff":
                        round(float(np.mean(within) - np.mean(across)), 4), "within_draws": len(within),
                    "across_draws": len(across)})
    return pd.DataFrame(out)


def pair_frame(rows: list) -> pd.DataFrame:
    """One row per unordered gold tool pair: how often it is needed together and how similar its descriptions are."""
    freq = collections.Counter()
    words_by_name = {}
    for r in rows:
        for p in r["gold_pairs"]:
            freq[p] += 1
        for nm, d in zip(r["_names"], r["_descs"]):
            w = P7.words(d)
            if w:
                words_by_name.setdefault(nm, w)
    names = sorted(words_by_name)
    out, seen, skipped = [], set(), 0
    for p, n in freq.most_common():
        t = tuple(sorted(p))
        if len(t) < 2:
            continue                                             # the same tool listed twice is not a dependency
        if t in seen:
            continue
        seen.add(t)
        a, b = t
        if a not in words_by_name or b not in words_by_name:
            skipped += 1                                          # the pair exists in the release but carries no
            continue                                              # description to compare, so no overlap is reportable
        rnd = random.Random(f"{SEED}|{a}|{b}").choice(names) if names else None
        out.append({"pair": f"{a} + {b}", "tool_a": a, "tool_b": b, "frequency": int(n),
                    "overlap": round(float(jac(words_by_name[a], words_by_name[b])), 4),
                    "random_tool": rnd, "random_overlap": (round(float(jac(words_by_name[a], words_by_name[rnd])), 4)
                                                           if rnd and rnd != a and rnd in words_by_name
                                                           else float("nan"))})
    df = pd.DataFrame(out)
    df.attrs["distinct_pairs_in_release"] = len(seen)
    df.attrs["pairs_without_a_description"] = skipped
    return df


def roster_frame(rows: list) -> pd.DataFrame:
    """One row per distinct candidate name in the release: its server, its local name and how often it was offered.

    T165's H3 asks how many *local* names are published by more than one server, which is a question about the whole
    name population rather than about a query, and the answer has to come from the same reader the other frames use.
    """
    seen = {}
    for r in rows:
        for nm, d, prm in zip(r["_names"], r["_descs"], r["_params"]):
            e = seen.get(nm)
            if e is None:
                m = re.search(r"[._]|::", str(nm).lower())
                seen[nm] = {"name": str(nm), "server": P7.server_of(nm),
                            "local_name": str(nm)[m.end():].lower() if m else str(nm).lower(),
                            "desc_words": len(P7.words(d)), "n_params": int(prm), "times_offered": 0,
                            "desc_sha": hashlib.sha1(" ".join(sorted(P7.words(d))).encode("utf-8")).hexdigest()[:16],
                            "queries": set()}
            seen[nm]["times_offered"] += 1
            seen[nm]["queries"].add(r["query_id"])
    out = []
    for nm in sorted(seen):
        e = seen[nm]
        out.append({k: (len(v) if k == "queries" else v) for k, v in e.items()})
    return pd.DataFrame(out)


def overlap_frame(rows: list) -> pd.DataFrame:
    """One row per sampled description pair around a tool: a same-server partner and a different-server partner.

    T165's H1 is a within-versus-across difference and the server frame already carries it at the server's own scale.
    This frame is the same comparison at the scale where a regression is possible - 4,161 tools, clustered on the
    tool each pair was drawn around - so the battery's E-steps have an estimand to run on rather than a 184-row frame
    the programme's own 200-row guard refuses.
    """
    tools = {}
    for r in rows:
        for nm, d in zip(r["_names"], r["_descs"]):
            if nm not in tools:
                tools[nm] = (P7.server_of(nm), P7.words(d))
    usable = {n: (s, w) for n, (s, w) in tools.items() if w}
    by_server = collections.defaultdict(list)
    for n in sorted(usable):
        by_server[usable[n][0]].append(n)
    allnames = sorted(usable)
    out = []
    for t in allnames:
        s, w = usable[t]
        rng = random.Random(f"{SEED}|{t}")
        same = [x for x in by_server[s] if x != t]
        partners = [(p, 1) for p in (rng.choices(same, k=TOOL_PAIR_DRAWS) if same else [])]
        for _ in range(TOOL_PAIR_DRAWS):
            for _try in range(50):
                p = rng.choice(allnames)
                if usable[p][0] != s:
                    partners.append((p, 0))
                    break
        for p, is_same in partners:
            ps, pw = usable[p]
            out.append({"tool": t, "server": s, "tool_words": len(w), "partner": p, "partner_server": ps,
                        "partner_words": len(pw), "same_server": int(is_same),
                        "jaccard": round(float(jac(set(w), set(pw))), 4)})
    return pd.DataFrame(out)


def census() -> dict:
    """EXP-0181's full-release numbers. The frame and the census read the same rows with the same rules, so if the two
    stop agreeing on the three quantities both compute, one of them has been changed without the other - and a
    coefficient in the designs would then be reported against a definition the freeze never cited."""
    for f in sorted(W.RAWRES.glob("EXP0181_wave7_premise_census_*.json"), reverse=True):
        a = json.loads(f.read_text(encoding="utf-8"))
        if "--rows" not in str(a.get("invocation", "")):
            return {"file": f.name, "rows": int(a["measured"]["rows"]), "measured": a["measured"]}
    raise SystemExit("ABORT: no full-release EXP-0181 census artefact exists, so the frame has nothing to cross-check "
                     "its definitions against")


def selftest() -> int:
    # Deliberate ordering: an irrelevant candidate sits at index 0, the gold at index 1, the frozen ranker put the
    # gold 2nd, so "a candidate above the gold with nothing in common with the question" is true by construction.
    cat = json.dumps([{"n": "jira", "d": "List issues in a project board", "p": ["project"]},
                      {"n": "fs.read_file", "d": "Read the contents of a file from disk", "p": ["path"]},
                      {"n": "fs.read_text", "d": "Read the contents of a text file", "p": ["path"]},
                      {"n": "weather_now", "d": "Fetch the current forecast for a city", "p": ["city"]}])

    class R:
        catalog_json, gold_idx, n_candidates, n_gold = cat, [1], 4, 1
        question, uuid, cfg = "read a file from disk please", "u1", "OSS"
        bm25_best_rank, bm25_margin, bm25_top1_score, fail_at_1 = 2, 0.5, 7.0, 1

    row = query_row(R())
    assert row and row["n_candidates"] == 4 and row["fail_at_1"] == 1
    assert row["decoy_present"] == 1 and row["decoy_count"] == 1, row            # fs.read_text is the look-alike
    assert row["max_similarity"] == 0.75, row["max_similarity"]                  # 3 of the 4 non-stop words shared
    # EXP-0181's frozen separator is dot, underscore or ::, so weather_now counts and a bare name does not: 3 of 4.
    assert row["namespaced_share"] == 0.75, row["namespaced_share"]
    assert row["distinct_servers"] == 3 and row["gold_has_params"] == 1
    assert row["irrelevant_above_gold"] == 1 and row["contaminated"] == 1, row   # jira sits above the gold one
    assert 0.0 < row["max_similarity"] <= 1.0 and row["affordance_density"] > 0
    assert len(row["gold_pairs"]) == 0 and row["n_gold"] == 1
    aux = [dict(query_id="q1", _names=["fs.read_file", "fs.read_text", "fs.write_file", "jira"],
                _descs=["Read the contents of a file from disk", "Read the contents of a text file",
                        "Write the contents of a file to disk", "List issues in a project board"],
                _params=[1, 1, 1, 1],
                gold_pairs=[frozenset({"fs.read_file", "fs.read_text"})]),
           dict(query_id="q2", _names=["fs.read_file", "fs.read_text"],
                _descs=["Read the contents of a file from disk", "Read the contents of a text file"],
                _params=[1, 1], gold_pairs=[frozenset({"fs.read_file", "fs.read_text"})])]
    rs, sv, pr = roster_frame(aux), server_frame(aux), pair_frame(aux)
    op = overlap_frame(aux)
    assert set(op["same_server"]) == {0, 1} and (op["same_server"] == 1).sum() > 0
    assert all((r.partner_server == r.server) == bool(r.same_server) for r in op.itertuples())
    assert float(op[op.same_server == 1]["jaccard"].mean()) > float(op[op.same_server == 0]["jaccard"].mean())
    assert len(rs) == 4 and int(rs["times_offered"].sum()) == 6, rs                # 6 candidate slots, 4 distinct names
    assert rs.set_index("name").loc["fs.read_file", "local_name"] == "read_file"
    assert len(set(rs["desc_sha"])) == 4                                       # four different sets of words
    sig_of = lambda s: hashlib.sha1(" ".join(sorted(P7.words(s))).encode("utf-8")).hexdigest()[:16]
    assert sig_of("disk file contents read the of from a") == sig_of("Read the contents of a file from disk")
    assert int((rs.groupby("local_name")["server"].nunique() >= 2).sum()) == 0     # every name here has one server
    assert len(sv) == 1 and sv["tools"].iloc[0] == 3 and np.isfinite(sv["diff"].iloc[0]), sv
    assert len(pr) == 1 and pr["frequency"].iloc[0] == 2 and pr["overlap"].iloc[0] > 0.4, pr
    print("SELFTEST OK: decoy, namespace, parameter, contamination and rank columns all land on a built catalogue")
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
    audit = {k: {"rows_total": v["rows_total"], "rows_kept": v["rows_kept"], "splits": v["split_counts"]}
             for k, v in (df.attrs.get("load_routing_audit") or {}).items()}
    rows, dropped = [], 0
    aff_tot = aff_loose = aff_bound = 0                            # W7-D05: the two readings of one frozen verb list
    for i, r in enumerate(df.itertuples(index=False)):
        q = query_row(r)
        if not q:
            dropped += 1
            continue
        cat = P7.entries(r.catalog_json)
        q["_names"] = [c["name"] for c in cat]                   # used only to build the three auxiliary frames
        q["_descs"] = [c["desc"] for c in cat]
        q["_params"] = [len(c["params"]) for c in cat]
        for d in q["_descs"]:
            if P7.words(d):
                aff_tot += 1
                aff_loose += int(any(v in d.lower() for v in P7.AFFORDANCE))
                aff_bound += int(bool(P7.AFFORD_RX.search(d.lower())))
        rows.append(q)
        if (i + 1) % 8000 == 0:
            print(f"  frame: {i + 1}/{len(df)} rows -> {len(rows)} queries measured", flush=True)
    if not rows:
        raise SystemExit("ABORT: no query yielded both a readable catalogue and a gold index inside it, so the wave "
                         "has no subject - and EXP-0181 already measured that this is not what the release looks like")
    srv, pairs = server_frame(rows), pair_frame(rows)
    roster = roster_frame(rows)
    opairs = overlap_frame(rows)
    F = pd.DataFrame([{k: v for k, v in r.items() if not k.startswith("_")} for r in rows])
    F["log_candidates"] = np.log1p(F["n_candidates"].astype(float))
    F["question_words_log"] = np.log1p(F["question_words"].astype(float))
    F["margin_z"] = (F["bm25_margin"] - F["bm25_margin"].mean()) / (F["bm25_margin"].std(ddof=0) or 1.0)
    F["afford_density_z"] = (F["affordance_density"] - F["affordance_density"].mean()) / \
                            (F["affordance_density"].std(ddof=0) or 1.0)
    F["cand_quartile"] = pd.qcut(F["n_candidates"].rank(method="first"), 4,
                                 labels=["q1_smallest", "q2", "q3", "q4_largest"]).astype(str)
    F["server_quartile"] = pd.qcut(F["distinct_servers"].rank(method="first"), 4,
                                   labels=["s1_fewest", "s2", "s3", "s4_most"]).astype(str)
    fmax = pairs.set_index("pair")["frequency"] if len(pairs) else pd.Series(dtype=float)
    pf, tp = [], []
    for pls in F["gold_pairs"]:
        best, key = 0.0, ""
        for p in (pls or []):
            t = tuple(sorted(p))
            if len(t) < 2:
                continue
            k = f"{t[0]} + {t[1]}"
            v = float(fmax.get(k, 0.0))
            if v > best:
                best, key = v, k                                         # the query's strongest co-needed pair
        pf.append(best)
        tp.append(key)
    F["max_pair_frequency"] = pf
    F["top_pair"] = tp
    F["pair_frequent"] = (F["max_pair_frequency"] >= 10).astype(int)
    F["multi_gold"] = (F["n_gold"] >= 2).astype(int)
    cen = census()
    cm = cen["measured"]
    x = {"fail_at_1_share": (round(float(F["fail_at_1"].mean()), 4), float(cm["fail_at_1_share"])),
         "decoy_present_share": (round(float(F["decoy_present"].mean()), 4),
                                 round(float(cm["queries_with_near_synonym_decoy"]) / cen["rows"], 4)),
         "contaminated_share": (round(float(F["contaminated"].mean()), 4),
                                round(float(cm["queries_with_irrelevant_candidate_above_gold"]) / cen["rows"], 4)),
         "multi_gold_queries": (float(F["multi_gold"].sum()), float(cm["queries_needing_2plus_gold"])),
         "distinct_tool_names": (float(len(roster)), float(cm["distinct_tools"])),
         "distinct_servers_in_roster": (float(roster["server"].nunique()), float(cm["distinct_servers"])),
         "distinct_gold_pairs": (float(pairs.attrs["distinct_pairs_in_release"]), float(cm["distinct_gold_pairs"]))}
    off = {k: v for k, v in x.items() if abs(v[0] - v[1]) > max(0.005, 0.002 * abs(v[1]))}
    if off:
        raise SystemExit(f"ABORT: the frame and EXP-0181 ({cen['file']}) disagree on {off} as (frame, census) - the "
                         f"two are one reader with one rule set, so a definition changed in only one of them")
    dest_q = W.OUT / "EXP0182_wave7_candidate_features.csv.gz"
    dest_s = W.OUT / "EXP0182_wave7_server_pairs.csv.gz"
    dest_p = W.OUT / "EXP0182_wave7_gold_pairs.csv.gz"
    dest_r = W.OUT / "EXP0182_wave7_tool_roster.csv.gz"
    dest_o = W.OUT / "EXP0182_wave7_overlap_pairs.csv.gz"
    F.drop(columns=["gold_pairs"]).to_csv(dest_q, compression="gzip", index=False, encoding="utf-8")
    srv.to_csv(dest_s, compression="gzip", index=False, encoding="utf-8")
    pairs.to_csv(dest_p, compression="gzip", index=False, encoding="utf-8")
    roster.to_csv(dest_r, compression="gzip", index=False, encoding="utf-8")
    opairs.to_csv(dest_o, compression="gzip", index=False, encoding="utf-8")
    slots = float(roster["times_offered"].sum())
    srv_share = roster.groupby("server")["times_offered"].sum().sort_index().sort_values(ascending=False,
                                                                                         kind="mergesort")
    # sort_index() first and a stable sort second, so a tie in slot counts cannot decide which twelve servers are
    # "the largest" differently between two runs over the same bytes
    reused = (roster.groupby("local_name")["server"].nunique())
    sig = roster.groupby("desc_sha")
    sig_tools, sig_servers = sig.size(), sig["server"].nunique()
    art = {"exp_id": EXP, "corpus": "P001 routing release, dev split only", "seed": SEED, "split_audit": audit,
           "rows_offered": int(len(df)), "queries_measured": int(len(F)), "queries_dropped": int(dropped),
           "drop_reason": "no readable catalogue or no gold index inside the catalogue; both were counted by "
                          "EXP-0181, which measured 1.0 coverage of each, so this count is expected to be 0",
           "by_config": {str(k): int(v) for k, v in F["cfg"].value_counts().items()},
           "census_artefact": cen["file"],
           "census_cross_check": {k: [v[0], v[1]] for k, v in x.items()},
           "cluster_unit": TD7.COMMON["sample"]["cluster_unit"],
           "median_candidates": float(F["n_candidates"].median()),
           "fail_at_1_share": round(float(F["fail_at_1"].mean()), 4),
           "decoy_present_share": round(float(F["decoy_present"].mean()), 4),
           "decoy_count_mean": round(float(F["decoy_count"].mean()), 3),
           "contaminated_share": round(float(F["contaminated"].mean()), 4),
           "namespaced_share_mean": round(float(F["namespaced_share"].mean()), 4),
           "affordance_density_mean": round(float(F["affordance_density"].mean()), 4),
           "affordance_desc_share_substring_rule": round(aff_loose / max(1, aff_tot), 4),
           "affordance_desc_share_boundary_rule": round(aff_bound / max(1, aff_tot), 4),
           "affordance_descriptions": int(aff_tot),
           "affordance_rule_note": "EXP-0181's G5 was measured with the substring test, which is what "
                                   f"affordance_desc_share_substring_rule reproduces here; the per-query column is "
                                   f"counted with a word boundary, which is {round(aff_bound/max(1,aff_tot),4)}, "
                                   "because a substring counts 'get' inside 'target' and a leading space misses a "
                                   "verb at position 0 (W7-D05)",
           "gold_has_params_share": round(float(F["gold_has_params"].mean()), 4),
           "multi_gold_queries": int(F["multi_gold"].sum()),
           "distinct_gold_pairs": int(pairs.attrs["distinct_pairs_in_release"]),
           "pairs_with_an_overlap_computable": int(len(pairs)),
           "pairs_dropped_for_a_missing_description": int(pairs.attrs["pairs_without_a_description"]),
           "pairs_with_frequency_10plus":
               int((pairs["frequency"] >= 10).sum()) if len(pairs) else 0,
           "queries_with_a_usable_top_pair": int((F["top_pair"] != "").sum()),
           "servers_in_pair_frame": int(len(srv)),
           "roster_tools": int(len(roster)), "roster_slots": int(slots),
           "roster_servers": int(roster["server"].nunique()),
           "roster_server_hhi": round(float(((srv_share / slots) ** 2).sum()), 4),
           "roster_top12_server_share": round(float(srv_share.head(12).sum() / slots), 4),
           "roster_local_names_under_2plus_servers": int((reused >= 2).sum()),
           "overlap_pair_rows": int(len(opairs)), "overlap_pair_tools": int(opairs["tool"].nunique()),
           "overlap_same_server_mean": round(float(opairs[opairs["same_server"] == 1]["jaccard"].mean()), 4),
           "overlap_other_server_mean": round(float(opairs[opairs["same_server"] == 0]["jaccard"].mean()), 4),
           "description_signatures": int(sig.ngroups),
           "signatures_carried_by_2plus_tools": int((sig_tools >= 2).sum()),
           "signatures_spanning_2plus_servers": int((sig_servers >= 2).sum()),
           "largest_description_group": int(sig_tools.max()),
           "within_minus_across_mean": round(float(srv["diff"].mean()), 4) if len(srv) else None,
           "frames": [dest_q.name, dest_s.name, dest_p.name, dest_r.name, dest_o.name], "started_at": W.now(),
           "wallclock_sec": round(time.time() - t0, 1), "invocation": " ".join([sys.executable] + sys.argv),
           "run_cost": W.run_cost_row(EXP, t0, int(len(F)), int(F.shape[1]), "wave-7 frame")}
    dest = W.write_raw(EXP, "wave7_candidate_matrix", art)
    print(json.dumps(art, indent=1, ensure_ascii=False, default=str)[:1500])
    print(f"\n{EXP}: wrote {dest_q.name} ({len(F)} queries), {dest_s.name} ({len(srv)} servers), "
          f"{dest_p.name} ({len(pairs)} pairs), {dest_r.name} ({len(roster)} tools), "
          f"{dest_o.name} ({len(opairs)} drawn pairs) and {dest.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
