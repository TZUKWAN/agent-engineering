"""EXP-0078: put `paper_id` in the experiment registry on one controlled vocabulary.

The registry's `paper_id` column carries two conventions at once: early recorders wrote the **topic** id (T037, T008,
T012, T024, "T001-T003"), later ones wrote the **paper** id (P001, P004, P005), and programme-level steps used four
different spellings of "programme". Nothing was wrong until something asked a per-paper question: building P002's
`configs/experiment_configs.csv` returned **0 rows**, because its two experiments are filed under T008. A count that
depends on which convention the person who wrote the row happened to use is not a registry.

Fix, without losing information:
  * `paper_id` becomes canonical - `P001`..`P005`, `;`-joined for the two experiments that genuinely serve two papers,
    or `programme` for programme-level steps;
  * the topic id moves to a new `topic_id` column, so the historical attribution is still readable;
  * the script asserts the result: every `paper_id` token is a known paper or `programme`, every `topic_id` is empty
    or matches `T\\d+` (or the recorded range string), and the row count and every other column are unchanged.
  * `package_audit.py` gains that vocabulary check, so a future recorder cannot reintroduce the drift.

    python 02_shared_code/registry/normalise_registry_paper_id.py
"""
from __future__ import annotations

import csv, io, json, pathlib, re, time

ROOT = pathlib.Path(__file__).resolve().parents[2]
REG = ROOT / "00_program_registry"
P = REG / "experiment_registry.csv"
PAPERS = {"P001", "P002", "P003", "P004", "P005"}
TOPIC_TO_PAPER = {"T037": "P001", "T001-T003": "P001", "T001": "P001", "T002": "P001", "T003": "P001",
                  "T008": "P002", "T012": "P003", "T024": "P004", "T013": "P005", "T014": "P005"}
FUNNEL_TOPICS = {"T004", "T007", "T029", "T036"}          # probed, never became a paper: paper_id = programme
PROGRAMME_SPELLINGS = {"PROGRAM", "program", "programme", "PROGRAM (literature)", "PROGRAM (funnel)"}


def main() -> int:
    rows = list(csv.reader(io.StringIO(P.read_text(encoding="utf-8"))))
    hdr, body = rows[0], [r for r in rows[1:] if r]
    if "topic_id" in hdr:
        print("[e78] topic_id column already present; re-checking the vocabulary only")
    else:
        hdr = hdr + ["topic_id"]
        body = [r + [""] for r in body]
    iP, iT = hdr.index("paper_id"), hdr.index("topic_id")
    before = [list(r) for r in body]
    moved = 0
    for r in body:
        raw = (r[iP] or "").strip()
        topic = ""
        if raw in PROGRAMME_SPELLINGS:
            canon, topic = "programme", ""
        elif raw.startswith("funnel:"):
            canon, topic = "programme", raw.split(":", 1)[1]
        else:
            # parentheticals are stripped BEFORE splitting on separators: "P005 (T013+T014)" would otherwise split
            # into "P005 (T013" and "T014)", which is what the vocabulary assertion caught on the first run
            cleaned = re.sub(r"\s*\(.*?\)", "", raw)
            cleaned = re.sub(r"\s*formerly.*$", "", cleaned)
            tokens, ok = [], True
            for tok in re.split(r"[;,+]", cleaned):
                tok = tok.strip()
                if not tok:
                    continue
                if tok in PAPERS:
                    tokens.append(tok)
                elif tok in TOPIC_TO_PAPER:
                    tokens.append(TOPIC_TO_PAPER[tok]); topic = tok
                elif tok in FUNNEL_TOPICS:
                    topic = topic or tok
                else:
                    ok = False
            canon = ";".join(sorted(set(tokens))) if ok and tokens else ("programme" if topic else raw)
        if canon != raw:
            moved += 1
        r[iP] = canon
        if not r[iT]:
            r[iT] = topic
    # ---- assertions: the point of this step is that a per-paper query can no longer miss rows
    bad = []
    for r in body:
        toks = [t.strip() for t in r[iP].split(";") if t.strip()]
        if not toks or any(t not in (PAPERS | {"programme"}) for t in toks):
            bad.append((r[0], r[iP]))
        if r[iT] and not re.fullmatch(r"T\d+(-T\d+)?", r[iT]):
            bad.append((r[0], "topic:" + r[iT]))
    if bad:
        raise SystemExit(f"[e78] ABORT: paper_id/topic_id vocabulary still violated by {len(bad)} rows: {bad[:8]}")
    for old, new in zip(before, body):
        if old[:iP] != new[:iP] or old[iP + 1:iT] != new[iP + 1:iT]:
            raise SystemExit(f"[e78] ABORT: a column other than paper_id/topic_id changed at {new[0]}")
    assert len(body) == len(before)

    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\r\n")
    w.writerow(hdr)
    w.writerows(body)
    P.write_text(buf.getvalue(), encoding="utf-8", newline="")
    import collections
    tally = collections.Counter(r[iP] for r in body)
    per_paper = {p: sum(1 for r in body if p in r[iP].split(";")) for p in sorted(PAPERS)}
    print(f"[e78] {len(body)} rows, {moved} paper_id values normalised; per-paper: {per_paper}")
    print(f"[e78] full tally: {json.dumps(dict(tally), ensure_ascii=False)}")

    # ---- teach the audit the vocabulary, so the drift cannot return silently
    A = ROOT / "02_shared_code" / "registry" / "package_audit.py"
    a = A.read_text(encoding="utf-8")
    marker = "def audit_paper("
    if "registry_paper_id_vocabulary" not in a:
        a = a.replace(marker, '''def registry_paper_id_vocabulary(program_dir: Path):
    """EXP-0078: paper_id must be P001-P005, `programme`, or a ';' join of those. Before this check the column mixed
    topic ids with paper ids, which made a per-paper query silently return nothing for P002."""
    import csv as _csv, io as _io, re as _re
    p = program_dir / "experiment_registry.csv"
    rows = list(_csv.DictReader(_io.StringIO(p.read_text(encoding="utf-8"))))
    bad = [r["exp_id"] for r in rows
           if not all(t.strip() in {"P001", "P002", "P003", "P004", "P005", "programme"}
                      for t in (r.get("paper_id") or "").split(";") if t.strip())]
    return {"rows": len(rows), "violations": bad}


''' + marker, 1)
    a = a.replace('    return {"experiments": len(df)',
                  '    return {"registry_paper_id_vocabulary": registry_paper_id_vocabulary(PROGRAM),\n'
                  '            "experiments": len(df)', 1)
    A.write_text(a, encoding="utf-8", newline="")
    print("[e78] package_audit gained the paper_id vocabulary check")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
