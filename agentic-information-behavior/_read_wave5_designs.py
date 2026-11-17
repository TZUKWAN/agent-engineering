"""Scratch read-back of wave 5's six design artefacts: every hypothesis, its estimate and why a cell is not testable.

Written because `not_testable_*` has two very different causes - a population the premise census measured as too thin,
and a fit that produced no coefficient - and only the first is what the frozen rule promises. Reading the shipped
numbers rather than the console line is also the check that no verdict rests on a NaN.
"""
import glob
import json
import pathlib

for f in sorted(glob.glob("results_raw/EXP016*_wave5_design_*.json") + glob.glob("results_raw/EXP0170_wave5*.json")):
    a = json.loads(pathlib.Path(f).read_text(encoding="utf-8"))
    print("=" * 100)
    print(f"{a.get('exp_id')} {a.get('topic')} turns={a.get('n_turns')} traj={a.get('n_trajectories')} "
          f"gate_scope={str(a.get('gate_scope'))[:70]}")
    for m in a.get("models") or []:
        if not isinstance(m, dict) or not m.get("hypothesis"):
            continue
        print(f"  {m.get('hypothesis'):4s} {str(m.get('term'))[:46]:46s} beta={m.get('beta')} "
              f"ci={m.get('ci_lo')},{m.get('ci_hi')} p={m.get('p')} p_holm={m.get('p_holm')} n={m.get('n')} "
              f"-> {m.get('verdict')}")
        for k in ("note", "boot_note", "reason", "verdict_rule", "direction", "predicted_direction",
                  "clusters", "is_bootstrap_mean", "why"):
            if m.get(k) is not None:
                print(f"       {k}: {str(m.get(k))[:170]}")
    for k in ("premise_gate", "gate_note", "not_measured", "h1_gate", "collinearity", "excluded"):
        if a.get(k):
            print(f"  artefact[{k}] = {str(a.get(k))[:260]}")
