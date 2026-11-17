"""EXP-0117: rank the live round-5 topics into a queue, on measured evidence, before anything is frozen.

Spec §20 forbids running dozens of main experiments at once and asks for a bounded queue, and the user's instruction on
2026-09-23 is to complete all 86 new topics to the same standard as the five packaged papers. So the order in which
they are attempted has to be a measurement, not a preference. Four inputs, all already on disk:

1. **data thickness** - the row count of the release the topic names, and the concept-coverage census EXP-0116 wrote;
2. **distinctness** - the construct overlap EXP-0116 computed against the five packaged papers and the other live
   topics (a topic that barely differs from P001 is last, not first);
3. **crowding margin** - the strong-title-hit count EXP-0115 got from the literature channels;
4. **offline executability** - whether the comparison the design needs already exists on disk as a natural experiment
   (four teacher configurations in Toucan, ~100 rollouts of the same PR in SWE-ZERO, the RR/ORR pair in MMAT, 19
   environments in AgentBank, separated thought/action in hermes) or whether it requires *running an agent with edited
   inputs*, which this programme cannot do: no model inference API is allowed during analysis, and a replay harness that
   re-scores a frozen retriever is a different, permitted thing. Topics whose core contrast needs a live agent are
   ranked into the `needs_agent_runtime` band and stated as such rather than quietly answered with a proxy.

    python 02_shared_code/registry/topic_queue_rank.py [--wave-size 5]
"""
from __future__ import annotations

import argparse, csv, datetime, io, json, pathlib, re, sys, time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = next(a for a in (HERE, *HERE.parents) if (a / "00_program_registry").is_dir())
REG, TOP = ROOT / "00_program_registry" / "experiment_registry.csv", ROOT / "00_program_registry" / "topic_registry.csv"
RAW = ROOT / "results_raw"
MAN = ROOT / "01_datasets" / "manifests"

# the contrast a design needs, and whether the estate already contains it
AGENT_ONLY = re.compile(r"rewrite|rewrit|inject|add\b.*description|controlled tool descriptions|build flat|hierarch|"
                        r"faceted|normalis.*vocab|counterfactual|replay with|give the agent|framed as|retrieve similar|"
                        r"compare no-memory|insert|manipulat|randomi[sz]e the|assign", re.I)
NATURAL = {
 "Toucan-1.5M": "4 teacher configs (OSS/Qwen3/Kimi-K2/SFT) + an irrelevant subset + per-query candidate catalogues",
 "SWE-ZERO-12M": "~100 rollouts of the same instance_id (317 instances / 20k trajectories) + exit_status",
 "AgentTrove": "multiple teachers/models per trial + result/judgment labels",
 "MMAT-1M": "RR and ORR variants of the same item (a compression pair already on disk)",
 "hermes-agent-reasoning-traces": "separated thought / action / observation in conversations + tools + category",
 "AgentBank": "19 environment configs (game_file/meta_information) over one schema",
 "code-act": "two configs, code actions vs general actions",
 "AgentInstruct": "one config, conversations only - no outcome label",
}


def latest(pat):
    h = sorted(RAW.glob(pat))
    return json.loads(h[-1].read_text(encoding="utf-8", errors="replace")) if h else {}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--wave-size", type=int, default=5)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    topics = list(csv.DictReader(io.StringIO(TOP.read_text(encoding="utf-8"))))
    live = [t for t in topics if t["status"].startswith("w1_audit_done")]
    f115 = latest("EXP0115_funnel_screen_round5_*.json")
    f116 = latest("EXP0116_funnel_retriage_*.json")
    crowding = {x["topic_id"]: x for x in f115.get("topics", [])}
    tri = f116.get("decided", {})
    pairs = {p[0]: p for p in f116.get("top_pair_evidence", [])}
    rows = {}
    for f in sorted(MAN.glob("*.audit.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        rows[f.name.replace(".audit.json", "")] = sum(int(c.get("total_rows_all_files") or 0)
                                                      for c in (d.get("configs") or {}).values())
    scored = []
    for t in live:
        tid = t["topic_id"]
        ds = t["primary_dataset"]
        thick = rows.get(ds, 0)
        cen = tri.get(tid, {}).get("census", {}) or {}
        cov = [v for v in cen.values() if isinstance(v, (int, float))]
        cover = sum(cov) / max(1, len(cen)) if cen else None
        near = max((pairs.get(tid) or [0, "", 0, "", 0])[2::2] or [0])
        strong = sum(1 for ch in (crowding.get(tid, {}).get("reason", "")).split(";") if "strong" in ch) \
            if "strong" in crowding.get(tid, {}).get("reason", "") else 0
        m = re.search(r"collision (\d+) strong", crowding.get(tid, {}).get("reason", ""))
        strong = int(m.group(1)) if m else 0
        need_agent = bool(AGENT_ONLY.search(t["main_method"] or ""))
        band = ("needs_agent_runtime" if need_agent and not NATURAL.get(ds) else
                "natural_experiment_available" if NATURAL.get(ds) else "offline_replay_only")
        score = (0 if need_agent else 3) + (2 if thick >= 1_000_000 else 1 if thick >= 50_000 else 0) \
            + (1 if cover and cover >= 0.5 else 0) - (1 if near >= 4 else 0) - (1 if strong >= 2 else 0)
        scored.append((score, tid, t, dict(rows_thick=thick, concept_coverage=(round(cover, 4) if cover else None),
                                           construct_overlap=near, strong_hits=strong, band=band)))
    scored.sort(key=lambda x: (-x[0], x[1]))
    # a wave must be mutually distinct: T108/T109/T110 all score 6 and all ask "when does lexical similarity stop
    # meaning relevance", so taking the top N by score alone would run three near-identical designs at once, which is
    # the thing §20's queue discipline exists to prevent. Select greedily, skipping anything whose nearest neighbour in
    # the wave shares >= 3 constructs.
    wave, skipped = [], []
    for entry in scored:
        tid = entry[1]
        near = (pairs.get(tid) or [0, "", 0, "", 0])
        if (near[2] + near[4]) >= 3 and wave:
            skipped.append(tid); continue
        wave.append(entry)
        if len(wave) >= a.wave_size:
            break
    out = ROOT / "00_program_registry" / "topic_queue_round5.csv"
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["rank", "topic_id", "queue_score", "band", "rows_in_primary_release", "concept_coverage",
                    "construct_overlap_with_nearest", "strong_literature_hits", "title_en", "next_step"])
        for i, (sc, tid, t, ev) in enumerate(scored, 1):
            w.writerow([i, tid, sc, ev["band"], ev["rows_thick"], ev["concept_coverage"], ev["construct_overlap"],
                        ev["strong_hits"], t["title_en"][:120],
                        "freeze protocol, then pilot" if tid in {w_[1] for w_ in wave} else
                        ("queued behind a similar design" if tid in skipped else "queued")])
    stamp = time.strftime("%Y%m%dT%H%M%S")
    art = {"exp_id": "EXP-0117", "finished_at": datetime.datetime.now().isoformat(timespec="seconds"),
           "rule": __doc__.split("python 02_shared_code")[0][-1200:], "live_topics": len(live),
           "bands": {b: sum(1 for s in scored if s[3]["band"] == b) for b in {s[3]["band"] for s in scored}},
           "wave_1": [{"topic_id": tt, "score": ss, **ee} for ss, tt, _xx, ee in wave],
           "wave_1_skipped_for_similarity": skipped,
           "queue_file": "00_program_registry/topic_queue_round5.csv"}
    (RAW / f"EXP0117_topic_queue_rank_{stamp}.json").write_text(json.dumps(art, ensure_ascii=False, indent=1),
                                                                encoding="utf-8")
    print(f"  {len(live)} live topics ranked -> {out.name}")
    print("  bands:", art["bands"])
    for sc, tid, t, ev in wave:
        print(f"  wave 1: {tid} score {sc} {ev['band']} rows={ev['rows_thick']:,} cov={ev['concept_coverage']} "
              f"| {t['title_en'][:58]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
