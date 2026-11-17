"""Write wave 1's protocol freezes from the frozen designs, before any outcome is computed (spec §7).

One `protocol_freeze.md` per topic package, generated from `topic_designs_wave1.py` so the document and the code that
runs the study cannot drift. The freeze carries the hypotheses, the operationalisation of every feature, the sample
rule, the seed, the effect-size bands, the decision rule for support/partial/null, the Holm family, the kill gate and -
where EXP-0118's structure census forced a change - the amendment, dated and attributed. The census is a schema and
marker measurement; no dependent-variable distribution was read before these files were written, and the thresholds
were not touched by the amendment.

    python 02_shared_code/package_factory/freeze_wave1.py
"""
from __future__ import annotations

import datetime, pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
ROOT = next(a for a in (HERE, *HERE.parents) if (a / "00_program_registry").is_dir())
from topic_designs_wave1 import COMMON, DESIGNS, PREMISES  # noqa: E402

FROZEN_ON = "2026-09-23"


def one(tid: str) -> tuple[str, str]:
    d = DESIGNS[tid]
    pkg = ROOT / "papers" / d["pkg"]
    am = PREMISES["amendments"].get(tid)
    body = f"""# {d['pkg']} protocol freeze - {d['title']}

Frozen {FROZEN_ON}, **before** any dependent variable was computed for this study. Any change after an outcome is
read requires a `deviations.md` entry and the affected hypothesis becomes exploratory.

Topic id `{tid}` (registered 2026-09-23; screened by EXP-0115, re-triaged by EXP-0116, queued by EXP-0117).

## 1 Question and hypotheses

{d['rq']}

""" + "\n".join(f"- {h}" for h in d["hypotheses"]) + f"""

## 2 Operationalisation (fixed)

""" + "\n".join(f"- **{k}**: {v}" for k, v in d["features"].items()) + """

Dependent variables:

""" + "\n".join(f"- **{k}**: {v}" for k, v in d["dvs"].items()) + f"""

## 3 Sample, seed and substrate (fixed)

- Seed: **{COMMON['seed']}**, the single constant used by every sampler, bootstrap and split in this package.
- Sample: {COMMON['sample']['rows_per_config']:,} rows per configuration, configs {COMMON['sample']['configs']},
  bucket `{COMMON['sample']['bucket']}`. {COMMON['sample']['rule']}. P001's test split is never read.
- Retriever: the frozen BM25 P001 ships (same tokeniser, same k1/b, no tuning for this study).
- Where a distributional measure is needed, the encoder is the locally run one from EXP-0061. **No model inference
  API is called**, and no judgement in this study comes from a model (spec §11).
- Clustering: every interval clusters on the unit the feature is computed from ({COMMON['notes'].split('.')[1].strip()}),
  never on rows.

## 4 Decision rule (fixed)

- **supported**: {d['thresholds']['support']}
- **partial**: {d['thresholds']['partial']}
- **null**: {d['thresholds']['null']}
- Effect bands: small {COMMON['bands']['small']}, medium {COMMON['bands']['medium']}, large {COMMON['bands']['large']}
  (the same bands the rest of the series uses).
- Multiplicity: Holm across the declared family of **{d['family']} tests**; a hypothesis that only survives
  uncorrected is reported as exploratory.
- Models: {"; ".join(d['models'])}.

## 5 Kill gate (fixed)

{d['kill_gate']}

## 6 Deliverables this freeze commits to producing

Tables: {", ".join(f"`tables/{t}`" for t in d["tables"])}

Figures: {", ".join(f"`figures/{f}`" for f in d["figures"])}

"""
    if am:
        body += f"""## 7 Amendment made after the structure census and before any outcome ({PREMISES['census']})

EXP-0118 measured the columns this design depends on: {PREMISES['measured']}.
Verdict on the trajectory dependent variables: {PREMISES['verdict_trajectory_dvs']}.

Amendment: {am}

{PREMISES['deviation_note']}.

"""
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "protocol_freeze.md").write_text(body, encoding="utf-8", newline="")
    return tid, str((pkg / "protocol_freeze.md").relative_to(ROOT))


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    for tid in sorted(DESIGNS):
        t, rel = one(tid)
        print(f"  {t}: {rel}")
    print(f"  {len(DESIGNS)} protocol freezes written for wave 1 "
          f"({', '.join(sorted(DESIGNS))}); no outcome had been read at write time")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
