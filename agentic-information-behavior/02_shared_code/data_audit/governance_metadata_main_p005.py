"""EXP-0049 (P005 main scan): the seven-level rights/provenance census over the eight agent-trajectory releases.

Implements `papers/P005_governance_metadata_verifiability/protocol_freeze.md` exactly. The instrument constants and
the licence classifier are imported from the pilot module rather than re-typed, so RQ1's prose column stays
comparable to EXP-0048 by construction.

Two-sided by design: H1-H5 each have an establishing and a refuting pattern (§7 of the freeze), 0/8 results are
reported with the rule-of-three bound, and every disagreement instance is written to its own row before it can be
counted.

    python 02_shared_code/data_audit/governance_metadata_main_p005.py
"""
from __future__ import annotations

import json, pathlib, re, sys, time
from collections import Counter, defaultdict

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from scipy.stats import fisher_exact

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "02_shared_code" / "data_audit"))
import governance_metadata_pilot_p005 as G          # noqa: E402  (CORPORA, GOV_ARTEFACTS, LIC_WORDS, PROV_KEYS, …)

DATA = G.DATA
OUT = ROOT / "results_raw"
PROC = ROOT / "results_processed"
FOOTER_FILE_CAP = 2500     # guard, not a sampling device: the largest release holds 1,230 parquet files (D-P2)
DIR_CAP = 400
JSONL_LINE_CAP = 200_000
SIZE_BANDS = {"n<1K": (0, 1e3), "1K<n<10K": (1e3, 1e4), "10K<n<100K": (1e4, 1e5), "100K<n<1M": (1e5, 1e6),
              "1M<n<10M": (1e6, 1e7), "10M<n<100M": (1e7, 1e8)}
UNVERIFIABLE_HOSTS = re.compile(r"huggingface|github", re.I)


def wilson(k, n, z=1.96):
    if n == 0:
        return [None, None]
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(max(0.0, c - h), 4), round(min(1.0, c + h), 4)]


def zero_bound(n):
    return round(3 / n, 4)          # rule of three: 0/n bounds the rate below ~3/n at 95%


def sentences(text):
    return re.split(r"(?<=[.!?])\s+|\n+", text)


def read_front(rel):
    d = DATA / rel
    rd = d / "README.md"
    if not rd.exists():
        return None, "", d, True
    text = rd.read_text(encoding="utf-8", errors="replace")
    fm, prose = G.front_matter(text)
    return fm, prose, d, False


def list_tree(d):
    dirs, files = [], []
    for p in sorted(d.rglob("*")):
        if p.is_dir():
            dirs.append(p)
        else:
            files.append(p)
        if len(files) > 20000:
            break
    return dirs, files


def as_list(v):
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def yaml_names(fm, key):
    """split / config names declared in the hub metadata, whichever shape the card used.

    Each returned item carries the declaration's own `data_files`/`data_dir` so a size claim can be compared against
    the rows of the files it actually refers to. Comparing a per-config `num_examples` against the whole release's
    row count is an apples-to-oranges test, and the first version of this scan did exactly that: it turned 19
    legitimate per-environment declarations in AgentBank into apparent disagreements (deviation D-P4).
    """
    out = []
    if not isinstance(fm, dict):
        return out

    def paths_of(b):
        p = b.get("data_files") or b.get("data_path") or b.get("path") or ""
        if isinstance(p, list):
            return [str(x) for x in p if isinstance(x, (str,))]
        if isinstance(p, dict):
            return [str(v) for v in p.values()]
        return [str(p)] if p else []

    di = fm.get("dataset_info")
    blocks = [b for b in as_list(di) if isinstance(b, dict)]
    for b in blocks + [fm]:
        cfg = str(b.get("config_name") or b.get("name") or "")
        cfg_paths = paths_of(b)
        for s in as_list(b.get("splits")) + as_list(b.get(key)):
            if isinstance(s, dict):
                nm = s.get("name") or s.get("config_name") or ""
                out.append((str(nm) if nm else cfg, s.get("num_examples"), cfg, cfg_paths + paths_of(s)))
            elif isinstance(s, str):
                out.append((s, None, cfg, cfg_paths))
    return out


def scan_release(name, rel):
    fm, prose, d, card_missing = read_front(rel)
    dirs, files = list_tree(d)
    r = {"corpus": name, "path": rel, "card_missing": card_missing}
    fset = {p.name for p in files}
    relpaths = {p.relative_to(d).as_posix() for p in files}      # as_posix, because on Windows str(PurePath) uses
    low_paths = {s.lower() for s in relpaths}                     # backslashes and would defeat every directory match

    # L1 root artefacts, L5 anywhere in the tree (D-P1: .gitattributes is not a governance artefact)
    root_files = {p.name for p in d.iterdir() if p.is_file()}
    r["L1_root_artefacts"] = sorted(G.GOV_ARTEFACTS & root_files)
    hit5 = sorted({p.name for p in files if p.name in G.GOV_ARTEFACTS})
    r["L5_artefacts_anywhere"] = hit5
    r["n_dirs"] = len(dirs)
    r["n_files"] = len(files)
    if len(dirs) > DIR_CAP:
        raise SystemExit(f"[e49] {name}: {len(dirs)} directories exceeds the frozen DIR_CAP guard")

    # L2 / L3 front matter
    keys = sorted(str(k) for k in fm) if isinstance(fm, dict) else []
    r["L2_licence_field"] = (fm or {}).get("license") if isinstance(fm, dict) else None
    r["L3_other_governance_keys"] = [k for k in keys if G.PROV_KEYS.search(k)]
    r["front_matter_keys"] = keys

    # L4 prose (same matcher as the pilot)
    sents = [s for s in sentences(prose) if G.LIC_WORDS.search(s)]
    r["L4_licence_sentences_n"] = len(sents)
    r["L4_examples"] = [re.sub(r"\s+", " ", s).strip()[:220] for s in sents[:4]]

    # L6 / L7 record and container level: census of every parquet footer
    cols, footer_keys, rows_by_split, n_pq, n_pq_err, n_lfs = set(), set(), defaultdict(int), 0, 0, 0
    for p in files:
        if p.suffix.lower() != ".parquet":
            continue
        if n_pq >= FOOTER_FILE_CAP:
            r["footer_cap_bound"] = True
            break
        try:
            f = pq.ParquetFile(p)
        except Exception as e:
            # A git-LFS pointer is a real finding about the snapshot, not a read failure to hide.
            try:
                head = p.open("rb").read(64)
            except Exception:
                head = b""
            if b"git-lfs" in head:
                n_lfs += 1
            else:
                n_pq_err += 1
                r.setdefault("footer_errors", []).append(f"{p.name}: {type(e).__name__}")
            continue
        cols |= set(f.schema_arrow.names)
        kv = (f.metadata.metadata or {}) if f.metadata else {}
        footer_keys |= {k.decode() for k in kv}
        n_pq += 1
        rp = p.relative_to(d).as_posix().lower()
        rows_by_split[rp] = int(f.metadata.num_rows)
    jfiles = [p for p in files if p.name.endswith(".jsonl")]
    for p in jfiles:
        try:
            with open(p, encoding="utf-8", errors="replace") as fh:
                line = fh.readline()[:G.MAX_JSONL_LINE]
            if line.strip().startswith("{"):
                cols |= set(json.loads(line).keys())
        except Exception:
            pass
    r["L6_parquet_footers_read"] = n_pq
    r["L6_lfs_pointer_files"] = n_lfs
    r["L6_parquet_files_present"] = sum(1 for p in files if p.suffix.lower() == ".parquet")
    r["L6_footer_read_errors"] = n_pq_err
    r["L6_jsonl_files"] = len(jfiles)
    r["L6_governance_columns"] = sorted(c for c in cols if G.PROV_KEYS.search(c))
    r["L7_governance_metadata_keys"] = sorted(k for k in footer_keys if G.PROV_KEYS.search(k))
    if n_pq and n_pq_err / max(1, n_pq + n_pq_err) > 0.10:
        raise SystemExit(f"[e49] {name}: {n_pq_err}/{n_pq + n_pq_err} footers unreadable - the level would be vacuous")

    # RQ2 components (strict = top-level dirs + declared config/split names; permissive adds prose/URL names)
    top = [p.name for p in sorted(d.iterdir()) if p.is_dir() and not p.name.startswith(".")]
    declared = [t[0] for t in yaml_names(fm, "configs") if t[0]]
    strict = sorted(set(top) | {x for x in declared if x})
    permissive = set(strict)
    for s in sentences(prose):
        if re.search(r"\b(built on|from|derived from|includes|annotated with|using|collect(ed|ion) via)\b", s, re.I):
            permissive |= {m for m in re.findall(r"\b[A-Za-z][A-Za-z0-9_+-]{3,}\b", s) if m.lower() not in
                           {"http", "https", "www", "the", "and", "with", "using", "data", "dataset"}}
    comp_rights = {}
    for c in strict:
        cd = d / c
        own = bool(cd.is_dir() and (G.GOV_ARTEFACTS & {p.name for p in cd.iterdir() if p.is_file()}))
        named = any(G.LIC_WORDS.search(s) and re.search(rf"\b{re.escape(c)}\b", s, re.I) for s in sentences(prose))
        comp_rights[c] = {"dir_exists": cd.is_dir(), "own_artefact": own, "licence_named_with_it": named}
    r["components_strict"] = strict
    r["components_permissive_n"] = len(permissive)
    r["components_with_rights"] = sorted(k for k, v in comp_rights.items() if v["own_artefact"] or v["licence_named_with_it"])
    r["component_detail"] = comp_rights

    # RQ4 disagreements, classes fixed in the freeze
    inst, observations, size_tests = [], [], []
    rows_by_rel, declared_pairs = dict(rows_by_split), set()
    for nm, ne, cfg, paths in yaml_names(fm, "configs"):
        label = nm or cfg
        if (label and label.lower() != "default" and not any(label.lower() in s for s in low_paths)
                and label.lower() not in fset):
            inst.append({"class": "D1_declared_split_or_config_absent", "declared": label,
                         "evidence": "no path segment in the release tree contains this name; the generic hub "
                                     "config label 'default' is exempt (D-P4)"})
        if ne is None:
            continue
        # scope the measurement to the files this declaration actually refers to
        want = [re.sub(r"^\./", "", p).lower() for p in paths if p]
        matched = {rp: v for rp, v in rows_by_rel.items() if any(w.rstrip("/*") in rp for w in want)} if want else {}
        basis = "declared_data_files"
        if not matched and cfg and cfg.lower() != "default" and (d / cfg).is_dir():
            matched = {rp: v for rp, v in rows_by_rel.items() if rp.startswith(cfg.lower() + "/")}
            basis = "config_directory"
        if not matched and not cfg and len({nm for nm, e, c, p in yaml_names(fm, "configs") if e is not None}) <= 1:
            matched, basis = dict(rows_by_rel), "single_declaration_whole_release"
        if not matched:
            observations.append({"class": "D2_not_comparable", "declared": f"{label}={ne}",
                                 "reason": "the declaration cannot be attributed to specific files; an unattributable "
                                           "pair is not a disagreement", "corpus": name})
            continue
        declared_pairs.add((cfg, label, int(ne)))
        meas = float(sum(matched.values()))
        size_tests.append({"scope": label or cfg, "declared": int(ne), "measured": int(meas),
                           "ratio": round(float(ne) / meas, 4) if meas else None, "basis": basis})
        try:
            dec = float(ne)
        except (TypeError, ValueError):
            continue
        if meas > 0 and not (0.8 <= dec / meas <= 1.25):
            inst.append({"class": "D2_size_claim_vs_file_rows", "declared": f"{label}={ne}", "measured": int(meas),
                         "ratio": round(dec / meas, 4), "basis": basis,
                         "evidence": f"{len(matched)} file(s) attributed to this declaration; exact footer rows"})
    tot_rows = sum(rows_by_rel.values())
    tot_decl = sum(ne for _, _, ne in declared_pairs)
    if not declared_pairs and tot_rows:
        # The hand-check pass (EXP-0051) caught a false negative here: when a card gives no config/data_files
        # attribution at all, every declaration used to be dropped, so code-act's declared 7,139 rows against 78,385
        # actual rows escaped the test. Comparing the aggregate of all declarations against the aggregate of all
        # footers is scope-matched in exactly this situation, because the release's files correspond to those
        # declarations collectively. It can only ever add testable comparisons, never remove one.
        all_decl = [(nm, ne) for nm, ne, cfg, paths in yaml_names(fm, "configs") if ne is not None]
        tot_decl = sum(int(ne) for _, ne in all_decl)
        for o in observations:
            o["resolved_by"] = "aggregate_comparison_added_below"
        if tot_decl and not (0.8 <= tot_decl / tot_rows <= 1.25):
            inst.append({"class": "D2_size_claim_vs_file_rows",
                         "declared": f"sum_of_{len(all_decl)}_declarations={tot_decl}", "measured": int(tot_rows),
                         "ratio": round(tot_decl / tot_rows, 4), "basis": "aggregate_when_unattributable",
                         "evidence": "no per-declaration attribution exists in the card, so the aggregate of all "
                                     "declarations is compared with the aggregate of all footer row counts"})
    if declared_pairs and tot_decl and tot_rows and not (0.8 <= tot_decl / tot_rows <= 1.25):
        inst.append({"class": "D2_size_claim_vs_file_rows", "declared": f"release_total_declared={tot_decl}",
                     "measured": int(tot_rows), "ratio": round(tot_decl / tot_rows, 4),
                     "basis": "aggregate_of_all_declarations_vs_all_footers",
                     "evidence": "sum of every declared num_examples against the release's exact footer rows"})
    if not any(i["class"].startswith("D2") for i in inst):
        band = (fm or {}).get("size_categories") if isinstance(fm, dict) else None
        if isinstance(band, list):                     # some cards give a list of bands
            band = str(band[0]) if band else None
        tot = sum(rows_by_split.values())
        if band in SIZE_BANDS and tot > 0:
            lo, hi = SIZE_BANDS[band]
            if not (lo <= tot <= hi):
                inst.append({"class": "D2_size_claim_vs_file_rows", "declared": f"size_categories={band}",
                             "measured": tot, "ratio": None, "basis": "declared_band_vs_footer_sum",
                             "evidence": f"band [{lo:.0f},{hi:.0f}] excludes {tot}"})
    for tok in set(re.findall(r"[\w./-]+\.(?:parquet|jsonl|csv|arrow|tsv|json)\b", prose)):
        base = tok.split("/")[-1]
        if base not in fset and not any(base.lower() in s for s in low_paths):
            inst.append({"class": "D3_card_named_file_absent", "declared": tok,
                         "evidence": "file name cited in the card body is not present in the release tree"})
    r["disagreements"] = inst
    r["observations"] = observations
    r["all_column_names"] = sorted(cols)
    r["total_exact_footer_rows"] = int(sum(rows_by_rel.values()))
    r["declarations_with_num_examples"] = len(declared_pairs) + len(observations)
    r["declarations_attributable"] = len(declared_pairs)
    if "tot_decl" in dir() and tot_decl and tot_rows:      # the aggregate comparison, when it was run
        size_tests.append({"scope": "AGGREGATE_ALL_DECLARATIONS", "declared": int(tot_decl),
                           "measured": int(tot_rows), "ratio": round(tot_decl / tot_rows, 4),
                           "basis": basis if not declared_pairs else "aggregate_of_all_declarations"})
    r["size_tests"] = size_tests

    # RQ5 reference structure (no availability measurement)
    urls = G.URL.findall(prose)
    hosts = Counter(re.sub(r"^www\.", "", u.split("/")[2].lower()) for u in urls if "//" in u)
    r["card_url_n"] = len(urls)
    r["card_hosts"] = hosts.most_common(8)
    r["card_unverifiable_host_share"] = round(sum(n for h, n in hosts.items() if UNVERIFIABLE_HOSTS.search(h))
                                              / max(1, sum(hosts.values())), 4)
    r["licence_class"], r["licence_field_value"] = G.licence_class(fm, prose, r["L1_root_artefacts"])
    return r


def holm(ps):
    items = sorted(((p, k) for k, p in ps.items() if p is not None), key=lambda x: x[0])
    m, out, prev = len(items), {}, 0.0
    for i, (p, k) in enumerate(items):
        adj = min(1.0, max(prev, (m - i) * p))
        prev = adj
        out[k] = round(adj, 6)
    for k in ps:
        out.setdefault(k, None)
    return out


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    res = {"exp_id": "EXP-0049", "paper_id": "P005", "protocol": "papers/P005_governance_metadata_verifiability/"
                                                                 "protocol_freeze.md",
           "levels": "L1 root artefact, L2 licence field, L3 other governance keys, L4 prose, L5 artefact anywhere, "
                     "L6 record columns, L7 container metadata",
           "census": f"every parquet footer in every release (cap guard {FOOTER_FILE_CAP}); "
                     f"jsonl first-record keys; no whole-shard load",
           "availability_unmeasured": "huggingface.co and github.com are unreachable from this host, so a fetch "
                                      "failure could not be distinguished from real link rot (PROGRAM_STATUS §3)",
           "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "releases": []}
    for name, rel in G.CORPORA.items():
        r = scan_release(name, rel)
        res["releases"].append(r)
        print(f"  {name:13s} L1={len(r['L1_root_artefacts'])} L2={str(r['L2_licence_field'])[:26]:26s} "
              f"L4={r['L4_licence_sentences_n']:2d} L5={len(r['L5_artefacts_anywhere'])} "
              f"L6cols={len(r['L6_governance_columns']):2d} footers={r['L6_parquet_footers_read']:4d} "
              f"comps={len(r['components_strict']):2d} dis={len(r['disagreements']):2d}", flush=True)

    R = res["releases"]
    n = len(R)
    flags = {
        "L1": [bool(r["L1_root_artefacts"]) for r in R],
        "L2": [bool(r["L2_licence_field"]) for r in R],
        "L3": [bool(r["L3_other_governance_keys"]) for r in R],
        "L4": [r["L4_licence_sentences_n"] > 0 for r in R],
        "L5": [bool(r["L5_artefacts_anywhere"]) for r in R],
        "L6": [bool(r["L6_governance_columns"]) for r in R],
        "L7": [bool(r["L7_governance_metadata_keys"]) for r in R],
        "L2_L6_L7_any_payload": [bool(r["L6_governance_columns"]) or bool(r["L7_governance_metadata_keys"])
                                 or bool(r["L5_artefacts_anywhere"]) for r in R]}
    cnt = {lv: sum(v) for lv, v in flags.items()}
    res["level_census"] = {lv: {"k": k, "n": n, "wilson95": wilson(k, n),
                                "note": (f"0/{n} bounds the rate below {zero_bound(n) * 100:.0f}% (rule of three)"
                                         if k == 0 else "")} for lv, k in cnt.items()}
    print(json.dumps({lv: v["k"] for lv, v in res["level_census"].items()}, ensure_ascii=False))

    multi = [r for r in R if len(r["components_strict"]) >= 5]
    res["rq2"] = {"multi_component_releases": [r["corpus"] for r in multi],
                  "components_named": {r["corpus"]: [len(r["components_strict"]), r["components_permissive_n"]]
                                       for r in multi},
                  "with_per_component_rights": {r["corpus"]: r["components_with_rights"] for r in multi}}

    byc = defaultdict(list)
    for r in R:
        for i in r["disagreements"]:
            byc[i["class"]].append({**i, "corpus": r["corpus"]})
    res["rq4"] = {c: {"instances": len(v), "releases": sorted({x["corpus"] for x in v})} for c, v in byc.items()}

    unver = np.mean([r["card_unverifiable_host_share"] for r in R])
    res["rq5"] = {"total_urls": sum(r["card_url_n"] for r in R),
                  "mean_unverifiable_host_share": round(float(unver), 4),
                  "per_release": {r["corpus"]: [r["card_url_n"], r["card_unverifiable_host_share"]] for r in R}}

    L2ok = cnt["L2"] >= 6
    L6uncapped = [r for r in R if not r.get("footer_cap_bound")]
    H = {
        "H1_release_level_only": {"established": bool(L2ok and cnt["L1"] <= 2 and cnt["L6"] <= 2),
                                  "refuted": cnt["L6"] >= 4,
                                  "inputs": {"L2": cnt["L2"], "L1": cnt["L1"], "L6": cnt["L6"],
                                             "uncapped_releases": len(L6uncapped)}},
        "H2_component_rights_gap": {"established": sum(1 for r in multi if not r["components_with_rights"]) >= 2,
                                    "refuted": len(multi) and sum(1 for r in multi if r["components_with_rights"])
                                    >= len(multi) / 2,
                                    "inputs": {"multi_component": [r["corpus"] for r in multi]}},
        "H3_a_disagreement_class_is_common": {"established": any(len(v["releases"]) >= 3 for v in res["rq4"].values()),
                                              "refuted": all(len(v["releases"]) <= 1 for v in res["rq4"].values()),
                                              "inputs": {c: len(v["releases"]) for c, v in res["rq4"].items()}},
        "H4_licence_verifiable_in_payload": {"established": cnt["L2_L6_L7_any_payload"] >= 1 and (
            cnt["L6"] + cnt["L7"] + cnt["L5"] >= 1),
            "refuted": cnt["L6"] == 0 and cnt["L7"] == 0 and cnt["L5"] == 0,
            "inputs": {"L5": cnt["L5"], "L6": cnt["L6"], "L7": cnt["L7"]}},
        "H5_scaffolding_points_at_unverifiable_hosts": {"established": bool(unver > 0.5), "refuted": bool(unver <= 0.5),
                                                        "inputs": {"mean_share": round(float(unver), 4)}}}
    res["hypotheses"] = H

    tests = {}
    a = [r["corpus"] for r in R if r["L1_root_artefacts"]]
    b = [r["corpus"] for r in R if r["L2_licence_field"]]
    tab = [[len(a), n - len(a)], [len(b), n - len(b)]]
    if len({len(a), len(b)}) == 1:
        tests["L1_vs_L2"] = {"p": 1.0, "table": tab, "note": "identical counts; the exact test is degenerate"}
    else:
        tests["L1_vs_L2"] = {"p": float(fisher_exact(tab)[1]), "table": tab}
    derived = [r for r in R if len(r["components_strict"]) >= 5]
    single = [r for r in R if len(r["components_strict"]) < 5]
    tab2 = [[sum(1 for r in derived if r["L2_licence_field"]), max(0, len(derived) - sum(1 for r in derived if r["L2_licence_field"]))],
            [sum(1 for r in single if r["L2_licence_field"]), max(0, len(single) - sum(1 for r in single if r["L2_licence_field"]))]]
    tests["declared_licence_multi_vs_single_component"] = {
        "p": (None if min(len(derived), len(single)) == 0 else float(fisher_exact(tab2)[1])), "table": tab2,
        "note": "reported despite small n; a comparison with an empty cell returns no p"}
    res["exact_tests"] = {"raw": tests, "holm_adjusted": holm({k: v["p"] for k, v in tests.items()})}

    res["wallclock_sec"] = round(time.time() - t0, 1)
    res["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    out = OUT / f"EXP0049_governance_census_{time.strftime('%Y%m%dT%H%M%S')}.json"
    out.write_text(json.dumps(res, indent=1, ensure_ascii=False, default=str), encoding="utf-8", newline="")

    with open(PROC / "EXP0049_disagreement_instances.csv", "w", newline="", encoding="utf-8") as fh:
        cols = ["corpus", "class", "declared", "measured", "ratio", "basis", "evidence"]
        fh.write(",".join(cols) + "\n")
        for c, v in sorted(byc.items()):
            for i in v:
                fh.write(",".join(str(i.get(k, "")).replace(",", ";") for k in cols) + "\n")
    pd.DataFrame([{"corpus": r["corpus"], **{lv: int(bool(r["L1_root_artefacts"] if lv == "L1" else
                                                        r["L2_licence_field"] if lv == "L2" else
                                                        r["L3_other_governance_keys"] if lv == "L3" else
                                                        r["L4_licence_sentences_n"] if lv == "L4" else
                                                        r["L5_artefacts_anywhere"] if lv == "L5" else
                                                        r["L6_governance_columns"] if lv == "L6" else
                                                        r["L7_governance_metadata_keys"])) for lv in
                  ("L1", "L2", "L3", "L4", "L5", "L6", "L7")},
                  "footers_read": r["L6_parquet_footers_read"], "files": r["n_files"],
                  "components_strict": len(r["components_strict"]),
                  "components_with_rights": len(r["components_with_rights"]),
                  "disagreements": len(r["disagreements"]),
                  "unverifiable_host_share": r["card_unverifiable_host_share"]} for r in R]
                 ).to_csv(PROC / "EXP0049_level_census.csv", index=False)
    print(json.dumps({k: (v["established"], v["refuted"]) for k, v in H.items()}, ensure_ascii=False))
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
