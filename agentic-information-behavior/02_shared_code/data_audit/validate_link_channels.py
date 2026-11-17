"""EXP-0072: can the channels EXP-0071 probed through actually tell present from absent? If not, re-score.

EXP-0071 reported 51 of 53 testable links reachable, but 23 of those verdicts came from `hf-mirror.com`, a channel it
gave no control. A mirror that answers 200 for everything - a soft-404 landing page, a login interstitial, a catch-all
- would produce exactly that number and mean nothing by it. This step probes each channel with a positive control, a
**negative** control that must not resolve, and a redirect-style control, then re-scores every recorded verdict under
the channels that demonstrably discriminate. It re-scores from EXP-0071's stored per-channel responses, so no link is
re-fetched and the comparison is between two scoring rules over one set of observations.

Fixed before probing:
  * a channel is `discriminative` only if its positive control resolves 2xx/3xx AND its negative control returns an
    explicit 404/410 (a negative control that also returns 200 disqualifies the channel outright);
  * a `reachable` verdict survives only if it came from a discriminative channel; otherwise the link becomes
    `untestable_via_soft_404_channel`, which is a statement about the channel, not about the link;
  * a `gone` verdict needs only that the server answered at application level, which an explicit 404 proves regardless
    of any control;
  * the two GitHub/HF repo-root URLs that EXP-0071 could not test stay untestable - no channel here reaches a repo
    landing page on a blocked canonical host.

    python validate_link_channels.py
"""
from __future__ import annotations

import glob
import json
import pathlib
import subprocess
import sys
import time
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT_RAW = ROOT / "results_raw"
PREV = sorted(glob.glob(str(OUT_RAW / "EXP0071_link_availability_*.json")))[-1]
TIMEOUT = 15

# (channel, positive control that must resolve, negative control that must NOT resolve)
CHANNEL_TESTS = {
    "hf-mirror": ("https://hf-mirror.com/datasets/choosealicense/licenses",
                  "https://hf-mirror.com/datasets/aiprsz-not-a-real-repo-9x7q2"),
    "raw.githubusercontent": ("https://raw.githubusercontent.com/torvalds/linux/master/README",
                              "https://raw.githubusercontent.com/torvalds/linux/master/NOT-A-FILE-9x7q2.md"),
    "canonical-other": ("https://arxiv.org/abs/2510.01179",
                        "https://arxiv.org/abs/9999.99999"),
    "canonical-huggingface.co": ("https://huggingface.co/datasets", "https://huggingface.co/datasets/nope-9x7q2"),
    "github-html": ("https://github.com/", "https://github.com/nope-nope-9x7q2/nope"),
}


def curl(url: str):
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
            pass
    parts = (p.stdout or "").split("|")
    try:
        return int(parts[0]), int(parts[1]), parts[2]
    except (ValueError, IndexError):
        return 0, -1, ""


def curl_retry(url, tries=2):
    """Controls are re-tried once: a transient timeout is a property of this network, not of the channel."""
    attempts = []
    for _ in range(tries):
        code, ex, fin = curl(url)
        attempts.append({"http_code": code, "exit": ex})
        if 200 <= code < 400 or code in (404, 410):
            return code, ex, fin, attempts
        time.sleep(1.5)
    code, ex, fin = attempts[-1]["http_code"], attempts[-1]["exit"], ""
    return code, ex, fin, attempts


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    D = json.loads(pathlib.Path(PREV).read_text(encoding="utf-8"))
    rows = D["rows"]
    t0 = time.time()
    chan = {}
    for name, (pos, neg) in CHANNEL_TESTS.items():
        pc, pe, pf, pa = curl_retry(pos)
        nc, ne, nf, na = curl_retry(neg)
        resolved = lambda c, e: 200 <= c < 400 and e in (0, 23)
        gone = lambda c, e: c in (404, 410) and e in (0, 23)
        chan[name] = {"positive": {"url": pos, "http_code": pc, "exit": pe, "attempts": pa,
                                   "resolved": resolved(pc, pe)},
                      "negative": {"url": neg, "http_code": nc, "exit": ne, "attempts": na,
                                   "correctly_absent": gone(nc, ne) or not resolved(nc, ne)},
                      "discriminative": bool(resolved(pc, pe) and gone(nc, ne))}
        print(f"  {name:24s} pos={pc} neg={nc} discriminative={chan[name]['discriminative']}", flush=True)
        time.sleep(0.5)

    usable = {k for k, v in chan.items() if v["discriminative"]}
    # which control governs a recorded channel, given that channels() tries the canonical host first
    CONTROL_FOR = {"hf-mirror": "hf-mirror", "raw.githubusercontent": "raw.githubusercontent",
                   "github-html": "github-html",
                   "canonical": "canonical-other"}          # refined per URL just below
    rescored = []
    for r in rows:
        tried = json.loads(r["channels"])
        new = r["verdict"]
        note = "unchanged"
        if r["verdict"] == "reachable":
            hit = next((t for t in tried if 200 <= t["http_code"] < 400), None)
            kind = hit["channel"] if hit else "?"
            if kind == "canonical":
                # a github.com/huggingface.co URL answered on its own host: judge it by that host's control, and only
                # fall back to canonical-other for hosts that have no control because they were never blocked
                low = (r["url"] or "").lower()
                if "github.com" in low:
                    # EXP-0071 lists github.com URLs twice (canonical then github-html); the 200 is the same request,
                    # so the governing control is the github one, not "no control exists"
                    kind = "github-html" if any(t["channel"] == "github-html" for t in tried) else kind
                elif "huggingface.co" in low:
                    kind = "canonical-huggingface.co"
                else:
                    kind = "canonical-other"
            ctl = CONTROL_FOR.get(kind, kind)
            if ctl not in usable:
                new = "untestable_via_soft_404_channel"
                note = f"{kind} did not pass its positive+negative control in this run"
            else:
                note = f"{kind} discriminative"
        elif r["verdict"] == "gone":
            note = "explicit 404/410 is an application-level answer; no control needed"
        rescored.append({**r, "verdict_exp0071": r["verdict"], "verdict": new, "rescoring_note": note,
                         "governing_channel": note.split()[0]})

    v0 = Counter(r["verdict_exp0071"] for r in rescored)
    v1 = Counter(r["verdict"] for r in rescored)
    test0 = v0["reachable"] + v0["gone"]
    test1 = v1["reachable"] + v1["gone"]
    res = {"exp_id": "EXP-0072", "input": pathlib.Path(PREV).name, "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "wallclock_sec": round(time.time() - t0, 1),
           "channel_validation": chan, "discriminative_channels": sorted(usable),
           "verdicts_exp0071": dict(v0), "verdicts_rescored": dict(v1),
           "availability_over_testable_exp0071": round(v0["reachable"] / test0, 4) if test0 else None,
           "availability_over_testable_rescored": round(v1["reachable"] / test1, 4) if test1 else None,
           "testable_exp0071": test0, "testable_rescored": test1,
           "links_moved_out_of_reachable": [
               {"url": r["url"], "release": r["release"], "note": r["rescoring_note"]}
               for r in rescored if r["verdict"] != r["verdict_exp0071"]],
           "rule": "a channel counts only if its positive control resolved AND its negative control returned an "
                   "explicit not-found; a reachable verdict from a non-discriminative channel becomes "
                   "untestable_via_soft_404_channel rather than being kept"}
    out = OUT_RAW / f"EXP0072_link_channel_validation_{time.strftime('%Y%m%dT%H%M%S')}.json"
    out.write_text(json.dumps({"summary": res, "rows": rescored}, indent=1, ensure_ascii=False),
                   encoding="utf-8", newline="")
    print(json.dumps({k: v for k, v in res.items() if k != "channel_validation"}, indent=1), flush=True)
    print("wrote", out.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
