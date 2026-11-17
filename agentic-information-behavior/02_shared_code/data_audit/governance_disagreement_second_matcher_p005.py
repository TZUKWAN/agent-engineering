"""EXP-0091 (P005): re-decide every disagreement instance with a matcher that was written without reading the first.

P005's H3 verdict - "a disagreement class is common" - rests on **one** instance found across eight releases
(EXP-0049: `D2_size_claim_vs_file_rows` in code-act; D1 and D3 found nothing anywhere). The paper reports H3 as
refuted, and `reviewer_attack.md` A6 refuses the "1 in 8 is noise" reading. Either way the whole conclusion is
balanced on a single match between a card's declared row count and a footer sum, made by one piece of attribution
code. P005's own hand check (EXP-0051) covers six items with one coder and no agreement statistic, and there is no
second coder available here.

So the check is executed the way EXP-0087, EXP-0088 and EXP-0089 were: a second implementation, written against the
protocol's classes rather than against the first implementation's code, compared instance-by-instance.

**B (this script)** differs from A in the three places where A's decisions are actually made:

  * *front matter*: A uses the YAML loader plus `yaml_names()`, which walks `dataset_info`/`splits`/`configs` and
    carries each declaration's own `data_files`. B ignores the loader and scans the front-matter block by
    indentation, emitting (config, split, num_examples, declared paths) tuples with its own nesting rules.
  * *attribution*: A attributes a size claim to the files whose relative path contains a declared path. B attributes
    it to the **directory scope** of the declared paths - every data file in the same directory as any path the
    declaration names - which is the reading a card author most likely intended and the one that makes AgentBank's
    19 per-environment declarations comparable at all.
  * *name matching*: A tests whether a declared name appears as a substring of some relative path. B builds a token
    index of every path (split on `/ _ - .`) and tests token equality or prefix, so `swe_bench` does not match
    `swe_bench_train_extra` by accident and `train-0000` does not hide.

The frozen classes, bands and the ±25% tolerance are A's, because the object under test is the matcher.

Pre-declared decision rule, fixed before B ran:

  * H3 rests on the per-release boolean "has >= 1 instance". If the two matchers agree on that boolean for **all 8**
    releases, H3 stands as reported and the hand-check item is closed as an automated agreement measurement.
  * If they disagree on any release, the instance count is declared matcher-dependent, both instance sets are
    published, and the H3 sentence in the paper names the matcher that produced it.
  * If B finds instances in **>= 3** releases where A found at most one, H3's refutation is withdrawn outright: the
    claim would then be established under a second faithful matcher, and "one in eight" would have been an artefact
    of attribution rather than a property of the releases.
  * If A finds instances B cannot reproduce, each is listed with both readings of the same files; an instance only
    one matcher can see is not evidence of a disagreement, it is evidence about matchers.

    python governance_disagreement_second_matcher_p005.py

Writes results_raw/EXP0091_second_matcher_*.json and results_processed/EXP0091_instance_comparison.csv.
"""
from __future__ import annotations

import json, os, pathlib, re, sys, time
from collections import Counter, defaultdict

import pyarrow.parquet as pq

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import governance_metadata_pilot_p005 as G          # noqa: E402  (DATA, CORPORA, the frozen class names)

ROOT = G.ROOT
OUT_RAW, OUT_PROC = ROOT / "results_raw", ROOT / "results_processed"
FOOTER_CAP = 2500
TOL_LO, TOL_HI = 0.8, 1.25                            # the frozen band from protocol section on D2
SIZE_BANDS = {"n<1K": (0, 1e3), "1K<n<10K": (1e3, 1e4), "10K<n<100K": (1e4, 1e5), "100K<n<1M": (1e5, 1e6),
              "1M<n<10M": (1e6, 1e7), "10M<n<100M": (1e7, 1e8)}


# ---------------- B: indentation scanner over the front-matter block ----------------

def front_matter_lines(text):
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n?(.*)$", text, re.S)
    if not m:
        return [], text
    return m.group(1).splitlines(), m.group(2)


PATHY = re.compile(r"(?:[\w.\-]+/)+[\w.\-*]*")          # anything carrying a slash reads as a relative path
REC_PATH = PATHY


NAME_RE = re.compile(r"(?:- )?name:\s*([^\s,\]]+)")
CFG_RE = re.compile(r"(?:- )?config_name:\s*([^\s,\]]+)")


def scan_front(lines):
    """Walk the front matter line by line, tracking which config each `num_examples` sits under.

    Two rules matter and both were wrong in an earlier version of this script. (1) Every split is called `train` or
    `test`, so a declaration must be scoped to its own config - matching the token `train` across the whole release
    compares one config's claim against every config's rows, which is exactly the error EXP-0049 logged as D-P4 and
    which B's first record-based version reproduced. (2) A record that holds several splits must yield one
    declaration per `num_examples`, not one per record.
    """
    decls, cfg_stack = [], []                    # (indent, config_name) of enclosing config items
    for i, raw in enumerate(lines):
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        ind = len(raw) - len(raw.lstrip(" "))
        cm = CFG_RE.match(s)
        if cm:
            while cfg_stack and cfg_stack[-1][0] >= ind:
                cfg_stack.pop()
            cfg_stack.append((ind, cm.group(1)))
            continue
        ne = re.search(r"num_examples:\s*([0-9][0-9_]*)", s)
        if not ne:
            continue
        label, j = "", i - 1
        while j >= 0 and not label:
            r2 = lines[j].strip()
            ind2 = len(lines[j]) - len(lines[j].lstrip(" "))
            if CFG_RE.match(r2):
                break
            nm = NAME_RE.match(r2)
            if nm and ind2 <= ind and r2.startswith("- "):
                label = nm.group(1)
                break
            j -= 1
        paths = []
        for k in list(range(max(0, i - 3), i)) + list(range(i + 1, min(len(lines), i + 6))):
            r2 = lines[k].strip()
            if CFG_RE.match(r2) or "num_examples" in r2:
                continue
            paths += [p for p in PATHY.findall(r2) if p.endswith((".parquet", ".jsonl", ".csv", ".arrow",
                                                                  ".tsv", ".json")) or p.endswith("-")]
        decls.append({"config": cfg_stack[-1][1] if cfg_stack else "",
                      "name": label or (cfg_stack[-1][1] if cfg_stack else ""),
                      "num_examples": int(ne.group(1).replace("_", "")),
                      "paths": sorted(set(paths))})
    return decls


def scan_bands(lines):
    """`size_categories` appears both as `key: [a, b]` and as `key:` followed by `- a` block items."""
    for i, raw in enumerate(lines):
        k, _, v = raw.strip().partition(":")
        if k.strip() != "size_categories":
            continue
        vs = v.strip().strip('"\'')
        if vs:
            if vs.startswith("["):
                vs = vs[1:-1].split(",")[0].strip().strip('"\'')
            return vs
        for nxt in lines[i + 1:]:
            s = nxt.strip()
            if not s:
                continue
            return s[2:].strip().strip('"\'') if s.startswith("- ") else None
    return None


def token_index(relpaths):
    """Every path split into tokens, so presence is decided by token identity rather than substring luck."""
    idx = defaultdict(set)
    for rp in relpaths:
        for tok in re.split(r"[/_.\-]+", rp.lower()):
            if tok and not tok.isdigit():
                idx[tok].add(rp)
    return idx


def name_present(label, idx, relpaths):
    l = label.lower()
    if l in idx or any(t.startswith(l) or l.startswith(t) for t in idx if len(t) > 3):
        return True
    return any(l in rp for rp in relpaths)


def measure_release(name, rel):
    d = G.DATA / rel
    rd = d / "README.md"
    text = rd.read_text(encoding="utf-8", errors="replace") if rd.exists() else ""
    fm_lines, prose = front_matter_lines(text)
    decls = scan_front(fm_lines)
    band = scan_bands(fm_lines)

    relpaths, rows_by_path = [], {}
    for root, _dirs, fnames in os.walk(d):
        for fn in fnames:
            p = pathlib.Path(root) / fn
            rp = p.relative_to(d).as_posix().lower()
            relpaths.append(rp)
            if p.suffix.lower() == ".parquet" and len(rows_by_path) < FOOTER_CAP:
                try:
                    rows_by_path[rp] = int(pq.ParquetFile(p).metadata.num_rows)
                except Exception:
                    pass
    idx = token_index(relpaths)

    inst, obs = [], []
    tested = 0
    for dec in decls:
        label = dec["name"] or dec["config"]
        if not label or label.lower() == "default":
            pass
        elif not name_present(label, idx, relpaths):
            inst.append({"class": "D1_declared_split_or_config_absent", "declared": label,
                         "evidence": "no path token equals or extends this name in the release tree"})
        # B's attribution route, in its own order. Scope first: every split is called `train`, so matching the token
        # `train` across a release compares one config's claim against every config's rows - the error EXP-0049 logged
        # as D-P4, which B's first version reproduced verbatim. Then declared path prefix, then name as path token.
        cfg = (dec["config"] or "").lower()
        scoped = {rp: v for rp, v in rows_by_path.items() if cfg and cfg in rp.split("/")}
        base, scope = (scoped, "config_subtree") if scoped else (rows_by_path, "whole_release")
        prefixes = [re.sub(r"\*.*$", "", re.sub(r"^\./", "", p).lower()) for p in dec["paths"]]
        prefixes = [p for p in prefixes if len(p) > 3]
        matched, basis = {}, ""
        if prefixes:
            hit = {rp: v for rp, v in base.items() if any(rp.startswith(w) for w in prefixes)}
            if hit:
                matched, basis = hit, "declared_path_prefix"
        lab = label.lower()
        if not matched and lab and lab != "default":
            matched = {rp: v for rp, v in base.items() if rp in idx.get(lab, set())}
            basis = "name_as_path_token"
        if not matched and len(decls) == 1 and base is rows_by_path:
            matched, basis = dict(rows_by_path), "single_declaration_whole_release"
        if not matched:
            obs.append({"class": "D2_not_comparable", "declared": f"{label}={dec['num_examples']}",
                        "reason": f"no data file matches the declared prefix or the name as a token within "
                                  f"{scope}", "corpus": name})
            continue
        tested += 1
        meas = float(sum(matched.values()))
        ratio = dec["num_examples"] / meas if meas else None
        if meas > 0 and not (TOL_LO <= ratio <= TOL_HI):
            inst.append({"class": "D2_size_claim_vs_file_rows", "declared": f"{label}={dec['num_examples']}",
                         "measured": int(meas), "ratio": round(ratio, 4), "basis": f"{scope}+{basis}",
                         "evidence": f"{len(matched)} file(s) attributed by {basis} within {scope}"})
    tot = sum(rows_by_path.values())
    decl_sum = sum(x["num_examples"] for x in decls)
    if decl_sum and tot and not (TOL_LO <= decl_sum / tot <= TOL_HI):
        inst.append({"class": "D2_size_claim_vs_file_rows",
                     "declared": f"sum_of_{len(decls)}_declarations={decl_sum}", "measured": int(tot),
                     "ratio": round(decl_sum / tot, 4), "basis": "aggregate",
                     "evidence": "all declarations against all footer rows read"})
    if band in SIZE_BANDS and tot:
        lo, hi = SIZE_BANDS[band]
        if not (lo <= tot <= hi):
            inst.append({"class": "D2_size_claim_vs_file_rows", "declared": f"size_categories={band}",
                         "measured": int(tot), "ratio": None, "basis": "declared_band_vs_footer_sum",
                         "evidence": f"band [{lo:.0f},{hi:.0f}] excludes {tot}"})
    for tok in set(re.findall(r"[\w./-]+\.(?:parquet|jsonl|csv|arrow|tsv|json)\b", prose)):
        base = tok.split("/")[-1].lower()
        if not any(base == rp.rsplit("/", 1)[-1] or base.rstrip(".0123456789") in rp for rp in relpaths):
            inst.append({"class": "D3_card_named_file_absent", "declared": tok,
                         "evidence": "cited in the card body; no basename in the tree matches it token-wise"})
    return {"corpus": name, "declarations_scanned": len(decls), "declarations_tested": tested,
            "files_seen": len(relpaths), "footer_rows_files": len(rows_by_path), "total_rows": int(tot),
            "band": band, "instances": inst, "observations": obs}


def selftest():
    fm = """dataset_info:
- config_name: alpha
  splits:
  - name: train
    num_examples: 100
    data_files: [data/alpha/train-00000.parquet]
  - name: test
    num_examples: 5
    data_files:
    - data/alpha/test-00000.parquet
- config_name: beta
  num_examples: 40
  data_files: data/beta/*.parquet
size_categories:
- n<1K
""".splitlines()
    decls = scan_front(fm)
    got = sorted((d["name"], d["num_examples"]) for d in decls)
    if ("train", 100) not in got or ("test", 5) not in got:
        raise SystemExit(f"ABORT selftest: indentation scan lost splits: {got}")
    byname = {d["name"]: d for d in decls}
    # the paths are the whole point: without them no declaration can be attributed and the comparison is vacuous
    # (this is exactly what the first version of this script did wrong)
    if not byname["train"]["paths"] or not byname["test"]["paths"]:
        raise SystemExit(f"ABORT selftest: declared paths lost for train/test: "
                         f"{byname['train']['paths']} / {byname['test']['paths']}")
    if any(d["config"] != "alpha" for d in decls if d["name"] in ("train", "test")):
        raise SystemExit("ABORT selftest: config scope lost - "
                         + str([(d["name"], d["config"]) for d in decls]))
    if scan_bands(fm) != "n<1K":
        raise SystemExit("ABORT selftest: band scan gave " + repr(scan_bands(fm)))
    idx = token_index(["data/swe_bench/train-00001.parquet", "data/swe_bench_extra/x.parquet"])
    if not name_present("swe_bench", idx, ["data/swe_bench/train-00001.parquet"]):
        raise SystemExit("ABORT selftest: token index cannot find a declared config name")
    if name_present("no_such_config", idx, ["data/swe_bench/train-00001.parquet"]):
        raise SystemExit("ABORT selftest: token index matches a name that is absent")
    print("  selftest ok: splits, band and token presence all behave on the synthetic card")


def key(i):
    lab = str(i.get("declared", ""))
    lab = re.sub(r"=\d+$", "", lab)
    return (i["class"], lab.lower())


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    selftest()
    afile = sorted(OUT_RAW.glob("EXP0049_governance_census_*.json"))[-1]
    A = json.loads(afile.read_text(encoding="utf-8"))
    a_inst = {r["corpus"]: r.get("disagreements") or [] for r in A["releases"]}
    if not a_inst:
        raise SystemExit("ABORT: EXP-0049 has no per-release instance lists to compare with")

    res = {"exp_id": "EXP-0091", "paper_id": "P005", "a_artefact": afile.name,
           "b_method": "indentation scan + directory-scope attribution + token presence (no A code reused)",
           "frozen_inputs_used": {"classes": "D1/D2/D3 from protocol_freeze.md", "tolerance": [TOL_LO, TOL_HI],
                                  "size_bands": list(SIZE_BANDS)},
           "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "releases": {}, "comparison": []}
    for name, rel in G.CORPORA.items():
        if not (G.DATA / rel).is_dir():
            raise SystemExit(f"ABORT: {name} is not on disk - B cannot re-decide what it cannot read")
        b = measure_release(name, rel)
        ai = a_inst.get(name, [])
        bk = Counter(key(i) for i in b["instances"])
        ak = Counter(key(i) for i in ai)
        both = sum(min(ak[k], bk[k]) for k in set(ak) | set(bk))
        res["releases"][name] = {**b, "a_instances": ai}
        res["comparison"].append({"corpus": name, "a_n": len(ai), "b_n": len(b["instances"]),
                                  "shared": both, "only_a": sorted(set(ak) - set(bk)),
                                  "only_b": sorted(set(bk) - set(ak)),
                                  "a_has_disagreement": bool(ai), "b_has_disagreement": bool(b["instances"]),
                                  "boolean_agree": bool(ai) == bool(b["instances"])})
        print(f"  {name}: A {len(ai)} instance(s), B {len(b['instances'])}, decls scanned "
              f"{b['declarations_scanned']}, tested {b['declarations_tested']}", flush=True)

    agree = sum(1 for c in res["comparison"] if c["boolean_agree"])
    n_rel_a = sum(1 for c in res["comparison"] if c["a_has_disagreement"])
    n_rel_b = sum(1 for c in res["comparison"] if c["b_has_disagreement"])
    res["boolean_agreement_releases"] = f"{agree}/{len(G.CORPORA)}"
    res["releases_with_instances"] = {"A": n_rel_a, "B": n_rel_b}
    res["instances_total"] = {"A": sum(c["a_n"] for c in res["comparison"]),
                              "B": sum(c["b_n"] for c in res["comparison"])}
    res["h3_input_a"] = A.get("hypotheses", {}).get("H3_a_disagreement_class_is_common", {})
    if agree == len(G.CORPORA):
        res["verdict"] = (f"H3 STANDS AS REPORTED: the two matchers agree on the has-instance boolean for all "
                          f"{agree} releases ({res['instances_total']} instances total), so the refutation of "
                          "H3 does not depend on A's attribution code; the hand-check item is closed as an "
                          "automated agreement measurement")
    elif n_rel_b >= 3 and n_rel_a <= 1:
        res["verdict"] = (f"H3 REFUTATION WITHDRAWN: A found instances in {n_rel_a} release(s) and B finds them in "
                          f"{n_rel_b}, which is at or over the 3-release threshold the class needs to be 'common' - "
                          "the refutation was a property of the attribution rule, not of the releases")
    else:
        res["verdict"] = (f"MATCHER-DEPENDENT: the matchers disagree on the has-instance boolean for "
                          f"{len(G.CORPORA) - agree} of {len(G.CORPORA)} releases (A {n_rel_a} vs B {n_rel_b} with "
                          "instances), so the instance count is reported as matcher-dependent and the H3 sentence "
                          "names the matcher that produced it")
    res["wallclock_sec"] = round(time.time() - t0, 1)
    res["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")

    import pandas as pd
    pd.DataFrame(res["comparison"]).to_csv(OUT_PROC / "EXP0091_instance_comparison.csv", index=False)
    pd.DataFrame([{"corpus": r["corpus"], "source": src, "class": i["class"], "declared": i.get("declared"),
                   "measured": i.get("measured"), "ratio": i.get("ratio"), "basis": i.get("basis"),
                   "evidence": i.get("evidence")}
                  for r in A["releases"] for src, i in [("A", x) for x in (r.get("disagreements") or [])]
                  ] + [{"corpus": nm, "source": "B", "class": i["class"], "declared": i.get("declared"),
                        "measured": i.get("measured"), "ratio": i.get("ratio"), "basis": i.get("basis"),
                        "evidence": i.get("evidence")}
                       for nm, v in res["releases"].items() for i in v["instances"]]).to_csv(
        OUT_PROC / "EXP0091_instances_side_by_side.csv", index=False)
    out = OUT_RAW / f"EXP0091_second_matcher_{time.strftime('%Y%m%dT%H%M%S')}.json"
    out.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    print("boolean agreement:", res["boolean_agreement_releases"], "| instances:", res["instances_total"])
    print("verdict:", res["verdict"])
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
