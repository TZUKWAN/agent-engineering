"""EXP-0069: a stricter, documented anchor filter for P004's collision screen - and a re-read of what survives it.

EXP-0068 showed the frozen EXP-0057 screen is uninformative for P004: its object family contains the bare words
`rating`, `score`, `label` and `judge`, so a menopause-rating-scale validity study clears L3 alongside the papers that
actually matter. The directly-relevant count for that paper cannot be built on such a screen, and the answer is not to
loosen a threshold but to add a requirement the rule was never given: **the work must be about text produced by a
model.**

This is deliberately NOT a change to `grade_collisions.py`. The frozen rule stays byte-identical because EXP-0057,
EXP-0064 and every `level_final` already recorded depend on it. Instead an anchor predicate is applied *after* the
frozen grade, so both levels are stored per record, the tightening is visible, and it can only ever remove candidates
- it cannot promote anything the frozen rule rejected. Registered as a protocol amendment (deviation) because it is a
new criterion introduced after a result was seen; it is applied to P004's expansion only, and the records it removes
are listed rather than deleted.

    python anchor_screen_p004.py
"""
from __future__ import annotations

import csv, io, json, pathlib, random, re, sys, time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from grade_collisions import grade  # noqa: E402 - the frozen rule, still the first gate

ROOT = HERE.parents[1]
REG = ROOT / "00_program_registry"
SRC = REG / "literature_p004_expansion.csv"
OUT = REG / "literature_p004_expansion_anchored.csv"
SUM = ROOT / "results_raw" / f"EXP0069_p004_anchored_screen_{time.strftime('%Y%m%dT%H%M%S')}.json"
ANCHOR = ["llm", "large language model", "gpt", "chatbot", "generated text", "text generation", "nlg",
          "natural language generation", "model output", "machine-generated", "code generation",
          "summarization", "summarisation", "machine translation", "dialogue system", "agent trajectory",
          "instruction-tuned", "foundation model", "prompt"]
SAMPLE_N = 12


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    if not SRC.exists():
        raise SystemExit("[e69] run EXP-0068 first; its expansion file is the input.")
    rows = list(csv.DictReader(io.StringIO(SRC.read_text(encoding="utf-8"))))
    kept = dropped = 0
    for r in rows:
        blob = (r["title"] + " " + r["abstract"]).lower()
        hits = [a for a in ANCHOR if a in blob]
        r["anchor_hits"] = json.dumps(hits, ensure_ascii=False)
        r["level_frozen_rule"] = r["level_rule"]
        l2 = r["level_rule"] in ("L2", "L3", "L4")
        r["passes_anchor"] = "1" if (l2 and hits) else "0"
        if l2:
            kept += int(bool(hits))
            dropped += int(not hits)
        # the reported level is the frozen grade only where the anchor also holds; elsewhere it is downgraded, never up
        if l2 and not hits:
            r["level_rule"] = "L1 (frozen L2+ but no model-produced-text anchor)"
    fields = list(rows[0].keys())
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\r\n", extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
    OUT.write_text(buf.getvalue(), encoding="utf-8", newline="")

    survivors = [r for r in rows if r["passes_anchor"] == "1"]
    readable = [r for r in survivors if int(r["abstract_chars"] or 0)]
    sample = random.Random(11).sample(readable, min(SAMPLE_N, len(readable)))
    res = {"exp_id": "EXP-0069", "in": SRC.name, "out": OUT.name,
           "records": len(rows), "frozen_L2plus": kept + dropped, "survived_anchor": kept,
           "removed_by_anchor": dropped, "survivors_readable": len(readable),
           "anchor_terms": ANCHOR,
           "sample": [{"title": r["title"][:120], "venue": r["venue"][:44], "year": r["year"],
                       "anchor_hits": r["anchor_hits"], "abstract": r["abstract"][:220]} for r in sample],
           "survivor_titles": [{"title": r["title"][:130], "venue": r["venue"][:44], "year": r["year"],
                                "level": r["level_frozen_rule"]} for r in survivors],
           "direction_of_change": "strictly narrowing: the anchor can only demote a frozen L2+ grade, never promote",
           "at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    SUM.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8", newline="")
    print(json.dumps({k: v for k, v in res.items() if k not in ("sample", "survivor_titles", "anchor_terms")},
                     indent=1), flush=True)
    print("\nsample read:")
    for s in res["sample"]:
        print(f"  - {s['title'][:92]} ({s['venue'][:26]}, {s['year']}) anchors={s['anchor_hits'][:60]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
