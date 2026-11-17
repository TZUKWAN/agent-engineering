"""Scratch diagnosis 2: why EXP-0166 H2 is not identified on its frozen population.

H2's frozen population is every turn carrying a conclusion marker whose overlap is defined (1,078 rows), not the
subset with prior evidence. The fit on that population returned a coefficient of -3e15 with a NaN cluster-robust
interval, so the question is what makes the design matrix singular there and not on the smaller frame: the order
indicator against the frozen controls, measured rather than argued.
"""
import sys

sys.path.insert(0, "02_shared_code/package_factory")
import numpy as np                                              # noqa: E402
import pandas as pd                                             # noqa: E402
import wave_lib as W                                            # noqa: E402
import exp_wave5_designs as D5                                  # noqa: E402

F = D5.load()
t = F[F["body_len"] >= 20]
d = t[t["act_conclusion"] == 1].dropna(subset=["ov_z"])
xs = ["concl_after_inspect"] + D5.CTRL
print("frozen H2 population:", len(d), "rows,", d["traj_id"].nunique(), "trajectories")
print("per-term (mean, distinct values):", {c: (round(float(d[c].mean()), 4), int(d[c].nunique())) for c in xs})
ind = (d["prior_inspections"] > 0).astype(int)
print("agree(concl_after_inspect, 1[prior_inspections>0]):", round(float((ind == d["concl_after_inspect"]).mean()), 4),
      " kappa:", round(float(D5.EF.kappa(ind, d["concl_after_inspect"].astype(int))), 4))
print("corr:", {c: round(float(d[c].astype(float).corr(d["concl_after_inspect"].astype(float))), 4) for c in xs})
X = np.column_stack([np.ones(len(d))] + [d[c].astype(float).to_numpy() for c in xs])
print("rank:", int(np.linalg.matrix_rank(X)), "of", X.shape[1], "columns; cond:",
      round(float(np.linalg.cond(X)), 1))
fit = W.glm_term(d, "ov_z", xs, "gaussian", cluster="traj_id")
print(fit[["term", "beta", "se", "ci_lo", "ci_hi", "converged"]].to_string(index=False))
noev = d[d["has_prior_evidence"] == 0]
print("rows with no prior evidence:", len(noev), " of them with concl_after_inspect=1:",
      int(noev["concl_after_inspect"].sum()))
print("ov_z mean by prior evidence:", {int(k): (round(float(g["ov_z"].mean()), 4), len(g))
                                       for k, g in d.groupby("has_prior_evidence", observed=True)})
