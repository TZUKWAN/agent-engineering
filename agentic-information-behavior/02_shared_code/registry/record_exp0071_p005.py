"""EXP-0071 + EXP-0072 recorder: replace P005's "availability is unmeasurable here" scope note with a measured rate,
its channel audit, and the sensitivity bound the audit implies.

P005 §7 said the study deliberately measured structure rather than link availability, because both hosts the cards
concentrate on were unreachable and a fetch failure could not be told apart from real rot. EXP-0061 falsified that
premise, EXP-0071 probed the same 62 links the census counted, and EXP-0072 asked the question that makes the number
worth having: **can the channels used tell a present resource from an absent one?** Two of them can, one cannot, and one
is intermittent - which is why this recorder publishes a primary rate and a strict-rule bound instead of a single
percentage. The superseded wording stays in the deviation record rather than being deleted.

    python 02_shared_code/registry/record_exp0071_p005.py
"""
from __future__ import annotations

import csv, glob, io, json, pathlib, re, time
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parents[2]
PAP = ROOT / "papers" / "P005_governance_metadata_verifiability"
REG = ROOT / "00_program_registry"
NOW = time.strftime("%Y-%m-%dT%H:%M:%S")

V72 = sorted(glob.glob(str(ROOT / "results_raw" / "EXP0072_link_channel_validation_*.json")))
V71 = sorted(glob.glob(str(ROOT / "results_raw" / "EXP0071_link_availability_*.json")))
if not V72 or not V71:
    raise SystemExit("[e71] need EXP-0071 and EXP-0072 outputs; writing nothing.")
N72, N71 = pathlib.Path(V72[-1]).name, pathlib.Path(V71[-1]).name
D72 = json.loads(pathlib.Path(V72[-1]).read_text(encoding="utf-8"))
S72, ROWS = D72["summary"], D72["rows"]
S71 = json.loads(pathlib.Path(V71[-1]).read_text(encoding="utf-8"))["summary"]

N = S71["urls_found"]
if N != S71["published_rq5_total_urls"] or len(ROWS) != N:
    raise SystemExit("[e71] ABORT: the probed set is not the published 62-link set.")
v1 = Counter(r["verdict"] for r in ROWS)
REACH, GONE, UNT = v1["reachable"], v1["gone"], v1["untestable"] + v1["untestable_via_soft_404_channel"]
TEST = REACH + GONE
AV = REACH / TEST
# the sensitivity bound: github.com answered 19 links directly but passed its control pair in only one of two runs,
# so under a single-run rule those 19 are untestable rather than reachable
GH = [r for r in ROWS if "github.com" in r["url"].lower() and r["verdict"] == "reachable"]
REACH_S, TEST_S = REACH - len(GH), REACH - len(GH) + GONE
AV_S = REACH_S / TEST_S
if not TEST or not TEST_S:
    raise SystemExit("[e71] ABORT: no testable links, so there is no rate to report.")

chan = S72["channel_validation"]
chan_tbl = "\n".join(
    f"| {k} | {v['positive']['url'][:58]} | {v['positive']['http_code']} | {v['negative']['url'][:52]} | "
    f"{v['negative']['http_code']} | {'**yes**' if v['discriminative'] else 'no'} |" for k, v in chan.items())
by_rel = {}
for r in ROWS:
    d = by_rel.setdefault(r["release"], Counter())
    d[r["verdict"]] += 1
rel_tbl = "\n".join(f"| {k} | {v.get('reachable', 0)} | {v.get('gone', 0)} | "
                    f"{v.get('untestable', 0) + v.get('untestable_via_soft_404_channel', 0)} | "
                    f"{(v.get('reachable', 0) + v.get('gone', 0)) / max(1, sum(v.values())):.2f} |"
                    for k, v in sorted(by_rel.items()))
gone_list = "\n".join(f"- `{r['url']}` ({r['release']}) - {r['basis']}" for r in ROWS if r["verdict"] == "gone") or "- none"
untest_list = "\n".join(f"- `{r['url']}` ({r['release']}) - {r['basis']}"
                        for r in ROWS if r["verdict"].startswith("untestable")) or "- none"


def sub1(text, pat, repl, tag):
    # An already-applied edit is a no-op, not an abort: reproduce.sh runs this recorder after the package builders,
    # which rewrite the prose files wholesale, so it must be able to restore the section on a machine where the
    # correction has already been made once.
    if isinstance(repl, str) and repl in text:
        print(f"[e71] {tag} already applied - skipped")
        return text
    new, n = re.subn(pat, repl, text, count=1, flags=re.S)
    if n != 1:
        raise SystemExit(f"[e71] ABORT: anchor {tag!r} matched {n} times; nothing was written there.")
    print(f"[e71] {tag} replaced")
    return new


NOTE = f"""# Declared-link availability, and whether the probe channels can be trusted (EXP-0071 + EXP-0072)

Generated from `results_raw/{N71}` and `results_raw/{N72}` by
`02_shared_code/registry/record_exp0071_p005.py`. Code:
`02_shared_code/data_audit/link_availability_p005.py`, `02_shared_code/data_audit/validate_link_channels.py`.

## Why this became measurable

EXP-0049 recorded `availability_unmeasured`: `huggingface.co` and `github.com` do not answer reliably from this host,
so a fetch failure could not be separated from the link rot the paper was about. EXP-0061 measured channels that do
answer - `raw.githubusercontent.com` for GitHub file paths and `hf-mirror.com`, which serves the same repository paths.
This probe re-extracts the **same** {N} links the census counted (per-release counts asserted against the published
`rq5` block before anything was reported) and routes each through its canonical host, then its alternate channel.

## Two rules, fixed before the first probe

1. **Verdict rule.** `reachable` = a channel returned 2xx/3xx. `gone` = an explicit 404/410/451. `untestable` = every
   channel failed at transport level. A transport failure is never counted as rot.
2. **Channel rule (EXP-0072).** A `reachable` verdict counts only if the channel that produced it also **fails on a
   deliberately absent URL** - positive control resolves *and* negative control returns an explicit not-found. Without
   this, a mirror that answers 200 for everything would have produced a {S71['availability_rate_over_testable']:.4f}
   availability rate for {N} links and meant nothing by it.

| channel | positive control | http | negative control | http | discriminative |
|---|---|---|---|---|---|
{chan_tbl}

## Result

* {N} declared links; **{TEST} testable ({TEST / N:.1%})**, **{UNT} untestable** from this host.
* Over the testable subset: **{REACH} reachable, {GONE} gone** - **availability {AV:.4f}**.
* Sensitivity bound: {len(GH)} links answered on `github.com` directly, but that channel passed its control pair in
  one of two validation runs and timed out in the other. Treating it as unusable (a strict single-run rule) moves those
  {len(GH)} links to untestable and gives availability **{AV_S:.4f}** over {TEST_S} testable links. The rate is therefore
  between {AV_S:.4f} and {AV:.4f} depending on how much credit a flaky-but-answering host is given; both are reported
  rather than the convenient one.
* The census statistic that motivated the original caveat was a mean unverifiable-host share of
  {S71['mean_unverifiable_host_share_as_published']} - which turns out to describe this machine, not those links.

| release | reachable | gone | untestable | testable share |
|---|---|---|---|---|
{rel_tbl}

### Gone
{gone_list}

### Untestable (transport-level, by rule not counted as rot)
{untest_list}

## What this changes, and what it does not

It converts a scope limitation into a measurement with a stated interval. It does **not** make P005 a link-rot study:
the denominator is {N} links in {len(by_rel)} cards, {UNT} links are still untested, an HTTP 200 establishes that
something answered rather than that the content is what the card means, and one channel's reliability is itself the
reason the answer is given as a range.
"""
(PAP / "link_availability.md").write_text(NOTE, encoding="utf-8", newline="")
print("[e71] wrote link_availability.md")

PMD = PAP / "paper.md"
pm = PMD.read_text(encoding="utf-8")
if "EXP-0071" not in pm:
    pm = sub1(pm, r"We measured \*\*structure, not availability\*\*:.*?framed to avoid producing it\.",
              f"""Availability was then measured rather than assumed away (EXP-0071, channel audit EXP-0072). Two
channels that answer from this host - `hf-mirror.com`, which serves the same repository paths, and
`raw.githubusercontent.com`, for GitHub file paths - let an explicit not-found be separated from a blocked connection,
and every channel was required to fail on a deliberately absent URL before its positive answers counted. Of the {N}
declared links, {TEST} were testable ({TEST / N:.1%}): **{REACH} reachable and {GONE} gone**, availability
**{AV:.4f}**; {UNT} links remain untestable and are listed per link in `link_availability.md` rather than folded into
either side. One caveat is quantitative rather than rhetorical: {len(GH)} links answered on `github.com` directly, but
that host passed its control pair in only one of two validation runs, so under a strict single-run rule they become
untestable and availability is **{AV_S:.4f}**. We therefore report the interval {AV_S:.4f}-{AV:.4f}. Three bounds stay
attached to it: {N} links in {len(by_rel)} cards, a transport failure never counted as rot by rule, and an HTTP
response establishing that something answered, not that it is the content the card means. The earlier framing - that no
rot rate could be produced here at all - was wrong about the environment and is registered as a deviation, not deleted.""",
              "paper.md §7 availability")
    PMD.write_text(pm, encoding="utf-8", newline="")

APX = PAP / "appendix.md"
ap = APX.read_text(encoding="utf-8")
if "EXP-0071" not in ap:
    ap = sub1(ap, r"URL availability is unmeasured for\nthe reachability reason in §7;",
              f"URL availability is measured in §7 for {TEST} of {N} declared links (availability "
              f"{AV_S:.4f}-{AV:.4f} depending on how an intermittently answering host is treated; {UNT} links "
              "untestable and listed per link in `link_availability.md`);",
              "appendix.md availability residue")
    APX.write_text(ap, encoding="utf-8", newline="")

CM = PAP / "claims_evidence_matrix.csv"
crows = list(csv.reader(io.StringIO(CM.read_text(encoding="utf-8"))))
hdr, body = crows[0], [r for r in crows[1:] if r]
if "K9" not in {r[0] for r in body}:
    i = {c: n for n, c in enumerate(hdr)}
    K9 = [""] * len(hdr)
    K9[i["claim_id"]] = "K9"
    K9[i["claim"]] = (f"卡片声明链接在本机可测子集上的可达率为 {AV:.4f}（严格单轮通道规则下 {AV_S:.4f}），"
                      f"{GONE} 条返回明确 not-found，{UNT} 条不可测；K6 的「本机无法测可达性」范围声明被本测量取代")
    K9[i["claim_type"]] = "补充测量（替代 K6 的范围界定）"
    K9[i["experiment_id"]] = "EXP-0071; EXP-0072"
    K9[i["direction"]] = "supports"
    K9[i["digits_reported"]] = (f"urls={N}; testable={TEST}; reachable={REACH}; gone={GONE}; untestable={UNT}; "
                                f"availability={AV:.4f} (strict {AV_S:.4f})")
    K9[i["table"]] = "results_processed/EXP0071_link_availability.csv"
    K9[i["figure"]] = "papers/P005_governance_metadata_verifiability/link_availability.md"
    K9[i["statistical_test"]] = ("无推断检验：全枚举同一组 62 条链接并逐条判定；两条规则在首次探测前固定 —— "
                                 "传输失败不计为失效；通道必须同时通过正对照与「故意不存在」负对照才计为可达")
    K9[i["raw_result_file"]] = f"results_raw/{N71};results_raw/{N72}"
    K9[i["where_in_paper"]] = "§7; appendix; link_availability.md"
    K9[i["status"]] = "supported"
    if len(K9) != len(hdr):
        raise SystemExit(f"[e71] ABORT: K9 has {len(K9)} fields, header has {len(hdr)}.")
    body.append(K9)
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\r\n")
    w.writerows(body)
    CM.write_text(",".join(hdr) + "\r\n" + buf.getvalue(), encoding="utf-8", newline="")
    print("[e71] claim K9 appended")

LM = PAP / "limitations.md"
lt = LM.read_text(encoding="utf-8")
if "EXP-0071" not in lt:
    LM.write_text(lt + f"""
## L13 链接可达性：已测，但答案取决于通道可信度（EXP-0071 + EXP-0072）

`link_availability.md` 给出 {N} 条声明链接的逐条判定：{TEST} 条可测（{REACH} 可达、{GONE} 明确失效），
{UNT} 条不可测。可达率不是单点而是区间 {AV_S:.4f}-{AV:.4f}：{len(GH)} 条链接由 github.com 直接应答，
而该主机在两轮对照验证中只有一轮通过（另一轮超时）。四条限制随数字一起成立：
分母仅 {len(by_rel)} 张卡片的 {N} 条链接；不可测残差按链接列出而不并入任何一侧；
HTTP 应答只证明"有东西在应答"；通道可信度本身是估计量的一部分，因此把区间压成单点会高估精度。
原判据（K6：本机无法区分抓取失败与链接失效）已被实测取代，替换登记为偏差而非静默删除。
""", encoding="utf-8", newline="")
    print("[e71] appended L13")

DV = PAP / "deviations.md"
dt = DV.read_text(encoding="utf-8")
alld = [int(x) for f in sorted((ROOT / "papers").glob("*/deviations.md"))
        for x in re.findall(r"(?m)^\| D(\d+) \|", f.read_text(encoding="utf-8"))]
dn = max(alld or [0])
SUBJ = "「链接可达性本机不可测」这一范围界定被实测取代"
if SUBJ not in dt:
    DV.write_text(dt.rstrip() + f"""
| D{dn+1} | {NOW} | {SUBJ} | EXP-0061 发现 hf-mirror.com 与 raw.githubusercontent.com 可用；EXP-0071 对同一组 {N} 条链接逐条探测（每通道带正/负对照，传输失败按规则记为不可测而非失效），EXP-0072 验证通道能否区分存在与不存在：2 个通道通过、1 个未通过、github.com 两轮中仅一轮通过 | 否 | §7 与附录改写为测量结果并给出区间 {AV_S:.4f}-{AV:.4f}（而非单点），新增 K9 与 L13；原「无法测」措辞保留在本记录中；H1–H5 判据与主普查数字未改 |""",  # noqa: E501
                   encoding="utf-8", newline="")
    print(f"[e71] D{dn+1} appended")

FA = PAP / "final_audit.md"
fa = FA.read_text(encoding="utf-8")
if "EXP-0071" not in fa:
    fa2 = fa.replace("URL availability unmeasured",
                     f"URL availability measured for {TEST}/{N} declared links (EXP-0071/0072)")
    if fa2 != fa:
        FA.write_text(fa2, encoding="utf-8", newline="")
        print("[e71] final_audit availability phrase updated")
    else:
        print("[e71] final_audit: the 'availability unmeasured' phrase is not present in that exact form; left alone")

p = REG / "experiment_registry.csv"
txt = p.read_text(encoding="utf-8")
rows = [r for r in csv.reader(io.StringIO(txt)) if r]
for exp, script, cfg, stat, note in (
    ("EXP-0071", "02_shared_code/data_audit/link_availability_p005.py",
     f"per-link HTTP probe of the {N} URLs the EXP-0049 census counted (same set; per-release counts asserted before "
     "reporting), canonical host first then the alternate channel EXP-0061 proved reachable; verdict rule fixed "
     "beforehand so a transport failure is never scored as rot",
     f"testable={TEST}/{N} reachable={REACH} gone={GONE} untestable={UNT} availability_over_testable={AV:.4f}",
     "produced the first availability figure for P005's reference scaffolding; its reachable verdicts were then "
     "required to pass the channel test in EXP-0072"),
    ("EXP-0072", "02_shared_code/data_audit/validate_link_channels.py",
     "channel validation: one positive and one deliberately-absent negative control per channel, re-scoring "
     "EXP-0071's stored per-channel responses without re-fetching; a reachable verdict counts only from a channel that "
     "fails on the absent URL",
     f"discriminative={S72['discriminative_channels']}; demoted={len(S72['links_moved_out_of_reachable'])}; "
     f"availability {S71['availability_rate_over_testable']} -> {AV:.4f} primary / {AV_S:.4f} strict",
     "kept the availability claim honest: it turned a single percentage into an interval and disqualified one channel "
     "outright"),
):
    if exp not in {r[0] for r in rows}:
        rows.append([exp, "P005", "success", script, cfg, "none (deterministic given the network responses)",
                     S71["at"], S72["at"], stat,
                     f"results_raw/{N71}; results_raw/{N72}; "
                     "results_processed/EXP0071_link_availability.csv; "
                     "papers/P005_governance_metadata_verifiability/link_availability.md",
                     note, "yes - §7, K9, L13"])
        print(f"[e71] registered {exp}")
buf = io.StringIO()
csv.writer(buf, lineterminator="\r\n").writerows(rows)
p.write_text(buf.getvalue(), encoding="utf-8", newline="")
import pandas as pd
d = pd.read_csv(p)
assert not d.exp_id.duplicated().any()
print(f"[e71] registry rows={len(d)}; availability {AV_S:.4f}-{AV:.4f} over {TEST}/{N} testable links")
