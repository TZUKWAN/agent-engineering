"""Program-level dataset audit (spec sections T04.01-T04.05).

Produces real, reproducible evidence for every external agent-trajectory
dataset: HF revision + per-file SHA256 + download timestamp parsed from the
local Hugging Face cache, license from the dataset card, full-row counts from
parquet footers, and a seeded random sample audited for schema, null ratio,
cardinality, list/turn distributions, source/model/tool/task distributions and
exact-duplicate rate.

Nothing here calls a model API; every number is read off the local files.

    python audit_datasets.py [--out DIR] [--rows N] [--shards K] [--only NAME]

Exit code is non-zero if any dataset fails to audit, so reproduce.sh can gate on it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import sys
import time
import traceback
from collections import Counter
from pathlib import Path

import pyarrow.parquet as pq

SEED = 42
DATA_ROOT = Path(r"G:/刘俊琦/AGENT ENGINEERING/MATLABINTOKEN/datasets")

# name -> HF repo id + where the parquet/jsonl actually live locally
DATASETS: dict[str, dict] = {
    "Toucan-1.5M": {
        "repo": "Agent-Ark/Toucan-1.5M",
        "rel": "Agent-Ark/Toucan-1.5M",
        "configs": {c: f"{c}/*.parquet" for c in ["OSS", "Qwen3", "Kimi-K2", "SFT"]},
        "key_text_col": "question",
        "outcome_cols": ["target_tools"],
        "categorical_cols": ["subset_name", "uuid"],
        "json_list_cols": ["available_tools", "messages"],
    },
    "AgentTrove": {
        "repo": "open-thoughts/AgentTrove",
        "rel": "open-thoughts/AgentTrove",
        "configs": {"train": "data/*.parquet"},
        "key_text_col": "instruction",
        "outcome_cols": ["result", "judgment", "verifier_output", "ground_truth"],
        "categorical_cols": ["agent", "model", "original_source", "trace_source", "task", "split"],
        "json_list_cols": ["conversations"],
    },
    "SWE-ZERO-12M": {
        "repo": "AlienKevin/SWE-ZERO-12M-trajectories",
        "rel": "AlienKevin/SWE-ZERO-12M-trajectories",
        "configs": {"train": "data/*.parquet"},
        "key_text_col": None,
        "outcome_cols": ["exit_status"],
        "categorical_cols": ["instance_id", "repo", "trajectory_format"],
        "json_list_cols": ["messages"],
        "numeric_cols": ["duration_sec"],
    },
    "AgentBank": {
        "repo": "Solaris99/AgentBank",
        "rel": "Solaris99/AgentBank",
        "configs": None,  # discovered from subdirectories
        "key_text_col": None,
        "outcome_cols": [],
        "categorical_cols": ["id"],
        "json_list_cols": ["conversations"],
    },
    "hermes-agent-reasoning-traces": {
        "repo": "lambda/hermes-agent-reasoning-traces",
        "rel": "lambda/hermes-agent-reasoning-traces",
        "configs": {"default": "data/train-*.parquet",
                    "glm-5.1": "data/glm-5.1/*.parquet",
                    "kimi": "data/kimi/*.parquet"},
        "key_text_col": "task",
        "outcome_cols": [],
        "categorical_cols": ["id", "category", "subcategory", "task"],
        "json_list_cols": ["conversations", "tools"],
    },
    "code-act": {
        "repo": "xingyaoww/code-act",
        "rel": "xingyaoww/code-act",
        "configs": {"codeact": "data/codeact-*.parquet", "general": "data/general-*.parquet"},
        "key_text_col": None,
        "outcome_cols": [],
        "categorical_cols": ["id"],
        "json_list_cols": ["conversations"],
    },
    "AgentInstruct": {
        "repo": "zai-org/AgentInstruct",
        "rel": "zai-org/AgentInstruct",
        "configs": None,
        "key_text_col": None,
        "outcome_cols": [],
        "categorical_cols": ["id"],
        "json_list_cols": ["conversations"],
    },
    "MMAT-1M": {
        "repo": "VIS-MPU-Agent/MMAT-1M",
        "rel": "VIS-MPU-Agent/MMAT-1M",
        "configs": None,
        "jsonl": True,
        "key_text_col": None,
        "outcome_cols": [],
        "categorical_cols": [],
        "json_list_cols": ["messages"],
    },
}

LOG_LINES: list[str] = []


def log(msg: str) -> None:
    line = f"[{time.strftime('%Y-%m-%dT%H:%M:%S')}] {msg}"
    LOG_LINES.append(line)
    print(line, flush=True)


def read_hf_file_metadata(ds_dir: Path) -> dict[str, dict]:
    """Parse HF cache .metadata files: line1=git commit, line2=sha256, line3=epoch ts."""
    out: dict[str, dict] = {}
    for meta in ds_dir.rglob(".cache/huggingface/download/**/*.metadata"):
        rel = str(meta.relative_to(ds_dir / ".cache" / "huggingface" / "download"))
        rel = rel[: -len(".metadata")]
        try:
            lines = meta.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        entry = {"git_commit": lines[0].strip() if len(lines) > 0 else None,
                 "sha256": lines[1].strip() if len(lines) > 1 else None,
                 "download_ts_epoch": float(lines[2]) if len(lines) > 2 and lines[2].strip() else None}
        entry["downloaded_at"] = (time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(entry["download_ts_epoch"]))
                                  if entry["download_ts_epoch"] else None)
        out[rel.replace("\\", "/")] = entry
    return out


def read_license(ds_dir: Path) -> dict:
    """Pull the license + declared size out of the dataset card front matter."""
    info = {"license": None, "card_declared_rows": {}, "card_path": None}
    for card in [ds_dir / "README.md"] + list(ds_dir.glob("*/README.md")):
        if not card.exists():
            continue
        txt = card.read_text(encoding="utf-8", errors="replace")
        m = re.search(r"^\s*license:\s*(.+)$", txt, re.M)
        if m and not info["license"]:
            info["license"] = m.group(1).strip()
            info["card_path"] = str(card.relative_to(ds_dir))
        for cm in re.finditer(r"- config_name:\s*(\S+)", txt):
            tail = txt[cm.end(): cm.end() + 900]
            ex = re.search(r"num_examples:\s*(\d+)", tail)
            if ex:
                info["card_declared_rows"][cm.group(1)] = int(ex.group(1))
    return info


def discover_configs(ds_dir: Path, cfg) -> dict[str, str]:
    if cfg:
        return dict(cfg)
    found = {}
    for sub in sorted(p for p in ds_dir.iterdir() if p.is_dir() and p.name != ".cache"):
        for pat, name in [("*.parquet", "parquet"), ("*.jsonl", "jsonl")]:
            if list(sub.glob(pat)):
                found[sub.name] = f"{sub.name}/{pat}"
    if not found:
        for pat, name in [("*.parquet", "parquet"), ("*.jsonl", "jsonl")]:
            if list(ds_dir.glob(pat)):
                found["root"] = pat
    return found


def q_norm(s) -> str:
    """Normalize free text for duplicate detection."""
    return re.sub(r"\s+", " ", str(s or "").strip().lower())[:400]


def jsonable(v):
    if isinstance(v, (dict, list)):
        try:
            return json.dumps(v, sort_keys=True, ensure_ascii=False)[:200]
        except Exception:
            return str(v)[:200]
    return v


def sample_rows_from_shards(files: list[str], n_per_shard: int, rng: random.Random):
    """Yield rows shard by shard, reading one row group at a time.

    Full-table take() on these datasets overflows pyarrow's 32-bit string
    offsets (AgentTrove ships a multi-GB binary column), and loading a whole
    Toucan shard can exceed available RAM, so bounded row-group slices are the
    only safe access pattern here.
    """
    for path in files:
        pf = pq.ParquetFile(path)
        names = [f.name for f in pf.schema_arrow if not str(f.type).startswith(("binary", "fixed_size_binary"))]
        n_rg = pf.metadata.num_row_groups
        rg_ids = list(range(n_rg))
        rng.shuffle(rg_ids)
        got = 0
        for rg_id in rg_ids:
            if got >= n_per_shard:
                break
            try:
                rg = pf.read_row_group(rg_id, columns=names)
            except Exception:
                continue
            m = rg.num_rows
            k = min(n_per_shard - got, m)
            idx = sorted(rng.sample(range(m), k)) if m > k else list(range(m))
            rows = rg.take(idx).to_pylist()
            got += len(rows)
            yield from rows


def audit_parquet_config(files: list[str], spec: dict, row_budget: int, shard_budget: int) -> dict:
    """Row counts from footers over ALL shards; deep audit over a seeded sample."""
    res: dict = {"n_files": len(files), "total_rows_all_files": 0, "unreadable_shards": 0}
    for f in files:
        try:
            res["total_rows_all_files"] += pq.ParquetFile(f).metadata.num_rows
        except Exception:
            res["unreadable_shards"] += 1

    rng = random.Random(SEED)
    picks = sorted(files)
    if len(picks) > shard_budget:
        picks = sorted(rng.sample(picks, shard_budget))
    schema = pq.ParquetFile(picks[0]).schema_arrow
    res["schema"] = {f.name: str(f.type) for f in schema}
    res["shards_audited"] = [os.path.basename(p) for p in picks]

    cols = [f.name for f in schema]
    skipped = [c for c in cols if str(schema.field(c).type).startswith(("binary", "fixed_size_binary"))]
    if skipped:
        res["binary_columns_skipped"] = skipped
    acc = {c: {"nulls": 0, "empty_str": 0, "uniq": set(), "non_null_n": 0,
               "list_len": [], "str_len": []} for c in cols}
    text_col = spec.get("key_text_col") if spec.get("key_text_col") in cols else None
    turn_lens, role_starts, dup_stream, numeric = [], Counter(), [], {}
    total_sampled = 0

    for row in sample_rows_from_shards(picks, max(1, row_budget // max(1, len(picks))), rng):
        total_sampled += 1
        for c in cols:
            v = row.get(c)
            a = acc[c]
            if v is None:
                a["nulls"] += 1
            elif isinstance(v, str):
                if v.strip() == "" or v.strip().lower() in ("none", "null"):
                    a["empty_str"] += 1
                else:
                    a["non_null_n"] += 1
                a["str_len"].append(len(v))
                if len(a["uniq"]) < 200_000:
                    a["uniq"].add(jsonable(v))
            elif isinstance(v, list):
                a["non_null_n"] += 1
                a["list_len"].append(len(v))
                if len(a["uniq"]) < 200_000:
                    a["uniq"].add(("__list__", len(v)))
            else:
                a["non_null_n"] += 1
                if len(a["uniq"]) < 200_000:
                    a["uniq"].add(jsonable(v))
        if text_col:
            dup_stream.append(q_norm(row.get(text_col)))
        for lc in spec.get("json_list_cols", []) + ["conversations", "messages"]:
            v = row.get(lc)
            if isinstance(v, list) and v and isinstance(v[0], dict):
                turn_lens.append(len(v))
                role_starts["first:" + str(v[0].get("role") or v[0].get("from"))] += 1
                break
        for nc in spec.get("numeric_cols", []):
            v = row.get(nc)
            if isinstance(v, (int, float)):
                numeric.setdefault(nc, []).append(v)

    res["rows_audited"] = total_sampled
    res["columns"] = {}
    for c, a in acc.items():
        d = {"null_ratio": round(a["nulls"] / total_sampled, 4) if total_sampled else None,
             "empty_or_sentinel_ratio": round(a["empty_str"] / total_sampled, 4) if total_sampled else None,
             "non_empty_ratio": round(a["non_null_n"] / total_sampled, 4) if total_sampled else None,
             "unique_in_sample": len(a["uniq"]),
             "sample_dup_ratio_by_unique": round(1 - len(a["uniq"]) / total_sampled, 4)
                 if total_sampled and not a["list_len"] else None}
        if a["str_len"]:
            d["str_len_mean"] = round(sum(a["str_len"]) / len(a["str_len"]), 1)
        if a["list_len"]:
            ll = sorted(a["list_len"])
            d["list_len_mean"] = round(sum(ll) / len(ll), 2)
            d["list_len_min"] = ll[0]
            d["list_len_max"] = ll[-1]
            d["list_len_p50"] = ll[len(ll) // 2]
            d["list_len_p95"] = ll[int(len(ll) * 0.95)]
        res["columns"][c] = d

    for c in spec.get("categorical_cols", []):
        if c in cols and acc[c]["uniq"]:
            vals = list(acc[c]["uniq"])[:40]
            res.setdefault("categorical_topk", {})[c] = vals
    for c in spec.get("outcome_cols", []) + spec.get("categorical_cols", []):
        if c in cols:
            res.setdefault("label_coverage", {})[c] = res["columns"][c]["non_empty_ratio"]
    if turn_lens:
        ft = sorted(turn_lens)
        res["trajectory_turns"] = {"mean": round(sum(ft) / len(ft), 2), "min": ft[0], "max": ft[-1],
                                   "p50": ft[len(ft) // 2], "p95": ft[int(len(ft) * 0.95)]}
    if role_starts:
        res["role_start_distribution"] = role_starts.most_common(6)
    if text_col and len(dup_stream) > 50:
        uniq = len(set(dup_stream))
        res["key_text_column"] = text_col
        res["exact_dup_ratio_key_text"] = round(1 - uniq / len(dup_stream), 4)
    for nc, vs in numeric.items():
        vs = sorted(vs)
        res.setdefault("numeric_summary", {})[nc] = {
            "n": len(vs), "mean": round(sum(vs) / len(vs), 2), "min": round(vs[0], 2),
            "p50": round(vs[len(vs) // 2], 2), "max": round(vs[-1], 2)}
    return res


def audit_jsonl_config(files: list[str], spec: dict, row_budget: int) -> dict:
    res: dict = {"n_files": len(files)}
    rng = random.Random(SEED)
    total_keys: Counter = Counter()
    rows = 0
    img_missing = img_total = 0
    msg_lens: list[int] = []
    role_starts: Counter = Counter()
    dup: list[str] = []
    per_file_rows: dict[str, int] = {}
    for p in files:
        seen = 0
        with open(p, "r", encoding="utf-8", errors="replace") as fh:
            for i, line in enumerate(fh):
                seen += 1
                if i >= row_budget:
                    continue
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                rows += 1
                total_keys.update(d.keys())
                if isinstance(d.get("messages"), list):
                    msg_lens.append(len(d["messages"]))
                    role_starts["first:" + str(d["messages"][0].get("role"))] += 1
                    for m in d["messages"]:
                        if m.get("role") == "user":
                            dup.append(q_norm(m.get("content")))
                            break
                for im in d.get("images") or []:
                    img_total += 1
                    if not os.path.exists(os.path.join(os.path.dirname(p), im)):
                        img_missing += 1
        per_file_rows[os.path.basename(p)] = seen
    res["rows_audited"] = rows
    res["line_counts_per_file"] = per_file_rows
    res["total_rows_all_files"] = sum(per_file_rows.values())
    res["columns"] = {k: {"appears_in_sample": v} for k, v in total_keys.items()}
    if msg_lens:
        msg_lens.sort()
        res["trajectory_turns"] = {"mean": round(sum(msg_lens) / len(msg_lens), 2),
                                   "min": msg_lens[0], "max": msg_lens[-1],
                                   "p50": msg_lens[len(msg_lens) // 2]}
    if role_starts:
        res["role_start_distribution"] = role_starts.most_common(6)
    if img_total:
        res["image_reference"] = {"total_refs_in_sample": img_total, "missing_on_disk": img_missing,
                                  "missing_ratio": round(img_missing / img_total, 4)}
    if len(dup) > 50:
        res["exact_dup_ratio_key_text"] = round(1 - len(set(dup)) / len(dup), 4)
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path(__file__).resolve().parents[2] / "01_datasets" / "manifests"))
    ap.add_argument("--rows", type=int, default=6000)
    ap.add_argument("--shards", type=int, default=6)
    ap.add_argument("--only", default=None)
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    log(f"START dataset audit | root={DATA_ROOT} | seed={SEED} | rows_budget={args.rows} | shard_budget={args.shards}")
    assert DATA_ROOT.exists(), f"data root missing: {DATA_ROOT}"

    registry, failures = [], []
    for name, spec in DATASETS.items():
        if args.only and args.only != name:
            continue
        ds_dir = DATA_ROOT / spec["rel"]
        log(f"== {name} ({spec['repo']})")
        rec: dict = {"dataset": name, "hf_repo_id": spec["repo"], "local_path": str(ds_dir),
                     "exists": ds_dir.exists()}
        try:
            if not ds_dir.exists():
                raise FileNotFoundError(ds_dir)
            filemeta = read_hf_file_metadata(ds_dir)
            commits = sorted({m["git_commit"] for m in filemeta.values() if m["git_commit"]})
            stamps = [m["download_ts_epoch"] for m in filemeta.values() if m["download_ts_epoch"]]
            rec.update({
                "n_files_recorded": len(filemeta),
                "hf_git_revisions": ";".join(commits),
                "revision_is_single": len(commits) == 1,
                "download_first_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(min(stamps))) if stamps else None,
                "download_last_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(max(stamps))) if stamps else None,
                "local_bytes": sum(os.path.getsize(f) for f in ds_dir.rglob("*")
                                   if f.is_file() and ".cache" not in f.parts),
            })
            lic = read_license(ds_dir)
            rec["license_declared"] = lic["license"]
            rec["card_declared_rows"] = json.dumps(lic["card_declared_rows"], ensure_ascii=False)

            configs = discover_configs(ds_dir, spec.get("configs"))
            rec["configs"] = ";".join(configs)
            audit: dict = {}
            for cname, pat in configs.items():
                files = sorted(str(f) for f in ds_dir.glob(pat))
                if not files:
                    continue
                log(f"   config {cname}: {len(files)} files")
                if pat.endswith(".jsonl") or spec.get("jsonl"):
                    r = audit_jsonl_config(files, spec, args.rows)
                else:
                    r = audit_parquet_config(files, spec, args.rows, args.shards)
                audit[cname] = r
                rec["total_rows_measured"] = rec.get("total_rows_measured", 0) + r.get("total_rows_all_files", 0)
            rec["configs_with_rowcount"] = json.dumps(
                {k: v.get("total_rows_all_files", v.get("rows_audited")) for k, v in audit.items()}, ensure_ascii=False)
            (out / f"{name}.file_manifest.json").write_text(
                json.dumps(filemeta, indent=1, ensure_ascii=False), encoding="utf-8")
            (out / f"{name}.audit.json").write_text(
                json.dumps({"dataset": name, "hf_repo_id": spec["repo"], "audited_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                            "seed": SEED, "configs": audit}, indent=1, ensure_ascii=False), encoding="utf-8")
            flat = {}
            for cname, r in audit.items():
                flat[cname] = {k: r.get(k) for k in ("total_rows_all_files", "rows_audited", "trajectory_turns",
                                                     "exact_dup_ratio_key_text", "label_coverage", "image_reference",
                                                     "numeric_summary", "role_start_distribution")}
            rec["audit_summary"] = json.dumps(flat, ensure_ascii=False)
            log(f"   total_rows_measured={rec.get('total_rows_measured')}")
        except Exception as e:
            rec["error"] = f"{type(e).__name__}: {e}"
            failures.append(name)
            log(f"   !! FAILED {type(e).__name__}: {e}")
            traceback.print_exc(file=sys.stdout)
        registry.append(rec)

    import csv
    cols = ["dataset", "hf_repo_id", "exists", "license_declared", "hf_git_revisions", "revision_is_single",
            "download_first_at", "download_last_at", "n_files_recorded", "local_bytes", "configs",
            "total_rows_measured", "configs_with_rowcount", "audit_summary", "error"]
    rp = out / "dataset_registry.csv"
    with open(rp, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in registry:
            w.writerow(r)
    (out / "audit_log.txt").write_text("\n".join(LOG_LINES), encoding="utf-8")
    log(f"WROTE {rp} ({len(registry)} datasets)")
    if failures:
        log(f"FAILURES: {failures}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
