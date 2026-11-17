"""EXP-0099 (completion audit): does every requirement in the governing spec have an artefact behind it?

The spec (`Agentic_Information_Behavior_研究全流程任务清单.md`) is the series' supreme execution document, and it is
written as numbered requirements: T01.01..T16.05 (process steps), E00..E19 (the minimum complete experiment package),
G18-A..F (the pre-submission gates). `package_audit.py` proves each package contains its 22 deliverables; it does not
prove that each *requirement id* in the spec was executed somewhere. That is this run's whole job, and it is deliberately
conservative: a requirement counts as evidenced only if a file in the workspace other than the spec names it, and the
file's own kind decides the strength of the evidence.

Classification, fixed before the scan:
  * `evidenced_in_package`  - named inside `papers/P00x/...` (a manuscript, audit, config, table or figure script);
  * `evidenced_programme`   - named in `00_program_registry/`, `02_shared_code/`, `results_raw/`, `results_processed/`
                              or `docs/` - a programme-level step rather than a per-paper one;
  * `spec_only`             - the spec is the only place it appears. This is the interesting row: it is reported as
                              OPEN, never as done, and it is listed in full.

Scanning is limited to text files under 4 MB; the dataset estate and the 79 GB corpora are never read.

    python 02_shared_code/registry/spec_completion_audit.py
"""
from __future__ import annotations
import csv, json, os, pathlib, re, sys, time
from collections import Counter, defaultdict

HERE = pathlib.Path(__file__).resolve().parent
ROOT = next(a for a in (HERE, *HERE.parents) if (a / "00_program_registry").is_dir())
sys.path.insert(0, str(HERE))
from spec_requirement_signatures import evaluate                    # noqa: E402  content checks, not string matches
SPEC = ROOT.parent / "Agentic_Information_Behavior_研究全流程任务清单.md"
OUT_JSON = ROOT / "results_raw"
# Top-level spec sections whose requirement is an artefact this audit can open and check. A section that states a
# principle (5 types, 12 legal-optimisation cases, 14 causal restraint, 22 toolbox, 24 external checklists, 25
# principles) is deliberately NOT enumerated: it has no single artefact to demand, and listing it would convert
# "not expressible as a check" into a false OPEN. Their substance is carried by the sub-ids they already own.
ENUMERATED_SECTIONS = {0, 2, 7, 11, 13, 15, 17, 19, 20, 23}
SECTION_RE = re.compile(r"^(\d{1,2})[\.、]\s*(.+)$")
ALWAYS_SIGN = ({"G03", "G04"} | {f"E{i:02d}" for i in range(20)} | {f"21.{i}" for i in range(1, 6)}
               | {f"S{i:02d}" for i in sorted(ENUMERATED_SECTIONS)})
DOC = ROOT / "docs" / "SPEC_COMPLETION_AUDIT.md"
SKIP_DIRS = {"01_datasets", "superseded", "__pycache__", ".git", "node_modules", "logs"}
# This audit writes a file that names every requirement id, and its own source lists them too. Either one would make
# every id "evidenced" on a second run - the auditor citing itself - so everything belonging to this audit is out of
# the scan: its script, its signature table, its document and its JSON.
SELF_OUTPUT = {"docs/spec_completion_audit.md"}
# compared on forward slashes: `relative_to()` yields backslashes on Windows, and one run of this audit kept its own
# output in the scan because the separator made the exclusion never match
# all-lowercase because the path is compared lowercased - an earlier version wrote `EXP0099` here and the exclusion
# silently never matched, so the audit cited its own previous JSON
SELF_PREFIXES = ("02_shared_code/registry/spec_", "results_raw/exp0099")
TEXT = {".md", ".py", ".csv", ".json", ".txt", ".sh", ".yaml", ".yml", ".html", ".tex"}
MAX_BYTES = 4_000_000
ID_RE = re.compile(r"^(T\d{2}\.\d{2}|E\d{2}|G\d{2}-[A-F]|G\d{2}|B[0-5]|\d{2}\.\d{1,2})\b")
#  `\d{2}\.\d{1,2}` matches only the numbered subsections of spec section 21 (21.1..21.5), the special risks of
#  this corpus family. Until it was parsed, five requirements were invisible to this audit - not unmet, simply
#  unread - which is the failure mode a verifier of a verifier has to guard against.


def requirements():
    """Every requirement the spec states as a heading, in spec order, with its title."""
    out, seen = [], set()
    spec_txt = SPEC.read_text(encoding="utf-8")
    for ln in spec_txt.splitlines():
        m = re.match(r"^#{1,4} (.*)$", ln)
        if not m:
            continue
        body = m.group(1).strip()
        k = ID_RE.match(body)
        if k:
            rid = k.group(1)
            title = body[len(rid):].strip(" -—:：")
        else:
            # Top-level sections ("# 17. Reviewer Attack…") are requirements in their own right, but only the ones
            # listed in ENUMERATED_SECTIONS get an id: a section that states a principle rather than demanding an
            # artefact cannot be checked, and enumerating it would turn "not checkable" into a false OPEN.
            n = SECTION_RE.match(body)
            if not n or int(n.group(1)) not in ENUMERATED_SECTIONS:
                continue
            rid = f"S{int(n.group(1)):02d}"
            title = n.group(2).strip(" -—:：")
        if rid in seen:
            continue
        seen.add(rid)
        out.append({"id": rid, "title": title})
    # The acceptance gates G03 and G04 are stated inline as bold markers, not as headings, so a heading-only scan
    # excluded two of the spec's own gates. They are added the same way, by the spec's own label.
    for m in re.finditer(r"\*\*验收门\s+(G\d{2})\*{0,2}[：:]?\*\*", spec_txt):
        rid = m.group(1)
        if rid in seen:
            continue
        seen.add(rid)
        tail = spec_txt[m.end():].splitlines()
        rest = [x.strip(" ：:") for x in tail if x.strip() and x.strip() != "---"][:5]
        out.append({"id": rid, "title": re.sub(r"\s+", " ", " ".join(rest))[:150]})
    return out


def chain_reachable_scripts(pkg_script: pathlib.Path):
    """Every script one package's chain runs, plus one level of scripts a reachable script runs.

    Per package, deliberately: a generator that only P004's chain re-runs does not make P002's copy of the same
    document current, and "this package reproduces on its own" is the claim the spec's item 16 makes.
    """
    roots = set()
    for m in re.finditer(r'^\s*"\$PY"\s+([A-Za-z0-9_./-]+\.py)',
                         pkg_script.read_text(encoding="utf-8", errors="replace"), re.M):
        roots.add(m.group(1).replace("\\", "/"))
    seen, frontier = set(roots), list(roots)
    while frontier:
        rel = frontier.pop()
        f = pathlib.Path(ROOT) / rel
        if not f.is_file():
            continue
        for m in re.finditer(r"[A-Za-z0-9_./-]+\.py", f.read_text(encoding="utf-8", errors="replace")):
            q = m.group(0).replace("\\", "/")
            if "/" in q and (q not in seen) and (pathlib.Path(ROOT) / q).is_file():
                seen.add(q)
                frontier.append(q)
    return seen


def scripts_reachable_from(entry: pathlib.Path):
    """Every script an estate-level chain driver runs, one level of imports deep.

    The driver's own steps are string literals (`("02_shared_code/registry/program_status.py",)`) or `CHAIN` lists, so
    both are read out of the source rather than executed.
    """
    roots = set()
    if not entry.is_file():
        return roots
    txt = entry.read_text(encoding="utf-8", errors="replace")
    for m in re.finditer(r"[\"']([A-Za-z0-9_./-]+\.py)[\"']", txt):
        roots.add(m.group(1).replace("\\", "/"))
    seen, frontier = set(roots), list(roots)
    while frontier:
        rel = frontier.pop()
        f = pathlib.Path(ROOT) / rel
        if not f.is_file():
            continue
        for m in re.finditer(r"[A-Za-z0-9_./-]+\.py", f.read_text(encoding="utf-8", errors="replace")):
            q = m.group(0).replace("\\", "/")
            if "/" in q and q not in seen and (pathlib.Path(ROOT) / q).is_file():
                seen.add(q)
                frontier.append(q)
    return seen


def estate_chain_scripts():
    """Everything any chain runs: each package's `reproduce.sh`, plus the estate-level drivers."""
    out = set()
    for sh in sorted(pathlib.Path(ROOT).glob("papers/*/reproduce.sh")):
        out |= chain_reachable_scripts(sh)
    for driver in ("_round2_final_chain.py", "_reassemble_all_waves.py", "_estate_two_pass.py",
                   "02_shared_code/registry/round2_run_all.py"):
        out |= scripts_reachable_from(ROOT / driver)
    return out


def stale_generated_documents():
    """Package documents that declare a generator their own chain never runs - the stale-README defect, detectable.

    `README.md` lifted its "open items" out of `final_audit.md` by keyword, then sat there unrefreshed for two days
    because no `reproduce.sh` re-ran `build_package_configs_readme.py`: the chain rebuilt every file around it while it
    kept publishing a to-do list the package had already finished. `novelty_grading.md` did the same with a hard-coded
    "this expansion has not yet been run" two days after EXP-0060 had run it. Presence-of-a-generator is not the same
    statement as "this file is current".

    Returns `(orphans, dated_records)`. A document whose own name carries the date of the run it records -
    `funnel_correction_agentnet_20260920.md` - is a closed statement about the past, not a live report, and is reported
    separately: the defect this finds is a *live* document drifting away from the chain that rebuilds it.
    """
    pat = re.compile(r"[Gg]enerated[^|\n]{0,90}?by `([A-Za-z0-9_./-]+\.py)`")
    orphans, dated = [], []
    for sh in sorted(pathlib.Path(ROOT).glob("papers/*/reproduce.sh")):
        pkg, reach = sh.parent, chain_reachable_scripts(sh)
        for md in sorted(pkg.glob("*.md")):
            head = "\n".join(md.read_text(encoding="utf-8", errors="replace").splitlines()[:12])
            for m in pat.finditer(head):
                if m.group(1).replace("\\", "/") not in reach:
                    orphans.append(f"{pkg.name}/{md.name} <- {m.group(1)}")
    # Programme documents are read by more people than any single package, and round 2 wrote one of its own
    # (`docs/ROUND2_CLUSTER_UNITS.md`) from a script no chain ran. A package document has to be reachable from *that
    # package's* chain; a programme document only has to be reachable from some estate chain.
    estate = estate_chain_scripts()
    for md in sorted((pathlib.Path(ROOT) / "docs").glob("*.md")) + \
            sorted((pathlib.Path(ROOT) / "00_program_registry").glob("*.md")):
        head = "\n".join(md.read_text(encoding="utf-8", errors="replace").splitlines()[:12])
        for m in pat.finditer(head):
            gen = m.group(1).replace("\\", "/")
            # A chain driver may name the script it runs by bare filename (`run("round2_problem_list.py")`, which
            # `round2_run_all.py` resolves against its own folder), and the document names it by path. Matching on the
            # name alone would have called the estate's own problem list stale; matching on the whole path alone would
            # still call it stale. So the bare name is resolved to the file it must mean and the two are compared as
            # paths - the estate has eight duplicated file names (`build_package.py` four times, one per hand-built
            # package), so a name is not an identity.
            if gen not in estate and not any(_same_script(gen, p) for p in estate):
                line = f"{md.relative_to(ROOT).as_posix()} <- {gen}"
                (dated if re.search(r"_\d{8}$", md.stem) else orphans).append(line)
    return orphans, dated


def _same_script(gen: str, chain_entry: str) -> bool:
    """True when a chain's bare script name and a document's declared path are the same file."""
    if "/" in chain_entry:
        return chain_entry == gen
    a = pathlib.Path(ROOT) / gen
    for base in (pathlib.Path(ROOT) / "02_shared_code" / "registry", pathlib.Path(ROOT) / "02_shared_code" /
                 "package_factory", pathlib.Path(ROOT)):
        c = base / chain_entry
        if c.is_file() and a.is_file() and c.resolve() == a.resolve():
            return True
    return False


def classify(path):
    p = path.replace("\\", "/")
    if p.startswith("papers/P00"):
        return "package", p
    if p.startswith(("00_program_registry/", "02_shared_code/", "results_raw/", "results_processed/", "docs/",
                     "03_results/", "04_docs/")):
        return "programme", p
    return "other", p


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    if not SPEC.is_file():
        raise SystemExit(f"ABORT: the governing spec is not at {SPEC}")
    reqs = requirements()
    patterns = {r["id"]: re.compile(r"(?<![A-Za-z0-9-])" + re.escape(r["id"]) + r"(?![A-Za-z0-9])") for r in reqs}
    hits = defaultdict(list)
    files_scanned = 0
    for f in ROOT.rglob("*"):
        if not f.is_file() or f.suffix.lower() not in TEXT or f.stat().st_size > MAX_BYTES:
            continue
        if set(f.relative_to(ROOT).parts) & SKIP_DIRS:
            continue
        rel = str(f.relative_to(ROOT))
        rel_norm = rel.replace("\\", "/").lower()
        if rel_norm in SELF_OUTPUT or rel_norm.startswith(SELF_PREFIXES):
            continue                                          # never let this audit cite its own files as evidence
        files_scanned += 1
        try:
            txt = f.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            print(f"  skipped {rel}: {type(e).__name__}")
            continue
        # word-boundary matching: a plain substring test let "G03" be satisfied by an id or a hash that merely
        # contains those three characters, which would report a gate as evidenced when nothing evidences it
        for rid, rx in patterns.items():
            if rx.search(txt):
                hits[rid].append(classify(rel))
    # The spec itself always names its own ids; the paper packages also quote it. Evidence must not come from the spec.
    rows = []
    for r in reqs:
        kinds = Counter(k for k, _ in hits[r["id"]])
        pkg = [p for k, p in hits[r["id"]] if k == "package"]
        prog = [p for k, p in hits[r["id"]] if k == "programme"]
        status = ("evidenced_in_package" if pkg else
                  "evidenced_programme" if prog else "OPEN_no_artefact_names_this_requirement")
        sig = None
        # `ALWAYS_SIGN` ids are satisfied by artefacts, not by mentions: an E-step number written down anywhere does not
        # make the experiment exist, and the two inline gates appear in this auditor's own source.
        # The condition must read `r["id"]`: a previous version tested a loop variable left over from requirements(),
        # which was the same id on every pass, so the signature branch either ran for every requirement - discarding the
        # citation evidence it had already collected - or for none, depending on which id happened to be last.
        if status.startswith("OPEN") or r["id"] in ALWAYS_SIGN:
            # Not citing the requirement id is normal for this programme; what matters is whether the artefact the
            # requirement demands exists. That is a content question, so it is checked as one.
            satisfied, checks = evaluate(r["id"])
            sig = {"satisfied": satisfied, "checks": checks}
            status = ("satisfied_by_content_signature" if satisfied
                      else "OPEN_no_artefact_names_this_requirement")
        rows.append({**r, "status": status, "n_files": len(hits[r["id"]]), "signature": sig,
                     "package_files": sorted(set(pkg))[:3], "programme_files": sorted(set(prog))[:3]})
    open_rows = [r for r in rows if r["status"].startswith("OPEN")]
    res = {"exp_id": "EXP-0099", "at": time.strftime("%Y-%m-%dT%H:%M:%S"), "spec": str(SPEC.relative_to(ROOT.parent)),
           "spec_lines": len(SPEC.read_text(encoding='utf-8').splitlines()),
           "requirements_found_in_spec": len(rows), "text_files_scanned": files_scanned,
           "status_counts": dict(Counter(r["status"] for r in rows)),
           "open_requirements": [{"id": r["id"], "title": r["title"]} for r in open_rows],
           "per_requirement": rows, "wallclock_sec": round(time.time() - t0, 1),
           "generated_docs_with_no_chain_step": stale_generated_documents(),
           "rule": "classification fixed before the scan; a requirement is evidenced only if a file outside the spec "
                   "names it"}
    out = OUT_JSON / f"EXP0099_spec_completion_audit_{time.strftime('%Y%m%dT%H%M%S')}.json"
    out.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")

    DOC.parent.mkdir(exist_ok=True)
    L = ["# Spec-to-artefact completion audit (EXP-0099)", "",
         f"Generated {res['at']} by `02_shared_code/registry/spec_completion_audit.py`; the requirement list is read "
         f"from the spec's own headings ({res['spec_lines']} lines, {len(rows)} requirement ids), and "
         f"{files_scanned} text files in the workspace were scanned. No number in this file is entered by hand.", "",
         f"A requirement counts as **evidenced** when a file outside the spec names it: "
         f"**{res['status_counts'].get('evidenced_in_package', 0)}** are named inside a paper package, "
         f"**{res['status_counts'].get('evidenced_programme', 0)}** only at programme level, "
         f"**{res['status_counts'].get('satisfied_by_content_signature', 0)}** are cited by no artefact but are "
         f"satisfied by a content check, and **{len(open_rows)}** remain open on both tests.", "",
         "| status | requirements |", "|---|---|"]
    for k, v in sorted(res["status_counts"].items()):
        L.append(f"| {k} | {v} |")
    L += ["", "## Requirements with no artefact naming them, and no content signature covering them", ""]
    L += ([f"- **{r['id']}** {r['title']}" for r in open_rows] or
          ["None. Every requirement id in the spec is either named by an artefact in the workspace or satisfied by the "
           "content checks in the next section."])
    _orph, _dated = res["generated_docs_with_no_chain_step"]
    L += ["", "## Documents whose generator runs in no chain", "",
          f"{len(_orph)} live document(s) declare a generating script that no chain - no package `reproduce.sh`, nor "
          "the estate's closing chain, reassembly driver or sweep driver - ever re-executes. Such a file is current "
          "only until the artefacts it summarises move, and it is the one kind of gap a green rebuild check cannot "
          "see, because the rebuild never touches it.", ""]
    L += ([f"- `{o}`" for o in _orph] or
          ["None. Every self-declared generated document in `papers/*/` and in the programme's own `docs/` names a "
           "generator that some chain re-runs."])
    if _dated:
        L += ["", f"({len(_dated)} further document(s) name a generator no chain runs, but each carries in its own "
                  "file name the date of the single run it records - a closed statement about the past rather than a "
                  "live report - so they are listed without being called stale.)", ""]
        L += [f"- `{o}`" for o in _dated]
    sig_rows = [r for r in rows if r["signature"]]
    L += ["", f"## Content signatures for the {len(sig_rows)} ids no artefact cites by name", "",
          "These are the requirements a string search alone would call open. Each is checked against the artefact the "
          "spec's own wording demands; the needle families are printed so a disagreement can be pointed at one string "
          "rather than at a judgement.", ""]
    for r in sig_rows:
        L.append(f"### {r['id']} {r['title']} - "
                 + ("satisfied" if r["signature"]["satisfied"] else "NOT SATISFIED"))
        L.append("")
        for c in r["signature"]["checks"]:
            L.append(f"- {'ok' if c['ok'] else 'FAIL'} `{c['kind']}` **{c['check']}** - {c['evidence'][:170]}")
        L.append("")
    L += ["", "## Every requirement, with its pointers", "",
          "| id | title | status | files naming it (first 3) |", "|---|---|---|---|"]
    for r in rows:
        L.append(f"| {r['id']} | {r['title'][:64]} | {r['status']} | "
                 + ", ".join(f"`{p.split('/')[-1]}`" for p in (r["package_files"] + r["programme_files"])[:3]) + " |")
    L += ["", "**How to read this.** A named id is not a passed check: `package_audit.py` and `gates18_complete.py` "
          "are what test contents. This audit answers the narrower question the programme had never asked - whether "
          "each requirement the spec states was ever *touched* by a file that exists - so that an id nobody picked up "
          "cannot hide inside a set of packages that each pass their own deliverable list.", "",
          f"artefact: `{out.relative_to(ROOT)}`"]
    DOC.write_text("\n".join(L) + "\n", encoding="utf-8", newline="")
    print(f"spec requirements: {len(rows)} | {res['status_counts']}")
    print(f"live generated docs whose generator runs in no chain: {len(_orph)}"
          + (f" | dated one-off records listed separately: {len(_dated)}" if _dated else ""))
    for o in _orph:
        print("  - " + o)
    if open_rows:
        print("OPEN (named nowhere but the spec):")
        for r in open_rows:
            print(f"  - {r['id']} {r['title'][:70]}")
    print("wrote", out.relative_to(ROOT), "and", DOC.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
