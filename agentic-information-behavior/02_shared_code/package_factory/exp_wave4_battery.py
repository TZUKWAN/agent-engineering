"""EXP-0158: the E00-E19 battery for wave 4, run by the same step loop as wave 2.

The steps that fit a single frame (ablation, scaling, replication, error taxonomy, contamination-by-row) are
imported from `exp_wave1_battery` and executed by `exp_wave2_battery.run_battery`, so an ablation in wave 4 means
exactly what it means in wave 2 and cannot drift. Wave 4 supplies the frames, the frozen (y, x, covariate) triples
and the steps whose subject is the *turn*: a second instrument for the hedge, a duplication audit over assistant
text, and two steps that are reported as not applicable with the measured reason rather than skipped.

    python 02_shared_code/package_factory/exp_wave3_battery.py-style CLI:
    python 02_shared_code/package_factory/exp_wave4_battery.py [--quick]
"""
from __future__ import annotations

import json
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import numpy as np                                              # noqa: E402
import pandas as pd                                             # noqa: E402
import wave_lib as W                                            # noqa: E402
import exp_wave2_battery as B2                                  # noqa: E402
import exp_wave4_designs as D4                                  # noqa: E402
import topic_designs_wave4 as TD4                               # noqa: E402

EXP = "EXP-0158"
CTRL = D4.CTRL

SPEC = {
    "T123": dict(frame="step", y="next_is_inspect", x="modal_turn", family="binomial", covars=CTRL,
                cluster="traj_id"),
    "T124": dict(frame="step_with_faces", y="next_is_inspect", x="hedge_diff", family="binomial",
                 covars=["hedge_sum", "conc"] + CTRL, cluster="traj_id"),
    "T126": dict(frame="step_after_observation", y="modal_turn", x="st_changed", family="binomial",
                 covars=["st_same", "st_diff_tool"] + CTRL,
                 cluster="traj_id"),
    "T127": dict(frame="step", y="stops_here", x="suffic_turn", family="binomial", covars=CTRL,
                cluster="traj_id"),
}


def frames() -> dict:
    F = D4.load()
    # The battery clusters on the trajectory, like every design in this wave. Each spec also names the *population*
    # its design estimates on: pointing T124 at the unfiltered turn frame would have measured the whole corpus
    # under a hypothesis about turns that have both faces, and the two numbers would disagree by construction.
    return {"step": F,
            "step_with_faces": F[(F["has_think"] == 1) & (F["body_len"] >= 20)],
            "step_after_observation": F[F["prev_state"] != "none"]}


def e06_second_instrument(fr: dict) -> dict:
    """Each construct measured a second way, plus the list of constructs that have only one operationalisation."""
    F = fr["step"].assign(control_rank=(lambda s: (s - float(s.mean())) / float(s.std(ddof=0)))
                          (fr["step"]["topical_count"].astype(float)))
    out = []

    def rho(a, b, label, note=""):
        d = F[[a, b, "traj_id"]].dropna()
        if d[a].nunique() < 3 or d[b].nunique() < 3:
            agree = float((d[a].gt(d[a].median()).astype(int) == d[b].gt(d[b].median()).astype(int)).mean())
            out.append({"construct": label, "status": "one or both instruments are near-degenerate: median-split "
                        "agreement reported, no rank correlation claimed", "agreement_share": round(agree, 4),
                        "n": int(len(d)), "note": note})
            return
        r = dict(W.rho_ci(d, "traj_id", a, b))
        r.update(construct=label, n=int(len(d)), clusters=int(d["traj_id"].nunique()), note=note)
        out.append(r)

    rho("modal_turn", "modal_think", "hedge: whole turn vs reasoning block only",
        "the two faces of one message, so a high agreement is not independence")
    rho("modal_turn", "modal_body", "hedge: whole turn vs user-facing body only")
    rho("suffic_turn", "suffic_think", "sufficiency claim: turn vs reasoning block")
    rho("modal_turn", "control_rank", "hedge indicator vs topical-word count",
        "the pre-registered control's count form; the frozen indicator sits at 0.9998 prevalence and cannot be "
        "correlated")
    return {"pairs": out,
            "single_instrument_constructs": ["verification behaviour (only the called tool's name family)",
                                             "stopping (only the absence of a following call)"],
            "note": "a construct with one operationalisation is listed, not silently dropped"}


def zishu(s: pd.Series) -> pd.Series:
    sd = float(s.std(ddof=0))
    return (s - float(s.mean())) / sd if sd else s * 0.0


def e08_external() -> dict:
    """Transfer to a second corpus, and the measured reason it cannot be done for these constructs."""
    return {"status": "not transferable on the corpora available locally",
            "reason": "wave 4 needs assistant turns with their own reasoning and their own tool calls. The routing "
                      "corpora that served as the external set for waves 1-3 carry a user instruction and a "
                      "released selection, not an agent transcript, so there is no second corpus on this host that "
                      "has both faces of the turn (EXP-0027/29/30 measured message sequence and user instruction as "
                      "the only concepts recoverable in all eight releases)",
            "arms": {}}


def e17_counterfactual(fr: dict) -> dict:
    """The intervention this wave could actually run, and the one its construct forbids."""
    F = fr["step"]
    # rewriting the text cannot rewrite recorded behaviour, so the counterfactual is a *measurement* intervention:
    # re-estimate the primary association with the marker moved to the other face of the same turn
    base = W.glm_term(F, "next_is_inspect", ["modal_turn"] + CTRL, "binomial", cluster="traj_id")
    alt = W.glm_term(F[F["has_think"] == 1], "next_is_inspect", ["modal_think"] + CTRL, "binomial",
                     cluster="traj_id")

    def b(f, name):
        if f is None or f.empty:
            return None
        r = f[f["term"] == name]
        return None if r.empty else [round(float(r.iloc[0]["beta"]), 4), round(float(r.iloc[0]["ci_lo"]), 4),
                                     round(float(r.iloc[0]["ci_hi"]), 4)]
    return {"instrument": "the same frozen model, estimated with the marker taken from each face of the turn",
            "arms": [{"arm": "modal_turn (whole turn)", "beta_ci": b(base, "modal_turn")},
                     {"arm": "modal_think (reasoning block only)", "beta_ci": b(alt, "modal_think")},
                     {"arm": "modal_body (user-facing body only)",
                      "beta_ci": b(W.glm_term(F[F["body_len"] >= 20], "next_is_inspect",
                                              ["modal_body"] + CTRL, "binomial",
                                              cluster="traj_id"), "modal_body")}],
            "note": "recorded behaviour cannot be re-simulated without a model, which the programme forbids here, "
                    "so no rewrite arm is offered; what is offered is the face swap, which is a measurement "
                    "intervention on the same rows",
            "rows": int(len(F))}


def e19_text_duplication(fr: dict) -> dict:
    """How much of the language being tested is the same text repeated across trajectories.

    A marker lexicon counts the same boilerplate sentence many times, so its prevalence is only as honest as the
    number of distinct texts behind it. The frame carries a digest of each turn's reasoning and body, which makes
    that measurable rather than assumed.
    """
    F = fr["step"]
    d = F.dropna(subset=["turn_sha"])
    vc = d["turn_sha"].value_counts()
    return {"rows_scanned": int(len(F)), "rows_with_a_digest": int(len(d)),
            "distinct_turn_texts": int(vc.size),
            "share_of_turns_that_are_a_repeat": round(float(1 - vc.size / max(1, len(d))), 4),
            "most_repeated_turn_text_rows": int(vc.iloc[0]) if len(vc) else 0,
            "modal_turn_share_among_repeats": round(float(d[d["turn_sha"].map(vc) > 1]["modal_turn"].mean()), 4)
            if len(vc) else None,
            "modal_turn_share_among_unique_turns": round(
                float(d[d["turn_sha"].map(vc) == 1]["modal_turn"].mean()), 4) if len(vc) else None,
            "rule": "one digest per (reasoning block, body) pair; a repeat is the same text in another trajectory"}


def shared(fr: dict, quick: bool = False) -> dict:
    return {"e06_second_instrument": e06_second_instrument(fr),
            "e08_external": e08_external(),
            "e17_counterfactual": e17_counterfactual(fr),
            "e19_contamination": e19_text_duplication(fr)}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    B2.run_battery(EXP, "wave4_battery_0158", frames, SPEC, shared, quick="--quick" in sys.argv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
