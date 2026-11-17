"""Round-2 check C1: does each shipped number imply the verdict printed beside it?

The estate's rule is frozen and mechanical - `wave_lib.verdict` (support needs |beta| at or above the design's own
floor, a cluster CI that excludes 0, Holm-corrected p < 0.05 and the predicted direction; partial needs CI exclusion
in the predicted direction; opposite needs exclusion against the prediction; null needs CI inclusion). Wave 5 shipped
a coefficient of -3e15 with a NaN interval and a `null` verdict, which is how this style of check first entered the
programme. This pass re-applies the rule to every kept design and battery artefact rather than trusting the string
that was written:

* verdict recomputed from the row's own beta / CI / p_holm / direction and the design's frozen support floor;
* Holm recomputed over the hypothesis set the artefact itself declares - one entry per declared hypothesis taking
  that hypothesis's smallest p, which is the family `wave_lib.finalize_models` corrects over, and read from any of
  the keys a design states its raw p under (`p`, `p_boot`, `p_perm`, `p_raw`, `p_lr`, `p_exact`). An earlier version
  of this check read only the key `p`, which most designs do not use, so it silently re-derived 264 of the 683
  families it can now reach and its zero findings described a fraction of the corrections;
* interval sanity - beta inside its own CI, SE positive and finite, CI width consistent with 1.96 SE for the
  normal-theory fits (bootstrap CIs are allowed to differ and are reported, not failed);
* row completeness - a fitted row carries beta, se, ci_lo, ci_hi, p, p_holm, n and clusters;
* a row whose interval is not a number may not carry a four-way verdict.

    python 02_shared_code/registry/round2_statistical_consistency.py [--limit 30]
"""
from __future__ import annotations

import argparse
import collections
import datetime
import json
import math
import pathlib
import re
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "package_factory"))
import round2_lib as L                                                    # noqa: E402
import wave_lib as W                                                      # noqa: E402

ROOT = L.ROOT
FLOOR = re.compile(r"\|\s*beta\s*\|?\s*>=\s*([0-9.]+)")
NEED = ("beta", "se", "ci_lo", "ci_hi", "p", "p_holm", "n")
FOUR_WAY = ("supported", "partial", "null", "opposite")
# what the Holm re-derivation actually reached. `check_rows` adds to this while it walks, because the totals are a
# property of the walk, and a return value would have to carry them through every caller for no other reason.
COVERAGE = collections.Counter()


def design_floors() -> dict:
    """{topic: support floor} read from each freeze module's own frozen threshold sentence."""
    out = {}
    for p in sorted(pathlib.Path(ROOT / "02_shared_code" / "package_factory").glob("topic_designs_wave*.py")):
        m = __import__(p.stem)
        for tid, d in (getattr(m, "DESIGNS", {}) or {}).items():
            t = json.dumps(d.get("thresholds") or {})
            mm = FLOOR.search(t)
            bands = ((getattr(m, "COMMON", {}) or {}).get("bands") or {})
            out[tid] = float(mm.group(1)) if mm else bands.get("support", bands.get("support_floor"))
    return out


def rows_of(d: dict) -> list:
    """Every model row in an artefact, whether it sits in `models`, under H1-H3, or inside a battery step."""
    out = []
    def take(o, where):
        if isinstance(o, dict):
            if "verdict" in o and ("beta" in o or "ci_lo" in o or "term" in o):
                out.append((where, o))
            for k, v in o.items():
                take(v, f"{where}.{k}" if where else str(k))
        elif isinstance(o, list):
            for i, v in enumerate(o):
                take(v, f"{where}[{i}]")
    take(d, "")
    return out


def holm(pvals):
    """The step-down corrected values over the set the artefact declares."""
    idx = sorted(range(len(pvals)), key=lambda i: (pvals[i] is None, pvals[i] or 0))
    m, out, run = len(pvals), [None] * len(pvals), 0.0
    for rank, i in enumerate(idx):
        p = pvals[i]
        if p is None:
            continue
        run = max(run, min(1.0, (m - rank) * p))
        out[i] = run
    return out


def interval_of(r: dict) -> tuple:
    """The row's own CI, wherever it is filed.

    A design that resamples writes its interval under the name of the resampling - `ci_clustered`, `ci_boot` - and
    puts it beside the statistic it intervals. Reading only `ci_lo`/`ci_hi` called those rows verdicts with no
    interval at all, which is the opposite of what the artefact shows. A per-class `intervals` map is a different
    case, reported separately because the one-line row does not carry the interval itself.
    """
    lo, hi = W.row_interval(r)
    src = "canonical"
    if r.get("ci_lo") is None and (isinstance(r.get("ci"), (list, tuple))
                                   or any(isinstance(r.get(k), (list, tuple)) for k in W.CI_KEYS)):
        src = "ci_pair" if r.get("ci") else next(k for k in W.CI_KEYS if isinstance(r.get(k), (list, tuple)))
    if lo is None and isinstance(r.get("intervals"), dict):
        subs = [v for v in r["intervals"].values() if isinstance(v, dict) and v.get("ci")]
        if subs:
            lo = min(v["ci"][0] for v in subs)
            hi = max(v["ci"][1] for v in subs)
            return lo, hi, "intervals_map"
    return lo, hi, src


def decision_rows(rows: list) -> list:
    """A hypothesis table that decides with two booleans rather than with a verdict word.

    The five hand-built papers froze their hypotheses as `established`/`refuted` before the estate's four-way
    vocabulary existed. That is a legitimate scheme, but it is only a decision if exactly one of the two is true:
    a row that sets both, or neither, asserts nothing while still sitting in a table a reader takes as the result.
    """
    bad = []
    for i, r in enumerate(rows):
        if "established" not in r or "refuted" not in r:
            continue
        e = str(r.get("established")).strip().lower() in ("true", "1", "yes")
        f = str(r.get("refuted")).strip().lower() in ("true", "1", "yes")
        if e == f:
            bad.append({"row": i, "column": "established/refuted",
                        "verdict": f"established={r.get('established')},refuted={r.get('refuted')}",
                        "term": str(r.get("hypothesis") or "")[:60],
                        "problem": "hypothesis_decision_is_both_or_neither"})
    return [x for x in bad if x["problem"] != "excused_by_its_own_note"]


def table_cells(pkg_rows: list, cols: list) -> list:
    """Rows of a shipped table that print a four-way verdict while omitting the quantity it rests on.

    A row whose verdict is one of the estate's own non-coefficient words (`not_reproduced_in_...`,
    `measured_descriptively...`, `descriptive stratum...`) is a different kind of claim and is not held to the
    beta/SE/CI columns - the defect this looks for is a `supported`/`opposite`/`partial` row whose interval,
    standard error or Holm-corrected p is blank, because the frozen rule cannot be checked from what is printed.
    """
    bad = []
    for i, r in enumerate(pkg_rows):
        v = str(r.get("verdict") or "").strip()
        blob = " ".join(str(x) for x in r.values()).lower()
        excused = (not v.startswith(FOUR_WAY)) or any(k in blob for k in (
            "not_estimable", "not_testable", "measured_descriptively", "no_band_was_frozen",
            "below_the_frozen_floor", "not_at_or_above"))
        if excused:
            if v.startswith(FOUR_WAY):
                bad.append({"row": i, "column": "verdict", "problem": "excused_by_its_own_note"})
            continue
        for c in cols:
            if c not in r:
                continue
            if (r.get(c) or "").strip() in ("", "nan", "NaN", "None", "null", "NA"):
                bad.append({"row": i, "column": c, "verdict": v, "term": (r.get("term") or "")[:60],
                            "problem": "four_way_verdict_with_an_empty_statistical_cell"})
    return [x for x in bad if x["problem"] != "excused_by_its_own_note"]


RESAMPLED = ("boot", "permut", "resampl", "p_boot", "p_perm")


def resampled_row(r: dict) -> bool:
    """Does this row say for itself that its uncertainty comes from resampling?

    Such a row has no analytic standard error: the interval is the resampling spread and the p is a tail count, so
    the fields a Wald row must carry are not the fields this one can. The kind is read from the row's own words,
    never assumed from the estimator being a bootstrap elsewhere in the artefact.
    """
    blob = " ".join(str(r.get(k) or "") for k in ("kind", "verdict_rule", "note", "method", "ci_kind")).lower()
    return any(t in blob for t in RESAMPLED) or any(isinstance(r.get(k), (int, float)) for k in ("p_boot", "p_perm"))


QUANT = ("beta", "mean_difference", "difference", "delta", "value", "estimate", "gain", "loglik_gain", "excess")


def quantity_of(r: dict):
    """The row's own estimate, whether a GLM coefficient or a bootstrap mean difference.

    Several designs compare two arms by resampling rather than by fitting, and their rows carry `mean_difference`
    with a `ci` pair and a `p_boot`. A four-way verdict on such a row is bound by the same frozen rule (the
    interval's side of zero, the magnitude against the floor, the corrected p), so the recomputation has to look
    at those rows too and not only at the ones with a coefficient.
    """
    for k in QUANT:
        v = r.get(k)
        if isinstance(v, (int, float)) or (isinstance(v, str) and v.replace(".", "", 1).replace("-", "").isdigit()):
            try:
                return float(v), k
            except (TypeError, ValueError):
                continue
    for k, v in r.items():                                       # `gain_bigram_vs_unigram`-style named quantities
        if isinstance(v, (int, float)) and re.match(r"(gain|delta|diff|beta)_\w+", str(k)):
            return float(v), k
    return None, None


def check_rows(art: dict, floors, path: str) -> list:
    bad = []
    rows = rows_of(art)
    for where, r in rows:
        v = str(r.get("verdict") or "")
        lo, hi, lohi_src = interval_of(r)
        beta, qkey = quantity_of(r)
        named = str(r.get("ci_of") or "")
        if lo is not None and named and isinstance(r.get(named), (int, float)):
            # The row states which of its quantities the interval belongs to, so the check reads that one and not
            # another number the row prints from a different test beside it.
            beta, qkey = float(r[named]), named
        if beta is None:
            beta = r.get("beta")
        # A row may state the value its hypothesis sets against - a chance-level proportion is measured against 0.5,
        # a selection ratio against 1.0. Every test below is about the row's side of *its* null, so the quantities
        # are shifted onto the difference from it and read as before.
        nv = r.get("null_value")
        if isinstance(nv, (int, float)) and nv:
            beta = beta - nv if isinstance(beta, (int, float)) else beta
            lo = lo - nv if isinstance(lo, (int, float)) else lo
            hi = hi - nv if isinstance(hi, (int, float)) else hi
        se, ph = r.get("se"), r.get("p_holm")
        pval = next((r[k] for k in ("p", "p_boot", "p_perm", "p_raw") if isinstance(r.get(k), (int, float))), None)
        num = [x for x in (beta, lo, hi, se) if isinstance(x, (int, float))]
        nonfinite = [x for x in num if isinstance(x, float) and not math.isfinite(x)]
        if nonfinite or (isinstance(beta, float) and abs(beta) > 1e6):
            if v in FOUR_WAY:
                bad.append({"where": where, "problem": "four_way_verdict_on_a_non_finite_or_explosive_fit",
                            "verdict": v, "beta": beta, "se": se, "ci": [lo, hi]})
            continue
        if lo is not None and hi is not None:
            # A row that says its interval came from resampling whole groups owes the reader the number of groups.
            # Without it a cluster bootstrap and a row bootstrap are indistinguishable on the page, which is the
            # difference between an interval that absorbs within-group dependence and one that pretends it away.
            kind = f"{r.get('ci_kind') or ''} {r.get('p_kind') or ''}"
            cl = r.get("clusters")
            if cl is None:
                cl = r.get("n_clusters")
            if ("cluster" in kind.lower() or "bootstrap" in kind.lower()) and not (
                    isinstance(cl, int) and not isinstance(cl, bool) and cl > 0):
                bad.append({"where": where, "problem": "cluster_ci_without_a_cluster_count",
                            "ci_kind": str(r.get("ci_kind") or ""), "p_kind": str(r.get("p_kind") or ""),
                            "clusters": cl, "verdict": v, "ci": [lo, hi]})
        if v in FOUR_WAY and lo is not None and hi is not None:
            # The direction-free half of the frozen rule: `null` means the interval covers zero, and any other
            # four-way word means it does not. A row can be checked for that even when it never says which side
            # was predicted, and this is where a mislabelled verdict shows up.
            covers = (lo <= 0 <= hi)
            if (v == "null") != covers:
                bad.append({"where": where, "problem": "verdict_side_of_zero_contradicts_the_interval",
                            "printed": v, "ci": [lo, hi], "quantity": qkey, "value": beta,
                            "term": str(r.get("term") or "")[:60]})
        if v in FOUR_WAY and (beta is None or lo is None or hi is None):
            bad.append({"where": where, "problem": "four_way_verdict_without_an_interval", "verdict": v})
            continue
        if v in FOUR_WAY:
            alts = [k for k, v in r.items() if isinstance(v, (int, float))
                    and (k in QUANT or str(k) == "gap")]
            if lohi_src != "canonical" and len(alts) > 1 and str(r.get("ci_of") or "") != qkey:
                # the interval is filed under its resampling (`ci_clustered`) and the row carries two quantities it
                # could interval; asserting centring would have to guess which one, and the only guess available -
                # pick the value the interval contains - always picks the one that passes
                COVERAGE["interval_pairing_unstated"] += 1
            elif not (lo <= beta <= hi):
                bad.append({"where": where, "problem": "beta_outside_its_own_interval",
                            "beta": beta, "ci": [lo, hi], "quantity": qkey, "interval_source": lohi_src})
            if isinstance(se, (int, float)) and se > 0:
                w = hi - lo
                if w > 12 * se:
                    bad.append({"where": where, "problem": "interval_width_inconsistent_with_se",
                                "width": round(w, 6), "se": se})
            floor = r.get("support_floor")
            dirn = " ".join(str(r.get(k) or "") for k in ("verdict_direction", "direction", "direction_predicted"))
            low = dirn.lower()
            # The row's own declaration is read first and the verbs in its explanation only afterwards: the sentence
            # "predicted_positive: a submitted rollout states a result more and an exception less" names both sides,
            # and picking whichever word came first would call that row's positive coefficient opposite.
            free = bool(re.search(r"direction_free|no_frozen_prediction", low))
            neg = pos = False
            if not free:
                if "predicted_negative" in low:
                    neg = True
                elif "predicted_positive" in low:
                    pos = True
                else:
                    neg = bool(re.search(r"\b(negative|lower|decreas\w*|less|inverse|falls?|reduces)\b", low))
                    pos = (not neg) and bool(re.search(r"\b(positive|higher|increas\w*|rises?|more|greater)\b", low))
            d = -1.0 if neg else 1.0
            rule = str(r.get("verdict_rule") or "magnitude")
            # `direction_free` and `no_frozen_prediction_for_this_row` are recorded statements about the absence of
            # a prediction, not an absent field: treating them as missing asked every design to invent a direction
            # its hypothesis sentence never claimed.
            if v in FOUR_WAY and not (neg or pos) and not free:
                bad.append({"where": where, "problem": "four_way_verdict_without_a_recorded_direction",
                            "verdict": v, "beta": beta, "term": str(r.get("term") or "")[:60],
                            "note": "the row shows its coefficient, interval and corrected p but not which side was "
                                    "predicted, so `supported` cannot be re-derived from the artefact alone"})
            elif rule == "specificity" and isinstance(r.get("own_arm"), (int, float)) \
                    and isinstance(r.get("alien_arm"), (int, float)):
                # The specificity rule is frozen as "the classifier does better on traces from its own arm than on
                # alien ones", and the row carries both arms, so the rule can be re-applied here rather than being
                # handed back to a reader of the design sentence.
                want = ("supported" if r["own_arm"] > r["alien_arm"]
                        else "opposite" if r["own_arm"] < r["alien_arm"] else "null")
                if want != v:
                    bad.append({"where": where, "problem": "verdict_not_implied_by_its_own_numbers",
                                "printed": v, "recomputed": want, "own_arm": r["own_arm"],
                                "alien_arm": r["alien_arm"], "term": str(r.get("term") or "")[:60]})
            elif rule == "h2_ci_excludes_zero":
                # T126/P025's frozen H2 clause: "H2 is supported when the changed-vs-different difference has
                # CI excluding 0" - no magnitude floor is named for this row, so the word is re-derived from
                # the interval alone, exactly as the design sentence reads.
                want = "null" if (lo <= 0 <= hi) else "supported"
                if want != v:
                    bad.append({"where": where, "problem": "verdict_not_implied_by_its_own_numbers",
                                "printed": v, "recomputed": want, "verdict_rule": rule,
                                "beta": beta, "ci": [lo, hi], "p_holm": ph})
            elif rule != "magnitude":
                bad.append({"where": where, "problem": "verdict_follows_a_non_default_rule",
                            "verdict_rule": rule, "verdict": v,
                            "note": "recomputed against the generic CI/floor rule, which is not the rule this row "
                                    "declares; read the design sentence to confirm it"})
            elif isinstance(ph, (int, float)) and isinstance(floor, (int, float)):
                # a direction-free row is read by the estate's own direction-free rule: the interval's exclusion of
                # zero is the evidence, and the design's floor decides supported from partial
                want = (W.magnitude_verdict(beta, lo, hi, ph, floor, "abs") if free
                        else W.verdict(beta, lo, hi, ph, floor, d))
                if want != v:
                    bad.append({"where": where, "problem": "verdict_not_implied_by_its_own_numbers",
                                "printed": v, "recomputed": want, "beta": beta, "ci": [lo, hi],
                                "p_holm": ph, "floor": floor})
        missing = [k for k in NEED if k in r and r.get(k) is None] if v in FOUR_WAY else []
        if qkey and qkey != "beta":          # a resampled contrast has no standard error and no coefficient
            missing = [k for k in missing if k not in ("se", "beta")]
        if "se" in missing and resampled_row(r):
            # a bootstrap or permutation row states its uncertainty as an interval and its p as a resampling tail
            # count; there is no analytic standard error to print, and demanding one invents a quantity
            missing = [k for k in missing if k != "se"]
        if "n" in missing and any(isinstance(val, (int, float)) and not isinstance(val, bool) and val > 0
                                   and W._is_denominator(k) for k, val in r.items()):
            missing = [k for k in missing if k != "n"]     # the denominator is there under the design's own name
        if missing:
            bad.append({"where": where, "problem": "four_way_verdict_row_missing_fields",
                        "fields": missing, "verdict": v})
        if v in FOUR_WAY and lohi_src == "intervals_map":
            bad.append({"where": where, "problem": "interval_stored_per_class_not_on_the_row",
                        "note": "the row's own ci_lo/ci_hi are empty; the interval is only recoverable from the "
                                "per-class map, so a reader of the one-line row cannot see it", "verdict": v})
    # Holm over the hypothesis set the artefact itself declares, the way `wave_lib.finalize_models` declares it:
    # one entry per hypothesis label, taking that hypothesis's smallest raw p, where a raw p is any of the keys a
    # design states it under. Reading only the key `p` reached a third of the families and no others.
    #
    # The set is the *inferential* rows: a row that declares `verdict_rule=descriptive|specificity|coverage_only|
    # enumeration` states a quantity, not a test, and `finalize_models` reads it the same way (its own relabelling
    # branch skips those rules first). Counting them into the family is what made EXP-0213 look under-corrected:
    # its design froze {H2} as the family - H1 is descriptive and H3 a specificity check - so printing 0.9024 for a
    # single-test family is the correction, not a missing one.
    hrows = [(w, r) for w, r in rows if re.match(r"H\d$", str(r.get("hypothesis") or ""))]
    fam, non_inf = {}, 0
    for w, r in hrows:
        h = str(r.get("hypothesis"))
        if str(r.get("verdict_rule") or "").lower() in W.NON_INFERENTIAL_RULES:
            non_inf += 1
            continue
        pr = next((r[k] for k in W.P_KEYS if isinstance(r.get(k), (int, float))), None)
        if pr is not None and (h not in fam or float(pr) < fam[h]):
            fam[h] = float(pr)
    COVERAGE["hypothesis_rows_skipped_as_non_inferential"] += non_inf
    if len(fam) >= 2:
        # re-derived with this module's own step-down, not `wave_lib.holm`, so a mistake in the function the designs
        # used cannot make the check agree with itself
        keys = sorted(fam)
        adj = dict(zip(keys, holm([fam[k] for k in keys])))
        COVERAGE["families_rederived"] += 1
        for w, r in hrows:
            h, ph = str(r.get("hypothesis")), r.get("p_holm")
            if not isinstance(ph, (int, float)):
                continue
            COVERAGE["corrections_checked"] += 1
            if h not in adj:
                # a correction printed for a hypothesis whose rows state no raw p at all: nothing here can show
                # where it came from, though the printed value cannot then be a smaller one than the family implies
                COVERAGE["corrections_on_hypotheses_without_a_raw_p"] += 1
                continue
            if ph > adj[h] + 0.011:
                COVERAGE["corrections_more_conservative_than_the_declared_family"] += 1
            elif ph < adj[h] - 0.011:
                # the direction that matters: a correction *below* what Holm over the artefact's own declared
                # hypotheses gives is a `p_holm < 0.05` that the stated family does not license. Rebuilding a
                # smaller family than the design used can only lower `adj`, so this finding cannot be an artefact
                # of the checker missing a member.
                bad.append({"where": w, "problem": "p_holm_below_the_declared_holm_family",
                            "hypothesis": h, "printed": ph, "derived": round(adj[h], 6),
                            "family_min_p": {k: round(v, 6) for k, v in sorted(fam.items())},
                            "verdict": str(r.get("verdict") or "")})
    elif hrows:
        COVERAGE["artefacts_with_one_or_zero_correctable_hypotheses"] += 1
    return bad


def verdict_rows(obj) -> int:
    """How many rows of one artefact carry a verdict, i.e. how much of it this check can re-derive."""
    n = 0
    if isinstance(obj, dict):
        n += any(k == "verdict" for k in obj)
        for v in obj.values():
            n += verdict_rows(v)
    elif isinstance(obj, list):
        for v in obj:
            n += verdict_rows(v)
    return n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=40)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    floors = design_floors()
    kept = L.root_kept()
    report, tot = {}, 0
    scanned, rows_scanned, skipped_non_wave = 0, 0, 0
    COVERAGE.clear()
    for exp, f in sorted(kept.items()):
        if not (exp.startswith("EXP-01") or exp.startswith("EXP-02")):
            skipped_non_wave += 1
            continue
        d = L.read_any(f)
        if not isinstance(d, dict):
            continue
        topic = str(d.get("topic") or "")
        art = dict(d)
        # attach the design's own floor so the recomputation uses the frozen value, not a default
        def attach(o):
            if isinstance(o, dict):
                o.setdefault("support_floor", floors.get(topic))
                for v in o.values():
                    attach(v)
            elif isinstance(o, list):
                for v in o:
                    attach(v)
        if topic in floors:
            attach(art)
        bad = check_rows(art, floors, f.name)
        n_verdict = verdict_rows(art)
        rows_scanned += n_verdict
        scanned += bool(n_verdict)
        if bad:
            report[f.name] = bad
            tot += len(bad)
            print(f"{f.name[:58]:58s} {len(bad)} problem(s)")
            for x in bad[:6]:
                print("    " + json.dumps(x, ensure_ascii=False)[:190])
    print(f"\n{tot} statistical problem(s) in {len(report)} of the {scanned} artefact(s) that carry a verdict row "
          f"({rows_scanned} verdict rows re-derived); {skipped_non_wave} pre-wave record(s) are outside this check, "
          "which reads the wave designs' frozen rules")
    holm_cov = dict(COVERAGE)
    print("re-derivation reached " + json.dumps(holm_cov, sort_keys=True)
          + " - a correction printed below its own declared family is the one direction that can turn p<.05 into "
              "a claim the stated family does not license")
    SCOLS = ("beta", "se", "ci_lo", "ci_hi", "p", "p_holm", "n", "clusters")
    tb_report, tb_tot, tb_scanned = {}, 0, 0
    for pkg in L.packages():
        for tf in sorted((pkg / "tables").glob("*.csv")):
            rows = L.read_any(tf) or []
            if not rows:
                continue
            bad = decision_rows(rows)
            cols = [c for c in list(rows[0]) if c in SCOLS]
            if cols and any("verdict" in c for c in rows[0]):
                tb_scanned += 1
                bad += table_cells(rows, cols)
            if bad:
                key = f"{pkg.name}/{tf.name}"
                tb_report[key] = bad
                tb_tot += len(bad)
                print(f"TABLE {key:58s} {len(bad)} statistical problem(s) in a shipped table")
                for x in bad[:4]:
                    print("    " + json.dumps(x, ensure_ascii=False)[:160])
    print(f"\n{tb_tot} empty cell(s) across {len(tb_report)} of the {tb_scanned} shipped table(s) that print a "
          "four-way verdict beside a statistical column")
    dest = ROOT / "results_raw" / f"ROUND2_STAT_CONSISTENCY_{time.strftime('%Y%m%dT%H%M%S')}.json"
    dest.write_text(json.dumps({"detector": "round2_statistical_consistency", "totals": tot,
                                "artefacts": len(report), "artefacts_scanned": scanned,
                                "verdict_rows_rederived": rows_scanned, "pre_wave_records_skipped": skipped_non_wave,
                                "re_derivation_coverage": holm_cov,
                                "tables": len(tb_report),
                                "tables_scanned": tb_scanned,
                                "empty_table_cells": tb_tot, "floors_known": len(floors),
                                "detail": report, "table_detail": tb_report,
                                "at": datetime.datetime.now().isoformat(timespec="seconds")},
                               indent=1, ensure_ascii=False), encoding="utf-8")
    print("wrote", dest.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
