"""EXP-0081: can an external tool-retrieval benchmark be acquired from this host? Measured channel by channel.

P001's L6 states that the external benchmarks are "not downloadable in this environment" and its final audit keeps
cross-dataset external validation open on that reason. That is an environment claim, and this programme has been
burned twice by unmeasured environment claims (EXP-0061 found the model weights were reachable after all; EXP-0072
found a channel that passed in one round and failed in the next). So each channel that could carry the corpus is
probed with a positive AND a deliberately absent negative control, under the rule fixed in EXP-0071:

    a transport failure is `untestable`, never `absent`; and a channel counts as answering only if it distinguishes
    the present case from the invented one.

Candidate dataset ids are taken from the authors' own arXiv record (2503.01763) rather than invented as claims, and
one invented id is included as the negative control. No inference API is called: every endpoint here returns stored
bibliographic or repository metadata.

    python external_benchmark_channel_probe.py
"""
from __future__ import annotations

import json, os, pathlib, re, subprocess, sys, time

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "results_raw"
OUT_DIR.mkdir(parents=True, exist_ok=True)          # the step must not assume its target exists
ENDPOINT = os.environ.get("HF_ENDPOINT", "https://hf-mirror.com")
POSITIVE_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
ABSENT = "mangopy/zz-definitely-absent-xyz"
DATASET_IDS = ["mangopy/tool-retrieval-benchmark", "mangopy/ToolRet", "mangopy/tool_retrieval_benchmark",
               "ethnue/tool-retrieval-benchmark", ABSENT]
ARXIV_ID = "2503.01763"
REPO = "mangopy/tool-retrieval-benchmark"


def curl(url: str, sink: pathlib.Path | None):
    """Return (http_code, bytes, exit_code). A non-zero exit with code 000 is a transport failure, not a 404."""
    cmd = ["curl", "-sS", "-g", "--max-time", "40", "-w", "%{http_code} %{size_download}"]
    if sink is not None:
        sink.parent.mkdir(parents=True, exist_ok=True)
        cmd += ["-o", str(sink)]
    else:
        cmd += ["-o", str(OUT_DIR / f".curl_sink_{int(time.time() * 1000)}.tmp")]
    cmd.append(url)
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = (r.stdout or "").strip().split()
    code, size = (out[0], out[1]) if len(out) >= 2 else ("000", "0")
    return code, int(size or 0), r.returncode, (r.stderr or "").strip()[:160]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    res = {"exp_id": "EXP-0081", "endpoint": ENDPOINT, "arxiv_id": ARXIV_ID, "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "rule": "a transport failure is untestable, not absent; a channel counts as answering only when it "
                   "separates the present case from the invented one", "http": {}, "probes": {}}

    fetch = ROOT / "logs" / "fetch"
    for name, url in (("arxiv_atom", f"https://export.arxiv.org/api/query?id_list={ARXIV_ID}"),
                      ("toolret_pdf", f"https://export.arxiv.org/pdf/{ARXIV_ID}v2"),
                      ("gh_readme_main", f"https://raw.githubusercontent.com/{REPO}/main/README.md"),
                      ("gh_readme_master", f"https://raw.githubusercontent.com/{REPO}/master/README.md"),
                      ("gh_negative_control", f"https://raw.githubusercontent.com/{REPO}/main/zz-absent-README.md"),
                      ("hub_main", f"https://github.com/{REPO}")):
        code, size, rc, err = curl(url, fetch / name)
        res["http"][name] = {"url": url, "http_code": code, "bytes": size, "curl_exit": rc, "error": err or None}
        print(f"  {name:20s} http={code} bytes={size} curl_exit={rc} {err[:70]}", flush=True)
    # the PDF is only 1.1 MB; the two GitHub hosts above are probes of the same channel, positive and negative
    found = re.findall(rb"https?://(?:github\.com|huggingface\.co)/[A-Za-z0-9_.:/-]+",
                       (fetch / "toolret_pdf").read_bytes())
    res["data_urls_named_by_the_paper"] = sorted({u.decode() for u in found})[:25]

    from huggingface_hub import HfApi          # the transport EXP-0061/0062 proved works for weight files
    api = HfApi(endpoint=ENDPOINT)
    for kind, ids in (("model", [POSITIVE_MODEL, ABSENT]), ("dataset", DATASET_IDS)):
        for i in ids:
            try:
                info = api.model_info(i) if kind == "model" else api.dataset_info(i)
                files = [s.rfilename for s in (info.siblings or [])]
                res["probes"][f"{kind}:{i}"] = {"found": True, "n_files": len(files), "sample": files[:8]}
                print(f"  {kind:7s} {i:44s} FOUND ({len(files)} files)", flush=True)
            except Exception as exc:                       # noqa: BLE001 - the outcome IS the observation
                res["probes"][f"{kind}:{i}"] = {"found": False, "error": f"{type(exc).__name__}: {exc}"[:200]}
                print(f"  {kind:7s} {i:44s} {type(exc).__name__}", flush=True)

    pos = res["probes"][f"model:{POSITIVE_MODEL}"]
    neg = res["probes"][f"model:{ABSENT}"]
    ds = {k: v for k, v in res["probes"].items() if k.startswith("dataset:")}
    res["channel_verdicts"] = {
        "arxiv_delivery": "reachable" if res["http"]["toolret_pdf"]["http_code"] == "200" else "not reachable",
        "raw_githubusercontent": "untestable (positive and negative control both failed at transport level)"
                                 if res["http"]["gh_readme_main"]["http_code"] == "000"
                                 and res["http"]["gh_negative_control"]["http_code"] == "000" else "answered",
        "hf_mirror_models": "discriminative" if pos.get("found") and not neg.get("found") else "NOT discriminative",
        "hf_mirror_datasets": "NOT discriminative (every id, present-shaped and invented alike, gets the same answer)"
                              if len({bool(v.get("found")) for v in ds.values()}) == 1 else "discriminative",
    }
    res["wallclock_sec"] = round(time.time() - t0, 1)
    fp = OUT_DIR / f"EXP0081_external_benchmark_channel_probe_{time.strftime('%Y%m%dT%H%M%S')}.json"
    fp.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8", newline="")
    print(json.dumps(res["channel_verdicts"], indent=1), "|", fp.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
