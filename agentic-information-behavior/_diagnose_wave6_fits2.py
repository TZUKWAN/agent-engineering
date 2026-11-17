"""Scratch diagnosis of the two remaining wave-6 fitting failures and of `single_rollout_instance`.

T155's H2 and T170's H1 returned no coefficient at all, and the number of rollouts the frame calls "in an instance
with more than one rollout" disagrees with the number the matrix artefact reported. Each is a code fact, not a
statistical one, so the fits are re-run in the open and the flag is recomputed from the frame itself.
"""
import sys

sys.path.insert(0, "02_shared_code/package_factory")
import numpy as np                                               # noqa: E402
import pandas as pd                                              # noqa: E402
import statsmodels.api as sm                                     # noqa: E402
import exp_wave6_designs as D6                                   # noqa: E402
import wave_lib as W                                             # noqa: E402

F = D6.load()
traj = F.drop_duplicates("traj_key")
rolls = traj.groupby("instance_id")["traj_key"].nunique()
print("rollouts in multi-rollout instances (recomputed):", int(rolls[rolls >= 2].sum()))
print("flag says single_rollout==0:", int((traj["single_rollout_instance"] == 0).sum()))
print("instances with 1 rollout (recomputed):", int((rolls == 1).sum()), "of", len(rolls))
bad = traj.groupby("traj_key")["single_rollout_instance"].first()
mism = [(i, rolls.get(i)) for i, v in bad.items() if (v == 1) != (rolls.get(i) == 1)]
print("trajectories whose flag disagrees with the recomputed count:", len(mism), mism[:3])


def raw_fit(tag, d, y, xs, fam):
    d = d.dropna(subset=[y] + xs)
    X = sm.add_constant(d[xs].astype(float))
    try:
        r = sm.GLM(d[y].astype(float), X, family=fam).fit(cov_type="cluster",
                                                          cov_kwds={"groups": d[D6.CLUSTER]})
        print(f"\n{tag}: fitted ok on {len(d)} rows; params {len(r.params)}; converged={r.converged}")
        print(r.summary2().tables[1].to_string()[:420])
    except Exception as e:                                        # noqa: BLE001 - the point is to see the error
        print(f"\n{tag}: RAISED {type(e).__name__}: {e}")


raw_fit("T155 H2 (submitted ~ depth at trajectory level)", traj, "submitted",
        ["log_steps", "need_words_z", "step_budget_log", "prev_failed"], sm.families.Binomial())
usable = traj[traj["single_rollout_instance"] == 0]
raw_fit("T170 H1 (concentration ~ off-modal first)", usable, "family_concentration",
        ["off_modal_first", "log_steps", "need_words_z", "obs_chars_log", "prev_failed"], sm.families.Gaussian())
raw_fit("T170 H1 on the recomputed usable set", traj[traj["instance_id"].map(rolls) >= 2], "family_concentration",
        ["off_modal_first", "log_steps", "need_words_z", "obs_chars_log", "prev_failed"], sm.families.Gaussian())
print("\nlevels of submitted among usable rollouts:",
      traj[traj["instance_id"].map(rolls) >= 2]["submitted"].value_counts().to_dict())
