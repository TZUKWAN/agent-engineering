"""EXP-0061: is a pretrained text encoder obtainable on this machine at all? A probe, not a recollection.

P001's `final_audit.md` keeps gate G18-B open because the dense/neural baseline is missing, and says the absence is
"a policy/resource decision that must be written up as a feasibility note". Such a note has been asserted from
memory twice in this programme already (once as "no GPU", which was wrong: the machine has an RTX 3060 and the real
blockers were a CPU-only torch build and un-downloadable weights). So this probe measures each link of the chain:

  1. what is installed (torch and whether CUDA is usable; transformers / sentence_transformers / faiss presence);
  2. whether the libraries could be installed at all from the reachable index (pip --dry-run against PyPI and the
     Tsinghua mirror, no install performed);
  3. whether pretrained **weights** can be fetched, tried against every candidate host this machine might reach,
     each with a real ranged GET so a CDN/edge behaviour cannot masquerade as availability;
  4. what remains if weights are unreachable: a from-scratch encoder, which EXP-0024 already built and which the
     programme's no-inference-API boundary allows.

The output is a machine-readable record for every attempt (host, url, bytes actually read, final status), so the
feasibility note can cite results instead of adjectives. Nothing here calls a model inference API.

    python 02_shared_code/data_audit/probe_pretrained_encoder_feasibility_p001.py
"""
from __future__ import annotations

import json, pathlib, subprocess, sys, time

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "results_raw"
PROC = ROOT / "results_processed"
TIMEOUT = 12

# one small file per host family: a config.json or a tokenizer, i.e. the cheapest artefact that proves the
# weight store is reachable. Ranged GET so we see the leading bytes of the real object, not an HTML error page.
CANDIDATES = [
    ("huggingface.co", "https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/resolve/main/config.json"),
    ("cdn-lfs.huggingface.co", "https://cdn-lfs.huggingface.com/repos/sentence-transformers/all-MiniLM-L6-v2/"
                               "f2f4b607f0e23efe7c084c9c7e2c0d4d1d9a8d0d1c1b1a191817161514131211?h=main"),
    ("hf-mirror.com", "https://hf-mirror.com/sentence-transformers/all-MiniLM-L6-v2/resolve/main/config.json"),
    ("modelscope.cn", "https://www.modelscope.cn/models/damo/nlp_csanmt_translation_en2zh/resolve/master/"
                      "configuration.json"),
    ("cas-server.onnx.ai", "https://cas-bridge.onnx.ai/model/miniLM"),
    ("raw.githubusercontent.com", "https://raw.githubusercontent.com/UKPLab/sentence-transformers/master/README.md"),
    ("pypi.org (json)", "https://pypi.org/pypi/sentence-transformers/json"),
    ("tsinghua-pypi (simple)", "https://pypi.tuna.tsinghua.edu.cn/simple/sentence-transformers/"),
]


def curl(url, range_header=None, tries=2):
    for k in range(tries):
        args = ["curl", "-sS", "-L", "--max-time", str(TIMEOUT), "-o", "-|head -c 400".split("|")[0],
                "-w", "\n__META__%{http_code}|%{size_download}|%{url_effective}"]
        if range_header:
            args += ["-H", "Range: bytes=0-399"]
        p = subprocess.run(args + [url], capture_output=True, text=True, encoding="utf-8", errors="replace")
        meta = ""
        body = p.stdout
        if "__META__" in p.stdout:
            body, _, meta = p.stdout.rpartition("__META__")
        if p.returncode == 0 and meta:
            code, size, eff = (meta.split("|") + ["", ""])[:3]
            return {"http_code": code, "bytes_read": int(float(size or 0)), "url_effective": eff.strip(),
                    "first_bytes": body[:200].strip().replace("\n", " "), "curl_error": None}
        time.sleep(1.5)
    return {"http_code": None, "bytes_read": 0, "url_effective": url, "first_bytes": "",
            "curl_error": f"exit={p.returncode} {p.stderr.strip()[:160]}"}


def probe_installed():
    out = {}
    import importlib.util as iu
    for m in ("torch", "transformers", "sentence_transformers", "faiss", "huggingface_hub", "numpy"):
        out[m + "_importable"] = iu.find_spec(m) is not None
    try:
        r = subprocess.run([sys.executable, "-c",
                            "import torch,json;print(json.dumps({'v':torch.__version__,'cuda_build':torch.version.cuda"
                            " is not None,'cuda_available':torch.cuda.is_available()}))"],
                           capture_output=True, text=True, timeout=180)
        out["torch"] = json.loads(r.stdout.strip().splitlines()[-1]) if r.stdout.strip() else {"stderr": r.stderr[:200]}
    except Exception as e:
        out["torch"] = {"error": type(e).__name__}
    try:
        import psutil
        out["ram_gb"] = round(psutil.virtual_memory().total / 2**30, 1)
    except Exception:
        pass
    return out


def probe_installability():
    """pip --dry-run: would the packages resolve from the reachable index? Nothing is installed."""
    res = {}
    for name, spec in (("pypi", ["sentence-transformers==3.0.1"]), ("tsinghua", ["sentence-transformers==3.0.1"])):
        idx = ("https://pypi.org/simple/" if name == "pypi"
               else "https://pypi.tuna.tsinghua.edu.cn/simple/")
        try:
            p = subprocess.run([sys.executable, "-m", "pip", "install", "--dry-run", "--quiet", "--no-input",
                                "--no-deps", "--index-url", idx, "--disable-pip-version-check"] + spec,
                               capture_output=True, text=True, timeout=90)
            res[name] = {"returncode": p.returncode, "would_install": [l.strip() for l in p.stdout.splitlines()
                                                                       if l.strip().startswith("Would install")][:1],
                         "stderr_tail": p.stderr.strip()[-200:]}
        except Exception as e:
            res[name] = {"error": type(e).__name__}
    return res


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    res = {"exp_id": "EXP-0061", "paper_id": "P001", "gate_item": "G18-B dense-baseline feasibility",
           "policy_note": "no model inference API is called; this probes obtainability of weights only",
           "started_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    res["installed"] = probe_installed()
    print("  installed:", json.dumps(res["installed"], ensure_ascii=False)[:260], flush=True)
    res["hosts"] = {}
    for host, url in CANDIDATES:
        r = curl(url, range_header=True)
        ok = bool(r["http_code"]) and str(r["http_code"])[0] == "2" and r["bytes_read"] > 0
        r["usable_weights_channel"] = ok
        res["hosts"][host] = r
        print(f"  {host:26} http={str(r['http_code']):>5} bytes={r['bytes_read']:5d} "
              f"{'USABLE' if ok else r['curl_error'] or r['http_code']}")
        time.sleep(1.0)
    res["installability"] = probe_installability()  # --no-deps: the question is whether the wheel is fetchable, not whether pip can solve a whole environment
    print("  installability:", json.dumps(res["installability"], ensure_ascii=False)[:260])

    chan = [h for h, v in res["hosts"].items() if v["usable_weights_channel"]
            and "pypi" not in h and "github" not in h.replace("raw.githubusercontent.com", "")]
    libs_ok = any(v.get("returncode") == 0 for v in res["installability"].values())
    res["verdict"] = ("PRETRAINED_ENCODER_OBTAINABLE" if chan else
                      "LIBRARIES_ONLY_NO_WEIGHTS" if libs_ok else "NOT_OBTAINABLE")
    res["consequence_for_p001"] = {
        "PRETRAINED_ENCODER_OBTAINABLE": "run a pretrained-encoder comparator in P001's dev protocol; G18-B's "
                                         "missing-baseline item can then be closed by a run, not by a note",
        "LIBRARIES_ONLY_NO_WEIGHTS": "the block is the weight store, not the toolchain; P001's from-scratch dense "
                                     "comparator (EXP-0024) is the strongest admissible baseline, and G18-B stays "
                                     "open as a documented resource limit rather than an unexplored one",
        "NOT_OBTAINABLE": "no dense learned comparator beyond the from-scratch one is admissible here; state it as a "
                          "resource boundary with the probe as evidence",
    }[res["verdict"]]
    res["wallclock_sec"] = round(time.time() - t0, 1)
    res["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    stamp = time.strftime("%Y%m%dT%H%M%S")
    (OUT / f"EXP0061_pretrained_encoder_feasibility_{stamp}.json").write_text(
        json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8", newline="")
    with open(PROC / "EXP0061_host_probe.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv_writer = __import__("csv").writer(fh)
        w.writerow(["host", "http_code", "bytes_read", "usable_weights_channel", "url_effective", "first_bytes",
                    "curl_error"])
        for h, v in res["hosts"].items():
            w.writerow([h, v["http_code"], v["bytes_read"], v["usable_weights_channel"], v["url_effective"],
                        v["first_bytes"][:120], v["curl_error"]])
    print("verdict:", res["verdict"])
    print("wrote", f"EXP0061_pretrained_encoder_feasibility_{stamp}.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
