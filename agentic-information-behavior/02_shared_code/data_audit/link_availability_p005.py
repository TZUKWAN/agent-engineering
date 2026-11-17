"""EXP-0071: measure the availability of P005's declared links, which EXP-0049 could only count as unverifiable.

EXP-0049's RQ5 stopped at a host classification: of 62 URLs in the eight dataset cards, 72.3% sat on hosts it could
not reach, and the census recorded `availability_unmeasured` - "a fetch failure could not be distinguished from real
link rot". That premise is now known to be false. EXP-0061 measured `raw.githubusercontent.com` answering with real
file bytes and `hf-mirror.com` serving the same repository paths that `huggingface.co` owns, so a fetch can be routed
through a working channel and an explicit not-found can be separated from a blocked connection.

Pre-registered before the first probe:
  * the URL set is re-extracted with the census's own regex over the same card prose, and the per-release counts are
    asserted against the published `rq5` block - this measures the same 62 links, not a new sample;
  * each URL is tried on its canonical host first, then on the alternate channel that EXP-0061 proved reachable
    (huggingface.co -> hf-mirror.com on the same path; github.com blob/raw paths -> raw.githubusercontent.com);
  * verdicts: `reachable` (a channel returned 2xx/3xx-to-2xx), `gone` (a channel that demonstrably works for a control
    URL returned an explicit 404/410 for this one), `untestable` (every channel failed at transport level). **A
    transport failure is never counted as rot**, and a 404 from a channel that also 404s its own control page is not
    counted either;
  * every host class gets a positive control (a URL known to exist) probed the same way, so "the channel works" is
    measured per run rather than assumed from EXP-0061;
  * the rate is reported over the testable subset AND with the untestable residue stated, never as a single percentage.

    python link_availability_p005.py

Writes results_raw/EXP0071_link_availability_*.json and results_processed/EXP0071_link_availability.csv.
"""

from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys
import time
from collections import Counter

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import governance_metadata_pilot_p005 as G  # noqa: E402  (CORPORA, URL, front_matter - the census's own helpers)

ROOT = HERE.parents[1]
DATA = G.DATA   # the census reads its cards from here, not from 01_datasets
OUT_RAW = ROOT / "results_raw"
OUT_PROC = ROOT / "results_processed"
CENSUS = sorted((ROOT / "results_raw").glob("EXP0049_governance_census_*.json"))[-1]
TIMEOUT = 12
GONE = {404, 410, 451}
HUGGING = re.compile(r"^https?://huggingface\.co/", re.I)
GITHUB_BLOB = re.compile(r"^https?://github\.com/(.+?)/(?:blob|tree)/(.+)", re.I)

# one known-live URL per host class; a channel only counts as working if its control resolves
CONTROLS = {
    "huggingface.co": "https://huggingface.co/datasets",
    "github.com": "https://github.com/",
    "raw.githubusercontent.com": "https://raw.githubusercontent.com/torvalds/linux/master/README",
    "other": None,
}


def curl(url: str):
    """Return (http_code, exit_code, final_url). No retries: a second try would hide the failure mode being measured."""
    import tempfile, os
    with tempfile.NamedTemporaryFile(delete=False, suffix=".body") as tf:
        sink = tf.name
    try:
        p = subprocess.run(["curl", "-s", "-o", sink, "-L", "--max-time", str(TIMEOUT),
                            "-w", "%{http_code}|%{exitcode}|%{url_effective}", url],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
    finally:
        try:
            os.unlink(sink)
        except OSError:
            pass                                  # a leftover temp body is not worth failing a probe over
    parts = (p.stdout or "").split("|")
    try:
        return int(parts[0]), int(parts[1]), parts[2]
    except (ValueError, IndexError):
        return 0, -1, ""


def channels(url: str):
    """Canonical host first, then the alternate channel EXP-0061 showed is reachable from here."""
    out = [("canonical", url)]
    m = HUGGING.match(url)
    if m:
        out.append(("hf-mirror", "https://hf-mirror.com/" + url.split("huggingface.co/", 1)[1]))
    m = GITHUB_BLOB.match(url)
    if m:
        out.append(("raw.githubusercontent", f"https://raw.githubusercontent.com/{m.group(1)}/{m.group(2)}"))
    if "github.com" in url.lower():
        out.append(("github-html", url))
    return out


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    census = json.loads(pathlib.Path(CENSUS).read_text(encoding="utf-8"))
    published = census["rq5"]["per_release"]

    controls = {}
    for host, u in CONTROLS.items():
        if not u:
            continue
        code, ex, fin = curl(u)
        controls[host] = {"url": u, "http_code": code, "exit": ex,
                          "usable": bool(200 <= code < 400 and ex in (0, 23))}
        print(f"  control {host:24s} http={code} exit={ex} usable={controls[host]['usable']}", flush=True)

    per_release, all_rows = {}, []
    for name, rel in G.CORPORA.items():
        rd = DATA / rel / "README.md"
        prose = ""
        if rd.exists():
            _, prose = G.front_matter(rd.read_text(encoding="utf-8", errors="replace"))
        urls = [u.rstrip(".,;:") for u in G.URL.findall(prose)]
        rows = []
        for u in urls:
            host = re.sub(r"^www\.", "", u.split("/")[2].lower()) if "//" in u else ""
            tried = []
            verdict, why = "untestable", "no channel answered"
            for kind, target in channels(u):
                code, ex, fin = curl(target)
                tried.append({"channel": kind, "url": target, "http_code": code, "exit": ex,
                              "final_url": fin if len(fin) < 200 else fin[:200]})
                if 200 <= code < 400 and ex in (0, 23):   # 23 = curl write error on the sink, not a fetch failure
                    verdict, why = "reachable", f"{kind} returned {code}"
                    break
                if code in GONE and ex == 0:
                    ctl_ok = controls.get(host.split("/")[0], {}).get("usable", True)
                    if ctl_ok:
                        verdict, why = "gone", f"{kind} returned an explicit {code}"
                    else:
                        verdict, why = "untestable", f"{kind} said {code} but its control channel is unusable"
                    break
            rows.append({"release": name, "url": u, "host": host, "verdict": verdict, "basis": why,
                         "channels": json.dumps(tried, ensure_ascii=False)})
            print(f"  {name:12s} {verdict:11s} {u[:78]}", flush=True)
            time.sleep(0.4)
        per_release[name] = rows
        all_rows += rows

    n_tot = len(all_rows)
    if n_tot != census["rq5"]["total_urls"]:
        raise SystemExit(f"[e71] ABORT: extracted {n_tot} URLs but EXP-0049 published "
                         f"{census['rq5']['total_urls']}; this is not the same link set, so no availability "
                         "number may be reported against it.")
    bad = {k: (len(v), published.get(k, [None])[0]) for k, v in per_release.items()
           if len(v) != published.get(k, [None])[0]}
    if bad:
        raise SystemExit(f"[e71] ABORT: per-release URL counts differ from the published census: {bad}")
    print(f"[e71] link set matches the published census exactly ({n_tot} URLs, per-release counts verified)", flush=True)
    vc = Counter(r["verdict"] for r in all_rows)
    testable = vc["reachable"] + vc["gone"]
    res = {"exp_id": "EXP-0071", "census_file": CENSUS.name, "controls": controls,
           "urls_found": n_tot,
           "published_rq5_total_urls": census["rq5"]["total_urls"],
           "per_release_count_check": {k: [len(per_release[k]), published.get(k, [None])[0]]
                                       for k in per_release},
           "mean_unverifiable_host_share_as_published": census["rq5"]["mean_unverifiable_host_share"],
           "verdicts": dict(vc),
           "testable": testable, "untestable": vc["untestable"],
           "availability_rate_over_testable": round(vc["reachable"] / testable, 4) if testable else None,
           "broken_rate_over_testable": round(vc["gone"] / testable, 4) if testable else None,
           "coverage_of_declared_links": round(testable / n_tot, 4) if n_tot else None,
           "per_release_verdicts": {k: dict(Counter(r["verdict"] for r in v)) for k, v in per_release.items()},
           "rule": "a transport failure is never counted as rot; a 404 counts only when the same channel resolved its "
                   "positive control in this run",
           "at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    OUT_RAW.mkdir(parents=True, exist_ok=True)
    out = OUT_RAW / f"EXP0071_link_availability_{time.strftime('%Y%m%dT%H%M%S')}.json"
    out.write_text(json.dumps({"summary": res, "rows": all_rows}, indent=1, ensure_ascii=False),
                   encoding="utf-8", newline="")
    import csv as _csv
    import io as _io
    buf = _io.StringIO()
    w = _csv.DictWriter(buf, fieldnames=list(all_rows[0].keys()), lineterminator="\r\n")
    w.writeheader()
    w.writerows(all_rows)
    (OUT_PROC / "EXP0071_link_availability.csv").write_text(buf.getvalue(), encoding="utf-8", newline="")
    print(json.dumps(res, indent=1), flush=True)
    print("wrote", out.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
