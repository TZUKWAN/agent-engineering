"""EXP-0106 (spec E02 + E04 for P003): what the census is compared against, and where its coverage actually comes from.

P003's E-coverage statement (EXP-0103) reported two steps open: **E02 基础基线** - nothing showed the headline is not
what any reader could get by matching field names - and **E04 消融实验** - nothing answered "逐项拿掉核心信息源/核心规
则，结论还剩多少". Both are answerable from the audit's own stored evidence: every cell of EXP-0029/EXP-0030 records
each candidate that was tried (`kind`, `source`, `coverage`), not only the winner, so the ablations are recomputations
of the published statistic on a restricted rule set rather than new passes over the corpora.

Headline statistic, fixed before this run and identical to the one the frozen kill-gate uses:
`concepts_direct_or_derived_in_7_of_8` - how many of the twelve concepts are carried or recoverable in at least seven of
the eight releases.

Baselines (E02):
  * `name_equality_only` - a concept counts only where a **directly named** field covers >= 95% of the sampled rows:
    what a reader with the schema and no rules would conclude;
  * `any_direct_mention` - a concept counts where any directly named field covers > 0%: the most generous naive rule;
  * `random_marginal` - 10,000 seeded draws of cell states from the observed marginal over the 96 cells: what the
    headline would look like if the states were assigned without looking at the releases.

Ablations (E04), each re-scoring every cell from its stored evidence list:
  * `drop_derived_rules` - keep only direct evidence entries (the instrument's recovery rules removed);
  * `drop_top_candidate` - remove the highest-coverage entry of each cell and re-score from the rest (is one field
    carrying the result?);
  * `leave_one_corpus_out` - recompute the headline on seven releases, once per release, naming any release whose
    removal moves the number;
  * `leave_one_concept_out` - report, per concept, how many releases carry it, so the concept that props up the
    headline is visible rather than averaged away.

No threshold is moved and no arm is dropped: every number is written to the artefact and to
`results_processed/EXP0106_*.csv`, and the verdict sentence states the smallest coverage among the arms, because the
point of the exercise is to find out how much of the finding is the rules, not to protect the finding.

    python 02_shared_code/data_audit/p003_ablation_and_baselines.py [--source EXP0030]
"""
from __future__ import annotations
import argparse, collections, glob, json, pathlib, random, sys, time

ROOT = next(a for a in [pathlib.Path(__file__).resolve().parent,
                        *pathlib.Path(__file__).resolve().parents] if (a / "00_program_registry").is_dir())
RAW, PROC = ROOT / "results_raw", ROOT / "results_processed"
MIN_CORPORA = 7            # the published statistic: in at least seven of the eight releases
DIRECT_STRONG = 0.95       # "carried by a named field" as the auditor itself defines it
DRAWS = 10_000
SEED = 42


def score(cell: str, arm: str):
    """State of one (corpus, concept) cell under an ablated rule set, read from its stored evidence list."""
    ev = cell.get("evidence") or []
    if arm == "audited":
        return cell.get("state")
    if arm == "drop_derived_rules":
        keep = [e for e in ev if e.get("kind") == "direct"]
    elif arm == "drop_top_candidate":
        ranked = sorted(ev, key=lambda e: -float(e.get("coverage") or 0))
        keep = ranked[1:]
    elif arm.startswith("name_equality_only"):
        keep = [e for e in ev if e.get("kind") == "direct" and float(e.get("coverage") or 0) >= DIRECT_STRONG]
    elif arm.startswith("any_direct_mention"):
        keep = [e for e in ev if e.get("kind") == "direct" and float(e.get("coverage") or 0) > 0]
    else:
        raise SystemExit(f"unknown arm {arm}")
    if not keep:
        return "absent"
    if all(e.get("kind") == "direct" for e in keep):
        return "direct"
    return "derived"


def headline(cells_by_corpus_concept, arms, corpora, concepts):
    """How many concepts clear `MIN_CORPORA` releases, per arm."""
    out = {}
    for arm in arms:
        good = 0
        per_concept = {}
        for c in concepts:
            n = sum(1 for k in corpora
                    if score(cells_by_corpus_concept[(k, c)], arm) in ("direct", "derived"))
            per_concept[c] = n
            good += n >= MIN_CORPORA
        out[arm] = {"concepts_in_7_of_8": good, "per_concept_release_counts": per_concept}
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="EXP0030", help="which published conformance run to re-score")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    files = sorted(glob.glob(str(RAW / f"{a.source}_p003_conformance_main_*.json")))
    if not files:
        raise SystemExit(f"ABORT: no {a.source} conformance artefact to re-score")
    src = pathlib.Path(files[-1])
    d = json.loads(src.read_text(encoding="utf-8"))
    corpora = sorted(d["corpora"])
    concepts = sorted(d["corpora"][corpora[0]]["cells"])
    cells = {(k, c): d["corpora"][k]["cells"][c] for k in corpora for c in concepts}
    missing = [key for key, v in cells.items() if not isinstance(v, dict) or "evidence" not in v]
    if missing:
        raise SystemExit(f"ABORT: {len(missing)} cells carry no evidence list, e.g. {missing[:3]} - the ablation would "
                         f"report them as absent when in fact they were never checked")
    published_stored = d.get("concepts_direct_or_derived_in_7_of_8")
    cov = d.get("coverage_by_concept") or {}
    arms = ["audited", "name_equality_only", "any_direct_mention", "drop_derived_rules", "drop_top_candidate"]
    res = headline(cells, arms, corpora, concepts)
    published = res["audited"]["concepts_in_7_of_8"]
    # two independent records in the artefact have to agree with the re-scoring: the per-concept release counts, and
    # the headline field when the run that wrote it stored one. A disagreement is a provenance finding, not a nuisance
    if cov:
        from_counts = sum(1 for n in cov.values() if n >= MIN_CORPORA)
        if from_counts != published:
            raise SystemExit(f"ABORT: coverage_by_concept implies {from_counts} concepts in >= {MIN_CORPORA} releases "
                             f"but re-scoring the cells gives {published}")
        for c, n in cov.items():
            mine = res["audited"]["per_concept_release_counts"].get(c)
            if mine is not None and mine != n:
                raise SystemExit(f"ABORT: {c} is recorded as present in {n} releases, cells say {mine}")
    if isinstance(published_stored, list) and len(published_stored) != published:
        raise SystemExit(f"ABORT: the artefact publishes {len(published_stored)} but the cells give {published}")

    # jackknife over information sources: the releases themselves
    jack = {}
    for drop in corpora:
        kept = [k for k in corpora if k != drop]
        good = sum(1 for c in concepts
                   if sum(1 for k in kept if score(cells[(k, c)], "audited") in ("direct", "derived")) >= MIN_CORPORA - 1)
        jack[drop] = {"concepts_in_7_of_8_minus_one_corpus": good,
                      "moves_the_headline": good != published}

    marginal = collections.Counter(score(v, "audited") for v in cells.values())
    rng = random.Random(SEED)
    states = list(marginal)
    weights = [marginal[s] for s in states]
    null = collections.Counter()
    for _ in range(DRAWS):
        rnd = {(k, c): rng.choices(states, weights)[0] for k in corpora for c in concepts}
        good = sum(1 for c in concepts
                   if sum(1 for k in corpora if rnd[(k, c)] in ("direct", "derived")) >= MIN_CORPORA)
        null[good] += 1
    exceed = sum(v for k, v in null.items() if k >= published)
    return_res = {
        "exp_id": "EXP-0106", "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "re_scores": src.name, "seed": SEED, "min_corpora": MIN_CORPORA, "direct_strong": DIRECT_STRONG,
        "draws": DRAWS, "published_headline": published,
        "baselines": {k: v for k, v in res.items() if k in ("name_equality_only", "any_direct_mention")},
        "ablations": {k: v for k, v in res.items() if k in ("drop_derived_rules", "drop_top_candidate")},
        "audited_reproduced": res["audited"],
        "random_marginal_null": {"state_counts": dict(marginal), "headline_distribution": dict(sorted(null.items())),
                                 "p_ge_published": round(exceed / DRAWS, 5), "draws": DRAWS},
        "leave_one_corpus_out": jack,
        "cell_state_counts": dict(marginal),
    }
    worst = min([v["concepts_in_7_of_8"] for v in res.values()])
    best_arm = min(res, key=lambda k: res[k]["concepts_in_7_of_8"])
    facts = []
    if res["name_equality_only"]["concepts_in_7_of_8"] < published:
        facts.append(f"it is not trivial: matching field names alone yields "
                     f"{res['name_equality_only']['concepts_in_7_of_8']} of the {published}")
    if res["drop_derived_rules"]["concepts_in_7_of_8"] < published:
        facts.append(f"{published - res['drop_derived_rules']['concepts_in_7_of_8']} of the {published} come from the "
                     f"recovery rules rather than from a named field")
    if res["drop_top_candidate"]["concepts_in_7_of_8"] < published:
        facts.append("each surviving concept rests on a single field: removing one best candidate per cell takes the "
                     f"headline to {res['drop_top_candidate']['concepts_in_7_of_8']}, so the census is a "
                     "single-source claim, not a redundantly supported one")
    facts.append(f"the smallest coverage over all arms is {worst}, reached under `{best_arm}`")
    facts.append("chance is excluded but thinness is not"
                 if return_res["random_marginal_null"]["p_ge_published"] < 0.05 else
                 "the headline is inside what chance would give")
    return_res["verdict"] = "; ".join(facts) + "."
    stamp = time.strftime("%Y%m%dT%H%M%S")
    (RAW / f"EXP0106_p003_ablation_baselines_{stamp}.json").write_text(
        json.dumps(return_res, indent=1, ensure_ascii=False), encoding="utf-8")
    import csv as _csv
    with open(PROC / "EXP0106_ablation_and_baselines.csv", "w", newline="", encoding="utf-8") as fh:
        w = _csv.writer(fh)
        w.writerow(["arm", "kind", "concepts_direct_or_derived_in_7_of_8", "per_concept_release_counts",
                    "moves_vs_published"])
        for arm in arms:
            w.writerow([arm, "baseline" if arm in ("name_equality_only", "any_direct_mention") else "ablation",
                        res[arm]["concepts_in_7_of_8"],
                        json.dumps(res[arm]["per_concept_release_counts"], ensure_ascii=False),
                        res[arm]["concepts_in_7_of_8"] - published])
        w.writerow(["random_marginal", "baseline", f"p(>= {published}) = "
                    f"{return_res['random_marginal_null']['p_ge_published']}", "", ""])
        for drop, v in sorted(jack.items()):
            w.writerow([f"leave_out:{drop}", "jackknife", v["concepts_in_7_of_8_minus_one_corpus"], "",
                        "yes" if v["moves_the_headline"] else "no"])
    print(f"  published headline: {published} concepts in >= {MIN_CORPORA} of {len(corpora)} releases")
    for arm in arms:
        print(f"  {arm:22s} -> {res[arm]['concepts_in_7_of_8']}")
    print(f"  random-marginal null: p(>= {published}) = {return_res['random_marginal_null']['p_ge_published']} "
          f"over {DRAWS} draws")
    print("  corpus jackknife moves the headline for:",
          [k for k, v in jack.items() if v["moves_the_headline"]] or "none")
    print("  verdict:", return_res["verdict"])
    print(f"  wrote EXP0106_*.json + EXP0106_ablation_and_baselines.csv ({round(time.time() - t0, 1)} s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
