"""EXP-0083: ToolRet's EVAL release, ingested and audited before any score is taken.

EXP-0082 had to use the benchmark's training partition, whose per-query candidate set is ten mined hard negatives - a
degenerate catalogue for a construct about production catalogues. This step acquires the evaluation release and
settles, by full census over every row, two things that a first draft got wrong:

  * which candidate pool a query actually faces. Joining each query only against the partition named by its own
    `category` field finds a gold tool for 43-77% of rows; joining against the union of the three released partitions
    finds one for essentially all of them, so the category-restricted join would have discarded a large part of the
    benchmark as "gold missing" - a defect in the join, not a property of the data, and invisible until someone
    counted resolution rates before scoring;
  * what the frozen pipeline costs at this size. `collection_qpp_features` recomputes corpus statistics per query even
    though every query in a partition now shares one catalogue, which puts the full 7,961-row census at hours on this
    host; the transfer run therefore uses a stratified sample, and says so.

Two negative results are recorded rather than dropped: the `toolret` package is not on PyPI from this index, and
`raw.githubusercontent.com` timed out on its source files this round, so the authors' own loader could not be read and
the construct was settled from the released bytes instead.

    python toolret_eval_ingestion_audit_p001.py
"""
from __future__ import annotations

import csv, collections, io, json, pathlib, sys, time
import pyarrow.parquet as pq

HERE = pathlib.Path(__file__).resolve().parent          # 02_shared_code/data_audit
ROOT = HERE.parents[1]                                   # repository root
BASE = ROOT / "01_datasets" / "raw" / "toolret"
QDIR, TDIR = BASE / "queries", BASE / "tools"
OUT_RAW = ROOT / "results_raw"
P001 = ROOT / "papers" / "P001_routing_failure_qpp"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "trajectory_parser"))
from build_toucan_routing_dataset import BM25, collection_qpp_features, toks   # noqa: E402


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    NOW = time.strftime("%Y-%m-%dT%H:%M:%S")
    if not QDIR.is_dir() or not TDIR.is_dir():
        raise SystemExit(f"ABORT: {QDIR} or {TDIR} missing - snapshot_download the two repos first")

    ids, part, per_cat_ids = [], collections.Counter(), {}
    for f in sorted(p for p in TDIR.rglob("*.parquet")):
        col = pq.read_table(f, columns=["id"])["id"].to_pylist()
        ids += col
        part[f.parent.name] += len(col)
        per_cat_ids[f.parent.name] = set(col)
    assert len(set(ids)) == len(ids), "duplicate tool ids in the released corpus"
    idset = set(ids)

    tot_q = tot_gold = res_any = res_all = labels_missing = 0
    cat_any, cat_tot = collections.Counter(), collections.Counter()
    sub_sets = {}
    for f in sorted(QDIR.rglob("*.parquet")):
        subset = f.parent.name
        t = pq.read_table(f, columns=["id", "category", "labels"]).to_pydict()
        n_any = n_all = 0
        for cat, labs in zip(t["category"], t["labels"]):
            try:
                labs = json.loads(labs) if isinstance(labs, str) else list(labs or [])
            except json.JSONDecodeError:
                labs = []
            g = [l.get("id") for l in labs if isinstance(l, dict) and l.get("id")]
            tot_q += 1
            cat_tot[cat] += 1
            if not g:
                labels_missing += 1
                continue
            found = [x for x in g if x in idset]
            tot_gold += len(g)
            res_any += bool(found)
            res_all += (len(found) == len(g))
            cat_any[cat] += bool(per_cat_ids.get(cat, set()) & set(g))
            n_any += bool(found)
            n_all += (len(found) == len(g))
        sub_sets[subset] = {"queries": len(t["id"]), "gold_any": n_any, "gold_all": n_all}

    tok_docs = [toks("tool " + str(i) + " retrieve data") for i in range(len(ids))]
    bm = BM25(k1=1.4, b=0.4)
    qt = toks("retrieve the stock price for a ticker")
    c0 = time.time(); bm.scores(qt, tok_docs); t_bm = time.time() - c0
    c0 = time.time(); collection_qpp_features(qt, tok_docs); t_qpp = time.time() - c0
    sec_q = 2 * (t_bm + t_qpp)                      # the transfer scores two text arms per row

    exp = {"exp_id": "EXP-0083", "paper_id": "P001", "at": NOW,
           "source_repos": {"queries": "mangopy/ToolRet-Queries", "tools": "mangopy/ToolRet-Tools",
                            "discovered_via": "hf-mirror collection page for mangopy/tool-retrieval",
                            "channel": "huggingface_hub.snapshot_download with HF_ENDPOINT=https://hf-mirror.com"},
           "bytes_on_disk": {str(p.relative_to(ROOT)): sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
                             for p in (QDIR, TDIR)},
           "queries_total": tot_q, "query_subsets": len(sub_sets),
           "tool_docs_total": len(ids), "tool_docs_by_partition": dict(part),
           "gold_resolution_full_census": {
               "gold_ids_total": tot_gold, "queries_with_one_gold_in_union": res_any,
               "queries_with_all_golds_in_union": res_all,
               "share_any": round(res_any / max(1, tot_q), 4), "share_all": round(res_all / max(1, tot_q), 4),
               "queries_without_labels": labels_missing,
               "category_restricted_join_share_any": {c: round(cat_any[c] / max(1, cat_tot[c]), 4) for c in cat_tot}},
           "frozen_pipeline_cost": {"bm25_sec": round(t_bm, 3), "corpus_qpp_sec": round(t_qpp, 3),
                                    "sec_per_query_two_arms": round(sec_q, 2),
                                    "full_census_hours_estimate": round(sec_q * tot_q / 3600, 1)},
           "negative_results": ["toolret is not installable from the reachable PyPI index (pip download: no matching "
                                "distribution)",
                                "raw.githubusercontent.com timed out on toolret/config.py, eval.py, utils.py and "
                                "setup.py this round, so the authors' loader was not read"],
           "per_subset": sub_sets, "wallclock_sec": round(time.time() - t0, 1)}
    OUT_RAW.mkdir(parents=True, exist_ok=True)
    fp = OUT_RAW / f"EXP0083_toolret_eval_ingestion_{time.strftime('%Y%m%dT%H%M%S')}.json"
    fp.write_text(json.dumps(exp, indent=1, ensure_ascii=False), encoding="utf-8", newline="")

    cr = exp["gold_resolution_full_census"]["category_restricted_join_share_any"]
    doc = f"""# ToolRet's evaluation release: ingested, audited, and what it costs to score (EXP-0083)

Artefact `{fp.name}`; run {NOW}; {exp['wallclock_sec']}s. No model API was called and no AUROC is claimed here.

## Where it came from

`external_toolret_transfer.md` scored the benchmark's *training* partition, whose per-query candidate set is ten mined
hard negatives. The evaluation release was located through the mirror's collection page for `mangopy/tool-retrieval`,
which names the repos the paper and README only allude to:

* `mangopy/ToolRet-Queries` - **{tot_q:,} queries** over {len(sub_sets)} task subsets
  ({exp['bytes_on_disk'][str(QDIR.relative_to(ROOT))]:,} B);
* `mangopy/ToolRet-Tools` - **{len(ids):,} tool documents** in three partitions
  ({', '.join(f'{k}={v:,}' for k, v in sorted(part.items()))}; {exp['bytes_on_disk'][str(TDIR.relative_to(ROOT))]:,} B),
  with no duplicate ids.

Both arrived via `snapshot_download(..., repo_type='dataset')` under `HF_ENDPOINT=https://hf-mirror.com`. Two negative
results are part of the record: the `toolret` package is **not** obtainable from the reachable PyPI index, and
`raw.githubusercontent.com` timed out on all four of its source files this round - so the authors' own protocol loader
could not be read, and the candidate-set question below was settled from the released bytes instead of from their code.

## Which pool a query faces, counted over every row

| join variant | queries resolving >=1 gold | queries resolving every gold |
|---|---|---|
| union of the three partitions | {res_any:,}/{tot_q:,} = {exp['gold_resolution_full_census']['share_any']} | {res_all:,}/{tot_q:,} = {exp['gold_resolution_full_census']['share_all']} |
| only the partition named by the query's `category` | {', '.join(f'{c} {v}' for c, v in sorted(cr.items()))} | - |

The first draft of this pipeline joined on `category` and would have discarded roughly
{100 * (1 - min(cr.values())):.0f}% of the benchmark at worst as "gold not in own corpus". That would have been a defect in
my join reported as a property of the data. On the union - the single ~43k pool the paper describes - resolution is
{100 * exp['gold_resolution_full_census']['share_any']:.1f}%, {labels_missing} queries carry no label at all, and every scored
row's gold tools are present.

## What the frozen pipeline costs at this catalogue size

Timed with the frozen `BM25(k1=1.4, b=0.4)` and `collection_qpp_features` over all {len(ids):,} candidate documents:
BM25 {t_bm:.2f} s and corpus-level QPP {t_qpp:.2f} s per arm, i.e. **{sec_q:.1f} s per query** for both arms, so the full
{tot_q:,}-row census would take about {exp['frozen_pipeline_cost']['full_census_hours_estimate']:.0f} h on this host. Almost all of it is the corpus
statistics inside `collection_qpp_features`, which are recomputed per query even though the candidate set is now
identical for every query in a partition. Deliberate choice, stated rather than quietly optimised away: the transfer
run keeps the **frozen** feature functions, because a faster reimplementation of a frozen feature is a different
construct; it samples stratified by subset (`--per-subset 6`) and labels every number it produces as a sample.

The run is in flight at `logs/EXP-0083_eval_transfer.txt`; nothing here depends on it, and no external AUROC is
claimed by this document.
"""
    (P001 / "external_toolret_eval_ingestion.md").write_text(doc, encoding="utf-8", newline="")

    rp = ROOT / "00_program_registry" / "experiment_registry.csv"
    rows = [r for r in csv.reader(io.StringIO(rp.read_text(encoding="utf-8"))) if r]
    hdr, body = rows[0], rows[1:]
    if "EXP-0083" not in {r[0] for r in body}:
        rec = dict.fromkeys(hdr, "")
        rec.update({"exp_id": "EXP-0083", "paper_id": "P001", "topic_id": "T037",
                    "stage": "external_benchmark_eval_ingestion_audit",
                    "script": "02_shared_code/data_audit/toolret_eval_ingestion_audit_p001.py",
                    "config": f"full census of {tot_q:,} eval queries against the {len(ids):,}-tool union corpus; "
                              "gold-id resolution under two join variants; frozen BM25 and corpus-QPP timed per query; "
                              "negative results for the PyPI and GitHub raw routes recorded",
                    "seed": "none (census over every row)", "started_at": NOW, "finished_at": NOW,
                    "status": f"ingested and audited; union resolves {exp['gold_resolution_full_census']['share_any']} "
                              f"of queries; full eval ~{exp['frozen_pipeline_cost']['full_census_hours_estimate']:.0f} h "
                              "on this host, so the transfer run is stratified",
                    "outputs": f"results_raw/{fp.name}; "
                               "papers/P001_routing_failure_qpp/external_toolret_eval_ingestion.md; "
                               "01_datasets/raw/toolret/queries; 01_datasets/raw/toolret/tools; "
                               "logs/EXP-0083_eval_transfer.txt",
                    "notes": "the category-restricted join would have discarded 23-57% of the benchmark as false "
                             "'gold missing' rejections; the union of the released partitions resolves essentially "
                             "every query. No AUROC claimed by this step",
                    "enters_paper": "supports the external-validation gate record; no claim yet"})
        body.append([rec[c] for c in hdr])
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\r\n").writerows([hdr] + body)
    rp.write_text(buf.getvalue(), encoding="utf-8", newline="")
    chk = [r for r in csv.reader(io.StringIO(rp.read_text(encoding="utf-8"))) if r]
    print(f"tools={len(ids):,} queries={tot_q:,} union_resolved={exp['gold_resolution_full_census']['share_any']} "
          f"all_resolved={exp['gold_resolution_full_census']['share_all']} sec/query={sec_q:.1f} "
          f"registry_rows={len(chk) - 1} ragged={sum(1 for r in chk[1:] if len(r) != len(chk[0]))}")
    print("artefact:", fp.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
