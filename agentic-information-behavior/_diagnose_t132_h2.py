"""Scratch diagnosis of EXP-0166 (T132) H2, whose coefficient came out at -3e15 with a NaN interval.

The design must not call an exploded fit a null result, so the question is what the fit actually reported:
convergence, the standard error, and how the tested term relates to the controls it is estimated beside.
"""
import sys

sys.path.insert(0, "02_shared_code/package_factory")
import numpy as np                                              # noqa: E402
import pandas as pd                                             # noqa: E402
import wave_lib as W                                            # noqa: E402
import exp_wave5_designs as D5                                  # noqa: E402

F = D5.load()
t = F[F["body_len"] >= 20]
d = t[(t["act_conclusion"] == 1) & (t["has_prior_evidence"] == 1)].dropna(subset=["ov_z"])
xs = ["concl_after_inspect"] + D5.CTRL
print("rows", len(d), "trajectories", d["traj_id"].nunique())
print("term shares:", {c: (round(float(d[c].mean()), 4), int(d[c].nunique())) for c in xs})
print("ov_z:", round(float(d["ov_z"].mean()), 4), round(float(d["ov_z"].std(ddof=0)), 4))
print("corr with concl_after_inspect:",
      {c: round(float(d[c].astype(float).corr(d["concl_after_inspect"].astype(float))), 4) for c in xs})
X = d[xs].astype(float)
print("condition number of the design matrix (with intercept):",
      round(float(np.linalg.cond(np.column_stack([np.ones(len(X)), X.to_numpy()]))), 1))
fit = W.glm_term(d, "ov_z", xs, "gaussian", cluster="traj_id")
print(fit[["term", "beta", "se", "ci_lo", "ci_hi", "converged", "n"]].to_string(index=False))
same = d[d["concl_after_inspect"] == 1]
print("rows with an inspection already made:", len(same), " rows without:", len(d) - len(same))
print("trajectories without:", int((d.groupby("traj_id")["concl_after_inspect"].max() == 0).sum()))
