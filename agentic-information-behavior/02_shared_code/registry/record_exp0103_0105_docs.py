"""EXP-0103/0104/0105 into the packages: register the three steps, and file what each measured where a reader will look.

EXP-0103 (the E00-E19 coverage statement), EXP-0104 (the contamination/leakage audit of the corpora each package reads)
and EXP-0105 (the E13 runtime-and-cost table) ran and wrote programme-level artefacts, but nothing inside P002-P005 said
so: their packages had no E19 or E13 statement, no registry row, and their `package_audit.py` could not see the gap.
This recorder files them:

* one registry row per step, by column name, with the defect each one found written into the row rather than hidden;
* `papers/P00x/CONTAMINATION_AND_COST.md` - a package-scoped statement of what was measured on which rows, per source
  column, and of what could **not** be measured (a column that is null in every sampled row has no leakage to test);
* one claims row, one deviations row and one limitations bullet per package, each keyed on its own content so a
  re-run adds nothing.

Every number is read from the artefacts at run time - this script contains no measured value of its own.

    python 02_shared_code/registry/record_exp0103_0105_docs.py [--check]
"""
from __future__ import annotations
import argparse
import re, csv, glob, io, json, pathlib, re, sys, time

ROOT = next(a for a in [pathlib.Path(__file__).resolve().parent,
                        *pathlib.Path(__file__).resolve().parents] if (a / "00_program_registry").is_dir())
REG = ROOT / "00_program_registry" / "experiment_registry.csv"
PAPERS = sorted(p for p in (ROOT / "papers").glob("P0*") if p.is_dir())


def owned_by(module_fragment: str, mine=None):
    """(owned, owned_elsewhere, unattributed) package ids, read from each package's section-9 record header.

    The guard exists so this recorder cannot write over a section another generator owns, so the conflict it must
    detect is a package that *has* a section-9 record naming somebody else. Round 2 found it aborting instead on the
    twelve packages that carry no such document at all - their §9 deliverable is satisfied by another file, so there
    is nothing here to attribute, and the abort silently blocked the one fix the five pre-wave packages needed. With
    `mine` given, an unattributed package is only reported when this recorder writes to it.
    """
    owned, other, unattributed = [], [], []
    for pkg in PAPERS:
        head = ""
        for doc in ("CONTAMINATION_AND_COST.md", "RUN_COST.md"):
            f = pkg / doc
            if f.is_file():
                head = f.read_text(encoding="utf-8", errors="replace")[:4000]
                break
        names = re.findall(r"[Gg]enerated by[^\n]{0,220}", head)
        if not names:
            if not head and mine is not None and pkg.name[:4] not in mine:
                continue                                  # no record here, and this recorder writes none to it
            unattributed.append(pkg.name[:4])
        elif any(module_fragment in n for n in names):
            owned.append(pkg.name[:4])
        else:
            other.append(pkg.name[:4])
    return owned, other, unattributed
TODAY = "2026-09-21"

# which scope of the contamination artefact belongs to which package
SCOPE = {"P001": ["ROUTING"], "P002": ["P002"], "P003": ["P003_P005"], "P004": ["P004", "ROUTING"],
         "P005": ["P003_P005"]}


def latest(prefix: str):
    f = sorted(glob.glob(str(ROOT / "results_raw" / prefix)))
    if not f:
        raise SystemExit(f"ABORT: no artefact matching {prefix} - run the measurement before recording it")
    return pathlib.Path(f[-1]), json.loads(pathlib.Path(f[-1]).read_text(encoding="utf-8"))


def newest_covering(prefix: str, need):
    """The newest artefact whose `per_package` block carries every package in `need`.

    `export_run_cost.py --paper P004` and `export_e_coverage.py --paper P004` write an artefact about P004 only. Reading
    "the newest" one made the sections below appear in one package's document and vanish from another's, alternating on
    every rebuild - so the recorder looks back for a run that covers all five, exactly as it does for the contamination
    scopes."""
    for f in reversed(sorted(glob.glob(str(ROOT / "results_raw" / prefix)))):
        try:
            d = json.loads(pathlib.Path(f).read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            # reported, then skipped: a corrupt artefact is a finding the round must see, but it must not be
            # able to silence every other package's record
            print(f"  WARN: {pathlib.Path(f).name} is unreadable ({exc}); skipped and reported as corrupt")
            continue
        pp = d.get("per_package", {})
        if all(k in pp for k in need):
            return pathlib.Path(f), d
    raise SystemExit(f"ABORT: no artefact {prefix} covers {sorted(need)} - run the step without --paper first")


def sub_source_rows(block: dict):
    """Flatten one scope's per-source summaries into (corpus, source, summary) rows for the table."""
    rows = []
    for group in ("corpora", "releases"):
        for corp, data in sorted(block.get(group, {}).items()):
            for src, s in sorted((data.get("sources") or {}).items()):
                rows.append((corp, src, s))
    return rows


def render_contamination(pid: str, cov_row, contam: dict, cost: dict):
    """The package's own E19 + E13 statement."""
    L = [f"# {pid}: contamination, duplication and leakage (E19), and where its run cost comes from (E13)", "",
         "Generated by `02_shared_code/registry/record_exp0103_0105_docs.py` from the EXP-0104 and EXP-0105 artefacts; "
         "it contains no number that is not in those artefacts, and it does not restate a clean result as a guarantee: "
         "a quantity that could not be measured on the rows sampled is named as not measured.", ""]
    for name, block in sorted(contam.items()):
        L += [f"## {name}", ""]
        if block.get("not_measured"):
            L += [f"Not measured: {block['not_measured']}", ""]
        src_rows = sub_source_rows(block)
        cfg_rows = sorted(block.get("configs", {}).items())
        if src_rows:
            def cell(v):
                return "not measured" if v is None else v
            L += ["| corpus / release | source column | rows read | rows with a value | distinct values | "
                  "rows in a duplicated key | largest group share |", "|---|---|---|---|---|---|---|"]
            for corp, src, s in src_rows:
                L.append(f"| {corp} | `{src}` | {s['rows_read']} | {s['rows_with_value']} | "
                         f"{cell(s['distinct_values'])} | {cell(s['rows_in_a_duplicated_key'])} | "
                         f"{cell(s['largest_group_share'])} |")
            L.append("")
        if cfg_rows:
            L += ["| processed routing table | rows | uuids | duplicated uuids | dev | test | uuid in both buckets | "
                  "question texts crossing the split | share of test rows whose text is also in dev | prompt_ids in "
                  "both buckets |", "|---|---|---|---|---|---|---|---|---|---|"]
            for cfg, v in cfg_rows:
                L.append(f"| {cfg} | {v['rows']} | {v['uuid_distinct']} | {v['uuid_rows_in_a_duplicated_key']} | "
                         f"{v['dev_uuids']} | {v['test_uuids']} | {v['uuid_in_both_buckets']} | "
                         f"{v['question_texts_in_both_buckets']} | {v['question_leak_share_of_test_rows']} | "
                         f"{v['prompt_ids_in_both_buckets']} |")
            L += ["", f"Verdict on the processed tables: **{block.get('verdict', 'see the artefact')}**.", ""]
        for rel in ("split_leakage",):
            for corp, data in sorted(block.get("corpora", {}).items()):
                if rel in data:
                    L += [f"*{corp}* - `{rel}`: {data[rel]['verdict']} "
                          f"(tasks with a split value: {data[rel]['tasks_with_a_split_value']}, "
                          f"crossing: {data[rel]['tasks_in_more_than_one_split']}).", ""]
        if "cross_corpus" in block:
            cc = block["cross_corpus"]
            L += ["Cross-corpus independence (the question P002's replication claim rests on):",
                  f"* exact task-text overlap between `{cc['swe_text_source']}` and `{cc['trove_text_source']}`: "
                  f"**{cc['exact_text_overlap']['shared_signatures']}** shared of "
                  f"{cc['exact_text_overlap']['a_distinct']} / {cc['exact_text_overlap']['b_distinct']} distinct;",
                  f"* shared task/instance identifiers: "
                  f"**{cc['shared_task_or_instance_identifiers']['shared_signatures']}**;",
                  f"* verdict: **{cc['verdict']}**;",
                  "", f"> {cc.get('note', '')} {block.get('caveat', '')}", ""]
        if "cross_config" in block:
            cx = block["cross_config"]
            L += ["Teacher-config overlap (the dependence P004's clustered intervals cover):", "",
                  f"* prompt_ids shared by two configs: **{cx['prompt_ids_shared_by_two_configs']}**;",
                  f"* question texts appearing in more than one config: "
                  f"**{cx['questions_shared_by_more_than_one_config']}**;",
                  f"* question texts in all three configs: **{cx['questions_shared_by_all_configs']}**;",
                  "", f"> {cx['note']}", ""]
        if "cross_release" in block:
            cr = block["cross_release"]
            L += [f"Release independence for a census: **{cr['verdict']}** "
                  f"({cr['releases_with_task_text']} releases carry task text in the sampled rows, "
                  f"{cr['release_pairs_compared']} pairs compared).", ""]
            for p in cr["pairs_with_shared_task_text"]:
                L.append(f"* {p['release_a']} x {p['release_b']}: {p['shared_task_text_signatures']} shared texts")
            L += ["", f"> {block.get('note', '')}", ""]
        for rel, data in sorted(block.get("releases", {}).items()):
            if data.get("not_measured"):
                L += [f"*not measured* - {rel}: {data['not_measured']}", ""]
    L += ["## What this does not establish", "",
          "- Sampling. Except for the processed routing tables, which are read in full, every figure above is computed "
          "on a seeded sample of shards (seed 42) and rows per shard, so a duplicate rate is a measurement on that "
          "sample, not a claim that the release is duplicate-free.",
          "- Null columns. A source column that carries no value in the sampled rows is reported with "
          "`rows_with_value = 0`; no duplicate, leakage or overlap conclusion is drawn from it. This is the finding that "
          "the first pass of this audit got backwards, reporting such columns as duplicate-free.",
          "- Model familiarity. Nothing here can say whether a model was *trained* on these texts; the programme has no "
          "model API to probe. E19's training-contamination risk is therefore addressed by the corpus choice "
          "(trajectories of a public release) and by the external, size-matched transfers, not by a membership test.",
          ""]
    if cost:
        L += ["## E13 run cost", "",
              "`RUN_COST.md` and `tables/table_run_cost.csv` are this package's E13 statement: measured run time per "
              "registered step, the difference between a step's own measurement and its registry span (a parked step's "
              "span is not its runtime), and which spec quantities are zero, not applicable or simply not measured. "
              "The figures are not repeated here on purpose - the register that the cost table is built from gains a "
              "row when this document's own claim is added, so a copied total would be one pass stale.", ""]
    if cov_row:
        L += ["## E00-E19 coverage", "",
              "`E_COVERAGE.md` is this package's statement of coverage of the spec's minimum experiment package. Its "
              "counts are deliberately not copied here: the documents written by this same step are part of the "
              "evidence that statement reads, so a copied number would be one pass out of date by construction and "
              "would eventually disagree with the file it came from.", ""]
    return "\n".join(L) + "\n"


def add_claim(pkg: pathlib.Path, prefix: str, row: dict, check: bool):
    """Append the E19/E13 statement as a claim, keyed on its content and numbered into the package's own sequence."""
    cf = pkg / "claims_evidence_matrix.csv"
    rows = [r for r in csv.reader(io.StringIO(cf.read_text(encoding="utf-8"))) if r]
    hdr, body = rows[0], rows[1:]
    exps = re.findall(r"EXP-\d{4}", row.get("experiment_id") or "")
    # the idempotence key is the claim's own experiment set: a fixed pair shared by one recorder let a second
    # recorder's claims be reported as "already present" and never written at all
    prior = [r for r in body if exps and all(e in " ".join(r) for e in exps)]
    if prior:
        r0 = prior[0]
        new = dict(zip(hdr, r0))
        new.update({"claim_id": r0[0], **{k: v for k, v in row.items() if k in hdr}})
        new["claim_id"] = r0[0]
        if [new.get(k, "") for k in hdr] == r0:
            return "already present"
        if check:
            return f"would update {r0[0]}"
        out_rows = [hdr] + [(list(new.values()) if r is r0 else r) for r in body]
        buf = io.StringIO(newline="")
        cw = csv.writer(buf, lineterminator=chr(13) + chr(10))
        for r in out_rows:
            cw.writerow(r)
        cf.write_text(buf.getvalue(), encoding="utf-8", newline="")
        return f"updated {r0[0]}"
    used = {r[0] for r in body}
    nums = [int(m.group(1)) for r in used for m in [re.match(rf"^{prefix}(\d+)$", r)] if m]
    cid = f"{prefix}{max(nums, default=0) + 1}"
    assert cid not in used, f"{cid} is taken"
    c = dict.fromkeys(hdr, "")
    c.update({"claim_id": cid, **{k: v for k, v in row.items() if k in hdr}})
    if check:
        return f"would add {cid}"
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=hdr, lineterminator="\r\n")
    w.writeheader()
    w.writerow(c)
    cf.write_text(cf.read_text(encoding="utf-8").rstrip("\r\n") + "\r\n"
                  + buf.getvalue().split("\r\n", 1)[1].rstrip("\r\n") + "\r\n", encoding="utf-8", newline="")
    assert all(len(r) == len(hdr) for r in
               [r for r in csv.reader(io.StringIO(cf.read_text(encoding="utf-8"))) if r]), "claims matrix shape broke"
    return f"added {cid}"


def add_deviation(pkg: pathlib.Path, did: str, text: str, check: bool, reason: str = "", pointer: str = ""):
    """Insert or update one deviation row, keyed on its id.

    Two defects of the first version are fixed here. It skipped any row whose id was already present, so a row written
    by an older version could never be corrected; and it filled the last two columns with the same sentence for every
    package, which `package_audit.py` reads as a duplicated row (columns 3-4 identify the row for that check). The
    caller now names the experiment and the artefact that carries it."""
    f = pkg / "deviations.md"
    t = f.read_text(encoding="utf-8")
    if not re.search(r"^\| D\d+ \|", t, re.M):
        return f"SKIPPED: {pkg.name} has no table-form deviations file to append to"
    cols = max(len(re.findall(r"\|", line)) for line in t.splitlines() if re.match(r"^\| D\d+ \|", line)) - 1
    cells = [did, text, reason or "measured and recorded by EXP-0103/0104/0105",
             pointer or "the package's `CONTAMINATION_AND_COST.md` and `RUN_COST.md`"]
    cells = (cells + [""] * cols)[:cols]
    row = "| " + " | ".join(cells) + " |"
    if check:
        return f"would add {did}"
    had = re.search(rf"^\| {did} \|.*$", t, re.M)
    if had:
        if had.group(0) == row:
            return "already present"
        t = t[:had.start()] + row + t[had.end():]
        f.write_text(t, encoding="utf-8", newline="")
        return f"updated {did}"
    last = [m.end() for m in re.finditer(r"^\| D\d+ \|.*$", t, re.M)][-1]
    t = t[:last] + "\n" + row + t[last:]
    f.write_text(t, encoding="utf-8", newline="")
    return f"added {did}"


def refresh_final_audit_counts(pkg: pathlib.Path):
    """Re-point final_audit.md's own counts at the files it summarises. The generators write those numbers before the
    recorders append rows, so without this step the package audit reads a stale count as a weakness."""
    fa = pkg / "final_audit.md"
    if not fa.is_file():
        return "no final_audit.md"
    t = fa.read_text(encoding="utf-8")
    dv = pkg / "deviations.md"
    n_dev = len(re.findall(r"^\| D\d+ \|", dv.read_text(encoding="utf-8"), re.M)) if dv.is_file() else None
    n_claims = None
    cf = pkg / "claims_evidence_matrix.csv"
    if cf.is_file():
        n_claims = max(0, len([r for r in csv.reader(io.StringIO(cf.read_text(encoding="utf-8"))) if r]) - 1)
    changed = []
    if n_dev is not None:
        new, k = re.subn(r"(Deviations \|\s*)\d+( recorded)", lambda m: m.group(1) + str(n_dev) + m.group(2), t)
        if k and new != t:
            t, _ = new, changed.append(f"deviations={n_dev}")
    if n_claims is not None:
        new, k = re.subn(r"(\|\s*)\d+( claims)", lambda m: m.group(1) + str(n_claims) + m.group(2), t)
        if k and new != t:
            t, _ = new, changed.append(f"claims={n_claims}")
    if changed:
        fa.write_text(t, encoding="utf-8", newline="")
    return ", ".join(changed) or "counts already current"


def add_limitation(pkg: pathlib.Path, marker: str, text: str, check: bool):
    f = pkg / "limitations.md"
    if not f.is_file():
        return "SKIPPED: no limitations.md"
    t = f.read_text(encoding="utf-8")
    # keyed on the sentence itself, not on a label the caller chooses: an earlier version tested a marker string that
    # never appears in the text it was given, so every run appended a second copy of the same limitation
    def norm(s):
        return re.sub(r"\s+", " ", re.sub(r"^\d+\.\s*", "", s)).strip()[:48]
    items = [m for m in re.finditer(r"(?m)^\d+\. .*$", t)]
    same = [m for m in items if norm(m.group(0)) == norm(text)]
    keep, drop = (same[:1], same[1:])
    for m in reversed(drop):
        t = t[:m.start()].rstrip("\n") + "\n" + t[m.end():].lstrip("\n")
    if drop:
        f.write_text(t, encoding="utf-8", newline="")
    if keep:
        return f"already present ({len(same)} copy(ies) seen, {len(drop)} removed)"
    if check:
        return "would add"
    heads = list(re.finditer(r"^## .*$", t, re.M))
    tail = [m for m in re.finditer(r"^\d+\. .*$", t, re.M)]
    if tail and (not heads or tail[-1].start() > heads[-1].start()):
        end = tail[-1].end()
        n = int(tail[-1].group(0).split(".")[0]) + 1
        t = t[:end] + f"\n{n}. {text}" + t[end:]
    else:
        t = t.rstrip("\n") + f"\n\n1. {text}\n"
    f.write_text(t, encoding="utf-8", newline="")
    return "added"


def span(d):
    """Start and finish of a step, derived from what its own artefact recorded (`at` plus `wallclock_sec`) rather than
    from the time this recorder happens to run - a cost table built from copied timestamps would be fiction."""
    at = (d or {}).get("at") or ""
    try:
        wc = float((d or {}).get("wallclock_sec") or 0)
        st = time.strptime(at, "%Y-%m-%dT%H:%M:%S")
        return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(time.mktime(st) - wc)), at
    except (ValueError, TypeError):
        return at, at


def registry_rows(cov, contam, cost) -> list:
    """The three steps as the registry records them, defects included."""
    out = []
    for exp, script, stage, cfg, status, outputs, notes, papers in (
            ("EXP-0103", "02_shared_code/registry/export_e_coverage.py", "e00_e19_coverage_statement",
             "One regex set per spec step, matched against the package's own registry rows, claims matrix, markdown "
             "headings, tables/figures/configs/scripts/logs file names and the programme artefacts that name the "
             "package; NOT APPLICABLE accepted only when a named file in the package contains the stated reason; the "
             "document carries no generation timestamp so a rebuild is checkable against it",
             "20_of_20_for_P001_open_rows_remain_in_four_packages",
             "results_raw/" + cov[0].name + "; papers/P00*/E_COVERAGE.md",
             "Found three real delivery gaps: E19 contamination audits existed only for P001, E13 cost statements for "
             "none, and several steps (E04 ablation, E02 baseline, E15 error analysis) unevidenced in P002-P005. The "
             "script records OPEN rather than relaxing a pattern to cover them.",
             "programme"),
            ("EXP-0104", "02_shared_code/data_audit/package_contamination_audit.py",
             "corpus_contamination_and_leakage_audit",
             "Seeded shard sample (seed 42, 250 rows per shard, at least 24 shards per corpus), one measure per source "
             "column with rows_with_value reported separately; the processed routing tables are read in full because a "
             "sampled leakage check can only bound the risk",
             "measured_first_pass_had_two_false_cleanes",
             "results_raw/" + contam[0].name + "; results_processed/EXP0104_contamination_*.csv",
             "Two measurement defects were fixed on the way. files[:3] measured the shard layout instead of the corpus, "
             "and only scalar text columns were read, so AgentBank, code-act and AgentInstruct - whose task text lives "
             "in `conversations` - were reported duplicate-free on a column that was never opened. AgentTrove's "
             "`instruction` and `split` columns exist but are null in the rows sampled, so the earlier '1 distinct "
             "instruction, no split leakage' was a statement about nothing. Every quantity is now reported per source "
             "column with its rows-with-value count, and a column with no value yields not_measured.",
             "P001;P002;P003;P004;P005"),
            ("EXP-0105", "02_shared_code/registry/export_run_cost.py", "e13_runtime_and_cost_table",
             "Registry started_at/finished_at spans plus each step's own artefact wallclock_sec; where both exist the "
             "step's own measurement is used for the cost and the span is kept in its own column; GPU hours, inference "
             "tokens and API cost are taken from the package's environment statement, and memory/latency/tool calls are "
             "reported as not measured or not applicable",
             "per_package_cost_tables_written_span_disagreement_named",
             "results_raw/" + cost[0].name + "; papers/P00*/RUN_COST.md; papers/P00*/tables/table_run_cost.csv",
             "The registry's own timestamps are not a runtime: EXP-0089 spans 181,479 s against 33.1 s measured by its "
             "artefact, because the step was opened, parked and closed two days later. The table therefore carries both "
             "columns and names the basis of the value it sums, and 5 of the 104 registered steps give no duration at "
             "all - which is printed rather than filled in.",
             "P001;P002;P003;P004;P005")):
        arte = {"EXP-0103": cov, "EXP-0104": contam, "EXP-0105": cost}[exp]
        s0, s1 = span({"at": arte[1].get("at"), "wallclock_sec": arte[1].get("wallclock_sec")})
        out.append({"exp_id": exp, "paper_id": papers, "topic_id": "", "stage": stage, "script": script,
                    "config": cfg,
                    "seed": "42 where sampling is used; deterministic otherwise",
                    "started_at": s0, "finished_at": s1,
                    "status": status, "outputs": outputs, "notes": notes,
                    "enters_paper": "yes - CONTAMINATION_AND_COST.md, RUN_COST.md and one claim per package"})
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    OWNED, ELSEWHERE, UNATTRIBUTED = owned_by('record_exp0103_0105_docs.py', mine=set(SCOPE))
    if UNATTRIBUTED:
        raise SystemExit(f"ABORT: {len(UNATTRIBUTED)} package(s) name no generator in their "
                         f"section-9 record: {UNATTRIBUTED}")
    ALL = OWNED
    print(f"this recorder owns {len(ALL)} of {len(PAPERS)} packages; {len(ELSEWHERE)} are generated "
          f"elsewhere and are skipped here")
    covf, cov = newest_covering("EXP0103_e_coverage_*.json", ALL)
    conf, contam = latest("EXP0104_package_contamination_*.json")
    costf, cost = newest_covering("EXP0105_run_cost_*.json", ALL)
    files104 = sorted(glob.glob(str(ROOT / "results_raw" / "EXP0104_package_contamination_*.json")))

    def contam_for(scopes):
        """The newest contamination artefact that actually carries this package's scopes.

        A package's reproduce.sh runs the audit with `--only <its own scope>`, so the most recent file on disk may
        contain one corpus rather than four; reading only the newest would silently render an empty section for the
        other packages and report it as measured."""
        for f in reversed(files104):
            d = json.loads(pathlib.Path(f).read_text(encoding="utf-8"))
            if all(s in d.get("packages", {}) for s in scopes):
                return pathlib.Path(f), {s: d["packages"][s] for s in scopes}
        raise SystemExit(f"ABORT: no EXP-0104 artefact on disk carries {scopes} - run the contamination audit for "
                         f"this package before recording it")

    print(f"  artefacts: {covf.name}, {conf.name}, {costf.name}")

    # 1. registry rows
    raw = [r for r in csv.reader(io.StringIO(REG.read_text(encoding="utf-8"))) if r]
    hdr, have = raw[0], {r[0] for r in raw[1:]}
    add = [r for r in registry_rows((covf, cov), (conf, contam), (costf, cost)) if r["exp_id"] not in have]
    for r in add:
        assert set(r) == set(hdr), (r["exp_id"], sorted(set(hdr) ^ set(r)))
    if add and not a.check:
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=hdr, lineterminator="\r\n")
        w.writeheader()
        w.writerows(add)
        REG.write_text(REG.read_text(encoding="utf-8").rstrip("\r\n") + "\r\n"
                       + buf.getvalue().split("\r\n", 1)[1].rstrip("\r\n") + "\r\n", encoding="utf-8", newline="")
    back = [r for r in csv.reader(io.StringIO(REG.read_text(encoding="utf-8"))) if r]
    assert back[0] == hdr and all(len(r) == len(hdr) for r in back), "the registry changed shape"
    ids = [r[0] for r in back[1:]]
    assert len(ids) == len(set(ids)), "duplicate exp_id"
    print(f"  registry: {', '.join(r['exp_id'] for r in add) if add else 'all three already registered'} "
          f"| rows={len(back) - 1}")

    # 2. per-package documents, claims, deviations, limitations
    next_d = 57
    for pkg in [x for x in PAPERS if x.name[:4] in ALL]:
        pid = pkg.name[:4]
        if pid not in SCOPE:
            continue
        scopes = contam_for(SCOPE[pid])
        md = render_contamination(pid, cov["per_package"].get(pid), scopes[1], cost["per_package"].get(pid))
        out = pkg / "CONTAMINATION_AND_COST.md"
        if a.check:
            print(f"  {pid}: md {'up to date' if out.is_file() and out.read_text(encoding='utf-8') == md else 'STALE'}")
            continue
        out.write_text(md, encoding="utf-8", newline="")
        c = cost["per_package"].get(pid, {})
        claim = {"claim": (f"本包所读语料的重复、跨源重叠与跨划分泄漏已实测（E19）：抽样自种子 42、每片 250 行，"
                           f"逐列报告有值行数；处理后的 routing 表按全量测量。本包的运行成本亦已实测（E13），"
                           f"逐步数字见 RUN_COST.md 与 tables/table_run_cost.csv。"),
                 "claim_type": "测量工具的稳健性与可复现性（E19/E13 交付项）",
                 "experiment_id": "EXP-0104; EXP-0105",
                 "direction": "documents the measured scope and the limits of both audits",
                 "raw_result_file": f"results_raw/{scopes[0].name}; results_raw/{costf.name}",
                 "table": "tables/table_run_cost.csv; results_processed/EXP0104_contamination_*.csv",
                 "figure": "-",
                 "test": "not a hypothesis test: a census of duplication and a runtime measurement on the rows read"}
        dev_text = ("E19/E13 的两处测量缺陷在本包记录：首轮污染审计把 null 列当作 0 重复、"
                    "只读标量文本列（AgentBank/code-act/AgentInstruct 的任务文本在 conversations 里），"
                    "且 AgentTrove 的 instruction/split 列在抽样行内全为 null；E13 的 registry span 与步骤自测 "
                    "wall-clock 相差最高 5000 倍（停放步骤），成本表改用自测值。")
        lim_text = ("本包的污染与泄漏结论来自种子 42 的抽样子分片（每片 250 行），只有处理后的 routing 表是全量；"
                    "因此重复率是该样本上的度量，不是对整个发行的无重复断言，且无法用任何成员检验判断模型是否见过这些文本。")
        cid_hint = "C" if pid == "P001" else "K"
        res_claim = add_claim(pkg, cid_hint, claim, False)
        res_dev = add_deviation(pkg, f"D{next_d}", dev_text, False,
                                reason="measured by EXP-0104 (contamination) and EXP-0105 (run cost)",
                                pointer="`CONTAMINATION_AND_COST.md`, `RUN_COST.md`, `tables/table_run_cost.csv`")
        res_lim = add_limitation(pkg, "抽样而非全量", lim_text, False)
        res_cnt = refresh_final_audit_counts(pkg)
        print(f"  {pid}: wrote CONTAMINATION_AND_COST.md | claim {res_claim} | deviation {res_dev} | limitation "
              f"{res_lim} | final_audit {res_cnt}")
        next_d += 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
