"""EXP-0054 (T004 feasibility): do these corpora even carry a declared instruction-provenance label, and does the
instruction text differ across it?

T004 was registered as "Real Human vs Synthetic Agent Instructions" on the strength of an AgentNet file that is NOT
on this machine (the eight corpora under `MATLABINTOKEN/datasets` are all that is here — measured by listing the
tree, not assumed). So the question is re-scoped honestly: which releases state, in their own metadata, which of
their instructions were human-written and which were generated or rewritten by a model; and where such a label
exists, does the text actually differ, or is the label documentation only?

Frozen GO rule, written before any statistic was computed: a paper is admissible iff in at least TWO releases a
logistic predictor of a declared PROVENANCE label (task taxonomies such as `category` are excluded - they are
reported but cannot count toward GO, a restriction added when the first run showed a task taxonomy clearing the bar) — scored out-of-fold with GroupKFold on that release's dependence key —
reaches AUC >= 0.75, beats a length-only baseline by >= 0.05, and beats its own label-permutation null by >= 0.05,
with the same direction of the length effect in both passing releases. Otherwise the topic dies at the pilot: the
spec's pruning rule, not a lack of interest.

    python 02_shared_code/data_audit/provenance_label_feasibility_t004.py
"""
from __future__ import annotations

import json, pathlib, random, re, sys, time, zlib
from collections import Counter

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "02_shared_code" / "data_audit"))
import governance_metadata_pilot_p005 as G      # noqa: E402

OUT, PROC = ROOT / "results_raw", ROOT / "results_processed"
SEED = 42
GROUPS_MIN = 60
ROWS_CAP = 4000
FILES_PER_RELEASE = 60
LABEL_COLS = {"subset_name", "category", "subcategory", "original_teacher", "agent", "trajectory_format",
              "config_name", "source", "orig_source", "trace_source"}
GROUP_KEYS = ["prompt_id", "instance_id", "repo", "uuid", "id"]
# The rule was construct-blind: it accepted ANY low-cardinality categorical column, so a task taxonomy could satisfy
# a bar written for human-vs-synthetic provenance. Task taxonomies are still reported, but they cannot count toward
# GO. The allowlist is the columns that state where a record came from, not what it is about.
TAXONOMY_COLS = {"category", "subcategory", "task"}
STOP = set("the a an and or of to in for with on at is are be this that it its you your we our as by from into".split())
FILE_RE = re.compile(r"[\w/-]+\.(py|json|csv|txt|md|parquet|tsv|ipynb|js|ts|go|rs|java|sh|yml|yaml)\b", re.I)
CONSTRAINT_WORDS = ["must", "should", "only", "exactly", "at least", "no more than", "each", "every", "without",
                    "using", "then", "before", "after", "do not", "ensure", "required"]
EPISTEMIC = ["why", "how", "what", "could", "would", "maybe", "perhaps", "unclear", "please", "approach",
             "recommend", "best", "suggest"]


def feats(text):
    t = str(text)
    toks = re.findall(r"[A-Za-z][A-Za-z']+", t.lower())
    n = max(1, len(toks))
    sent = max(1, len([s for s in re.split(r"[.!?]\s", t.strip()) if s.strip()]))
    low = t.lower()
    return {"n_tokens": float(len(toks)), "n_chars": float(len(t)),
            "mean_word_len": sum(map(len, toks)) / n, "lex_diversity": len(set(toks) - STOP) / n,
            "tokens_per_sent": len(toks) / sent, "question_mark": float("?" in t),
            "uppercase_ratio": sum(c.isupper() for c in t) / max(1, len(t)),
            "digit_ratio": sum(c.isdigit() for c in t) / max(1, len(t)),
            "newline_n": float(t.count("\n")), "bullet_n": float(len(re.findall(r"(?m)^\s*[-*]\s", t))),
            "url_n": float(len(re.findall(r"https?://", t))), "file_ref_n": float(len(FILE_RE.findall(t))),
            "quoted_n": float(t.count('"') // 2),
            "constraint_n": float(sum(low.count(w) for w in CONSTRAINT_WORDS)),
            "epistemic_n": float(sum(low.count(w) for w in EPISTEMIC)),
            "nonascii_ratio": sum(ord(c) > 127 for c in t) / max(1, len(t))}


def instruction_text(row):
    parts = []
    for k, v in row.items():
        kl = k.lower()
        if kl in {"question", "instruction", "task", "prompt", "user_query", "goal"}:
            parts.append(str(v))
        elif kl in {"messages", "conversations"}:
            msgs = v
            if isinstance(msgs, str):
                try:
                    msgs = json.loads(msgs)
                except Exception:
                    msgs = []
            for m in msgs if isinstance(msgs, list) else []:
                if isinstance(m, dict) and str(m.get("role", m.get("from", ""))).lower() in ("user", "human"):
                    parts.append(str(m.get("content", m.get("value", ""))))
    return "\n".join(parts)


def sample_rows(d, cap, seed):
    """One random row group per file, over a random subset of files (bounded, coverage recorded)."""
    rng = random.Random(seed)
    # stratified over top-level config directories, so a minority subset cannot be missed by drawing 60 files from
    # the whole release
    dirs = [x for x in sorted(d.iterdir()) if x.is_dir() and not x.name.startswith(".")] or [d]
    files = []
    per = max(1, FILES_PER_RELEASE // max(1, len(dirs)))
    for sub in dirs:
        cand = sorted(sub.rglob("*.parquet"))
        if cand:
            files += sorted(rng.sample(cand, min(len(cand), per)))
    files = sorted(set(files))
    rows = []
    for p in files:
        if len(rows) >= cap:
            break
        try:
            f = pq.ParquetFile(p)
            if not f.metadata.num_rows:
                continue
            rg = rng.randrange(int(f.metadata.num_row_groups))
            take = max(1, cap // max(1, len(files)))
            tbl = f.read_row_group(rg)
            if tbl.num_rows > take:
                tbl = tbl.take(sorted(rng.sample(range(tbl.num_rows), take)))
            rows.extend(tbl.to_pylist())
        except Exception:
            continue
    return rows


def oof_auc(M, y, g, cols, seed=SEED, shuffle=False):
    p = np.zeros(len(y))
    yy = y.copy()
    if shuffle:
        np.random.default_rng(seed).shuffle(yy)
    idx = list(range(M.shape[1])) if cols is None else cols
    try:
        for a, b in GroupKFold(n_splits=5).split(M[:, idx], yy, groups=g):
            if len(set(yy[a])) < 2:
                return None
            m = make_pipeline(StandardScaler(), LogisticRegression(max_iter=3000, C=0.5))
            m.fit(M[a][:, idx], yy[a])
            p[b] = m.predict_proba(M[b][:, idx])[:, 1]
    except ValueError:
        return None
    if len(set(yy)) < 2:
        return None
    return round(float(roc_auc_score(yy, p)), 4)


def contrast(name, rel, label_col, values, files_seed, pair=None):
    """One labelled pair. `pair` lets the caller test every declared pair, not just the two largest groups: the
    first version took only the two largest, which for Toucan compared diversify against multi-turn and never
    compared the human-written subset against its LLM-rewritten version - the actual construct."""
    keep = list(pair) if pair else [g for g, c in values.most_common(2) if c >= GROUPS_MIN]
    if len(keep) < 2:
        return None
    rows = sample_rows(G.DATA / rel, max(ROWS_CAP, 6000), files_seed)
    X, y, g, gaps = [], [], [], []
    key_used = None
    for i, r in enumerate(rows):
        lab = str(r.get(label_col, ""))
        if lab not in keep:
            continue
        txt = instruction_text(r)
        if len(txt.strip()) < 20:
            continue
        f = feats(txt)
        X.append(f); y.append(1 if lab == keep[0] else 0)
        k = next((k for k in GROUP_KEYS if k in r), None)
        key_used = key_used or k
        g.append(str(r[k]) if k else f"row{i}")
    if min(Counter(y).values()) < GROUPS_MIN:
        return None
    df = pd.DataFrame(X)
    M, yv, gv = df.values, np.array(y), np.array(g)
    len_cols = [list(df.columns).index(c) for c in ("n_tokens", "n_chars")]
    auc_all = oof_auc(M, yv, gv, None)
    auc_len = oof_auc(M, yv, gv, len_cols)
    nulls = [oof_auc(M, yv, gv, None, seed=SEED + 7 * i, shuffle=True) for i in range(10)]
    nulls = [x for x in nulls if x is not None]
    mt = {keep[0]: float(df[yv == 1].n_tokens.mean()), keep[1]: float(df[yv == 0].n_tokens.mean())}
    gaps = {c: round(float(df[yv == 1][c].mean() - df[yv == 0][c].mean()), 3) for c in df.columns}
    return {"corpus": name, "label_col": label_col, "kept": keep, "n": int(len(df)),
            "dependence_key": key_used, "n_groups": int(len(set(g))),
            "auc_all_features": auc_all, "auc_length_only": auc_len,
            "permutation_null_mean_auc": round(float(np.mean(nulls)), 4) if nulls else None,
            "permutation_null_max_auc": round(float(np.max(nulls)), 4) if nulls else None,
            "mean_tokens": {k: round(v, 1) for k, v in mt.items()},
            "longer_group": max(mt, key=mt.get), "feature_gaps": gaps,
            "cardinality_declared_groups": len(values)}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    res = {"exp_id": "EXP-0054", "topic": "T004 (re-scoped: AgentNet is not on this machine)",
           "rule": "GO iff >=2 releases: AUC>=0.75, >=0.05 over length-only, >=0.05 over permutation null, "
                   "same sign of the length effect", "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "label_census": [], "contrasts": []}
    for name, rel in G.CORPORA.items():
        d = G.DATA / rel
        # Stratified census: one random row group from one random file per top-level config directory. The first
        # version read the first three files' first row groups, which for Toucan returned a single `subset_name`
        # value and so never tested a contrast the release does declare
        # (single-turn-original / single-turn-diversify / multi-turn / irrelevant).
        dirs = [x for x in sorted(d.iterdir()) if x.is_dir() and not x.name.startswith(".")] or [d]
        vals = {}
        for sub in dirs:
            cand = sorted(sub.rglob("*.parquet"))
            if not cand:
                continue
            p = cand[random.Random(SEED + zlib.crc32(sub.name.encode()) % 9973).randrange(len(cand))]
            try:
                f = pq.ParquetFile(p)
                rg = random.Random(SEED + zlib.crc32(str(sub.name).encode()) % 9973).randrange(
                    int(f.metadata.num_row_groups))
                tab = f.read_row_group(rg)
            except Exception:
                continue
            for c in [x for x in tab.column_names if x in LABEL_COLS]:
                try:
                    cnt = Counter(str(v)[:60] for v in tab.column(c).to_pylist()[:2000])
                except Exception:
                    continue
                for k, v in cnt.items():
                    vals.setdefault(c, Counter())[k] += v
        res["label_census"].append({"corpus": name, "label_columns": sorted(vals),
                                    "observed_values": {c: dict(Counter(v).most_common(8)) for c, v in vals.items()}})
        print(f"  {name:13s} label columns={sorted(vals)}")
        for c in sorted(vals):
            if c in TAXONOMY_COLS and 2 <= len(vals[c]) <= 12:
                res.setdefault("taxonomy_labels_reported_only", []).append(
                    {"corpus": name, "label_col": c, "values": dict(vals[c].most_common(8)),
                     "reason": "a task taxonomy is not an instruction-provenance statement"})
                continue
            if 2 <= len(vals[c]) <= 12:
                big = [g for g, n in vals[c].most_common(4) if n >= GROUPS_MIN]
                pairs = [(a, b) for i, a in enumerate(big) for b in big[i + 1:]] or [None]
                for pr in pairs:
                    out = contrast(name, rel, c, vals[c], SEED + zlib.crc32(name.encode()) % 9973, pair=pr)
                    if out:
                        res["contrasts"].append(out)
                        print(f"     {c} vs {out['kept']}: n={out['n']} auc={out['auc_all_features']} "
                              f"len={out['auc_length_only']} null={out['permutation_null_mean_auc']}")
    passing = [c for c in res["contrasts"] if c["auc_all_features"] and c["auc_length_only"] is not None
               and c["permutation_null_mean_auc"] is not None
               and c["auc_all_features"] >= 0.75
               and c["auc_all_features"] - c["auc_length_only"] >= 0.05
               and c["auc_all_features"] - c["permutation_null_mean_auc"] >= 0.05]
    res["n_contrasts_tested"] = len(res["contrasts"])
    res["n_passing"] = len(passing)
    res["passing"] = [{"corpus": c["corpus"], "label": c["label_col"], "auc": c["auc_all_features"],
                       "longer": c["longer_group"]} for c in passing]
    same_sign = len({c["longer_group"] for c in passing}) == 1 and len(passing) >= 2
    res["length_sign_consistent"] = bool(same_sign)
    res["verdict"] = "GO" if (len(passing) >= 2 and same_sign) else (
        "PILOT_ONLY_ONE_CONTRAST" if passing else "NO_GO_NOT_MEASURABLE_OR_UNCODED")
    res["wallclock_sec"] = round(time.time() - t0, 1)
    res["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    out = OUT / f"EXP0054_provenance_label_feasibility_{time.strftime('%Y%m%dT%H%M%S')}.json"
    out.write_text(json.dumps(res, indent=1, ensure_ascii=False, default=str), encoding="utf-8", newline="")
    pd.DataFrame([{"corpus": c["corpus"], "label_col": c["label_col"], "kept": "|".join(map(str, c["kept"])),
                   "n": c["n"], "dependence_key": c["dependence_key"], "auc": c["auc_all_features"],
                   "auc_length": c["auc_length_only"], "null_mean": c["permutation_null_mean_auc"],
                   "longer_group": c["longer_group"]} for c in res["contrasts"]]
                 ).to_csv(PROC / "EXP0054_label_contrasts.csv", index=False)
    print("verdict", res["verdict"], "| contrasts", res["n_contrasts_tested"], "| passing", len(passing))
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
