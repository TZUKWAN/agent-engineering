"""Scratch diagnosis of the three wave-6 hypotheses that returned `not_testable_no_coefficient_estimated`.

A missing coefficient row has several distinct causes - the term name never reaching the fitted frame, a fit that
returns nothing, an empty cell after the drops - and only the last is a premise fact. The shipped artefacts say the
verdict; this reads the fit itself.
"""
import sys

sys.path.insert(0, "02_shared_code/package_factory")
import pandas as pd                                              # noqa: E402
import wave_lib as W                                             # noqa: E402
import exp_wave6_designs as D6                                   # noqa: E402

F = D6.load()
CLUSTER = D6.CLUSTER


def probe(tag, d, y, xs, family):
    xs2 = [c for c in dict.fromkeys(xs) if c in d.columns and c != y]
    dd = d.dropna(subset=[y] + xs2)
    print(f"\n== {tag}: rows {len(d)} -> {len(dd)} after dropna; y={y} levels={dd[y].nunique()} "
          f"clusters={dd[CLUSTER].nunique()}")
    print("   terms kept:", xs2)
    f = W.glm_term(dd, y, xs2, family, cluster=CLUSTER)
    if f is None:
        print("   glm_term returned None (the fit itself failed)")
        return
    if f.empty:
        print("   glm_term returned an empty frame")
        return
    print(f[["term", "beta", "se", "p", "converged", "n"]].to_string(index=False)[:700])


probe("T155 H1", F, "log_steps", ["need_words_z"] + D6.CTRL, "gaussian")
probe("T158 H1", F[F["step_index"] < F["n_steps"]], "continues", ["prev_new_z"] + D6.CTRL, "binomial")
traj = F.drop_duplicates("traj_key")
probe("T170 H1", traj[traj["single_rollout_instance"] == 0], "family_concentration",
      ["off_modal_first"] + [c for c in D6.CTRL if c != "step_position"], "gaussian")
probe("T168 H1 as control", F[(F["step_index"] > 1) & (F["obs_chars"] > 0)].dropna(subset=["new_information"]),
      "new_z", ["switched"] + D6.CTRL, "gaussian")
