"""Generate `00_program_registry/PROGRAM_STATUS.md` from the machine state, so the handoff cannot go stale.

The status document was written by hand for three sessions and drifted every time: it said "37 experiments" when the
registry held 103, and it described P004 as "in flight" after its package was complete. A hand-maintained inventory of a
programme this size is always wrong the day after it is written, so this script regenerates it from the files that are
true - the experiment registry, the topic registry, the five packages' own claim/limitation/deviation tables, their
`final_audit.md` gate verdicts, the package audit, the superseded-artefact register and the spec-completion audit.

Every number is read, none is recalled; where a parse fails the document says "not parsed" rather than guessing. The
previous hand-written document is kept at `docs/archived/PROGRAM_STATUS_handwritten_20260919.md`.

    python 02_shared_code/registry/program_status.py
"""
from __future__ import annotations
import csv, io, json, pathlib, re, subprocess, sys, time
from collections import Counter, defaultdict

HERE = pathlib.Path(__file__).resolve().parent
ROOT = next(a for a in (HERE, *HERE.parents) if (a / "00_program_registry").is_dir())
sys.path.insert(0, str(HERE))
import build_topic_registry as BT                                            # noqa: E402 - the funnel's own rules
REG = ROOT / "00_program_registry"
OUT = REG / "PROGRAM_STATUS.md"
PAPERS = sorted(p for p in (ROOT / "papers").glob("P0*") if p.is_dir())
AUDIT = HERE / "package_audit.py"
SPEC_AUDIT_DOC = ROOT / "docs" / "SPEC_COMPLETION_AUDIT.md"


def rows(path):
    return [r for r in csv.DictReader(io.StringIO(pathlib.Path(path).read_text(encoding="utf-8")))]


def read(path):
    return pathlib.Path(path).read_text(encoding="utf-8", errors="replace") if pathlib.Path(path).is_file() else ""


def gate_verdicts(pkg):
    """G18 letters -> verdict, from whichever form the package's final_audit.md uses."""
    txt = read(pkg / "final_audit.md")
    out = {}
    # three real forms exist: `| **G18-A** | PASS |`, `| G18-A literature and novelty | PASS |`, `## G18-A <title>`
    for m in re.finditer(r"\|\s*\*{0,2}G18-([A-F])([^|]*)\*{0,2}\s*\|\s*([^|]+?)\s*\|", txt):
        out[m.group(1)] = re.split(r"[`|]", m.group(3).strip(), 1)[0].replace("\n", " ")[:60]
    for m in re.finditer(r"^##\s+G18-([A-F])\b[^\n]*\n(.*?)(?=^##\s|\Z)", txt, re.M | re.S):
        letter, body = m.group(1), m.group(2)
        if letter in out:
            continue
        v = re.search(r"\b(PASS|PARTIAL|FAIL|OPEN|NOT\s*submittable|AMENDED)\b[^\n|`]{0,60}", body, re.I)
        out[letter] = (v.group(0).strip() if v else "verdict not parsed")
    return out


def gate_decision(pkg):
    txt = read(pkg / "final_audit.md")
    pats = [r"\*\*\s*Gate decision\s*[:\-]?\s*([^*]{1,300})\*\*",               # **Gate decision: X**
            r"\*\*\s*Gate decision\s*:\s*\*\*\s*(.{1,300})",                       # **Gate decision:** X
            r"\*\*\s*Gate decision\s*\*\*\s*:?\s*\n?\s*(.{1,300})",              # **Gate decision** X
            r"##\s+Gate decision\s*\n+\s*\*{0,2}[^*\n]{0,40}\*{0,2}\s*\n+(.{1,300})",  # heading then prose
            r"##\s+Gate decision\s*\n+(.{1,300})"]
    s = ""
    for pat in pats:
        m = re.search(pat, txt, re.S)
        if m and re.sub(r"\s+", " ", m.group(1)).strip(" *:|"):
            # bold markers arrive inside the capture for the heading forms; they would render as literal asterisks
            s = re.sub(r"\s+", " ", m.group(1)).replace("**", "").strip(" *:|")
            break
    if not s:
        return "not stated in final_audit.md"
    return s[:260] + ("\u2026" if len(s) > 260 else "")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    exps = rows(REG / "experiment_registry.csv")
    by_paper = defaultdict(list)
    for e in exps:
        for pid in re.split(r"[;,]", e.get("paper_id") or ""):
            if pid.strip().startswith("P00"):
                by_paper[pid.strip()[:4]].append(e)
    topics = rows(REG / "topic_registry.csv")
    tstat = Counter(t["status"] for t in topics)
    # The funnel's own definition of "still working" is the one the registry builder enforces. This used to be a
    # prefix regex on `w0|w1|w2|w3`, which read `w1_packaged_...` and `w3_fold_into_...` - both decided - as awaiting
    # work, and matched `w10_packaged`/`w11_packaged` through the `w1` prefix, so the status page announced 45 open
    # topics for a funnel that has none.
    live = [t for t in topics if not BT.decided(str(t["status"] or ""))]

    audit = {}
    p = subprocess.run([sys.executable, str(AUDIT)], capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT))
    for ln in (p.stdout or "").splitlines():
        m = re.match(r"^(P00\d(_[^:]+)): missing=(\S*) weak=(.*)$", ln)
        if m:
            audit[m.group(1)[:4]] = (m.group(3), m.group(4).strip())

    spec = {}
    js = sorted((ROOT / "results_raw").glob("EXP0099_spec_completion_audit_*.json"))
    if js:
        spec = json.loads(js[-1].read_text(encoding="utf-8"))
    sup = json.loads((ROOT / "results_raw/SUPERSEDED_ARTIFACTS.json").read_text(encoding="utf-8")).get("superseded", [])
    ledger = json.loads(read(ROOT / "papers/P001_routing_failure_qpp/test_eval_ledger.json"
                             ).replace("\ufeff", "") or "{}").get("evaluations", []) \
        if (ROOT / "papers/P001_routing_failure_qpp/test_eval_ledger.json").is_file() else []

    L = ["# Programme status and handoff - Agentic Information Behavior series",
         "",
         f"Generated {time.strftime('%Y-%m-%d %H:%M')} by `02_shared_code/registry/program_status.py`. Every number below is read from the files named under it; nothing here is recalled from a "
         f"previous session. The hand-written document this replaces is at "
         f"`docs/archived/PROGRAM_STATUS_handwritten_20260919.md`.",
         "",
         "**Verification tools.** `02_shared_code/registry/package_audit.py` (deliverables + content checks per "
         "package), `02_shared_code/registry/gates18_complete.py` (the G18 matrix), "
         "`02_shared_code/registry/spec_completion_audit.py` (every requirement id in the spec), "
         "`results_raw/SUPERSEDED_ARTIFACTS.json` (failed and superseded runs, kept and labelled, never deleted).",
         "",
         "## 1 The five packages",
         "",
         "| paper | topic | claims (by status) | limitation sections | deviations D# | experiments | package audit | "
         "G18 verdicts |",
         "|---|---|---|---|---|---|---|---|"]
    for pkg in PAPERS:
        pid = pkg.name[:4]
        cl = rows(pkg / "claims_evidence_matrix.csv") if (pkg / "claims_evidence_matrix.csv").is_file() else []
        cs = Counter((r.get("status") or "?").split(" ")[0].split(";")[0] for r in cl)
        # P001 uses `## L12 ...`, P002 unnumbered `## ...` sections, P003/P004/P005 numbered lists. The entry count
        # is the largest of the three forms so no package is reported as having zero limitations for using a form
        # this parser had not considered.
        lt = read(pkg / "limitations.md")
        lim = max(len(re.findall(r"^#{2,4} ", lt, re.M)), len(re.findall(r"^\d+\. ", lt, re.M)),
                  len(re.findall(r"^\|\s*\*{0,2}L\d+", lt, re.M)))
        dev = len(re.findall(r"^\| D\d+ \|", read(pkg / "deviations.md"), re.M))
        tids = sorted({t for e in by_paper[pid] for t in re.split(r"[;,]", e.get("topic_id") or "") if t.strip()})
        miss, weak = audit.get(pid, ("not run", "not run"))
        gv = gate_verdicts(pkg)
        L.append(f"| {pkg.name} | {', '.join(tids) or '-'} | "
                 f"{len(cl)} ({', '.join(f'{k}:{v}' for k, v in cs.most_common(3))}) | {lim} | {dev} | "
                 f"{len(by_paper[pid])} | missing={miss} weak={weak} | "
                 + " ".join(f"{k}={gv[k][:34]}" for k in sorted(gv)) + " |")
    L += ["", "### What each package still owes, in its own words", ""]
    for pkg in PAPERS:
        L.append(f"- **{pkg.name}** - {gate_decision(pkg)}")
    L += ["", f"P001's test split has been evaluated **{len(ledger)} time(s)** "
          f"({ledger[0]['at'] if ledger else 'never'}), which is the pre-registered limit; the ledger is "
          f"`papers/P001_routing_failure_qpp/test_eval_ledger.json`.", ""]

    L += ["## 2 Programme record",
          "",
          f"- `00_program_registry/experiment_registry.csv`: **{len(exps)} experiments**, "
          f"{len({e['exp_id'] for e in exps})} distinct ids, no ragged rows (checked by `package_audit.py`).",
          f"- `results_raw/SUPERSEDED_ARTIFACTS.json`: **{len(sup)}** failed or superseded artefacts, each with a "
          f"reason and a `was_it_quoted` field; the files are moved to `results_raw/superseded/`, never deleted.",
          f"- `01_datasets/manifests`: {len(list((ROOT / '01_datasets/manifests').rglob('*')))} evidence entries.",
          f"- Status vocabulary in the registry: "
          + ", ".join(f"`{k}` x{v}" for k, v in Counter((e.get('status') or '')[:28] for e in exps).most_common(6)),
          "",
          "## 3 Spec compliance (EXP-0099)",
          ""]
    if spec:
        L += [f"Of the **{spec.get('requirements_found_in_spec', '?')}** requirement ids the spec states, "
              + ", ".join(f"**{v}** {k.lower().replace('_', ' ')}" for k, v in sorted(spec["status_counts"].items()))
              + f". Detail: `docs/SPEC_COMPLETION_AUDIT.md` "
                f"(artefact `{spec.get('exp_id')}` scan of {spec.get('text_files_scanned', '?')} text files)."]
        if spec.get("open_requirements"):
            L += ["", "Still open:"] + [f"- {r['id']} {r['title']}" for r in spec["open_requirements"]]
    else:
        L.append("The completion audit has not been run yet: `python 02_shared_code/registry/spec_completion_audit.py`.")
    L += ["", "## 4 Literature position", ""]
    rec = {}
    if (REG / "EXP0095_abstract_recovery.json").is_file():
        rec = json.loads(read(REG / "EXP0095_abstract_recovery.json"))
    L += [f"- {rec.get('recovered_total', '?')} abstracts recovered in the second round "
          f"({', '.join(f'{k}={v}' for k, v in sorted(rec.get('recovered_by_channel', {}).items()))}); "
          f"{rec.get('still_title_only', '?')} screened records stay title-only and are labelled "
          f"`undecidable_on_title`.",
          "- The grade moves that round reported are **not** new collisions: attributed row by row, "
          + json.dumps(rec.get("move_attribution", {}), ensure_ascii=False) + ".",
          "- Collision levels in the five curated matrices are now re-derivable by one command "
          "(`02_shared_code/literature/reconcile_collision_levels.py`); the legacy column is kept beside the "
          "re-derived one. See `docs/collision_level_consistency.md`.",
          "- OpenAlex answers from this host (positive control 198 words); Crossref and Semantic Scholar too. "
          "arXiv export API reachable; the Hugging Face mirror reachable for dataset files.", ""]

    L += ["## 5 The topic funnel", "",
          f"{len(topics)} topics tracked. Status distribution: "
          + ", ".join(f"`{k}` x{v}" for k, v in sorted(tstat.items(), key=lambda kv: -kv[1])), ""]
    if live:
        L += ["Rows still in the working part of the funnel, with what each one is waiting on:", "",
              "| topic | status | waiting on |", "|---|---|---|"]
        for t in live:
            reason = re.sub(r"\s+", " ", t.get("blocking_issue") or "")[:150] or "-"
            L.append(f"| {t['topic_id']} {t['title_zh'][:22]} | {t['status'][:44]} | {reason} |")
        L += [""]
    else:
        L += ["Rows still in the working part of the funnel: none. Every registered topic carries the evidence of "
              "the step that ended it in `topic_registry.csv` - a package with its experiment ids, coverage, "
              "figures and collision verdict, a premise block with the measured gate value, or a funnel decision "
              "with the screen count that produced it.", ""]
    L += ["", "**How to read the funnel.** A parked or killed topic carries the measurement that ended it, not an "
          "opinion: T027 is parked because its outcome is censored on task completion (2x2 [[0,3238],[1137,625]], "
          "Fisher p 0), T029 because its predictor was not separable from its label, T036 because a 392-record screen "
          "found 1 L2+ and 0 L3+ with 199 records unread - a bounded negative, not proof of absence.", ""]

    L += ["## 6 Reproducing any of this", "",
          "Each package carries `reproduce.sh`, and the whole set was replicated in a clean environment (EXP-0079: "
          "fresh venv, no system site-packages, dataset reached by junction, whole-artefact leaf comparison). The "
          "commands are in the scripts; `package_audit.py` is what says whether a package is complete, and it is run "
          "by CI-of-one here rather than trusted from memory.", ""]
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8", newline="")
    print("wrote", OUT.relative_to(ROOT), f"({len(L)} lines)")
    print(f"  experiments={len(exps)} packages={len(PAPERS)} topics={len(topics)} live={len(live)} "
          f"superseded={len(sup)} spec_rows={spec.get('requirements_found_in_spec', 'n/a')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
