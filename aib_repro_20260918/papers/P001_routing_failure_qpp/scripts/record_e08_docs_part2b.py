"""E08 docs 2b: fill A12 and the card section from templates, and extend reproduce.sh."""

from __future__ import annotations

import glob
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PAP = ROOT / "papers" / "P001_routing_failure_qpp"
SC = PAP / "scripts"


def last(pat):
    return json.loads(Path(sorted(glob.glob(str(ROOT / "results_raw" / pat)))[-1]).read_text(encoding="utf-8"))


E20, E21, E23, E23a = (last("EXP0020_toucan_routing_dataset_*.json"), last("EXP0021_cross_pipeline_transfer_*.json"),
                       last("EXP0023_hermes_transfer_*.json"), last("EXP0023a_hermes_toolcall_feasibility_*.json"))
s, a1, a1b, a2, ov = (E20["configs"]["SFT"], E21["arm1_external_pipeline"], E21["arm1b_catalogue_disjoint"],
                      E21["arm2_unseen_tool_family"], E21["overlap_audit"])
her, hc, hi = E23["transfer"], E23["corpus_after_inclusion_rule"], E23["independence_audit"]
TOK = {
    "sft_kept": s["rows_kept"], "sft_seen": s["rows_seen"], "sft_rej": s["rejection_accounting"],
    "sft_cat_mean": s["catalog_size"]["mean"], "sft_prev": s["dev"]["fail_at_3_prevalence"],
    "ov_names": f"{ov['distinct_tool_names']['exact_overlap']}/{ov['distinct_tool_names']['target']}",
    "ov_tokens": f"{ov['target_catalog_token_coverage_by_source']:.0%}",
    "ov_fp": ov["distinct_catalogue_fingerprints"]["shared_fingerprints"],
    "a1_auc": a1["auc_transfer_source_dev_to_target"], "a1_ci": a1["auc_transfer_ci95_catalogue_bootstrap"],
    "src_oof": round(sum(a1["auc_source_reference_oof_dev"]) / len(a1["auc_source_reference_oof_dev"]), 4),
    "a1b_rows": a1b["n_rows"], "a1b_auc": a1b["auc_transfer_disjoint_catalogues"],
    "a2_n": a2["n_families_tested"], "a2_cons": a2["n_families_considered"],
    "a2_minpos": a2["min_positives_required"], "a2_seen": a2["mean_auc_family_seen_reference"],
    "a2_unseen": a2["mean_auc_unseen_family"], "a2_drop": a2["mean_drop_vs_seen"],
    "a2_len": a2["mean_auc_length_only"],
    "hc_rows": hc["n_rows"], "hc_prev": hc["fail_at_3_prevalence"], "hc_cats": hc["distinct_catalogues"],
    "hc_rej": E23["corpus_extraction"]["rejection_accounting"],
    "hi_unseen": f"{hi['unseen_tool_name_share']:.0%}", "hi_names": hi["external_tool_names"],
    "hi_tokens": f"{hi['external_catalog_tokens_covered_by_source']:.0%}",
    "her_auc": her["auc_source_dev_to_hermes"], "her_ci": her["ci95_row_bootstrap"],
    "her_oof": round(sum(her["auc_within_hermes_oof"]) / len(her["auc_within_hermes_oof"]), 4),
    "her_len": her["auc_hermes_length_only_B0"], "her_post": her["auc_hermes_post_retrieval_margin"],
    "her_cov": her["auc_hermes_idf_coverage_only"], "her_verdict": her["verdict"],
    "e23a_rows": E23a["rows_read"], "e23a_fps": E23a["distinct_catalogue_fingerprints"],
}


def fill(name):
    t = (SC / name).read_text(encoding="utf-8")
    for k, v in TOK.items():
        t = t.replace(f"<<{k}>>", str(v))
    left = [x for x in re.findall(r"<<[a-z0-9_]+>>", t)]
    assert not left, f"unfilled tokens in {name}: {left}"
    return t


ap = PAP / "appendix.md"
t = ap.read_text(encoding="utf-8")
if "## A12" not in t:
    ap.write_text(t.replace("## A11 Experiment inventory", fill("a12_template.md") + "\n## A11 Experiment inventory"),
                  encoding="utf-8")
    print("appendix: A12 inserted")

cd = PAP / "dataset_card.md"
t = cd.read_text(encoding="utf-8")
if "E08 round (EXP-0020..EXP-0023)" not in t:
    cd.write_text(t + fill("card_template.md"), encoding="utf-8")
    print("dataset card: E08 section appended")

rp = PAP / "reproduce.sh"
t = rp.read_text(encoding="utf-8")
if "EXP-0023" not in t:
    for old, new in (("[repro] 6/9 ", "[repro] 6/10 "), ("[repro] 7/9 ", "[repro] 7/10 "),
                     ("[repro] 9/9 verifying", "[repro] 10/10 verifying")):
        assert old in t, old
        t = t.replace(old, new, 1)
    stage = ('echo "[repro] 8/10 E08: external-catalogue availability probe and cross-corpus transfer"\n'
             '"$PY" 02_shared_code/data_audit/probe_external_catalogue_availability.py\n'
             '"$PY" 02_shared_code/data_audit/probe_hermes_toolcalls.py\n'
             '"$PY" 02_shared_code/trajectory_parser/build_toucan_routing_dataset.py --configs SFT \\\n'
             '     --exp-id EXP-0020 --rows-per-config "$ROWS" --shards-per-config "$SHARDS"\n'
             '"$PY" 02_shared_code/statistics/cross_pipeline_transfer_e08.py\n'
             '"$PY" 02_shared_code/statistics/external_corpus_transfer_hermes.py\n\n'
             'echo "[repro] 9/10 figures, tables and the paper-level package"\n')
    t = t.replace('echo "[repro] 8/9 figures, tables and the paper-level package"\n', stage, 1)
    t = t.replace("results_raw/SUPERSEDED_ARTIFACTS.json",
                  "results_raw/EXP0021_cross_pipeline_transfer_*.json \\\n         "
                  "results_raw/EXP0023_hermes_transfer_*.json \\\n         "
                  "papers/P001_routing_failure_qpp/tables/table12_external_transfer.csv \\\n         "
                  "results_raw/SUPERSEDED_ARTIFACTS.json", 1)
    rp.write_text(t, encoding="utf-8")
    print("reproduce.sh: stage 8/10 added")
print("2b done")
