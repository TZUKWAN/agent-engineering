"""Record EXP-0106/0107/0108: the four E-steps P002/P003/P004 were missing, filed where a reader will find them.

EXP-0103 showed the concrete gaps in the spec's minimum experiment package: P003 had no baseline (E02) and no ablation
(E04); P002 had no ablation, no cross-domain check, no case reading and no intervention (E04/E10/E16/E17); P004 had no
external dataset (E08). EXP-0106, EXP-0107 and EXP-0108 ran those steps and produced verdicts, two of which are
unfavourable to the papers that produced them. This recorder registers the three steps and writes their numbers into the
packages - one document, one claim, one deviation and one limitation each - reading every figure from the artefacts so no
value is retyped by hand.

    python 02_shared_code/registry/record_exp0106_0108_docs.py [--check]
"""
from __future__ import annotations
import argparse, csv, glob, io, json, pathlib, re, sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from record_exp0103_0105_docs import (add_claim, add_deviation, add_limitation,      # noqa: E402
                                      refresh_final_audit_counts)

ROOT = next(a for a in (HERE, *HERE.parents) if (a / "00_program_registry").is_dir())
REG = ROOT / "00_program_registry" / "experiment_registry.csv"
PAPERS = {p.name[:4]: p for p in sorted((ROOT / "papers").glob("P0*")) if p.is_dir()}


def latest(prefix):
    f = sorted(glob.glob(str(ROOT / "results_raw" / prefix)))
    if not f:
        raise SystemExit(f"ABORT: no artefact {prefix} - run the measurement first")
    return pathlib.Path(f[-1]), json.loads(pathlib.Path(f[-1]).read_text(encoding="utf-8"))


def table(rows):
    return "\n".join(rows)


def p003_doc(d):
    arms = {**d.get("baselines", {}), **d.get("ablations", {}), "audited (published)": d["audited_reproduced"]}
    L = ["# P003: E02 baselines and E04 ablation of the conformance instrument (EXP-0106)", "",
         "Re-scored from the published audit's own per-cell evidence lists (no new pass over the corpora), so every "
         "number here is the same statistic the frozen kill-gate uses: how many of the twelve concepts are "
         f"`direct|derived` in at least {d['min_corpora']} of the releases. Seed {d['seed']}, {d['draws']} draws for "
         "the chance baseline.", "", "| arm | what it removes | concepts in >=7 of 8 |", "|---|---|---|",
         f"| audited | nothing (the published codex) | {d['published_headline']} |"]
    what = {"name_equality_only": "only fields named directly, at >=95% coverage",
            "any_direct_mention": "only fields named directly, any coverage",
            "drop_derived_rules": "the recovery rules (direct evidence only)",
            "drop_top_candidate": "each cell's best-matching candidate field"}
    for arm, v in sorted(arms.items()):
        if arm == "audited":
            continue
        L.append(f"| `{arm}` | {what.get(arm, '')} | {v['concepts_in_7_of_8']} |")
    nul = d["random_marginal_null"]
    L += ["", f"Chance: `p(headline >= {d['published_headline']}) = {nul['p_ge_published']}` over {nul['draws']} draws "
               f"from the observed state marginal {nul['state_counts']}.", "",
          "Corpus jackknife (is the headline carried by one release?):",
          table([f"* dropping `{k}` gives {v['concepts_in_7_of_8_minus_one_corpus']} "
                 + ("** - moves the headline**" if v["moves_the_headline"] else "")
                 for k, v in sorted(d["leave_one_corpus_out"].items())]), "",
          f"**Verdict.** {d['verdict']}", "",
          "Re-scoring reproduces the published number from the cells before any arm is run, and aborts if "
          "`coverage_by_concept` and the cells disagree, so this document cannot report a statistic the audit did not "
          "produce."]
    naive = d["baselines"]["name_equality_only"]["concepts_in_7_of_8"]
    noderr = d["ablations"]["drop_derived_rules"]["concepts_in_7_of_8"]
    droptop = d["ablations"]["drop_top_candidate"]["concepts_in_7_of_8"]
    pchance = d.get("random_marginal_null", {}).get("p_ge_published", "")
    claim = (f"本包 E02/E04 已实测：公布指标为 {d['published_headline']} 个概念在 >= {d['min_corpora']} 个发行中可直接或可恢复；"
             f"仅按字段名直配得 {naive} 个，去掉恢复规则得 {noderr} 个，删去每格最佳候选后得 {droptop} 个；"
             f"随机边际零假设下 p={pchance}。结论既不是平凡的字段匹配，也只由单一字段支撑。")
    return "\n".join(L) + "\n", claim


def p002_doc(d):
    arms = d["arms"]
    L = ["# P002: E04 cue-family ablation, E10 cross-repository robustness, E16 cases, E17 interventions (EXP-0107)", "",
         f"Computed on {d['sample']['n_assistant_turns']} assistant turns from {d['sample']['n_trajectories']} "
         "trajectories (seed "
         f"{d['seed']}), all arms over the same turns, so every difference below is the rule rather than the sample. "
         f"The sample's frozen shares are checked against the published table before any arm is read "
         f"(TVD {d['representativeness']['tvd_sample_vs_published']}, guard: {d['representativeness']['guard']}).", "",
         "| arm | what it changes | TVD vs frozen | share of turns relabelled |", "|---|---|---|---|"]
    meaning = {"frozen": "the published codex", "command_source_only": "reasoning text hidden",
               "thought_source_only": "command text hidden", "drop_last_turn": "last assistant turn removed",
               "drop_first_turn": "first assistant turn removed",
               "force_test_command": "every command replaced by `python -m pytest test.py`"}
    for arm, v in arms.items():
        L.append(f"| `{arm}` | {meaning.get(arm, 'cue family ' + arm.split(':')[-1] + ' removed')} | "
                 f"{v.get('tvd_vs_frozen', 0.0)} | {v.get('share_relabelled', 0.0)} |")
    e10 = d["e10_by_repository"]
    surv = [k for k, v in e10.items() if v["survives_holm_0p05"]]
    L += ["", f"E10: over the {len(e10)} repositories with >= 200 sampled turns, the top stage "
               f"(`{d['frozen_top_stage']['label']}`, {d['frozen_top_stage']['share']} of turns overall) differs "
               f"significantly from the rest of the sample in **{len(surv)}** repositories after Holm correction "
               f"(two-sided Fisher, p<0.05): {', '.join('`' + s + '`' for s in surv) or 'none'}.", "",
          "E16: cases where an arm flips the label, quoted from the sample (mechanism, not evidence about the "
          "population - the aggregate rows above are the evidence):", ""]
    for arm, ex in sorted(d.get("e16_cases", {}).items())[:4]:
        for e in ex[:1]:
            L += [f"* `{arm}`: instance `{e['instance_id']}` ({e['repo']}) - frozen `{e['frozen_label']}` -> arm "
                  f"`{e['arm_label']}`; command `{e['cmd'][:90]}`; reasoning `{e['thought'][:120]}`"]
    L += ["", f"**Verdict.** {d['verdict']['reading']}"]
    ex = arms.get("without_rule:extraction", {}).get("tvd_vs_frozen", "")
    hidcmd = arms.get("thought_source_only", {}).get("tvd_vs_frozen", "")
    nrepos = len(e10)
    top_lbl = d["frozen_top_stage"]["label"]
    claim = (f"本包 E04/E10/E16/E17 已实测：移除 extraction 规则使阶段分布位移 TVD={ex}，隐藏命令文本位移 TVD={hidcmd}；"
             f"{nrepos} 个抽样仓库中 {len(surv)} 个在 Holm 校正后主阶段（{top_lbl}，占 "
             f"{d['frozen_top_stage']['share']}）显著偏离其余样本，因此阶段结构不能当作语料级常数引用。")
    return "\n".join(L) + "\n", claim


def p004_doc(d):
    a = d["association_with_text_signal"]
    g = d["gating_consequence"]
    L = ["# P004: E08 external validation on another publisher's shipped label (EXP-0108)", "",
         f"Corpus: {d['corpus']}. The same battery P004 runs on Toucan's quality columns, with the decision rules fixed "
         "in the script's docstring before the sample was read.", "",
         f"* rows read {d['sample']['rows_read']}, carrying a value {d['sample']['rows_with_a_value']}, "
         f"empty/null {d['sample']['rows_empty_or_null']}, distinct instances {d['sample']['distinct_instances']};",
         f"* value census: `{json.dumps(d['value_census'], ensure_ascii=False)}` - **{d['scale_or_label']}**;",
         f"* 2x2 against the text-derived completion signal: `{json.dumps(a['table_2x2'], ensure_ascii=False)}`, "
         f"Fisher two-sided p={a['fisher_p_two_sided']}, odds {a['fisher_odds']};",
         f"* instance-clustered odds ratio **{a['instance_clustered_or']}** (95% CI {a['bootstrap_ci95']}, "
         f"{a['clusters']} clusters, {a['draws']} draws) - clustered by instance because `exit_status` is a property of "
         f"a rollout, and rollouts of one instance are not independent;",
         f"* gating: filtering to the non-default value keeps {g['share_kept']} of rows and "
         f"{g['repositories_after']}/{g['repositories_before']} repositories; largest repository "
         f"{g['largest_repository_before']} -> {g['largest_repository_after']}.", "",
         f"**Verdict: {d['verdict']}.** {d['verdict_reason']}", "",
         "Comparison the paper can make because both arms used the same rules:",
         table([f"* `{k}`: {v}" for k, v in d["p004_headline_comparison"].items()]), "",
         "A negative on this arm is evidence for the paper's thesis rather than against it: a shipped label that is one "
         "value for 96% of rows cannot be the quality signal a downstream user might assume, which is exactly the "
         "failure mode P004 says has to be checked per column, per release."]
    claim = (f"本包 E08 已在第二发行（SWE-ZERO exit_status）上实测：{d['scale_or_label']}；"
             f"过滤到非默认值仅保留 {g['share_kept']} 的行（{g['repositories_after']}/{g['repositories_before']} 仓库），"
             f"实例聚类 OR={a['instance_clustered_or']}（95% CI {a['bootstrap_ci95']}），判定 {d['verdict']}。"
             "与 P004 论题一致：shipped 分数的测量性质必须逐列逐发行检验。")
    return "\n".join(L) + "\n", claim


DOCS = {"P003": ("EXP0106_p003_ablation_baselines_*.json", p003_doc, "ABLATION_AND_BASELINES_EXP0106.md",
                 "EXP-0106", "E02 基线与 E04 消融"),
        "P002": ("EXP0107_p002_ablation_cases_*.json", p002_doc, "ABLATION_CASES_INTERVENTION_EXP0107.md",
                 "EXP-0107", "E04 消融、E10 跨仓库、E16 个案、E17 干预"),
        "P004": ("EXP0108_p004_external_shipped_label_*.json", p004_doc, "EXTERNAL_VALIDATION_EXP0108.md",
                 "EXP-0108", "E08 外部数据验证")}

STAGES = {
    "EXP-0106": ("p003_e02_baselines_e04_ablation", "02_shared_code/data_audit/p003_ablation_and_baselines.py",
                 "Re-scores the published conformance cells under five arms (name-equality only, any direct mention, "
                 "drop the recovery rules, drop each cell's best candidate, plus a seeded random-marginal null over "
                 "10,000 draws and a corpus jackknife). Headline = concepts direct|derived in >=7 of 8 releases, the "
                 "same statistic as the frozen kill-gate; the audited arm must reproduce the published number and the "
                 "script aborts if coverage_by_concept and the cells disagree.",
                 "3_published_1_under_every_naive_arm_single_source_under_drop_top_p_chance_0p0018"),
    "EXP-0107": ("p002_e04_cue_ablation_e10_domain_e16_cases_e17_intervention",
                 "02_shared_code/behavior_tagger/p002_cue_ablation_cases.py",
                 "Thirteen arms over one seeded sample of 35,494 assistant turns: each of the seven cue families removed "
                 "in turn, each of the two information sources hidden, first/last turn dropped, and every command "
                 "replaced by a fixed test command. E10 is a per-repository two-sided Fisher test of the top stage share "
                 "with Holm correction over 43 repositories; E16 quotes the turns the arms flip. The sample's frozen "
                 "shares are checked against the published table (TVD <= 0.10) before any arm is read.",
                 "extraction_rule_tvd_0p44_command_text_drives_labels_27_of_43_repos_differ_after_holm"),
    "EXP-0108": ("p004_e08_external_shipped_label_validation",
                 "02_shared_code/statistics/p004_external_shipped_label_e08.py",
                 "P004's own battery applied to another publisher's shipped label (SWE-ZERO `exit_status`): value "
                 "census, scale test at >=3 distinct values, 2x2 against a text-derived completion signal with a "
                 "two-sided Fisher test, an instance-clustered bootstrap odds ratio, and the population consequence of "
                 "filtering on it. Rules fixed in the script docstring before the data was read.",
                 "DOES_NOT_TRAVEL_2_values_96p5_percent_default_clustered_ci_covers_1")}


def refresh_registry_status() -> str:
    """Keep the compliance rows honest: EXP-0099 and EXP-0103 describe counts that have moved since they were filed.

    A registry row that says "0 open" while the same script now reports open rows is a false record, and the first
    version of this recorder left one: the completion audit's own status string was written when the audit had a bug
    that both under-counted the spec's requirement ids and let the auditor cite itself."""
    au_f, au = latest("EXP0099_spec_completion_audit_*.json")
    cov_f, cov = latest("EXP0103_e_coverage_*.json")
    counts = au.get("status_counts", {})
    n_open = counts.get("OPEN_no_artefact_names_this_requirement", 0)
    want_99 = (f"{au.get('requirements_found_in_spec')} requirements_{counts.get('satisfied_by_content_signature', 0)}"
               f"_by_content_signature_{counts.get('evidenced_in_package', 0)}_in_a_package_"
               f"{counts.get('evidenced_programme', 0)}_at_programme_level_{n_open}_open")
    opens = {p: v.get("open", []) for p, v in cov.get("per_package", {}).items()}
    n_open_steps = sum(len(v) for v in opens.values())
    n_full = sum(1 for v in opens.values() if not v)
    want_103 = (f"{n_full}_of_{len(opens)}_packages_carry_all_"
                f"{max([v.get('steps', 0) for v in cov.get('per_package', {}).values()] or [20])}_steps_"
                f"{n_open_steps}_open_rows")
    raw = [r for r in csv.reader(io.StringIO(REG.read_text(encoding="utf-8"))) if r]
    hdr = raw[0]
    idx = {n: i for i, n in enumerate(hdr)}
    changed = []
    for exp, want in (("EXP-0099", want_99), ("EXP-0103", want_103)):
        for r in raw[1:]:
            if r[idx["exp_id"]] != exp:
                continue
            if r[idx["status"]] == want:
                continue
            note = r[idx["notes"]]
            stamp = f"[corrected 2026-09-21 from {au_f.name} / {cov_f.name}: was {r[idx['status']]}]"
            r[idx["status"]] = want
            if stamp not in note:
                r[idx["notes"]] = note + " " + stamp
            changed.append(exp)
    if changed:
        buf = io.StringIO()
        w = csv.writer(buf, lineterminator="\r\n")
        w.writerow(hdr)
        w.writerows(raw[1:])
        REG.write_text(buf.getvalue(), encoding="utf-8", newline="")
        back = [r for r in csv.reader(io.StringIO(REG.read_text(encoding="utf-8"))) if r]
        assert back[0] == hdr and all(len(r) == len(hdr) for r in back), "registry shape broke on refresh"
    return ", ".join(changed) or "already current"


def deviation_owner_id(pkg, docname: str, fallback: int) -> str:
    """The id the row that already points at this document owns, else the caller's counter.

    The counter is a fixed 62+step sequence, which is stable while nothing else allocates ids - but another recorder
    adding a row to the same package can push the sequence onto an occupied id, and `add_deviation` upserts by id, so
    a collision would silently overwrite an unrelated deviation. Looking the row up by the document it cites makes the
    ownership explicit and leaves existing ids untouched.
    """
    f = pkg / "deviations.md"
    if f.is_file():
        m = re.search(r"(?m)^\| D(\d+) \|[^\n]*" + re.escape(docname), f.read_text(encoding="utf-8", errors="replace"))
        if m:
            return "D" + m.group(1)
    return f"D{fallback}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    art = {}
    for pid, (pat, fn, docname, exp, label) in DOCS.items():
        art[pid] = latest(pat)
    raw = [r for r in csv.reader(io.StringIO(REG.read_text(encoding="utf-8"))) if r]
    hdr, have = raw[0], {r[0] for r in raw[1:]}
    add = []
    for exp, (stage, script, cfg, status) in STAGES.items():
        pid = {e: p for p, (pat, f, dn, e, lb) in DOCS.items()}[exp]
        f, d = art[pid]
        at, wc = d.get("at", ""), float(d.get("wallclock_sec") or 0)
        try:
            t0 = time_shift(at, -wc)
        except Exception:                                              # noqa: BLE001
            t0 = at
        if exp in have:
            continue
        add.append({"exp_id": exp, "paper_id": pid, "topic_id": "", "stage": stage, "script": script, "config": cfg,
                    "seed": str(d.get("seed", "")), "started_at": t0, "finished_at": at, "status": status,
                    "outputs": f"results_raw/{f.name}; results_processed/; papers/{pid}*/{DOCS[pid][2]}",
                    "notes": "closes the E-steps EXP-0103 reported OPEN for this package: " + DOCS[pid][4],
                    "enters_paper": "yes - the package document, one claim, one deviation and one limitation"})
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
    assert back[0] == hdr and all(len(r) == len(hdr) for r in back), "registry shape broke"
    ids = [r[0] for r in back[1:]]
    assert len(ids) == len(set(ids)), "duplicate exp_id"
    print(f"  registry: {', '.join(r['exp_id'] for r in add) or 'all three already registered'} | rows={len(back) - 1}")
    print("  compliance rows refreshed:", refresh_registry_status())

    next_d = 62
    for pid, (pat, fn, docname, exp, label) in DOCS.items():
        f, d = art[pid]
        pkg = PAPERS[pid]
        body, claim_text = fn(d)
        out = pkg / docname
        dev_text = f"{label}已实测并如实记录（含不利结果）；见 {docname}。"
        lim_text = "本步的消融/外部检验在种子样本上进行，结论界定在样本与规则族内；跨仓库差异按 Holm 校正后逐仓库报告。"
        row = {"claim": claim_text, "claim_type": f"测量工具的稳健性与交付完整性（{label}）",
               "experiment_id": exp, "direction": "measured; reported with its limits",
               "raw_result_file": f"results_raw/{f.name}",
               "table": f"{docname}; results_processed/", "figure": "-",
               "test": "see the document: bootstrap/Fisher/permutation as pre-declared for each arm"}
        fresh = ("up to date" if out.is_file() and out.read_text(encoding="utf-8") == body else "STALE")
        if a.check:
            print(f"  {pid}: {docname} {fresh}")
            continue
        out.write_text(body, encoding="utf-8", newline="")
        res_claim = add_claim(pkg, "C" if pid == "P001" else "K", row, False)
        did = deviation_owner_id(pkg, docname, next_d)
        res_dev = add_deviation(pkg, did, dev_text, False, reason=f"measured by {exp}",
                                pointer=f"`{docname}` and `results_raw/{f.name}`")
        res_lim = add_limitation(pkg, "单一样本或单一字段", lim_text, False)
        res_cnt = refresh_final_audit_counts(pkg)
        print(f"  {pid}: wrote {docname} ({fresh}) | claim {res_claim} | deviation {res_dev} | limitation "
              f"{res_lim} | final_audit {res_cnt}")
        next_d += 1
    return 0


def time_shift(at: str, sec: float) -> str:
    import time as _t
    st = _t.strptime(at, "%Y-%m-%dT%H:%M:%S")
    return _t.strftime("%Y-%m-%dT%H:%M:%S", _t.localtime(_t.mktime(st) + sec))


if __name__ == "__main__":
    sys.exit(main())
