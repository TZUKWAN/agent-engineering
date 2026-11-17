"""EXP-0081 recorder (v2): register the acquisition finding and rewrite P001's external-validation wording from artefacts.

v1 was written from a round in which `raw.githubusercontent.com` timed out on its positive control. The next round
answered 200 with a working 404 control, and a real file then came down from the benchmark's HuggingFace release, so
v1's prose was wrong and is replaced here. Nothing in this file touches the network: every number is read from
`results_raw/EXP0081_*.json`, which the probe steps wrote.

Edits are marker-guarded, so the recorder can run again after the package builders rewrite the prose files.

    python record_exp0081_p001.py
"""
from __future__ import annotations

import csv, glob, io, json, pathlib, re, sys, time

HERE = pathlib.Path(__file__).resolve().parent          # 02_shared_code/registry
ROOT = HERE.parents[1]                                   # repository root
P = ROOT / "papers" / "P001_routing_failure_qpp"
NOW = time.strftime("%Y-%m-%dT%H:%M:%S")


def sub1(text, pat, repl, tag, marker=None):
    if marker and marker in text:
        print(f"  [{tag}] already applied - skipped")
        return text
    n = len(re.findall(pat, text, re.S))
    if n != 1:
        raise SystemExit(f"ABORT [{tag}]: matched {n} times, expected 1: {pat[:70]!r}")
    print(f"  [{tag}] applied")
    return re.sub(pat, repl, text, count=1, flags=re.S)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ver = json.loads(sorted((ROOT / "results_raw").glob("EXP0081_toolret_acquisition_verified_*.json"))[-1]
                     .read_text(encoding="utf-8"))
    ch = json.loads(sorted((ROOT / "results_raw").glob("EXP0081_external_benchmark_channel_probe_*.json"))[-1]
                     .read_text(encoding="utf-8"))
    got = ver["downloads"]["mangopy/ToolRet-Training-20w"]
    ctl = ver["downloads"]["mangopy/zz-definitely-absent-xyz"]
    assert got["found"] and not ctl["found"], "the dataset channel is not discriminative - nothing may be claimed"
    h = ch["http"]
    atom_b, pdf_b = h["arxiv_atom"]["bytes"], h["toolret_pdf"]["bytes"]
    gh_b, gh_c = h["gh_readme_master"]["bytes"], h["gh_readme_master"]["http_code"]
    gh_n = h["gh_negative_control"]["http_code"]

    # ---------------------------------------------------------------- 1. limitations L6
    lim_new = (
        "EXP-0081 逐通道实测：arXiv 记录与全文 PDF 均可达（HTTP 200，{pdf:,} B）。raw.githubusercontent 在 `master` 分支"
        "判别成功（README {gh_c} / {gh:,} B，虚构路径对照 {ghn}），而同一轮 `main` 分支为传输级失败（curl 28/35）——即该主机会"
        "抖动，与 EXP-0072 的记录一致。hf-mirror 的 dataset_info()（GET /api/datasets/<id>）对候选 id 与虚构 id 一律返回同一错误（该调用不可判别），但同一主机上的 list_repo_files 树列表调用可判别（真实仓库返回文件清单、虚构 id 抛错），而数据集文件下载路径同样可判别：`mangopy/ToolRet-Training-20w` 的 README.md 实际取回 {sz:,} B，虚构 id 返回 404。"
        "因此旧句「在本环境不可下载」不再成立：外部基准属于可获取资源，尚未完成的只是把它的每查询目录按 P001 冻结的特征模式"
        "重建这一常规工程步骤。").format(pdf=pdf_b, gh=gh_b, gh_c=gh_c, ghn=gh_n, sz=got["bytes"])
    lim = (P / "limitations.md").read_text(encoding="utf-8")
    lim = sub1(lim, r"外部基准（STAC / ToolBench / API-Bank / ToolRet）在本环境不可下载[^。]*。[^。]*。",
               lim_new, "L6", marker="EXP-0081 逐通道实测")
    (P / "limitations.md").write_text(lim, encoding="utf-8", newline="")

    # ---------------------------------------------------------------- 2. final audit gate row
    fa = (P / "final_audit.md").read_text(encoding="utf-8")
    fa = sub1(fa, r"\| cross-dataset external validation \|[^\n]*\n",
              "| cross-dataset external validation | **OPEN - no longer an environment blocker (EXP-0081)** | three "
              "configs of one corpus family only so far; the ToolRet paper, its data card and the release README were "
              "downloaded here (arXiv {a} B record + {p:,} B PDF; GitHub `master` README {g:,} B against an invented-"
              "path {n} control), and a file from the benchmark's HuggingFace release was fetched through hf-mirror "
              "({s:,} B against 404 for an invented id), so the acquisition channel works. Outstanding work is "
              "ingesting the eval corpus and mapping its per-query catalogue onto the frozen feature schema - see "
              "`external_benchmark_probe.md` and limitations L6 |\n".format(a=atom_b, p=pdf_b, g=gh_b, n=gh_n,
                                                                           s=got["bytes"]),
              "final_audit row", marker="no longer an environment blocker")
    (P / "final_audit.md").write_text(fa, encoding="utf-8", newline="")

    # ---------------------------------------------------------------- 3. register the experiment
    rp = ROOT / "00_program_registry" / "experiment_registry.csv"
    rows = [r for r in csv.reader(io.StringIO(rp.read_text(encoding="utf-8"))) if r]
    hdr, body = rows[0], rows[1:]
    arts = sorted(pathlib.Path("results_raw").glob("EXP0081_*.json"))
    if "EXP-0081" not in {r[0] for r in body}:
        rec = dict.fromkeys(hdr, "")
        rec.update({
            "exp_id": "EXP-0081", "paper_id": "P001", "topic_id": "T037",
            "stage": "external_benchmark_acquisition_probe",
            "script": "02_shared_code/literature/external_benchmark_channel_probe.py; "
                      "02_shared_code/registry/record_exp0081_p001.py",
            "config": "per-channel positive and invented-id negative control; frozen rule that a transport failure is "
                      "untestable rather than absent and that a channel counts only if it separates present from "
                      "invented; candidate ids read out of the authors' own arXiv record and release README rather "
                      "than invented as claims",
            "seed": "none (deterministic probe)", "started_at": ch["at"], "finished_at": ver["at"],
            "status": "ACQUISITION CHANNEL VERIFIED - corpus not yet ingested",
            "outputs": "; ".join(["results_raw/" + a.name for a in arts] +
                                 ["papers/P001_routing_failure_qpp/external_benchmark_probe.md",
                                  "logs/fetch/toolret.pdf", "logs/fetch/gh_readme_master"]),
            "notes": "arXiv metadata and full PDF reachable (200); GitHub raw discriminative on `master` (200 vs an "
                     "invented-path 404) while `main` failed at transport in the same round; hf-mirror's "
                     "/api/datasets metadata is non-discriminative but its dataset file-download path is - "
                     f"mangopy/ToolRet-Training-20w README.md fetched ({got['bytes']} B) against 404 for an invented "
                     "id. L6's \"not downloadable in this environment\" is withdrawn and the gate's reason becomes "
                     "unfinished work rather than an environment wall",
            "enters_paper": "yes - limitations L6, final_audit gate, deviations"})
        body.append([rec[c] for c in hdr])
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\r\n").writerows([hdr] + body)
    rp.write_text(buf.getvalue(), encoding="utf-8", newline="")
    check = [r for r in csv.reader(io.StringIO(rp.read_text(encoding="utf-8"))) if r]
    ragged = sum(1 for r in check[1:] if len(r) != len(check[0]))
    if ragged:
        raise SystemExit(f"registry has {ragged} ragged rows after writing")

    # ---------------------------------------------------------------- 4. the deviation entry
    used = set()
    for f in glob.glob(str(ROOT / "papers" / "*" / "deviations.md")):
        used |= {int(x) for x in re.findall(r"^\| D(\d+) \|", pathlib.Path(f).read_text(encoding="utf-8"), re.M)}
    did = max(used | {0}) + 1
    dv = P / "deviations.md"
    s = dv.read_text(encoding="utf-8")
    # the guard must key on CONTENT, not on the next free id: a fresh id is always "not in s", so an id-keyed guard
    # appends a duplicate row on every re-run (measured - the first version of this recorder wrote D48 after D47)
    if "EXP-0081 逐通道正/负对照" not in s:
        s = s.rstrip() + "\n" + (
            f"| D{did} | {NOW} | 撤回 L6 的环境前提：「外部基准在本环境不可下载」被实测否证 | EXP-0081 逐通道正/负对照："
            f"arXiv 记录与全文 PDF 均 HTTP 200（{pdf_b:,} B）；raw.githubusercontent 在 master 分支 README {gh_c} / {gh_b:,} B、"
            "虚构路径 404（可判别），同轮 main 分支为传输级失败；hf-mirror 的 /api/datasets 元数据端点对候选与虚构 id 一律同错"
            f"（不可判别），但数据集文件下载路径可判别——真实取回 mangopy/ToolRet-Training-20w 的 README.md {got['bytes']:,} B，"
            "虚构 id 返回 404 | 否（未读取任何外部语料的行，论文中的任何数字都未因此改变） | 门槛状态仍为 OPEN，但理由从「环境阻断」"
            "改为「未完成的工程」；本行不构成任何外部验证结论，也不改变 E08 以 hermes 为替代语料的既有证据 |\n")
        dv.write_text(s, encoding="utf-8", newline="")
        print(f"  deviations: appended D{did}")
    print(f"  registry rows={len(check) - 1}; artefacts={', '.join(a.name for a in arts)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
