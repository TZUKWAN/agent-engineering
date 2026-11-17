"""Round-2 check D: is every registered experiment an actual run that can be opened?

Each row of `experiment_registry.csv` claims a script, a seed, a window of time and an artefact. This checks the
claim against the filesystem rather than against the registry's own wording:

* the script the row names exists at that path;
* the artefact exists, its embedded `exp_id` equals the row's, and the command line it recorded names that script;
* the artefact's seed equals the row's (or the row says why there is no seed);
* `started_at` <= `finished_at` and both are inside the artefact's own recorded window where the artefact records one;
* the register's time claim is the kind its own artefacts support: `round2_register_windows.py` labels every row's
  window as `measured`, `instant_recorded`, `output_stamp` or one of the honest not-recorded shapes in its notes,
  and this check re-tests that the label still holds - a `measured` row must have a generation of its own inside
  its window, an instant row within two minutes of its stated reading. Filename stamps are used rather than file
  mtimes because the estate's own packaging moves mtimes; rows carrying no label are reported as such.
* where a package copies the artefact into its own `results_raw`, the copy is byte-identical to the programme one;
* the kept generation of each experiment is not in the supersession ledger (a package that ships a retired
  generation is reporting a number a later run contradicted).

Anything that fails is printed with the file, because a run nobody can reopen is not evidence.

    python 02_shared_code/registry/round2_run_reality.py [--limit 40]
"""
from __future__ import annotations

import argparse
import collections
import datetime
import hashlib
import json
import pathlib
import re
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import round2_lib as L                                                    # noqa: E402
import compare_artefact_generations as C                                  # noqa: E402

ROOT = L.ROOT
REC = ROOT / "00_program_registry" / "experiment_registry.csv"


def norm_id(s: str) -> str:
    """`EXP0008f`, `EXP-0008f` and `exp-0008f` are the same run."""
    s = (s or "").strip().upper()
    return s if s.startswith("EXP-") else ("EXP-" + s[3:]) if s.startswith("EXP") else s


def h(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def parts_of(spec: str) -> list:
    """Split an `outputs` cell on `;` and `,` without cutting inside a brace list.

    `routing_{OSS,Qwen3,Kimi-K2}.parquet` is one path pattern, and splitting it on its commas turned a valid
    declared output into three fragments that match nothing - which the first pass of this check reported as a
    run whose declared output does not exist.
    """
    out, depth, cur = [], 0, ""
    for ch in spec:
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth = max(0, depth - 1)
        if ch in ";," and depth == 0:
            out.append(cur)
            cur = ""
            continue
        cur += ch
    out.append(cur)
    return out


def expand(root: pathlib.Path, spec: str) -> list:
    """Resolve one `outputs` cell: the registry is the authority for where a run wrote, so the lookup follows the
    row's own glob (which may be a brace list, a Windows path, or prose about a console probe)."""
    out = []
    for part in parts_of(spec):
        part = part.strip().lstrip(">").strip()
        if not part or "(" in part or "console" in part.lower() or "no file" in part.lower():
            continue
        part = part.replace(chr(92), "/")
        if "{" in part and "}" in part and "," not in part.split("{", 1)[1].split("}", 1)[0]:
            # `EXP0014_pairs_{cfg}.parquet` is a placeholder for whatever the run named each shard, not a brace
            # list of alternatives; read as a glob it resolves to the files that exist instead of to nothing
            field = part.split("{", 1)[1].split("}", 1)[0]
            part = part.replace("{" + field + "}", "*")
        if "{" in part and "}" in part:
            head, rest = part.split("{", 1)
            mid, tail = rest.split("}", 1)
            for alt in mid.split(","):
                out += expand(root, head + alt + tail)
            continue
        if "*" in part or "?" in part:
            out += [f for f in sorted(root.glob(part)) if f.is_file()]
        elif (root / part).is_file():
            out.append(root / part)
    return out


def script_path(field: str) -> tuple:
    """(path or None, is_prose) for the registry's `script` cell, which sometimes carries its own arguments."""
    for tok in re.split(r"[;,()]", field or ""):
        tok = tok.strip().split()[0] if tok.strip() else ""
        if tok.endswith(".py"):
            return tok, False
    return None, bool((field or "").strip())


STAMP = re.compile(r"_(\d{8})T(\d{6})(?=\D|$)")
SLACK = 120                                                              # seconds of clock jitter absorbed
# what the timeline pass could and could not test, kept beside its findings so a zero is read with its coverage
COVERAGE = collections.Counter()


def stamp_of(name: str) -> str:
    """The production time a filename declares, or "" for the early runs that name their output without one.

    Only the stamp is read, and deliberately not the filesystem mtime: the recorders write
    `..._20260920T040334.json` from the clock at write time, so the stamp is the run's own declaration, while an
    mtime is whatever the last copy did to it - the estate's own pruning and packaging move mtimes, and a check
    that read them would flag and unflag the same file between two runs of this detector.
    """
    m = STAMP.search(name)
    if not m:
        return ""
    d, t = m.group(1), m.group(2)
    return f"{d[0:4]}-{d[4:6]}-{d[6:8]}T{t[0:2]}:{t[2:4]}:{t[4:6]}"


def timeline(row: dict, found: list, kinds: dict) -> list:
    """Does the register's time claim still hold against the generations the row itself produced?

    `round2_register_windows.py` labels every row with a `window_kind=...` note, because the estate's recorders
    mixed measured windows, hand-rounded approximations and single write-time readings, and a reader cannot tell
    which of the three a given row is from the columns alone. Each label states what the row's own artefacts can
    corroborate, so the test here is that the label holds: a `measured` row must have a generation inside its
    window, an `instant_recorded` or `output_stamp` row must have one within two minutes of its stated instant.
    A row that carries no label at all - one added since the labeler last ran - is reported rather than guessed at.
    """
    out = []
    m = re.search(r"window_kind=(\S+)", row.get("notes") or "")
    kind = m.group(1) if m else ""
    kinds[kind or "unlabelled"] = kinds.get(kind or "unlabelled", 0) + 1
    stamps = sorted({s for s in (stamp_of(f.name) for f in found) if s})
    if not kind:
        return out + [{"exp": row.get("exp_id"), "problem": "registry_row_carries_no_window_kind",
                       "hint": "run 02_shared_code/registry/round2_register_windows.py --apply"}]
    rs, rf = iso(row.get("started_at")), iso(row.get("finished_at"))
    if rs and rf and rf < rs:
        out.append({"exp": row.get("exp_id"), "problem": "registry_window_reversed",
                    "started": str(row.get("started_at")), "finished": str(row.get("finished_at"))})
    if kind == "measured":
        hit = [s for s in stamps if rs and rf
               and rs - datetime.timedelta(seconds=SLACK) <= iso(s) <= rf + datetime.timedelta(seconds=SLACK)]
        if not hit:
            out.append({"exp": row.get("exp_id"), "problem": "registered_window_not_corroborated_by_any_output",
                        "window": [str(row.get("started_at")), str(row.get("finished_at"))],
                        "own_generations": stamps[:2], "n_generations": len(stamps)})
    elif kind in ("instant_recorded", "output_stamp"):
        stated = rs or rf
        if not stamps:
            # nothing this row produced carries a time, so the label is exactly what it says - an untested reading -
            # and demanding corroboration here would flag the artefact's naming convention rather than the row
            COVERAGE["instant_without_a_stamped_output"] += 1
        else:
            near = [s for s in stamps if stated and abs((iso(s) - stated).total_seconds()) <= SLACK]
            if not near:
                out.append({"exp": row.get("exp_id"), "problem": "registered_instant_not_corroborated_by_any_output",
                            "instant": str(row.get("started_at") or row.get("finished_at")),
                            "own_generations": stamps[:2], "kind": kind})
    return out


def iso(s: str):
    try:
        return datetime.datetime.fromisoformat((s or "").strip().replace("Z", ""))
    except ValueError:
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=40)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    rows = L.read_any(REC) or []
    kept = L.root_kept()
    sup = L.superseded()
    by_id = {(r.get("exp_id") or "").strip().upper(): r for r in rows}
    bad, checked = [], 0
    kinds = {}
    COVERAGE.clear()
    for r in rows:
        exp = (r.get("exp_id") or "").strip()
        if not exp:
            bad.append({"exp": "?", "problem": "registry_row_without_an_id"})
            continue
        checked += 1
        globs = parts_of(r.get("outputs") or "")
        found = [f for g in globs for f in expand(ROOT, g)]
        bad += timeline(r, found, kinds)
        succ = re.search(r"superseded_by_(EXP-?\d{4})", (r.get("status") or ""), re.I)
        if succ:
            # a row may honestly record a run that left no artefact - an inline console probe - once the claim it
            # carried is re-measured by a promoted script. What then has to hold is that the successor exists and
            # did leave one; the probe row itself is a record, not a run a reader is asked to reproduce.
            target = succ.group(1).upper().replace("EXP", "EXP-").replace("EXP--", "EXP-")
            t = by_id.get(target) or by_id.get(target.replace("-", "")) or {}
            tf = [f for g in parts_of(t.get("outputs") or "") for f in expand(ROOT, g)]
            if not t:
                bad.append({"exp": exp, "problem": "superseded_row_names_a_run_that_is_not_registered",
                            "successor": target})
            elif not tf:
                bad.append({"exp": exp, "problem": "successor_run_has_no_artefact_either", "successor": target,
                            "successor_outputs": (t.get("outputs") or "")[:90]})
            continue
        script = (r.get("script") or "").strip()
        sp, _prose = script_path(script)
        for one in [sp] if sp else []:
            if not (ROOT / one).is_file():
                bad.append({"exp": exp, "problem": "registered_script_not_on_disk", "script": one})
        if not sp:
            bad.append({"exp": exp, "problem": "run_has_no_script_that_can_be_rerun", "script": script[:90]})
        if not found and not globs:
            bad.append({"exp": exp, "problem": "registry_row_names_no_output_glob"})
            continue
        # The kept generation is the newest file the row's own `outputs` glob resolves to that the supersession
        # ledger does not retire; `root_kept()` only knows `EXPnnnn_*` names, which a fifth of the early runs use.
        fresh = [f for f in found if f.name not in sup] or found
        art = max(fresh, key=lambda f: f.stat().st_mtime) if fresh else kept.get(exp)
        if art is None:
            bad.append({"exp": exp, "problem": "no_kept_artefact_for_a_registered_run",
                        "globs": globs[:2], "on_disk": [f.name for f in found[:3]]})
            continue
        if not found:
            bad.append({"exp": exp, "problem": "declared_output_glob_matches_nothing", "globs": globs[:2],
                        "kept": art.name})
        d = L.read_any(art)
        if isinstance(d, dict):
            inside = norm_id(str(d.get("exp_id") or ""))
            # a summary artefact may name the several runs it summarises ("EXP-0121;EXP-0122"); the id is fine
            # when the row's own run is among them
            inside_parts = [norm_id(x) for x in str(d.get("exp_id") or "").split(";") if norm_id(x)]
            # EXP-0006b is the estate's five-seed re-run of EXP-0006: a row id that extends a base id with a
            # letter suffix legitimately holds an artefact whose inside id is the base (class-triaged as not a
            # defect; see ROUND2_PROBLEM_STATUS artefact_files_under_a_different_id|class_triage).
            suffix_ok = re.fullmatch(r"(EXP-\d{4})[A-Z]", norm_id(exp)) and inside == norm_id(
                re.fullmatch(r"(EXP-\d{4})[A-Z]", norm_id(exp)).group(1))
            if inside and inside != norm_id(exp) and norm_id(exp) not in inside_parts and not suffix_ok:
                bad.append({"exp": exp, "problem": "artefact_files_under_a_different_id",
                            "inside": d.get("exp_id"), "artefact": art.name})
            inv = str(d.get("invocation") or "")
            if inv and script and not any(s.strip().split("/")[-1] in inv for s in re.split(r"[;,]", script)
                                          if s.strip()):
                bad.append({"exp": exp, "problem": "recorded_command_line_does_not_name_the_registered_script",
                            "invocation": inv[:150], "script": script[:80]})
            seed_row, seed_art = str(r.get("seed") or ""), d.get("seed")
            if seed_art is not None and seed_row and str(seed_art) not in seed_row and "n/a" not in seed_row:
                bad.append({"exp": exp, "problem": "row_seed_differs_from_the_run", "row": seed_row,
                            "artefact": seed_art})
            st, fi = str(d.get("started_at") or ""), str(d.get("finished_at") or "")
            if st and fi and fi < st:
                bad.append({"exp": exp, "problem": "finished_before_it_started", "started": st, "finished": fi})
        # a package must ship the kept generation, byte for byte, not a retired one. The reference set is every
        # non-retired artefact the row itself declares: a run may write a raw JSON and a processed CSV, and the
        # newest mtime does not decide which of them a package is judged against (the EXP-0032 false positive).
        fresh_json = {f.name for f in fresh if f.suffix == ".json" and (ROOT / "results_raw" / f.name).is_file()}
        prefix = art.name[:11]
        for pkg in L.packages():
            for f in (pkg / "results_raw").glob(prefix + "*.json"):
                if f.name in fresh_json:
                    if h(f) != h(ROOT / "results_raw" / f.name):
                        bad.append({"exp": exp, "problem": "package_copy_differs_from_the_programme_artefact",
                                    "package": pkg.name, "file": f.name,
                                    "pkg_digest": h(f), "root_digest": h(ROOT / "results_raw" / f.name)})
                elif f.name in sup:
                    # Shipping a retired generation beside the kept one is the audit trail the ledger exists for;
                    # shipping one *instead* of the kept generation is the defect.
                    if not any((pkg / "results_raw" / n).is_file() for n in fresh_json):
                        bad.append({"exp": exp, "problem": "package_ships_only_a_superseded_generation",
                                    "package": pkg.name, "superseded_file": f.name,
                                    "kept_file": sorted(fresh_json)[:1]})
    # A generation that no row declares and the ledger does not retire is neither evidence nor audit trail: it is
    # an untracked file a reader cannot interpret. The five `EXP0006_preretrieval_*` generations are the case that
    # prompted this - two runs and three intermediate attempts, all sharing one filename prefix.
    # Two carve-outs, identical to `supersede_undeclared_generations.census`, keep the two tools from disagreeing:
    # a file a package ships is accounted for by definition (its paper points at it), and a file whose filename
    # stem a package ships belongs to the same audit trail.
    declared = {f.name for r in rows for g in parts_of(r.get("outputs") or "") for f in expand(ROOT, g)}
    owners = {}
    for r in rows:
        for g in parts_of(r.get("outputs") or ""):
            for f in expand(ROOT, g):
                owners[f.name] = r["exp_id"]
    shipped = set()
    for pkg in L.packages():
        for sub in ("results_raw", "results_processed"):
            d = pkg / sub
            if d.is_dir():
                shipped.update(f.name for f in d.iterdir() if f.is_file())
    shipped_stems = {C.stem_of(n) for n in shipped}
    for f in sorted((ROOT / "results_raw").glob("EXP0*.json")) + sorted((ROOT / "results_processed").glob("EXP0*.csv")):
        if f.name in declared or f.name in sup:
            continue
        if f.name in shipped or C.stem_of(f.name) in shipped_stems:
            continue
        bad.append({"exp": owners.get(f.name, "?"), "problem": "artefact_generation_no_registry_row_declares",
                    "file": str(f.relative_to(ROOT)).replace(chr(92), "/"),
                    "same_prefix_as": sorted({o for n, o in owners.items() if n[:11] == f.name[:11]})[:3]})
    # One path declared by two runs can only be one run's bytes. `analyze_routing_failure.py` names its table after
    # its own experiment id, so the 3-seed and the 5-seed ladder both declare it and the later run overwrote the
    # earlier; that pair is in the supersession ledger as "kept, not citable", which is the estate's answer. Most
    # other shared names are programme documents several runs legitimately update in place - `topic_registry.csv`,
    # `package_audit.json`, the register itself - and a maintenance run's effect on them *is* its output, verifiable
    # in the file and described in the row's own notes. So this reports the shape rather than calling it a defect:
    # every name several rows declare, and which rows leave nothing but such a name. A run whose evidence a package
    # actually cites is covered by `missing_copies` and `cited_artefact_not_in_package`, where a reader's inability
    # to open it is the finding.
    shared, per_row = {}, {}
    for r in rows:
        exact, anyf = [], []
        for g in parts_of(r.get("outputs") or ""):
            g = g.strip().lstrip(">").strip().replace(chr(92), "/")
            if not g:
                continue
            if "*" in g or "?" in g:
                anyf += [f.name for f in expand(ROOT, g)]
                continue                    # a wildcard is a family claim, not a claim about one shared file
            p = ROOT / g
            if p.is_file():
                anyf.append(p.name)
                exact.append(p.name)
                shared.setdefault(p.name, []).append((r.get("exp_id") or "").strip())
        per_row[(r.get("exp_id") or "").strip()] = (exact, anyf)
    # second pass, because whether a name is shared is only known once every row has been read
    shared_names = {n: sorted(set(o)) for n, o in sorted(shared.items()) if len(set(o)) > 1 and n not in sup}
    only_shared = sorted(e for e, (exact, anyf) in per_row.items()
                         if exact and not [n for n in anyf if n not in shared_names])
    by = {}
    for x in bad:
        by[x["problem"]] = by.get(x["problem"], 0) + 1
    for x in bad[:a.limit]:
        print(json.dumps(x, ensure_ascii=False)[:210])
    print(f"\n{checked} registry row(s) checked; {len(bad)} finding(s)")
    print("registry time claims (window_kind): " + json.dumps(kinds, sort_keys=True)
          + " untested: " + json.dumps(dict(COVERAGE), sort_keys=True))
    print(f"{len(shared_names)} output path(s) declared by more than one row; "
          f"{len(only_shared)} row(s) declare nothing but such a path: {only_shared[:8]}")
    print(json.dumps(by, indent=1))
    dest = ROOT / "results_raw" / f"ROUND2_RUN_REALITY_{time.strftime('%Y%m%dT%H%M%S')}.json"
    scored = sum(v for k, v in kinds.items() if k in ("measured", "instant_recorded", "output_stamp"))
    dest.write_text(json.dumps({"detector": "round2_run_reality", "rows_checked": checked,
                                "window_kinds": kinds, "timeline_rows_scored": scored,
                                "timeline_untested": dict(COVERAGE),
                                "shared_path_declarations": shared_names,
                                "runs_declaring_only_a_shared_file": only_shared,
                                "totals": by, "detail": bad,
                                "at": datetime.datetime.now().isoformat(timespec="seconds")},
                               indent=1, ensure_ascii=False), encoding="utf-8")
    print("wrote", dest.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
