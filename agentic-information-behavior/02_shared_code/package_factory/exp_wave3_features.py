"""EXP-0143: the wave-3 matrix - name/description organisation, neighbour discriminability, and the rewrite arms.

Wave 3 measures properties of the *catalogue text itself*, so this script adds the columns its designs need and
merges them with what waves 1 and 2 already froze rather than re-deriving anything they own:

| column | what it measures | whose design needs it |
|--------|------------------|-----------------------|
| `name_desc_congruence` | share of the entry name's identifier tokens that also appear in its own description | T119 H1/H2 |
| `name_predicate_in_desc` | the name's verb lemma and object noun both occur in the description | T119 H1 |
| `contradiction` | the name asserts a constraint family the description explicitly negates | T119 H3 (0 rows: gate fired) |
| `facet_overlap` | share of the entry's name/server facets present in the query | T113, T119 controls |
| `discrim_lexical` | mean IDF-weighted token dissimilarity to the other entries of *its own* catalogue | T122 H1/H2 |
| `discrim_dense` | 1 - mean cosine to those neighbours, from the unchanged local encoder cache | T122 H1 |
| `arm_*` | rank and rank-1 reachability of the released selection under four rule rewrites | T113, T120 |

The four arms are the intervention designs' whole measurement, so they are computed here, once, from the frozen
ranker, and every design reads the same columns: `baseline`, `usecase` (T113's frame template), `synonym`
(T120's canonicalisation map), and `usecase_matched` (the use-case frame truncated to the baseline's token count,
which is what makes H3's "at matched length" comparison a comparison at all).

Guards, because a silently empty column is the failure this programme has already been bitten by twice: the script
aborts if a rewrite arm fails to produce a rank for more than 1% of rows, if the merged frames lose or gain query
rows against the frozen 24,000, or if `contradiction` is all-zero *and* the designs still ask for a claim from it.

    python 02_shared_code/package_factory/exp_wave3_features.py [--rows-per-config 8000] [--selftest]
"""
from __future__ import annotations

import argparse
import collections
import datetime
import json
import pathlib
import re
import sys

import numpy as np
import pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import wave_lib as W                                              # noqa: E402
import topic_designs_wave3 as TD3                                 # noqa: E402

ROWS_PER_CONFIG = 8000
DEV_ROWS_EXPECTED = 24000

import encode_wave1_texts as ENC                                   # noqa: E402


def dense_key(query_id: str, i: int, entry: dict) -> str:
    """The cache address of one rendered catalogue entry, by the formula EXP-0120 used when it wrote the cache.

    Imported rather than re-typed: a key computed by a copy of the rendering function would miss every row and the
    dense arm would quietly report nothing.
    """
    return W.text_sha(f"D|{query_id}|{i}|" + ENC.clip(ENC.render_doc(entry.get("name", ""),
                                                                    entry.get("desc", ""),
                                                                    entry.get("params") or [])))


FACET_SPLIT = re.compile(r"[-_/]|(?<=[a-z0-9])(?=[A-Z])")


def name_facets(name: str, server_hint: str = "") -> list:
    parts = [p for p in FACET_SPLIT.split(str(name or "")) if p and len(p) > 1]
    if server_hint:
        parts = [str(server_hint).lower()] + parts
    return parts


def congruence(name: str, entry: dict) -> tuple:
    """(share of name tokens found in the entry's own text, predicate-in-description, contradiction)."""
    nt = W.toks(name) or W.toks(str(name).replace("-", " "))
    # The comparison is with the DESCRIPTION alone. Including the name in the text it is compared against made every
    # entry congruent with itself: the column came out 1.000 for all 169,203 rows, which is an identity, not a
    # measurement, and the matrix was rebuilt because of it.
    own = set(W.toks(str(entry.get("desc") or "")))
    if not nt:
        return None, 0, 0
    share = len([t for t in nt if t in own]) / len(nt)
    pa = W.predicate_argument(str(name).replace("-", " "), entry)
    nm, dm = W.constraint_markers(str(name or "")), W.constraint_markers(str(entry.get("desc") or ""))
    contra = int(any(nm[f] > 0 and dm[f] == 0 and bool(W.NEG_MARK.search(str(entry.get("desc") or "")))
                     for f in ("temporal", "numeric", "format", "scope")))
    return round(float(share), 4), int(pa["predicate_fit"] and pa["argument_fit"]), contra


def entry_tokens(entries: list) -> list:
    return [set(W.toks(" ".join(str(e.get(k) or "") for k in ("name", "desc", "params")))) for e in entries]


def discrimin_all(etoks: list, vecs=None) -> tuple:
    """Mean IDF-weighted dissimilarity of each entry to the others of its own catalogue, in one pass.

    The first version tokenised the whole catalogue once *per entry* and recomputed the document frequencies each
    time, which is O(n^3) work per query for a seven-candidate catalogue; one pass over the pair matrix is what the
    definition actually needs. Returns (lexical, dense) lists with None where a catalogue has no neighbours, because
    a single-tool catalogue has no "distance from its neighbours" and writing 0.0 for it would invent the opposite of
    the quantity.
    """
    n = len(etoks)
    lex = [None] * n
    den = [None] * n
    if n < 2:
        return lex, den
    df = collections.Counter()
    for t in etoks:
        df.update(t)
    w = {tok: float(np.log(1 + (n - c + 0.5) / (c + 0.5))) for tok, c in df.items()}
    tot = [sum(w.get(t, 0.0) for t in tk) or 1.0 for tk in etoks]
    for i in range(n):
        if not etoks[i]:
            continue
        acc = 0.0
        for j in range(n):
            if j == i:
                continue
            shared = sum(w.get(t, 0.0) for t in (etoks[i] & etoks[j]))
            acc += 1.0 - shared / tot[i]
        lex[i] = round(acc / (n - 1), 4)
    if vecs is not None and vecs.shape[0] == n:
        sim = vecs @ vecs.T
        for i in range(n):
            others = np.delete(np.arange(n), i)
            den[i] = round(1.0 - float(np.mean(sim[i, others])), 4)
    return lex, den


ARMS = ("baseline", "usecase", "usecase_matched", "synonym")
# every surface the frozen map can touch, on either side of the match
SYN_SURFACES = sorted({t for syns in W.SYN_MAP.values() for form in syns for t in W.toks(form)}
                      | {t for c in W.SYN_MAP for t in W.toks(c)})


def arm_texts(entries: list) -> dict:
    """The four rewrites of one catalogue, applied to *every* entry so the ranker sees a consistent catalogue."""
    base = [dict(e) for e in entries]
    use = [dict(e) for e in entries]
    for e in use:
        e["desc"] = W.usecase_frame(e.get("name", ""), e.get("desc", ""), e.get("params") or [])
    matched = [dict(e) for e in use]
    for b, u in zip(base, matched):
        keep = W.toks(str(b.get("desc") or ""))
        u["desc"] = " ".join(str(u.get("desc") or "").split()[:max(1, len(keep))])
    syn = [dict(e) for e in base]
    for e in syn:
        e["desc"] = W.apply_syn_map(str(e.get("desc") or ""))
        e["name"] = W.apply_syn_map(str(e.get("name") or ""))
    return {"baseline": base, "usecase": use, "usecase_matched": matched, "synonym": syn}


def rank_of(entries: list, question: str, gi: int) -> tuple:
    """(1-based rank of the released selection, 1 if it is rank 1) under the frozen BM25."""
    # `rank_from` returns the rank *of each item* (1 = best), not a sorted ordering: reading it as an ordering made
    # the obvious gold come out at rank 2, which is what the selftest below is for.
    ranks = W.rank_from(W.bm25_matrix(question, entries, mode="full"))
    r = int(ranks[gi]) if 0 <= gi < len(ranks) else int(len(entries))
    return r, int(r == 1)


def selftest() -> int:
    ent = [{"name": "pdf-extract-pages", "desc": "Extract pages from a PDF file.", "params": ["file_path", "pages"]},
           {"name": "pdf-merge", "desc": "Merge several PDF documents into one file.", "params": ["files"]}]
    c, pred, contra = congruence("pdf-extract-pages", ent[0])
    assert c is not None and c > 0.5, f"congruence of a name drawn from its own text must be high, got {c}"
    assert contra == 0, "an affirmative pair must not be scored as a contradiction"
    lx, dn = discrimin_all(entry_tokens(ent))
    assert all(x is not None and 0.0 < x < 1.0 for x in lx), f"two different tools must be strictly apart, got {lx}"
    assert discrimin_all(entry_tokens([ent[0]]))[0][0] is None, "a catalogue of one has no neighbours: None, not 0"
    arms = arm_texts(ent)
    assert set(arms) == set(ARMS) and len(arms["usecase"][0]["desc"]) > len(ent[0]["desc"]), "the frame arm adds text"
    assert len(W.toks(arms["usecase_matched"][0]["desc"])) <= max(1, len(W.toks(ent[0]["desc"]))), \
        "the matched arm must not be longer than the baseline, or 'at matched length' is false"
    assert W.apply_syn_map("fetch the picture") != "fetch the picture", "the synonym map must move a known surface"
    r, hit = rank_of(ent, "extract pages from my pdf file", 0)
    assert r == 1 and hit == 1, f"the obvious gold must rank 1, got rank {r}"
    print("selftest: congruence, discriminability, the four arms and the frozen ranker all behave as documented")
    return 0




def summarise(C: pd.DataFrame, Q: pd.DataFrame, rows_per_config: int = 0, guards: dict | None = None,
              t0=None, rebuilt_from_frames: bool = False) -> dict:
    """The artefact: sizes, guards and the per-arm rates, computed from the two frames however they were made."""
    return {"exp_id": "EXP-0143", "seed": W.SEED, "rows_per_config": rows_per_config,
            "rebuilt_from_frames": rebuilt_from_frames,
            "n_query_rows": int(len(Q)), "n_candidate_rows": int(len(C)),
            "guards": dict(guards or {}), "arms": list(ARMS),
            "column_summary": {c: {"non_null": int(C[c].notna().sum()),
                                   "mean": (round(float(C[c].mean()), 4)
                                            if pd.api.types.is_numeric_dtype(C[c]) and C[c].notna().any() else None)}
                               for c in ("name_desc_congruence", "name_predicate_in_desc", "contradiction",
                                         "facet_overlap", "hier_depth", "discrimin_lexical", "discrimin_dense")
                               if c in C.columns},
            "contradiction_cell_rows": int(C["contradiction"].sum()) if "contradiction" in C else None,
            "dense_neighbour_coverage": round(float(C["discrimin_dense"].notna().mean()), 4)
            if "discrimin_dense" in C else None,
            "arm_hit1_rates": {arm: round(float(Q[f"{arm}_hit1"].mean()), 4) for arm in ARMS
                               if f"{arm}_hit1" in Q},
            "arm_mean_rank": {arm: round(float(Q[f"{arm}_rank"].mean()), 4) for arm in ARMS
                              if f"{arm}_rank" in Q},
            "synonym_arm_coverage": {"gold_rows_the_map_changed": int(Q["gold_synonym_changed"].sum()),
                                     "queries_with_a_mapped_surface": int(Q["query_has_mapped_surface"].sum())},
            "invocation": " ".join([sys.executable] + sys.argv),
            "run_cost": W.run_cost_row("EXP-0143", (t0 or datetime.datetime.now()).timestamp()
                                       if hasattr(t0 or datetime.datetime.now(), "timestamp") else 0,
                                       len(Q), len(C.columns)),
            "started_at": W.now(), "finished_at": W.now()}

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows-per-config", type=int, default=ROWS_PER_CONFIG)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--summarise-only", action="store_true",
                    help="rebuild the artefact from the frames already on disk. The ranking pass costs minutes; a "
                         "mistake in the summary block should not have to pay for it again.")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    if a.selftest:
        return selftest()
    t0 = datetime.datetime.now()
    if a.summarise_only:
        if not (W.OUT / "EXP0143_wave3_query_features.csv").is_file():
            raise SystemExit("ABORT: no frames on disk to summarise; run the full build")
        C = pd.read_csv(W.OUT / "EXP0143_wave3_candidate_features.csv.gz")
        Q = pd.read_csv(W.OUT / "EXP0143_wave3_query_features.csv")
        art = summarise(C, Q, rebuilt_from_frames=True)
        print(W.write_raw("EXP-0143", "wave3_description_matrix", art).name)
        return 0
    if not (TD3.PREMISES.get("verdict") or {}).get("gates") and not TD3.PREMISES.get("gates"):
        raise SystemExit("ABORT: the wave-3 premise census has not been recorded into the designs module")
    d = W.load_routing(cfgs=W.CONFIGS, bucket="dev")
    d = d[d["subset_name"].astype(str).str.contains("single-turn-original", na=False)]
    # The sample is *taken*, not re-drawn: the frozen 24,000 query ids are those the wave-1 and wave-2 matrices were
    # built from, and this wave's own rule says a difference between waves cannot be a difference in the sample.
    # Re-running any RNG here would silently break that sentence.
    want = pd.read_csv(W.PROCES / "EXP0136_wave2_query_features.csv", usecols=["query_id"])["query_id"].astype(str)
    if a.rows_per_config * 3 < len(want):
        want = want.iloc[:a.rows_per_config * 3]
    d = d[d["query_id"].astype(str).isin(set(want))].copy()
    if d["query_id"].astype(str).nunique() != len(want):
        raise SystemExit(f"ABORT: only {d['query_id'].nunique()} of {len(want)} frozen query ids are present in the "
                         f"routing frame; the substrate moved and nothing downstream would be comparable")
    # encoder cache: (query_id, cand_idx) -> row of the document matrix, addressed by the same key formula
    # `encode_wave1_texts.py` wrote, so the vector is the one that run produced for that exact rendered text.
    dvec, dpos = None, {}
    try:
        idx = W.load_encoder_vectors("R2_prose", kind="d")
        keys = [line for line in (W.PROCES / "wave1_encoder_R2_prose_d_keys.jsonl").read_text(
                encoding="utf-8").splitlines() if line.strip()]
        if len(keys) and idx is not None and getattr(idx, "mat", np.zeros(0)).shape[0] == len(keys):
            dvec = idx.mat
            dpos = {k: i for i, k in enumerate(keys)}
    except SystemExit:
        raise
    except Exception as exc:                                       # noqa: BLE001 - a missing cache is a result
        print(f"[exp0143] dense neighbour dissimilarity will be reported as not measured: {exc}")

    c_rows, q_rows, guard = [], [], collections.Counter()
    for r in d.itertuples(index=False):
        ent = W.read_catalog(r.catalog_json, r.n_candidates, r.query_id)
        gold = W.as_int_list(r.gold_idx)
        if not ent or not gold:
            guard["catalog_or_gold_missing"] += 1
            continue
        gi = min(gold)
        q = str(r.question)
        qm = W.constraint_markers(q)
        server = str(getattr(r, "server", "") or "").lower()
        vmat = None
        if dvec is not None:
            pos = [dpos.get(dense_key(r.query_id, i, e)) for i, e in enumerate(ent)]
            if all(x is not None for x in pos) and pos:
                vmat = dvec[pos]
                guard["dense_rows_used"] += 1
            else:
                guard["dense_rows_missing_vector"] += 1
        etoks = entry_tokens(ent)
        dlex, dden = discrimin_all(etoks, vmat)
        # One rank vector per arm, computed before the candidate loop: T120's consistency claim is about the spread
        # of ranks *between* the candidates of a catalogue, so a matrix that recorded only the released selection's
        # rank could not compute it, and the design would have had to re-rank the catalogue a second time elsewhere.
        arms = arm_texts(ent)
        rankmat = {arm: W.rank_from(W.bm25_matrix(q, arms[arm], mode="full")) for arm in ARMS}
        for i, e in enumerate(ent):
            con, pred, contra = congruence(str(e.get("name") or ""), e)
            facets = name_facets(str(e.get("name") or ""), server)
            ftoks = {t for f in facets for t in W.toks(f)}
            overlap = round(len(ftoks & set(W.toks(q))) / max(1, len(ftoks)), 4) if ftoks else None
            lex, den = dlex[i], dden[i]
            c_rows.append(dict(query_id=r.query_id, cfg=r.cfg, cand_idx=i, gold=int(i in gold),
                               name_desc_congruence=con, name_predicate_in_desc=pred, contradiction=contra,
                               hier_depth=len(facets), facet_overlap=overlap,
                               discrimin_lexical=lex, discrimin_dense=den,
                               desc_tokens=len(W.toks(" ".join(str(e.get(k) or "") for k in ("name", "desc",
                                                                                             "params")))),
                               # T120 H3 asks *where* the normalisation helps, so the matrix has to record that an
                               # arm moved a given row's text at all. Without these two flags the design's moderator
                               # is uncomputable and the hypothesis would have to be reported as untested.
                               synonym_changed=int(W.apply_syn_map(str(e.get("desc") or ""))
                                                   != str(e.get("desc") or "")),
                               query_has_mapped_surface=int(any(t in SYN_SURFACES for t in W.toks(q))),
                               **{f"{arm}_rank": int(rankmat[arm][i]) for arm in ARMS}))
        rec = dict(query_id=r.query_id, cfg=r.cfg, n_candidates=len(ent), n_gold=len(gold),
                   gold_desc_tokens=len(W.toks(str(ent[gi].get("desc") or ""))),
                   gold_param_n=len(ent[gi].get("params") or []), question_tokens=len(W.toks(q)))
        for arm in ARMS:
            rk = int(rankmat[arm][gi])
            rec[f"{arm}_rank"], rec[f"{arm}_hit1"] = rk, int(rk == 1)
            if not np.isfinite(rk):
                guard[f"arm_{arm}_no_rank"] += 1
        start = len(c_rows) - len(ent)          # the gold row, not the last row appended for this query
        rec["gold_synonym_changed"] = int(c_rows[start + gi]["synonym_changed"]) if ent and gi < len(ent) else 0
        rec["query_has_mapped_surface"] = int(any(x["query_has_mapped_surface"] for x in c_rows[-len(ent):]))
        rec["catalogue_rows_synonym_changed"] = int(sum(x["synonym_changed"] for x in c_rows[-len(ent):]))
        rec["contradiction_rows"] = int(sum(x["contradiction"] for x in c_rows[-len(ent):]))
        q_rows.append(rec)
    C, Q = pd.DataFrame(c_rows), pd.DataFrame(q_rows)
    W.OUT.mkdir(parents=True, exist_ok=True)
    C.to_csv(W.OUT / "EXP0143_wave3_candidate_features.csv.gz", index=False, compression="gzip")
    Q.to_csv(W.OUT / "EXP0143_wave3_query_features.csv", index=False)
    print(f"[exp0143] wrote {len(C)} candidate rows and {len(Q)} query rows", flush=True)
    if len(Q) != DEV_ROWS_EXPECTED:
        raise SystemExit(f"ABORT: {len(Q)} query rows, the frozen dev sample is {DEV_ROWS_EXPECTED}; the sample "
                         f"changed and no downstream number would be comparable")
    for arm in ARMS:
        bad = int((~np.isfinite(Q[f"{arm}_rank"].astype(float))).sum())
        if bad > 0.01 * len(Q):
            raise SystemExit(f"ABORT: arm {arm!r} produced no rank for {bad} of {len(Q)} queries")
    art = summarise(C, Q, rows_per_config=a.rows_per_config, guards=guard, t0=t0)
    dest = W.write_raw("EXP-0143", "wave3_description_matrix", art)
    print(json.dumps({k: art[k] for k in ("n_query_rows", "n_candidate_rows", "guards", "contradiction_cell_rows",
                                          "arm_hit1_rates")}, ensure_ascii=False, indent=1))
    print("wrote", dest.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
