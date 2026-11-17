"""EXP-0056: retrieve the abstract of every record in the five literature matrices.

The novelty audits currently grade collisions from titles only, because the harvesters scored relevance with the
abstract but did not store it (only `verify_status` records that one was present). Principle 2 of the programme spec
requires reading the abstract before a gap is accepted, so this fetches them once, into a programme-level file that
`grade_collisions.py` reads:

  * Crossref records -> `api.crossref.org/works?filter=doi:A|B|...&select=...` in batches of 40
  * arXiv records    -> `export.arxiv.org/api/query?id_list=...` in batches of 40

Both channels go through curl: python's urllib is refused HTTP 406 by export.arxiv.org here for every header
variant, while curl returns 200 for the same URL (measured 2026-09-19).

The run is resumable and never truncates the log: batches accumulate in a checkpoint JSON and the CSV is written
once, at the end, from the whole set (an earlier harvester in this programme opened its log with "w" and destroyed
the evidence it was meant to record before it crashed).

    python 02_shared_code/literature/fetch_abstracts.py            # full run
    python 02_shared_code/literature/fetch_abstracts.py --resume    # continue from the checkpoint
"""
from __future__ import annotations

import csv, json, pathlib, re, subprocess, sys, time, urllib.parse
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[2]
REG = ROOT / "00_program_registry"
CKPT = REG / "literature_abstracts_checkpoint.json"
OUT = REG / "literature_abstracts.csv"
BATCH = 40
PACE = 1.2
NS = {"a": "http://www.w3.org/2005/Atom"}


def curl(url, tries=3):
    for k in range(tries):
        p = subprocess.run(["curl", "-sS", "-f", "--max-time", "60", url], capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        if p.returncode == 0 and p.stdout:
            return p.stdout, None
        time.sleep(PACE * (k + 2))
    return None, f"curl exit {p.returncode}: {p.stderr.strip()[:140]}"


def load_rows():
    """Every matrix row, tagged with its paper."""
    out = []
    for f in sorted((ROOT / "papers").glob("P00*/literature_matrix.csv")):
        pid = f.parts[1].split("_")[0]
        for r in csv.DictReader(open(f, encoding="utf-8")):
            out.append({**r, "paper_id_file": pid})
    return out


def batches(items):
    for i in range(0, len(items), BATCH):
        yield items[i:i + BATCH]


def crossref_one(doi):
    """One DOI per request. A batched `filter=doi:A|B|C` returns ZERO rows if any single id in it is unknown, which
    is what made the first run come back with no Crossref abstracts at all; per-work GETs are unaffected.
    """
    url = "https://api.crossref.org/works/" + urllib.parse.quote(doi, safe="/") + "?mailto=aib-program@example.org"
    body, err = curl(url, tries=2)
    if not body:
        return None, err
    try:
        it = json.loads(body)["message"]
    except Exception as e:
        return None, f"parse {type(e).__name__}"
    ab = re.sub(r"<[^>]+>", " ", it.get("abstract") or "")
    ct = it.get("container-title") or [""]
    return {"title": re.sub(r"\s+", " ", (it.get("title") or [""])[0]).strip(),
            "abstract": re.sub(r"\s+", " ", ab).strip()[:3000],
            "venue": ct[0] if isinstance(ct, list) else str(ct),
            "year": str((it.get("published") or it.get("issued") or {}).get("date-parts", [[""]])[0][0])}, None


def arxiv_batch(ids):
    url = "https://export.arxiv.org/api/query?id_list=" + ",".join(ids) + f"&max_results={len(ids) * 2}"
    body, err = curl(url)
    if not body:
        return {}, err
    got = {}
    try:
        for e in ET.fromstring(body).findall("a:entry", NS):
            aid = (e.findtext("a:id", "", NS) or "").rsplit("/", 1)[-1]
            base = re.sub(r"v\d+$", "", aid)
            got[base] = {"title": re.sub(r"\s+", " ", e.findtext("a:title", "", NS) or "").strip(),
                         "abstract": re.sub(r"\s+", " ", e.findtext("a:summary", "", NS) or "").strip()[:3000],
                         "venue": "arXiv",
                         "year": (e.findtext("a:published", "", NS) or "")[:4]}
    except Exception as ex:
        return got, f"parse {type(ex).__name__}"
    return got, None


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    rows = load_rows()
    raw = json.loads(CKPT.read_text(encoding="utf-8")) if ("--resume" in sys.argv and CKPT.exists()) else {}
    # a checkpointed failure is not a result: re-look-up anything that came back without an abstract
    state = {k: v for k, v in raw.items() if v.get("abstract")}
    print(f"[abs] checkpoint kept {len(state)} of {len(raw)} entries")
    dois, aids = [], []
    for r in rows:
        u = (r.get("url") or "").strip()
        m = re.search(r"doi\.org/(.+)$", u)
        a = re.search(r"arxiv\.org/abs/([0-9.]+v?\d*)", u)
        if m and m.group(1).lower() not in state:
            dois.append(m.group(1))
        elif a and a.group(1) not in state and a.group(1).split("v")[0] not in state:
            aids.append(a.group(1))
    print(f"[abs] {len(rows)} matrix rows | to fetch: {len(set(dois))} Crossref DOIs, {len(set(aids))} arXiv ids "
          f"| already in checkpoint: {len(state)}")
    t0 = time.time()
    err_n = 0
    for key in sorted(set(dois)):
        if key.lower() in state:
            continue
        rec, err = crossref_one(key)
        if rec and rec.get("abstract"):
            state[key.lower()] = {**rec, "source": "crossref"}
        else:
            err_n += 1
            state[key.lower()] = {"title": (rec or {}).get("title", ""), "abstract": "",
                                  "venue": (rec or {}).get("venue", "crossref"),
                                  "year": (rec or {}).get("year", ""), "source": "crossref",
                                  "status": "no_abstract_deposited" if not err else "fetch_failed"}
        if len(state) % 20 == 0:
            CKPT.write_text(json.dumps(state, indent=0, ensure_ascii=False), encoding="utf-8", newline="")
            print(f"  [crossref] {sum(1 for v in state.values() if v.get('abstract'))} abstracts of {len(state)} "
                  f"looked up ({round(time.time() - t0)}s)", flush=True)
        time.sleep(0.6)
    for bi, batch in enumerate(batches(sorted(set(aids)))):
        got, err = arxiv_batch(batch)
        for key in batch:
            rec = got.get(key.split("v")[0])
            if rec and rec.get("abstract"):
                state[key] = {**rec, "source": "arxiv"}
            else:
                err_n += 1
                state[key] = {"title": "", "abstract": "", "venue": "arxiv", "year": "", "source": "arxiv",
                              "status": "no_abstract_returned" if not err else "fetch_failed"}
        CKPT.write_text(json.dumps(state, indent=0, ensure_ascii=False), encoding="utf-8", newline="")
        print(f"  [arxiv] batch {bi + 1}: {sum(1 for v in state.values() if v.get('abstract'))} abstracts of "
              f"{len(state)} looked up ({round(time.time() - t0)}s)", flush=True)
        time.sleep(PACE)

    fields = ["paper_id", "cite_key", "source", "identifier", "year", "venue", "title", "abstract",
              "abstract_present", "collision_target", "overlap_level_current", "url"]
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(fields)
        for r in rows:
            u = (r.get("url") or "").strip()
            m = re.search(r"doi\.org/(.+)$", u)
            a = re.search(r"arxiv\.org/abs/([0-9.]+v?\d*)", u)
            key = (m.group(1) if m else (a.group(1) if a else "")).lower()
            rec = state.get(key, {})
            w.writerow([r.get("paper_id") or r["paper_id_file"], r.get("cite_key", ""),
                        rec.get("source", "none"), key, rec.get("year", r.get("year", "")),
                        rec.get("venue", r.get("venue", "")), rec.get("title", r.get("title", "")),
                        rec.get("abstract", ""), 1 if rec.get("abstract") else 0,
                        r.get("collision_target", ""), r.get("overlap_level", ""), u])
    n_abs = sum(1 for v in state.values() if v.get("abstract"))
    print(f"[abs] wrote {OUT.name}: {len(rows)} rows, {n_abs} with abstract, {err_n} lookups returned nothing")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
