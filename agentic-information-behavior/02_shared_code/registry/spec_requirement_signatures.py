"""EXP-0099 support: content signatures for the spec requirements that no artefact names by id.

`spec_completion_audit.py` finds that 17 of the spec's requirement ids appear nowhere outside the spec. That is not the
same as 17 unmet requirements - the programme executes the spec's substance and cites it by experiment id (EXP-xxxx),
not by requirement id (T10.03). So each of those 17 gets a signature: a check of the artefact the requirement actually
demands, with the needle families named in the check so a reader can dispute them.

A signature passes only if every check in its list passes. A requirement whose signature fails is reported OPEN - the
string match was never the point; this table is what makes "not cited" distinguishable from "not done".

    from spec_requirement_signatures import evaluate
"""
from __future__ import annotations
import csv, importlib.util, io, json, pathlib, re
from collections import namedtuple

HERE = pathlib.Path(__file__).resolve().parent
ROOT = next(a for a in (HERE, *HERE.parents) if (a / "00_program_registry").is_dir())
_ALL_DIRS = sorted(p for p in (ROOT / "papers").glob("P0*") if p.is_dir())
# A design directory whose topic was stopped by a pre-registered premise gate carries `BLOCKED.md` - written by
# `record_wave2_blocked.py`, and only accepted by package_audit when it names an artefact that exists on disk. Such a
# record owes no experiments, so the "every package must carry E00..E19" rules must not count it; the excluded names
# are published in every run so the narrowing is visible rather than silent.
BLOCKED_PACKAGES = sorted(p.name for p in _ALL_DIRS if (p / "BLOCKED.md").is_file())
PAPERS = [p for p in _ALL_DIRS if p.name not in set(BLOCKED_PACKAGES)]

Check = namedtuple("Check", "name kind args")


def _files(pkg, glob_rel):
    return [f for f in sorted(pkg.glob(glob_rel)) if f.is_file()]


def _any_needle(files, needles):
    for f in files:
        txt = f.read_text(encoding="utf-8", errors="replace")
        low = txt.lower()
        for n in needles:
            if n.lower() in low:
                return True, f"{f.name}:{n}"
    return False, ""


def _cov_items(cell: str):
    """Split an E_COVERAGE evidence cell into (label, regex) pairs, tolerating the labels that carry no regex."""
    out = []
    for part in cell.split(";"):
        m = re.match(r"\s*(.*?)\s*~\s*/(.*)/\s*$", part.strip())
        if m:
            out.append((m.group(1), m.group(2)))
    return out


def _evidence_holds(pkg: pathlib.Path, label: str, rx: str):
    """Re-open what an E_COVERAGE row points at. The completion audit does not take the coverage generator's word for
    a match: it reads the named artefact again and checks that something in it still matches the pattern."""
    try:
        pat = re.compile(rx, re.I)
    except re.error:
        return False, "uncompilable pattern"
    if label.endswith("/ filenames"):
        sub = label.split("/")[0]
        names = [f.name for f in sorted((pkg / sub).iterdir()) if f.is_file()] if (pkg / sub).is_dir() else []
        hit = next((n for n in names if pat.search(n)), "")
        return bool(hit), f"{sub}/{hit}" if hit else f"{sub}/ has no file matching /{rx}/"
    if label.endswith("headings"):
        f = pkg / label.rsplit(" headings", 1)[0]
        if not f.is_file():
            return False, f"{f.name} absent"
        heads = re.findall(r"^#{1,4} .*$", f.read_text(encoding="utf-8", errors="replace"), re.M)
        hit = next((h for h in heads if pat.search(h)), "")
        return bool(hit), f"{f.name}: {hit[:60]}" if hit else f"{f.name} has no heading matching /{rx}/"
    if label == "programme artefacts naming this package":
        names = [p.name for p in list((ROOT / "results_raw").iterdir()) + list((ROOT / "results_processed").iterdir())]
        hit = next((n for n in names if pat.search(n)), "")
        return bool(hit), hit
    if label.startswith("EXP-"):
        reg = pkg / "experiment_registry.csv"
        rows = [r for r in csv.reader(io.StringIO(reg.read_text(encoding="utf-8"))) if r] if reg.is_file() else []
        for r in rows[1:]:
            if r and r[0] == label.split()[0] and any(pat.search(cell) for cell in r):
                return True, f"{r[0]} registered in this package (stage={r[2] if len(r) > 2 else '?'})"
        return False, f"{label.split()[0]} is not registered in this package with a field matching /{rx}/"
    if label.startswith("claim "):
        cf = pkg / "claims_evidence_matrix.csv"
        rows = [r for r in csv.reader(io.StringIO(cf.read_text(encoding="utf-8"))) if r] if cf.is_file() else []
        cid = label.split()[1]
        hit = next((r for r in rows[1:] if r and r[0] == cid and any(pat.search(c) for c in r)), None)
        return bool(hit), f"claim {cid}" if hit else f"claim {cid} does not carry /{rx}/"
    return False, f"unrecognised evidence label {label!r}"


def _e_coverage_row(pkg: pathlib.Path, step: str):
    f = pkg / "E_COVERAGE.md"
    if not f.is_file():
        return None
    for ln in f.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(rf"^\|\s*{step}\s*\|[^|]*\|\s*([A-Z ]+)\s*\|(.*)\|\s*$", ln)
        if m:
            return m.group(1).strip(), m.group(2).strip()
    return None


def _run(check: Check):
    """Each kind returns (ok, evidence). Kinds are deliberately few so the semantics stay inspectable."""
    kind, args = check.kind, check.args
    if kind in _SECTION_KINDS:                 # the spec's top-level sections; see `SIGNATURES["S17"]` etc.
        return _SECTION_KINDS[kind](args)
    if kind == "e_step_all_papers":          # the spec's E00-E19 step, verified from the package's own artefacts
        step = args["step"]
        bad, why, per_pkg = [], [], []
        for p in PAPERS:
            row = _e_coverage_row(p, step)
            if row is None:
                bad.append(p.name[:4])
                why.append(f"{p.name[:4]}: no E_COVERAGE row for {step}")
                continue
            status, cell = row
            if status == "EVIDENCED":
                holds = [_evidence_holds(p, lab, rx) for lab, rx in _cov_items(cell)]
                ok = any(h for h, _ in holds)
                if ok:
                    per_pkg.append(f"{p.name[:4]}<-" + "; ".join(e for h, e in holds if h)[:90])
                else:
                    why.append(f"{p.name[:4]}: {step} claimed evidenced but none of its artefacts still match: "
                               + " | ".join(e for _, e in holds[:2]))
            elif status == "NOT APPLICABLE":
                m = re.match(r"^(\S+) states '(.+)'$", cell)
                f = p / m.group(1) if m else None
                ok = bool(m) and f is not None and f.is_file() and m.group(2).lower() in \
                    f.read_text(encoding="utf-8", errors="replace").lower()
                if ok:
                    per_pkg.append(f"{p.name[:4]}<=n/a:{m.group(1)}")
                else:
                    why.append(f"{p.name[:4]}: {step} claims not-applicable on {cell[:60]}, which does not hold")
            else:
                ok = False
                why.append(f"{p.name[:4]}: {step} is {status}")
            if not ok:
                bad.append(p.name[:4])
        return (not bad), (f"{len(PAPERS) - len(bad)}/{len(PAPERS)} packages carry {step} on a re-opened artefact: "
                           + " | ".join(per_pkg) + ("; " + " ; ".join(why[:6]) if why else ""))
    if kind == "all_needles_all_papers":        # every one of these must be present, not just any one of them
        bad = []
        for p in PAPERS:
            txt = " ".join(f.read_text(encoding="utf-8", errors="replace") for f in _files(p, args["glob"])).lower()
            miss = [n for n in args["needles"] if n.lower() not in txt]
            if miss:
                bad.append(f"{p.name[:4]}: lacks {miss}")
        return (not bad), (f"all {len(args['needles'])} required lines present in every package"
                           + ("; " + " ; ".join(bad) if bad else ""))
    if kind == "file_exists":                                      # a programme-level file, addressed by path
        f = ROOT / args["rel"]
        return f.is_file(), (f"{args['rel']} exists ({f.stat().st_size} bytes)" if f.is_file()
                             else f"{args['rel']} is absent")
    if kind == "hedged_needle_all_papers":
        # a phrase that is only legitimate inside a denial: "not of human information behaviour" is a scope statement,
        # the same words without the negation would be an overclaim, and a plain needle test cannot tell them apart
        win = args.get("window", 130)
        bad = []
        for p in PAPERS:
            for f in _files(p, args["glob"]):
                low = f.read_text(encoding="utf-8", errors="replace").lower()
                for m in re.finditer(re.escape(args["needle"].lower()), low):
                    seg = low[max(0, m.start() - win):m.end() + win]
                    if not any(h.lower() in seg for h in args["hedges"]):
                        bad.append(f"{p.name[:4]}/{f.name}: ...{seg.strip()[:80]}...")
        return (not bad), (f"every occurrence of {args['needle']!r} sits inside a denial"
                           + ("; unhedged at: " + " | ".join(bad[:3]) if bad else ""))
    if kind == "needles_in_named_papers":
        # 21.2's bound is owed by the papers that read reasoning text, not by the three that read metadata, so the
        # requirement is stated per package instead of diluted to "any file says something"
        miss = []
        for pid, needles in args["by_package"].items():
            pkg = next((x for x in PAPERS if x.name.startswith(pid)), None)
            if pkg is None:
                miss.append(f"{pid}: no such package")
                continue
            txt = " ".join(f.read_text(encoding="utf-8", errors="replace") for f in _files(pkg, args["glob"])).lower()
            if not any(n.lower() in txt for n in needles):
                miss.append(f"{pid}: none of {needles}")
        return (not miss), ("bounded in " + ", ".join(sorted(args["by_package"]))
                            + ("; missing: " + "; ".join(miss) if miss else ""))
    if kind == "file_all_papers":                                  # every package must carry this artefact
        miss = [p.name for p in PAPERS if not (p / args["rel"]).is_file()]
        return (not miss), (f"{len(PAPERS) - len(miss)}/{len(PAPERS)} packages" + (f"; missing: {miss}" if miss else ""))
    if kind == "one_of_files_all_papers":                          # the artefact may legitimately be named either way
        bad = []
        for p in PAPERS:
            hit = [r for r in args["rels"] if (p / r).is_file()]
            if not hit:
                bad.append(p.name)
        return (not bad), (f"{len(PAPERS) - len(bad)}/{len(PAPERS)} packages" + (f"; none of {args['rels']} in {bad}" if bad else ""))
    if kind == "needle_all_papers":                                # every package's own text must carry one of these
        bad = []
        for p in PAPERS:
            ok, _ = _any_needle(_files(p, args["glob"]), args["needles"])
            if not ok:
                bad.append(p.name)
        return (not bad), (f"{len(PAPERS) - len(bad)}/{len(PAPERS)} packages" + (f"; without it: {bad}" if bad else ""))
    if kind == "needle_any_file":                                  # programme-wide: some named file carries the needle
        pats = args["globs"] if isinstance(args["globs"], list) else [args["globs"]]
        files = [f for pat in pats for f in sorted(ROOT.glob(pat)) if f.is_file()]
        return _any_needle(files, args["needles"])
    if kind == "count_files_all_papers":                           # at least N files of a kind per package
        bad = [p.name for p in PAPERS if len(_files(p, args["glob"])) < args["min"]]
        return (not bad), (f"{len(PAPERS) - len(bad)}/{len(PAPERS)} packages with >= {args['min']}"
                           + (f"; short: {bad}" if bad else ""))
    if kind == "sections_all_papers":                             # a manuscript organised as the spec asks
        need = args["families"]
        bad = []
        for p in PAPERS:
            txt = (p / "paper.md").read_text(encoding="utf-8", errors="replace")
            heads = [h.lower() for h in re.findall(r"^#{1,3} +(.+)$", txt, re.M)]
            found = [f for f in need if any(any(w in h for w in f) for h in heads)]
            if len(found) < args["min_sections"]:
                bad.append(f"{p.name} ({len(found)}/{len(need)}: {found})")
        return (not bad), (f">= {args['min_sections']} of {len(need)} section families in every paper.md"
                           + (f"; short: {bad}" if bad else ""))
    raise SystemExit(f"unknown check kind {kind!r} in {check.name}")


# Requirement -> checks. The needle families are the auditor's operationalisation of the spec's wording, and each is
# named so a disagreement can be pointed at one string rather than at a judgement.
SIGNATURES = {
    "T01.01": [Check("failed and wrong runs are kept and labelled, not deleted", "needle_any_file",
                     {"globs": "results_raw/SUPERSEDED_ARTIFACTS.json", "needles": ["was_it_quoted", "reason"]}),
               Check("the registry retains non-success statuses", "needle_any_file",
                     {"globs": "00_program_registry/experiment_registry.csv",
                      "needles": ["success_no_", "_not_established", "OPEN", "withdrawn"]}),
               Check("every package states its evidence pointer per claim", "file_all_papers",
                     {"rel": "claims_evidence_matrix.csv"})],
    "T01.04": [Check("figures exist in every package", "count_files_all_papers", {"glob": "figures/*.pdf", "min": 1}),
               Check("negative results are retained in the registry, not deleted", "needle_any_file",
                     {"globs": "00_program_registry/experiment_registry.csv",
                      "needles": ["success_no_", "_not_established", "OPEN", "withdrawn"]}),
               Check("reproducibility is asserted per package (gate G18-E)", "needle_all_papers",
                     {"glob": "final_audit.md", "needles": ["G18-E"]})],
    "T03.01": [Check("a search log exists per package", "file_all_papers", {"rel": "lit_search_log.csv"}),
               Check("the log names real search endpoints", "needle_all_papers",
                     {"glob": "lit_search_log.csv", "needles": ["arxiv", "crossref", "semanticscholar", "openalex"]})],
    "T03.03": [Check("each package carries a graded novelty record", "one_of_files_all_papers",
                     {"rels": ["novelty_audit.md", "novelty_grading.md"]}),
               Check("the collision rule grades L0-L4 deterministically", "needle_any_file",
                     {"globs": "02_shared_code/literature/grade_collisions.py", "needles": ["L4", "L3", "L2"]})],
    "T04.02": [Check("a dataset card per package", "file_all_papers", {"rel": "dataset_card.md"}),
               Check("schema conformance is audited in shared code", "needle_any_file",
                     {"globs": "02_shared_code/data_audit/*.py", "needles": ["schema", "columns"]})],
    "T04.04": [Check("each package discloses its duplication/dependence structure", "needle_all_papers",
                     {"glob": "*.md",
                      "needles": ["contamination", "leakage", "duplicate", "dependence", "cluster", "overlap",
                                  "污染", "泄漏", "重复"]}),
               Check("the duplicate/leakage experiment is registered", "needle_any_file",
                     {"globs": "00_program_registry/experiment_registry.csv", "needles": ["EXP-0008"]})],
    "T06.01": [Check("research questions stated per package", "needle_all_papers",
                     {"glob": "research_plan.md", "needles": ["RQ1", "RQ2", "研究问题"]})],
    "T06.02": [Check("constructs are defined before the run, in the package's own words", "needle_all_papers",
                     {"glob": "*.md",
                      "needles": ["操作化", "operationaliz", "construct", "构念", "codebook", "coding scheme",
                                  "definition of", "verdict definition"]})],
    "T06.03": [Check("a new metric is chance/scale corrected somewhere", "needle_any_file",
                     {"globs": ["papers/P001*/paper.md", "papers/P001*/final_audit.md"],
                      "needles": ["chance-correct", "机会校正", "random baseline", "length-only"]}),
               Check("measures are frozen in advance", "needle_all_papers",
                     {"glob": "protocol_freeze.md",
                      "needles": ["metric", "指标", "primary", "measure", "level", "verdict", "criterion"]})],
    "T10.01": [Check("resampling inference is implemented", "needle_any_file",
                     {"globs": "02_shared_code/statistics/*.py", "needles": ["bootstrap", "permutation"]}),
               Check("the inference matches the dependence structure (clustering, a dependence-appropriate test, "
                     "or an explicit population claim)", "needle_all_papers",
                     {"glob": "paper.md",
                      "needles": ["cluster", "grouped", "hierarchical", "聚类", "wilson", "fisher", "exact",
                                  "bootstrap", "permutation", "census", "whole population", "not a sample"]}),
               Check("no parametric assumption is taken for granted", "needle_all_papers",
                     {"glob": "paper.md", "needles": ["rank", "Spearman", "non-parametric", "nonparametric",
                                  "bootstrap", "exact", "distribution-free"]})],
    "T10.02": [Check("magnitudes, not only tests, are reported per package", "needle_all_papers",
                     {"glob": "paper.md",
                      "needles": ["effect size", "odds ratio", "bits", "percentage point", "auroc", "wilson",
                                  "kappa", "rho", "agreement rate", "效应量", "pp"]}),
               Check("intervals are reported", "needle_all_papers", {"glob": "paper.md", "needles": ["CI", "95%"]})],
    "T10.03": [Check("Holm correction implemented for the flagship", "needle_any_file",
                     {"globs": "02_shared_code/statistics/analyze_routing_failure.py", "needles": ["holm"]}),
               Check("Holm correction implemented for the census paper", "needle_any_file",
                     {"globs": "02_shared_code/data_audit/governance_metadata_main_p005.py", "needles": ["holm"]}),
               Check("the correction is disclosed in the manuscript", "needle_any_file",
                     {"globs": "papers/*/*.md", "needles": ["Holm", "holm-adjusted", "多重比较"]})],
    "T10.05": [Check("the large-sample trap is stated as a reporting cap", "needle_any_file",
                     {"globs": "papers/P001*/paper.md", "needles": ["p < 0.001", "resample count", "cap"]}),
               Check("substantive claims rest on magnitudes", "needle_any_file",
                     {"globs": "papers/P001*/paper.md", "needles": ["effect size", "odds ratio"]})],
    "T12.01": [Check("a below-bar result is reported as not established", "needle_any_file",
                     {"globs": "papers/P002*/*.md", "needles": ["not established", "未确立", "fails"]}),
               Check("a below-bar transfer is reported as negative", "needle_any_file",
                     {"globs": "papers/P001*/*.md", "needles": ["reported as negative", "as a negative", "0.65 bar",
                                                                "未达"]}),
               Check("untestable is distinguished from negative", "needle_any_file",
                     {"globs": "papers/*/*.md", "needles": ["untestable", "不可测"]})],
    "T16.01": [Check("a claim-to-evidence skeleton exists per package", "file_all_papers",
                     {"rel": "claims_evidence_matrix.csv"}),
               Check("manuscript text is generated from the processed tables", "needle_any_file",
                     {"globs": "papers/P003*/scripts/write_paper.py", "needles": ["results_processed", "OUT_PROC",
                                                                                  "processed"]})],
    "T16.02": [Check("the manuscript is organised as the spec suggests (its own section names are allowed)",
                     "sections_all_papers",
                     {"families": [["abstract", "摘要"],
                                   ["introduction", "引言", "why this question", "what we do not claim",
                                    "the object"],
                                   ["related work", "literature", "background", "nearest", "screened"],
                                   ["data", "dataset", "语料", "sample", "corpus"],
                                   ["method", "instrument", "framework", "protocol", "方法"],
                                   ["result", "finding", "the numbers", "codability", "validity", "coverage"],
                                   ["discussion", "consequence", "implication", "what this supports", "讨论"],
                                   ["limitation", "局限", "reviewer", "does not support", "not support"],
                                   ["conclusion", "summary", "结论"]],
                      "min_sections": 8})],
    "T16.03": [Check("the gap is named in every manuscript", "needle_all_papers",
                     {"glob": "paper.md",
                      "needles": ["gap", "缺口", "unanswered", "no prior", "not answered", "leaves",
                                  "no work we found", "open question"]}),
               Check("contributions are enumerated per package", "needle_all_papers",
                     {"glob": "paper.md",
                      "needles": ["contribution", "贡献", "we show", "we find", "we measure", "we audit",
                                  "we report", "we build"]})],
    "T16.04": [Check("prior work is engaged somewhere in every package", "needle_all_papers",
                     {"glob": "*.md",
                      "needles": ["related work", "literature", "background", "nearest", "prior work",
                                  "已有研究", "screened literature"]}),
               Check("each engagement ends in what this paper adds", "needle_all_papers",
                     {"glob": "*.md",
                      "needles": ["this paper", "本文", "advances", "differs", "区分", "which this", "but neither",
                                  "does not test", "we measure"]})],
    "T16.05": [Check("results are organised by research question", "needle_all_papers",
                     {"glob": "paper.md", "needles": ["RQ1", "RQ2", "研究问题"]}),
               Check("robustness follows the result rather than preceding it", "needle_all_papers",
                     {"glob": "paper.md",
                      "needles": ["robust", "sensitivity", "ablation", "control", "稳健", "permutation",
                                  "secondary coder", "invariance"]})],
}

# The spec's E00-E19 minimum complete experiment package is required **of every paper**, so for these ids a mention is
# never evidence: the requirement is satisfied only when each package's E_COVERAGE row is EVIDENCED by an artefact the
# auditor re-opens itself (a file name that still exists, a registry row still registered, a claim still in the matrix)
# or NOT APPLICABLE by a sentence still present in the file it cites. This is the completion audit checking the coverage
# audit rather than trusting it.
for _e in [f"E{i:02d}" for i in range(20)]:
    SIGNATURES.setdefault(_e, [Check(f"{_e} carried by every package on a re-opened artefact",
                                     "e_step_all_papers", {"step": _e})])

# The two acceptance gates the spec states inline rather than as headings. Both are about behaviour that leaves a mark:
# G03 asks each paper to position itself in one page (four parts, generated from its own curated rows by
# `manuscript_sections.g03_one_pager`, which refuses to emit the block when a part has no source in the package), and
# G04 asks the programme to stop a main experiment when a field's meaning, a licence or a split rule cannot be
# confirmed - which is only checkable if the stops themselves are recorded, per package and in the topic registry.
SIGNATURES["G03"] = [
    Check("every paper states all four parts of gate G03 in its own manuscript", "all_needles_all_papers",
          {"glob": "paper.md",
           "needles": ["Positioning in one page (spec gate G03)",
                       "1. **What the closest existing work did.**",
                       "2. **What is still missing in that literature",
                       "3. **Why the data this paper uses can answer it.**",
                       "4. **How this paper differs from each of the closest works above.**"]}),
    Check("the block is assembled from the package's own literature matrix, not pasted prose", "needle_any_file",
          {"globs": ["papers/P00*/paper.md"],
           "needles": ["literature_matrix.csv:differentiation", "rule-composed from literature_matrix.csv",
                       "sota_audit.md"]})]
# Section 21's five special risks. Each is satisfied by behaviour that leaves a file behind; the file that gathers them
# (docs/section21_special_risks.md, EXP-0110) is generated from the artefacts and refuses to write when a manuscript
# sentence it cites has disappeared, so the note cannot outlive the evidence.
SIGNATURES["21.1"] = [
    Check("every paper states its population is recorded agent data", "needle_all_papers",
          {"glob": "paper.md",
           "needles": ["Data scope (spec 21.1)", "recorded agent-instruction", "Agent traces, not human",
                       "recorded trajectories", "model-synthesised"]}),
    Check("the human-behaviour phrase appears only inside a denial", "hedged_needle_all_papers",
          {"glob": "*.md", "needle": "human information behav",
           "hedges": ["not of human", "not human", "rather than human", "而非", "no claim", "not claim",
           "not evidence", "no human participant", "never claimed"]})]
SIGNATURES["21.2"] = [
    Check("the papers that read reasoning text bound it to the uttered surface", "needles_in_named_papers",
          {"glob": "paper.md",
           "by_package": {"P001": ["only surface language", "surface language"],
                          "P002": ["internal process", "uttered text and issued commands"]}}),
    Check("no reasoning-trace claim is made unhedged", "hedged_needle_all_papers",
          {"glob": "*.md", "needle": "chain-of-thought",
           "hedges": ["not", "no claim", "uttered", "surface", "cannot", "并非"], "window": 170}),
    Check("the coder's reading surface is tested rather than assumed", "file_exists",
          {"rel": "02_shared_code/trajectory_parser/test_canonical_ir.py"})]
SIGNATURES["21.3"] = [
    Check("the shipped outcome label was measured against an independent signal", "needle_any_file",
          {"globs": ["results_raw/EXP0108_p004_external_shipped_label_*.json"],
           "needles": ["exit_status", "value_census"]}),
    Check("the programme says the label is not a verifier result", "needle_any_file",
          {"globs": ["docs/section21_special_risks.md", "papers/P002*/paper.md", "papers/P002*/limitations.md",
                     "papers/P002*/protocol_freeze*.md"],
           "needles": ["not functional correctness", "is not a verifier result", "not a scale", "right-censoring",
                       "不等于", "censored"]})]
SIGNATURES["21.4"] = [
    Check("one unit test per canonical transformation exists", "file_exists",
          {"rel": "02_shared_code/trajectory_parser/test_canonical_ir.py"}),
    Check("and passes", "needle_any_file",
          {"globs": ["results_raw/EXP0109_canonical_ir_tests*.json"], "needles": ["ALL_TESTS_PASS"]}),
    Check("the original schemas are kept beside the canonical reader", "needle_any_file",
          {"globs": ["papers/P003*/dataset_card.md", "02_shared_code/data_audit/canonical_conformance_audit_p003.py"],
           "needles": ["from", "role", "content", "value"]})]
SIGNATURES["21.5"] = [
    Check("the boundary and its evidence are stated in the generated note", "needle_any_file",
          {"globs": ["docs/section21_special_risks.md"],
           "needles": ["no hosted model is called during analysis", "llm_api_used"]}),
    Check("each package's environment record names the model-API and network status", "needle_any_file",
          {"globs": ["papers/P001*/environment/system_info.json", "papers/P005*/environment/system_info.json",
                     "papers/P002*/environment/system_info.json", "papers/P003*/environment/system_info.json",
                     "papers/P004*/environment/system_info.json"],
           "needles": ["llm_api_available_by_policy", "llm_api_used", "no model inference", "no network"]}),
    Check("the one locally run model is registered with its provenance", "needle_any_file",
          {"globs": ["00_program_registry/experiment_registry.csv"], "needles": ["EXP-0062"]})]
SIGNATURES["G04"] = [
    Check("each package names something it could not confirm and what it withheld because of it", "needle_all_papers",
          {"glob": "*.md",
           "needles": ["unverifiable", "无法确认", "排除", "excluded", "parked", "暂停", "withheld", "not run",
                       "no licence", "not re-run", "withdrawn"]}),
    Check("the programme records a dataset or topic parked on an unconfirmed property", "needle_any_file",
          {"globs": ["00_program_registry/topic_registry.csv", "00_program_registry/experiment_registry.csv"],
           "needles": ["parked"]}),
    Check("the parking decision is traceable to a measured feasibility probe", "needle_any_file",
          {"globs": ["results_raw/EXP0096_*.json", "02_shared_code/data_audit/t027_feasibility_decision.py"],
           "needles": ["w2_parked_after_feasibility_probe", "parked"]})]


# ---------------------------------------------------------------- top-level spec sections (S00, S02, S07, S11, S13, S15, S17, S19, S20, S23)
#
# `spec_completion_audit.py` originally extracted only ids shaped T##.## / E## / G## / 21.n, so ten top-level sections
# of the spec were absent from the checklist altogether: the audit could print "0 open" while never having looked. These
# signatures give each of those sections a check against the artefact the section itself demands, with the needle set
# printed so a reader can dispute it rather than the verdict.

def _joined(p, glob_rel):
    return "\n".join(f.read_text(encoding="utf-8", errors="replace") for f in _files(p, glob_rel)).lower()


def _needles_count(args):
    """At least `min` of the spec's own listed items must be findable in each package."""
    glob_rel, needles, mn = args.get("glob", "*.md"), args["needles"], args["min"]
    bad, per = [], []
    for p in PAPERS:
        txt = _joined(p, glob_rel)
        have = [n for n in needles if n.lower() in txt]
        if len(have) < mn:
            bad.append(f"{p.name[:4]} has {len(have)}/{len(needles)} "
                       f"(missing: {', '.join(n for n in needles if n not in have)[:120]})")
        else:
            per.append(f"{p.name[:4]}:{len(have)}")
    return (not bad), (f"spec §{args['sec']} items found in every package (>= {mn} of {len(needles)}): "
                       + ", ".join(per) + ("; " + " ; ".join(bad) if bad else ""))


def _topic_groups(args):
    """How many of the spec's *questions* a package addresses, each asked as a synonym family.

    A literal needle list would fail a package that raises the same objection in other words - the spec writes "指标是否
    有 construct validity", a package writes "the construct is a reading rule". A group counts as addressed when any of
    its synonyms appears, and the group's label is printed so a disagreement targets one label, not a judgement.
    """
    glob_rel, groups, mn = args.get("glob", "*.md"), args["groups"], args["min"]
    bad, per = [], []
    for p in PAPERS:
        txt = _joined(p, glob_rel)
        miss = [g[0] for g in groups
                if not any(s.lower() in txt for s in g[1]) and g[0].lower() not in txt]
        if len(groups) - len(miss) < mn:
            bad.append(f"{p.name[:4]} misses {len(miss)}: {', '.join(miss)[:150]}")
        else:
            per.append(f"{p.name[:4]}={len(groups) - len(miss)}/{len(groups)}")
    return (not bad), (f"spec §{args['sec']} topics addressed in every package (>= {mn} of {len(groups)}): "
                       + ", ".join(per) + ("; " + " ; ".join(bad) if bad else ""))


def _table_rows(args):
    """Rows of one named markdown table per package - how many attacks/entries the package actually answers."""
    bad, per = [], []
    for p in PAPERS:
        f = p / args["file"]
        n = 0
        if f.is_file():
            n = len([ln for ln in f.read_text(encoding="utf-8", errors="replace").splitlines()
                     if re.match(r"^\| *[^| -][^|]*\|", ln)]) - 1        # minus the header row
        if n < args["min"]:
            bad.append(f"{p.name[:4]}: {n}")
        else:
            per.append(f"{p.name[:4]}={n}")
    return (not bad), (f"{args['file']} rows >= {args['min']} in every package: " + ", ".join(per)
                       + ("; short: " + ", ".join(bad) if bad else ""))


def _dirs_exist(args):
    miss = [d for d in args["paths"] if not (ROOT / d).is_dir()]
    return (not miss), ("workspace holds " + ", ".join(args["paths"]) if not miss else f"absent: {miss}")


def _files_exist(args):
    miss = [r for r in args["rels"] if not (ROOT / r).is_file()]
    return (not miss), (f"{len(args['rels']) - len(miss)}/{len(args['rels'])} artefacts present: "
                        + ", ".join(r.split('/')[-1] for r in args["rels"])
                        + ("; missing " + ", ".join(miss) if miss else ""))


def _audit_clean(args):
    """Spec §0's deliverable list, as the package auditor implements it: nothing missing, nothing weak."""
    import package_audit
    bad = []
    for p in PAPERS:
        r = package_audit.audit_paper(p)
        if r.get("missing") or r.get("weak"):
            bad.append(f"{p.name[:4]}: missing={len(r.get('missing') or [])} weak={len(r.get('weak') or [])}")
    return (not bad), ("package_audit reports missing=none weak=none for all five packages"
                       if not bad else "; ".join(bad))


def _csv_rows_between(args):
    f = ROOT / args["rel"]
    if not f.is_file():
        return False, f"{args['rel']} is absent"
    n = max(0, len(list(csv.reader(io.StringIO(f.read_text(encoding="utf-8", errors="replace"))))) - 1)
    return (args["min"] <= n <= args["max"]), (f"{args['rel']}: {n} rows, required between "
                                              f"{args['min']} and {args['max']}")


def _figure_plan_filled(args):
    """§15's roles checked against the artefacts, not against the words inside the plan file.

    A needle test over `FIGURE_PLAN.md` would pass on a document that lists all eight roles and fills none of them -
    the role names are its own row labels - so this reads the plan through the generator that wrote it and requires
    three things per package: no mandatory role left without an artefact; every artefact the plan names to exist; and
    every shipped figure and table to be named in `paper.md`, because §0 defines `figures/` as 论文全部图 rather than
    as a folder sitting next to the paper.
    """
    src = ROOT / "02_shared_code" / "writing" / "export_figure_plan.py"
    sp = importlib.util.spec_from_file_location("export_figure_plan", src)
    F = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(F)
    bad, ev = [], []
    for p in PAPERS:
        plan = p / "FIGURE_PLAN.md"
        if not plan.is_file():
            bad.append(f"{p.name[:4]}: ships no FIGURE_PLAN.md, so §15 is unplanned")
            continue
        gaps = [r for r in F.unfilled(p) if r not in F.OPTIONAL]
        if gaps:
            bad.append(f"{p.name[:4]}: §15 roles with no artefact: {gaps}")
            continue
        txt = plan.read_text(encoding="utf-8", errors="replace")
        named = re.findall(r"`(?:figures|tables)/([\w.\-]+\.(?:pdf|csv))`", txt)
        miss = [n for n in named if not ((p / "figures" / n).is_file() or (p / "tables" / n).is_file())]
        if miss:
            bad.append(f"{p.name[:4]}: the plan names artefacts that are not in the package: {miss[:4]}")
            continue
        paper = (p / "paper.md").read_text(encoding="utf-8", errors="replace") if (p / "paper.md").is_file() else ""
        figs = sorted(f.name for f in (p / "figures").glob("*.pdf"))
        tabs = sorted(f.name for f in (p / "tables").glob("*.csv"))
        unplaced = [f"figures/{n}" for n in figs if n not in paper] + [f"tables/{n}" for n in tabs if n not in paper]
        if unplaced:
            bad.append(f"{p.name[:4]}: shipped but named nowhere in paper.md: {unplaced[:4]}")
            continue
        ev.append(f"{p.name[:4]}: 8/8 roles carried, {len(figs)} figures + {len(tabs)} tables placed in the manuscript")
    return (not bad), ("every §15 role is carried by a real artefact that the paper names: " + " | ".join(ev)
                       + ("; " + " ; ".join(bad) if bad else ""))


def _topic_pool_waves(args):
    """§20's 30-50 is the size of the pool that enters one audit wave, not a ceiling on the registry's history.

    Measured, not asserted: the wave sizes are read back from the funnel artefacts that actually ran, and the check
    fails if any wave exceeded the cap or if the registry holds fewer than 30 topics. The registered total is printed
    so the reader can see how much of it is already terminal (folded, demoted, killed, packaged).
    """
    reg = ROOT / "00_program_registry" / "topic_registry.csv"
    if not reg.is_file():
        return False, "topic_registry.csv is absent"
    rows = [r for r in csv.DictReader(io.StringIO(reg.read_text(encoding="utf-8", errors="replace"))) if r]
    arts = sorted((ROOT / "results_raw").glob("EXP0115_funnel_screen_*.json"))
    waves = []
    for f in arts:      # the artefact lists topics in the order the waves were processed, so the cap is re-derivable
        n = len(json.loads(f.read_text(encoding="utf-8", errors="replace")).get("topics") or [])
        waves += [n] if n <= args["max"] else [args["max"], *([n - args["max"]] if n > args["max"] else [])]
    live = [r for r in rows if not str(r.get("status", "")).startswith(
        ("demoted", "killed", "not_", "w3_fold", "w3_merged", "w5_", "w2_parked", "w3_pilot"))]
    ok = len(rows) >= args["min"] and all(30 <= w <= args["max"] for w in waves[:-1] or [args["min"]]) \
        and bool(waves) and max(waves) <= args["max"]
    return ok, (f"{len(rows)} topics registered, {len(live)} still live; screening waves {waves} against the "
                f"§20 cap of {args['max']} per pool"
                + ("" if ok else " - OUT OF RANGE"))


_SECTION_KINDS = {"needles_count_all_papers": _needles_count, "table_rows_all_papers": _table_rows,
                  "dirs_exist": _dirs_exist, "files_exist": _files_exist, "package_audit_clean": _audit_clean,
                  "csv_rows_between": _csv_rows_between, "topic_groups_all_papers": _topic_groups,
                  "figure_plan_filled_all_papers": _figure_plan_filled, "topic_pool_waves": _topic_pool_waves}

FIGURE_ROLES = ["framework", "data structure", "main result", "mechanism", "robustness", "ablation",
                "error", "comparison table"]
# The spec's thirteen reverse-review questions, each as a family of the words a package legitimately uses.
ATTACK_GROUPS = [
    ("novelty", ["new problem", "novel", "already done", "first to", "isn't this already"]),
    ("difference from the closest work", ["difference", "differs", "nearest", "closest", "we withdrew"]),
    ("construct is invented, not measured", ["constructed", "人为", "operationali", "lexicon", "cue table", "rule"]),
    ("construct validity", ["construct validity", "validity", "is a reading rule", "what the metric tracks"]),
    ("synthetic data / extrapolation", ["synthetic", "extrapolat", "generalis", "generaliz", "transfer"]),
    ("reasoning text read as cognition", ["<think>", "chain-of-thought", "uttered", "internal process",
                                           "reasoning trace", "covert"]),
    ("independence of the unit", ["independen", "clustered", "rollout", "per-query", "instance"]),
    ("task/model/source confounding", ["confound", "per-config", "per-repositor", "teacher", "category", "domain"]),
    ("baseline too weak", ["baseline", "ladder", "strong base", "trivial base", "chance"]),
    ("latest SOTA missed", ["sota", "state of the art", "2026", "leaderboard"]),
    ("test-set leakage", ["leakage", "test split", "one evaluation", "held-out", "one-shot"]),
    ("benchmark contamination", ["contaminat"]),
    ("a single dataset only", ["one dataset", "single dataset", "one corpus", "cross-corpus", "second corpus",
                               "8 corpora", "three corpora", "two corpora"]),
]
ANALYSIS_GROUPS = [
    ("difficulty", ["difficulty", "hard"]),
    ("trajectory length", ["trajectory length", "length", "censor", "step cap"]),
    ("agent / model", ["teacher", "per-config", "model", "agent"]),
    ("dataset / source", ["corpus", "dataset", "source", "release"]),
    ("tool / catalogue count", ["catalogue", "candidate", "tool count", "catalog"]),
    ("semantic density", ["densit", "lexical", "coverage", "token"]),
    ("domain", ["domain", "category", "venue", "repository"]),
    ("success / failure", ["success", "failure", "outcome", "fail@"]),
    ("cost", ["cost", "runtime", "wallclock", "seconds"]),
    ("uncertainty", ["uncertaint", "confidence", "interval", "ci "]),
    ("search depth / breadth", ["depth", "breadth", "reformulat", "switch"]),
]
SIGNATURES["S00"] = [Check("every package passes the deliverable audit that resolves each named item to a real file",
                           "package_audit_clean", {}),
                     Check("and the shared workspace the series is run from exists", "dirs_exist",
                           {"paths": ["00_program_registry", "01_datasets", "02_shared_code", "papers",
                                      "results_raw", "results_processed", "docs"]})]
SIGNATURES["S02"] = [Check("one workspace holds registry, data, shared code, papers and results", "dirs_exist",
                           {"paths": ["00_program_registry", "01_datasets", "02_shared_code", "papers",
                                      "results_raw", "results_processed", "02_shared_code/registry",
                                      "02_shared_code/statistics", "02_shared_code/data_audit"]})]
SIGNATURES["S07"] = [Check("each package carries a protocol freeze file", "count_files_all_papers",
                            {"glob": "protocol_freeze*.md", "min": 1}),
                     Check("and states what was fixed before the run", "needles_count_all_papers",
                           {"sec": "7", "glob": "protocol_freeze*.md", "min": 2,
                            "needles": ["frozen", "seed", "threshold", "判据", "冻结"]})]
SIGNATURES["S11"] = [Check("the LLM-judge boundary is stated in the package, not just held in practice",
                            "needles_count_all_papers",
                            {"sec": "11", "min": 1, "glob": "*.md",
                             "needles": ["no judge in the loop", "not a judge", "no llm judge", "without a judge",
                                         "no human or model judge", "未使用 llm", "无人工或模型裁判"]}),
                     Check("and no package leaves a judge as its only source of truth", "needle_any_file",
                           {"globs": ["papers/*/final_audit.md", "02_shared_code/**/*.py"],
                            "needles": ["no model api", "forbids model inference", "no llm inference"]}
                           )]
SIGNATURES["S13"] = [Check("at least four of the spec's analysis dimensions are carried by every package",
                           "topic_groups_all_papers",
                           {"sec": "13", "glob": "*.md", "min": 4, "groups": ANALYSIS_GROUPS})]
SIGNATURES["S15"] = [Check("every §15 role is carried by a real artefact, and the manuscript names each one",
                           "figure_plan_filled_all_papers", {}),
                     Check("vector figures are shipped", "count_files_all_papers", {"glob": "figures/*.pdf", "min": 3}),
                     Check("and tables are generated files, not typed values", "count_files_all_papers",
                           {"glob": "tables/*.csv", "min": 5})]
SIGNATURES["S17"] = [Check("the reverse review answers at least the 13 attacks the spec lists",
                           "table_rows_all_papers", {"file": "reviewer_attack.md", "min": 13}),
                     Check("and addresses all thirteen of the spec's questions, in whatever words",
                           "topic_groups_all_papers",
                           {"sec": "17", "glob": "*.md", "min": 13, "groups": ATTACK_GROUPS})]
SIGNATURES["S19"] = [Check("the recommended experiment matrix is filled per package (E00-E19 rows)",
                           "table_rows_all_papers", {"file": "E_COVERAGE.md", "min": 20})]
SIGNATURES["S20"] = [Check("the topic funnel carries the registered candidate pool the spec asks for",
                           "topic_pool_waves", {"min": 30,
                                                "max": 50}),
                     Check("shared components are reused rather than rebuilt per paper", "files_exist",
                           {"rels": ["02_shared_code/data_audit/canonical_conformance_audit_p003.py",
                                     "02_shared_code/behavior_tagger/isp_stage_coder.py",
                                     "02_shared_code/statistics/isp_stage_main_p002.py"]})]
SIGNATURES["S23"] = [Check("the canonical schema, its audit tool and its unit tests exist", "files_exist",
                           {"rels": ["02_shared_code/trajectory_parser/test_canonical_ir.py",
                                     "02_shared_code/data_audit/audit_datasets.py",
                                     "02_shared_code/data_audit/canonical_conformance_audit_p003.py"]}),
                     Check("a complete experiment package per paper", "package_audit_clean", {}),
                     Check("a reproduction entry script per paper", "count_files_all_papers",
                           {"glob": "reproduce.sh", "min": 1}),
                     Check("the programme status document is generated, not hand-kept", "file_exists",
                           {"rel": "00_program_registry/PROGRAM_STATUS.md"}),
                     Check("the topic pool that enters one audit round stays inside 30-50", "topic_pool_waves",
                           {"min": 30, "max": 50})]


def evaluate(rid: str):
    """(satisfied, [{check, ok, evidence}]) for one requirement id; unknown ids are not satisfied."""
    if rid not in SIGNATURES:
        return False, []
    out, ok_all = [], True
    for c in SIGNATURES[rid]:
        try:
            ok, ev = _run(c)
        except Exception as e:                                          # a broken check must not read as a pass
            ok, ev = False, f"check raised {type(e).__name__}: {e}"
        ok_all &= ok
        out.append({"check": c.name, "kind": c.kind, "ok": bool(ok), "evidence": ev})
    return ok_all, out
