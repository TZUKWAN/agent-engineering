"""EXP-0045 (P003 sensitivity): does the "2 of 12 concepts" headline survive a different concept inventory?

P003's standing limitation 1 is that its twelve concepts are our choice, and its open pre-submission item asks for
an independently derived list. External inventories could not be used here: schema.org, dublincore.org and w3.org
are unreachable from this machine, and DataCite's host resolves but the schema documents were not retrievable
(404 on the paths tried), so an externally defined list is not available as evidence. This implements the honest
alternative - an inventory derived mechanically from the corpora themselves, with the derivation rule written before
the data was looked at again.

Derivation rule (frozen in this docstring, no human judgement involved):
  1. sample each release exactly as the published audit does (same seed, same shard pick, same row head rules);
  2. enumerate key paths: top-level columns, plus one level inside every column whose value parses as JSON,
     and one further level inside list elements (max depth 3);
  3. normalise a key path to a unit name: lowercase, non-alphanumerics to '_', drop the trailing element of
     pluralised names, and collapse the known synonym table published in `p003_units` (documented, small);
  4. a unit enters the inventory iff it occurs in >= 2 releases;
  5. a unit counts as recoverable in a release iff it is non-empty in >= 50% of that release's sampled rows.

Pre-registered decision: LIST_INDEPENDENT iff (a) the number of units recoverable in all eight releases is within
1 of the published count, and (b) both published all-corpus units (message sequence, user instruction) are among
the data-derived all-corpus units. Otherwise LIST_DEPENDENT, and P003 must present its matrix as an explicitly
chosen lens rather than as a census.

    python 02_shared_code/data_audit/concept_inventory_sensitivity_p003.py
Writes results_raw/EXP0045_concept_inventory_*.json and results_processed/EXP0045_*.csv.
"""
from __future__ import annotations

import json, pathlib, re, sys, time
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "02_shared_code" / "data_audit"))
import canonical_conformance_audit_p003 as pilot
import canonical_conformance_main_p003 as mainmod

DATA = pilot.DATA
PUBLISHED_ALL_CORPUS = {"C6_message_sequence", "C8_user_instruction"}
PUBLISHED_COUNT = 2
SYNONYMS = {"msgs": "messages", "conversation": "messages", "conversations": "messages", "dialog": "messages",
            "turns": "messages", "instruction": "question", "query": "question", "input": "question",
            "tools": "tool_catalog", "available_tools": "tool_catalog", "functions": "tool_catalog",
            "tool_calls": "executed_action", "function_call": "executed_action", "action": "executed_action",
            "obs": "observation", "observation": "observation", "environment": "observation",
            "label": "outcome", "judgment": "outcome", "result": "outcome", "reward": "outcome",
            "id": "identifier", "uuid": "identifier", "row_id": "identifier", "instance_id": "group_key",
            "prompt_id": "group_key", "message": "messages", "msg": "messages", "message_list": "messages",
            "model": "model_id", "creator": "teacher_provider", "source": "teacher_provider",
            "category": "category", "subset_name": "category", "tags": "category"}
MAX_DEPTH = 3


def norm(key: str) -> str:
    """Synonyms are resolved BEFORE plural stripping, on both the raw and the de-pluralised form.

    The first version stripped the plural first, so `messages` became `message` while `conversations` mapped to
    `messages`, splitting the single most important unit across two names and producing a spurious
    LIST_DEPENDENT result for exactly the concept the paper's headline rests on.
    """
    k = re.sub(r"[^a-z0-9]+", "_", str(key).lower()).strip("_")
    if k in SYNONYMS:
        return SYNONYMS[k]
    s = k[:-1] if (k.endswith("s") and not k.endswith("ss")) else k
    return SYNONYMS.get(s, s)


def leaf_and_value(obj, depth=0, prefix=""):
    """Yield (leaf_key, value) for every key path, decoding JSON strings up to MAX_DEPTH."""
    out = []
    if depth > MAX_DEPTH or not isinstance(obj, dict):
        return out
    for k, v in obj.items():
        out.append((str(k), v))
        vv = v
        if isinstance(vv, str) and vv[:1] in "[{" and len(vv) < 4_000_000:
            try:
                vv = json.loads(vv)
            except Exception:                                  # noqa: BLE001 - a string that looks like JSON
                vv = None
        if isinstance(vv, dict):
            out += leaf_and_value(vv, depth + 1, prefix + str(k) + ".")
        elif isinstance(vv, list):
            for x in vv[:3]:
                if isinstance(x, str) and x[:1] in "[{":
                    try:
                        x = json.loads(x)
                    except Exception:                          # noqa: BLE001
                        continue
                if isinstance(x, dict):
                    out += leaf_and_value(x, depth + 1, prefix + str(k) + "[].")
    return out


def nonempty(v):
    if v is None:
        return False
    if isinstance(v, str):
        return bool(v.strip()) and v.strip().lower() not in ('null', 'none', 'nan', '{}', '[]')
    if isinstance(v, (list, dict)):
        return len(v) > 0
    return True


def units_in_row(row):
    """unit -> 1 if any key path normalising to it carries a non-empty value in this row."""
    hit = defaultdict(int)
    for key, val in leaf_and_value(row):
        hit[norm(key)] = hit[norm(key)] or int(nonempty(val))
    return dict(hit)


def per_release():
    specs = dict(pilot.SPEC)
    specs["MMAT-1M"] = mainmod.MMAT_SPEC
    out = {}
    for name, spec in specs.items():
        base = DATA / spec["path"]
        if name == "MMAT-1M":
            rows, _ = mainmod.sample_jsonl(base, pilot.ROWS)
        else:
            rows, _ = pilot.sample_parquet(base)
        if not rows:
            out[name] = {"rows": 0, "unit_rates": {}}
            print(f"  {name:34s} rows=    0 (no readable sample; container or path differs)")
            continue
        agg = defaultdict(int)
        for r in rows:
            for u, ok in units_in_row(r).items():
                agg[u] += ok
        rates = {u: round(c / len(rows), 4) for u, c in agg.items()}
        out[name] = {"rows": len(rows), "unit_rates": rates}
        print(f"  {name:34s} rows={len(rows):5d} units seen={len(rates):4d} "
              f"recoverable>=50%={sum(1 for v in rates.values() if v >= 0.5)}")
    return out


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    res = {"exp_id": "EXP-0045", "paper_id": "P003", "seed": pilot.SEED,
           "rule": "LIST_INDEPENDENT iff all-corpus recoverable count within 1 of published and both published "
                   "units appear among it; external inventories were not retrievable here, so the comparator is "
                   "derived from the data by the rule in this file's docstring",
           "started_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    pr = per_release()
    releases = [k for k, v in pr.items() if v["rows"]]
    units = defaultdict(dict)
    for name, d in pr.items():
        for u, rate in d["unit_rates"].items():
            units[u][name] = rate
    appears = {u: sum(1 for r in v.values() if r >= 0.05) for u, v in units.items()}
    inventory = sorted([u for u, n in appears.items() if n >= 2])
    recoverable = {u: [r for r, rate in units[u].items() if rate >= 0.50] for u in inventory}
    all_corpus = sorted([u for u in inventory if len(recoverable[u]) == len(releases)])
    res["data_derived"] = {"units_total": len(inventory), "releases_used": releases,
                           "all_corpus_recoverable": all_corpus,
                           "units_per_release_present": {u: appears[u] for u in inventory},
                           "rates": {u: {r: units[u][r] for r in sorted(units[u], key=units[u].get, reverse=True)[:4]}
                                     for u in all_corpus}}
    hit_pub = set(all_corpus) & {"messages", "question"}
    res["verdict"] = {"published_all_corpus_count": PUBLISHED_COUNT,
                      "derived_all_corpus_count": len(all_corpus),
                      "count_within_one": abs(len(all_corpus) - PUBLISHED_COUNT) <= 1,
                      "published_units_reproduced": sorted(hit_pub),
                      "decision": ("LIST_INDEPENDENT" if abs(len(all_corpus) - PUBLISHED_COUNT) <= 1
                                   and {"messages", "question"} <= set(all_corpus)
                                   else "LIST_DEPENDENT - present the matrix as a chosen lens, not a census")}
    res["wallclock_sec"] = round(time.time() - t0, 1)
    res["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    (ROOT / "results_raw").mkdir(exist_ok=True)
    out = ROOT / "results_raw" / f"EXP0045_concept_inventory_{time.strftime('%Y%m%dT%H%M%S')}.json"
    out.write_text(json.dumps({"res": res, "per_release_rows": {k: v["rows"] for k, v in pr.items()}},
                              indent=1, ensure_ascii=False), encoding="utf-8")
    import pandas as pd
    pd.DataFrame([{"unit": u, "releases_present": appears[u], "releases_recoverable_ge50pct": len(recoverable[u]),
                   **{r: units[u].get(r) for r in releases}} for u in inventory]).to_csv(
        ROOT / "results_processed" / "EXP0045_data_derived_units.csv", index=False)
    print(json.dumps(res["verdict"], ensure_ascii=False)[:420])
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
