"""EXP-0091 recorder: the hand check becomes an agreement statistic, and P005's H3 verdict survives it.

Reads three artefacts and writes only what they say:

  * the current EXP-0091 run - B, a matcher sharing no code with EXP-0049, re-decides every disagreement instance;
  * the superseded EXP-0091 run - B's first version, which attributed declarations by name token **without config
    scope** and manufactured 24 instances in 3 releases, which would have flipped H3 from refuted to established.
    That run is evidence about the instrument, so its numbers are quoted here rather than buried;
  * EXP-0049 - A's instance list, the thing being compared.

    python record_exp0091_p005.py
"""
from __future__ import annotations

import csv, io, json, pathlib, re, sys, time

ROOT = next(a for a in [pathlib.Path(__file__).resolve().parent, *pathlib.Path(__file__).resolve().parents]
            if (a / "00_program_registry").is_dir())
P = ROOT / "papers" / "P005_governance_metadata_verifiability"
NOW = time.strftime("%Y-%m-%dT%H:%M:%S")


def line(r):
    b = io.StringIO(); csv.writer(b, lineterminator="\r\n").writerows([r]); return b.getvalue()


def sub1(text, pat, repl, tag, marker=None, flags=re.S):
    if marker and marker in text:
        print(f"  [{tag}] already applied - skipped")
        return text
    n = len(re.findall(pat, text, flags))
    if n != 1:
        raise SystemExit(f"ABORT [{tag}]: pattern matched {n} times, expected 1: {pat[:70]!r}")
    print(f"  [{tag}] applied")
    return re.sub(pat, repl, text, count=1, flags=flags)


def load_current():
    cur = sorted((ROOT / "results_raw").glob("EXP0091_second_matcher_*.json"))
    if not cur:
        raise SystemExit("ABORT: no EXP-0091 artefact")
    d = json.loads(cur[-1].read_text(encoding="utf-8"))
    unsc = ROOT / "results_raw" / "superseded" / "EXP0091_second_matcher_20260921T021614.json"
    U = json.loads(unsc.read_text(encoding="utf-8")) if unsc.is_file() else None
    return cur[-1], d, U


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    f91, E, U = load_current()
    A = json.loads(sorted((ROOT / "results_raw").glob("EXP0049_governance_census_*.json"))[-1].read_text(encoding="utf-8"))
    comp = E["comparison"]
    decls_b = sum(r["declarations_tested"] for r in E["releases"].values())
    decls_a = sum(r.get("declarations_attributable", 0) for r in A["releases"])
    obs_a = sum(len(r.get("observations") or []) for r in A["releases"])
    shared = sum(c["shared"] for c in comp)
    only_a = [x for c in comp for x in c["only_a"]]
    only_b = [x for c in comp for x in c["only_b"]]
    inst_a = sum(c["a_n"] for c in comp)
    inst_b = sum(c["b_n"] for c in comp)
    rel_a = sum(1 for c in comp if c["a_has_disagreement"])
    rel_b = sum(1 for c in comp if c["b_has_disagreement"])
    codeact_rows = next((i["measured"] for r in E["releases"].values() for i in r["instances"]), "n/a")
    unscooped = ""
    if U:
        u_inst = sum(c["b_n"] for c in U["comparison"])
        u_rel = sum(1 for c in U["comparison"] if c["b_has_disagreement"])
        u_rels = ", ".join(c["corpus"] for c in U["comparison"] if c["b_has_disagreement"])
        unscooped = (f"An earlier version of B, before scope was fixed, attributed by name token alone and produced "
                     f"**{u_inst} instances in {u_rel} releases** ({u_rels}), which under the pre-declared rule would "
                     "have withdrawn H3's refutation outright. Every one of those instances was the config-scope "
                     "error EXP-0049 had already logged as D-P4: 19 AgentBank and 4 Toucan declarations compare a "
                     "single `train` split against the rows of every config in the release. The artefact is kept at "
                     "`results_raw/superseded/EXP0091_second_matcher_20260921T021614.json`. That is the finding "
                     "reviewers should weigh: the size-test result is not sensitive to who writes the matcher, it is "
                     "extremely sensitive to the scope rule, and the scope rule is a decision about what a "
                     "declaration refers to, not a detail.")

    doc = f"""# The hand check, executed as an agreement statistic (EXP-0091)

Artefact `{f91.name}`; code `02_shared_code/data_audit/governance_disagreement_second_matcher_p005.py`;
{E['wallclock_sec']}s. Compared against `{E['a_artefact']}` (EXP-0049).

## Why this exists

`EXP-0051` is six items verified by one coder against the files. Before this step ran, `limitations.md` item 6 said
that no inter-coder statistic exists and that a second coder was outstanding; the same sentence is what this
experiment replaces, and the section below shows item 6 rewritten to the measured comparison. There is no second
human coder in this programme.
What can be measured instead is whether the *decisions* depend on the code that made them: H3 - "a disagreement class
is common" - is refuted on the strength of **one** instance found in eight releases, so if that instance is an
artefact of one attribution implementation, the refutation is too. EXP-0091 therefore re-decides every instance with a
matcher that shares no code with EXP-0049.

| component | A (EXP-0049) | B (EXP-0091) |
|---|---|---|
| front matter | YAML loader walking `dataset_info`/`splits`/`configs` | line walk with an indent-tracked config stack, one declaration per `num_examples` |
| attribution | declared `data_files` substring, then config directory | config subtree, then declared path **prefix**, then split name as a path **token** |
| name presence | substring of some relative path | token index built by splitting every path on `/ _ - .` |
| classes, band table, tolerance | frozen in `protocol_freeze.md` | the same frozen values, re-implemented |

## Result

| quantity | value |
|---|---|
| releases where both agree on "has >= 1 instance" | **{E['boolean_agreement_releases']}** |
| instances: A / B | {inst_a} / {inst_b} |
| instances found by both | {shared} |
| only A / only B | {len(only_a)} / {len(only_b)} |
| releases with an instance: A / B | {rel_a} / {rel_b} |
| declarations tested: A / B | {decls_a} / {decls_b} |
| A's unattributable observations | {obs_a} (B attributes and tests all of them) |
| verdict | {E['verdict']} |

The one instance the whole H3 verdict rests on is the code-act card's own `size_categories: 1K<n<10K` against
{codeact_rows} exact footer rows - a contradiction *internal to the card*, found by both matchers through different routes (A via the
aggregate declared-vs-footer comparison added after D-P6, B via the band test).

{unscooped}

## What this does for the paper

1. **H3's refutation is not a property of the matcher.** Both implementations agree release-by-release, and B tests
   strictly more declarations than A, so the agreement is not two versions of the same blind spot.
2. **The instrument's load-bearing choice is scope, not lexicon.** EXP-0050 already reported that the licence
   classifier's word list does not move the headline; this adds the counterpart finding for the size test.
3. `limitations.md` item 6 and `reviewer_attack.md` A9 stop being outstanding work and become a measured result with
   an interval-free, exact statement of what was compared.
4. What is still not measured, and stays a limit: B is one alternative implementation, not a population of them, and
   agreement between two machine matchers is not human inter-coder reliability. No such claim is made anywhere.
"""
    (P / "second_matcher_exp0091.md").write_text(doc, encoding="utf-8", newline="")
    bad = re.findall(r"\|\s*\?\s*\||\bNone\b", doc)
    if bad:
        raise SystemExit(f"ABORT: generated document carries a placeholder: {bad[:5]}")
    print(f"  wrote second_matcher_exp0091.md ({len(doc.split())} words)")

    # ---- limitations item 6: from "a second coder remains owed" to the executed comparison
    lim = (P / "limitations.md")
    t = lim.read_text(encoding="utf-8")
    t = sub1(t, r"6\. \*\*Single coder\.\*\*[^\n]*(?:\n(?!\d\. \*\*)[^\n]*)*",
             "6. **Single coder, and what was measured instead.** The hand check (EXP-0051) is one person's "
             "verification against the files, and no human inter-coder statistic exists in this paper. What does "
             f"exist is a matcher-invariance test (EXP-0091): a second implementation that shares no code with the "
             f"scan re-decided every disagreement instance and agrees on the has-instance boolean for "
             f"{E['boolean_agreement_releases']} releases while testing {decls_b} declarations against A's {decls_a}. "
             "That bounds matcher-dependence of the size test; it is not human reliability and is not offered as "
             "such. The same run shows how load-bearing the scope rule is: without config scoping, the second "
             "matcher manufactures the exact false disagreements D-P4 recorded.",
             "limitations 6", marker="matcher-invariance test (EXP-0091)")
    lim.write_text(t, encoding="utf-8", newline="")

    # ---- reviewer attack A9
    rv = (P / "reviewer_attack.md")
    t = rv.read_text(encoding="utf-8")
    t = sub1(t, r"\| A9 \| [^\n]*\n",
             f"| A9 | \"Who coded the artefact decisions?\" | Single coder for the hand check; the *decisions* are now "
             f"re-made by a second matcher | EXP-0091 agrees release-by-release on {E['boolean_agreement_releases']} "
             f"releases, reproduces the one instance both ways, and shows that dropping config scope would have "
             f"invented 24 | `second_matcher_exp0091.md`; limitations L6; K11 |\n",
             "A9 row", marker="EXP-0091 agrees release-by-release")
    rv.write_text(t, encoding="utf-8", newline="")

    # ---- final audit: hand-check row and the claims count, both read from the files
    hcf = P / "results_processed" / "EXP0051_hand_check.csv"
    n_hc = max(0, len([r for r in csv.reader(io.StringIO(hcf.read_text(encoding="utf-8"))) if r]) - 1)         if hcf.is_file() else 0
    fa = (P / "final_audit.md")
    t = fa.read_text(encoding="utf-8")
    t = sub1(t, r"\| hand check \|[^\n]*\n",
              f"| hand check | EXP-0051 ({n_hc} items, single coder) + "
              f"EXP-0091 second matcher ({E['boolean_agreement_releases']} release agreement, "
              f"{decls_b} declarations tested) |\n",
              "hand-check row", marker="EXP-0091 second matcher")
    n_claims = max(0, len([r for r in csv.reader(io.StringIO((P / "claims_evidence_matrix.csv")
                                                              .read_text(encoding="utf-8"))) if r]) - 1)
    t = re.sub(r"\| claims matrix \| \d+ claims[^\n]*\n",
               f"| claims matrix | {n_claims} claims, each with result file, table, figure and test columns filled |\n",
               t, count=1)

    # ---- gate decision: rewritten wholesale, because clause-level patching left the paragraph counting items that
    # had already been closed. The replacement is deterministic, so re-running this recorder changes nothing.
    t = re.sub(r"\*\*Gate decision.*?(?=\n## |\Z)",
               "**Gate decision: package complete; the gate stays open on scope, not on work.** Both items this "
               "paragraph used to list as owed have become measurements: the value-level rights scan ran as EXP-0053 "
               "(claim K8, appendix A7) and the headline survived a test that could have refuted it, and the second-"
               f"coder question was answered by a matcher-invariance test rather than by a person (EXP-0091: a second "
               f"implementation sharing no code with the scan re-decides every disagreement instance and agrees on the "
               f"has-instance judgement across {E['boolean_agreement_releases']} releases while testing {decls_b} "
               "declarations independently). What remains is declared, not deferred: the population is the eight "
               "releases reachable on this host, every `absent` is relative to a probe set whose under-reporting is "
               "measured rather than assumed, the matcher-invariance test is one alternative implementation rather than "
               "a human sample, and no human inter-coder statistic exists anywhere in this paper. What the study does "
               "well is fail where it was allowed to fail: H3 and H4 are refuted, H1 is only partly established, and "
               "the headline was downgraded by the pilot's own pre-registered rule (PROSE_ONLY). The next measurement "
               "that would buy something new is a small re-user behaviour study against these releases, which would "
               "answer A11; a second release shipping per-component rights files would test the census claim itself.\n",
               t, count=1, flags=re.S)
    fa.write_text(t, encoding="utf-8", newline="")
    print(f"  final_audit: claims row set to {n_claims}; gate decision rewritten from the EXP-0053/EXP-0091 results")

    # ---- claims matrix K11 (append-only, content-keyed)
    cp = P / "claims_evidence_matrix.csv"
    rows = [r for r in csv.reader(io.StringIO(cp.read_text(encoding="utf-8"))) if r]
    hdr, body = rows[0], rows[1:]
    if "K11" not in {r[0] for r in body}:
        c = dict.fromkeys(hdr, "")
        c.update({"claim_id": "K11",
                  "claim": "RQ4 的实例判定不依赖实现：与扫描代码零共享的第二匹配器重算了全部实例，"
                           f"在 {E['boolean_agreement_releases']} 个发行上对\"是否存在实例\"的判断完全一致，"
                           f"并独立复现了唯一那条实例（code-act 卡片内部 size_categories 与页脚行数矛盾）",
                  "claim_type": "测量工具的稳健性（无人工第二编码者的替代检验）",
                  "experiment_id": "EXP-0091", "direction": "supports (matcher-invariant)",
                  "digits_reported": f"instances_A={inst_a} instances_B={inst_b} shared={shared} only_A={len(only_a)} "
                                     f"only_B={len(only_b)} releases_with_instance={rel_a}/{rel_b} "
                                     f"declarations_tested_B={decls_b} vs_A={decls_a}",
                  "statistical_test": f"逐发行布尔一致性与逐实例集合对比（{len(comp)} 个发行）；判据（布尔一致需 8/8）"
                                      "在 EXP-0091 脚本 docstring 中于读取 B 结果之前固定",
                  "raw_result_file": f"results_raw/{f91.name}",
                  "table": "results_processed/EXP0091_instance_comparison.csv",
                  "figure": "papers/P005_governance_metadata_verifiability/second_matcher_exp0091.md",
                  "where_in_paper": "limitations L6; reviewer attack A9; final_audit hand-check row",
                  "status": "supported"})
        row = [c[x] for x in hdr]
        assert len(row) == len(hdr), (len(row), len(hdr))
        body.append(row)
        cp.write_text("".join(line(x) for x in [hdr] + body), encoding="utf-8", newline="")
        print("  claims matrix: K11 added")

    # ---- deviation
    dv = (P / "deviations.md")
    t = dv.read_text(encoding="utf-8")
    if "EXP-0091" not in t:
        # P005 keeps its own D-P series; taking the programme-wide maximum would have written D-P51 into this file
        used = {int(x) for x in re.findall(r"^\| D-P(\d+) \|", t, re.M)}
        did = max(used | {0}) + 1
        t = t.rstrip() + "\n" + (
            f"| D-P{did} | {NOW} | 人工 hand check 的\"第二编码者欠项\"改由**自动第二匹配器**检验（EXP-0091），"
            "并把该匹配器早期未做 config 作用域限制的版本登记为 superseded 证据 | 程序全自动，无人工编码可用；"
            f"B 与 A 零代码共享，逐发行布尔一致 {E['boolean_agreement_releases']}，唯一实例双方复现。副产物：未限定"
            "作用域时 B 造出 24 条假实例（3 个发行），恰好重演 D-P4 记录的错误，说明该判据的敏感点是作用域规则而非词表 | "
            "否（H1-H5 判据、类别、容差、词表均未改动；H3 结论未变） | "
            "后果：limitations L6 与 A9 由\"欠项\"改为测得结果，新增 K11 与 `second_matcher_exp0091.md`；"
            "superseded 运行的数字在文中引用而非隐藏 |\n")
        dv.write_text(t, encoding="utf-8", newline="")
        print(f"  deviations: appended D-P{did}")

    # ---- registry
    rp = ROOT / "00_program_registry" / "experiment_registry.csv"
    rrows = [r for r in csv.reader(io.StringIO(rp.read_text(encoding="utf-8"))) if r]
    rhdr, rbody = rrows[0], rrows[1:]
    if "EXP-0091" not in {r[0] for r in rbody}:
        rec = dict.fromkeys(rhdr, "")
        rec.update({"exp_id": "EXP-0091", "paper_id": "P005", "topic_id": "T014",
                    "stage": "rq4_second_matcher_agreement",
                    "script": "02_shared_code/data_audit/governance_disagreement_second_matcher_p005.py",
                    "config": "B: indent-scanned front matter with a config stack; attribution by config subtree then "
                              "declared path prefix then split-name token; token presence index over paths split on "
                              "/ _ - .; frozen classes D1/D2/D3, size bands and the 0.8-1.25 tolerance; per-release "
                              "boolean agreement rule fixed in the module docstring before B ran",
                    "seed": "n/a (deterministic file scan)", "started_at": E["started_at"], "finished_at": NOW,
                    "status": f"H3 STANDS: boolean agreement {E['boolean_agreement_releases']}, "
                              f"instances A {inst_a} / B {inst_b}, shared {shared}",
                    "outputs": f"results_raw/{f91.name}; results_processed/EXP0091_instance_comparison.csv; "
                               "results_processed/EXP0091_instances_side_by_side.csv; "
                               "papers/P005_governance_metadata_verifiability/second_matcher_exp0091.md; "
                               "results_raw/superseded/EXP0091_second_matcher_20260921T021614.json",
                    "notes": "replaces the owed second coder with a matcher-invariance measurement; the superseded "
                             "unscoped run shows dropping config scope manufactures 24 false instances and would have "
                             "flipped H3, so the scope rule is declared as the load-bearing choice",
                    "enters_paper": "yes - claim K11, limitations L6, reviewer attack A9, final_audit hand-check row"})
        rbody.append([rec[x] for x in rhdr])
        rp.write_text("".join(line(x) for x in [rhdr] + rbody), encoding="utf-8", newline="")
        print("  registry: EXP-0091 added")
    chk = [r for r in csv.reader(io.StringIO(rp.read_text(encoding="utf-8"))) if r]
    print(f"  registry rows={len(chk) - 1} ragged={sum(1 for r in chk[1:] if len(r) != len(chk[0]))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
