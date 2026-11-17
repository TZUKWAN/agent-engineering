"""EXP-0018: a split that no catalogue can straddle (protocol amendment D13), added as `split_v6`.

EXP-0017 measured that the published prompt_id-grouped split lets one row's CANDIDATE CATALOGUE appear
on both sides: 63.7-88.1% of test rows share their exact catalogue with at least one dev row
(498-887 distinct catalogues span the boundary), and grouping the development cross-validation by
catalogue fingerprint costs up to 0.111 AUROC. Since every collection-aware QPP feature is a function of
the catalogue, a repeated catalogue is repeated information about the competitive situation, whether or
not the prompt text repeats - so the published test AUROC is an upper bound on generalisation to unseen
catalogues.

The fix is a joint grouping: build connected components over the bipartite relation
    row -- catalogue fingerprint,   row -- prompt_id
and assign WHOLE components to dev or test by md5(component id). No catalogue and no prompt can then
appear on both sides. Components are hashed rather than greedily packed, so the assignment stays
deterministic and independent of row order.

The new assignment is written as an additional column `split_v6`; `split` is left untouched so every
already-published artifact remains readable and byte-comparable.

    python build_catalog_disjoint_split.py

Outputs results_raw/EXP0018_catalog_disjoint_split_*.json and rewrites
01_datasets/processed/routing_<cfg>.parquet with the extra column (row set and digest unchanged).
"""

from __future__ import annotations

import hashlib
import json
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PROC = ROOT / "01_datasets" / "processed"
OUT = ROOT / "results_raw"
MAN = ROOT / "01_datasets" / "manifests"
CONFIGS = ["OSS", "Qwen3", "Kimi-K2"]
DEV_THRESHOLD = 700          # md5 % 1000 < 700 -> dev, matching the published ratio
K = 3


def fp_of(catalog_json: str) -> str:
    cat = json.loads(catalog_json)
    return hashlib.sha1("|".join(sorted(d["n"] for d in cat)).encode()).hexdigest()[:16]


def main() -> int:
    t0 = time.time()
    anchor = json.loads((MAN / "routing_sample_identity.json").read_text(encoding="utf-8"))["configs"]
    summary = {}
    for cfg in CONFIGS:
        path = PROC / f"routing_{cfg}.parquet"
        df = pd.read_parquet(path)
        before = hashlib.sha256("|".join(sorted(df.uuid.astype(str))).encode()).hexdigest()[:16]
        if before != anchor[cfg]["uuid_digest"]:
            raise SystemExit(f"[{cfg}] refusing to touch a sample that is not the published one "
                             f"({before} != {anchor[cfg]['uuid_digest']})")

        df = df.assign(fp=[fp_of(s) for s in df.catalog_json])
        # --- union-find over catalogue ids and prompt ids, encoded as distinct key namespaces
        parent: dict[str, str] = {}

        def find(x):
            parent.setdefault(x, x)
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a, b):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[rb] = ra

        for c, p in zip(df.fp, df.prompt_id):
            union("C:" + str(c), "P:" + str(p))
        comp = np.array([find("C:" + str(c)) for c in df.fp])
        df["component"] = [hashlib.sha1(str(x).encode()).hexdigest()[:16] for x in comp]
        df["split_v6"] = ["dev" if int(hashlib.md5(c.encode()).hexdigest(), 16) % 1000 < DEV_THRESHOLD
                          else "test" for c in df.component]

        dv, ts = df[df.split_v6 == "dev"], df[df.split_v6 == "test"]
        overlap_fp = len(set(dv.fp) & set(ts.fp))
        overlap_pid = len(set(dv.prompt_id) & set(ts.prompt_id))
        if overlap_fp or overlap_pid:
            raise SystemExit(f"[{cfg}] v6 split is not disjoint: {overlap_fp} catalogues, "
                             f"{overlap_pid} prompts straddle")
        sub_dv = dv[dv.n_candidates > K]
        summary[cfg] = {
            "rows": int(len(df)), "uuid_digest_unchanged": True,
            "components": int(df.component.nunique()),
            "distinct_catalogues": int(df.fp.nunique()), "distinct_prompts": int(df.prompt_id.nunique()),
            "largest_component_rows": int(df.component.value_counts().iloc[0]),
            "median_component_rows": float(df.component.value_counts().median()),
            "dev_rows": int(len(dv)), "test_rows": int(len(ts)),
            "dev_share": round(float(len(dv) / len(df)), 4),
            "dev_rows_informative_n_gt_3": int(len(sub_dv)),
            "test_rows_informative_n_gt_3": int(len(ts[ts.n_candidates > K])),
            "fail_at_3_dev_v6": round(float(sub_dv.fail_at_3.mean()), 4),
            "fail_at_3_test_v6": round(float(ts[ts.n_candidates > K].fail_at_3.mean()), 4),
            "catalogues_straddling_v6": overlap_fp, "prompts_straddling_v6": overlap_pid,
            "catalogues_straddling_published_split": int(
                len(set(df[df.split == "dev"].fp) & set(df[df.split == "test"].fp))),
            "test_rows_sharing_catalogue_with_dev_published": int(
                df[(df.split == "test")].fp.isin(set(df[df.split == "dev"].fp)).mean() * len(df[df.split == "test"])),
        }
        df.drop(columns=["fp"]).to_parquet(path, index=False)
        print(f"[{cfg}] v6 dev={summary[cfg]['dev_rows']} test={summary[cfg]['test_rows']} "
              f"| informative dev={summary[cfg]['dev_rows_informative_n_gt_3']} "
              f"test={summary[cfg]['test_rows_informative_n_gt_3']} "
              f"| straddling catalogues: published "
              f"{summary[cfg]['catalogues_straddling_published_split']} -> v6 0")

    res = {"exp_id": "EXP-0018", "stage": "protocol_amendment_D13_catalog_disjoint_split",
           "dev_threshold_md5_mod_1000": DEV_THRESHOLD, "seed_note": "deterministic md5 hash, no RNG",
           "grouping": "connected components over (catalogue fingerprint <-> prompt_id)",
           "written_as_column": "split_v6 (published `split` left untouched)",
           "configs": summary, "test_split_read": False,
           "runtime_sec": round(time.time() - t0, 1),
           "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    p = OUT / f"EXP0018_catalog_disjoint_split_{time.strftime('%Y%m%dT%H%M%S')}.json"
    p.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))
    print("wrote", p.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
