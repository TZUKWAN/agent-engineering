"""Shared machinery for the round-2 verification pass: what a package's numbers are allowed to be.

The first audit round checked that a package *has* its 20 deliverables and that rebuilding them is deterministic.
It never asked whether a figure printed in `paper.md` is a value some run produced. This module is the bookkeeping
for that question: it resolves which artefact generation a package is entitled to cite (the newest per experiment id
minus everything the supersession ledger retired), collects every number those artefacts carry, and provides the
tolerances a prose sentence legitimately needs (it rounds, it quotes a rate as a percentage, it subtracts two
measured values and calls the result a gap).

A number is **supported** when, at the precision the sentence itself used, it equals an artefact or shipped-table
value, or 100x such a value, or a difference/ratio of two of them. Everything else is reported, not forgiven:
this is a detector whose residual is read by a person, and an unsupportable number is the classic way a
measurement claim drifts away from the measurement.
"""
from __future__ import annotations

import csv
import fnmatch
import glob
import io
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
LEDGER = ROOT / "results_raw" / "SUPERSEDED_ARTIFACTS.json"
NUM = re.compile(r"(?<![\w.])\d[\d,]*(?:\.\d+)?(?:[eE][-+]?\d+)?(?![\w])")
FROZEN = set()
SMALL_STRUCTURAL = 30           # channels, hypotheses, waves, quartiles: counts a sentence states, not measures


def superseded() -> set:
    global _SUP
    if _SUP is None:
        _SUP = {e["file"] for e in json.loads(LEDGER.read_text(encoding="utf-8")).get("superseded", [])} \
            if LEDGER.is_file() else set()
    return _SUP


_SUP = None
_ROOT_KEPT = None


def kept_artefacts(pkg: pathlib.Path) -> dict:
    """{exp_id: path} for the newest generation of each experiment this package may cite."""
    sup = superseded()
    out = {}
    for f in sorted((pkg / "results_raw").glob("*")):
        m = re.match(r"(EXP\d{4})(?![A-Za-z])", f.name)      # `EXP0008f_` is a different run from `EXP0008_`
        if not m or f.name in sup:
            continue
        exp = "EXP-" + m.group(1)[3:]
        prev = out.get(exp)
        if prev is None or f.stat().st_mtime >= prev.stat().st_mtime:
            out[exp] = f
    return out


def root_kept() -> dict:
    """{exp_id: path} for the newest non-superseded artefact of every experiment in the programme."""
    global _ROOT_KEPT
    if _ROOT_KEPT is not None:
        return _ROOT_KEPT
    sup = superseded()
    out = {}
    for f in sorted((ROOT / "results_raw").glob("EXP*")):
        m = re.match(r"(EXP\d{4})(?![A-Za-z])", f.name)      # a letter suffix is its own experiment id
        if not m or f.name in sup:
            continue
        exp = "EXP-" + m.group(1)[3:]
        prev = out.get(exp)
        if prev is None or f.stat().st_mtime >= prev.stat().st_mtime:
            out[exp] = f
    _ROOT_KEPT = out
    return out


def run_declared_artefacts(exp: str) -> list:
    """Every file the register declares for this run that exists and the ledger has not retired.

    The declaration, not "the newest file matching a pattern", is the authority here: a run that wrote one record per
    scope declares each record it wrote, and a document quoting a figure from one of those scopes is quoting what the
    run produced. Wildcard families in the cell (a CSV per release, say) contribute all of their matches, because the
    row says the run wrote that whole family.
    """
    row = registry_rows().get(exp) or {}
    sup = superseded()
    out = []
    for t in re.split(r"[;,]", str(row.get("outputs") or "")):
        t = t.strip().replace(chr(92), "/")
        if not t or "(" in t or "console" in t.lower() or t.startswith("papers/"):
            continue
        if "{" in t and "}" in t:
            head, rest = t.split("{", 1)
            mid, tail = rest.split("}", 1)
            for alt in mid.split(","):
                out += [p for p in run_declared_artefacts_matching(head + alt + tail, sup)]
            continue
        out += run_declared_artefacts_matching(t, sup)
    return out


def run_declared_artefacts_matching(token: str, sup: set) -> list:
    pat = str(ROOT / token)
    hits = sorted(glob.glob(pat)) if ("*" in token or "?" in token) else ([pat] if pathlib.Path(pat).is_file() else [])
    return [pathlib.Path(h) for h in hits if pathlib.Path(h).is_file() and pathlib.Path(h).name not in sup]


def kept_artefact_list(pkg: pathlib.Path) -> dict:
    """{exp_id: [path, ...]} of what this package may quote: its held generations plus the programme's, as declared."""
    out = {}
    sup = superseded()
    for exp, f in kept_artefacts(pkg).items():
        out[exp] = [f]
    for exp in cited_exps(pkg):
        if exp in out:
            continue
        p = root_kept().get(exp)
        if p:
            out[exp] = [p]
    for exp, files in list(out.items()):
        declared = run_declared_artefacts(exp)
        if declared:
            # keep the held copy when the package ships one, so the bytes read are the ones the reader sees
            merged = list(files) + [d for d in declared if not any(d.name == f.name for f in files)]
            out[exp] = [f for f in merged if f.name not in sup] or files
    return out


CITE = re.compile(r"EXP-0\d{3}")
# the dated records in a package: each prints what was measured on the day it was written
HISTORY_DOCS = ("protocol_freeze.md",)
RETIRED_SCAN_CAP = 6


_RETIRED_BY_EXP = None


def retired_by_experiment() -> dict:
    """{EXPnnnn: [path, ...] newest first} for the retired JSON records in the programme's results folder.

    Built once per process: scanning with a glob per cited run would walk a folder of twenty thousand files some two
    thousand times across the estate, which is minutes of nothing but directory reads.
    """
    global _RETIRED_BY_EXP
    if _RETIRED_BY_EXP is not None:
        return _RETIRED_BY_EXP
    sup = superseded()
    out = {}
    for f in sorted((ROOT / "results_raw").glob("EXP*.json"), key=lambda p: p.name, reverse=True):
        m = re.match(r"(EXP\d{4})(?![A-Za-z])", f.name)
        if m and f.name in sup:
            out.setdefault(m.group(1), []).append(f)
    _RETIRED_BY_EXP = out
    return out


def historic_numbers(pkg: pathlib.Path) -> set:
    """Numbers carried by the *retired* generations of the runs this package cites, newest retired first.

    `protocol_freeze.md` is a dated record. It prints what the census measured on the day the design was frozen, and a
    later re-run of the same census can print a different number under the same key - wave 4's premise census read
    `sufficiency_marker_turn_share` at 0.0464 in the generations of 2026-09-24 morning and 0.0444 in the kept one. A
    freeze must not be rewritten after measurement, because that is precisely what pre-registering forbids, and the
    design module has already been refreshed to the kept value by EXP-0163. So a freeze document is scored against the
    generations it was actually written from, and every other page is scored against the kept artefacts only.

    Only JSON records are read, and only the newest few per run, so the exemption cannot quietly become "the whole
    results folder".
    """
    sup = superseded()
    if not sup:
        return set()
    idx = retired_by_experiment()
    out = set()
    for exp in sorted(cited_exps(pkg)):
        for f in idx.get(exp.replace("-", ""), [])[:RETIRED_SCAN_CAP]:
            out |= file_numbers(f)
    return out


def cited_exps(pkg: pathlib.Path) -> set:
    """Every experiment id this package's own documents, tables or register point at."""
    ids = set()
    for f in list(pkg.glob("*.md")) + list(pkg.glob("*.csv")) + list(pkg.glob("tables/*.csv")) \
            + list(pkg.glob("scripts/*.py")):
        if f.is_file():
            ids |= set(CITE.findall(f.read_text(encoding="utf-8", errors="replace")))
    return ids


def declared_runs(pkg: pathlib.Path) -> set:
    """The experiments this package declares as its own provenance.

    `table7_experiment_provenance.csv` and the package copy of the register are the package's statement of which
    runs it is built from, so those - not every EXP id mentioned in prose - are what has to be openable inside it.
    """
    ids = set()
    for f in [pkg / "tables" / "table7_experiment_provenance.csv", pkg / "experiment_registry.csv"]:
        if f.is_file():
            rows = read_any(f) or []
            for r in rows:
                for v in (r or {}).values():
                    ids |= set(re.findall(r"EXP-0\d{3}", str(v)))
    return ids


_REG_ROWS = None


def registry_rows() -> dict:
    """{exp_id: row} from the master register - the authority on what each run wrote and where."""
    global _REG_ROWS
    if _REG_ROWS is None:
        f = ROOT / "00_program_registry" / "experiment_registry.csv"
        _REG_ROWS = {r["exp_id"]: r for r in read_any(f) or []} if f.is_file() else {}
    return _REG_ROWS


HOLDABLE = ("results_raw/", "results_processed/", "logs/", "configs/")


def _pattern_of(tok: str, pkg: pathlib.Path):
    """(path relative to this package, programme-relative pattern) for one declared output cell.

    A run that wrote one record into every package addresses them through a wildcard folder and/or a digit
    placeholder standing for the package's own number - `papers/*/environment/clean_room_run_P00x.json` is how
    EXP-0079's clean-room records are declared, and P002's own copy is on disk as `clean_room_run_P002.json`. Each
    `x` becomes one `?`, so a translated placeholder keeps the width of a real package id and cannot match a
    neighbouring package by accident.
    """
    pat = re.sub(r"P[0-9]*x[0-9x]*\b", lambda m: "P" + "?" * (len(m.group(0)) - 1), tok)
    return re.sub(r"^papers/(\*|" + re.escape(pkg.name) + r")/", "", pat), pat


def missing_copies(pkg: pathlib.Path) -> list:
    """Declared runs a reader cannot open inside this package.

    What counts as openable is decided by the paths the register declares for the run, not by a filename shape.
    Three real cases broke a name-prefix rule: EXP-0002 and EXP-0003 wrote `P000_gold_tool_grounding_*.json`, two
    runs sharing one stem; EXP-0084's row re-uses EXP-0083's CSVs, which is what the row was written to say; and
    EXP-0079 wrote a clean-room record into each package's own `environment/`, addressed through a placeholder
    (`papers/*/environment/clean_room_run_P00x.json`). All three files were in the folder and all three were
    reported missing.

    A run whose declaration holds nothing a package could carry - a programme register, a series-level review
    document, another paper's literature matrix, or no file at all because it was a console probe - is not a
    citation a reader of this package can be missing, so it is not reported.
    """
    names = {f.name for f in pkg.rglob("*") if f.is_file()}
    rel = {str(f.relative_to(pkg)).replace(chr(92), "/") for f in pkg.rglob("*") if f.is_file()}
    sup = superseded()
    reg = registry_rows()
    out = []
    for e in declared_runs(pkg):
        toks = [t.strip().replace(chr(92), "/") for t in ((reg.get(e) or {}).get("outputs") or "").split(";")
                if t.strip()]
        if not any(t.startswith(HOLDABLE) or t.startswith("papers/") for t in toks):
            continue                                      # the run wrote nothing this folder could hold
        held = False
        for t in toks:
            base = t.split("/")[-1]
            if base in sup:
                continue                                  # a retired generation is not the run's current artefact
            tail, pat = _pattern_of(t, pkg)
            if "*" in pat or "?" in pat:
                held = held or any(fnmatch.fnmatch(r, tail) or fnmatch.fnmatch(f"papers/{pkg.name}/{r}", pat)
                                   for r in rel)
            else:
                held = held or (t in {f"papers/{pkg.name}/{r}" for r in rel}) or (base in names and
                                                                                 t.startswith(HOLDABLE))
        if not held:
            out.append(e)
    return sorted(out)


def walk_numbers(o, bag: set) -> None:
    """Every number anywhere inside a decoded artefact; numeric strings included, booleans excluded."""
    if isinstance(o, bool):
        return
    if isinstance(o, (int, float)):
        if not isinstance(o, float) or (o == o and abs(o) != float("inf")):
            bag.add(float(o))
    elif isinstance(o, str):
        for t in NUM.findall(o):
            try:
                bag.add(float(t.replace(",", "")))
            except ValueError:
                pass
    elif isinstance(o, dict):
        for v in o.values():
            walk_numbers(v, bag)
    elif isinstance(o, (list, tuple)):
        for v in o:
            walk_numbers(v, bag)


_READS = {}


def read_any(p: pathlib.Path):
    """Parse an artefact once per (path, mtime) - several packages cite the same shared matrix."""
    key = (str(p), p.stat().st_mtime if p.exists() else None)
    if key not in _READS:
        if p.suffix == ".json":
            try:
                _READS[key] = json.loads(p.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                _READS[key] = None
        elif p.suffix == ".csv":
            _READS[key] = list(csv.DictReader(io.StringIO(p.read_text(encoding="utf-8-sig", errors="replace"))))
        else:
            _READS[key] = None
    return _READS[key]


_FILENUMS = {}


def file_numbers(p: pathlib.Path) -> set:
    key = (str(p), p.stat().st_mtime)
    if key not in _FILENUMS:
        vals = set()
        walk_numbers(read_any(p), vals)
        _FILENUMS[key] = vals
    return _FILENUMS[key]


def row_numbers(p: pathlib.Path) -> list:
    """The numeric cells of each row of one table - the parts a prose sentence adds up for a denominator."""
    out = []
    for r in read_any(p) or []:
        nums = []
        for v in (r or {}).values():
            try:
                nums.append(float(str(v).replace(",", "").rstrip("%")))
            except (TypeError, ValueError):
                continue
        if nums:
            out.append(nums)
    return out


def column_totals(p: pathlib.Path) -> list:
    """Each column of a shipped table added over its own rows, as `(column, total, rows_used)`.

    A sentence in a paper often prints the estate-wide total of something a table lists release by release - P005's
    "15,789,996 rows counted from footers" is the `exact_rows_from_footers` column of its own inventory table. The
    parts are shipped, so the number is carried by the package; only the addition was left to the reader. Counts add
    up to a defensible total, so a column with any fractional cell is not offered, and a one-row column is just the
    cell itself.
    """
    rows = read_any(p) or []
    if len(rows) < 2:
        return []
    out = []
    for c in (rows[0] or {}):
        vals, ok = [], True
        for r in rows:
            s = str((r or {}).get(c) or "").replace(",", "").rstrip("%").strip()
            if s in ("", "None", "nan", "NaN", "not_recorded", "n/a"):
                continue
            try:
                v = float(s)
            except ValueError:
                ok = False
                break
            if not float(v).is_integer():
                ok = False
                break
            vals.append(v)
        if ok and len(vals) >= 2 and abs(sum(vals)) <= 1e12:
            out.append((str(c), float(sum(vals)), len(vals)))
    return out


def block_numbers(o, depth: int = 4) -> list:
    """(value, field name) for the numbers a result block states, up to four levels down.

    A corpus block reads `{turns: 3566324, trajectories: 240000, gains_first_minus: {zero_order: {mean: 0.3091}}}`, so
    the counts and the statistic they rescale sit two and three levels apart. The field name travels with the value
    because the rules below fire only between a *named* count and a *named* statistic, which is what keeps this a
    reading of the block instead of a search through everything it holds.
    """
    out = []
    stack = [(o, 0)]
    while stack:
        cur, d = stack.pop()
        if isinstance(cur, dict):
            for k, v in cur.items():
                if isinstance(v, (int, float)) and not isinstance(v, bool) and 0 < abs(float(v)) <= 1e12:
                    out.append((float(v), str(k)))
                elif d < depth:
                    stack.append((v, d + 1))
        elif isinstance(cur, list) and d < depth:
            for v in cur:
                stack.append((v, d + 1))
    return out


SIBOPS_CAP = 3_000_000


COUNT_FIELDS = re.compile(r"(^|_)(n|count|turns?|trajector(?:y|ies)|rows|instances|prompts|calls|samples|queries"
                          r"|items|rollouts|conversations|documents?|docs|releases?|shards?)$|_turns$|_rows$")
STAT_FIELDS = re.compile(r"(^|_)(mean|gain|beta|coef|coefficient|delta|diff|d|rho|auc|loss|ll|rate|share|value"
                         r"|effect|proportion|accuracy|error|sd|se)(_|$)")


def stated_precision(v) -> float:
    """Half a unit in the last digit the record writes - the rounding error that value carries.

    A record that writes `240000` states an exact count, not a real rounded to the nearest integer, so integral values
    carry no uncertainty; treating them as ±0.5 turned every count ratio into a band wide enough to swallow unrelated
    figures (the matcher accepted 55 % of them on P005 with that rule).
    """
    f = float(v)
    if f.is_integer():
        return 0.0
    s = repr(f)
    if "e" in s or "E" in s:
        return 0.5e-6
    return 0.5 * 10 ** -min(6, len(s.split(".")[1])) if "." in s else 0.0


def sibling_ops(path) -> dict:
    """{figure: rounding uncertainty} for the readings a run record states about itself.

    A package's reporting layer converts units with the counts written in the same block - `turns / trajectories` turns
    a bits-per-turn gain into a bits-per-trajectory one - and the rounded result, not the conversion, is what the prose
    then prints. A reader cannot re-derive that from the page, so the check has to be able to, and the rule is kept as
    narrow as the reading actually is:

    * the two terms must sit in one block of one record (never two unrelated records);
    * the divisor pair must be named counts (`turns`, `trajectories`, `n_rows`, ...) and the thing converted must be a
      named statistic (`mean`, `gain`, `beta`, `rate`, ...), or the record must state the ratio itself
      (`mean_turns_per_trajectory`);
    * a difference is offered only between two named statistics of the same order as the difference, so a huge count
      beside a tiny one cannot "explain" any small figure;
    * each candidate's own rounding error is recorded (`stated_precision`) but deliberately **not** applied when
      matching: propagating it is mathematically right and leaves the check with no power, because a statistic printed
      to two decimals times a ratio of fifteen has an honest band of ±0.08, and with a few thousand such bands the
      matcher accepted 53 % of unrelated figures on P005. Figures are matched at the precision the prose prints, so a
      conversion that only agrees inside its inputs' own rounding stays a finding - P002's pilot prints 1.367 where
      0.0916 × 14.918 = 1.3663.

    Blocks with more than 120 numbers are row dumps rather than result statements and are skipped.
    """
    try:
        d = json.loads(pathlib.Path(path).read_text(encoding="utf-8", errors="replace"))
    except (OSError, ValueError, UnicodeDecodeError):
        return {}
    out = {}

    def add(v, unc):
        if len(out) > SIBOPS_CAP:
            return
        prev = out.get(v)
        if prev is None or unc < prev:
            out[v] = unc

    def walk(o):
        if len(out) > SIBOPS_CAP:
            return
        if isinstance(o, dict):
            raw = block_numbers(o)
            items = [(v, k, stated_precision(v)) for v, k in raw]
            if 2 <= len(items) <= 120:
                counts = [(v, k) for v, k, _u in items
                          if float(v).is_integer() and abs(v) >= 2 and COUNT_FIELDS.search(k)]
                stats = [(v, u) for v, k, u in items if STAT_FIELDS.search(k)]
                ratios = [(v, u) for v, k, u in items if "_per_" in k and not float(v).is_integer()]
                for a, _ka in counts:
                    for b, _kb in counts:
                        if a != b:
                            ratios.append((abs(a / b), 0.0))
                for r, ru in ratios:
                    add(round(r, 9), ru)
                    for f, fu in stats:
                        add(round(abs(f) * r, 9), abs(r) * fu + abs(f) * ru)
                for a, au in stats:
                    for b, bu in stats:
                        if a != b and max(abs(a), abs(b)) <= 10 * max(abs(a - b), 1.0):
                            add(round(abs(abs(a) - abs(b)), 9), au + bu)
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(d)
    return out


def value_pool(pkg: pathlib.Path) -> tuple:
    """(values from the artefacts this package may cite, values from its shipped tables, provenance, row groups,
    column totals, the arithmetic available inside each run record)."""
    art, tbl, src = set(), set(), {}
    groups, colsums, sibs = [], {}, {}
    pool_files = kept_artefact_list(pkg)
    for exp, files in pool_files.items():
        for f in files:
            vals = file_numbers(f)
            art |= vals
            if f.suffix == ".json":
                sibs.update(sibling_ops(f))
            for v in vals:
                src.setdefault(v, exp)
    # the estate's own measurement records a package may quote but does not copy: the dataset audit manifests
    # (row and shard counts), and the package's literature tables (numbers quoted from a cited paper).
    extra = sorted((ROOT / "01_datasets" / "manifests").glob("*.audit.json")) +         [f for f in (pkg / "literature_matrix.csv", pkg / "lit_search_log.csv",
                     pkg / "novelty_grading.md") if f.is_file()]
    for f in extra:
        vals = file_numbers(f)
        art |= vals
        if f.suffix == ".json":
            sibs.update(sibling_ops(f))
        for v in vals:
            src.setdefault(v, f"estate:{f.name}")
    for f in sorted((pkg / "results_processed").glob("*.csv")) + sorted((pkg / "tables").glob("*.csv")):
        vals = file_numbers(f)
        groups += row_numbers(f)
        for c, total, k in column_totals(f):
            colsums.setdefault(round(total, 6), (f"{f.name}.{c}", k))
        tbl |= vals
        for v in vals:
            src.setdefault(v, f"table:{f.name}")
    return art, tbl, src, groups, colsums, sibs


def _tol(dp: int) -> float:
    return 0.5 * 10 ** (-dp) if dp > 0 else 0.5


SENT_NUM = re.compile(r"(?<![\d.,])[-−+]?\d[\d,]*(?:\.\d+)?(?![\d.])")


class Pools:
    """Sorted views of a package's supported values, so a match test is a binary search not a scan."""

    def __init__(self, art: set, tables: set, row_groups: list = None, colsums: dict = None,
                 sibops: set = None):
        self.art, self.tables = art, tables
        self.row_groups = row_groups or []
        self.colsums = colsums or {}
        self.both = art | tables
        self.s = sorted(self.both)
        self.p = sorted(a * 100.0 for a in self.both)
        self.keys = {round(a, 6) for a in self.both} | {round(a * 100.0, 6) for a in self.both}
        self._sorted = sorted(self.both)
        self.s_art = sorted(art)
        self.p_art = sorted(a * 100.0 for a in art)
        self.near = sorted((a for a in self.both if a), key=lambda x: -abs(x))[:600]
        # A derived figure is only warranted when its terms are cells of one and the same row: P001's 0.4919 is
        # 605 / (605 + 625), read off one contingency row, and a relative selection ratio is two cells of one row.
        # The first version of this rule tested `v * d` against the pool for every sum or difference of any two cells
        # of any row - 231 to 1.1M candidate denominators per package - and accepted 1,500 of 1,500 random
        # four-decimal numbers, which made the provenance detector's zero findings mean nothing. Enumerating inside a
        # row is both what a reader actually does and small enough that an accidental hit is not a certainty.
        self.rowops = set()
        for grp in (row_groups or []):
            nums = [abs(float(x)) for x in grp
                    if isinstance(x, (int, float)) and not isinstance(x, bool) and 0 < abs(float(x)) <= 1e9]
            total = sum(nums)
            for a in nums:
                if total:
                    self.rowops.add(round(a / total, 9))
                    self.rowops.add(round(1 - a / total, 9))
                for b in nums:
                    if b and a != b:
                        self.rowops.add(round(a / b, 9))
                        self.rowops.add(round(a * b, 9))
        self.rowop_list = sorted(self.rowops)
        # Sibling arithmetic inside a run record: a package's reporting layer turns a per-turn quantity into a
        # per-trajectory one by dividing the two counts the same result block prints (`turns / trajectories`), and the
        # rounded quotient then appears in the prose - P002's 14.86 turns/trajectory, and the 4.593 built from it, are
        # of that kind. Allowed, but only between two numbers sitting in one dict of one kept record: a handful of
        # pairs per block, not a search of the pool. The set is computed while the records are read (see
        # `sibling_ops`) and passed in, because the same records are read once per package.
        self.sibops = dict(sibops or {})
        self.sib_list = sorted(self.sibops)

    def with_history(self, extra: set) -> "Pools":
        """The same pool, widened by numbers from generations this run has retired.

        Used only for a dated record (`protocol_freeze.md`). Row-derived arithmetic is deliberately not re-enumerated
        here: what the exemption buys is the right to quote a figure that an earlier generation of the cited run
        measured, not a second set of ratios to match against.
        """
        return Pools(self.art | set(extra), self.tables, [], self.colsums)

    def sentence_arithmetic(self, v: float, dp: int, ctx: str) -> str:
        """A figure a reader computes from two numbers the same passage prints.

        "B2-B1 = 4.593 (0.3091 bits/turn x 14.86 turns/traj)" and "20,000 rows came from 317 `instance_id` values
        (~63.1 rollouts per instance)" are arithmetic stated in words: the estate's reporting layer multiplies a
        per-turn quantity by a per-run quantity, and the product appears in no table row. Each term must itself be a
        value the package measured, so the rule is a reading of the passage rather than a search of the pool - and
        `matcher_specificity()` measures the cost of that reading on every package, because a paragraph offers many
        pairs and an uncontrolled rule would drift back into accepting anything.
        """
        if not ctx:
            return ""
        terms = []
        for tok in SENT_NUM.findall(ctx):
            t = tok.replace(",", "").lstrip("+").replace("−", "-")
            try:
                f = float(t)
            except ValueError:
                continue
            if abs(f) < 1e-9:
                continue
            # a term quoted in prose is quoted rounded, so it counts as a measured value when some value the package
            # holds rounds to it at the precision printed - demanding an exact six-decimal identity would reject the
            # "0.3091 bits/turn" the artefact stores as 0.309148 and the reader faithfully copies
            dpt = len(t.split(".")[1]) if "." in t else 0
            if any(Pools._hit(seq, f, _tol(dpt)) for seq in (self._sorted, self.p)):
                terms.append(f)
        if len(terms) < 2:
            return ""
        tol = _tol(dp)
        want = abs(v)
        cands = (("product", lambda a, b: abs(a * b)), ("quotient", lambda a, b: abs(a / b) if b else 0.0),
                 ("difference", lambda a, b: abs(abs(a) - abs(b))))
        if "%" in ctx:                    # a figure expressed as a percentage: "52 of 62 (83.9 %)"
            cands += (("percent", lambda a, b: 100.0 * abs(a / b) if b else 0.0),)
        for a in terms:
            for b in terms:
                if a == b:
                    continue
                for lbl, f in cands:
                    cand = f(a, b)
                    if cand and abs(cand - want) <= tol:
                        return f"derived({lbl}_of_two_numbers_in_the_passage)"
        return ""

    @staticmethod
    def _hit(lst, v, tol):
        import bisect
        i = bisect.bisect_left(lst, v - tol)
        return i < len(lst) and lst[i] <= v + tol

    def direct(self, v: float, dp: int) -> str:
        tol = _tol(dp)
        if Pools._hit(self.s_art, v, tol):
            return "artefact"
        if Pools._hit(self.p_art, v, tol):
            return "artefact(percent)"
        if Pools._hit(self.s, v, tol):
            return "table"
        if Pools._hit(self.p, v, tol):
            return "table(percent)"
        return ""

    def derived(self, v: float, dp: int) -> str:
        """A difference, product or share a reader can compute from what the package itself printed.

        Two branches, both bounded. `derived(diff)` needs both terms to be values the package holds, within a factor
        of a hundred of the figure being explained. `derived(product_or_share_within_one_row)` needs the two terms to
        be cells of one and the same table row - a share of that row's total, one of its cells over another, or their
        product - matched at the precision the figure is printed to. A cross-pool quotient was tried first and
        rejected as a rule: with `w / a` rounded to four decimals against a pool that holds 0.01 and 111, nearly every
        value in [0, 3] is "explained" by some pair that has nothing to do with it (289 of 300 unrelated random
        figures passed on P045 that way).
        """
        k = max(dp, 4)
        for sgn in (1.0, -1.0):
            w = sgn * abs(v)
            for a in self.near:
                if not a or abs(w) / 100.0 > abs(a) or abs(a) > max(abs(w), 1.0) * 100.0:
                    continue
                for want in (a - w, w - a, w + a):
                    if round(want, k) in self.keys:
                        return "derived(diff)"
            if w and Pools._hit(self.rowop_list, abs(w), _tol(dp)):
                return "derived(product_or_share_within_one_row)"
            if w and Pools._hit(self.sib_list, abs(w), _tol(dp)):
                return "derived(arithmetic_within_one_run_record)"
        return ""

    COL_STOP = {"n", "num", "tot", "total", "sum", "count", "value", "all", "per", "the", "and", "own"}

    def column_total(self, v: float, dp: int, ctx: str) -> str:
        """A prose number that is one shipped table column added over its rows - when the sentence names the column.

        The name test is what keeps this honest: a table can hold a hundred columns whose totals coincide with
        unrelated numbers by accident, so the sentence has to say which quantity it is adding up.
        """
        if not self.colsums or not ctx:
            return ""
        low, tol = ctx.lower(), max(_tol(dp), 0.5)
        for val, (spec, k) in self.colsums.items():
            if abs(val - abs(v)) > tol:
                continue
            col = spec.rsplit(".", 1)[-1]
            words = [w for w in re.split(r"[^a-z0-9]+", col.lower()) if len(w) > 2 and w not in self.COL_STOP]
            if any(w in low for w in words):
                return f"total_of_a_shipped_column({spec} over {k} rows)"
        return ""


def frozen_constants() -> set:
    """Every number the twelve freeze modules state as a rule: floors, bands, caps, seeds, gate thresholds.

    A sentence quoting "the medium band starts at 0.15" is quoting a decision written before the data was read,
    not a measurement, so those values are supported by the freeze source rather than by an artefact.
    """
    vals = set()
    for f in sorted((ROOT / "02_shared_code" / "package_factory").glob("topic_designs_wave*.py")):
        walk_numbers(NUM.findall(f.read_text(encoding="utf-8", errors="replace")), vals)
    return vals


def support(v: float, dp: int, pools: "Pools", ctx: str = "", para: str = None) -> str:
    """Why this number is allowed, or "" when nothing the package measured carries it.

    `ctx` is the window around the figure and `para` the whole wrapped paragraph. Each rule reads the context its own
    justification allows: a column total has to be named near the number, while arithmetic stated in prose may have
    its terms on the line above.
    """
    out = (pools.direct(v, dp) or pools.derived(v, dp) or pools.column_total(v, dp, ctx)
           or pools.sentence_arithmetic(v, dp, ctx if para is None else para)
           # prose quotes magnitudes and lets the words carry the sign ("falls by 0.0499"), and a figure lifted out of
           # a sentence arrives unsigned, so the same value on the other side of zero is the same measurement
           or (pools.direct(-v, dp) and "sign_carried_by_the_words"))
    if out:
        return out
    tol = _tol(dp)
    for a in FROZEN:
        if abs(a - abs(v)) <= tol:
            return "frozen_constant"
    return ""


def numbers_in(text: str) -> list:
    """[(value, decimals used, the surrounding phrase)] for every number a sentence asserts."""
    out = []
    for m in NUM.finditer(text):
        raw = m.group(0)
        dp = len(raw.split(".")[1]) if "." in raw else 0
        try:
            v = float(raw.replace(",", ""))
        except ValueError:
            continue
        out.append((v, dp, text[max(0, m.start() - 60):m.end() + 40].replace("\n", " ").strip()))
    return out


def packages() -> list:
    return sorted(p for p in (ROOT / "papers").glob("P0*") if p.is_dir())


DOCS = ("paper.md", "appendix.md", "README.md", "protocol_freeze.md", "limitations.md", "novelty_audit.md",
        "sota_audit.md", "reviewer_attack.md", "final_audit.md", "E_COVERAGE.md", "RUN_COST.md",
        "CONTAMINATION_AND_COST.md", "deviations.md", "dataset_card.md", "pilot_report.md", "research_plan.md",
        "novelty_grading.md")

# Documents a reader can open inside a package whose figures the checks do NOT read, and the reason each is left
# out. A named exclusion has to be a reason a reader can disagree with; an unnamed omission is just a blind spot.
DOC_EXCLUSIONS = {
    "logs/RUN_INDEX.md": "an index of the build - file names, byte sizes and the pass that wrote them. Its numbers "
                         "describe the estate's own run, and `round2_run_reality.py` is the check that reads those.",
}


def package_docs(pkg) -> list:
    """Every markdown document in one package that a reader is shown, in the order the checker should read it.

    Round 2 found the prose check working from a fixed list of seventeen names while 38 further package documents
    carried figures - including the premise-gate record `BLOCKED.md` in the twelve gated packages, a package's own
    second freeze, its error census and its external-probe reports. A list has to be maintained by whoever adds a
    document, which is how it fell behind; this derives the set from the package instead, minus what is excluded
    above with a reason. The classic names lead, so the order of the report is stable as documents are added.
    """
    rel = {str(f.relative_to(pkg)).replace(chr(92), "/") for f in pkg.rglob("*.md")}
    known = [d for d in DOCS if d in rel]
    rest = sorted(rel - set(DOCS) - set(DOC_EXCLUSIONS))
    return known + rest
