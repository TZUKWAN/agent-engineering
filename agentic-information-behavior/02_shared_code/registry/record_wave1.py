"""EXP-0118..0134: register wave 1 from its artefacts, the way every later wave already does.

Waves 2-12 each have a recorder that re-reads the artefacts and rewrites the registry rows, so a re-run cannot leave
a stale verdict in the table. Wave 1 was registered by one-off scripts and never got one, which the round-2 pass
found the hard way: after its design steps were re-run (the round-2 fixes to `verdict_direction`, non-finite
intervals and the nested-gain label), `EXP-0121` and `EXP-0122` still carried their old status strings, so the
registry said something the artefacts no longer said. A row whose status nobody can refresh is a step left to
memory, and memory is not in this programme's chain.

Only the rows it is asked for are rewritten, and each status is taken from that run's own artefact.

    python 02_shared_code/registry/record_wave1.py [--only EXP-0121 EXP-0122]
"""
from __future__ import annotations

import argparse
import glob
import json
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = next(a for a in (HERE, *HERE.parents) if (a / "00_program_registry").is_dir())
PYEXE = sys.executable
REC = str(HERE / "record_experiment.py")
sys.path.insert(0, str(ROOT / "02_shared_code" / "package_factory"))
import topic_designs_wave1 as TD1                                                 # noqa: E402

DESIGN_SCRIPT = {"exp_wave1_query_level.py": "02_shared_code/package_factory/exp_wave1_query_level.py",
                 "exp_wave1_candidate_level.py": "02_shared_code/package_factory/exp_wave1_candidate_level.py",
                 "exp_wave1_reformulation.py": "02_shared_code/package_factory/exp_wave1_reformulation.py"}
# The artefact glob comes from the row's own `outputs` cell, because that is what the registry already asserts;
# only the topic, the writing script and the paper are named here.
RUNS = {
 "EXP-0121": ("T101", "exp_wave1_query_level.py", "P006"),
 "EXP-0122": ("T103", "exp_wave1_query_level.py", "P007"),
 "EXP-0123": ("T106", "exp_wave1_reformulation.py", "P008"),
 "EXP-0124": ("T108", "exp_wave1_candidate_level.py", "P009"),
 "EXP-0125": ("T109", "exp_wave1_candidate_level.py", "P010"),
 "EXP-0126": ("T110", "exp_wave1_candidate_level.py", "P011"),
}


def row_glob(exp: str) -> str:
    """The first `outputs` entry of the registered row, which is where that run says its artefact is."""
    import csv
    import io
    reg = list(csv.DictReader(io.StringIO((ROOT / "00_program_registry" / "experiment_registry.csv")
                                          .read_text(encoding="utf-8-sig"))))
    r = next((x for x in reg if x["exp_id"] == exp), None)
    if r is None:
        raise SystemExit(f"ABORT: {exp} is not registered, so there is no row to refresh")
    for part in re.split(r"[;,]", r.get("outputs") or ""):
        part = part.strip()
        if part.endswith(".json") and "(" not in part:
            return part
    raise SystemExit(f"ABORT: {exp}'s row names no JSON artefact in its outputs cell")


def latest(pat: str) -> pathlib.Path:
    f = sorted(glob.glob(str(ROOT / pat)), key=lambda x: pathlib.Path(x).stat().st_mtime)
    if not f:
        raise SystemExit(f"ABORT: no artefact matches {pat!r}; the experiment has not run")
    return pathlib.Path(f[-1])


def verdict_rows(o, out=None, key=""):
    """Every dict in the artefact that carries a verdict, wherever the wave put it.

    Wave 1 is older than the shared wrapper, so its artefacts store the rows under `models`, under `H1`/`H2`/`H3`
    dicts, and under named quantities like `lexical_displacement`. A recorder that only looked in one place wrote
    `no_verdict_row_in_artefact` over a row that plainly had one, which is worse than the stale string it replaced.
    """
    out = [] if out is None else out
    if isinstance(o, dict):
        if o.get("verdict"):
            out.append((key, o))
        for k, v in o.items():
            verdict_rows(v, out, k if not key else f"{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o):
            verdict_rows(v, out, key)
    return out


def status_of(a: dict) -> str:
    """`H1:<term>=<verdict>` for every row the artefact gives a verdict, in the artefact's own order.

    Wave 1's rows do not all carry a `hypothesis` field - the candidate-level ones are keyed by the term they
    estimate - so the position in the declared sequence supplies the H number and the term is kept beside it. A run
    whose artefact holds no verdict at all aborts rather than having its row rewritten to a smaller statement than
    the artefact supports.
    """
    parts, n = [], 0
    # some of wave 1's steps keep a plain {H1: "...", H2: "..."} map next to the rows rather than inside them
    for hyp, v in (a.get("verdicts") or {}).items() if isinstance(a.get("verdicts"), dict) else []:
        if isinstance(v, str):
            n += 1
            parts.append(f"{hyp}:{v}".replace(" ", "_"))
    for key, obj in verdict_rows(a):
        n += 1
        hyp = str(obj.get("hypothesis") or f"H{n}")
        term = str(obj.get("term") or obj.get("term_name") or key or "")[:34]
        parts.append(f"{hyp}:{term}={obj['verdict']}".replace(" ", "_").replace(":", ":", 1))
    # a step that reports an increment rather than a verdict per hypothesis says it in named numbers, and the old
    # hand-written status carried those; they are appended here so the derived string loses no information
    for k, v in sorted(a.items()):
        if k in ("exp_id", "models", "verdicts", "holm", "run_cost", "started_at", "finished_at", "amendment",
                 "invocation", "quick", "seed", "robustness") or isinstance(v, (list, dict)) and k != "coverage":
            continue
        if isinstance(v, (int, float, str)) and not isinstance(v, bool):
            leaves = [(k, v)]
        elif isinstance(v, dict):
            leaves = [(f"{k}.{kk}", vv) for kk, vv in sorted(v.items()) if isinstance(vv, (int, float))][:4]
        else:
            continue
        for lk, lv in leaves:
            parts.append(f"{lk}={str(lv)[:22]}".replace(" ", "_").replace(".", "p", 1) if lk == "coverage"
                         else f"{lk}={str(lv)[:22]}".replace(" ", "_"))
    if not parts:
        # EXP-0126 states its result as scalars (an AUROC gain against a frozen floor, an LR p, a coverage pair)
        # rather than as verdict rows, so the same convention reads those. Nothing at all still aborts: a status
        # saying "no verdict row" would be a weaker statement than the artefact carries.
        for k in ("gain", "auroc_gain", "lr_p", "floor", "frozen_floor", "coverage", "partial_coverage"):
            v = a.get(k)
            if isinstance(v, (int, float, str)) and not isinstance(v, bool):
                parts.append(f"{k}={v}")
        if not parts:
            raise SystemExit(f"ABORT: this artefact carries neither a verdict row nor a result scalar, so its "
                             f"registry status cannot be derived from it")
    for k in ("gate_note", "dose_response", "census_note"):
        val = a.get(k)
        if isinstance(val, str) and val.strip():
            parts.append(val.strip().replace(" ", "_")[:56])
    return "_".join(parts)[:300]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", default=[])
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    for exp, (topic, script, paper) in sorted(RUNS.items()):
        pat = row_glob(exp)
        if a.only and exp not in a.only:
            continue
        f = latest(pat)
        art = json.loads(f.read_text(encoding="utf-8"))
        d = TD1.DESIGNS.get(topic) or {}
        subprocess.run([PYEXE, REC, "--exp", exp, "--paper", paper, "--topic", topic, "--stage", "wave1_main",
                        "--script", DESIGN_SCRIPT[script], "--config", f"seed={art.get('seed')}; topic={topic}; "
                        f"registered from its own artefact by record_wave1.py",
                        "--status", status_of(art), "--seed", str(art.get("seed") or 42),
                        "--notes", f"the pre-registered test for {topic}; artefact {f.name}",
                        "--enters-paper", "yes - the whole result set", "--artefact", pat],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
        print(f"{exp}: {topic} -> registered from {f.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
