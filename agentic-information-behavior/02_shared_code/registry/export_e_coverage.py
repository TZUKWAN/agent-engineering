"""EXP-0103 (spec §9): map every step of the minimum complete experiment package onto each paper's own artefacts.

The governing spec requires E00-E19 for **every** paper ("每篇论文的最低完整实验包"), and only P001 had ever written that
mapping down. The other four packages ran pilots, mains, sensitivity runs, replications and instrument-invariance tests
without ever saying which of E00-E19 each of those runs discharges - so a reader could not tell whether a step was
missing, unnecessary here, or simply undocumented. This script produces that statement per package, and it refuses to
pretend:

* `EVIDENCED`      - a regex for the step matched this package's own evidence corpus (registry stage names, script
                     paths, table and figure file names, the claims matrix's test column, and the manuscript headings).
                     The matched strings are printed as the proof, so the row can be disputed.
* `NOT APPLICABLE` - declared in NA below, and **only accepted if the file cited as its reason exists and contains the
                     stated needle**. An unverified "not applicable" is impossible by construction.
* `OPEN`           - neither. The row is printed as open and the package audit reports it, so nothing is hidden.

Scope is the five pre-factory packages, and the round-2 pass is why that is now enforced rather than assumed.
`E_COVERAGE.md` has a second writer: `package_factory/wave_package.py` emits it for every package it assembles, with
its own step titles (E06 = sensitivity analysis, E07 = pilot). This script's `PAPERS` used to be "every directory
under papers/", so a single unparameterised run here overwrites 65 factory statements with a mapping those packages'
reproduce.sh never regenerates - one such run happened during this round and was undone by re-assembling the wave -
and it also printed nine OPEN steps into the blocked packages, which owe none. Which generator owns which package is
now read from the package's own files instead of from a list that drifts.

    python 02_shared_code/registry/export_e_coverage.py [--paper P003] [--check]

Idempotent: the document is regenerated from the package's files, so a re-run yields the same bytes unless a run, table
or claim was added.
"""
from __future__ import annotations
import argparse, csv, io, json, pathlib, re, sys, time
from collections import OrderedDict

ROOT = next(a for a in [pathlib.Path(__file__).resolve().parent,
                        *pathlib.Path(__file__).resolve().parents] if (a / "00_program_registry").is_dir())


def _this_script_owns(pkg: pathlib.Path) -> bool:
    """True only for a package whose coverage statement this script is the generator of.

    Two other kinds of package exist and neither is this script's to write. One that the 20-deliverable factory
    assembles already emits its own `E_COVERAGE.md` from its own artefacts, with its own step titles, and its
    reproduce.sh regenerates that one - a second writer over the same file means whichever script ran last wins, and
    a rebuild silently flips the statement back. And one stopped by a pre-registered premise gate (`BLOCKED.md`)
    owes no E00-E19 steps at all, so printing nine OPEN rows into it would invent a debt the design retired before
    any data was read.
    """
    rec = pkg / "reproduce.sh"
    if (pkg / "BLOCKED.md").is_file():
        return False
    return not (rec.is_file() and "wave_package.py" in rec.read_text(encoding="utf-8", errors="replace"))


PAPERS = sorted(p for p in (ROOT / "papers").glob("P0*") if p.is_dir() and _this_script_owns(p))
OUT = ROOT / "results_raw"

SPEC = OrderedDict([
    ("E00", ("数据描述与基础统计 / dataset description and base statistics",
             [r"presence_scan", r"base_stat", r"descriptive", r"conformance_pilot", r"sample_census", r"census",
              r"dataset_card", r"table_.*descriptiv", r"sample_description"])),
    ("E01", ("主效应/主任务实验 / main effect or main task",
             [r"_main_", r"main_DONE", r"_main\b", r"validity_main", r"routing_failure", r"census_DONE",
              r"RQ1|RQ2|RQ3|RQ4", r"table_criterion_validity", r"table_.*main"])),
    ("E02", ("基础基线 / trivial and published baselines",
             [r"baseline", r"length_only", r"length-only", r"B0\b", r"B1\b", r"null ladder", r"position_only",
              r"constant", r"table_.*baseline"])),
    ("E03", ("强基线/SOTA 对比 / strongest baseline or SOTA comparison",
             [r"comparator", r"dense_comparator", r"sota", r"pretrained", r"strongest", r"table_sota",
              r"sota_audit"])),
    ("E04", ("消融实验 / ablation",
             [r"ablation", r"feature_family", r"instruction_only", r"collection_aware", r"leave.one.out",
              r"partial_rho", r"confound", r"component"])),
    ("E05", ("替代操作化 / alternative operationalisation",
             [r"equivalence", r"alt_definition", r"alternative", r"second_matcher", r"extractor_invariance",
              r"lexicon", r"concept_inventory", r"strict_name", r"two.sided"])),
    ("E06", ("超参数敏感性 / hyperparameter sensitivity",
             [r"hyperparam", r"sensitivity", r"band_sweep", r"grid", r"C\s*=\s*", r"tolerance", r"k1=1.4"])),
    ("E07", ("随机种子 / seeds and seed variance",
             [r"seed", r"seeds 42", r"repeats", r"rng", r"default_rng", r"42,43,44"])),
    ("E08", ("跨数据集外部验证 / external validation on another dataset",
             [r"external", r"toolret", r"hermes", r"cross_corpus", r"transfer", r"second_corpus",
              r"agenttrove", r"value_level"])),
    ("E09", ("跨模型验证 / across-model validation",
             [r"config", r"teacher", r"OSS.*Qwen|Qwen.*Kimi", r"cross.model", r"three configs", r"per.config"])),
    ("E10", ("跨任务/领域稳健性 / across-task or domain robustness",
             [r"cross_corpus", r"eight corpora", r"8 corpora", r"per_release", r"by_release", r"domain",
              r"stratum", r"per.config"])),
    ("E11", ("Robustness（扰动/重测/稳健性）",
             [r"robust", r"randomised_resample", r"invariance", r"second_auditor", r"sensitivity",
              r"clustered", r"bootstrap"])),
    ("E12", ("Scaling / sample or catalogue scaling",
             [r"learning_curve", r"scaling", r"size_matched", r"rows_per", r"shards", r"n_candidates"])),
    ("E13", ("效率与成本 / runtime and cost",
             [r"wallclock", r"cost", r"runtime", r"ms per", r"seconds", r"_sec\b"])),
    ("E14", ("Statistical significance / CIs, corrections",
             [r"bootstrap", r"CI", r"fisher", r"holm", r"wilson", r"permutation", r"p.?0\.0", r"spearman"])),
    ("E15", ("Error Analysis / error analysis",
             [r"error_analysis", r"census", r"false_negative", r"FN\b", r"error_census"])),
    ("E16", ("Case Study / case reading",
             [r"case", r"example", r"hand_check", r"read sample", r"adjudicat", r"exemplar"])),
    ("E17", ("Counterfactual / intervention",
             [r"intervention", r"counterfactual", r"catalog_intervention", r"gating", r"randomised_resample"])),
    ("E18", ("Replication / replication",
             [r"replication", r"clean_room", r"reproduce", r"re_?run", r"EXP-0079"])),
    ("E19", ("Contamination Audit / contamination and leakage",
             [r"contamination", r"leakage", r"split_integrity", r"overlap", r"dedup", r"duplicate"])),
])

# Declared not-applicable rows. Each cites a file plus a needle that must be present in it, so the claim is checkable:
# if the artefact or the sentence disappears, the script stops treating the step as not applicable.
NA = {
    "P003": {"E06": ("protocol_freeze.md", "no model"), "E09": ("protocol_freeze.md", "no model"),
             "E12": ("dataset_card.md", "eight")},
    "P005": {"E06": ("protocol_freeze.md", "deterministic"), "E09": ("protocol_freeze.md", "no model"),
             "E12": ("dataset_card.md", "eight"), "E17": ("protocol_freeze.md", "census")},
    "P004": {"E09": ("protocol_freeze.md", "config")},
    "P002": {"E03": ("sota_audit.md", "no SOTA"), "E09": ("protocol_freeze.md", "no model")},
}


def evidence_corpus(pkg: pathlib.Path):
    """Everything a step can be evidenced by inside one package, as (label, text) pairs.

    Deliberately narrow, because a corpus that ingests the package's whole prose would let any sentence that happens
    to contain the word "ablation" certify an ablation. The corpus is: the package's registry rows (stage, script,
    config, status and the artefact paths it wrote), its claims matrix, the headings of every markdown file it ships,
    its tables/figures/configs/scripts/logs file names, and the programme-level artefacts whose file name names this
    package. A step is then evidenced by an artefact a reader can open, not by a phrase."""
    out = []
    reg = pkg / "experiment_registry.csv"
    if reg.is_file():
        for r in csv.DictReader(io.StringIO(reg.read_text(encoding="utf-8"))):
            out.append((f"{r['exp_id']} stage={r.get('stage', '')}",
                        " ".join([str(r.get(c, "")) for c in ("stage", "script", "config", "status", "outputs")])))
    cf = pkg / "claims_evidence_matrix.csv"
    if cf.is_file():
        for r in csv.DictReader(io.StringIO(cf.read_text(encoding="utf-8"))):
            out.append((f"claim {r.get('claim_id', '?')}",
                        " ".join(str(r.get(c, "")) for c in r)))
    for f in sorted(pkg.glob("*.md")):
        heads = " ".join(re.findall(r"^#{1,4} .*$", f.read_text(encoding="utf-8", errors="replace"), re.M))
        if heads:
            out.append((f"{f.name} headings", heads))
    for sub in ("tables", "figures", "configs", "scripts", "logs"):
        d = pkg / sub
        if d.is_dir():
            out.append((f"{sub}/ filenames", " ".join(p.name for p in sorted(d.iterdir()))))
    named = [p.name for pid in (pkg.name[:4], pkg.name[:4].lower())
             for p in list((ROOT / "results_raw").glob(f"*{pid}*")) + list((ROOT / "results_processed").glob(f"*{pid}*"))]
    if named:
        out.append(("programme artefacts naming this package", " ".join(sorted(set(named)))))
    return out


def analyse(pkg: pathlib.Path, pid: str, corpus):
    rows = []
    for eid, (title, pats) in SPEC.items():
        hits = []
        for rx in pats:
            for label, text in corpus:
                if re.search(rx, text, re.I):
                    hits.append(f"{label} ~ /{rx}/")
                    break
            if len(hits) >= 3:
                break
        na = NA.get(pid, {}).get(eid)
        if hits:
            rows.append((eid, title, "EVIDENCED", "; ".join(hits[:3])))
        elif na:
            rel, needle = na
            f = pkg / rel
            ok = f.is_file() and needle.lower() in f.read_text(encoding="utf-8", errors="replace").lower()
            rows.append((eid, title, "NOT APPLICABLE" if ok else "OPEN",
                         (f"{rel} states {needle!r}" if ok else
                          f"declared not applicable, but {rel} does not contain {needle!r}")))
        else:
            rows.append((eid, title, "OPEN", "no artefact in this package matches any evidence pattern for the step"))
    return rows


def render(pid, rows):
    n_open = sum(1 for r in rows if r[2] == "OPEN")
    L = [f"# {pid}: coverage of the spec's minimum complete experiment package (§9, E00-E19)", "",
         "Generated by `02_shared_code/registry/export_e_coverage.py` - deliberately without a generation timestamp, so "
         "re-running it on an unchanged package reproduces identical bytes and a rebuild can be checked against it. "
         "A step is "
         "`EVIDENCED` only when a pattern for it matches a named artefact of this package, and the matched artefacts "
         f"are printed so the row can be disputed; `NOT APPLICABLE` requires a file in this package that states the "
         f"reason. **{n_open} step(s) are OPEN.**", "",
         "| step | spec requirement | status | evidence |", "|---|---|---|---|"]
    for eid, title, status, ev in rows:
        L.append(f"| {eid} | {title[:64]} | {status} | {ev[:220]} |")
    return "\n".join(L) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--paper", default="")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    summary = {}
    for pkg in PAPERS:
        pid = pkg.name[:4]
        if a.paper and pid != a.paper:
            continue
        rows = analyse(pkg, pid, evidence_corpus(pkg))
        text = render(pid, rows)
        out = pkg / "E_COVERAGE.md"
        opens = [r[0] for r in rows if r[2] == "OPEN"]
        summary[pid] = {"steps": len(rows), "evidenced": sum(1 for r in rows if r[2] == "EVIDENCED"),
                        "not_applicable": sum(1 for r in rows if r[2] == "NOT APPLICABLE"), "open": opens}
        if a.check:
            same = out.is_file() and out.read_text(encoding="utf-8") == text
            print(f"  {pid}: {'up to date' if same else 'STALE'} | open: {opens or 'none'}")
        else:
            out.write_text(text, encoding="utf-8", newline="")
            print(f"  {pid}: wrote E_COVERAGE.md | {summary[pid]['evidenced']} evidenced, "
                  f"{summary[pid]['not_applicable']} not applicable, open: {opens or 'none'}", flush=True)
    res = {"exp_id": "EXP-0103", "at": time.strftime("%Y-%m-%dT%H:%M:%S"), "per_package": summary,
           "rule": "evidenced only by a matched artefact of the package; not-applicable only with a file that says so",
           "wallclock_sec": round(time.time() - t0, 1)}
    (OUT / f"EXP0103_e_coverage_{time.strftime('%Y%m%dT%H%M%S')}.json").write_text(
        json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    print("wrote the EXP-0103 artefact")
    return 0


if __name__ == "__main__":
    sys.exit(main())
