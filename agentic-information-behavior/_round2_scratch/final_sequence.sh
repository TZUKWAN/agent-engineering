#!/bin/bash
# Final verification sequence for round 2, run only after every generator fix has landed:
#   1. the five pre-wave packages get the same chain the wave packages get (the estate's reassemble loop skips them,
#      which is why two packages shipped prose naming a record they did not carry);
#   2. the full 18-step closing chain re-runs, whose last step is the two-pass rebuild that must measure the estate
#      in its final state.
cd "G:/刘俊琦/AGENT ENGINEERING/agentic-information-behavior" || exit 9
L=_round2_scratch/final_seq.log
CHAIN="writing/export_figure_plan.py writing/embed_paper_artefacts.py registry/export_package_registry.py registry/build_package_configs_readme.py registry/reconcile_package_evidence.py"
{
  echo "start $(date -Is)"
  for p in P001 P002 P003 P004 P005; do
    for s in $CHAIN; do
      py -3.11 "02_shared_code/$s" --paper "$p" >> "_round2_scratch/prewave_${p}_chain.log" 2>&1
      echo "$p $s rc=$?"
    done
  done
  echo "--- closing chain $(date -Is) ---"
  py -3.11 -u _round2_final_chain.py
  echo "chain rc=$?"
  echo "end $(date -Is)"
} > "$L" 2>&1
