"""Shared measurement and inference library for the wave packages (T101+).

Everything a wave design is *allowed* to touch lives here, so that a topic cannot quietly acquire a new definition
of "constraint" or a new bootstrap rule halfway to a result. Four rules govern the file:

1. **Dev rows only.** `load_routing` refuses any row whose frozen split is not `dev`, and counts what it dropped.
   P001's test split is evaluated exactly once, in P001; a wave package must not read it at all.
2. **Import, do not rewrite.** The tokeniser, the BM25 scorer and the catalogue parser are the ones P001 shipped
   (`build_toucan_retrieval`), so a wave number and a P001 number mean the same thing.
3. **Cluster where the feature is computed.** A query-level statistic clusters on the query; a candidate-level
   statistic clusters on the query too, never on its own rows. `cluster_boot` enforces that the caller names the
   cluster column.
4. **No judge, no API.** Rule and lexical extractors plus classical statistics; the one pretrained component is the
   locally-run encoder in `load_encoder_vectors`, which reads a cached `.npy` produced by a local process.

    from wave_lib import load_routing, cluster_boot, verdict
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import os
import pathlib
import re
import sys
import time
from collections import Counter, defaultdict

import numpy as np
import pandas as pd
from scipy import stats

HERE = pathlib.Path(__file__).resolve().parent
ROOT = next(a for a in (HERE, *HERE.parents) if (a / "00_program_registry").is_dir())
sys.path.insert(0, str(ROOT / "02_shared_code" / "trajectory_parser"))
sys.path.insert(0, str(ROOT / "02_shared_code" / "statistics"))

from build_toucan_retrieval import BM25, doc_tokens, parse_catalog, toks  # noqa: E402  (frozen, imported)

SEED = 42
PROC = ROOT / "01_datasets" / "processed"        # frozen INPUT frames (read-only for every package)
# `AIB_ARTEFACT_DIR` / `AIB_PROCESSED_DIR` exist for the clean-room re-runs: a verification pass that writes into the
# estate's own results directories would replace the measured run with itself, which is how a 4,500-row quick sample
# once overwrote a 24,000-row canonical artefact. With the override the re-run lands beside the original and the two
# are compared as files.
RAWRES = pathlib.Path(os.environ.get("AIB_ARTEFACT_DIR") or ROOT / "results_raw")
PROCES = ROOT / "results_processed"        # shared INPUTS: always the estate, never redirected
# `OUT` is where *this run* writes, and is the side the clean-room override redirects. Collapsing input and output into
# one constant made a verification re-run look for the shared matrix inside its own empty scratch directory.
OUT = pathlib.Path(os.environ.get("AIB_PROCESSED_DIR") or ROOT / "results_processed")
LOGS = ROOT / "logs"
BANDS = dict(small=0.05, medium=0.15, large=0.30)
CONFIGS = ("OSS", "Qwen3", "Kimi-K2")


def stamp() -> str:
    return time.strftime("%Y%m%dT%H%M%S")


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def _drop_non_finite(o):
    """NaN and infinity are not measurements. `json.dumps` happily writes `NaN`, which is not valid JSON, and a CSV
    writer turns it into the string `nan` in a cell a reader takes for a missing value; both become null here so an
    unestimable quantity is reported as absent rather than as a number that is not one."""
    if isinstance(o, float) and not math.isfinite(o):
        return None
    if isinstance(o, dict):
        return {k: _drop_non_finite(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_drop_non_finite(v) for v in o]
    return o


_DESIGNS = None


def design_hypotheses(topic: str) -> list:
    """The frozen hypothesis sentences for a topic, whichever wave module froze it (cached across a run)."""
    global _DESIGNS
    if _DESIGNS is None:
        _DESIGNS = {}
        here = pathlib.Path(__file__).resolve().parent
        for f in sorted(here.glob("topic_designs_wave*.py")):
            try:
                m = importlib.import_module(f.stem)
            except Exception:                                        # noqa: BLE001 - a module that will not import
                continue                                             # contributes no designs, and says so elsewhere
            for tid, d in (getattr(m, "DESIGNS", {}) or {}).items():
                _DESIGNS.setdefault(tid, d.get("hypotheses") or [])
    return _DESIGNS.get(topic) or []


FOUR_WAY = ("supported", "partial", "null", "opposite")
FLOOR_RX = re.compile(r"\|\s*beta\s*\|?\s*>=\s*([0-9.]+)")
_FLOORS = None


def design_floor(topic: str):
    """The support floor the topic's own frozen threshold sentence names, or None when it names no floor.

    `magnitude_verdict` needs this to decide between `supported` and `partial`, and the round-2 detector reads the
    same sentence from the same module - so both sides of the check take the threshold from the design, not from a
    default this library invents.
    """
    global _FLOORS
    if _FLOORS is None:
        _FLOORS = {}
        here = pathlib.Path(__file__).resolve().parent
        for f in sorted(here.glob("topic_designs_wave*.py")):
            try:
                m = importlib.import_module(f.stem)
            except Exception:                                        # noqa: BLE001 - see design_hypotheses
                continue
            bands = (getattr(m, "COMMON", {}) or {}).get("bands") or {}
            default = bands.get("support") or bands.get("support_floor")
            for tid, d in (getattr(m, "DESIGNS", {}) or {}).items():
                mm = FLOOR_RX.search(json.dumps(d.get("thresholds") or {}))
                _FLOORS.setdefault(tid, float(mm.group(1)) if mm else default)
    return _FLOORS.get(topic)

# `p_exact` is a Fisher or binomial exact probability - a p-value under the frozen rule, printed under the name the
# estimator gives it. Reading only the five names above left such a row looking like a verdict with no test at all.
P_KEYS = ("p", "p_boot", "p_perm", "p_raw", "p_lr", "p_exact")
DIRECTION_KEYS = ("verdict_direction", "direction", "direction_predicted")
# the nouns this programme's designs use for their unit of observation, i.e. a positive value here is a stated
# denominator for the row that carries it
# rule names the designs use for a comparison that asserts no effect direction and fits no sampling model; a
# four-way word on such a row would be an inferential claim the row's own rule disclaims
NON_INFERENTIAL_RULES = {"descriptive", "specificity", "coverage_only", "enumeration"}
_UNITS = {"n", "rows", "queries", "turns", "conversations", "trajectories", "prompts", "documents", "steps",
          "messages", "episodes", "rollouts", "instances", "observations", "cases", "sessions", "attempts",
          "tasks", "records", "events", "calls", "pairs", "samples", "clusters", "candidates", "examples",
          "sequences", "tools", "items", "shards", "repos", "nodes", "links", "windows", "arms", "cells",
          "groups", "files", "edges", "submissions", "pr_numbers", "sentences", "catalogues", "transitions"}


def _is_denominator(key: str) -> bool:
    """Does this field name the number of observations an estimate was computed over?

    Only unit-of-observation nouns count. A feature count (`n_tokens`, `n_chars`) says how big a row is, not how
    many rows the estimate rests on, so it must not satisfy the denominator guard - that would let the check pass
    on exactly the rows it exists to catch. The designs state their unit several ways: `n`, `conversations`,
    `transitions`, and compounds that put the unit first (`rows_in_random_arm`).
    """
    k = str(key).lower()
    if k in _UNITS or k.endswith(("_count", "_total")):
        return True
    toks = k.split("_")
    if toks[0] in _UNITS:
        return True
    head, _, tail = k.partition("_")
    return head in ("n", "num", "total") and tail in _UNITS


def finalize_models(models: list, holm_ok: bool = True, floor=None) -> list:
    """Make every four-way verdict provable from the row that carries it.

    The frozen vocabulary is defined by three quantities: the interval's side of zero, the magnitude against the
    design's own floor, and Holm-corrected p < 0.05 over the hypotheses the design declared. Waves 7-12 shipped rows
    printed `supported` or `opposite` with no `p_holm` (a bootstrap or permutation row that was left out of the
    Holm family), and wave 1 shipped rows with no interval at all - so the artefact asserted a verdict it could not
    show. Two things happen here, in this order:

    1. a row inside a declared hypothesis whose only missing quantity is the correction gets `p_holm` computed by
       Holm over exactly the hypotheses the design carries, each hypothesis contributing its smallest p;
    2. a row that still lacks one of the three governing quantities is relabelled with the estate's own
       non-inferential word for that case, so nothing is silently left claiming a support it cannot evidence.
    """
    rows = [r for r in (models or []) if isinstance(r, dict)]
    fam, supplier = {}, {}
    for r in rows:
        h = str(r.get("hypothesis") or "")
        p = next((r[k] for k in P_KEYS if isinstance(r.get(k), (int, float))), None)
        if re.match(r"H\d$", h) and p is not None:
            if h not in fam or float(p) < fam[h]:
                fam[h], supplier[h] = float(p), r
    adj = holm(dict(fam)) if len(fam) >= 2 else dict(fam)
    for r in rows:
        v = str(r.get("verdict") or "")
        if v not in FOUR_WAY:
            continue
        h = str(r.get("hypothesis") or "")
        if str(r.get("verdict_rule") or "").lower() in NON_INFERENTIAL_RULES:
            # Checked first, because a row whose own declared rule says "this is a description, no sampling model was
            # fitted" is not a failed estimate: demoting it for carrying no interval would tell the reader the design
            # could not measure the quantity, when the truth is that it never claimed an inference from it.
            r["verdict"] = "measured_descriptively_rule_declared_non_inferential"
            r["note"] = (str(r.get("note") or "") + f" | round-2: this row declares verdict_rule="
                                                    f"{r.get('verdict_rule')!r}, which is not an inferential rule, "
                                                    "so no four-way word belongs on it").strip()
            continue
        # Only the row whose own test produced the family's smallest p may carry the corrected value. An earlier
        # version wrote `adj[h]` onto every row labelled H_h, which handed a permutation p to a descriptive share
        # that has no test at all - a number in a shipped table that no measurement of that quantity produced.
        if r.get("p_holm") is None and holm_ok and supplier.get(h) is r:
            r["p_holm"] = adj[h]
            r["p_holm_derived_by_round2_finalize"] = True
        lo, hi = row_interval(r)
        # The row may name the value its hypothesis is measured against (a chance-level proportion against 0.5, a
        # selection ratio against 1.0). The invariants below are about the interval's side of that value, so they
        # read the shifted bounds while the row keeps printing the quantity as it was measured.
        nv = r.get("null_value")
        if isinstance(nv, (int, float)) and nv:
            lo = lo - nv if isinstance(lo, (int, float)) else lo
            hi = hi - nv if isinstance(hi, (int, float)) else hi
        has_p = r.get("p_holm") is not None or any(isinstance(r.get(k), (int, float)) for k in P_KEYS)
        has_n = r.get("n") is not None or r.get("clusters") is not None or r.get("rows") is not None
        if not has_n:
            # the estate's designs mostly name their denominator `n`, but a step-level or turn-level design records
            # it as `conversations`, `turns`, `trajectories` - reading only the three literal keys demoted rows
            # whose denominator was stated, which is the opposite of what this function is for
            has_n = any(isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0 and _is_denominator(k)
                        for k, v in r.items())
        if lo is None or hi is None:
            r["verdict"] = "not_estimable_no_interval_for_this_statistic"
            r["note"] = (str(r.get("note") or "") + " | round-2: `supported`/`null` require an interval that "
                                                    "excludes or covers zero, and this row carries none").strip()
        elif not has_p:
            r["verdict"] = "not_estimable_no_corrected_p_in_the_frozen_family"
            r["note"] = (str(r.get("note") or "") + " | round-2: the Holm family this design declared does not "
                                                    "include this statistic, so no corrected p exists").strip()
        elif not has_n:
            r["verdict"] = "not_estimable_denominator_not_recorded"
            r["note"] = (str(r.get("note") or "") + " | round-2: neither rows, clusters nor an n was recorded, so "
                                                    "the estimate has no stated denominator").strip()
        # ---- an invariant that holds whatever name the design gives its rule --------------------------------
        if str(r.get("verdict") or "") == "supported" and lo is not None and hi is not None \
                and float(lo) <= 0 <= float(hi):
            # `supported` asserts an effect; an interval that covers zero is the definition of not having shown one,
            # whatever the row's own rule is called. The predicted side is not what is in question here, so the
            # word becomes `null` - the estate's word for "measured, and nothing separates it from zero" - and
            # `verdict_direction` still carries which way the point estimate went.
            r["verdict"] = "null"
            r["note"] = (str(r.get("note") or "") + " | round-2: printed `supported` on an interval that covers "
                                                    "zero, which no rule can read as an effect; the estimate is "
                                                    "reported as null and its side is left in verdict_direction"
                        ).strip()
        # A row that no frozen hypothesis sentence covers is secondary - a control term, a per-stratum slice. The
        # absence of a prediction is then a fact about the row, and the artefact has to say it rather than leave
        # the field blank for a reader to guess at. Stamped first, because the direction-free rule below reads it:
        # recording the absence and then applying the rule in one pass is what makes the shipped word the one a
        # reader can re-derive, instead of one that only changes when the artefact is re-run.
        rec = " ".join(str(r.get(k) or "") for k in DIRECTION_KEYS)
        if str(r.get("verdict") or "") in FOUR_WAY and not rec.strip():
            r["verdict_direction"] = "no_frozen_prediction_for_this_row"
            rec = r["verdict_direction"]
        free = bool(re.search(r"direction_free|no_frozen_prediction", rec, re.I))
        if free and str(r.get("verdict") or "") in FOUR_WAY and lo is not None and hi is not None:
            declared_rule = str(r.get("verdict_rule") or "").strip().lower()
            if declared_rule and declared_rule not in NON_INFERENTIAL_RULES:
                # The row declares its own inferential rule (e.g. T126's H2: supported when the contrast's CI
                # excludes zero - topic_designs_wave4 thresholds.h2). Its design sentence governs the word, so
                # the generic direction-free magnitude re-derivation must not overwrite it; the
                # statistical-consistency detector re-derives the word from the declared rule instead.
                continue
            # A row that records no frozen direction cannot carry a word that means "as predicted" or "against the
            # prediction". The estate already has the rule for that case - `magnitude_verdict`, the direction-free
            # three-way rule the freezes state for hypotheses written as "differs" or "changes" - so the word is
            # re-derived with it, on the row's own interval, corrected p and the floor its design names.
            val = r.get("beta")
            if not isinstance(val, (int, float)) and isinstance(r.get(str(r.get("ci_of") or "")), (int, float)):
                val = r[str(r["ci_of"])]
            if isinstance(val, (int, float)) and isinstance(nv, (int, float)) and nv:
                val = val - nv
            fl = r.get("support_floor") if isinstance(r.get("support_floor"), (int, float)) else floor
            ph = r.get("p_holm")
            if ph is None and not holm_ok:
                # a row finalised outside its design's declared Holm family has no corrected p to wait for: the test
                # it carries is its own, and a single-hypothesis family leaves the corrected value equal to it
                ph = next((r[k] for k in P_KEYS if isinstance(r.get(k), (int, float))), None)
            want = magnitude_verdict(val, lo, hi, ph, fl, "abs")
            if want != r["verdict"]:
                r["note"] = (str(r.get("note") or "") + f" | round-2: printed `{r['verdict']}` on a row that states "
                                                        f"no direction was frozen; the word is re-derived from its "
                                                        f"own interval, corrected p and the design's floor").strip()
                r["verdict"] = want
        if str(r.get("verdict") or "") in FOUR_WAY and not rec.strip():
            r["verdict_direction"] = "no_frozen_prediction_for_this_row"
    return models or []


TOPIC_KEY = re.compile(r"^T\d{3}$")
_TOPICS_BY_EXP = None


def registry_topic(exp_id: str) -> str:
    """The topic a registered run measured, read from the master register when the artefact does not say.

    Several waves write one artefact per topic without carrying a `topic` field, and the freeze keys its summaries
    by topic (`{"T101": {"models": [...]}}`). Without the register the design sentences - and so the predicted side
    and the floor - could not be attached to those rows, and every one of them read as a verdict with no prediction.
    """
    global _TOPICS_BY_EXP
    if _TOPICS_BY_EXP is None:
        _TOPICS_BY_EXP = {}
        f = ROOT / "00_program_registry" / "experiment_registry.csv"
        if f.is_file():
            import csv as _csv
            import io as _io
            for r in _csv.DictReader(_io.StringIO(f.read_text(encoding="utf-8-sig"))):
                t = [x for x in re.split(r"[;,]", str(r.get("topic_id") or "")) if TOPIC_KEY.match(x.strip())]
                if len(t) == 1:
                    _TOPICS_BY_EXP.setdefault(str(r.get("exp_id") or "").replace("-", ""), t[0].strip())
    return _TOPICS_BY_EXP.get(str(exp_id).replace("-", ""), "")

# a design that resamples files its interval under the name of the resampling; reading only `ci_lo`/`ci_hi` called
# such a row a verdict with no interval and demoted a claim the row does evidence
CI_KEYS = ("ci_clustered", "ci_boot", "ci_bootstrap", "ci_perm", "ci_resampled")


def row_interval(r: dict) -> tuple:
    """The (lo, hi) a row carries, under whichever of the estate's names it was filed."""
    lo, hi = r.get("ci_lo"), r.get("ci_hi")
    if (lo is None or hi is None) and isinstance(r.get("ci"), (list, tuple)) and len(r.get("ci") or []) == 2:
        lo, hi = r["ci"]
    if lo is None or hi is None:
        for k in CI_KEYS:
            v = r.get(k)
            if isinstance(v, (list, tuple)) and len(v) == 2 and all(isinstance(x, (int, float)) for x in v):
                lo, hi = v[0], v[1]
                break
    return lo, hi


def normalise_rows(obj, topic: str = "") -> int:
    """Run the four-way verdict rules over every row the artefact holds, wherever the design filed it.

    `finalize_models` was called on a top-level `models` list only. Wave 1's summaries key the artefact by topic
    (`{"T101": {"models": [...]}}`), and several designs file one hypothesis's row under the hypothesis name itself
    (`{"H1": {...}}`), so those rows never met the rules: an `opposite` with no prediction frozen, a `supported` with
    no test, a stratum row with no interval. Every one of them is the same defect the pass exists to find.

    A row found outside a `models` list is normalised with `holm_ok=False`: it is not the declared family the design
    froze, so inventing a corrected p for it would put a number in the artefact no measurement produced.
    """
    seen, n = set(), 0

    def is_row(x):
        return isinstance(x, dict) and str(x.get("verdict") or "") != ""

    def walk(o, tp):
        nonlocal n
        if isinstance(o, dict):
            tp = str(o.get("topic") or tp)
            for k, v in o.items():
                if TOPIC_KEY.match(str(k)):
                    walk(v, str(k))
                    continue
                if isinstance(v, list) and v and all(is_row(x) for x in v):
                    for x in v:
                        seen.add(id(x))
                    attach_directions(v, design_hypotheses(tp))
                    finalize_models(v, floor=design_floor(tp))
                    n += len(v)
                    continue
                walk(v, tp)
            if is_row(o) and id(o) not in seen:
                seen.add(id(o))
                attach_directions([o], design_hypotheses(tp))
                finalize_models([o], holm_ok=False, floor=design_floor(tp))
                n += 1
        elif isinstance(o, list):
            for v in o:
                walk(v, tp)

    walk(obj, topic)
    return n


def write_raw(exp_id: str, tag: str, obj: dict) -> pathlib.Path:
    RAWRES.mkdir(parents=True, exist_ok=True)
    # A four-way verdict is only meaningful against a prediction, and the prediction lived in the freeze document
    # rather than in the artefact, so a reader holding one artefact could not re-derive `supported` from
    # `opposite`. The row carries it from here on, read off the design that froze it.
    if isinstance(obj, dict):
        normalise_rows(obj, str(obj.get("topic") or registry_topic(exp_id)))
    obj = _drop_non_finite(obj)
    p = RAWRES / f"{exp_id.replace('-', '')}_{tag}_{stamp()}.json"
    p.write_text(json.dumps(obj, indent=1, ensure_ascii=False, sort_keys=True, default=str), encoding="utf-8")
    return p


# --------------------------------------------------------------------------------- substrate loading (dev only)
def as_int_list(g):
    """gold_idx reaches us as a real list, a numpy array, or the string "[0, 3]" depending on the frame's writer.

    The routing frames were written by two builders at different times and only one of them kept the arrow list type,
    so a silent `int(g)` on the string form raises deep inside a bootstrap instead of here.
    """
    if g is None or (isinstance(g, float) and not math.isfinite(g)):
        return []
    if isinstance(g, (list, tuple, np.ndarray)):
        return [int(x) for x in g]
    s = str(g).strip()
    if not s:
        return []
    if s.startswith("["):
        return [int(x) for x in json.loads(s)]
    return [int(float(x)) for x in re.split(r"[;,]", s) if x.strip()]


def load_routing(cfgs=CONFIGS, bucket="dev", cols=None) -> pd.DataFrame:
    """Read P001's frozen routing frames and keep exactly one split.

    The split filter is an assertion, not a preference: dropping a `test` row silently would let a wave package
    estimate on data it has no licence to open, so the function raises if the requested bucket is empty and reports
    the excluded bucket counts in `load_routing_audit`.
    """
    frames = []
    audit = {}
    for cfg in cfgs:
        f = PROC / f"routing_{cfg}.parquet"
        if not f.is_file():
            raise FileNotFoundError(f"missing frozen frame {f}")
        df = pd.read_parquet(f)
        counts = {str(k): int(v) for k, v in df["split"].value_counts().items()}
        keep = df[df["split"].astype(str) == bucket].copy()
        if keep.empty:
            raise ValueError(f"{cfg}: no rows in split {bucket!r} (present: {counts})")
        keep["cfg"] = cfg
        audit[cfg] = {"rows_total": int(len(df)), "split_counts": counts, "rows_kept": int(len(keep))}
        frames.append(keep)
    out = pd.concat(frames, ignore_index=True)
    out["query_id"] = out["cfg"].astype(str) + "|" + out["uuid"].astype(str)
    out["catalog_json"] = out["catalog_json"].astype(str)
    out["gold_idx"] = out["gold_idx"].apply(as_int_list)
    if cols:
        out = out[[c for c in out.columns if c in cols or c in ("cfg", "uuid", "query_id")]]
    out.attrs["load_routing_audit"] = audit
    return out.reset_index(drop=True)


def catalog_entries(df: pd.DataFrame) -> list:
    """The per-query candidate catalogues, parsed by P001's own parser (None where that parser rejects the row)."""
    return [parse_catalog(j) for j in df["catalog_json"].tolist()]


def read_catalog(s: str, n_candidates: int = None, row_id: str = "") -> list:
    """Read a per-query catalogue in either of the two shapes the frozen frames actually carry.

    `build_toucan_retrieval` stores full `{"name","description","parameters"}` objects, while the routing frames store
    a compact `{"n","d","p"}` form written by the routing builder. The compact form is *normalised back* to the full
    key names so every downstream function (including the imported `doc_tokens`) sees one shape.

    The length assertion is the point of this function: EXP-0119's first run produced 24,000 query rows and zero
    candidate rows because the parser rejected every compact catalogue and the loop silently skipped them. A
    candidate-level design that quietly loses its candidates would report a result computed on nothing.
    """
    entries = parse_catalog(s)
    if entries is None:
        try:
            raw = json.loads(s) if isinstance(s, str) else s
        except Exception:                                       # noqa: BLE001 - not JSON at all
            raw = None
        if isinstance(raw, list):
            entries = [{"name": str(e.get("n") or e.get("name") or ""),
                        "desc": str(e.get("d") or e.get("description") or ""),
                        "params": list(e.get("p") or e.get("params") or [])}
                       for e in raw if isinstance(e, dict) and (e.get("n") or e.get("name"))]
    entries = entries or []
    if n_candidates is not None and len(entries) != int(n_candidates):
        raise AssertionError(f"catalogue parse mismatch on {row_id}: parsed {len(entries)}, "
                             f"frame says {n_candidates}")
    return entries


def hermes_routing(bucket="external") -> pd.DataFrame:
    """The second-corpus routing frame, used only as external transfer - its rows are not pooled with Toucan's."""
    return load_routing(cfgs=("HERMES",), bucket=bucket)


# ------------------------------------------------------------------------------------ linguistic extractors
TEMPORAL = ["today", "yesterday", "tomorrow", "last week", "last month", "last year", "next week", "next month",
            "recent", "recently", "earlier", "since", "during", "while", "before", "after", "then", "when",
            "daily", "weekly", "monthly", "quarterly", "annual", "quarter", "weekend", "season"]
DATE_RE = re.compile(r"\b(\d{4}-\d{1,2}(-\d{1,2})?|\d{1,2}/\d{1,2}/\d{2,4}|(jan|feb|mar|apr|may|jun|jul|aug|"
                     r"sep|oct|nov|dec)[a-z]* \d{1,2})\b", re.I)
NUM_RE = re.compile(r"\b(top|first|last|least|most|at least|no more than|up to|around|about)?\s*\d+(st|nd|rd|th)?\b")
NUMWORD = ["one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "hundred", "thousand"]
FORMAT_WORDS = ["json", "csv", "tsv", "xml", "yaml", "md", "markdown", "pdf", "html", "txt", "parquet", "excel",
                "table", "list", "array", "dict", "dictionary", "tuple", "dataframe", "string", "integer", "float",
                "boolean", "format", "formatted", "structure", "structured", "schema", "extension", "uppercase",
                "lowercase", "snake_case", "camelcase", "sorted", "ascending", "descending", "deduplicated",
                "abbreviation", "acronym", "iso", "utc", "timestamp", "precision", "decimal"]
SCOPE_WORDS = ["only", "all", "every", "each", "any", "just", "alone", "excluding", "including", "within",
               "limited to", "specific", "particular", "among", "across", "entire", "whole", "both", "either",
               "neither", "restrict", "filter", "subset", "range", "between", "except", "instead of", "relevant"]
NEG_WORDS = ["not", "no ", "none", "never", "without", "avoid", "exclude", "don't", "does not", "did not",
             "cannot", "can't", "must not", "rather than", "unless", "neither", "remove", "nothing"]
ANAPHORA = ["it", "they", "them", "this", "that", "these", "those", "there", "their", "its", "one", "ones",
            "same", "above", "previous", "former", "latter"]
TRANSITIVE = ["fix", "update", "refactor", "add", "remove", "check", "run", "deploy", "migrate", "sort", "filter",
              "merge", "convert", "parse", "download", "install", "rename", "create", "delete", "optimise",
              "optimize", "debug", "test", "summarise", "summarize", "translate", "extract", "compute", "generate",
              "compare", "identify", "find", "locate", "replace", "append", "insert", "count", "print", "return",
              "write", "read", "open", "close", "fetch", "query", "search", "retrieve", "verify", "validate"]
PROPER_RE = re.compile(r"(?<![.\s])[A-Z][a-z]{2,}|[A-Za-z][A-Za-z0-9_]*[0-9]|[a-z0-9][A-Z][a-z]+|"
                       r"\b[\w.-]+\.(?:py|js|ts|json|csv|md|txt|yml|yaml|parquet|html|sql|ipynb|sh|lock|toml)\b")
SENT_RE = re.compile(r"[^.!?]+[.!?]?")


def _sentences(text: str) -> list:
    return [s.strip() for s in SENT_RE.findall(str(text or "")) if s.strip()]


def constraint_markers(text: str) -> dict:
    """The six frozen constraint families, counted as marker occurrences per family.

    `entity` counts named entities (proper-noun-like spans), which is what the freeze means by an entity constraint:
    the instruction pins the target to a named thing. `numeric` counts both digits and number words.
    """
    ql = " " + re.sub(r"\s+", " ", str(text or "").lower()) + " "
    ntok = max(1, len([t for t in re.split(r"\W+", ql) if t]))
    temporal = sum(ql.count(" " + w + " ") for w in TEMPORAL) + len(DATE_RE.findall(str(text)))
    numeric = len(NUM_RE.findall(ql)) + sum(ql.count(" " + w + " ") for w in NUMWORD)
    fmt = sum(ql.count(" " + w + " ") for w in FORMAT_WORDS)
    scope = sum(ql.count(" " + w + " ") for w in SCOPE_WORDS)
    neg = sum(ql.count(" " + w + " ") for w in NEG_WORDS)
    ent = len(PROPER_RE.findall(str(text or "")))
    return dict(temporal=temporal, entity=ent, numeric=numeric, format=fmt, scope=scope, negation=neg,
                total=temporal + ent + numeric + fmt + scope + neg, types=int(sum(
                    1 for v in (temporal, ent, numeric, fmt, scope, neg) if v > 0)), per_100=round(
                    100.0 * (temporal + ent + numeric + fmt + scope + neg) / ntok, 4))


def unresolved_references(text: str) -> int:
    """Anaphora with no content-word antecedent earlier in the same sentence.

    Deliberately conservative: a sentence like "summarise the report and email it" has an antecedent ("report") and
    is NOT counted. Only a bare "it"/"this" whose sentence offers nothing before it to attach to is, which is the
    underspecification the construct is about rather than ordinary cohesion.
    """
    n = 0
    for s in _sentences(text):
        w = re.findall(r"[a-z']+", s.lower())
        for i, t in enumerate(w):
            if t in ANAPHORA and not any(
                    x not in ANAPHORA and x not in _STOP_SET and len(x) > 2 for x in w[:i]):
                n += 1
    return n


_STOP_SET = set("""a an the and or of to in on for with without you your our i my is are be can could will would
should please them they it this that these those from at as by if then there here what which how when where who all
any some one two three first also just need want me help make do does did done we us his her its to's""".split())


def ellipsis(text: str) -> int:
    """Imperative clauses whose transitive verb has no object slot filled before the clause ends."""
    n = 0
    for s in _sentences(text):
        for clause in re.split(r",|;|\band\b", s.lower()):
            w = [x for x in re.findall(r"[a-z']+", clause)]
            if not w:
                continue
            for k, t in enumerate(w):
                if t in TRANSITIVE:
                    head = w[k + 1:]
                    if not any(x not in ANAPHORA and x not in _STOP_SET and len(x) > 2 for x in head):
                        n += 1
                    break
    return n


def entity_density(text: str, n_chars: float = None) -> float:
    nc = float(n_chars) if n_chars and n_chars > 0 else max(1.0, float(len(str(text or ""))))
    return round(100.0 * len(PROPER_RE.findall(str(text or ""))) / nc, 4)


def zscore(v: pd.Series) -> pd.Series:
    sd = float(v.std(ddof=0))
    if not math.isfinite(sd) or sd == 0:
        return pd.Series(np.zeros(len(v)), index=v.index)
    return (v.astype(float) - float(v.mean())) / sd


def underspec_index(df: pd.DataFrame) -> pd.Series:
    """z-scored, sign-fixed per the freeze: higher = LESS specified.

    constraint count and entity density enter negatively (they are specification); unresolved references and ellipsis
    enter positively (they are missingness). Equal weights, because the freeze fixed equal weights before anything
    was read - a weighted index would need a rationale the protocol does not have.
    """
    parts = pd.DataFrame({"c": -zscore(df["constraint_total"]), "u": zscore(df["unresolved_ref"]),
                          "e": zscore(df["ellipsis_n"]), "d": -zscore(df["entity_density"])})
    return pd.Series(parts.mean(axis=1).to_numpy(), index=df.index, name="underspec_index")


def add_linguistic_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Compute every wave-1 linguistic feature from `question`, plus the frozen index."""
    d = df.copy()
    cm = [constraint_markers(q) for q in d["question"]]
    cdf = pd.DataFrame(cm, index=d.index)
    d = pd.concat([d, cdf.add_prefix("c_").rename(columns={
        "c_temporal": "constraint_temporal", "c_entity": "constraint_entity", "c_numeric": "constraint_numeric",
        "c_format": "constraint_format", "c_scope": "constraint_scope", "c_negation": "constraint_negation",
        "c_total": "constraint_total", "c_types": "constraint_types", "c_per_100": "constraint_per_100"})], axis=1)
    d["unresolved_ref"] = [unresolved_references(q) for q in d["question"]]
    d["ellipsis_n"] = [ellipsis(q) for q in d["question"]]
    d["entity_density"] = [entity_density(q, n) for q, n in zip(d["question"], d.get("n_chars", pd.Series("", index=d.index)))]
    d["underspec_index"] = underspec_index(d)
    d["n_sentences_w"] = [len(_sentences(q)) for q in d["question"]]
    return d


# --------------------------------------------------------------------------------- relevance: lexical + dense
def bm25_matrix(query: str, entries: list, mode: str = "full") -> np.ndarray:
    """Per-candidate BM25 with P001's frozen scorer. `full` = name words + description + parameter names."""
    q = toks(query)
    docs = [doc_tokens(entries, i, mode) for i in range(len(entries))]
    if not docs:
        return np.zeros(0)
    order = BM25().rank(q, docs)
    out = np.zeros(len(docs))
    scores = _bm25_scores(q, docs)
    for i in range(len(docs)):
        out[i] = scores[i]
    return out


def _bm25_scores(q_tokens, docs_tokens, k1=1.4, b=0.4) -> list:
    """The same Okapi formula as the frozen `BM25.rank`, exposed per document instead of as an ordering.

    Re-implemented only because the shipped class returns an ordering, not the scores, and re-ranking the ordering
    to recover a score would change nothing but invite a reviewer's doubt. A test asserts the two agree.
    """
    n = len(docs_tokens)
    if n == 0:
        return []
    df, tf, dl = Counter(), [], []
    for dd in docs_tokens:
        c = Counter(dd)
        tf.append(c)
        dl.append(len(dd))
        df.update(c.keys())
    avgdl = sum(dl) / n if n else 1.0
    out = []
    for i in range(n):
        s = 0.0
        # sorted(): the query terms are a set, and iterating a set of strings follows PYTHONHASHSEED. Float
        # addition is not associative, so the previous form changed the last bits of a score between two runs of
        # identical code - and 204 of the 7,476 dev rows measured here have the gold exactly tied with a rival,
        # where a last-bit difference flips hit@1. Sorting the terms costs nothing and makes the score fixed.
        for t in sorted(set(q_tokens)):
            f = tf[i].get(t, 0)
            if not f:
                continue
            idf = math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5))
            s += idf * f * (k1 + 1) / (f + k1 * (1 - b + b * dl[i] / avgdl))
        out.append(s)
    return out


def rank_from(scores) -> np.ndarray:
    """Descending ranks (1 = best); ties broken by candidate index, which is what the frozen ranker does."""
    s = list(scores)
    order = sorted(range(len(s)), key=lambda i: (-s[i], i))
    r = np.zeros(len(s), dtype=int)
    for k, i in enumerate(order, 1):
        r[i] = k
    return r


class VectorIndex:
    """sha-keyed view over an encoder matrix, so a caller asks for a text's vector and gets None if it has none.

    `missing` counts the lookups that failed. A design that silently substitutes zero vectors for unavailable
    embeddings would compute a similarity of 0 for them and read that as "semantically unrelated", which is a
    fabricated measurement; `cos` therefore returns NaN and every model using it drops the row and reports how many.
    """

    def __init__(self, keys: list, mat):
        self.pos = {k: i for i, k in enumerate(keys)}
        self.mat = mat
        self.missing = 0
        self.hits = 0

    def __bool__(self):
        return len(self.pos) > 0

    def vec_for(self, kind: str, key: str):
        i = self.pos.get(f"{kind}|{key}")
        if i is None:
            self.missing += 1
            return None
        self.hits += 1
        return self.mat[i]

    def cos(self, kind_a: str, a: str, kind_b: str, b: str) -> float:
        va, vb = self.vec_for(kind_a, a), self.vec_for(kind_b, b)
        return cosine(va, vb)

    def stats(self) -> dict:
        return {"vectors": len(self.pos), "lookup_hits": self.hits, "lookup_misses": self.missing}


def load_encoder_vectors(tag: str = "R2_prose", kind: str = None) -> object:
    """Read the locally-computed encoder embeddings written by encode_wave1_texts.py (EXP-0120).

    Returns an empty VectorIndex when the cache is absent, so a caller must report `not_measured` for that DV rather
    than substitute a lexical proxy for a distributional one.
    """
    kf = PROCES / f"wave1_encoder_{tag}_q_keys.jsonl"
    df_ = PROCES / f"wave1_encoder_{tag}_d_keys.jsonl"
    qf = PROCES / f"wave1_encoder_{tag}_q.npy"
    dm = PROCES / f"wave1_encoder_{tag}_d.npy"
    parts = []
    if kind in (None, "q") and kf.is_file() and qf.is_file():
        parts.append((["q|" + x for x in kf.read_text(encoding="utf-8").splitlines() if x.strip()],
                      np.load(qf)))
    if kind in (None, "d") and df_.is_file() and dm.is_file():
        parts.append((["d|" + x for x in df_.read_text(encoding="utf-8").splitlines() if x.strip()],
                      np.load(dm)))
    if not parts:
        return VectorIndex([], np.zeros((0, 0)))
    keys = [k for ks, _ in parts for k in ks]
    dim = max(m.shape[1] for _, m in parts if m.shape[0])
    mat = np.vstack([m if m.shape[0] else np.zeros((0, dim)) for _, m in parts])
    return VectorIndex(keys, mat)


def text_sha(s: str) -> str:
    return hashlib.sha256(str(s).encode("utf-8")).hexdigest()[:16]


def cosine(a, b) -> float:
    if a is None or b is None:
        return float("nan")
    na, nb = float(np.linalg.norm(a)), float(np.linalg.norm(b))
    if na == 0 or nb == 0:
        return float("nan")
    return float(np.dot(a, b) / (na * nb))


# ----------------------------------------------------------------------------------------- predicate/argument
VERB_LEMMA = {
    "send": ["send", "sends", "sending", "sent", "dispatch", "mail", "email"],
    "retrieve": ["retrieve", "get", "fetch", "pull", "load", "read", "obtain"],
    "store": ["store", "save", "write", "persist", "record", "log", "archive"],
    "transform": ["convert", "transform", "change", "modify", "update", "edit", "rewrite", "replace"],
    "create": ["create", "make", "generate", "build", "add", "insert", "author"],
    "delete": ["delete", "remove", "drop", "purge", "clear", "erase"],
    "search": ["search", "find", "query", "look", "locate", "lookup", "retrieve"],
    "summarize": ["summarize", "summarise", "condense", "abstract", "recap", "digest"],
    "translate": ["translate", "localize", "localise", "render"],
    "analyze": ["analyze", "analyse", "compute", "calculate", "evaluate", "measure", "count"],
    "compare": ["compare", "diff", "contrast", "match"],
    "validate": ["validate", "verify", "check", "test", "audit", "confirm"],
    "sort": ["sort", "order", "rank", "arrange"],
    "filter": ["filter", "select", "subset", "screen"],
    "execute": ["execute", "run", "invoke", "call", "trigger", "launch", "deploy"],
    "list": ["list", "enumerate", "catalog", "index"],
    "notify": ["notify", "alert", "message", "ping", "announce"],
    "schedule": ["schedule", "plan", "book", "reserve", "appoint"],
    "download": ["download", "fetch", "pull", "retrieve"],
    "upload": ["upload", "post", "push", "send"],
}
OBJECT_NOUNS = {
    "file": ["file", "files", "document", "docs", "folder", "directory", "path"],
    "message": ["message", "messages", "email", "mail", "note", "comment", "text"],
    "record": ["record", "records", "row", "rows", "entry", "entries", "database", "table"],
    "code": ["code", "function", "class", "module", "script", "program", "repo", "repository"],
    "media": ["image", "images", "photo", "picture", "video", "audio", "music", "song"],
    "person": ["user", "users", "person", "people", "contact", "customer", "employee", "team"],
    "time": ["date", "time", "schedule", "meeting", "event", "appointment", "calendar"],
    "location": ["location", "place", "city", "address", "coordinates", "map"],
    "money": ["price", "cost", "amount", "payment", "invoice", "balance", "budget"],
    "task": ["task", "job", "ticket", "issue", "project", "todo", "workitem"],
    "web": ["website", "page", "url", "link", "web", "site", "api", "endpoint"],
    "product": ["product", "item", "order", "stock", "inventory", "sku"],
    "weather": ["weather", "forecast", "temperature", "climate"],
    "travel": ["flight", "hotel", "trip", "train", "booking", "reservation"],
}


# --------------------------------------------------------------------------------- wave-3 text instruments (rule only)
# T113 and T120 are intervention designs, so the intervention has to be one checked-in rule that every script reads
# the same way - not a rewrite invented per run. Both arms are reversible by reading the table or the template.
WB = chr(92) + 'b'
WS_CLS = '[\s_]+'
NEG_MARK = re.compile(WB + '(not|no|cannot|ca\'t|unable|without|never|prohibit|unsupport|invalid|exclude)' + WB, re.I)

# canonical form <- the surface synonyms mapped onto it. Authored from the verb and object vocabulary that
# `VERB_LEMMA`/`OBJECT_NOUNS` already carry, so the map is the same lexicon the agreement features use and cannot
# smuggle in a notion of "same meaning" the rest of the programme does not recognise.
SYN_MAP = {
    "retrieve": ("fetch", "get", "obtain", "pull", "look_up", "search_for"),
    "summarize": ("sum_up", "condense", "abstract", "recap"),
    "transform": ("convert", "change", "modify", "alter", "reshape", "process"),
    "calculate": ("compute", "evaluate", "determine", "work_out"),
    "validate": ("check", "verify", "confirm", "assess"),
    "generate": ("produce", "create", "make", "emit", "output"),
    "store": ("save", "persist", "write", "record", "keep"),
    "delete": ("remove", "drop", "erase", "clear"),
    "list": ("enumerate", "show", "display", "print"),
    "file": ("document", "artifact", "asset"),
    "user": ("client", "customer", "account"),
    "message": ("text", "content", "communication"),
    "image": ("picture", "photo", "figure"),
    "database": ("db", "table", "index"),
    "error": ("failure", "fault", "problem"),
}


def apply_syn_map(text: str) -> str:
    """Replace every mapped synonym with its canonical form. Deterministic, case-folded, whole-word only."""
    t = str(text or "")
    for canon, syns in SYN_MAP.items():
        for w in (canon,) + tuple(s.replace("_", " ") for s in syns):
            pat = WB + re.escape(str(w).strip()).replace(' ', WS_CLS).replace('_', WS_CLS) + WB
            t = re.sub(pat, canon, t, flags=re.I)
        for s_ in syns:                                     # snake_case surfaces, as they appear in tool names
            t = re.sub(WB + re.escape(s_) + WB, canon, t, flags=re.I)
    return t


def usecase_frame(name: str, desc: str, params=None) -> str:
    """T113's use-case arm: the same content, framed as the task it serves. Rule-built, nothing invented.

    The template puts the operation first, names the parameters it needs, and keeps the released description as the
    tail, so the only change is *ordering and framing* plus the parameter names that the catalogue already carries.
    """
    p = " ".join(str(x) for x in (params or [])).strip()
    head = f"use {str(name or '').replace('-', ' ')}"
    if p:
        head += f" with {p}"
    return f"{head} for {str(desc or '').strip()}".strip()


def _norm_words(s) -> set:
    return {w for w in re.findall(r"[a-z]+", str(s or "").lower()) if len(w) > 1}


def predicate_argument(query: str, entry: dict) -> dict:
    """Frozen predicate-argument fit between one instruction and one candidate tool.

    predicate_fit = 1 if a verb lemma named in the instruction also appears in the tool's name/description/params,
    argument_fit = 1 over the object classes, overlap = both. Coverage flags say whether the lexicon could even
    speak to the text, because an effect that only exists where the lexicon fired is a coverage artefact.
    """
    qw, dw = _norm_words(query), _norm_words(" ".join([entry.get("name", ""), entry.get("desc", ""),
                                                       " ".join(entry.get("params", []) or [])]))
    qverbs = {lem for lem, forms in VERB_LEMMA.items() if qw & set(forms)}
    dverbs = {lem for lem, forms in VERB_LEMMA.items() if dw & set(forms)}
    qobjs = {c for c, forms in OBJECT_NOUNS.items() if qw & set(forms)}
    dobjs = {c for c, forms in OBJECT_NOUNS.items() if dw & set(forms)}
    return dict(predicate_fit=int(bool(qverbs & dverbs)), argument_fit=int(bool(qobjs & dobjs)),
                both_fit=int(bool(qverbs & dverbs) and bool(qobjs & dobjs)),
                q_pred_n=len(qverbs), d_pred_n=len(dverbs), q_arg_n=len(qobjs), d_arg_n=len(dobjs),
                pred_coverage=int(bool(qverbs)), arg_coverage=int(bool(qobjs)))


# ---------------------------------------------------------------------------------------- inference machinery
def cluster_boot(df: pd.DataFrame, by: str, fn, draws: int = 2000, seed: int = SEED):
    """Percentile CI of `fn(sub_frame)` under a cluster bootstrap over `by` (never over rows).

    Refuses a cluster column with fewer than 30 groups and says so in the returned count, because an interval built
    from a handful of clusters is not an interval.
    """
    if by not in df.columns:
        raise ValueError(f"cluster_boot needs the cluster column {by!r}")
    groups = [g.index.values for _, g in df.groupby(by)]
    if len(groups) < 30:
        return None, None, len(groups)
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(draws):
        take = np.concatenate([groups[i] for i in rng.choice(len(groups), len(groups), True)])
        try:
            v = fn(df.loc[take])
        except Exception:                                              # noqa: BLE001 - degenerate resamples happen
            continue
        if v is not None and np.isfinite(v):
            vals.append(float(v))
    if len(vals) < max(50, int(0.2 * draws)):
        return None, None, len(groups)
    a = np.array(vals)
    return round(float(np.percentile(a, 2.5)), 4), round(float(np.percentile(a, 97.5)), 4), len(groups)


def cluster_boot_ci_and_p(df: pd.DataFrame, by: str, fn, null: float = 0.0, draws: int = 2000, seed: int = SEED):
    """One cluster bootstrap, read two ways: the percentile interval *and* the bootstrap p at `null`.

    Calling `cluster_boot` and `boot_p` separately would resample the same statistic twice, doubling the cost and -
    worse - letting the interval and the p disagree about which draws exist. Same draws, same seed, both quantities.
    p is floored at 1/draws, so a resample set can never print p = 0.
    """
    groups = [g.index.values for _, g in df.groupby(by)]
    if len(groups) < 30:
        return {"error": f"fewer than 30 clusters in {by!r}", "clusters": len(groups)}
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(draws):
        take = np.concatenate([groups[i] for i in rng.choice(len(groups), len(groups), True)])
        try:
            v = fn(df.loc[take])
        except Exception:                                              # noqa: BLE001 - degenerate resamples happen
            continue
        if v is not None and np.isfinite(v):
            vals.append(float(v))
    if len(vals) < max(50, int(0.2 * draws)):
        return {"error": "too few finite draws", "clusters": len(groups), "draws_used": len(vals)}
    a = np.array(vals)
    p = 2 * min(float((a <= null).mean()), float((a >= null).mean()))
    return {"ci": [round(float(np.percentile(a, 2.5)), 4), round(float(np.percentile(a, 97.5)), 4)],
            "p": max(round(p, 6), 1.0 / draws), "clusters": len(groups), "draws_used": len(vals),
            "ci_kind": "cluster_bootstrap_percentile", "p_kind": "bootstrap_two_sided_tail",
            "point_of_bootstrap_mean": round(float(a.mean()), 4)}


def boot_p(df: pd.DataFrame, by: str, fn, null: float = 0.0, draws: int = 2000, seed: int = SEED):
    """A two-sided p-value taken from the cluster bootstrap distribution of the statistic itself.

    This exists because a bootstrap confidence interval does not come with a p-value, and inventing one (for example
    `0.001 if the interval excludes zero`) would be a fabricated number in a paper whose whole point is traceability.
    The reported value is `2 * min(P(boot <= null), P(boot >= null))`, floored at `1/draws` so a resample set can
    never print p = 0.
    """
    groups = [g.index.values for _, g in df.groupby(by)]
    if len(groups) < 30:
        return None, 0
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(draws):
        take = np.concatenate([groups[i] for i in rng.choice(len(groups), len(groups), True)])
        try:
            v = fn(df.loc[take])
        except Exception:                                          # noqa: BLE001
            continue
        if v is not None and np.isfinite(v):
            vals.append(float(v))
    if len(vals) < max(50, int(0.2 * draws)):
        return None, len(vals)
    a = np.array(vals)
    p = 2.0 * min(float((a <= null).mean()), float((a >= null).mean()))
    return round(max(p, 1.0 / draws), 6), len(vals)


def glm(df: pd.DataFrame, y: str, x: list, family, cluster: str = "query_id"):
    """Cluster-robust GLM fit; returns (params frame, deviance, n, converged) or None when the fit cannot be made."""
    import statsmodels.api as sm
    d = df[[y] + x + [cluster]].dropna()
    if len(d) == 0 and len(df) > 0:
        # An empty complete-case frame is not "too few rows to fit", it is a broken join upstream: a mis-aligned
        # reindex once turned every covariate into NaN and the fit reported a bare numpy reduction error.
        raise ValueError(f"glm({y}, {x}): all {len(df)} rows were dropped as incomplete. A column that is entirely "
                         f"NaN means the frame was assembled with a mis-aligned join, not that the data is thin.")
    if len(d) < 200 or d[y].nunique() < 2 and str(family.__class__.__name__).startswith("Binomial"):
        return None
    X = sm.add_constant(d[x].astype(float))
    try:
        res = sm.GLM(d[y].astype(float), X, family=family).fit(cov_type="cluster",
                                                              cov_kwds={"groups": d[cluster]})
    except Exception:                                                  # noqa: BLE001 - separation, singularity
        return None
    p = pd.DataFrame({"term": X.columns, "beta": np.asarray(res.params, dtype=float),
                      "se": np.asarray(res.bse, dtype=float), "p": np.asarray(res.pvalues, dtype=float)})
    return p, float(res.deviance), int(len(d)), bool(res.converged)


def glm_term(df, y, xs, family_name, cluster="query_id"):
    """Fit and flatten to a parameter frame with 95% cluster-robust intervals, or None if it cannot be fitted.

    Every wave script used to call `W.logit` and then index the returned tuple as a frame, which is how EXP-0123's
    first full run died. The interval is Wald (beta +/- 1.96 se) on the cluster-robust standard error, and the
    bootstrap route to an interval stays available through `cluster_boot`.
    """
    fam = {"binomial": logit, "poisson": poisson, "gaussian": ols}[family_name]
    fit = fam(df, y, xs, cluster=cluster)
    if fit is None:
        return None
    p, dev, n, ok = fit
    p = p.copy()
    p["ci_lo"] = p["beta"] - 1.959963985 * p["se"]
    p["ci_hi"] = p["beta"] + 1.959963985 * p["se"]
    p["dv"], p["n"], p["converged"], p["deviance"] = y, n, ok, dev
    return p


def poisson(df, y, x, cluster="query_id"):
    import statsmodels.api as sm
    return glm(df, y, x, sm.families.Poisson(), cluster)


def logit(df, y, x, cluster="query_id"):
    import statsmodels.api as sm
    return glm(df, y, x, sm.families.Binomial(), cluster)


def ols(df, y, x, cluster="query_id"):
    import statsmodels.api as sm
    return glm(df, y, x, sm.families.Gaussian(), cluster)


def partial_r2(y, fitted_full, fitted_reduced) -> float:
    """R^2(full) - R^2(reduced) from two fitted-value vectors, the nested-model gain the freeze asks for."""
    y = np.asarray(y, dtype=float)
    tss = float(((y - y.mean()) ** 2).sum())
    if tss == 0:
        return float("nan")
    def r2(f):
        f = np.asarray(f, dtype=float)
        return 1.0 - float(((y - f) ** 2).sum()) / tss
    return r2(fitted_full) - r2(fitted_reduced)


def holm(ps: dict) -> dict:
    """Holm step-down over a declared family; imported from P002's implementation so the two agree exactly."""
    spec = importlib.util.spec_from_file_location(
        "_p002c", ROOT / "02_shared_code" / "behavior_tagger" / "p002_cue_ablation_cases.py")
    m = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(m)
        return m.holm_correct(dict(ps))
    except Exception:                                                  # noqa: BLE001 - fall back, and say so
        items = sorted(ps.items(), key=lambda kv: kv[1])
        out, prev = {}, 0.0
        for i, (k, p) in enumerate(items):
            adj = min(1.0, max(prev, (len(items) - i) * p))
            out[k] = round(adj, 6)
            prev = adj
        return out


def vif(design: pd.DataFrame) -> dict:
    """Variance inflation factors for a numeric design matrix, computed by the definition (1/(1-R^2_j))."""
    out = {}
    X = design.astype(float).dropna()
    for c in X.columns:
        others = [o for o in X.columns if o != c]
        if not others:
            out[c] = 1.0
            continue
        import statsmodels.api as sm
        y = X[c]
        if float(y.std()) == 0:
            out[c] = float("nan")
            continue
        r = sm.OLS(y, sm.add_constant(X[others])).fit()
        out[c] = round(1.0 / max(1e-9, 1.0 - float(r.rsquared)), 3)
    return out


def rho_ci(df, by, x, y, draws=2000, seed=SEED):
    """Spearman rho with a cluster bootstrap interval - the freeze's kill gate is a correlation, not a p-value."""
    r = stats.spearmanr(df[x].astype(float), df[y].astype(float), nan_policy="omit")
    lo, hi, k = cluster_boot(df[[x, y, by]], by,
                             lambda d: float(stats.spearmanr(d[x].astype(float), d[y].astype(float),
                                                             nan_policy="omit").statistic), draws, seed)
    return dict(rho=round(float(r.statistic), 4), p=float(r.pvalue), ci=[lo, hi], clusters=k)


def wilson(k: float, n: float, z: float = 1.959963985) -> list:
    if n <= 0:
        return [float("nan"), float("nan")]
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    s = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return [round((c - s) / d, 4), round((c + s) / d, 4)]


def verdict(beta, lo, hi, p_holm, support_floor, direction=1.0) -> str:
    """The frozen three-way rule, applied identically in every wave package.

    support  : |beta| >= floor AND the cluster CI excludes 0 AND Holm-corrected p < 0.05, in the predicted direction
    partial  : the CI excludes 0 in the predicted direction but the magnitude is below the floor (or p_holm >= .05)
    null     : the CI includes 0 - reported as null, never as "no evidence" dressed up as a finding
    """
    if beta is None or lo is None or not np.isfinite(beta):
        return "not_testable"
    signed = beta * direction
    ci_excludes = (lo > 0) or (hi is not None and hi < 0)
    if ci_excludes and signed > 0 and abs(beta) >= support_floor and p_holm is not None and p_holm < 0.05:
        return "supported"
    if ci_excludes and signed > 0:
        return "partial"
    if ci_excludes and signed < 0:
        return "opposite"
    return "null"


POS_RX = re.compile(r"(positively|raises|increase|larger|higher|more|falls|reduces|lower|fewer|stronger|"
                    r"better|concentrated|absent|negatively|worse|shorter|later|slower)", re.I)


def attach_directions(models: list, hypotheses: list) -> list:
    """Put the predicted side on every model row, from the design's own frozen hypothesis sentence.

    `verdict` is a four-way word only meaningful against a prediction: `supported` needs the interval on the
    predicted side of zero, `opposite` is what an interval on the other side is called. The prediction lived in
    `protocol_freeze.md` and the claims matrix but not in the artefact, so a reader holding only the artefact could
    check a verdict's magnitude and p-value but not its direction. This writes it from the hypothesis text the wave
    already froze - positively-oriented verbs as `predicted_positive`, the rest as `predicted_negative`, and
    `direction_free` where the sentence asks only that two things differ - so the rule can be re-applied without
    opening the package.
    """
    neg = ("reduces", "lower", "fewer", "falls", "absent", "negatively", "worse", "shorter", "later", "slower")
    free = ("differ", "changes", "is not the same", "whether")
    by_h = {}
    for h in hypotheses or []:
        m = re.match(r"\s*(H\d)", str(h))
        if not m:
            continue
        low = str(h).lower()
        side = "direction_free" if any(k in low for k in free) and not any(k in low for k in neg)             else ("predicted_negative" if any(k in low for k in neg) else "predicted_positive")
        by_h[m.group(1)] = side
    for r in models or []:
        if isinstance(r, dict):
            h = str(r.get("hypothesis") or "")
            if h in by_h and not " ".join(str(r.get(k) or "") for k in DIRECTION_KEYS).strip():
                r["verdict_direction"] = by_h[h]
    return models or []


def magnitude_verdict(value, lo, hi, p_holm, floor, side="abs") -> str:
    """The frozen three-way rule for a design whose hypothesis does not name a direction.

    `verdict` above serves a predicted sign; several designs are written as "changes", "differs" or "beats", where
    the interval's *exclusion* of zero is the evidence and the side only says whether the predicted direction
    (if any) held. Three things this makes impossible, each of which a hand-rolled expression in an early wave did:

    * reading a missing bound as zero, which turned a row whose interval was never computed into `null` - a claim
      about the data rather than about the fit, so such a row is reported `not_estimable_*` instead;
    * calling an interval that excludes zero `null` because it sits on the unexpected side;
    * letting a `supported` label stand when the design's own threshold sentence names no floor for this quantity
      (a proportion difference under a rule frozen for a coefficient and a rank shift) - that row is `partial`.

    `floor` may be None to mean "the freeze names no floor for this quantity"; `side` is "abs", "pos" or "neg".
    """
    if lo is None or hi is None:
        return "not_estimable_interval_not_reported"
    try:
        lo, hi = float(lo), float(hi)
    except (TypeError, ValueError):
        return "not_estimable_interval_not_a_number"
    if not (math.isfinite(lo) and math.isfinite(hi)):
        return "not_estimable_interval_not_a_number"
    if lo <= 0.0 <= hi:
        return "null"
    held = (side == "abs" or (side == "pos" and lo > 0.0) or (side == "neg" and hi < 0.0))
    if not held:
        return "opposite"
    if floor is None or value is None:
        return "partial"
    return "supported" if (abs(float(value)) >= float(floor)
                           and p_holm is not None and float(p_holm) < 0.05) else "partial"


# --------------------------------------------------------------------------------------------- plotting utils
def strip_pdf_metadata(pdf_path: pathlib.Path) -> None:
    """Remove CreationDate/Producer so a rebuilt figure is byte-comparable across rebuild rounds."""
    t = pdf_path.read_bytes()
    out = re.sub(rb"/(CreationDate|ModDate|Producer|Author)\s*\([^)]*\)", b"", t)
    pdf_path.write_bytes(out)


def new_fig(figsize=(6.8, 4.2)):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"svg.hashsalt": "aib-wave", "pdf.fonttype": 42, "font.size": 9})
    return plt, matplotlib


def strip_svg_timestamp(svg_path: pathlib.Path) -> None:
    """Remove the embedded `<dc:date>` from a generated SVG.

    matplotlib stamps the SVG with the wall-clock of the render even when `svg.hashsalt` is pinned, so a rebuild round
    reported every figure as changed while the drawing was byte-for-byte the same apart from that one line. Stripping
    it is the fix; excluding SVGs from the comparison would have hidden a real (if trivial) nondeterminism instead of
    removing it.
    """
    svg_path.write_bytes(re.sub(rb"<dc:date>[^<]*</dc:date>\s*", b"", svg_path.read_bytes()))


def save_fig(fig, outdir: pathlib.Path, name: str, caption: str) -> dict:
    outdir.mkdir(parents=True, exist_ok=True)
    pdf, svg = outdir / name, outdir / (name.replace(".pdf", ".svg"))
    fig.savefig(pdf, format="pdf")
    fig.savefig(svg, format="svg")
    strip_pdf_metadata(pdf)
    strip_svg_timestamp(svg)
    cap = outdir / name.replace(".pdf", ".caption.txt")
    cap.write_text(caption.strip() + "\n", encoding="utf-8")
    import matplotlib.pyplot as plt
    plt.close(fig)
    return {"pdf": pdf.name, "svg": svg.name, "caption": cap.name,
            "bytes": [pdf.stat().st_size, svg.stat().st_size]}


# ----------------------------------------------------------------------------------- provenance / cost table
def run_cost_row(exp_id: str, started: float, rows: int, cols: int, note: str = "") -> dict:
    return {"exp_id": exp_id, "started_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(started)),
            "wallclock_sec": round(time.time() - started, 1), "rows_in": rows, "cols_in": cols,
            "python": sys.version.split()[0], "note": note}


def environment_record() -> dict:
    import platform
    pk = {}
    for m in ("numpy", "pandas", "scipy", "sklearn", "statsmodels", "matplotlib", "pyarrow"):
        try:
            pk[m] = __import__(m).__version__
        except Exception:                                              # noqa: BLE001
            pk[m] = "absent"
    return {"system": platform.system(), "release": platform.release(), "machine": platform.machine(),
            "python": sys.version.split()[0], "executable": sys.executable,
            "cpus_logical": os.cpu_count(), "packages": pk,
            "llm_api_available_by_policy": False,
            "network_used_during_analysis": "none (all datasets are on local disk)",
            "cluster": "query_id (cfg|uuid) for every interval in this wave"}
