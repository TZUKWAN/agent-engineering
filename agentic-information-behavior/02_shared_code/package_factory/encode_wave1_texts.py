"""EXP-0120: encode the wave-1 substrate with a locally-run pretrained encoder (no API, no training).

T109 ("when semantic and lexical relevance conflict") and T110 (predicate-argument fit over and above text
similarity) both need a *distributional* relevance score that is not BM25. The programme's rule is that a pretrained
component may run locally but no inference API may be called, and EXP-0062 already established the recipe: the
unmodified `sentence-transformers/all-MiniLM-L6-v2` weights, loaded from the local HF cache, encoding the R2 "prose"
rendering (query text as written; document = name words + description + "Parameters: ..." prose).

This script does the encoding only. It writes an aligned key list and a float32 matrix that `wave_lib.VectorIndex`
reads; analysis never imports sentence-transformers, so the six packages share one representation and one cost.

Run with the interpreter that has the encoder installed:
    G:/刘俊琦/AGENT ENGINEERING/.venv_e0062/Scripts/python.exe \
        02_shared_code/package_factory/encode_wave1_texts.py
"""
from __future__ import annotations

import json
import os
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = next(a for a in (HERE, *HERE.parents) if (a / "00_program_registry").is_dir())
os.environ.setdefault("HF_HUB_OFFLINE", "1")            # the weights are cached; a network call here would be a bug
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
sys.path.insert(0, str(HERE))
import numpy as np                                        # noqa: E402
import wave_lib as W                                      # noqa: E402

MODEL = "sentence-transformers/all-MiniLM-L6-v2"
BATCH = 256
# Dense-arm sample and render length, fixed before any conflict set or AUROC was computed. The first attempt encoded
# all 24,000 queries and 169,203 candidate documents; documents here are tool descriptions that often carry whole
# source files, and after 22 minutes and 14 GB of RSS the run had produced nothing measurable. The dense arm is
# therefore a seeded subsample of 2,000 queries per config with renders truncated to 1,200 characters, and the
# truncation is part of the reported rendering rather than a silent clip.
QUERY_CAP_PER_CONFIG = 2000
MAX_CHARS = 1200


def clip(s: str) -> str:
    s = str(s or "")
    return s if len(s) <= MAX_CHARS else s[:MAX_CHARS]


def render_query(q: str) -> str:
    return str(q or "").strip()


def render_doc(name: str, desc: str, params: list) -> str:
    words = " ".join(str(name or "").replace("-", " ").replace("_", " ").split())
    p = " ".join(str(x) for x in (params or []))
    return clip((words + ". " + str(desc or "").strip() + (" Parameters: " + p if p else "")).strip())


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    import pandas as pd
    t0 = time.time()
    d = W.load_routing(cfgs=W.CONFIGS, bucket="dev")
    d = d[d["subset_name"].astype(str).str.contains("single-turn-original", na=False)]
    import random
    keep = []
    for cfg, g in d.groupby("cfg"):
        idx = sorted(random.Random(W.SEED).sample(range(len(g)), min(QUERY_CAP_PER_CONFIG, len(g))))
        keep.append(g.iloc[idx])
    d = pd.concat(keep, ignore_index=True)
    qtexts, qkeys, doctexts, dockeys = [], [], [], []
    for r in d.itertuples(index=False):
        ent = W.read_catalog(r.catalog_json, r.n_candidates, r.query_id)
        t = clip(render_query(r.question))
        qkeys.append(W.text_sha("Q|" + t)); qtexts.append(t)
        for i, e in enumerate(ent):
            dt = render_doc(e["name"], e["desc"], e["params"])
            dockeys.append(W.text_sha(f"D|{r.query_id}|{i}|" + dt)); doctexts.append(dt)
    print(f"[exp0120] to encode: {len(qtexts)} queries, {len(doctexts)} documents "
              f"(cap={QUERY_CAP_PER_CONFIG}/config, MAX_CHARS={MAX_CHARS})", flush=True)
    from sentence_transformers import SentenceTransformer
    import torch
    torch.set_num_threads(max(1, os.cpu_count() or 4))
    m = SentenceTransformer(MODEL, device="cpu")
    m.max_seq_length = 256

    def enc(texts, tag):
        out = m.encode(texts, batch_size=BATCH, convert_to_numpy=True, normalize_embeddings=True,
                       show_progress_bar=False)
        print(f"  {tag}: {out.shape} at {time.time() - t0:.0f}s", flush=True)
        return out.astype(np.float32)

    qv, dv = enc(qtexts, "queries"), enc(doctexts, "documents")
    (W.PROCES / "wave1_encoder_R2_prose_q_keys.jsonl").write_text(
        "\n".join(qkeys), encoding="utf-8")
    (W.PROCES / "wave1_encoder_R2_prose_d_keys.jsonl").write_text(
        "\n".join(dockeys), encoding="utf-8")
    np.save(W.PROCES / "wave1_encoder_R2_prose_q.npy", qv)
    np.save(W.PROCES / "wave1_encoder_R2_prose_d.npy", dv)
    art = {"exp_id": "EXP-0120", "seed": W.SEED, "started_at": W.now(), "model": MODEL,
           "unmodified": True, "rendering": "R2 prose (query as written; doc = name words + description + "
                                            "'Parameters: ...')",
           "offline": {"HF_HUB_OFFLINE": os.environ.get("HF_HUB_OFFLINE"),
                       "TRANSFORMERS_OFFLINE": os.environ.get("TRANSFORMERS_OFFLINE")},
           "n_query_vectors": int(len(qkeys)), "n_doc_vectors": int(len(dockeys)),
           "dense_arm_sample": {"queries_per_config": QUERY_CAP_PER_CONFIG,
                                "max_chars_per_render": MAX_CHARS,
                                "reason": "the full-substrate attempt ran 22 min at 14 GB RSS without finishing; recorded as a deviation in the packages that use this cache"},
           "dim": int(qv.shape[1]), "normalised": True,
           "outputs": ["results_processed/wave1_encoder_R2_prose_q.npy",
                       "results_processed/wave1_encoder_R2_prose_d.npy",
                       "results_processed/wave1_encoder_R2_prose_q_keys.jsonl",
                       "results_processed/wave1_encoder_R2_prose_d_keys.jsonl"],
           "run_cost": {"wallclock_sec": round(time.time() - t0, 1), "batch": BATCH,
                        "threads": int(torch.get_num_threads()), "python": sys.version.split()[0],
                        "device": "cpu"},
           "finished_at": W.now()}
    p = W.write_raw("EXP-0120", "wave1_encoder_run", art)
    print(json.dumps(art["run_cost"], indent=1), "\nwrote", p.relative_to(W.ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
