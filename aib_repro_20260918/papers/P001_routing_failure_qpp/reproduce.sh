#!/usr/bin/env bash
# P001 end-to-end reproduction: dataset audit -> join feasibility -> routing dataset ->
# dev selection -> dev robustness/inference -> figures & tables.
#
# The FINAL TEST stage is deliberately NOT part of reproduce.sh: the protocol allows exactly
# one test evaluation, recorded in papers/P001_routing_failure_qpp/test_eval_ledger.json.
# Re-running it requires an explicit --override-reason and a deviations.md entry.
#
# Interpreter must be given absolutely: `python` on PATH is the WindowsApps stub here.
set -euo pipefail

PY="${AIB_PYTHON:-D:/Environment/anaconda3/python.exe}"
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
ROWS="${AIB_ROWS:-15000}"
SHARDS="${AIB_SHARDS:-10}"
SEED=42

echo "[repro] interpreter: $PY"
"$PY" -c "import sys,numpy,pandas,pyarrow,sklearn,scipy,matplotlib;print('python',sys.version.split()[0]);print('numpy',numpy.__version__,'pandas',pandas.__version__,'pyarrow',pyarrow.__version__,'sklearn',sklearn.__version__,'scipy',scipy.__version__)"

cd "$ROOT"
echo "[repro] 1/8 program-level dataset audit (seed=$SEED)"
"$PY" 02_shared_code/data_audit/audit_datasets.py --rows 3000 --shards 3

echo "[repro] 2/8 gold-label grounding probe"
"$PY" 02_shared_code/data_audit/probe_gold_tool_grounding.py --rows 1000 || echo "[repro] grounding below threshold for some config (expected: SFT)"

echo "[repro] 3/8 split-integrity / contamination audit"
"$PY" 02_shared_code/data_audit/audit_split_integrity.py --rows 3000

echo "[repro] 4/8 build routing dataset ($ROWS rows/config, $SHARDS shards/config)"
"$PY" 02_shared_code/trajectory_parser/build_toucan_routing_dataset.py --rows-per-config "$ROWS" --shards-per-config "$SHARDS"

echo "[repro] 5/8 development selection + robustness/inference (5 seeds)"
"$PY" 02_shared_code/statistics/run_p001_experiments.py --stage dev-select --repeats 5
"$PY" 02_shared_code/statistics/run_p001_experiments.py --stage robust    --repeats 5

echo "[repro] 6/10 H4 alternative dependent variable (development only; never touches test)"
"$PY" 02_shared_code/statistics/equivalence_relabel_h4.py
"$PY" 02_shared_code/statistics/adjudicate_equivalence_sample.py --write

echo "[repro] 7/10 controlled catalog interventions and statistical-unit corrections"
"$PY" 02_shared_code/statistics/catalog_intervention_e17.py
"$PY" 02_shared_code/trajectory_parser/build_catalog_disjoint_split.py
"$PY" 02_shared_code/statistics/hierarchical_dependence.py
"$PY" 02_shared_code/statistics/catalogue_clustered_inference.py

echo "[repro] 8/10 E08: external-catalogue availability probe and cross-corpus transfer"
"$PY" 02_shared_code/data_audit/probe_external_catalogue_availability.py
"$PY" 02_shared_code/data_audit/probe_hermes_toolcalls.py
"$PY" 02_shared_code/trajectory_parser/build_toucan_routing_dataset.py --configs SFT \
     --exp-id EXP-0020 --rows-per-config "$ROWS" --shards-per-config "$SHARDS"
"$PY" 02_shared_code/statistics/cross_pipeline_transfer_e08.py
"$PY" 02_shared_code/statistics/external_corpus_transfer_hermes.py

echo "[repro] 9/11 E03b: trained dense comparator (CPU, no test row read; ~10 min)"
"$PY" 02_shared_code/statistics/dense_comparator_e03b.py

echo "[repro] 10/11 figures, tables and the paper-level package"
"$PY" papers/P001_routing_failure_qpp/scripts/make_figures_tables.py
"$PY" papers/P001_routing_failure_qpp/scripts/package_p001.py

echo "[repro] 11/11 verifying the rebuilt dataset is the SAME sample the paper reports on"
# The row SET depends on --shards-per-config, whose default is not this run's value (deviation D11).
"$PY" - <<'EOF'
import hashlib, json, sys
import pandas as pd
anchor = json.load(open("01_datasets/manifests/routing_sample_identity.json", encoding="utf-8"))["configs"]
for cfg in ("OSS", "Qwen3", "Kimi-K2"):
    df = pd.read_parquet(f"01_datasets/processed/routing_{cfg}.parquet")
    got = hashlib.sha256("|".join(sorted(df.uuid.astype(str))).encode()).hexdigest()[:16]
    want = anchor[cfg]["uuid_digest"]
    prev = round(float(df[(df.split == "dev")].fail_at_3.mean()), 4)
    print(f"  {cfg:8s} digest {got} expect {want} {'OK' if got == want else 'MISMATCH'}  dev fail@3 {prev}")
    if got != want:
        sys.exit(f"[repro] SAMPLE MISMATCH in {cfg}: the paper's numbers do not apply to this build")
EOF

echo "[repro] verifying claim evidence files exist"
for f in results_raw/EXP0012_FINAL_TEST_*.json results_raw/EXP0014_equivalence_relabel_*.json \ \n         results_raw/EXP0015_equivalence_adjudication_*.json \ \n         papers/P001_routing_failure_qpp/claims_evidence_matrix.csv \ \n         papers/P001_routing_failure_qpp/tables/table3_main_test.csv \ \n         papers/P001_routing_failure_qpp/tables/table9_h4_equivalence_relabel.csv \ \n         results_raw/EXP0016_catalog_intervention_*.json \n         results_raw/EXP0017_hierarchical_dependence_*.json \n         results_raw/EXP0019_catalogue_clustered_inference_*.json \n         papers/P001_routing_failure_qpp/tables/table10_catalog_interventions.csv \n         papers/P001_routing_failure_qpp/tables/table11_dependence_and_inference.csv \n         results_raw/EXP0021_cross_pipeline_transfer_*.json \ \n         results_raw/EXP0023_hermes_transfer_*.json \n         results_raw/EXP0024_dense_comparator_*.json \n         papers/P001_routing_failure_qpp/tables/table13_dense_comparator.csv \ \n         papers/P001_routing_failure_qpp/tables/table12_external_transfer.csv \ \n         results_raw/SUPERSEDED_ARTIFACTS.json \n         papers/P001_routing_failure_qpp/environment/dependencies.txt; do
  ls $f >/dev/null 2>&1 || { echo "[repro] MISSING $f (EXP-0012 must be run once manually)"; exit 1; }
done
echo "[repro] done. Regenerable artefacts are in results_raw/, results_processed/, papers/P001_routing_failure_qpp/{figures,tables}/"
