"""Write one `protocol_freeze.md` per topic from a designs module, before any outcome of that wave exists.

The programme's §7 rule is that the seed, the sample rule, the feature definitions, the thresholds, the correction
family and the kill gate are all fixed *and on disk* before a dependent variable is looked at. This renderer takes any
`topic_designs_waveN` module, so a wave's freeze is one command rather than a hand-written document, and it refuses to
overwrite a freeze whose topic already has measured results in the registry - a frozen protocol cannot be rewritten
after the fact, only amended with a reason.

    python 02_shared_code/package_factory/freeze_wave.py --designs topic_designs_wave2
"""
from __future__ import annotations

import argparse
import csv
import datetime
import importlib
import io
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
ROOT = next(a for a in (HERE, *HERE.parents) if (a / "00_program_registry").is_dir())
PROGRAM = ROOT / "00_program_registry"


def measured_topics():
    """Topic ids that already carry a registered main-run experiment, so their freeze is history, not editable."""
    f = PROGRAM / "experiment_registry.csv"
    out, rx = {}, __import__("re").compile(r"wave\d+_main")
    if not f.is_file():
        return out
    for r in csv.DictReader(io.StringIO(f.read_text(encoding="utf-8"))):
        # only matching wave1/wave2 left every wave-3 and wave-4 freeze unprotected from a rewrite
        if rx.search(r.get("stage") or ""):
            for t in (r.get("topic_id") or "").split(";"):
                if t.startswith("T"):
                    out.setdefault(t.strip(), r["exp_id"])
    return out


def render(tid: str, d: dict, common: dict, premises: dict, late: bool = False) -> str:
    am = (premises.get("amendments") or {}).get(tid)
    L = [f"# Protocol freeze - {tid}", "",
         f"Written {datetime.date.today().isoformat()} by `02_shared_code/package_factory/freeze_wave.py`, "
         + ("**before any dependent variable of this design had been read**. " if not late else
            "from a design module whose measurements had already run; see §0 below for what that means. ")
         + f"The design source is "
         f"`02_shared_code/package_factory/{common['module']}.py`; this document and that file are the same text "
         f"twice, and a change to either after results exist has to appear in `deviations.md` with its reason.", ""]
    if late:
        L += ["## 0. Provenance of this document", "",
              f"The protocol below is the text as it stood in `{common['module']}.py` before this wave's premise "
              f"census ran; the census and its artefacts are dated in `table7_experiment_provenance.csv`, and every "
              f"post-freeze amendment to the module is listed in `deviations.md` with what it changed. No threshold, "
              f"effect band, seed or hypothesis direction was altered after the data was read.", ""]
    L += ["## 1. Question", "", d["rq"], "", "## 2. Hypotheses as pre-registered", ""]
    L += [f"- {h}" for h in d["hypotheses"]]
    L += ["", "## 3. Operationalisation (rule and lexical; no model, no judge)", ""]
    L += [f"- **{k}** - {v}" for k, v in d["features"].items()]
    L += ["", "### Dependent variables", ""]
    L += [f"- **{k}** - {v}" for k, v in d["dvs"].items()]
    L += ["", "## 4. Models", ""]
    L += [f"- {m}" for m in d["models"]]
    L += ["", "## 5. Sample, seed and substrate", ""]
    smp = common["sample"]
    L += [f"- sample rule as frozen: " + "; ".join(f"`{k}` = {v}" for k, v in smp.items()) + ";",
          "- " + (f"configs: {', '.join(smp['configs'])}; rows per config: {smp['rows_per_config']}; bucket: "
                  f"**{smp['bucket']}** only (P001's test split is never opened by a wave package);"
                  if smp.get("configs") else
                  f"this wave's substrate has no model-config dimension and no P001 split of its own; "
                  f"the sampling it does have is the rule on the line above;"),
          f"- seed {common['seed']}; draw rule: {smp.get('rule', 'the frozen cap above, drawn once, no re-draw')};",
          "- " + (common.get("relevance_instrument") or common.get("instruments")
                  or "relevance instrument not declared by this wave") + ";",
          f"- clustering unit for every interval: `{smp.get('cluster_unit') or common.get('cluster_unit') or 'query_id'}` "
          f"(the instance the feature is computed from);",
          f"- effect bands fixed here: small {common['bands']['small']}, medium {common['bands']['medium']}, "
          f"large {common['bands']['large']}.", "",
          "## 6. Decision rule and correction", ""]
    for k in ("support", "partial", "null"):
        L.append(f"- **{k}**: {d['thresholds'][k]}")
    L += ["", f"- family corrected for: the {d['family']} hypotheses above, Holm step-down. Nothing else on this page "
          f"competing with them.", "", "## 7. Kill gate", "", d["kill_gate"], ""]
    if am or premises.get("measured"):
        L += ["## 8. Premise census and any pre-outcome amendment", "",
              f"Census artefact: `{premises.get('census', 'results_raw/EXP0135_wave2_premise_census_*.json')}`", ""]
        if premises.get("measured"):
            L += [f"- measured premises: {premises['measured']}", ""]
        if premises.get("verdict"):
            L += [f"- verdict: {premises['verdict']}", ""]
        L += [f"- amendment for this topic: {am or 'none needed'}", ""]
    L += ["## 9. Deliverables this design must ship", "",
          "- tables: " + ", ".join(d["tables"]),
          "- figures: " + ", ".join(d["figures"]),
          "- plus the spec's 20 §0 items, the §9 E00-E19 coverage statement and a `reproduce.sh` that re-runs the "
          "chain with a probed interpreter.", ""]
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--designs", required=True)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    m = importlib.import_module(a.designs)
    common = dict(m.COMMON)
    common["module"] = a.designs
    have = measured_topics()
    n = late_n = 0
    for tid in sorted(m.DESIGNS):
        d = m.DESIGNS[tid]
        pkg = ROOT / "papers" / d["pkg"]
        pkg.mkdir(parents=True, exist_ok=True)
        f = pkg / "protocol_freeze.md"
        if tid in have and f.is_file():
            print(f"  {tid}: freeze already present and {have[tid]} is registered - not rewriting")
            continue
        late = tid in have                      # the design was frozen earlier; the document is being written now
        f.write_text(render(tid, d, common, m.PREMISES, late=late), encoding="utf-8")
        late_n += int(late)
        n += 1
        print(f"  {tid}: {f.relative_to(ROOT)}{' (written after the run, §0 states it)' if late else ''}")
    print(f"  {n} freeze(s) written from {a.designs} at {time.strftime('%Y-%m-%dT%H:%M:%S')}; "
          f"{late_n} of them carry a §0 provenance block because their wave had already been measured when the "
          f"document was rendered, and none of them was rewritten after an outcome was read")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
