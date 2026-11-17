"""EXP-0021 (E08): does the frozen pre-retrieval model survive on an UNSEEN pipeline and UNSEEN tool families?

D13/D14 narrowed P001's headline AUROC to "an upper bound for catalogues never seen in training",
because 63.7-88.1% of test rows share a catalogue fingerprint with the training rows and the split
cannot be repaired (largest connected component = 86-98% of rows). Two ways out of that:

  Arm 1 - external pipeline. Toucan-1.5M ships a fourth generation config, `SFT`, which the frozen
  protocol never referenced, never sampled and never evaluated. EXP-0020 built it with the identical
  code path: a different rollout pipeline (SFT model, no `metadata` column, bare function-name gold
  labels, largely non-English instructions). It was hoped to be an unseen catalogue; the overlap audit
  in this run MEASURED that it is not - 1797/1797 of its tool names and 100% of its catalogue tokens
  also occur in the source dev pool, and 848/1447 of its catalogue fingerprints are byte-identical to
  a source-dev catalogue. Arm 1 therefore measures transfer across pipelines over a SHARED tool
  universe, Arm 1b re-scores only the rows whose whole catalogue is absent from the source, and the
  genuinely unseen-tool question is pushed to Arm 2.

  Arm 2 - leave-one-tool-family-out. Within the source data, hold out an entire tool family: the model
  is fitted only on rows whose catalogue contains NO tool of family f, then scored on rows whose gold
  tool belongs to f. No tool name, description or parameter in the test rows was ever seen in training,
  which is the memorisation channel the catalogue-grouped CV (EXP-0017) could only implicate.

Decision rules below were written into this file BEFORE any target label was read, and are re-stated in
the output so the run cannot be reinterpreted afterwards:
  * transfer verdict: AUROC >= 0.65 "transfers"; 0.55 <= AUROC < 0.65 "partial"; < 0.55 "does not transfer";
    in every case the transfer AUROC is additionally compared against the B0 length-only baseline,
    because beating chance while losing to instruction length is not evidence for the QPP construct;
  * family-holdout verdict: mean LOFO AUROC within 0.02 of the ordinary random-fold AUROC on the same
    rows -> tool-family familiarity is not load-bearing; a larger drop is reported as such.

Nothing here touches P001's published test split; the target rows were not used for any earlier design
choice, and every number in the output is computed from files on disk.

    python cross_pipeline_transfer_e08.py

Outputs results_raw/EXP0021_cross_pipeline_transfer_*.json,
        results_processed/EXP0021_transfer_{summary,families}.csv,
        logs/EXP-0021_cross_pipeline_transfer.txt
"""

from __future__ import annotations

import json
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "trajectory_parser"))
from analyze_routing_failure import CONFIGS, PROC, SEEDS, oof_auc, scaled_pipeline  # noqa: E402
from build_toucan_routing_dataset import toks  # noqa: E402
from hierarchical_dependence import fingerprint  # noqa: E402
from run_p001_experiments import FROZEN_C, FROZEN_FEATURES, matrices  # noqa: E402

K = 3
DV = "fail_at_3"
TARGET_CFG = "SFT"
OUT_RAW = HERE.parents[1] / "results_raw"
OUT_PROC = HERE.parents[1] / "results_processed"
N_FAMILIES = 12          # top-N tool families by gold count, fixed before looking at any AUROC
MIN_FAMILY_ROWS = 60     # smaller families cannot give a stable AUROC on their own
MIN_POSITIVES = 10       # fewer than this many routing failures makes an AUROC meaningless
CLUSTER_BOOT = 2000
BOOT_SEED = 42


def stem(name: str) -> str:
    """Tool family = the tool name minus its final component (same rule as EXP-0017's gold_stem)."""
    parts = [p for p in str(name).lower().replace("_", "-").split("-") if not p.isdigit()]
    return "-".join(parts[:-1]) if len(parts) > 1 else (parts[0] if parts else "")


def row_stems(catalog_json: str) -> list[str]:
    return sorted({stem(d["n"]) for d in json.loads(catalog_json)})


def gold_family(row) -> str:
    cat = json.loads(row.catalog_json)
    g = json.loads(row.gold_idx)
    return stem(cat[g[0]]["n"]) if g else ""


def load(cfg: str, split: str | None = None) -> pd.DataFrame:
    df = pd.read_parquet(PROC / f"routing_{cfg}.parquet")
    df = df[df.n_candidates > K].copy()
    if split:
        df = df[df.split == split]
    df["catalog_fp"] = df.catalog_json.apply(fingerprint)
    return df.reset_index(drop=True)


def cluster_boot_auc(y: np.ndarray, s: np.ndarray, clusters: np.ndarray,
                     boot: int = CLUSTER_BOOT, seed: int = BOOT_SEED):
    """AUROC resampled by CATALOGUE, the unit that a routing model can memorise."""
    rng = np.random.default_rng(seed)
    uniq = np.unique(clusters)
    idx_of = {c: np.where(clusters == c)[0] for c in uniq}
    out = []
    for _ in range(boot):
        take = np.concatenate([idx_of[c] for c in rng.choice(uniq, size=len(uniq), replace=True)])
        yy, ss = y[take], s[take]
        if yy.sum() in (0, len(yy)):
            continue
        out.append(roc_auc_score(yy, ss))
    return [float(np.percentile(out, q)) for q in (2.5, 97.5)], len(out)


def overlap_audit(src: pd.DataFrame, tgt: pd.DataFrame) -> dict:
    """How much of the target's vocabulary could have been memorised from the source?

    catalog_json persists the short keys the builder writes: n=tool name, d=description, p=params.
    """
    src_names, tgt_names, src_toks, tgt_toks = set(), set(), Counter(), Counter()
    for cj in src.catalog_json:
        for d in json.loads(cj):
            src_names.add(d["n"])
            src_toks.update(toks(d["n"].replace("-", " ").replace("_", " ")) + toks(d["d"])
                            + toks(" ".join(d["p"])))
    for cj in tgt.catalog_json:
        for d in json.loads(cj):
            tgt_names.add(d["n"])
            tgt_toks.update(toks(d["n"].replace("-", " ").replace("_", " ")) + toks(d["d"])
                            + toks(" ".join(d["p"])))
    seen = sum(v for t, v in tgt_toks.items() if t in src_toks)
    tot = sum(tgt_toks.values()) or 1
    PT = {"de", "da", "do", "para", "com", "uma", "que", "nao", "voce", "gostaria", "preciso",
          "quero", "como", "sobre", "e", "em", "os", "as", "por", "mais"}
    EN = {"the", "of", "and", "to", "in", "for", "with", "please", "i", "my", "is", "are",
          "how", "what", "can", "you", "need", "want", "on", "a"}

    def lang_rate(texts):
        pt = en = n = 0
        for t in texts:
            w = set(toks(t))
            pt += len(w & PT); en += len(w & EN); n += 1
        return {"pt_function_word_rate": round(pt / max(1, n), 4),
                "en_function_word_rate": round(en / max(1, n), 4)}

    return {
        "distinct_tool_names": {"source": len(src_names), "target": len(tgt_names),
                                "exact_overlap": len(src_names & tgt_names),
                                "target_names_unseen_in_source": round(
                                    1 - len(src_names & tgt_names) / max(1, len(tgt_names)), 4)},
        "distinct_catalogue_fingerprints": {
            "source": int(src.catalog_fp.nunique()), "target": int(tgt.catalog_fp.nunique()),
            "shared_fingerprints": int(len(set(src.catalog_fp) & set(tgt.catalog_fp)))},
        "target_catalog_token_coverage_by_source": round(seen / tot, 4),
        "instruction_language": {"source": lang_rate(src.question.head(2000).tolist()),
                                 "target": lang_rate(tgt.question.head(2000).tolist())},
    }


def leave_one_family_out(dev: pd.DataFrame, feats_key: str = "all", n_families: int = N_FAMILIES) -> list[dict]:
    """Fit WITHOUT any row whose catalogue contains family f; score rows whose gold tool is in f.

    The test rows necessarily DO contain family f (their gold tool is drawn from it); the exclusion
    applies to the training rows, which is what makes the answer family unseen to the fitted model.
    """
    dev = dev.copy()
    dev["families"] = dev.catalog_json.apply(row_stems)
    dev["gold_family"] = dev.apply(gold_family, axis=1)
    gold_counts = Counter(dev.gold_family)
    rows, skipped_low_positives = [], []
    for fam, _ in gold_counts.most_common():
        if gold_counts[fam] < MIN_FAMILY_ROWS:
            continue
        contains = dev.families.apply(lambda r: fam in r)
        test = dev[dev.gold_family == fam]
        train = dev[~contains]
        if len(test) < MIN_FAMILY_ROWS or len(train) < 200:
            continue
        Xt = matrices(test, FROZEN_FEATURES)[feats_key]
        Xr = matrices(train, FROZEN_FEATURES)[feats_key]
        yt, yr = test[DV].values.astype(int), train[DV].values.astype(int)
        # a family whose test rows contain fewer than MIN_POSITIVES failures cannot give an AUROC at
        # all (measured: some families are 100% non-failing), so it is skipped and counted, not faked.
        if yt.sum() < MIN_POSITIVES or yr.sum() < MIN_POSITIVES:
            skipped_low_positives.append(fam)
            continue
        m = scaled_pipeline(FROZEN_C)().fit(Xr, yr)
        p = m.predict_proba(Xt)[:, 1]
        # same rows scored by a model that WAS allowed to see the family (upper reference)
        aucs_seen = []
        for tr, te in StratifiedKFold(5, shuffle=True, random_state=SEEDS[0]).split(Xt, yt):
            if yt[tr].sum() < 3 or yt[te].sum() == 0 or yt[te].sum() == len(te):
                continue
            mm = scaled_pipeline(FROZEN_C)().fit(Xt[tr], yt[tr])
            aucs_seen.append(roc_auc_score(yt[te], mm.predict_proba(Xt[te])[:, 1]))
        # how much of the test rows' text was absent from the training catalogues
        train_toks = set()
        for cj in train.catalog_json:
            for d in json.loads(cj):
                train_toks.update(toks(d["n"].replace("-", " ").replace("_", " ")) + toks(d["d"])
                                  + toks(" ".join(d["p"])))
        tot = un = 0
        for _, r in test.iterrows():
            for d in json.loads(r.catalog_json):
                if stem(d["n"]) == fam:
                    tt = toks(d["n"].replace("-", " ").replace("_", " ")) + toks(d["d"]) + toks(" ".join(d["p"]))
                    tot += len(tt); un += sum(1 for t in tt if t not in train_toks)
        rows.append({"family": fam, "n_test": int(len(test)), "n_train_excluding_family": int(len(train)),
                     "catalogue_rows_containing_family": int(contains.sum()),
                     "fail_at_3_prevalence_test": round(float(yt.mean()), 4),
                     "auc_unseen_family": round(float(roc_auc_score(yt, p)), 4),
                     "auc_family_seen_cv_reference": round(float(np.mean(aucs_seen)), 4),
                     "auc_length_only": round(float(roc_auc_score(yt, -test.n_tokens.values)), 4),
                     "heldout_family_tokens_unseen_in_train": round(un / max(1, tot), 4)})
        if len(rows) >= n_families:
            break
    return rows, skipped_low_positives


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    exp = {"exp_id": "EXP-0021", "e_id": "E08", "seed": SEEDS[0], "k": K, "dv": DV,
           "frozen_model": {"C": FROZEN_C, "n_canonical_features": len(FROZEN_FEATURES or []),
                            "features_file": "papers/P001_routing_failure_qpp/configs/P001_frozen_model.json"},
           "started_at": time.strftime("%Y-%m-%dT%H:%M:%S")}

    src = pd.concat([load(c, "dev") for c in CONFIGS], ignore_index=True)
    tgt = load(TARGET_CFG)
    print(f"source dev rows={len(src)}  target({TARGET_CFG}) rows={len(tgt)}  "
          f"target fail@3 prevalence={round(float(tgt[DV].mean()), 4)}")

    exp["source"] = {"configs": list(CONFIGS), "n_rows": int(len(src)),
                     "fail_at_3_prevalence": round(float(src[DV].mean()), 4),
                     "mean_catalogue": round(float(src.n_candidates.mean()), 2),
                     "uuid_digests": {c: str(pd.read_parquet(PROC / f"routing_{c}.parquet").uuid_digest.iloc[0])
                                      for c in CONFIGS}}
    exp["target"] = {"config": TARGET_CFG, "n_rows": int(len(tgt)),
                     "splits": {k: int(v) for k, v in tgt.split.value_counts().items()},
                     "fail_at_3_prevalence": round(float(tgt[DV].mean()), 4),
                     "chance_hit_3": round(float(tgt.chance_hit_3.mean()), 4),
                     "mean_catalogue": round(float(tgt.n_candidates.mean()), 2),
                     "mean_gold_per_query": round(float(tgt.n_gold.mean()), 3),
                     "mean_query_tokens": round(float(tgt.n_tokens.mean()), 1),
                     "uuid_digest": str(tgt.uuid_digest.iloc[0]),
                     "note": "SFT carries no metadata column, so EXP-0020 could not verify gold against a "
                             "per-row MCP server tool index; the join is exact-name / unique-suffix only"}
    exp["overlap_audit"] = overlap_audit(src, tgt)
    print("overlap:", json.dumps(exp["overlap_audit"]["distinct_tool_names"], indent=None))
    print("shared catalogue fingerprints:",
          exp["overlap_audit"]["distinct_catalogue_fingerprints"]["shared_fingerprints"])

    # ---------------- Arm 1: fit on source dev, score the unseen pipeline ----------------
    Xs, Xt = matrices(src, FROZEN_FEATURES)["all"], matrices(tgt, FROZEN_FEATURES)["all"]
    ys, yt = src[DV].values.astype(int), tgt[DV].values.astype(int)
    model = scaled_pipeline(FROZEN_C)().fit(Xs, ys)
    p_transfer = model.predict_proba(Xt)[:, 1]
    auc_transfer = float(roc_auc_score(yt, p_transfer))
    ci, nb = cluster_boot_auc(yt, p_transfer, tgt.catalog_fp.values)
    src_ref = [oof_auc(Xs, ys, scaled_pipeline(FROZEN_C), s)[0] for s in SEEDS]
    tgt_dev = tgt[tgt.split == "dev"]
    Xtd = matrices(tgt_dev, FROZEN_FEATURES)["all"]
    ytd = tgt_dev[DV].values.astype(int)
    tgt_within = [oof_auc(Xtd, ytd, scaled_pipeline(FROZEN_C), s)[0] for s in SEEDS]

    arm1 = {
        "auc_transfer_source_dev_to_target": round(auc_transfer, 4),
        "auc_transfer_ci95_catalogue_bootstrap": [round(x, 4) for x in ci], "n_boot_used": nb,
        "auc_source_reference_oof_dev": [round(a, 4) for a in src_ref],
        "auc_target_within_domain_oof_dev": [round(a, 4) for a in tgt_within],
        "auc_target_length_only_B0": round(float(roc_auc_score(yt, -tgt.n_tokens.values)), 4),
        "auc_target_post_retrieval_margin": round(float(roc_auc_score(yt, -tgt.bm25_margin.values)), 4),
        "auc_target_chance_qpp_coverage_only": round(float(roc_auc_score(yt, tgt.qpp_coverage.values)), 4),
        "target_hit_at_3": round(float(1 - tgt[DV].mean()), 4),
        "target_chance_hit_at_3": round(float(tgt.chance_hit_3.mean()), 4),
        "mean_transfer_minus_length": round(auc_transfer - float(roc_auc_score(yt, -tgt.n_tokens.values)), 4),
        "mean_transfer_minus_within_domain": round(auc_transfer - float(np.mean(tgt_within)), 4),
    }
    arm1["verdict"] = ("transfers" if auc_transfer >= 0.65 else
                       "partial" if auc_transfer >= 0.55 else "does not transfer")
    arm1["beats_length_baseline"] = bool(arm1["mean_transfer_minus_length"] > 0)
    exp["arm1_external_pipeline"] = arm1
    print(f"[arm1] transfer AUROC={arm1['auc_transfer_source_dev_to_target']} CI{ci} | "
          f"source OOF={np.mean(src_ref):.4f} | within-target OOF={np.mean(tgt_within):.4f} | "
          f"length-only={arm1['auc_target_length_only_B0']} -> {arm1['verdict']}")

    # -------- Arm 1b: the overlap audit says every target TOOL is familiar, so cut to rows whose
    # -------- catalogue as a whole is absent from the source, and report both numbers.
    src_fp = set(src.catalog_fp)
    src_names = {d["n"] for cj in src.catalog_json for d in json.loads(cj)}
    dis = tgt[~tgt.catalog_fp.isin(src_fp)]
    name_familiar = float(np.mean([
        np.mean([1.0 if d["n"] in src_names else 0.0 for d in json.loads(c)]) for c in dis.catalog_json])) \
        if len(dis) else float("nan")
    yd = dis[DV].values.astype(int)
    arm1b = {"n_rows": int(len(dis)), "n_positives": int(yd.sum()),
             "share_of_target_rows": round(len(dis) / max(1, len(tgt)), 4),
             "mean_tool_names_also_present_in_source": round(name_familiar, 4),
             "fail_at_3_prevalence": round(float(yd.mean()), 4) if len(dis) else None}
    if len(dis) >= 200 and 0 < yd.sum() < len(yd):
        pd_ = model.predict_proba(matrices(dis, FROZEN_FEATURES)["all"])[:, 1]
        arm1b["auc_transfer_disjoint_catalogues"] = round(float(roc_auc_score(yd, pd_)), 4)
        arm1b["ci95_catalogue_bootstrap"] = [round(x, 4) for x in
                                             cluster_boot_auc(yd, pd_, dis.catalog_fp.values)[0]]
        arm1b["auc_length_only_B0"] = round(float(roc_auc_score(yd, -dis.n_tokens.values)), 4)
    exp["arm1b_catalogue_disjoint"] = arm1b
    print(f"[arm1b] disjoint-catalogue rows={arm1b['n_rows']} "
          f"({arm1b['share_of_target_rows']}) auc={arm1b.get('auc_transfer_disjoint_catalogues')} "
          f"tool-name familiarity={arm1b['mean_tool_names_also_present_in_source']}")

    # ---------------- Arm 2: leave-one-tool-family-out inside the source ----------------
    fams, fam_skipped = leave_one_family_out(src)
    exp["arm2_unseen_tool_family"] = {
        "n_families_tested": len(fams), "min_family_rows": MIN_FAMILY_ROWS,
        "min_positives_required": MIN_POSITIVES,
        "families_skipped_for_too_few_failures": fam_skipped,
        "n_families_considered": len(fams) + len(fam_skipped),
        "per_family": fams,
        "mean_auc_unseen_family": round(float(np.mean([f["auc_unseen_family"] for f in fams])), 4) if fams else None,
        "mean_auc_family_seen_reference": round(float(np.mean([f["auc_family_seen_cv_reference"] for f in fams])), 4) if fams else None,
        "mean_auc_length_only": round(float(np.mean([f["auc_length_only"] for f in fams])), 4) if fams else None,
    }
    d = (exp["arm2_unseen_tool_family"]["mean_auc_unseen_family"] is not None and
         exp["arm2_unseen_tool_family"]["mean_auc_family_seen_reference"] is not None)
    if d:
        drop = (exp["arm2_unseen_tool_family"]["mean_auc_family_seen_reference"] -
                exp["arm2_unseen_tool_family"]["mean_auc_unseen_family"])
        exp["arm2_unseen_tool_family"]["mean_drop_vs_seen"] = round(float(drop), 4)
        exp["arm2_unseen_tool_family"]["verdict"] = ("tool-family familiarity is not load-bearing" if drop < 0.02
                                                     else "tool-family familiarity contributes")
    exp["arm2_unseen_tool_family"]["caveat"] = (
        "a family-holdout row still keeps the row's own other catalogue tools, so this removes answer-"
        "family memorisation but not the competitive-structure reuse measured by catalogue-grouped CV")
    print(f"[arm2] families={len(fams)} mean unseen={exp['arm2_unseen_tool_family']['mean_auc_unseen_family']} "
          f"seen-reference={exp['arm2_unseen_tool_family']['mean_auc_family_seen_reference']} "
          f"verdict={exp['arm2_unseen_tool_family'].get('verdict')}")

    exp["headline_impact"] = {
        "published_test_auc_p001": {"OSS": 0.8233, "Qwen3": 0.8294, "Kimi-K2": 0.7951},
        "reading": "D13 reported these as an upper bound for unseen catalogues. Arm 1 measures an unseen "
                   "pipeline directly and Arm 2 measures unseen tool families; whichever way the numbers "
                   "fall, the bound is now evidenced rather than asserted.",
    }
    exp["wallclock_sec"] = round(time.time() - t0, 1)
    exp["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")

    OUT_RAW.mkdir(parents=True, exist_ok=True)
    out = OUT_RAW / f"EXP0021_cross_pipeline_transfer_{time.strftime('%Y%m%dT%H%M%S')}.json"
    out.write_text(json.dumps(exp, indent=1, ensure_ascii=False), encoding="utf-8")
    flat = [{"metric": k, "value": json.dumps(v) if isinstance(v, (list, dict)) else v}
            for k, v in list(arm1.items())]
    pd.DataFrame(flat).to_csv(OUT_PROC / "EXP0021_transfer_summary.csv", index=False)
    pd.DataFrame(fams).to_csv(OUT_PROC / "EXP0021_transfer_families.csv", index=False)
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
