"""EXP-0095 (literature tail, round 2): try to recover abstract text for the records still graded from titles alone.

`literature_graded.csv` holds 287 screened records; 94 of them are graded on **title only** because the abstract was
never retrieved (89 of the 94 carry a DOI, none is an arXiv id). The programme's rule is that a title is not a read:
those rows are marked `title_only` and cannot carry a novelty conclusion. The earlier recovery round (EXP-0063/0064)
pulled abstracts from arXiv and Semantic Scholar and moved what it could; this round goes after the remainder through
the three channels that key on a DOI, and it measures the channels as it goes, because "0 recovered" and "channel
unreachable" are different findings and only one of them is about the literature.

Channels tried per record, in this order, first hit wins:
  1. Crossref `https://api.crossref.org/works/<doi>` - the `abstract` field (publisher-deposited, often absent);
  2. OpenAlex `https://api.openalex.org/works/doi:<doi>` - `abstract_inverted_index`, reconstructed to text;
  3. Semantic Scholar `https://api.semanticscholar.org/graph/v1/paper/DOI:<doi>?fields=title,abstract`.

Pre-declared rules, fixed before any request is made:
  * every channel is tested on a **positive control** (a DOI taken from a record whose abstract is already on disk)
    and a **negative control** (a deliberately invented DOI). A channel is "working" only if it returns text for the
    control and nothing for the negative case; a channel that fails the positive control is recorded as unavailable
    here, and any 0-recovery result on it is about the channel, not about the literature;
  * recovered abstracts are appended to a new file (`literature_abstracts_v3.csv`); v1/v2 stay untouched;
  * the frozen grading rule is re-applied by importing `grade_collisions.grade`, not by re-implementing it, and the
    delta (which grades moved, which did not) is written out;
  * records that still have no abstract text are left `title_only` and labelled `undecidable_on_title`, and they are
    excluded from citation-based novelty conclusions exactly as before. No grade is upgraded on a title, and no grade
    is downgraded because a channel came back empty.

Amendments registered after the first pass (they report, they do not re-decide anything): every grade move is
attributed either to an abstract this round recovered or to a stored level the frozen rule cannot reproduce from the
text already on disk, the curated per-paper `literature_matrix.csv` columns are compared against the rule, and the
script's own previous v3 output is reused by default so a correction run cannot lose data to a rate limit.

    python literature_abstract_recovery_round2.py [--limit 94] [--sleep 0.6]

Writes 00_program_registry/EXP0095_abstract_recovery.json plus the v3 CSVs.
"""
from __future__ import annotations

import argparse, csv, io, json, os, pathlib, re, subprocess, sys, time
from collections import Counter

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import grade_collisions as GC                    # noqa: E402  the frozen rule, imported not copied

ROOT = HERE.parents[1]
REG = ROOT / "00_program_registry"
V1, V2 = REG / "literature_abstracts.csv", REG / "literature_abstracts_v2.csv"
V3 = REG / "literature_abstracts_v3.csv"
GRADED = REG / "literature_graded.csv"
GRADED_V3 = REG / "literature_graded_v3.csv"
OUT = REG / "EXP0095_abstract_recovery.json"
UA = "agentic-information-behavior-programme/1.0 (research use; contact via repository)"
TIMEOUT = 25


CODE = {}                      # last HTTP status per URL, so "empty" and "unreachable" are never conflated


def fetch(url: str, retries: int = 2):
    """GET via curl (the tool this environment's channel probe already validated).

    Returns the body or None, and records the HTTP status in CODE: a 200 with no abstract field, a 404, a 429 rate
    limit and a connection failure are four different findings, and the earlier version of this function reported all
    four as "nothing recovered".
    """
    for attempt in range(retries + 1):
        try:
            r = subprocess.run(["curl", "-sS", "-o", "-", "-w", "\n%{http_code}", "--max-time", str(TIMEOUT),
                                "-A", UA, url], capture_output=True, text=True, encoding="utf-8",
                               errors="replace", timeout=TIMEOUT + 10)
        except Exception as e:
            CODE[url] = f"exception:{type(e).__name__}"
            return None
        out = r.stdout or ""
        body, _, code = out.rpartition("\n")
        CODE[url] = CODE["last"] = code.strip() or f"rc{r.returncode}"
        if code.strip() in ("429", "503", "500") and attempt < retries:
            time.sleep(2.0 + 3.0 * attempt)          # polite backoff; these APIs rate-limit hard
            continue
        if r.returncode != 0 and not body.strip():
            return None
        return body if body.strip() else None
    return None


def norm(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s or "")).strip()


def from_crossref(doi):
    t = fetch("https://api.crossref.org/works/" + doi)
    if not t:
        return None
    try:
        m = json.loads(t).get("message") or {}
    except Exception:
        return None
    return norm(m.get("abstract")) or None


def from_openalex(doi):
    t = fetch("https://api.openalex.org/works/doi:" + doi)
    if not t:
        return None
    try:
        m = json.loads(t)
    except Exception:
        return None
    inv = m.get("abstract_inverted_index")
    if not inv:
        return None
    pos = {}
    for w, idxs in inv.items():
        for i in idxs:
            pos[i] = w
    return norm(" ".join(pos[i] for i in sorted(pos))) or None


def from_s2(doi):
    t = fetch("https://api.semanticscholar.org/graph/v1/paper/DOI:" + doi + "?fields=title,abstract")
    if not t:
        return None
    try:
        m = json.loads(t)
    except Exception:
        return None
    return norm(m.get("abstract")) or None


CHANNELS = [("crossref", from_crossref), ("openalex", from_openalex), ("semanticscholar", from_s2)]
NEGATIVE_DOI = "10.0000/agentic.programme.control.does.not.exist"


def load_dois():
    """The DOI-bearing rows still graded on titles alone."""
    graded = list(csv.DictReader(io.StringIO(GRADED.read_text(encoding="utf-8"))))
    title_only = [g for g in graded if g.get("graded_on") == "title_only"]
    have = {}
    for p in (V1, V2):
        if p.is_file():
            for r in csv.DictReader(io.StringIO(p.read_text(encoding="utf-8"))):
                have[(r.get("paper_id"), r.get("cite_key"))] = r
    out = []
    for g in title_only:
        doi = (g.get("identifier") or "").strip()
        if not doi.lower().startswith("10."):
            continue
        src = have.get((g["paper_id"], g["cite_key"]), {})
        out.append({"paper_id": g["paper_id"], "cite_key": g["cite_key"], "doi": doi,
                    "title": g.get("title") or src.get("title") or "", "url": g.get("url") or "",
                    "year": g.get("year") or src.get("year") or ""})
    return out, title_only, graded


def openalex_control_pool(n: int = 8):
    """DOIs OpenAlex itself says carry an abstract - the only honest way to test whether a channel can return text."""
    t = fetch("https://api.openalex.org/works?filter=has_abstract:true,from_publication_date:2019-01-01"
              f"&per-page={n}&select=id,doi")
    if not t:
        return []
    try:
        j = json.loads(t)
    except Exception:
        return []
    out = []
    for r in j.get("results") or []:
        d = (r.get("doi") or "").replace("https://doi.org/", "").strip()
        if d.lower().startswith("10."):
            out.append(d)
    return out


def probe_channels():
    """Per channel: HTTP reachability, an abstract control, and the negative control, kept as three separate facts."""
    probes = {}
    pool = openalex_control_pool()
    for name, fn in CHANNELS:
        p = {"control_candidates_tried": len(pool), "positive_words": 0, "positive_control_doi": None,
             "negative_returned_text": False, "http_status": CODE.get("last", "")}
        for c in pool:
            a = fn(c)
            p["http_status"] = CODE.get("last", p["http_status"])
            if a and len(a.split()) >= 25:
                p["positive_control_doi"], p["positive_words"] = c, len(a.split())
                break
        neg = fn(NEGATIVE_DOI)
        p["negative_returned_text"] = bool(neg and len(neg.split()) >= 5)
        if p["positive_control_doi"] and not p["negative_returned_text"]:
            p["status"] = "working"
        elif p["negative_returned_text"]:
            p["status"] = "unreliable(returns text for an invented DOI)"
        else:
            p["status"] = ("reachable_but_no_abstract_for_any_control"
                           if str(p["http_status"]).startswith("2") else
                           f"unreachable_or_rate_limited(http {p['http_status'] or 'none'})")
        probes[name] = p
        time.sleep(1.0)
    return probes


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=200)
    ap.add_argument("--sleep", type=float, default=0.6)
    ap.add_argument("--no-cache", dest="no_cache", action="store_true",
                    help="re-query every DOI instead of reusing this script's own previous v3 output; caching is on "
                         "by default so that a correction run cannot silently lose abstracts to a rate limit and "
                         "report a smaller corpus than the run it is correcting")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    targets, title_only, graded = load_dois()
    targets = targets[:args.limit]
    print(f"  {len(title_only)} title_only rows, {len(targets)} with a DOI to try", flush=True)

    # ---- channel probes first, with controls, so an empty result is interpretable
    probes = probe_channels()
    for name, pr in probes.items():
        print(f"  channel {name}: {pr['status']} (control {pr['positive_words']} words, "
              f"last http {pr.get('http_status')})", flush=True)

    # A row the graded file calls title_only has no usable abstract, so any >= 25-word abstract this script's own
    # output holds for such a key can only come from a previous EXP-0095 pass.
    cache = {}
    if not args.no_cache and V3.is_file():
        for r in csv.DictReader(io.StringIO(V3.read_text(encoding="utf-8"))):
            a, src = (r.get("abstract") or "").strip(), r.get("source") or ""
            if len(a.split()) >= 25 and src.startswith("EXP-0095"):
                cache[(r.get("paper_id"), r.get("cite_key"))] = (a, src.split(":", 1)[1])
    got, fails, by_channel, reused = {}, Counter(), Counter(), 0
    for i, tg in enumerate(targets, 1):
        key = (tg["paper_id"], tg["cite_key"])
        if key in cache:
            a, ch = cache[key]
            got[key] = {"abstract": a, "channel": ch, "doi": tg["doi"], "from_cache": True}
            by_channel[ch] += 1
            reused += 1
            continue
        for name, fn in CHANNELS:
            if probes[name]["status"] != "working":
                fails[f"{name}:channel_unavailable"] += 1
                continue
            try:
                a = fn(tg["doi"])
            except Exception as e:
                fails[f"{name}:{type(e).__name__}"] += 1
                a = None
            if a and len(a.split()) >= 25:
                got[(tg["paper_id"], tg["cite_key"])] = {"abstract": a, "channel": name, "doi": tg["doi"]}
                by_channel[name] += 1
                break
            time.sleep(args.sleep)
        else:
            fails["no_channel_returned_text"] += 1
        if i % 10 == 0:
            print(f"  {i}/{len(targets)} tried, {len(got)} recovered", flush=True)
        time.sleep(args.sleep)

    # ---- write v3 abstracts (union of prior files plus what this round recovered)
    fields = ["paper_id", "cite_key", "title", "abstract", "year", "venue", "url", "doi", "source"]
    merged, seen = [], set()
    for p, src_tag in ((V2, "v2"), (V1, "v1")):
        if not p.is_file():
            continue
        for r in csv.DictReader(io.StringIO(p.read_text(encoding="utf-8"))):
            k = (r.get("paper_id"), r.get("cite_key"))
            if k in seen:
                continue
            seen.add(k)
            r = dict(r)
            r["source"] = r.get("source") or src_tag
            merged.append(r)
    added = 0
    for (pid, ck), v in got.items():
        tgt = next((t for t in targets if (t["paper_id"], t["cite_key"]) == (pid, ck)), None)
        if tgt is None:
            continue
        row = {f: "" for f in fields}
        row.update({"paper_id": pid, "cite_key": ck, "title": tgt["title"], "abstract": v["abstract"],
                    "year": tgt["year"], "url": tgt["url"], "doi": v["doi"], "source": "EXP-0095:" + v["channel"]})
        if (pid, ck) in seen:
            for m in merged:
                if (m.get("paper_id"), m.get("cite_key")) == (pid, ck):
                    m["abstract"], m["source"] = v["abstract"], "EXP-0095:" + v["channel"]
        else:
            merged.append(row)
            seen.add((pid, ck))
        added += 1
    hdr = list(merged[0].keys()) if merged else fields
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=hdr, lineterminator="\r\n", extrasaction="ignore")
    w.writeheader()
    w.writerows(merged)
    V3.write_text(buf.getvalue(), encoding="utf-8", newline="")
    print(f"  wrote {V3.name}: {len(merged)} rows ({added} newly recovered)", flush=True)

    # ---- re-apply the FROZEN grading rule to every record, reading abstracts from v3
    absmap = {(r.get("paper_id"), r.get("cite_key")): (r.get("abstract") or "") for r in merged}
    before = Counter(g.get("overlap_level_current") for g in graded)
    rows_out, moved, still_title = [], [], []
    for g in graded:
        k = (g["paper_id"], g["cite_key"])
        a = absmap.get(k, "")
        # `literature_graded.csv` mixes two populations: screened references that carry an L0-L4 grade, and funnel
        # candidates whose level field holds a screening state ("candidate - abstract read, not yet graded"). The
        # frozen collision rule was never applied to the second group, so re-grading them would report ~200 spurious
        # "grade changes" and read as if the recovery round had rewritten the whole corpus.
        screened = (g.get("overlap_level_current") or "").startswith(("L",)) or \
            (g.get("overlap_level_current") or "") in ("L1_provisional",)
        graded_on = "title+abstract" if len(a.split()) >= 25 else "title_only"
        if not screened:
            rows_out.append({**g, "regraded_by": "EXP-0095 (not in scope: screening state, not a grade)"})
            continue
        lvl = (GC.grade(g["paper_id"], g.get("title") or "", a)[0] if graded_on == "title+abstract"
               else g.get("overlap_level_current"))
        rows_out.append({**g, "overlap_level_current": lvl, "graded_on": graded_on,
                         "regraded_by": "EXP-0095", "level_rule": g.get("level_rule") or "frozen rule (grade_collisions)"})
        if lvl != g.get("overlap_level_current"):
            moved.append({"paper_id": g["paper_id"], "cite_key": g["cite_key"], "from": g.get("overlap_level_current"),
                          "to": lvl, "graded_on_before": g.get("graded_on"), "graded_on_now": graded_on,
                          "abstract_recovered_by_this_round": k in got})
        if graded_on == "title_only":
            still_title.append({"paper_id": g["paper_id"], "cite_key": g["cite_key"], "doi": g.get("identifier"),
                                "label": "undecidable_on_title"})
    buf2 = io.StringIO()
    w2 = csv.DictWriter(buf2, fieldnames=list(graded[0].keys()), lineterminator="\r\n", extrasaction="ignore")
    w2.writeheader()
    w2.writerows(rows_out)
    GRADED_V3.write_text(buf2.getvalue(), encoding="utf-8", newline="")

    attr = Counter("abstract_recovered_by_this_round" if m["abstract_recovered_by_this_round"]
                   else "stored_level_not_reproducible_from_the_text_already_on_disk" for m in moved)
    mat_agreement = {}
    for pid in sorted({m["paper_id"] for m in moved}):
        pdir = next(iter((ROOT / "papers").glob(pid + "_*")), None)
        mf = (pdir / "literature_matrix.csv") if pdir else None
        if not mf or not mf.is_file():
            mat_agreement[pid] = {"error": "no curated matrix found"}
            continue
        re_by_key = {r["cite_key"]: r["overlap_level_current"] for r in rows_out if r["paper_id"] == pid}
        cmp_rows, disagree = 0, []
        for r in csv.DictReader(io.StringIO(mf.read_text(encoding="utf-8"))):
            lvl = str(r.get("overlap_level") or "")
            if not lvl.startswith("L"):
                continue
            cmp_rows += 1
            new = re_by_key.get(r["cite_key"])
            if new and new != lvl:
                disagree.append({"cite_key": r["cite_key"], "matrix": lvl, "frozen_rule": new})
        mat_agreement[pid] = {"matrix_rows_with_a_level": cmp_rows, "disagree_with_frozen_rule": len(disagree),
                              "examples": disagree[:6]}

    def _holds_grade(k):
        g = next((x for x in graded if (x["paper_id"], x["cite_key"]) == k), {})
        return str(g.get("overlap_level_current") or "").startswith("L")

    res = {"exp_id": "EXP-0095", "at": time.strftime("%Y-%m-%dT%H:%M:%S"), "wallclock_sec": None,
           "targets": {"title_only_rows": len(title_only), "with_doi_tried": len(targets)},
           "channel_probes": probes, "recovered_by_channel": dict(by_channel),
           "recovered_total": len(got), "failure_counter": dict(fails),
           "graded_rows": len(rows_out), "grades_moved": len(moved), "moved_detail": moved[:40],
           "abstracts_reused_from_this_scripts_prior_v3_run": reused,
           "recovered_rows_holding_a_grade": sum(1 for k in got if _holds_grade(k)),
           "recovered_rows_holding_only_a_screening_state": sum(1 for k in got if not _holds_grade(k)),
           "move_attribution": dict(attr),
           "curated_matrix_agreement_with_frozen_rule": mat_agreement,
           "still_title_only": len(still_title), "still_title_only_detail": still_title[:40],
           "abstracts_before": int(sum(1 for g in graded if g.get("graded_on") == "title+abstract")),
           "abstracts_after": int(sum(1 for r in rows_out if r["graded_on"] == "title+abstract")),
           "level_counts_before": dict(before), "level_counts_after": dict(Counter(r["overlap_level_current"] for r in rows_out)),
           "rule": "pre-declared in the module docstring: channels need a positive control to count as working; "
                   "no grade changes on a title; no upgrade is inferred from an unavailable channel"}
    if added == 0 and all(p["status"] != "working" for p in probes.values()):
        res["verdict"] = ("NO CONCLUSION ABOUT THE LITERATURE: no DOI-keyed channel returned text for the positive "
                          "control here, so the tail stays title-only because of this machine's network, and the "
                          "affected records remain labelled undecidable_on_title")
    elif added == 0:
        res["verdict"] = (f"CHANNELS WORK, NOTHING RECOVERED: the controls pass but no title-only record yielded "
                          f">= 25 words of abstract, so the {len(targets)} remaining records have no abstract at "
                          "these sources; they stay title-only and are excluded from novelty conclusions")
    else:
        by_move = ", ".join(f"{k}={v}" for k, v in sorted(attr.items()))
        res["verdict"] = (f"RECOVERED {added} abstracts via "
                          f"{', '.join(f'{k}={v}' for k, v in sorted(by_channel.items()))} "
                          f"({sum(1 for k in got if _holds_grade(k))} of them on records that carry a grade, "
                          f"{sum(1 for k in got if not _holds_grade(k))} on funnel candidates that were never "
                          f"graded); {len(still_title)} screened record(s) remain title-only and are labelled "
                          f"undecidable_on_title. {len(moved)} grade(s) moved under the frozen rule, attributed "
                          f"as: {by_move}. "
                          + ("The recovery round changed no grade: every move is a stored level the frozen rule does "
                             "not reproduce from the abstract already on disk, so this is a finding about the "
                             "consistency of the level columns, not about the literature. "
                             if attr.get("abstract_recovered_by_this_round", 0) == 0 and moved else "")
                          + "Curated matrix columns disagree with the rule on "
                          + "; ".join(f"{p}: {d.get('disagree_with_frozen_rule', '?')} of "
                                      f"{d.get('matrix_rows_with_a_level', '?')}"
                                      for p, d in sorted(mat_agreement.items())) + " - both levels are kept.")
    res["wallclock_sec"] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: res[k] for k in ("recovered_total", "grades_moved", "still_title_only", "abstracts_before",
                                          "abstracts_after")}, ensure_ascii=False))
    print("verdict:", res["verdict"])
    print("wrote", OUT.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
