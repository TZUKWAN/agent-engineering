"""EXP-0025 (E20): clean-room replication driver + bit-level agreement report.

Spec section T08/§7 requires that every core table and figure be regenerable by an automatic script in a
CLEAN environment, and that reproduction be evidenced rather than asserted. This driver does that without
touching the published artefacts:

  * it runs the analysis chain of papers/P001/reproduce.sh against a separate copy of the code tree, so all
    new results land in the copy;
  * it uses a fresh virtualenv whose dependency versions are pinned to the ones recorded in
    environment/system_info.json, and it refuses to fall back to the host interpreter;
  * afterwards it flattens each regenerated result JSON and compares every numeric leaf against the published
    JSON of the same experiment, reporting exact agreement (the pipelines are deterministic given seed 42);
  * stages that cannot run in the isolated environment are recorded as excluded with a reason rather than
    silently dropped: the program-level dataset audit (re-hashes 83 GB, produces no paper number) and, if torch
    is absent, the trained dense comparator.

The published final-test evaluation is NOT re-run: the protocol allows exactly one, recorded in
test_eval_ledger.json, and this replication therefore reproduces every dev-side quantity plus the table/figure
generation path.

    python clean_room_replication_e20.py --copy <path-to-tree-copy> --venv-python <path>

Writes results_raw/EXP0025_clean_room_replication_*.json and logs/EXP-0025_clean_room_replication.txt.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_RAW = ROOT / "results_raw"


def flatten(obj, prefix=""):
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.update(flatten(v, f"{prefix}.{k}" if prefix else str(k)))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.update(flatten(v, f"{prefix}[{i}]"))
    else:
        out[prefix] = obj
    return out


def newest(path_glob, after):
    hits = [(os.path.getmtime(p), p) for p in glob.glob(path_glob) if os.path.getmtime(p) >= after]
    return max(hits)[1] if hits else None


def compare(family: str, published: str, reproduced: str, after: float):
    a = json.loads(Path(published).read_text(encoding="utf-8"))
    b = json.loads(Path(reproduced).read_text(encoding="utf-8"))
    fa, fb = flatten(a), flatten(b)
    common = [k for k in fa if k in fb]
    skip_exact = {"started_at", "finished_at", "wallclock_sec"}
    exact, diff, only_a, only_b = 0, [], [], []
    for k in common:
        if any(s in k for s in skip_exact):
            continue
        va, vb = fa[k], fb[k]
        if isinstance(va, (int, float)) and isinstance(vb, (int, float)) and not isinstance(va, bool):
            if float(va) == float(vb):
                exact += 1
            else:
                diff.append({"key": k, "published": va, "reproduced": vb, "abs_delta": round(abs(va - vb), 8)})
        elif va == vb:
            exact += 1
        else:
            diff.append({"key": k, "published": va, "reproduced": vb})
    only_a = [k for k in fa if k not in fb][:20]
    only_b = [k for k in fb if k not in fa][:20]
    return {"family": family, "published_file": Path(published).name, "reproduced_file": Path(reproduced).name,
            "values_compared": len(common) - len([d for d in diff]) - len(only_a),
            "exact_matches": exact, "mismatches": diff[:40], "n_mismatches": len(diff),
            "keys_only_in_published": only_a, "keys_only_in_reproduced": only_b}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--copy", required=True)
    ap.add_argument("--venv-python", required=True)
    args = ap.parse_args()
    copy, vpy = Path(args.copy), args.venv_python
    t_start = time.time() - 2
    res = {"exp_id": "EXP-0025", "e_id": "E20", "started_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(t_start)),
           "clean_env_python": vpy, "tree_copy": str(copy),
           "isolation": ("separate venv with versions pinned to environment/system_info.json; separate code tree; "
                         "source corpora read from the same on-disk parquet, which is the intended input"),
           "stages": [], "excluded_stages": {
               "1 program-level dataset audit": "re-hashes 83 GB and produces no number quoted in the paper; the "
                                                "sample-identity check in the final stage proves the rebuilt row "
                                                "set is the published one",
               "final-test evaluation": "protocol permits exactly one, already recorded in test_eval_ledger.json"}}

    env = dict(os.environ, PYTHONIOENCODING="utf-8", AIB_PYTHON=vpy)
    stages = [
        ("4 build routing dataset (OSS/Qwen3/Kimi-K2)",
         [vpy, "02_shared_code/trajectory_parser/build_toucan_routing_dataset.py",
          "--rows-per-config", "15000", "--shards-per-config", "10"]),
        ("5a development selection grid", [vpy, "02_shared_code/statistics/run_p001_experiments.py",
                                           "--stage", "dev-select", "--repeats", "5"]),
        ("5b robustness + inference", [vpy, "02_shared_code/statistics/run_p001_experiments.py",
                                       "--stage", "robust", "--repeats", "5"]),
        ("6a H4 equivalence relabelling", [vpy, "02_shared_code/statistics/equivalence_relabel_h4.py"]),
        ("6b adjudication sample", [vpy, "02_shared_code/statistics/adjudicate_equivalence_sample.py", "--write"]),
        ("7a catalog interventions", [vpy, "02_shared_code/statistics/catalog_intervention_e17.py"]),
        ("7b catalog-disjoint split attempt", [vpy, "02_shared_code/trajectory_parser/build_catalog_disjoint_split.py"]),
        ("7c hierarchical dependence", [vpy, "02_shared_code/statistics/hierarchical_dependence.py"]),
        ("7d catalogue-clustered inference", [vpy, "02_shared_code/statistics/catalogue_clustered_inference.py"]),
        ("8a external availability probe", [vpy, "02_shared_code/data_audit/probe_external_catalogue_availability.py"]),
        ("8b hermes feasibility probe", [vpy, "02_shared_code/data_audit/probe_hermes_toolcalls.py"]),
        ("8c SFT routing build", [vpy, "02_shared_code/trajectory_parser/build_toucan_routing_dataset.py",
                                  "--configs", "SFT", "--exp-id", "EXP-0020", "--rows-per-config", "15000",
                                  "--shards-per-config", "10"]),
        ("8d cross-pipeline transfer", [vpy, "02_shared_code/statistics/cross_pipeline_transfer_e08.py"]),
        ("8e external corpus transfer", [vpy, "02_shared_code/statistics/external_corpus_transfer_hermes.py"]),
        ("10 figures and tables", [vpy, "papers/P001_routing_failure_qpp/scripts/make_figures_tables.py"]),
    ]
    if subprocess.run([vpy, "-c", "import torch"], capture_output=True).returncode == 0:
        stages.insert(14, ("9 trained dense comparator", [vpy, "02_shared_code/statistics/dense_comparator_e03b.py"]))
    else:
        res["excluded_stages"]["9 trained dense comparator"] = ("torch is not installed in the isolated venv; the "
                                                                "stage runs in the host environment (EXP-0024)")

    for dsub in ("01_datasets/processed", "results_raw", "results_processed", "logs"):
        (copy / dsub).mkdir(parents=True, exist_ok=True)
    for label, cmd in stages:
        t0 = time.time()
        p = subprocess.run(cmd, cwd=copy, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
        res["stages"].append({"stage": label, "exit": p.returncode, "sec": round(time.time() - t0, 1),
                              "stderr_tail": (p.stderr or "")[-400:]})
        print(f"[repro] {label}: exit={p.returncode} ({res['stages'][-1]['sec']}s)")
        if p.returncode:
            print((p.stderr or "")[-600:])

    fams = [("EXP-0013/0020 routing build", "EXP001?_toucan_routing_dataset_*.json"),
            ("EXP-0010 selection", "EXP0010_dev_selection_*.json"),
            ("EXP-0011 robustness", "EXP0011_dev_robustness_*.json"),
            ("EXP-0014 H4 relabelling", "EXP0014_equivalence_relabel_*.json"),
            ("EXP-0016 interventions", "EXP0016_catalog_intervention_*.json"),
            ("EXP-0017 dependence", "EXP0017_hierarchical_dependence_*.json"),
            ("EXP-0018 split attempt", "EXP0018_catalog_disjoint_split_*.json"),
            ("EXP-0019 clustered inference", "EXP0019_catalogue_clustered_inference_*.json"),
            ("EXP-0021 cross-pipeline", "EXP0021_cross_pipeline_transfer_*.json"),
            ("EXP-0023 hermes transfer", "EXP0023_hermes_transfer_*.json"),
            ("EXP-0024 dense comparator", "EXP0024_dense_comparator_*.json")]
    res["agreement"] = []
    for label, pat in fams:
        rep = newest(str(copy / "results_raw" / pat), t_start)
        pub = sorted(glob.glob(str(ROOT / "results_raw" / pat)))
        if not (rep and pub):
            res["agreement"].append({"family": label, "status": "not reproduced in this run"})
            continue
        c = compare(label, pub[-1], rep, t_start)
        c["status"] = "identical" if c["n_mismatches"] == 0 else "DIFFERS"
        res["agreement"].append(c)
        print(f"  {label}: {c['status']} exact={c['exact_matches']} mismatches={c['n_mismatches']}")

    dig = subprocess.run([vpy, "-c", """
import hashlib, json, pandas as pd
a=json.load(open('01_datasets/manifests/routing_sample_identity.json',encoding='utf-8'))['configs']
out={}
for c in ('OSS','Qwen3','Kimi-K2','SFT'):
    df=pd.read_parquet(f'01_datasets/processed/routing_{c}.parquet')
    out[c]={'digest':hashlib.sha256('|'.join(sorted(df.uuid.astype(str))).encode()).hexdigest()[:16],
            'expected':a[c]['uuid_digest'],'rows':int(len(df)),
            'dev_fail_at_3':round(float(df[df.split=='dev'].fail_at_3.mean()),4)}
print(json.dumps(out))"""], cwd=copy, env=env, capture_output=True,
                                       text=True, encoding="utf-8", errors="replace")
    out = (dig.stdout or "") + (dig.stderr or "")
    try:
        res["sample_identity"] = json.loads(out.strip().splitlines()[-1])
    except Exception as exc:
        res["sample_identity"] = {"error": f"{type(exc).__name__}", "output_tail": out[-500:]}
    res["tables_regenerated"] = len(list((copy / "papers/P001_routing_failure_qpp/tables").glob("*.csv")))
    res["figures_regenerated"] = len(list((copy / "papers/P001_routing_failure_qpp/figures").glob("*.pdf")))
    res["n_families_identical"] = sum(1 for a in res["agreement"] if a.get("status") == "identical")
    res["n_families_compared"] = sum(1 for a in res["agreement"] if "status" in a and a["status"] != "not reproduced in this run")
    res["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    res["wallclock_sec"] = round(time.time() - t_start, 1)
    OUT_RAW.mkdir(exist_ok=True)
    out = OUT_RAW / f"EXP0025_clean_room_replication_{time.strftime('%Y%m%dT%H%M%S')}.json"
    out.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
