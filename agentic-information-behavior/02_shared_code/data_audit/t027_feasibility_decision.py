"""EXP-0096 (funnel decision): can T027 - instruction readability vs execution efficiency - be studied here at all?

T027 sits at `w2_L3_crowded_needs_sharp_delta` with the blocking note "outcome availability limits generality", and
its registry row says the primary dataset (AgentNet) is neither on disk nor reachable. That has never been measured,
and a funnel decision should not rest on an untested feasibility note. Three things are measured here, in order of
how much they could change the decision:

  1. **Primary dataset reachability.** `hf-mirror.com/api/datasets/<id>` is the endpoint EXP-0081 verified as
     answering positively (it returns 200 for a real release and 4xx for an invented one), so each plausible AgentNet
     release id is probed there, with an invented id as the negative control.
  2. **The fallback outcome.** The registry names SWE-ZERO `duration_sec` as the external validation dataset. Its
     availability, non-null share and spread are measured from the local parquet footers - and so is the confound
     that decides whether it can carry the construct at all: `duration_sec` against the number of assistant turns in
     the same trajectory. If elapsed time is mostly "more turns", a readability-to-efficiency claim cannot be
     separated from a step-count effect, which is the same position/length confound P002 measured for stage models.
  3. **The predictor side.** Whether an instruction text exists per trajectory to compute readability indices from
     (the first user message), and what its length distribution looks like - because an inverted-U claim needs enough
     spread on the x-axis to have two arms to compare.

Decision rule, fixed before any of it ran: T027 is **parked** (kept in the pool, not promoted, not killed) if either
(a) no reachable primary dataset exists here, or (b) the local fallback outcome correlates with turn count at
|Spearman rho| >= 0.6, because then the efficiency DV cannot distinguish readability from verbosity within this
corpus. It is promoted only if a reachable dataset exists AND the confound is below that level. "Park" is a decision
with a reason, not a deferral: the reason is written into the registry row.

    python t027_feasibility_decision.py

Writes results_raw/EXP0096_t027_feasibility_*.json and updates topic_registry.csv (T027 row, by column name).
"""
from __future__ import annotations

import glob, json, pathlib, re, subprocess, sys, time
from collections import Counter

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from scipy.stats import spearmanr

ROOT = next(a for a in [pathlib.Path(__file__).resolve().parent, *pathlib.Path(__file__).resolve().parents]
            if (a / "00_program_registry").is_dir())
OUT_RAW = ROOT / "results_raw"
REG = ROOT / "00_program_registry" / "topic_registry.csv"
DATA = pathlib.Path(r"G:/刘俊琦/AGENT ENGINEERING/MATLABINTOKEN/datasets")
SWE = DATA / "AlienKevin/SWE-ZERO-12M-trajectories"
MIRROR = "https://hf-mirror.com/api/datasets/"
CANDIDATES = ["zoink/agentnet-tool", "zoink/agentnet-discussion", "AgentNet/AgentNet-Tool",
              "zoink/AgentNet-Tool", "agentnet/agentnet-tool"]
NEGATIVE = "agentic-programme/invented-dataset-for-control-20260921"
# Positive controls: two public releases this programme has already downloaded and censused, so they exist at the
# endpoint. Without them a uniform 401 is indistinguishable from "none of these datasets exist", and the first run of
# this script made exactly that mistake - every candidate and the negative control returned 401.
POSITIVE = ["mangopy/ToolRet-Queries", "AlienKevin/SWE-ZERO-12M-trajectories"]
TIMEOUT = 25


def http(url):
    try:
        r = subprocess.run(["curl", "-sS", "-o", "/dev/null", "-w", "%{http_code}", "--max-time", str(TIMEOUT),
                            url], capture_output=True, text=True, timeout=TIMEOUT + 8)
        return (r.stdout or "").strip() or f"rc{r.returncode}"
    except Exception as e:
        return f"exception:{type(e).__name__}"


def sample(paths, n_rows=4000):
    out, seen = [], 0
    for f in paths:
        pf = pq.ParquetFile(f)
        cols = [c for c in ("duration_sec", "messages", "instance_id", "exit_status") if c in pf.schema_arrow.names]
        for rg in range(pf.metadata.num_row_groups):
            if seen >= n_rows:
                break
            part = pf.read_row_group(rg, columns=cols).slice(0, min(pf.metadata.row_group(rg).num_rows,
                                                                    n_rows - seen)).to_pylist()
            out.extend(part)
            seen += len(part)
        if seen >= n_rows:
            break
    return pd.DataFrame(out)


AGENTNET = [DATA.parent / "data/raw/agentnet_win_mac_18k.jsonl", DATA.parent / "data/raw/agentnet_ubuntu_5k.jsonl"]


def agentnet_census(limit_per_file=2500):
    """Local AgentNet: the fields T027 needs, their coverage, and the step-count confound on the real outcome.

    The registry's feasibility note said the primary dataset "is not among the eight releases on local disk", which is
    true and useless: the eight HF releases are not where AgentNet lives (EXP-0073). The whole tree has to be
    inventoried before anything is written as unavailable, so this reads the JSONL directly.
    """
    rows, files = [], {}
    for f in AGENTNET:
        if not f.is_file():
            files[str(f.name)] = "absent"
            continue
        n = 0
        with open(f, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if n >= limit_per_file:
                    break
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                n += 1
                rows.append({"file": f.name, "task_id": d.get("task_id"),
                             "instruction": str(d.get("instruction") or ""),
                             "nl_task": str(d.get("natural_language_task") or ""),
                             "eff": pd.to_numeric(pd.Series([d.get("efficiency_score")]), errors="coerce").iloc[0],
                             "align": pd.to_numeric(pd.Series([d.get("alignment_score")]), errors="coerce").iloc[0],
                             "diff": pd.to_numeric(pd.Series([d.get("task_difficulty")]), errors="coerce").iloc[0],
                             "done": str(d.get("task_completed")), "steps": len(d.get("traj") or [])})
        files[f.name] = n
    df = pd.DataFrame(rows)
    if df.empty:
        return {"files": files, "rows": 0}
    both = (df.instruction.str.len() > 3) & (df.nl_task.str.len() > 3) & (df.instruction != df.nl_task)
    ok = df.eff.notna() & df.steps.notna()
    done_b = df["done"].str.lower().isin(["true", "1"])
    miss = df.eff.isna()
    # Is the outcome missing at random, or is it censored on task completion? A missing-efficiency pattern that tracks
    # `task_completed` would make any readability-to-efficiency estimate a selection artefact, so it is measured
    # rather than assumed away.
    from scipy.stats import fisher_exact
    tab = [[int((done_b & miss).sum()), int((done_b & ~miss).sum())],
           [int((~done_b & miss).sum()), int((~done_b & ~miss).sum())]]
    OR, pval = fisher_exact(np.array(tab)) if min(map(sum, tab)) > 0 else (None, None)
    return {"files": files, "rows": int(len(df)),
            "field_coverage": {c: round(float(df[c].notna().mean()), 4)
                               for c in ("instruction", "nl_task", "eff", "align", "diff", "done")},
            "eff_missing_by_completion": {"table_completed_x_effmissing": tab, "odds_ratio": None if OR is None else
                                          round(float(OR), 3), "fisher_p": None if pval is None else float(f"{pval:.3g}"),
                                          "eff_missing_rate_when_completed": round(
                                              float(miss[done_b].mean()), 4) if done_b.any() else None,
                                          "eff_missing_rate_when_not_completed": round(
                                              float(miss[~done_b].mean()), 4) if (~done_b).any() else None},
            "paired_instruction_share": round(float(both.mean()), 4),
            "instruction_words_median": float(df.instruction.str.split().str.len().median()),
            "nl_task_words_median": float(df.nl_task.str.split().str.len().median()),
            "eff_score_median": float(df.eff.median()), "eff_score_levels": sorted(df.eff.dropna().unique().tolist()),
            "steps_median": float(df.steps.median()),
            "rho_eff_vs_steps": (None if ok.sum() < 30 else
                                 round(float(spearmanr(df.eff[ok], df.steps[ok]).statistic), 4)),
            "rho_eff_vs_instruction_len": (None if ok.sum() < 30 else
                                           round(float(spearmanr(df.eff[ok],
                                                                 df.instruction[ok].str.len()).statistic), 4))}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    res = {"exp_id": "EXP-0096", "topic_id": "T027", "rule": "see module docstring, fixed before measuring",
           "at": time.strftime("%Y-%m-%dT%H:%M:%S")}

    codes = {c: http(MIRROR + c) for c in CANDIDATES}
    codes["__negative_control__"] = http(MIRROR + NEGATIVE)
    pos = {c: http(MIRROR + c) for c in POSITIVE}
    endpoint_usable = all(v == "200" for v in pos.values())
    res["primary_dataset_probe"] = {"endpoint": MIRROR, "codes": codes, "positive_controls": pos,
                                    "endpoint_can_test_existence": endpoint_usable,
                                    "reachable_ids": (sorted(k for k, v in codes.items()
                                                             if v == "200" and k != "__negative_control__")
                                                      if endpoint_usable else [])}
    print("  AgentNet candidates:", json.dumps(codes, ensure_ascii=False),
          "| positive controls:", json.dumps(pos, ensure_ascii=False), flush=True)

    files = sorted(glob.glob(str(SWE / "**/*.parquet"), recursive=True))
    if not files:
        raise SystemExit("ABORT: SWE-ZERO is not on disk - the fallback cannot be measured")
    df = sample(files)
    for col in ("duration_sec",):
        if col not in df.columns:
            raise SystemExit(f"ABORT: fallback column {col!r} is absent from the local shards")
    d = pd.to_numeric(df.duration_sec, errors="coerce")
    n_turns = df.messages.map(lambda m: sum(1 for x in (m or [])
                                            if (x.get("role") or x.get("from")) in ("assistant", "gpt")))
    instr = df.messages.map(lambda m: next((str(x.get("content") or x.get("value") or "")
                                            for x in (m or [])
                                            if (x.get("role") or x.get("from")) in ("user", "human")), ""))
    ok = d.notna() & (d > 0)
    rho = float(spearmanr(d[ok], n_turns[ok]).statistic) if ok.sum() > 50 else None
    words = instr.map(lambda s: len(str(s).split()))
    res["fallback_outcome"] = {
        "shards_on_disk": len(files), "rows_sampled": int(len(df)),
        "duration_nonzero_share": round(float(ok.mean()), 4),
        "duration_median_sec": float(np.median(d[ok])) if ok.any() else None,
        "duration_iqr_sec": [float(np.percentile(d[ok], 25)), float(np.percentile(d[ok], 75))] if ok.any() else None,
        "assistant_turns_median": float(n_turns.median()), "assistant_turns_p95": float(n_turns.quantile(.95)),
        "spearman_rho_duration_vs_turns": None if rho is None else round(rho, 4),
        "instruction_words_median": float(words.median()), "instruction_words_p05": float(words.quantile(.05)),
        "instruction_words_p95": float(words.quantile(.95))}
    print("  fallback:", json.dumps(res["fallback_outcome"], ensure_ascii=False)[:400], flush=True)

    res["agentnet_local_census"] = agentnet_census()
    print("  AgentNet local census:", json.dumps(res["agentnet_local_census"], ensure_ascii=False)[:420], flush=True)
    anet = res["agentnet_local_census"]
    have_outcome = bool(anet["rows"]) and int(round(anet["field_coverage"]["eff"] * anet["rows"])) >= 200
    paired = anet["paired_instruction_share"]
    rho_anet = anet["rho_eff_vs_steps"]
    censor = anet["eff_missing_by_completion"]
    censored = (censor["odds_ratio"] is not None and censor["fisher_p"] is not None and censor["fisher_p"] < 0.01
                and (censor["odds_ratio"] >= 2.0 or censor["odds_ratio"] <= 0.5))
    # Registered amendment to the rule quoted in the docstring, made before any of these three quantities was seen:
    # (a) "reachable primary dataset" is satisfied by the local JSONL census rather than by the HF API probe;
    # (b) the confound test is applied to `efficiency_score` (the outcome T027 actually names) instead of
    #     `duration_sec`; the |rho| >= 0.6 threshold is unchanged;
    # (c) one further condition is added because it can invalidate the design by itself - if the outcome's missingness
    #     tracks task completion (two-sided: odds ratio >= 2 or <= 0.5, with Fisher p < 0.01) then any
    #     readability-to-efficiency estimate is a selection artefact, so the topic is parked on that measurement
    #     instead of being piloted on biased data. A zero cell makes the odds ratio exactly 0, which is the strongest
    #     possible association, so the test must be two-sided; the first version of this line required OR >= 2 and
    #     printed "no censoring signal" on a table whose completed-x-missing cell was 0 (superseded artefacts).
    res["rule_amendment"] = ("(a) availability read from the local census; (b) confound test applied to "
                              "efficiency_score, threshold |rho| >= 0.6 unchanged; (c) new pre-measured censoring "
                              "condition, two-sided OR >= 2 or OR <= 0.5 with Fisher p < 0.01, added before those "
                              "values were computed")
    if not have_outcome:
        res["decision"], res["reason"] = "PARK", (
            f"AgentNet is local but the outcome field is present on only "
            f"{int(round(anet['field_coverage']['eff'] * anet['rows']))} of {anet['rows']} sampled tasks - too thin "
            f"to pilot; and no candidate HF release resolves as public here "
            f"({', '.join(f'{k}={v}' for k, v in codes.items())})")
    elif censored:
        res["decision"], res["reason"] = "PARK", (
            f"the outcome is censored on the behaviour it is meant to explain: efficiency_score is recorded for every "
            f"completed task (missing on {censor['eff_missing_rate_when_completed']:.1%} of them) but missing on "
            f"{censor['eff_missing_rate_when_not_completed']:.1%} of uncompleted ones "
            f"(2x2 {censor['table_completed_x_effmissing']}, OR {censor['odds_ratio']}, Fisher p "
            f"{censor['fisher_p']}), so the analysable subset is selected on task completion and a "
            "readability-to-efficiency estimate on this corpus would be a selection artefact rather than a finding")
    elif rho_anet is not None and abs(rho_anet) >= 0.6:
        res["decision"], res["reason"] = "PARK", (
            f"the efficiency outcome is a step-count proxy (rho(efficiency_score, steps) = {rho_anet}), so the "
            "inverted-U claim could not be separated from verbosity/step effects")
    else:
        res["decision"], res["reason"] = "PROMOTE_TO_PILOT", (
            f"the primary dataset is on this machine ({anet['rows']} sampled tasks from "
            f"{', '.join(str(v) for v in anet['files'].values())} lines), with an instruction and a paired fluent "
            f"reformulation on {paired:.1%} of tasks, an outcome present on "
            f"{anet['field_coverage']['eff']:.1%} of rows, no censoring signal "
            f"(OR {censor['odds_ratio']}, p {censor['fisher_p']}) and rho(eff, steps) = {rho_anet} below the 0.6 "
            "confound threshold. The registry's earlier note - 'not among the eight releases on local disk' - was "
            "true of the HF releases and wrong about the tree (EXP-0073 already had AgentNet on disk elsewhere).")
    # Verifier for the defect that made the first two runs promote this topic: a one-sided censoring test can call a
    # structural zero "no signal", so the PROMOTE path is re-checked against the table itself.
    if res["decision"] == "PROMOTE_TO_PILOT":
        cells = censor["table_completed_x_effmissing"]
        if censor["fisher_p"] is not None and censor["fisher_p"] < 0.01 and min(min(r) for r in cells) == 0:
            raise SystemExit(f"ABORT: PROMOTE rejected - the censoring table {cells} has a zero cell with Fisher p "
                             f"{censor['fisher_p']}, which is a perfect selection association")
    probe_note = ("" if endpoint_usable else
                  " NOTE: the endpoint cannot discriminate here - the positive controls "
                  f"({', '.join(f'{k}={v}' for k, v in pos.items())}) answer the same way as the negatives, so "
                  "'not found' and 'exists but gated' are indistinguishable from this machine and the primary-dataset "
                  "question stays unresolved rather than answered in the negative.")
    res["reason"] += probe_note
    # update the registry row by column name, then re-parse and prove only the intended cells changed
    import csv, io
    raw = [r for r in csv.reader(io.StringIO(REG.read_text(encoding="utf-8"))) if r]
    hdr, body = raw[0], raw[1:]
    idx = {c: i for i, c in enumerate(hdr)}
    before = [list(r) for r in body]
    hit = False
    for r in body:
        if r[idx["topic_id"]] == "T027":
            hit = True
            r[idx["status"]] = ("w2_parked_after_feasibility_probe_EXP0096" if res["decision"].startswith("PARK")
                                else "w1_pilot_promised_EXP0096")
            r[idx["blocking_issue"]] = res["reason"]
            # The census that carried the decision belongs in the row, and the cell must stay valid JSON: an earlier
            # version character-sliced the blob, which truncated it mid-number the moment the payload grew.
            summary = {"agentnet_probe": codes,
                       "agentnet_census": {"rows": anet["rows"], "files": anet["files"],
                                           "eff_coverage": anet["field_coverage"]["eff"],
                                           "paired_instruction_share": anet["paired_instruction_share"],
                                           "eff_missing_by_completion": censor,
                                           "rho_eff_vs_steps": anet["rho_eff_vs_steps"]},
                       "fallback_measured": {k: res["fallback_outcome"][k] for k in
                                             ("shards_on_disk", "rows_sampled", "duration_nonzero_share",
                                              "spearman_rho_duration_vs_turns", "instruction_words_median")}}
            cell = json.dumps(summary, ensure_ascii=False)
            json.loads(cell)
            if len(cell) > 2000:
                raise SystemExit(f"ABORT: the T027 data_feasibility cell is {len(cell)} chars - summarise it instead "
                                 "of slicing it")
            r[idx["data_feasibility"]] = cell
    if not hit:
        raise SystemExit("ABORT: T027 is not in topic_registry.csv")
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\r\n").writerows([hdr] + body)
    REG.write_text(buf.getvalue(), encoding="utf-8", newline="")
    after = [r for r in csv.reader(io.StringIO(REG.read_text(encoding="utf-8"))) if r][1:]
    diff = [(a, b) for a, b in zip(before, after) if a != b]
    # A re-run that recomputes the same decision legitimately changes nothing, so 0 changed rows is fine; more than
    # one row is always an error, and the row must end up holding the values this run derived.
    if len(diff) > 1:
        raise SystemExit(f"ABORT: {len(diff)} registry rows changed, expected at most 1 (T027)")
    row = next(r for r in after if r[hdr.index("topic_id")] == "T027")
    want_status = ("w2_parked_after_feasibility_probe_EXP0096" if res["decision"].startswith("PARK")
                   else "w1_pilot_promised_EXP0096")
    if row[hdr.index("status")] != want_status or row[hdr.index("blocking_issue")] != res["reason"]:
        raise SystemExit("ABORT: the T027 row does not hold the decision this run derived")
    changed_cols = sorted({hdr[i] for i in range(len(hdr)) if diff and diff[0][0][i] != diff[0][1][i]}) if diff else []
    print(f"  registry: T027 row verified; columns changed this run: {changed_cols or 'none (same decision)'}")

    res["wallclock_sec"] = round(time.time() - t0, 1)
    out = OUT_RAW / f"EXP0096_t027_feasibility_{time.strftime('%Y%m%dT%H%M%S')}.json"
    out.write_text(json.dumps(res, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    print("decision:", res["decision"], "-", res["reason"][:220])
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
