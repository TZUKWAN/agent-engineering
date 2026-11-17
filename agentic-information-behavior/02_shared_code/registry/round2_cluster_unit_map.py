"""EXP-0232: the unit behind every cluster-robust interval in the estate, joined to the counts it produced.

Round 2 scans 2,054 fields that print a cluster count (`clusters`, `n_clusters`) across the kept wave artefacts. A
cluster bootstrap is only right if it resamples whole groups of the unit the statistic is computed from - queries, not
candidate rows; conversations, not turns - so the number of clusters is meaningless to a reader who is not also told
what was grouped. This publishes the pairing from both sides a reader can check:

* the artefact side, which is what a reader actually holds: for each run record, the `cluster_unit` declarations inside
  it and the cluster counts it prints, so a row's count can be joined to the unit the run states;
* the code side, which is what the run did: every call to the estate's clustered resampler, the column it groups by
  resolved from the running module (a literal, a module constant, an enclosing function's local or default, or another
  module's constant), and the counts that module's own kept artefacts print.

An artefact that prints a count and no unit anywhere, or a call whose unit the scan cannot resolve, is listed rather
than assumed - the recurrence this is designed to catch is a design that silently bootstraps rows while its freeze
names a coarser unit.

    py -3.11 02_shared_code/registry/round2_cluster_unit_map.py [--check]
"""
from __future__ import annotations

import argparse
import ast
import collections
import csv
import datetime
import importlib
import io
import json
import pathlib
import re
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = next(a for a in (HERE, *HERE.parents) if (a / "00_program_registry").is_dir())
FAC = ROOT / "02_shared_code" / "package_factory"
RAW = ROOT / "results_raw"
DOC = ROOT / "docs" / "ROUND2_CLUSTER_UNITS.md"
REG = ROOT / "00_program_registry" / "experiment_registry.csv"
LEDGER = ROOT / "00_program_registry" / "SUPERSEDED_ARTIFACTS.json"
EXP = "EXP-0232"

CLUSTER_FUNCS = ("cluster_boot", "cluster_boot_ci_and_p")
# the words these helpers give their own parameter, which a caller may hand straight back; none of them names a column
GENERIC_ARG_NAMES = {"cluster", "clusters", "key", "keys", "col", "column", "columns", "group", "groups", "grp",
                     "ids", "unit", "units", "values", "vals", "x", "d", "df", "rows"}
COUNT_KEYS = ("clusters", "n_clusters")
UNIT_KEYS = ("cluster_unit", "clustered_by", "cluster_by", "grouped_by", "resampled_over")
# a column is a candidate unit if it names a thing that contains rows, not a property of one row
UNITISH = re.compile(r"(^|_)(id|ids|key|group|cluster|unit|set)$|query|session|conversation|trajectory|task|"
                     r"release|corpus|repository|document|doc|prompt|turn|rollout|attempt|step|shard|topic", re.I)


def enclosing(tree: ast.Module, lineno: int) -> str:
    """The function a call sits in - which is the topic or step the measurement belongs to."""
    names = [n.name for n in ast.walk(tree)
             if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
             and n.lineno <= lineno <= getattr(n, "end_lineno", lineno)]
    return names[-1] if names else "<module>"


def module_values(mod: pathlib.Path):
    """(module object, {alias: module name}) for one design module, or (None, {}) if it will not import.

    The unit is resolved by reading the running module rather than by matching text, because that is where the estate
    keeps it: `CLUSTER = D10.CLUSTER`, `CLUSTER = TD10.COMMON["sample"]["cluster_unit"]` and `CLUSTER = "traj_id"` are
    one fact written three ways, and only evaluating the assignment resolves all three. A module that will not import is
    reported as unresolved, not guessed at.
    """
    try:
        if str(FAC) not in sys.path:
            sys.path.insert(0, str(FAC))
        m = importlib.import_module(mod.stem)
    except Exception:                                              # noqa: BLE001 - an unimportable module says so below
        return None, {}
    aliases = {}
    try:
        tree = ast.parse(mod.read_text(encoding="utf-8", errors="replace"))
    except (SyntaxError, OSError):
        return m, {}
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names:
                aliases[a.asname or a.name.split(".")[0]] = a.name
    return m, aliases


def local_string(tree: ast.Module, lineno: int, name: str):
    """The string the enclosing function binds to `name`: a local assignment or a parameter default."""
    best = None
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.lineno <= lineno <= getattr(n, "end_lineno",
                                                                                                    n.lineno):
            if best is None or n.lineno > best.lineno:
                best = n
    if best is None:
        return None
    for st in ast.walk(best):
        if isinstance(st, ast.Assign) and isinstance(st.value, ast.Constant) and isinstance(st.value.value, str):
            if any(isinstance(t, ast.Name) and t.id == name for t in st.targets):
                return st.value.value
    a = best.args
    for p, d in zip(list(a.args)[len(a.args) - len(a.defaults):] if a.defaults else [], a.defaults or []):
        if p.arg == name and isinstance(d, ast.Constant) and isinstance(d.value, str):
            return d.value
    for p, d in zip(a.kwonlyargs, a.kw_defaults):
        if p.arg == name and isinstance(d, ast.Constant) and isinstance(d.value, str):
            return d.value
    return None


def resolve_key(node, mod_obj, aliases, tree: ast.Module, lineno: int) -> tuple:
    """(column, expression text, how it was resolved) for a clustered call's second argument."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value, node.value, "literal"
    if node is None:
        return "", "<no argument>", "unreadable"
    text = ast.unparse(node)
    if isinstance(node, ast.Name):
        loc = local_string(tree, lineno, node.id)
        if loc:
            return loc, text, "enclosing function"
        v = getattr(mod_obj, node.id, None) if mod_obj is not None else None
        return (v, text, "module constant") if isinstance(v, str) else ("", text, "unresolved")
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and mod_obj is not None:
        target = aliases.get(node.value.id)
        try:
            v = getattr(importlib.import_module(target), node.attr, None) if target else None
        except Exception:                                          # noqa: BLE001
            v = None
        return (v, text, "another module's constant") if isinstance(v, str) else ("", text, "unresolved")
    return "", text, "unresolved"


def call_sites(mod: pathlib.Path) -> list:
    """Every clustered-resampler call in one module."""
    tree = ast.parse(mod.read_text(encoding="utf-8", errors="replace"))
    mod_obj, aliases = module_values(mod)
    out = []
    for n in ast.walk(tree):
        if not isinstance(n, ast.Call):
            continue
        fn = n.func
        name = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", "")
        if name not in CLUSTER_FUNCS:
            continue
        key, raw, via = resolve_key(n.args[1] if len(n.args) > 1 else None, mod_obj, aliases, tree, n.lineno)
        kw = {k.arg: ast.unparse(k.value) for k in n.keywords}
        out.append({"call": name, "frame": ast.unparse(n.args[0]) if n.args else "", "key": key,
                    "key_expression": raw, "key_via": via, "unresolved": via in ("unresolved", "unreadable"),
                    "draws": kw.get("draws", "default(2000)"), "line": n.lineno,
                    "enclosing": enclosing(tree, n.lineno)})
    return out


def caller_graph(mods: list) -> dict:
    """{function name: [(module, line, enclosing function, [argument text], {keyword: argument text})]}."""
    graph = collections.defaultdict(list)
    for mod in mods:
        try:
            tree = ast.parse(mod.read_text(encoding="utf-8", errors="replace"))
        except (SyntaxError, OSError):
            continue
        for n in ast.walk(tree):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
                graph[n.func.id].append((mod.name, n.lineno, enclosing(tree, n.lineno),
                                         [ast.unparse(a) for a in n.args],
                                         {k.arg: ast.unparse(k.value) for k in n.keywords}))
    return graph


def param_index(mods: list, fname: str, pname: str):
    """Position of `pname` in `fname`'s signature, or None if no module defines that function with that parameter."""
    return param_shape(mods, fname, pname)[0]


def param_shape(mods: list, fname: str, pname: str):
    """(position of `pname`, {module: the expression its signature gives it when a call omits the argument}).

    The default matters because these batteries pass the unit that way: `def kappa(d, label, a, b, note,
    cluster=CLUSTER)` resamples `CLUSTER` on every call that does not say otherwise, and reading only the call sites
    reported the site as unreadable.
    """
    idx, defaults = None, {}
    for mod in mods:
        try:
            tree = ast.parse(mod.read_text(encoding="utf-8", errors="replace"))
        except (SyntaxError, OSError):
            continue
        for n in ast.walk(tree):
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == fname:
                args = [a.arg for a in n.args.args]
                if pname not in args:
                    continue
                i = args.index(pname)
                idx = i if idx is None else idx
                first = len(n.args.args) - len(n.args.defaults)
                if i >= first:
                    defaults[mod.name] = ast.unparse(n.args.defaults[i - first])
    return idx, defaults


def arg_to_unit(expr: str, consts: dict | None = None) -> str:
    """The column name an argument expression reads as, or "" when it does not read as one.

    Deliberately narrow: a string literal in a subscript, a module constant's value (`CLUSTER` where the calling
    module sets `CLUSTER = "query_id"`), or a bare name that itself looks like a collection (`qid`, `traj_id`).
    Anything looser - a comprehension, a call, a parameter handed down from another helper - cannot be turned into
    a column name by reading one line, and the map's whole point is that it says what it actually saw. A caller
    that does not read stays on the record as unreadable rather than being guessed at.
    """
    e = (expr or "").strip()
    if not e:
        return ""
    if re.fullmatch(r"""['"].+?['"]""", e):
        return e[1:-1]                                   # a column name passed as a string literal
    m = re.search(r'''\[\s*["']([\w\-]+)["']\s*\]''', e)
    if m:
        return m.group(1)
    if re.fullmatch(r"[A-Z][A-Z0-9_]*", e) and consts:
        v = consts.get(e)
        return v if isinstance(v, str) and UNITISH.search(v) else ""
    if re.fullmatch(r"[\w.]+", e):
        tail = e.split(".")[-1]
        # `cluster`, `key`, `col` etc. are the names these helpers give the parameter itself, so a caller that hands
        # one back has not said what unit it uses; taking the word as the column would invent an answer
        if tail.isupper() or tail in GENERIC_ARG_NAMES:
            return ""
        return tail if UNITISH.search(tail) else ""
    return ""


def module_constants(mods: list) -> dict:
    """{module name: {UPPER_CASE name: string value}} read from each module's own top-level assignments.

    Read off the syntax tree rather than by importing the module: these scripts read environment paths and corpus
    files at import time, and a documentation scan must not depend on being able to run them.

    Two shapes are read. The simple one is `CLUSTER = "query_id"`. The one that defeated the first version of this
    scan is the estate's frozen-design form, `CLUSTER = TD10.COMMON["sample"]["cluster_unit"]`, where the string the
    design froze lives in a literal dictionary in the design module the script imports. That is resolved by parsing
    the imported module as well: a wave's frozen `cluster_unit` is the authority on what that wave groups by, so
    reading it states a stronger claim than guessing at it, and the value reported is the one the design carries.
    """
    envs = {}
    for mod in mods:
        envs[mod.stem] = _literal_env(mod)
    for stem in sorted({t for mod in mods for t in _aliases(mod).values()}):
        if stem not in envs and (FAC / f"{stem}.py").is_file():
            envs[stem] = _literal_env(FAC / f"{stem}.py")          # the design file the frozen value is read from
    cache = {mod.stem: _aliases(mod) for mod in mods}

    def alias_of(stem: str) -> dict:
        if stem not in cache:
            cache[stem] = _aliases(FAC / f"{stem}.py") if (FAC / f"{stem}.py").is_file() else {}
        return cache[stem]

    out = {}
    for mod in mods:
        consts = {}
        for name, val in envs[mod.stem].items():
            if not name.isupper():
                continue
            v = val if isinstance(val, str) else _eval_chain(val, mod.stem, envs, alias_of)
            if isinstance(v, str):
                consts[name] = v
        out[mod.name] = consts
    return out


def _aliases(mod) -> dict:
    """{alias or imported name: module stem} for one module's imports, so a chain can cross into the design file."""
    out = {}
    try:
        tree = ast.parse(mod.read_text(encoding="utf-8", errors="replace"))
    except (SyntaxError, OSError):
        return out
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names:
                out[a.asname or a.name.split(".")[-1]] = a.name.split(".")[-1]
        elif isinstance(n, ast.ImportFrom) and n.module:
            for a in n.names:
                out[a.asname or a.name] = n.module
    return out


def _soft(node):
    """A literal value where the node is one, and a marker string where it is not.

    A frozen design dictionary is not always a pure literal - it holds expressions for caps and seeds - so the
    parts that are text are kept and the rest are named by their source. Only a value that reads as a collection
    is ever reported, so a marker can leave a site unresolved but cannot invent a column.
    """
    try:
        return True, ast.literal_eval(node)
    except (ValueError, SyntaxError, TypeError):
        pass
    if isinstance(node, ast.Dict):
        out = {}
        for k, v in zip(node.keys, node.values):
            kk = k.value if isinstance(k, ast.Constant) and isinstance(k.value, str) else None
            ok, vv = _soft(v)
            if kk is not None and (ok or isinstance(vv, (dict, list))):
                out[kk] = vv
        return True, out
    if isinstance(node, ast.List):
        vals = [_soft(e)[1] for e in node.elts]
        return True, [v for ok, v in zip(map(_soft, node.elts), vals) if ok]
    return False, "<" + type(node).__name__ + ">"


def _literal_env(path) -> dict:
    """{top-level assigned name: its literal value, or its unevaluated node when that needs a chain to read}."""
    env = {}
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except (SyntaxError, OSError):
        return env
    for n in tree.body:
        if not isinstance(n, ast.Assign) or not n.targets or not isinstance(n.targets[0], ast.Name):
            continue
        ok, val = _soft(n.value)
        env[n.targets[0].id] = val if ok else n.value
    return env


def _eval_chain(node, stem: str, envs: dict, alias_of, depth: int = 0):
    """Value of `NAME`, `MOD.NAME`, or either subscripted by string keys, read across the frozen design modules."""
    if node is None or depth > 8:
        return None
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Attribute):
        if isinstance(node.value, ast.Name) and node.value.id in alias_of(stem):
            owner = alias_of(stem)[node.value.id]
            return _const_value(node.attr, owner, envs, alias_of, depth + 1) if owner in envs else None
        base = _eval_chain(node.value, stem, envs, alias_of, depth + 1)
        return base.get(node.attr) if isinstance(base, dict) else None
    if isinstance(node, ast.Subscript):
        base = _eval_chain(node.value, stem, envs, alias_of, depth + 1)
        key = node.slice
        return base.get(key.value) if isinstance(base, dict) and isinstance(key, ast.Constant) else None
    if isinstance(node, ast.Name):
        return _const_value(node.id, stem, envs, alias_of, depth + 1)
    return None


def _const_value(name: str, stem: str, envs: dict, alias_of, depth: int = 0):
    """What a module binds a name to, following the binding into whichever module the name was imported from.

    The batteries write `CLUSTER = D10.CLUSTER` and the designs write `CLUSTER = TD10.COMMON["sample"]
    ["cluster_unit"]`, so one more hop is needed than a single file can answer: the value of a wave's grouping
    column is frozen in that wave's design module, and reading it there is the point of the exercise.
    """
    env = envs.get(stem) or {}
    owner = stem
    if name not in env:
        hits = [s for s, e in envs.items() if name in e]
        if len(hits) != 1:
            return None
        owner, env = hits[0], envs[hits[0]]
    v = env[name]
    if not isinstance(v, ast.expr):
        return v
    return _eval_chain(v, owner, envs, alias_of, depth + 1)


def _defining_modules(mods: list, fname: str, nparams: int) -> set:
    """Which wave modules define a function `fname` taking at least `nparams` positional arguments."""
    out = set()
    for mod in mods:
        try:
            tree = ast.parse(mod.read_text(encoding="utf-8", errors="replace"))
        except (SyntaxError, OSError):
            continue
        for n in ast.walk(tree):
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == fname and len(n.args.args) >= nparams:
                out.add(mod.name)
    return out


def resolve_through_callers(site: dict, mods: list, graph: dict, consts: dict, where: str = "",
                            depth: int = 0) -> dict:
    """Fill a helper's cluster key by reading who calls the helper and with what.

    `cluster_boot_ci_and_p(values, cluster, draws)` inside a function named `boot` cannot say what was resampled:
    the unit is decided at every call of `boot`. Each wave module carries its own `boot`, so the callers counted
    are those of the modules that define it, and a module that merely calls an imported one is reported as a
    caller of that same definition - which is why the shape is read from the signature and not from a name.
    Round 2 first published these sites - the estate's most-used CI helper - as unresolved, which is honest but
    leaves the claim untested. Following the call graph turns it into a reading of the code, and only a call set
    that is **fully** readable and disagrees counts as the finding this table exists to surface: one helper
    resampling two different units. A partly readable set stays unresolved and says how much of it was read.
    """
    fname, pname = site.get("enclosing") or "", site.get("key_expression") or ""
    if not fname or fname == "<module>" or not re.fullmatch(r"[\w.]+", pname or ""):
        return site
    idx, defaults = param_shape(mods, fname, pname)
    if idx is None:
        return site
    homes = _defining_modules(mods, fname, idx + 1)
    if where in homes:
        homes = {where}      # the module that defines this helper is the one whose calls decide its unit
    seen, unreadable, raw, per_caller = [], 0, [], collections.defaultdict(set)
    for cm, cl, cfn, args, kws in graph.get(fname, []):
        if homes and cm not in homes:
            continue                                    # a call of a same-named helper defined elsewhere
        expr = kws.get(pname) or (args[idx] if idx < len(args) else "")
        by_default = False
        if not expr and defaults.get(where):
            expr, by_default = defaults[where], True       # the signature says what an omitted argument resamples
        u = arg_to_unit(expr, consts.get(cm) or consts.get(where))
        if not u and depth < 2 and cfn and re.fullmatch(r"[a-z_][\w]*", expr or "") and expr != fname:
            # the caller hands on one of its own parameters, so the unit is decided one level up: read that
            # function's callers the same way rather than reporting the site as unreadable
            sub = resolve_through_callers({"enclosing": cfn, "key_expression": expr, "line": cl},
                                          mods, graph, consts, cm, depth + 1)
            if sub.get("key") and str(sub.get("key_via", "")).startswith("the "):
                u = sub["key"]
                for part in str(u).split(" | "):
                    per_caller[(cm, cfn)].add(part)
        if u:
            seen.append(f"{cm}:{cl} in {cfn}() -> {u}" + (", by the parameter's default" if by_default else ""))
            if "|" not in u:
                per_caller[(cm, cfn)].add(u)
        elif expr:
            unreadable += 1
            raw.append(f"{cm}:{cl} passes {expr[:40]!r}")
    units = sorted({s.split("-> ")[1].split(",")[0] for s in seen})
    # One helper serving several designs is normal; one design resampling two different units is not. The suspect
    # case is therefore keyed on the calling context, not on the helper: `boot()` called with `conversation_id` by
    # T184 and `instance_id` by T194 says the shared helper is generic, while two units from the same function
    # would say one interval was claimed on a grouping the statistic is not computed from.
    mixed = sorted(f"{cm}.{cfn}() on {sorted(us)}" for (cm, cfn), us in per_caller.items() if len(us) > 1)
    if not units:
        # nothing read as a column, but the call sites themselves are the evidence a person needs to check the
        # claim, so they go on the record rather than being reduced to "unresolved"
        out = dict(site)
        out["unresolved"] = True
        out["callers"] = raw[:8]
        return out
    out = dict(site)
    out["key"] = " | ".join(units)
    out["callers"] = seen[:8]
    full = unreadable == 0
    out["key_via"] = (f"the {len(per_caller)} calling context(s) of {fname}()" if full else
                      f"partly: {len(seen)} of the calls of {fname}() read as a column, {unreadable} do not")
    out["unresolved"] = (not full) or bool(mixed)
    out["suspect"] = bool(mixed)
    out["mixed_in_one_caller"] = mixed
    return out


def superseded_names() -> set:
    if not LEDGER.is_file():
        return set()
    try:
        d = json.loads(LEDGER.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return set()
    ent = d.get("entries", d) if isinstance(d, dict) else d
    out = set()
    for e in ent or []:
        for v in (e.values() if isinstance(e, dict) else [e]):
            if isinstance(v, str):
                out.add(v.split("/")[-1])
    return out


def scan_record(path: pathlib.Path) -> dict:
    """What one run record says about clustering: the units it declares and the counts it prints."""
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return {}
    units, counts = collections.Counter(), collections.Counter()

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in UNIT_KEYS and isinstance(v, str):
                    units[v] += 1
                elif k in COUNT_KEYS and isinstance(v, int) and not isinstance(v, bool):
                    counts[v] += 1
                else:
                    walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(d)
    return {"units": dict(units), "counts": dict(counts)}


def artefact_side(exp_ids_by_module: dict) -> tuple:
    """Per run record: declared units and printed cluster counts, for the runs the design modules produce.

    Returns (rows, counts_of_the_condition_the_reader_cannot_check) - a record that prints a count while naming no
    unit anywhere in itself is the case a reader cannot close on their own.
    """
    prefixes = {e.replace("-", ""): m for m, ids in exp_ids_by_module.items() for e in ids}
    sup = superseded_names()
    rows, blind = [], 0
    for f in sorted(RAW.glob("EXP0*.json")):
        pref = next((p for p in prefixes if f.name.startswith(p)), "")
        if not pref or f.name in sup:
            continue
        got = scan_record(f)
        if not got.get("counts"):
            continue
        has_unit = bool(got.get("units"))
        blind += not has_unit
        rows.append({"file": f.name, "module": prefixes[pref], "counts": sorted(got["counts"])[:8],
                     "n_counts": sum(got["counts"].values()), "units": sorted(got["units"])[:6],
                     "reader_can_pair": has_unit})
    return rows, blind


def package_unit_prose() -> set:
    """{P0nn} for the packages whose own documents state a clustering rule.

    The question a reader of a shipped record asks is not "does this JSON name its unit" but "can I tell from this
    package what was grouped", and a method sentence in `protocol_freeze.md` or `appendix.md` answers it. Counting those
    packages is what turns "248 records name no unit" into a statement about readers rather than about JSON layout.
    """
    rx = re.compile(r"cluster_unit|cluster[- ]bootstrap|clustered", re.I)
    out = set()
    for p in sorted((ROOT / "papers").glob("P0*")):
        if not p.is_dir():
            continue
        for f in list(p.glob("*.md")) + list(p.glob("tables/*.csv")):
            try:
                if rx.search(f.read_text(encoding="utf-8", errors="replace")):
                    out.add(p.name)
                    break
            except (OSError, UnicodeDecodeError):
                continue
    return out


def classify_reader_reach(art_rows: list) -> dict:
    """For the records that name no unit: who holds them, and is the unit stated where they are held."""
    shipped = {}
    for p in sorted((ROOT / "papers").glob("P0*")):
        if not p.is_dir():
            continue
        for sub in ("results_raw", "results_processed"):
            for f in (p / sub).glob("EXP*"):
                shipped.setdefault(f.name, set()).add(p.name)
    prose = package_unit_prose()
    c = {"in_record": 0, "shipped_with_a_stated_unit": 0, "shipped_without_any_statement": 0, "programme_only": 0}
    orphans = []
    for x in art_rows:
        if x["reader_can_pair"]:
            c["in_record"] += 1
            continue
        pks = shipped.get(x["file"], set())
        if not pks:
            c["programme_only"] += 1
        elif pks & prose:
            c["shipped_with_a_stated_unit"] += 1
        else:
            c["shipped_without_any_statement"] += 1
            orphans.append(f"{x['file']} ({', '.join(sorted(pks))})")
    c["orphans"] = orphans
    return c


def module_runs() -> dict:
    """{module file name: [exp_id, ...]} from the register's `script` column."""
    out = collections.defaultdict(list)
    if REG.is_file():
        for r in csv.DictReader(io.StringIO(REG.read_text(encoding="utf-8"))):
            s = (r.get("script") or "").replace("\\", "/").split("/")[-1]
            if s:
                out[s].append(r["exp_id"])
    return out


def ensure_row(started: str, finished: str) -> None:
    """Carry this run in the master register before it writes, so the map is a registered measurement."""
    if not REG.is_file():
        return
    row = {"exp_id": EXP, "paper_id": "programme", "stage": "round2_cluster_unit_map",
           "script": "02_shared_code/registry/round2_cluster_unit_map.py",
           "config": "every kept artefact of the runs the design modules produce, read for its cluster_unit "
                     "declarations and its cluster counts, joined to an AST-and-import scan of every "
                     "cluster_boot call in 02_shared_code/package_factory; no measurement is taken",
           "seed": "n/a (a static and structural scan)", "started_at": started, "finished_at": finished,
           "status": "cluster_units_mapped",
           "outputs": "results_raw/EXP0232_cluster_unit_map_*.json; docs/ROUND2_CLUSTER_UNITS.md",
           "enters_paper": "no",
           "notes": "round-2: 2,054 artefact fields print a cluster count. A count is only checkable next to the unit "
                    "that was grouped, so this publishes both sides: what each run record declares as its cluster "
                    "unit, and what each clustered call in the code groups by."}
    rows = list(csv.DictReader(io.StringIO(REG.read_text(encoding="utf-8"))))
    cols = list(rows[0])
    hit = next((r for r in rows if r["exp_id"] == EXP), None)
    if hit is None:
        hit = {c: "" for c in cols}
        hit["exp_id"] = EXP
        rows.append(hit)
    n = 0
    for k, v in row.items():
        if k in cols and hit.get(k) != v:
            hit[k] = v
            n += 1
    if not n:
        return
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, lineterminator=chr(10))
    w.writeheader()
    for r in rows:
        w.writerow({c: str(r.get(c) or "") for c in cols})
    REG.write_text(buf.getvalue(), encoding="utf-8")
    print(f"registry: {EXP} row set ({n} field(s) written)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="write the artefact report but not the document or register")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    t0 = time.time()
    started = datetime.datetime.now().isoformat(timespec="seconds")
    runs = module_runs()
    mods = sorted(FAC.glob("exp_wave*.py"))
    graph = caller_graph(mods)
    consts = module_constants(mods)
    rows, sus = [], []
    for mod in mods:
        for s in call_sites(mod):
            if s["unresolved"]:
                s = resolve_through_callers(s, mods, graph, consts, mod.name)
            if s.get("suspect"):
                sus.append(f"{mod.name}:{s['line']} groups by more than one unit *within one calling design*: "
                           f"{'; '.join(s['mixed_in_one_caller'])} - one interval is therefore claimed on a "
                           f"grouping that its statistic may not be computed from")
            elif s["unresolved"]:
                sus.append(f"{mod.name}:{s['line']} groups by {s['key_expression']}, which this scan cannot resolve "
                           f"to a column name"
                           + (f" nor the {len(s['callers'])} call(s) of {s['enclosing']}() that would say: "
                              + "; ".join(s["callers"]) if s.get("callers") else ""))
            elif not UNITISH.search(s["key"]):
                sus.append(f"{mod.name}:{s['line']} groups by {s['key']!r}, which does not name a collection")
            rows.append({**s, "module": mod.name})
    art_rows, blind = artefact_side(runs)
    reach = classify_reader_reach(art_rows)
    grouped = collections.OrderedDict()
    for x in sorted(art_rows, key=lambda y: y["file"]):
        stem = re.sub(r"_\d{8}T\d{6}(?:_\w+)?\.json$", "", x["file"])
        g = grouped.setdefault((x["module"], stem, tuple(x["units"]), x["reader_can_pair"]),
                               {"n": 0, "counts": set()})
        g["n"] += 1
        g["counts"].update(x["counts"])
    finished = datetime.datetime.now().isoformat(timespec="seconds")
    units = sorted({u for r in rows if r["key"] for u in r["key"].split(" | ")}
                   | {u for x in art_rows for u in x["units"]})
    paired = sum(1 for x in art_rows if x["reader_can_pair"])

    L_ = ["# Round-2: the unit behind every cluster-robust interval", "",
          f"Generated by `02_shared_code/registry/round2_cluster_unit_map.py` ({EXP}) at {finished}; re-run it after "
          "changing a design's resampling. Do not hand-edit this file.", "",
          f"A cluster bootstrap is right only if it resamples whole groups of the unit the statistic is computed from. "
          f"This records both sides of that claim: {len(rows)} clustered call site(s) in "
          f"{len({r['module'] for r in rows})} module(s), and {len(art_rows)} kept run record(s) - "
          f"{len(grouped)} runs - that print a cluster count, of which {paired} also state their cluster unit inside "
          f"themselves.", "",
          "## Who can tell what was grouped", "",
          f"- `{reach['in_record']}` records name their own unit, so the count and the unit are in one file;",
          f"- `{reach['shipped_with_a_stated_unit']}` name no unit but are shipped by a package whose method text "
          f"states a clustering rule, so a reader of that package can still answer the question;",
          f"- `{reach['programme_only']}` name no unit and live only in the programme's own results folder - they are "
          f"the estate's internal battery and audit records, held by no package;",
          f"- `{reach['shipped_without_any_statement']}` are shipped by a package that states no clustering rule "
          f"anywhere - listed below, and the condition this table exists to catch.", ""]
    L_ += [f"  - {o}" for o in reach["orphans"][:20]]
    L_ += ["", "## What each run record says", "",
           "| run | module | cluster counts printed | cluster unit(s) it declares | generations | pairable alone |",
           "|---|---|---|---|---|---|"]
    for (module, stem, u, can), g in list(grouped.items())[:80]:
        L_.append(f"| `{stem}` | `{module}` | {sorted(g['counts'])[:8]} | {list(u) or 'none'} | {g['n']} | "
                  f"{'yes' if can else 'NO'} |")
    L_ += ["",
           "## What each clustered call groups by", "",
           "| module | step / function | line | resampler | grouped by | how that was read | draws |",
           "|---|---|---|---|---|---|---|"]
    for r in sorted(rows, key=lambda x: (x["module"], x["line"])):
        unit = f"`{r['key']}`" if r["key"] else f"not resolved (`{r['key_expression']}`)"
        L_.append(f"| `{r['module']}` | `{r['enclosing']}` | {r['line']} | `{r['call']}` | {unit} | {r['key_via']} | "
                  f"{r['draws']} |")
    L_ += ["", "## Calls whose unit is not resolvable, or does not name a collection", ""]
    L_ += [f"- {s}" for s in sus] or ["- none: every clustered call resolves to a column whose name denotes a "
                                      "collection (query, conversation, trajectory, instance, ...) rather than a row."]
    L_ += ["", "## What this does not claim", "",
           "Neither table re-derives an interval; that is `round2_statistical_consistency.py` and "
           "`round2_interval_audit.py`. A record stating a unit is not proof that its count equals the number of "
           "distinct values of that unit in the frame it read - checking that would mean re-reading the frames "
           "themselves, which is what `round2_corpus_remeasurement.py` does for counts and row totals. Where the two "
           "sides disagree, the code side is the one to believe, and the disagreement is a defect to fix in the "
           f"design, not to paper over here.", ""]
    body = "\n".join(L_) + "\n"
    if a.check:
        print(body[:1200])
    else:
        DOC.parent.mkdir(exist_ok=True)
        DOC.write_text(body, encoding="utf-8")
        ensure_row(started, finished)
    payload = {"detector": "round2_cluster_unit_map", "exp_id": EXP, "at": finished,
               "call_sites": len(rows), "modules": len({r['module'] for r in rows}), "units": units,
               "records_with_counts": len(art_rows), "runs_with_counts": len(grouped),
               "records_pairable": paired, "records_naming_no_unit": blind, "reader_reach": reach,
               "suspect": sus, "rows": rows, "artefacts": art_rows,
               "wallclock_sec": round(time.time() - t0, 1)}
    out = RAW / f"EXP0232_cluster_unit_map_{time.strftime('%Y%m%dT%H%M%S')}.json"
    out.write_text(json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"{len(rows)} call site(s) | {len(units)} unit column(s) | {len(art_rows)} records over {len(grouped)} runs "
          f"({paired} pairable; unpaired: {reach['shipped_with_a_stated_unit']} with a stated rule, "
          f"{reach['programme_only']} programme-only, {reach['shipped_without_any_statement']} with nothing) | "
          f"{len(sus)} suspect(s) | wrote {out.name}"
          + ("" if not a.check else " (--check: document not written)"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
