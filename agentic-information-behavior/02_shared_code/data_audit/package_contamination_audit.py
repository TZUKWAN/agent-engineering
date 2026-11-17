"""EXP-0104 (spec E19): a contamination, duplication and leakage audit for the packages that had none.

P001 has had this since EXP-0008/EXP-0019/EXP-0022 (split integrity, catalogue overlap, cross-corpus transfer). When
EXP-0103 mapped every package onto the spec's minimum complete experiment package, E19 came out OPEN for P002, P003,
P004 and P005 - the papers reason about shared identifiers (an `instance_id` covered by ~63 rollouts, three teacher
configs built from the same prompts, the same releases audited from two angles) without ever measuring the overlap.
This script measures it on the rows those packages read.

Four scopes, each with its own question:
  * **P002** - are SWE-ZERO and AgentTrove independent evidence, and does AgentTrove's own `split` column leak?
  * **P004 / P001 routing lineage** - does the same question text appear in both buckets of the dev/test split? The
    split is `md5(prompt_id) % 1000 < 700` (EXP-0008 moved it off `uuid` precisely because follow-up rows share a
    prompt_id), so a *prompt_id* cannot straddle the boundary - but two rows with identical question text and
    different prompt_ids can, and that residual is what this measures over the whole processed dataset, not a sample.
  * **P004 teacher configs** - how much of the three configs' evidence is the same underlying prompt.
  * **P003 / P005** - are the releases independent evidence for a census, i.e. does one task text appear in two of them.

Two measurement defects were fixed after the first pass, and both are the same class of error: a check that cannot see
its subject reports a clean zero. `files[:3]` measured the shard layout rather than the corpus, and reading only
scalar text columns silently reported AgentBank, code-act and AgentInstruct - whose task text lives inside
`conversations` - as duplicate-free. A third was found in this rewrite: AgentTrove's `instruction` and `split` columns
exist but are null in every row sampled, so `1 distinct instruction` was the distinct count of nothing, and the
"no split leakage" verdict had no subject. Every quantity below is therefore reported **per source column**, with the
number of rows that actually carry a value next to it, and `not_measured` when that number is zero.

    python 02_shared_code/data_audit/package_contamination_audit.py [--rows 250] [--skip-routing]

Numbers go to `results_processed/EXP0104_contamination_<scope>.csv` plus a JSON artefact; each package's E19 row in
`E_COVERAGE.md` then points at them.
"""
from __future__ import annotations
import argparse, collections, glob, hashlib, json, pathlib, re, sys, time
from collections import Counter

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = next(a for a in [pathlib.Path(__file__).resolve().parent,
                        *pathlib.Path(__file__).resolve().parents] if (a / "00_program_registry").is_dir())
DATA = ROOT.parent / "MATLABINTOKEN" / "datasets"
ROUTED = ROOT / "01_datasets" / "processed"
OUT_PROC = ROOT / "results_processed"
OUT_RAW = ROOT / "results_raw"
SEED = 42
NORM = re.compile(r"\s+")
TEXT_SOURCES = ("instruction", "question", "prompt", "task", "problem_statement", "problem", "query", "text")
MSG_SOURCES = ("conversations", "messages", "turns", "dialog")
ID_SOURCES = ("uuid", "id", "run_id", "task_id", "episode", "instance_id", "repo")
TEMPLATE_SHARE = 0.5        # a value carried by >50% of rows is a template, not a task identity


def sig(text) -> str:
    return hashlib.sha1(NORM.sub(" ", str(text or "")).strip().lower().encode("utf-8")).hexdigest()[:16]


def turn_text(msg_list):
    """First user/human turn of a message list, from whichever key the release uses (`role`/`from`, `content`/`value`)."""
    for m in (msg_list or []):
        if not isinstance(m, dict):
            continue
        if (m.get("role") or m.get("from")) in ("user", "human"):
            return str(m.get("content") or m.get("value") or "")
    return ""


def pick(files, n_per_file):
    """Seeded shard choice, capped rows per shard. The shard count deliberately exceeds the square-root rule the
    analysis runs use, because some releases store one task per shard: sampling few shards then measures the shard
    layout rather than the corpus."""
    rng = np.random.default_rng(SEED)
    k = min(len(files), max(24, int(len(files) ** 0.5) * 4))
    idx = rng.permutation(len(files))[:k]
    return [files[i] for i in sorted(idx)], n_per_file


def summarise(vals):
    """Duplicate structure of one source column over the rows read, with the empties counted rather than dropped."""
    filled = [sig(v) for v in vals if str(v or "").strip()]
    c = Counter(filled)
    dups = {k: v for k, v in c.items() if v > 1}
    return {"rows_read": len(vals), "rows_with_value": len(filled), "distinct_values": len(c),
            "keys_in_more_than_one_row": len(dups), "rows_in_a_duplicated_key": int(sum(dups.values())),
            "largest_group": max(dups.values()) if dups else 1,
            "share_duplicated": round(sum(dups.values()) / len(filled), 4) if filled else None,
            "largest_group_share": round(max(c.values()) / len(filled), 4) if filled else None,
            "is_template": bool(filled) and max(c.values()) / len(filled) > TEMPLATE_SHARE,
            "not_measured": "column present but no row sampled carries a value" if not filled else None}


def profile(files, rows_per_file, extra_text=None):
    """Per-source-column summary over a seeded shard sample. Returns (shards, {source: summary}, schema)."""
    fs, _ = pick(files, rows_per_file)
    cols_seen, schema = set(), set()
    buckets = collections.defaultdict(list)
    for f in fs:
        have = set(pq.ParquetFile(f).schema_arrow.names)
        schema |= have
        use = [c for c in TEXT_SOURCES + MSG_SOURCES + ID_SOURCES + tuple(extra_text or ()) if c in have]
        cols_seen.update(use)
        recs = pq.read_table(f, columns=use).slice(0, rows_per_file).to_pylist()
        for r in recs:
            for c in use:
                if c in MSG_SOURCES:
                    buckets[f"{c}[first user turn]"].append(turn_text(r.get(c)))
                else:
                    buckets[c].append(r.get(c))
    return fs, {k: summarise(v) for k, v in sorted(buckets.items())}, sorted(schema)


def best_text_source(summaries, exclude_idlike=()):
    """The source to compare between corpora: a populated one, not an identifier, not a template."""
    for k, s in sorted(summaries.items()):
        if s["rows_with_value"] == 0 or k in exclude_idlike:
            continue
        if k in ID_SOURCES or "[first user turn]" not in k and k not in TEXT_SOURCES:
            continue
        if s["is_template"]:
            continue
        return k
    return ""


def text_sigs(files, rows_per_file, source):
    """Signatures of one named source over the seeded sample, for cross-corpus comparison. A source named
    `<message column>[first user turn]` is read out of the message list rather than as a scalar column."""
    fs = pick(files, rows_per_file)[0]
    scalar, msgcol = source, None
    if "[first user turn]" in source:
        msgcol, scalar = source.split("[", 1)[0], None
    out = set()
    for f in fs:
        have = set(pq.ParquetFile(f).schema_arrow.names)
        col = msgcol or scalar
        if col not in have:
            continue
        recs = pq.read_table(f, columns=[col]).slice(0, rows_per_file).to_pylist()
        for r in recs:
            v = turn_text(r.get(col)) if msgcol else r.get(col)
            if str(v or "").strip():
                out.add(sig(v))
    return out


def overlap_a_b(a, b, note):
    shared = a & b
    return {"shared_signatures": len(shared), "a_distinct": len(a), "b_distinct": len(b), "note": note}


# ------------------------------------------------------------------ P002
def p002(rows_per_file):
    out = {"package": "P002", "corpora": {}}
    swe = [f for f in sorted(glob.glob(str(DATA / "AlienKevin/SWE-ZERO-12M-trajectories/**/*.parquet"), recursive=True))
           if ".cache" not in f]
    trove = [f for f in sorted(glob.glob(str(DATA / "open-thoughts/AgentTrove/**/*.parquet"), recursive=True))
             if ".cache" not in f]
    if not swe or not trove:
        raise SystemExit("ABORT: P002's corpora are not on this disk - the audit would report nothing")
    fs, sum_swe, sch_swe = profile(swe, rows_per_file)
    out["corpora"]["SWE-ZERO-12M"] = {"shards_sampled": len(fs), "schema": sch_swe, "sources": sum_swe}
    ft, sum_tro, sch_tro = profile(trove, rows_per_file)
    # split integrity on the release's own `split` column, keyed on the task slug where one exists
    split_of = collections.defaultdict(set)
    for f in ft:
        have = set(pq.ParquetFile(f).schema_arrow.names)
        use = [c for c in ("split", "task", "run_id", "episode") if c in have]
        for r in pq.read_table(f, columns=use).slice(0, rows_per_file).to_pylist():
            key = str(r.get("task") or r.get("run_id") or r.get("episode") or "")
            if key and r.get("split") is not None:
                split_of[sig(key)].add(str(r.get("split")))
    cross = sum(1 for v in split_of.values() if len(v) > 1)
    n_split_rows = sum(1 for v in split_of.values() if v)
    out["corpora"]["AgentTrove"] = {
        "shards_sampled": len(ft), "schema": sch_tro, "sources": sum_tro,
        "split_leakage": {"tasks_with_a_split_value": n_split_rows, "tasks_in_more_than_one_split": cross,
                          "verdict": ("LEAKAGE: a task slug appears under two split values" if cross else
                                      ("no task slug crosses a split boundary in this sample" if n_split_rows else
                                       "NOT TESTABLE: the release's `split` column is null in every row sampled, "
                                       "so there is no boundary to check and no leakage claim can be made"))}}
    # independence: identifiers never match across the two releases, so the question is the task text
    swe_src = best_text_source(sum_swe) or "messages[first user turn]"
    tro_src = best_text_source(sum_tro) or "conversations[first user turn]"
    a = text_sigs(swe, rows_per_file, swe_src)
    b = text_sigs(trove, rows_per_file, tro_src)
    out["cross_corpus"] = {
        "swe_text_source": swe_src, "trove_text_source": tro_src,
        "swe_template_share": sum_swe.get(swe_src, {}).get("largest_group_share"),
        "trove_template_share": sum_tro.get(tro_src, {}).get("largest_group_share"),
        "comparable": bool(a) and bool(b),
        "exact_text_overlap": overlap_a_b(a, b, "signatures of the whole first-turn text"),
        "shared_task_or_instance_identifiers": overlap_a_b(
            text_sigs(swe, rows_per_file, "instance_id"), text_sigs(trove, rows_per_file, "task"),
            "different naming schemes, so a match would mean one release is derived from the other"),
        "verdict": ("NOT COMPARABLE: one side yielded no task text in the sampled rows, so a zero overlap would be a "
                    "statement about nothing" if not (a and b) else
                    ("INDEPENDENT: no shared identifier and no shared task text" if not (a & b)
                     else "OVERLAP: the two corpora are not independent evidence"))}
    templ = [s for s, summ in ((swe_src, sum_swe), (tro_src, sum_tro)) if summ.get(s, {}).get("is_template")]
    out["caveat"] = (f"{', '.join(templ)}: one value covers most of the rows, so overlap measured on it is template "
                     f"sharing rather than task sharing; the identifier comparison is the strong one." if templ else
                     "both text sources carry per-row distinct task text in the sampled rows, so exact-text overlap is "
                     "a meaningful independence test there; the identifier comparison is reported alongside it.")
    return out


# ------------------------------------------------------------------ P004 teacher configs
def p004(rows_per_file):
    out = {"package": "P004", "corpora": {}}
    base = DATA / "Agent-Ark/Toucan-1.5M"
    cfgs = [p.name for p in sorted(base.iterdir()) if p.is_dir() and p.name in ("OSS", "Qwen3", "Kimi-K2")]
    if not cfgs:
        raise SystemExit(f"ABORT: no Toucan configs under {base}")
    per_cfg_prompts, pid_pool, all_uuids = {}, {}, []
    for cfg in cfgs:
        files = [f for f in sorted(glob.glob(str(base / cfg / "*.parquet"))) if ".cache" not in f]
        fs, summ, sch = profile(files, rows_per_file, extra_text=("metadata",))
        by_pid = collections.defaultdict(set)
        for f in fs:
            have = set(pq.ParquetFile(f).schema_arrow.names)
            use = [c for c in ("uuid", "question", "metadata") if c in have]
            for r in pq.read_table(f, columns=use).slice(0, rows_per_file).to_pylist():
                try:
                    pid = str(json.loads(r["metadata"]).get("prompt_id") or r["uuid"])
                except Exception:                                      # noqa: BLE001
                    pid = str(r["uuid"])
                by_pid[pid].add(sig(r.get("question")))
                pid_pool.setdefault(cfg, set()).add(pid)
                all_uuids.append(str(r.get("uuid")))
        per_cfg_prompts[cfg] = {s for v in by_pid.values() for s in v}
        out["corpora"][cfg] = {"shards_sampled": len(fs), "schema": sch, "sources": summ,
                               "questions_sharing_a_prompt_id": int(sum(1 for v in by_pid.values() if len(v) > 1))}
    shared_any = set()
    seen = {}
    for cfg, s in per_cfg_prompts.items():
        for q in s:
            if q in seen:
                shared_any.add(q)
            seen[q] = cfg
    pools = list(pid_pool.values())
    pid_shared = set()
    for i in range(len(pools)):
        for j in range(i + 1, len(pools)):
            pid_shared |= pools[i] & pools[j]
    out["cross_config"] = {
        "configs": cfgs, "prompt_ids_shared_by_two_configs": len(pid_shared),
        "questions_shared_by_all_configs": len(set.intersection(*per_cfg_prompts.values()) if per_cfg_prompts else set()),
        "questions_shared_by_more_than_one_config": len(shared_any),
        "uuid_shared_across_configs_rows": int(len(all_uuids) - len(set(all_uuids))),
        "note": "the teacher configs are generated from overlapping prompt pools, so the same question appearing in "
                "two configs is the dependence P004's clustered intervals and P001's per-config reporting exist to cover"}
    return out


# ------------------------------------------------------------------ the dev/test boundary (whole dataset, not a sample)
def routing(rows_per_file):
    """Residual leakage across the split the papers' test numbers are computed on.

    The processed routing tables are what every downstream step reads, so this scope is measured on all of their rows:
    a sampled leakage check can only ever bound the risk, and the claim at stake is that the test bucket is unseen."""
    out = {"package": "P001+P004 (processed routing)", "configs": {}}
    files = sorted(ROUTED.glob("routing_*.parquet"))
    if not files:
        out["not_measured"] = f"no routing_*.parquet under {ROUTED}"
        return out
    per_cfg_q, per_cfg_gold = {}, {}
    for f in files:
        cfg = f.stem.replace("routing_", "")
        have = set(pq.ParquetFile(f).schema_arrow.names)
        cols = [c for c in ("uuid", "question", "prompt_id", "split", "gold_idx") if c in have]
        if "split" not in cols or "question" not in cols:
            out["configs"][cfg] = {"not_measured": f"the processed table has no {'/'.join(('split','question'))} "
                                                   f"column; present: {sorted(have)}"}
            continue
        df = pd.read_parquet(f, columns=cols)
        qs = collections.defaultdict(set)
        for q, s in zip(df["question"].astype(str), df["split"].astype(str)):
            qs[sig(q)].add(s)
        dev = set(df[df["split"] == "dev"]["uuid"].astype(str))
        test = set(df[df["split"] == "test"]["uuid"].astype(str))
        per_cfg_q[cfg] = {sig(q) for q in df["question"].astype(str)}
        dup_q = {k for k, v in qs.items() if len(v) > 1}
        pid_col = "prompt_id" if "prompt_id" in df.columns else None
        pid_leak = 0
        if pid_col:
            g = df.groupby(df[pid_col].astype(str))["split"].nunique()
            pid_leak = int((g > 1).sum())
        out["configs"][cfg] = {
            "rows": int(len(df)), "uuid_distinct": int(df["uuid"].nunique()),
            "uuid_rows_in_a_duplicated_key": int(len(df) - df["uuid"].nunique()),
            "dev_uuids": len(dev), "test_uuids": len(test), "uuid_in_both_buckets": len(dev & test),
            "question_texts": len(qs), "question_texts_in_both_buckets": len(dup_q),
            "test_rows_whose_text_also_appears_in_dev": int(
                df[(df["split"] == "test") & (df["question"].astype(str).map(sig).isin(dup_q))].shape[0]),
            "question_leak_share_of_test_rows": round(
                float(df[(df["split"] == "test") & (df["question"].astype(str).map(sig).isin(dup_q))].shape[0]) /
                max(1, len(test)), 6),
            "prompt_ids_in_both_buckets": pid_leak}
        if "gold_idx" in df.columns:
            per_cfg_gold[cfg] = {sig(str(v)) for v in df["gold_idx"].astype(str)}
    names = sorted(out["configs"])
    pairs = []
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i], names[j]
            shared = per_cfg_q.get(a, set()) & per_cfg_q.get(b, set())
            gold = per_cfg_gold.get(a, set()) & per_cfg_gold.get(b, set())
            pairs.append({"config_a": a, "config_b": b, "shared_question_texts": len(shared),
                          "shared_gold_sets": len(gold)})
    out["cross_config_text"] = pairs
    measured = {c: v for c, v in out["configs"].items() if "rows" in v}
    leaked = {c: v["question_texts_in_both_buckets"] for c, v in measured.items()
              if v.get("question_texts_in_both_buckets")}
    out["verdict"] = ("CLEAN: no question text appears in both buckets in any config" if not leaked
                      else f"LEAKAGE: question text crosses the boundary in {sorted(leaked)}")
    if not measured:
        out["verdict"] = "NOT MEASURED: no processed routing table carries both a question and a split column"
    return out


# ------------------------------------------------------------------ P003 / P005 (release-level independence)
def estate(rows_per_file):
    """The releases P003 and P005 audit are the same directories on disk; their contamination question is whether the
    releases are independent evidence, which is answerable from the task text each one exposes."""
    out = {"package": "P003+P005", "releases": {}}
    texts_by_release = {}
    for org in sorted(p for p in DATA.iterdir() if p.is_dir()):
        for repo in sorted(p for p in org.iterdir() if p.is_dir()):
            name = f"{org.name}/{repo.name}"
            files = [f for f in sorted(glob.glob(str(repo / "**/*.parquet"), recursive=True)) if ".cache" not in f]
            if not files:
                out["releases"][name] = {"shards_sampled": 0, "not_measured": "no parquet shards on disk"}
                continue
            fs, summ, sch = profile(files, rows_per_file)
            src = best_text_source(summ)
            entry = {"shards_sampled": len(fs), "schema": sch, "sources": summ, "text_source_used": src or None}
            if not src:
                entry["not_measured"] = ("no source column carries task text in the sampled rows: "
                                         + ", ".join(f"{k}={v['rows_with_value']}/{v['rows_read']}"
                                                     for k, v in sorted(summ.items())
                                                     if k in TEXT_SOURCES or "[first user turn]" in k))
            out["releases"][name] = entry
            texts_by_release[name] = text_sigs(files, rows_per_file, src) if src else set()
    names = sorted(texts_by_release)
    pairs, compared = [], 0
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i], names[j]
            if not texts_by_release[a] or not texts_by_release[b]:
                continue
            compared += 1
            shared = texts_by_release[a] & texts_by_release[b]
            if shared:
                pairs.append({"release_a": a, "release_b": b, "shared_task_text_signatures": len(shared),
                              "a_texts": len(texts_by_release[a]), "b_texts": len(texts_by_release[b])})
    out["cross_release"] = {"releases_with_task_text": sum(1 for v in texts_by_release.values() if v),
                            "release_pairs_compared": compared, "pairs_with_shared_task_text": pairs,
                            "verdict": ("INDEPENDENT on exact task text in the sampled shards" if not pairs
                                        else "OVERLAP: two releases carry the same task text")}
    out["note"] = ("P003 and P005 ask about schemas and declared rights, so their E19 exposure is whether the releases "
                   "are independent evidence. Exact task-text signatures are compared here; the cross-release "
                   "tool-name overlap was measured already at programme level (EXP-0020..0023). A release whose sampled "
                   "rows carry no task text is reported as not measured and is left out of the pairwise comparison.")
    return out


def flatten(path: str, d, rows, depth=0):
    """One CSV row per leaf of the nested result, addressed by its path, so the CSV cannot silently drop a level."""
    for k in sorted(d):
        v = d[k]
        p = f"{path}/{k}" if path else k
        if isinstance(v, dict):
            flatten(p, v, rows, depth + 1)
        else:
            rows.append({"measure": p, "value": json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v})


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=250, help="rows read per sampled shard")
    ap.add_argument("--skip-routing", action="store_true", help="skip the whole-dataset split-leakage scope")
    ap.add_argument("--only", default="", help="comma list of scopes to run (P002, P004, P003_P005, ROUTING); a "
                                              "package's reproduce.sh names only its own so a rebuild does not "
                                              "re-audit every corpus on disk")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    res = {"exp_id": "EXP-0104", "at": time.strftime("%Y-%m-%dT%H:%M:%S"), "rows_per_shard": a.rows, "seed": SEED,
           "rule": "one row per source column; a column with no sampled value is reported as not measured, never as a "
                   "clean zero", "packages": {}}
    scopes = [("P002", p002), ("P004", p004), ("P003_P005", estate), ("ROUTING", routing)]
    want = {s.strip() for s in a.only.split(",") if s.strip()}
    if want:
        unknown = want - {s for s, _ in scopes}
        if unknown:
            raise SystemExit(f"ABORT: unknown scope(s) {sorted(unknown)} - the audit would silently run nothing")
        scopes = [sc for sc in scopes if sc[0] in want]
    if a.skip_routing:
        scopes = [sc for sc in scopes if sc[0] != "ROUTING"]
    if not scopes:
        raise SystemExit("ABORT: no scope selected")
    for name, fn in scopes:
        print(f"  {name} ...", flush=True)
        d = fn(a.rows)
        res["packages"][name] = d
        key = name.lower().replace("_", "-")
        flat = []
        flatten(name, {k: v for k, v in d.items() if k in ("corpora", "releases", "configs")}, flat)
        for extra in ("cross_corpus", "cross_config", "cross_release", "cross_config_text", "verdict", "caveat",
                      "note", "not_measured"):
            if extra in d:
                flatten(name, {extra: d[extra]}, flat)
        pd.DataFrame(flat, columns=["measure", "value"]).to_csv(
            OUT_PROC / f"EXP0104_contamination_{key}.csv", index=False)
        for rel, vals in d.get("releases", {}).items():
            if isinstance(vals, dict) and vals.get("not_measured"):
                print(f"    NOT MEASURED {rel}: {str(vals['not_measured'])[:110]}")
        if "cross_corpus" in d:
            print("    cross-corpus exact-text overlap:", d["cross_corpus"]["exact_text_overlap"]["shared_signatures"],
                  "| shared identifiers:", d["cross_corpus"]["shared_task_or_instance_identifiers"]["shared_signatures"],
                  "|", d["cross_corpus"]["verdict"])
            print("    AgentTrove split:", d["corpora"]["AgentTrove"]["split_leakage"]["verdict"])
        if "cross_config" in d:
            print("    questions shared by >1 config:", d["cross_config"]["questions_shared_by_more_than_one_config"])
        if "cross_release" in d:
            cr = d["cross_release"]
            print(f"    {cr['verdict']} ({cr['release_pairs_compared']} pairs, "
                  f"{cr['releases_with_task_text']} releases with task text)")
            for p in cr["pairs_with_shared_task_text"]:
                print(f"      {p['release_a']} x {p['release_b']}: {p['shared_task_text_signatures']} shared")
        if "configs" in d:
            print(f"    {d['verdict']}")
            for cfg, v in sorted(d["configs"].items()):
                if "rows" not in v:
                    print(f"      {cfg}: NOT MEASURED - {v.get('not_measured')}")
                    continue
                print(f"      {cfg}: rows={v['rows']} question_texts_in_both_buckets="
                      f"{v['question_texts_in_both_buckets']} uuid_in_both_buckets={v['uuid_in_both_buckets']} "
                      f"prompt_ids_in_both_buckets={v['prompt_ids_in_both_buckets']}")
    res["wallclock_sec"] = round(time.time() - t0, 1)
    out = OUT_RAW / f"EXP0104_package_contamination_{time.strftime('%Y%m%dT%H%M%S')}.json"
    out.write_text(json.dumps(res, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    print("wrote", out.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
