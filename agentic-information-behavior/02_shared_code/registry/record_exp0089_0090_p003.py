"""Record EXP-0089 (blind second auditor) and EXP-0090 (the correction it forced) into P003's package.

What the two runs say, in one line each:

  * EXP-0089 - a second auditor written without access to the per-corpus mapping reproduces the usable verdict on
    87 of 96 cells (kappa 0.7236) and crosses the boundary on 9; both pre-declared tolerance triggers fired, so the
    audit's states are not auditor-independent.
  * EXP-0090 - three of those crossings were real and are corrected: Toucan-1.5M stores `messages` as a JSON string
    and the frozen accessor iterated it as characters, so two message-derived cells were scored `absent` at coverage
    0.0; AgentBank's `Observation:` text was carried by a parser that existed but was never hypothesised for it. The
    all-corpus concept count moves from two to three, so the paper's headline is regenerated, not patched.

Everything below is read from the two artefacts; the script aborts rather than write a sentence whose number it
cannot find. The recorder is idempotent and its guards key on strings the rows themselves write.

    python record_exp0089_0090_p003.py
"""
from __future__ import annotations

import csv, io, json, pathlib, re, sys, time
from collections import Counter

ROOT = next(a for a in [pathlib.Path(__file__).resolve().parent, *pathlib.Path(__file__).resolve().parents]
            if (a / "00_program_registry").is_dir())
P = ROOT / "papers" / "P003_metadata_interoperability"
NOW = time.strftime("%Y-%m-%dT%H:%M:%S")
USABLE = ("direct", "derived")


def line(r):
    b = io.StringIO(); csv.writer(b, lineterminator="\r\n").writerows([r]); return b.getvalue()


def art(pat, must=True):
    f = sorted((ROOT / "results_raw").glob(pat))
    if not f:
        if must:
            raise SystemExit(f"ABORT: no artefact matches {pat!r}")
        return None, None
    return f[-1], json.loads(f[-1].read_text(encoding="utf-8"))


def value(d, *needles, want=(int, float, str, bool)):
    """Fetch a named value anywhere in the artefact, or abort - no '?' placeholders in generated text."""
    stack = [d]
    while stack:
        cur = stack.pop(0)
        if isinstance(cur, dict):
            for k, v in cur.items():
                if any(n.lower() in str(k).lower() for n in needles) and isinstance(v, want):
                    return v
                stack.append(v)
        elif isinstance(cur, list):
            stack.extend(cur)
    raise SystemExit(f"ABORT: none of {needles} found in the artefact - refusing to write a placeholder")


def attribute(cross, fixed):
    """Label each crossing with the rule that produced it, using only fields the artefact measured. A crossing is
    'confirmed' when the corrected probes actually move that cell, which is evidence rather than interpretation."""
    rows = []
    for c in cross:
        key = f"{c['corpus']}:{c['concept']}"
        mech = c.get("mechanism") or {}
        if key in fixed:
            why = (f"confirmed - EXP-0090 moves this cell (probe `{fixed[key]}`), and the carrier is present in "
                   f"{mech.get('b_hit_rows', 0)} of the sampled rows")
            cls = "A miss (corrected)"
        elif mech.get("coverage_if_json_nested_scalars_allowed", 0) >= 0.60:
            why = ("second auditor's own rule: it only treats top-level columns as candidates, and relaxing that "
                   f"single rule raises its coverage to {mech['coverage_if_json_nested_scalars_allowed']}")
            cls = "B limit"
        elif c["concept"] == "C1_trajectory_id":
            vals = mech.get("values_in_id") or {}
            why = ("second auditor decides identity by shape (UUID / long non-numeric string); these values are "
                   f"{', '.join(list(vals)[:3]) or 'short labels'} - the column is a real identifier, the shape test "
                   "is the wrong test")
            cls = "B limit"
        elif c["concept"] == "C12_outcome_signal":
            why = ("second auditor's outcome keyword list does not contain this corpus's vocabulary "
                   f"({', '.join(list((mech.get('values_in_exit_status') or {}))[:3])})")
            cls = "B limit"
        elif any("nested" in str(e.get("source", "")) for e in (c.get("a_evidence") or [])):
            _ae = [e for e in c["a_evidence"] if "nested" in str(e.get("source", ""))]
            why = ("the carrier sits inside a list nested within a JSON-encoded column, which B's one-level JSON "
                   f"expansion does not reach; A's nested probe `{_ae[0]['source']}` covers "
                   f"{_ae[0]['coverage']} of the same rows, so the value is there and B is blind to it")
            cls = "B limit"
        else:
            why = "not attributable to a measured rule difference; reported as an unresolved disagreement"
            cls = "unresolved"
        rows.append((c, cls, why))
    return rows


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    f89, E = art("EXP0089_p003_second_auditor_*.json")
    f90, C = art("EXP0090_p003_conformance_corrected_*.json")
    pre = art("EXP0030_p003_conformance_main_*.json")[1]
    cross = E["crossing_list"]
    fixed = {f"{m['corpus']}:{m['concept']}": m["decided_by"] for m in C["moved_cells"]
             if m["a_state"] == "absent" and m["new_state"] in USABLE}
    att = attribute(cross, fixed)
    n_a_miss = sum(1 for _c, cls, _w in att if cls == "A miss (corrected)")
    n_b = sum(1 for _c, cls, _w in att if cls == "B limit")
    n_unres = sum(1 for _c, cls, _w in att if cls == "unresolved")
    full_new = [k for k, v in C["coverage_by_concept"].items() if v >= len(C["corpora"])]
    full_pre = [k for k, v in pre["coverage_by_concept"].items() if v >= len(pre["corpora"])]
    for label, count in (("A miss", n_a_miss), ("B limit", n_b), ("unresolved", n_unres)):
        print(f"  attribution: {label} = {count}")
    if n_a_miss + n_b + n_unres != len(cross):
        raise SystemExit("ABORT: the attribution table does not cover every crossing")

    tbl = "\n".join(
        f"| {c['corpus']} | {c['concept']} | {c['a_state']} ({c['a_coverage']}) | {c['b_state']} "
        f"({c['b_coverage']}) | {cls} | {why} |"
        for c, cls, why in att)

    doc = f"""# Re-deriving the audit with an auditor that never saw our mapping (EXP-0089), and what it cost us (EXP-0090)

Artefacts `{f89.name}` and `{f90.name}`; code
`02_shared_code/data_audit/canonical_conformance_second_auditor_p003.py` and
`02_shared_code/data_audit/canonical_conformance_corrected_p003.py`; seed {E['seed']};
{E['wallclock_sec']}s + {C['wallclock_sec']}s.

## Why this exists

`protocol_freeze.md` asked for a hand re-derivation of 30 self-audit cells, and `final_audit.md` carried that as the
one item still owed before submission. This programme has no human step, and re-running the frozen auditor against
itself would produce perfect agreement by construction. So the check was re-instantiated the way EXP-0087 and
EXP-0088 were: a **second implementation, written against the constructs rather than against the mapping**, compared
over a census instead of a sample.

* **A** - the frozen audit (EXP-0029/0030): per-corpus lists of candidate columns and named parsers, frozen order.
* **B** - this run: no column list at all. Every node of every row is walked (top-level columns, nested dicts and
  lists, JSON strings expanded), and each concept is decided by a value-shape signature - identifiers by their form,
  timestamps by theirs, message sequences by lists of dicts carrying a role key and a content key. Direct vs derived
  is structural: reachable as a top-level column node means direct.

The cut-points are A's ({value(E['thresholds'], 'direct')} / {value(E['thresholds'], 'derived')} /
{value(E['thresholds'], 'signal_floor')}), because the object under test is the mapping, not the thresholds. All
{E['n_cells']} corpus x concept cells were re-derived rather than the 30 sampled ones: 21 of those 30 are `absent`,
and a chance-corrected statistic on a one-class panel is not a check (the failure mode that made EXP-0087's first
panel degenerate).

## Agreement

| quantity | value |
|---|---|
| exact state agreement | {E['exact_state_agreement']} |
| usable-set agreement (direct|derived vs the rest) | **{E['usable_agreement']}** |
| Cohen kappa over the five states | {E['cohen_kappa_states']} |
| cells crossing the usable boundary | {E['boundary_crossings']} |
| A said `absent`, B found it | {E['a_under_reports']} |
| A said usable, B did not | {E['a_over_reports']} |
| pre-declared tolerances | under >= 3, over >= 3 (both fired) |
| B parse-error rows | {E['b_error_rows']} |

B has no `conflict` state, so A's {E['a_conflict_cells']} conflict cell(s) count as disagreements by construction
({E['b_label_note']}).

## Every crossing, attributed to a measured rule

Attribution is evidence, not narration: a cell is called a real A miss only when the corrected probes (EXP-0090)
actually move it. Of {len(cross)} crossings, **{n_a_miss} are confirmed A misses**, {n_b} are the second auditor's own
structural limits, and {n_unres} could not be attributed to a rule difference and stays reported as unresolved.

| corpus | concept | A (coverage) | B (coverage) | class | measured reason |
|---|---|---|---|---|---|
{tbl}

## The defect, and the irony

Toucan-1.5M stores `messages` as a **JSON string**: {C['dialect']['Toucan-1.5M']['rows_with_json_string_messages']:,}
of {C['corpora']['Toucan-1.5M']['n_rows']:,} sampled rows parse as JSON text rather than arriving as a list. The
frozen accessor is `list(m or [])`, which on a string returns a list of characters, so every message-derived parser
for that corpus returned nothing and the cell was scored `absent` with coverage 0.0 - while the roles
`assistant|function|system|user` are in the file (B measured them at 100% coverage). AgentBank's observations are
carried by an `Observation:` prefix whose parser exists in the same module but was only ever hypothesised for
SWE-ZERO. Storage dialect across all eight corpora is censused in `{f90.name}` rather than illustrated.

P003's subject is metadata a pipeline assumes is present and silently is not. Our own instrument failed for exactly
that reason, and only an auditor written without access to our mapping found it.

## What EXP-0090 changed

Corrected probes were **appended after** the frozen candidate list, so no frozen cell can be displaced by a new one;
same rows (sample size asserted against A per corpus), same thresholds, same concept list, same gate.

* {C['n_moved']} cells change state; {C['n_absent_to_usable']} cross `absent` -> usable
  ({', '.join(fixed)})
* all-corpus concepts: {len(full_pre)} ({', '.join(full_pre)}) -> **{len(full_new)}** ({', '.join(full_new)})
* observation recoverability: {pre['coverage_by_concept']['C11_observation']}/8 ->
  {C['coverage_by_concept']['C11_observation']}/8
* role vocabulary recoverability: {pre['coverage_by_concept']['C7_role_vocabulary']}/8 ->
  {C['coverage_by_concept']['C7_role_vocabulary']}/8
* loss ratio: Toucan-1.5M {C['a_loss_ratios']['Toucan-1.5M']} -> {C['loss_ratios']['Toucan-1.5M']};
  AgentBank {C['a_loss_ratios']['AgentBank']} -> {C['loss_ratios']['AgentBank']}
* kill gate: {C['gate']['a_concepts_passing']} -> {C['gate']['concepts_passing']} concepts passing the 7-corpus test,
  so the paper's conclusion is unaffected while its numbers are

`paper.md`, the claims matrix, `tables/table_coverage_matrix.csv` and the heatmap were regenerated from the corrected
matrix by `write_paper.py` / `build_package.py`; the headline sentence now takes its count and concept names from the
matrix rather than from prose, which is why "two of twelve" became "three of twelve" without anyone editing it.
Section 5.4's closing claim - that one probe fix moved one cell and so the verdicts are robust to probe fixes - is
withdrawn in the same regeneration: it was an over-generalisation from n=1, and this is the counterexample.

## What this does not settle

* B is also a rule set. Agreement between two implementations bounds auditor-dependence; it is not ground truth, and
  the {n_unres} unresolved crossing(s) stay unresolved.
* The census is over the same {sum(C['corpora'][k]['n_rows'] for k in C['corpora']):,} sampled rows as A, so it tests
  the mapping, not the sampling (EXP-0036 did that separately).
* A third auditor would move more cells. The honest claim is the one now printed in limitations 4: every `absent` is
  an upper bound on what the release carries, relative to the probe set that produced it.
"""
    (P / "second_auditor_exp0089.md").write_text(doc, encoding="utf-8", newline="")
    bad = re.findall(r"\|\s*\?\s*\||None|\{[a-z_]+\}", doc)
    if bad:
        raise SystemExit(f"ABORT: generated document still carries a placeholder or an unfilled field: {bad[:5]}")
    print(f"  wrote second_auditor_exp0089.md ({len(doc.split())} words)")

    # ---- deviations (guard keys on text this row itself writes)
    dv = (P / "deviations.md")
    txt = dv.read_text(encoding="utf-8")
    if "EXP-0089" not in txt:
        used = set()
        for f in (ROOT / "papers").glob("*/deviations.md"):
            used |= {int(x) for x in re.findall(r"^\| D(\d+) \|", f.read_text(encoding="utf-8"), re.M)}
        did = max(used | {0}) + 1
        txt = txt.rstrip() + "\n" + (
            f"| D{did} | {NOW} | 冻结审计的 ingest 缺陷由第二审计员发现并更正（EXP-0089 -> EXP-0090；论文标题数字随之重算） | "
            "EXP-0089 用不看映射的第二套判定器重算 96 格，9 格跨过 usable 边界；其中 Toucan 的 C7/C11 与 AgentBank 的 C11 "
            f"经 EXP-0090 追加探针后确实由 absent 变为 usable（{C['n_absent_to_usable']} 格）。根因：Toucan 的 messages 列是 "
            "JSON 字符串，冻结访问器 `list(m or [])` 把字符串按字符迭代，故该语料所有 message 派生概念静默为 0 | "
            "是（受影响数字全部重算，未改动判据/概念表/门槛） | "
            f"后果：全部-corpus 概念数 {len(full_pre)}->{len(full_new)}，observation {pre['coverage_by_concept']['C11_observation']}"
            f"/8->{C['coverage_by_concept']['C11_observation']}/8，Toucan loss {C['a_loss_ratios']['Toucan-1.5M']}"
            f"->{C['loss_ratios']['Toucan-1.5M']}，AgentBank {C['a_loss_ratios']['AgentBank']}"
            f"->{C['loss_ratios']['AgentBank']}；kill gate 不变（{C['gate']['concepts_passing']}）；"
            "5.4 节由单次探针修补外推的稳健性结论撤回；EXP-0030 矩阵改列为更正前对照，EXP-0090 为引用矩阵 |\n")
        dv.write_text(txt, encoding="utf-8", newline="")
        print(f"  deviations: appended D{did}")

    # ---- registry
    rp = ROOT / "00_program_registry" / "experiment_registry.csv"
    rrows = [r for r in csv.reader(io.StringIO(rp.read_text(encoding="utf-8"))) if r]
    rhdr, rbody = rrows[0], rrows[1:]

    def add(exp, stage, script, cfg, status, outputs, notes, started, enters):
        if exp in {r[0] for r in rbody}:
            print(f"  registry: {exp} already present - skipped")
            return
        rec = dict.fromkeys(rhdr, "")
        rec.update({"exp_id": exp, "paper_id": "P003", "topic_id": "T012", "stage": stage, "script": script,
                    "config": cfg, "seed": str(E["seed"]), "started_at": started, "finished_at": NOW,
                    "status": status, "outputs": outputs, "notes": notes, "enters_paper": enters})
        rbody.append([rec[x] for x in rhdr])

    add("EXP-0089", "instrument_verification_second_auditor",
        "02_shared_code/data_audit/canonical_conformance_second_auditor_p003.py",
        f"blind second auditor: shape signatures over every row node (no access to pilot.SPEC); same rows and same "
        f"frozen cut-points 0.95/0.60/0.05; {E['n_cells']} cells (8 corpora x 12 concepts), seed {E['seed']}; "
        "tolerances under>=3 / over>=3 fixed in the module docstring before B ran",
        f"CROSSED ON {E['boundary_crossings']} of {E['n_cells']}: usable agreement {E['usable_agreement']}, "
        f"kappa {E['cohen_kappa_states']}, exact {E['exact_state_agreement']}",
        f"results_raw/{f89.name}; results_processed/EXP0089_cell_rederivation.csv; "
        "papers/P003_metadata_interoperability/second_auditor_exp0089.md; "
        "results_raw/superseded/EXP0089_p003_second_auditor_20260921T014435.json",
        "replaces the 30-cell hand re-derivation with a measured census; detected the ingest defect EXP-0090 fixes; "
        "both tolerance triggers fired, so the audit's states are not auditor-independent",
        E["started_at"], "yes - claim K9, limitations 2 and 4, reviewer attack A9, final_audit gate decision")
    add("EXP-0090", "instrument_correction_after_second_auditor",
        "02_shared_code/data_audit/canonical_conformance_corrected_p003.py",
        "corrected probes (JSON-decoding message accessor, function/observation role vocabulary, Observation: prefix) "
        "appended AFTER the frozen candidate list, so frozen precedence is untouched; same rows per corpus (asserted "
        "against EXP-0030 n_rows), same thresholds, same concept list, same gate",
        f"{C['n_moved']} cells change state, {C['n_absent_to_usable']} cross absent->usable; all-corpus concepts "
        f"{len(full_pre)}->{len(full_new)}; gate unchanged at {C['gate']['concepts_passing']}",
        f"results_raw/{f90.name}; results_processed/EXP0090_coverage_matrix.csv; "
        "results_processed/EXP0090_moved_cells.csv; "
        "results_raw/superseded/EXP0090_p003_conformance_corrected_20260921T015237.json",
        "the corrected matrix is what the paper cites; EXP-0030 kept as the pre-correction comparison; the root cause "
        "is a JSON-string message column read as characters by the frozen accessor",
        C["started_at"], "yes - claim K1/K2 regenerated from this matrix; claim K10; section 5.5; deviations")
    rp.write_text("".join(line(x) for x in [rhdr] + rbody), encoding="utf-8", newline="")
    chk = [r for r in csv.reader(io.StringIO(rp.read_text(encoding="utf-8"))) if r]
    print(f"  registry rows={len(chk) - 1} ragged={sum(1 for r in chk[1:] if len(r) != len(chk[0]))}")

    # ---- reproduce.sh is a source-maintained file (D21), so this verifies rather than edits it: the two new steps
    # and this recorder must be wired ahead of the document generators, which now read their artefacts.
    sh = P / "reproduce.sh"
    s = sh.read_text(encoding="utf-8")
    for needle in ("canonical_conformance_second_auditor_p003.py", "canonical_conformance_corrected_p003.py",
                   "record_exp0089_0090_p003.py"):
        if needle not in s:
            raise SystemExit(f"ABORT: reproduce.sh does not run {needle} - the paper would regenerate from a matrix "
                             "that reproduce cannot produce")
    if s.index("record_exp0089_0090_p003.py") > s.index("write_paper.py"):
        raise SystemExit("ABORT: reproduce.sh runs the recorder after write_paper.py, so the deviation count printed "
                         "in final_audit.md would lag the file it describes")
    print("  reproduce.sh verified: auditor, correction and recorder are wired before the generators")

    # §0 item 9 asks for an *independent* package, so a path this step registers in the experiment registry has to
    # resolve inside the package too. The two analysis scripts write their summaries to the workspace-level
    # `results_processed/`, which left P003's manuscript citing a file that only existed one directory above the
    # package; the artefacts are copied here, byte for byte, rather than cited from outside.
    import shutil
    for _rel in ("results_processed/EXP0089_cell_rederivation.csv",
                 "results_processed/EXP0090_coverage_matrix.csv",
                 "results_processed/EXP0090_moved_cells.csv"):
        _src, _dst = ROOT / _rel, P / _rel
        if _src.is_file():
            _dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(_src, _dst)
            print(f"  package copy: {_rel} ({_dst.stat().st_size} B)")
        elif not _dst.is_file():
            raise SystemExit(f"ABORT: {_rel} exists neither at the workspace root nor in the package - the registry "
                             "row would cite an artefact nobody can open")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
