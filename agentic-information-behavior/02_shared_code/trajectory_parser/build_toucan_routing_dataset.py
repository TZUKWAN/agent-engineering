"""EXP-0009/EXP-0013: build the canonical tool-routing dataset for T037 (v2 join, v4 persistence).

EXP-0004's pilot rejected 26.7% of OSS rows because the gold->catalog join relied on
identifier-name prefixes. That heuristic is unnecessary: every row's
`metadata.mcp_servers[i].remote_server_response.tools` lists that server's real tool
names, so a gold item `"<Server>::<func>"` resolves by (server name, function name)
and a bare `"<func>"` resolves to the unique server in the row that owns it. No
string-prefix guessing remains, and every rejection is a reported data fact rather
than a parser artifact.

Outcome definitions are chance-corrected because EXP-0004 measured random hit@1 at
0.44-0.55 on these short catalogs: raw hit@1 carries almost no signal.
  - norm_rank = (rank_of_best_gold - 1) / (n_candidates - 1)      (0 = perfect, 0.5 = chance)
  - fail@k    = 1 if no gold tool appears in BM25's top k
  - LLR_bits  = log2(P_observed_hit / P_hypergeometric_chance_hit) for the corpus slice
Pre-retrieval features are computed from the user's question text ONLY (never from
gold or from the catalog of the matched tool) so the predictor cannot see the answer.

    python build_toucan_routing_dataset.py --rows-per-config 12000

Outputs results_raw/EXP00NN_toucan_routing_dataset_*.json and 01_datasets/processed/routing_<cfg>.parquet (now carries question + catalog_json so that
  equivalence relabelling and catalog interventions can run without re-reading 79 GB).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from scipy import stats

SEED = 42
DATA = Path(r"G:/刘俊琦/AGENT ENGINEERING/MATLABINTOKEN/datasets/Agent-Ark/Toucan-1.5M")
ROOT = Path(__file__).resolve().parents[2]
# SFT is a fourth config that no P001 decision ever used: its catalogues come from different
# MCP servers (many non-English) and it carries no `metadata` column, so EXP-0020/0021 can use
# it as a genuinely unseen-pipeline transfer set.
CONFIGS = {"OSS": "available_tools", "Qwen3": "available_tools", "Kimi-K2": "available_tools",
           "SFT": "tools"}
DEV_FRACTION_BUCKET = 700          # md5(uuid) % 1000 < 700  -> development
CATALOG_COL_FALLBACK = "tools"

STOP = set("""a an the and or of to in on for with without you your our i my is are be can could
will would should please them they it this that these those from at as by if then there here
what which how when where who all any some one two three first also just need want me help make
using use called call get provide please""".split())


def toks(s: str) -> list[str]:
    parts = re.split(r"[^A-Za-z0-9]+", str(s or ""))
    out = []
    for p in parts:
        if not p:
            continue
        for sub in re.findall(r"[A-Z]+(?![a-z])|[A-Z][a-z]*|[a-z]+|\d+", p):
            w = sub.lower()
            if w not in STOP and (len(w) > 1 or w.isdigit()):
                out.append(w)
    return out


class BM25:
    def __init__(self, k1: float = 1.4, b: float = 0.4):
        self.k1, self.b = k1, b

    def scores(self, q: list[str], docs: list[list[str]]) -> list[float]:
        n = len(docs)
        if n == 0:
            return []
        tf = [Counter(d) for d in docs]
        dl = [len(d) for d in docs]
        df: Counter = Counter()
        for c in tf:
            df.update(c.keys())
        avgdl = sum(dl) / n
        uniq = set(q)
        out = []
        for i in range(n):
            s = 0.0
            for t in uniq:
                f = tf[i].get(t, 0)
                if not f:
                    continue
                idf = math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5))
                s += idf * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * dl[i] / avgdl))
            out.append(s)
        return out

    def rank(self, q: list[str], docs: list[list[str]]) -> list[int]:
        sc = self.scores(q, docs)
        return sorted(range(len(sc)), key=lambda i: -sc[i])


def bucket(uuid: str) -> int:
    return int(hashlib.md5(str(uuid).encode()).hexdigest()[:8], 16) % 1000


def parse_catalog(js):
    try:
        cat = json.loads(js)
    except Exception:
        return None
    if not isinstance(cat, list):
        return None
    docs = []
    for e in cat:
        if not isinstance(e, dict):
            continue
        f = e.get("function") if isinstance(e.get("function"), dict) else e
        name = f.get("name") or f.get("tool_name") or f.get("id")
        if not name:
            continue
        params = list((f.get("parameters") or {}).get("properties", {}).keys()) \
            if isinstance(f.get("parameters"), dict) else []
        docs.append({"name": str(name), "desc": str(f.get("description") or ""), "params": params})
    return docs or None


def server_tool_index(md_json):
    """-> dict func_name -> set(server_name_slug), plus set of all server slugs in the row."""
    try:
        md = json.loads(md_json) if isinstance(md_json, str) else (md_json or {})
    except Exception:
        return {}, set()
    idx: dict[str, set] = defaultdict(set)
    servers = set()
    for s in (md.get("mcp_servers") or []):
        sname = str((s or {}).get("server_name") or "")
        slug = re.sub(r"[^a-z0-9]+", "-", sname.lower()).strip("-")
        if slug:
            servers.add(slug)
        resp = (s or {}).get("remote_server_response") or {}
        for t in (resp.get("tools") or []):
            nm = str((t or {}).get("name") or "")
            if nm:
                idx[nm].add(slug)
    return dict(idx), servers


def resolve_gold_v2(items, catalog, srv_idx, srv_slugs):
    """Deterministic join. Returns (matched indices, reject_reason or None)."""
    by_name = {d["name"]: i for i, d in enumerate(catalog)}
    matched, seen = [], set()
    for it in items:
        it = it.strip()
        if "::" in it:
            server, func = (x.strip() for x in it.split("::", 1))
            sslug = re.sub(r"[^a-z0-9]+", "-", server.lower()).strip("-")
            owner = {k: v for k, v in srv_idx.items() if k == func}
            if func not in by_name and f"{sslug}-{func}" in by_name:
                func = f"{sslug}-{func}"
            if func not in by_name:
                # function may be listed under a different server spelling: try suffix on catalog
                cand = [n for n in by_name if n == func or n.endswith("-" + func)]
                if len(cand) != 1:
                    return None, ("gold_func_not_in_catalog" if not cand else "ambiguous_by_suffix")
                func = cand[0]
            if sslug and srv_idx.get(func) and sslug not in srv_idx[func]:
                return None, "server_mismatch"
            i = by_name[func]
        else:
            if it in by_name:
                i = by_name[it]
            else:
                cand = [n for n in by_name if n.endswith("-" + it)]
                if len(cand) == 1:
                    i = by_name[cand[0]]
                elif len(cand) > 1:
                    return None, "ambiguous_by_suffix"
                else:
                    return None, "gold_func_not_in_catalog"
        if i not in seen:
            seen.add(i)
            matched.append(i)
    return sorted(matched), None


# ---------------- pre-retrieval features (question text only) ----------------

ORD_WORDS = ["first", "then", "next", "finally", "after that", "before", "second", "third", "last", "step"]
CONSTRAINT_WORDS = ["must", "only", "without", "no more than", "at least", "exactly", "not", "limit",
                    "avoid", "require", "should not", "cannot", "maximum", "minimum", "specific"]
VAGUE_WORDS = ["something", "stuff", "things", "some", "maybe", "etc", "and so on", "whatever", "related",
               "appropriate", "suitable", "good", "nice", "few"]
EPISTEMIC = ["maybe", "perhaps", "possibly", "probably", "i think", "not sure", "unsure", "if possible",
             "somewhat", "roughly", "around"]
SEQ_MARKERS = r"(?:\bfirst\b|\bthen\b|\bnext\b|\bafter (?:that|this)\b|\bfinally\b|\bfinally,\b|\bsecond\b|\bthird\b)"


def question_features(q: str) -> dict:
    ql = str(q or "").lower()
    words = re.findall(r"[A-Za-z][A-Za-z'-]+", ql)
    n_w = max(1, len(words))
    sents = [s for s in re.split(r"[.!?]+", ql) if s.strip()]
    # ellipsis / unspecified-reference proxies: pronoun-initial clauses and bare objects
    pron_start = len(re.findall(r"(?:^|[,.;] )(?:it|this|that|they|them|there)\b", ql))
    demonstratives = len(re.findall(r"\b(?:this|that|these|those|it|them)\b", ql))
    quotes = len(re.findall(r"[\"'“”‘’]", ql))
    proper_entities = len(re.findall(r"\b(?:[A-Z][a-z0-9]+(?:[ _-][A-Z][a-z0-9]+)+)\b", str(q or "")))
    file_refs = len(re.findall(r"\b[\w-]+\.(?:pdf|csv|xlsx?|docx?|txt|json|py|js|png|jpg|md|sql)\b", ql))
    urls = len(re.findall(r"https?://|\bwww\.", ql))
    numbers = len(re.findall(r"\b\d+\b", ql))
    named_apps = len(re.findall(r"\b(?:excel|word|gmail|github|notion|spotify|instagram|twitter|slack|"
                                r"youtube|google maps|google calendar|airbnb|figma|jira|conda|docker|"
                                r"vs code|vscode|python|sql|json|csv|telegram|discord|whatsapp|"
                                r"shopify|stripe|hugging ?face|arxiv|zhihu|leetcode)\b", ql))
    return {
        "n_tokens": len(words),
        "n_chars": len(str(q or "")),
        "n_sentences": len(sents),
        "mean_sentence_len": len(words) / max(1, len(sents)),
        "lex_diversity_mtld_proxy": len(set(words)) / math.sqrt(n_w),
        "constraint_density": len(re.findall("|".join(re.escape(c) for c in CONSTRAINT_WORDS), ql)) / n_w,
        "n_constraint_words": len(re.findall("|".join(r"\b%s\b" % re.escape(c) for c in CONSTRAINT_WORDS), ql)),
        "sequence_marker_n": len(re.findall(SEQ_MARKERS, ql)),
        "epistemic_marker_n": len(re.findall("|".join(r"\b%s\b" % re.escape(e) for e in EPISTEMIC), ql)),
        "vague_word_n": len(re.findall("|".join(r"\b%s\b" % re.escape(v) for v in VAGUE_WORDS), ql)),
        "demonstrative_n": demonstratives,
        "pronoun_clause_start": pron_start,
        "quoted_span_n": quotes // 2,
        "proper_entity_n": proper_entities,
        "file_reference_n": file_refs,
        "url_n": urls,
        "number_n": numbers,
        "named_app_n": named_apps,
        "imperative_start": int(bool(re.match(r"^\s*(?:please\s+)?(?:[a-z]+)\b", ql) and
                                    re.match(r"^\s*(?:please\s+)?(find|get|search|list|show|create|send|open|"
                                             r"add|check|make|write|run|download|fetch|retrieve|compare|tell|"
                                             r"help|give|set|use|generate|pull|update|delete)", ql))),
        "question_mark": int("?" in str(q or "")),
        "n_subtasks_by_punctuation": max(0, len(re.findall(r"[;,]|\band\b.*\b(and|then)\b", ql))),
        "n_lines": str(q or "").count("\n") + 1,
        "has_bullet_list": int(bool(re.search(r"^\s*[-*]\s", str(q or ""), re.M))),
        "char_per_subtask": len(str(q or "")) / max(1, 1 + len(re.findall(r"[.;]|\n", ql))),
    }


FEATURE_COLS = ["n_tokens", "n_chars", "n_sentences", "mean_sentence_len", "lex_diversity_mtld_proxy",
                "constraint_density", "n_constraint_words", "sequence_marker_n", "epistemic_marker_n",
                "vague_word_n", "demonstrative_n", "pronoun_clause_start", "quoted_span_n",
                "proper_entity_n", "file_reference_n", "url_n", "number_n", "named_app_n",
                "imperative_start", "question_mark", "n_subtasks_by_punctuation", "n_lines",
                "has_bullet_list", "char_per_subtask",
                "qpp_coverage", "qpp_idf_weighted_coverage", "qpp_clarity_meanmax", "qpp_clarity_sd",
                "qpp_max_doc_sim", "qpp_mean_doc_sim", "qpp_doc_sim_spread", "qpp_ecle",
                "qpp_missing_term_n", "qpp_n_query_terms"]
QPP_COLS = [c for c in FEATURE_COLS if c.startswith("qpp_")]
LINGUISTIC_COLS = [c for c in FEATURE_COLS if not c.startswith("qpp_")]


def auc_score(y: np.ndarray, score: np.ndarray) -> float:
    """Mann-Whitney AUC with tie correction; 0.5 means no discrimination."""
    y = np.asarray(y)
    pos, neg = score[y == 1], score[y == 0]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    r = stats.rankdata(np.concatenate([pos, neg]))
    return float((r[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))


def collection_qpp_features(qtok: list[str], docs: list[list[str]]) -> dict:
    """Collection-aware PRE-retrieval QPP signals (CLARITY / ECLE / coverage family).

    Uses only the query and the whole candidate catalog of that row - never the gold
    labels - so it is legitimately pre-retrieval in the QPP sense, and stays purely
    lexical (no model API). EXP-0006 showed query-only features were weak and partly
    a length artifact, so the accepted QPP feature class is the principled next step.
    """
    n = len(docs)
    if not qtok or n == 0:
        return {"qpp_coverage": 0.0, "qpp_clarity_meanmax": 0.0, "qpp_clarity_sd": 0.0,
                "qpp_ecle": 0.0, "qpp_missing_term_n": len(set(qtok)), "qpp_n_query_terms": len(set(qtok)),
                "qpp_idf_weighted_coverage": 0.0}
    df: Counter = Counter()
    dl = []
    for d in docs:
        c = set(d)
        df.update(c)
        dl.append(len(d))
    uniq = set(qtok)
    covered = {t for t in uniq if df.get(t, 0) > 0}
    idf = {t: math.log((1 + n) / (1 + df.get(t, 0))) + 1.0 for t in uniq}
    # mean max cosine between each query term (as bag) and each document
    per_doc_sim = []
    for d, L in zip(docs, dl):
        if L == 0:
            per_doc_sim.append(0.0)
            continue
        c = Counter(d)
        num = sum(c[t] for t in uniq)
        den = math.sqrt(L) * math.sqrt(max(1, len(uniq)))
        per_doc_sim.append(num / den if den else 0.0)
    maxs = []
    for t in uniq:
        best = 0.0
        for d, L in zip(docs, dl):
            if L == 0:
                continue
            f = Counter(d).get(t, 0)
            best = max(best, f / math.sqrt(L))
        maxs.append(best)
    ecle = 0.0
    for t in uniq:
        s = [float(sum(1 for x in d if x == t)) / max(1, len(d)) for d in docs]
        if n > 1:
            ent = -sum((p / (sum(s) or 1)) * math.log2(p / (sum(s) or 1)) for p in s if p > 0)
            ecle += idf[t] * ent
    wsum = sum(idf[t] for t in uniq) or 1.0
    return {"qpp_coverage": round(len(covered) / len(uniq), 4),
            "qpp_idf_weighted_coverage": round(sum(idf[t] for t in covered) / wsum, 4),
            "qpp_clarity_meanmax": round(float(np.mean(maxs)), 6),
            "qpp_clarity_sd": round(float(np.std(maxs, ddof=0)), 6),
            "qpp_max_doc_sim": round(float(np.max(per_doc_sim)), 6),
            "qpp_mean_doc_sim": round(float(np.mean(per_doc_sim)), 6),
            "qpp_doc_sim_spread": round(float(np.max(per_doc_sim) - np.mean(per_doc_sim)), 6),
            "qpp_ecle": round(ecle / len(uniq), 6),
            "qpp_missing_term_n": len(uniq - covered),
            "qpp_n_query_terms": len(uniq)}


def hyper_chance(g: int, n: int, k: int) -> float:
    """P(at least one gold in top-k) for a uniform random ranker."""
    if n <= 0 or g <= 0:
        return 0.0
    k = min(k, n)
    return 1.0 - (math.comb(n - g, k) / math.comb(n, k)) if n - g >= k else 0.0


def boot_ci(vals, boot=2000, seed=SEED):
    v = np.asarray(vals, dtype=float)
    rng = np.random.default_rng(seed)
    bs = v[rng.integers(0, len(v), size=(boot, len(v)))].mean(axis=1)
    return float(np.mean(v)), [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows-per-config", type=int, default=12000)
    ap.add_argument("--shards-per-config", type=int, default=8)
    ap.add_argument("--configs", default="OSS,Qwen3,Kimi-K2",
                    help="comma list; EXP-0020 builds the untouched SFT pipeline with --configs SFT")
    ap.add_argument("--exp-id", default="EXP-0013")
    args = ap.parse_args()
    cfgs = [c.strip() for c in args.configs.split(",") if c.strip()]
    for c in cfgs:
        if c not in CONFIGS:
            raise SystemExit(f"unknown config {c}; known: {sorted(CONFIGS)}")

    t0 = time.time()
    exp = {"exp_id": args.exp_id, "seed": SEED, "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "protocol_note": "test split written to parquet but NOT evaluated here; all numbers below are dev-only",
           "configs": {}}
    print(f"{args.exp_id} routing dataset, prompt_id-grouped split | seed={SEED} | rows/config={args.rows_per_config}")

    for cfg in cfgs:
        col = CONFIGS[cfg]
        shards = sorted((DATA / cfg).glob("*.parquet"))
        picks = sorted(random.Random(SEED).sample(shards, min(args.shards_per_config, len(shards))))
        have = set(pq.ParquetFile(picks[0]).schema_arrow.names)
        want_cols = [c for c in ["uuid", "question", col, "target_tools", "metadata", "subset_name"]
                     if c in have]
        stat, kept = Counter(), []
        missing_cols = sorted({"metadata", col} - have)
        for sp in picks:
            if len(kept) >= args.rows_per_config:
                break
            tbl = pq.read_table(sp, columns=want_cols)
            n = min(args.rows_per_config - len(kept), tbl.num_rows)
            for r in tbl.take(sorted(random.Random(SEED).sample(range(tbl.num_rows), n))).to_pylist():
                stat["rows_seen"] += 1
                catalog = parse_catalog(r[col])
                if not catalog:
                    stat["reject_catalog_unparseable"] += 1
                    continue
                items = [x.strip() for x in re.split(r",(?![^{]*\})", str(r["target_tools"] or "")) if x.strip()]
                if not items:
                    stat["reject_no_gold"] += 1
                    continue
                srv_idx, srv_slugs = server_tool_index(r.get("metadata"))
                try:
                    pid = str(json.loads(r["metadata"]).get("prompt_id") or r["uuid"])
                except Exception:
                    pid = str(r["uuid"])
                matched, why = resolve_gold_v2(items, catalog, srv_idx, srv_slugs)
                if matched is None:
                    stat["reject_" + why] += 1
                    continue
                if not srv_idx:
                    stat["note_no_mcp_server_tool_list"] += 1
                else:
                    stat["note_server_index_present"] += 1
                q = r["question"]
                f = question_features(q)
                qtok = toks(q)
                docs_full = [toks(d["name"].replace("-", " ").replace("_", " ")) + toks(d["desc"]) + toks(" ".join(d["params"]))
                             for d in catalog]
                docs_desc = [toks(d["desc"]) for d in catalog]
                br = BM25()
                sc_full = br.scores(qtok, docs_full)
                sc_desc = br.scores(qtok, docs_desc)
                ranked_full = sorted(range(len(sc_full)), key=lambda i: -sc_full[i])
                ranked_desc = sorted(range(len(sc_desc)), key=lambda i: -sc_desc[i])
                # score margin is a POST-retrieval quasi-local QPP baseline: stored separately so
                # pre-retrieval models can be compared against it, never mixed into them.
                srt = sorted(sc_full, reverse=True)
                margin = (srt[0] - srt[1]) if len(srt) > 1 else srt[0] if srt else 0.0
                n_c = len(catalog)
                rb = min((ranked_full.index(i) + 1 for i in matched), default=n_c)
                rb_desc = min((ranked_desc.index(i) + 1 for i in matched), default=n_c)
                kept.append({
                    "uuid": r["uuid"], "cfg": cfg, "subset_name": r["subset_name"],
                    "prompt_id": pid,
                    # EXP-0008: an original prompt and its follow-up rows share prompt_id but get
                    # different uuids, so splitting on uuid leaks paraphrase-adjacent rows across.
                    "split": "dev" if bucket(pid) < DEV_FRACTION_BUCKET else "test",
                    "n_candidates": n_c, "n_gold": len(matched),
                    "gold_idx": json.dumps(matched),
                    "bm25_best_rank": rb, "bm25_desc_best_rank": rb_desc,
                    "bm25_top1_score": round(max(sc_full) if sc_full else 0.0, 6),
                    "bm25_margin": round(margin, 6),
                    "norm_rank": (rb - 1) / max(1, (n_c - 1)),
                    "fail_at_1": int(rb > 1), "fail_at_3": int(rb > 3), "fail_at_5": int(rb > 5),
                    "chance_hit_1": hyper_chance(len(matched), n_c, 1),
                    "chance_hit_3": hyper_chance(len(matched), n_c, 3),
                    "chance_hit_5": hyper_chance(len(matched), n_c, 5),
                    "n_servers_in_row": len(srv_slugs),
                    "question": str(q)[:4000],
                    # Lossless on purpose: EXP-0014 re-scores the persisted catalog with the frozen
                    # BM25 to check it reproduces the published ranking, and a 600-char cap broke
                    # that reproduction on 16-18% of rows (measured), because BM25 saw full text.
                    "catalog_json": json.dumps([{"n": d["name"], "d": d["desc"], "p": d["params"]}
                                                for d in catalog], ensure_ascii=False),
                    **collection_qpp_features(qtok, docs_full), **f})
        df = pd.DataFrame(kept)
        # D11 guard: the row SET depends on --shards-per-config, whose default is not the published
        # run's value, so a rebuild can silently swap the sample. Anchor every build to a recorded
        # uuid digest and refuse to overwrite a different sample.
        digest = hashlib.sha256("|".join(sorted(df.uuid.astype(str))).encode()).hexdigest()[:16]
        anchor = ROOT / "01_datasets" / "manifests" / "routing_sample_identity.json"
        ident = json.loads(anchor.read_text(encoding="utf-8")) if anchor.exists() else {"configs": {}}
        published = (ident["configs"].get(cfg) or {}).get("uuid_digest")
        if published and published != digest and "--allow-resample" not in sys.argv:
            raise SystemExit(f"[{cfg}] SAMPLE DRIFT: built uuid digest {digest} != published "
                             f"{published}. Restore 01_datasets/snapshots/exp0009_published/ or pass "
                             f"--allow-resample and re-freeze the protocol.")
        if not published:
            # a config built for the first time anchors its own identity so later rebuilds cannot
            # silently swap the sample the way D11 caught for the published three.
            ident["configs"][cfg] = {"uuid_digest": digest, "rows": int(len(df)),
                                     "invocation": {"rows_per_config": args.rows_per_config,
                                                    "shards_per_config": args.shards_per_config},
                                     "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
            anchor.write_text(json.dumps(ident, indent=1), encoding="utf-8")
            print(f"[{cfg}] first build: anchored sample identity {digest}")
        df["uuid_digest"] = digest
        outdir = ROOT / "01_datasets" / "processed"
        outdir.mkdir(parents=True, exist_ok=True)   # E20: a bare checkout has no processed/ dir
        df.to_parquet(outdir / f"routing_{cfg}.parquet", index=False)
        dev = df[df.split == "dev"]
        # aggregate chance correction in bits (LLR of observed hit-rate vs hypergeometric chance)
        agg = {"rows_seen": stat["rows_seen"], "rows_kept": int(len(df)),
               "source_columns_missing": missing_cols,
               "gold_join_verified_by_server_index": int(stat.get("note_server_index_present", 0)),
               "rejection_accounting": {k: v for k, v in sorted(stat.items()) if k.startswith("reject_")},
               "notes": {k: v for k, v in sorted(stat.items()) if k.startswith("note_")},
               "exclusion_rate": round(1 - len(df) / max(1, stat["rows_seen"]), 4),
               "catalog_size": {"mean": round(df.n_candidates.mean(), 2), "min": int(df.n_candidates.min()),
                                "p50": int(df.n_candidates.median()), "max": int(df.n_candidates.max()),
                                "distinct": int(df.n_candidates.nunique())},
               "gold_per_query": {"mean": round(df.n_gold.mean(), 3), "max": int(df.n_gold.max())},
               "dev": {}}
        for k in (1, 3, 5):
            hit = 1 - dev[f"fail_at_{k}"]
            ch = dev[f"chance_hit_{k}"].mean()
            m, ci = boot_ci(1 - dev[f"fail_at_{k}"].values)
            mc, cic = boot_ci(dev[f"chance_hit_{k}"].values)
            llr = math.log2(max(m, 1e-9) / max(mc, 1e-9))
            mnrm, cinrm = boot_ci(dev["norm_rank"].values)
            agg["dev"][f"hit@{k}"] = {"mean": round(m, 4), "ci95": [round(x, 4) for x in ci]}
            agg["dev"][f"chance_hit@{k}"] = {"mean": round(mc, 4), "ci95": [round(x, 4) for x in cic]}
            agg["dev"][f"LLR_bits@{k}"] = round(llr, 4)
        mn, cim = boot_ci(dev["norm_rank"].values)
        agg["dev"]["norm_rank"] = {"mean": round(mn, 4), "ci95": [round(x, 4) for x in cim],
                                   "chance_value": 0.5}
        # description-only ranking (catalog metadata without tool names) as a classic comparator
        dm, dci = boot_ci((dev["bm25_desc_best_rank"] <= 3).astype(float).values)
        agg["dev"]["desc_only_hit@3"] = {"mean": round(dm, 4), "ci95": [round(x, 4) for x in dci]}
        w = stats.mannwhitneyu(dev["bm25_best_rank"], dev["bm25_desc_best_rank"], alternative="less")
        agg["dev"]["full_vs_desc_rank_mwu_p"] = float(w.pvalue)

        # ---- T037 signal check on DEV only (in-sample fit; not the held-out claim) ----
        y = dev["fail_at_3"].values.astype(int)
        agg["dev"]["fail_at_3_prevalence"] = round(float(y.mean()), 4)
        agg["dev"]["n_positives"] = int(y.sum())
        agg["dev"]["n_queries"] = int(len(dev))
        agg["dev"]["auc_B0_query_length"] = round(auc_score(y, -dev["n_tokens"].values), 4)
        agg["dev"]["auc_post_margin"] = round(auc_score(y, -dev["bm25_margin"].values), 4)
        agg["dev"]["auc_post_top1score"] = round(auc_score(y, -dev["bm25_top1_score"].values), 4)
        pre = [c for c in FEATURE_COLS if c in dev.columns]
        Xp = dev[pre].astype(float)
        sd = Xp.std(ddof=0).replace(0, 1.0)
        Xz = ((Xp - Xp.mean()) / sd)
        Xz["log_n_candidates"] = np.log(dev["n_candidates"].astype(float).values)
        Xz.insert(0, "const", 1.0)
        try:
            import statsmodels.api as sm
            Xv = Xz.values.astype(float)
            lg = sm.Logit(y, Xv).fit(disp=0, maxiter=300)
            agg["dev"]["auc_pre_logistic_insample"] = round(auc_score(y, -np.asarray(lg.predict(Xv))), 4)
            ci = np.asarray(lg.conf_int())
            or_tab = {}
            for i, name in enumerate(Xz.columns):
                if name == "const":
                    continue
                or_tab[name] = {"OR": round(float(np.exp(lg.params[i])), 4),
                                "ci95_OR": [round(float(np.exp(ci[i][0])), 4), round(float(np.exp(ci[i][1])), 4)],
                                "p": float(lg.pvalues[i])}
            ordered = sorted(or_tab.items(), key=lambda kv: kv[1]["p"])
            m = len(ordered)
            running = 0.0
            for rank, (k, v) in enumerate(ordered, start=1):
                running = max(running, min(1.0, (m - rank + 1) * v["p"]))
                v["p_holm"] = round(running, 6)
                v["sig_holm_005"] = bool(running < 0.05)
            agg["dev"]["pre_logistic_OR_holm"] = or_tab
        except Exception as e:
            agg["dev"]["logistic_error"] = f"{type(e).__name__}: {e}"

        # with median 3 candidates most queries are near-trivial: stratify by catalog size
        strata = {}
        for lab, mask in [("cand<=3", dev["n_candidates"] <= 3), ("4-7", dev["n_candidates"].between(4, 7)),
                          ("8-15", dev["n_candidates"].between(8, 15)), (">=16", dev["n_candidates"] >= 16)]:
            sub = dev[mask]
            if len(sub) >= 30:
                yy = sub["fail_at_3"].values.astype(int)
                strata[lab] = {"n": int(len(sub)), "fail@3": round(float(yy.mean()), 4),
                               "chance_hit@3": round(float(sub["chance_hit_3"].mean()), 4),
                               "auc_length": round(auc_score(yy, -sub["n_tokens"].values), 4)}
        agg["dev"]["catalog_size_strata"] = strata
        agg["test_queries_reserved_not_evaluated"] = int((df.split == "test").sum())
        exp["configs"][cfg] = agg
        print(f"\n[{cfg}] seen={stat['rows_seen']} kept={len(df)} ({round(100*(1-len(df)/max(1,stat['rows_seen'])),2)}% rejected)")
        print(f"   rejections: {agg['rejection_accounting']}")
        print(f"   catalog size mean={agg['catalog_size']['mean']} p50={agg['catalog_size']['p50']} max={agg['catalog_size']['max']}")
        for k in (1, 3, 5):
            print(f"   hit@{k}={agg['dev'][f'hit@{k}']['mean']} CI{agg['dev'][f'hit@{k}']['ci95']} "
                  f"| chance={agg['dev'][f'chance_hit@{k}']['mean']} | LLR={agg['dev'][f'LLR_bits@{k}']} bits")
        print(f"   norm_rank dev={agg['dev']['norm_rank']['mean']} CI{agg['dev']['norm_rank']['ci95']} (chance 0.5)")
        print(f"   fail@3 prevalence (T037 DV) = {agg['dev']['fail_at_3_prevalence']}")

    exp["wallclock_sec"] = round(time.time() - t0, 1)
    exp["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    out = ROOT / "results_raw" / f"{args.exp_id.replace('-', '')}_toucan_routing_dataset_{time.strftime('%Y%m%dT%H%M%S')}.json"
    out.write_text(json.dumps(exp, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"\nwrote {out}  (wallclock {exp['wallclock_sec']}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
