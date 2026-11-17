#!/bin/bash
# Apply the two fixes round 2 just surfaced (the pilot recorder's swapped paper_id/topic_id, and the citation
# pattern that could not see a letter-suffixed run id), then re-run exactly the steps that consume them.
cd "G:/刘俊琦/AGENT ENGINEERING/agentic-information-behavior" || exit 9
L=_round2_scratch/fix_seq.log
CHAIN="writing/export_figure_plan.py writing/embed_paper_artefacts.py registry/export_package_registry.py registry/build_package_configs_readme.py registry/reconcile_package_evidence.py"
{
  echo "start $(date -Is)"
  py -3.11 papers/P002_isp_stage_measurement/scripts/register_pilot.py 2>&1 | tail -2; echo "rc(register_pilot)=$?"
  py -3.11 02_shared_code/registry/fix_prewave_registry_rows_p001.py 2>&1 | tail -1
  py -3.11 02_shared_code/registry/supersede_undeclared_generations.py --apply 2>&1 | tail -1
  py -3.11 02_shared_code/registry/round2_register_windows.py --apply 2>&1 | tail -1
  for p in P001 P002 P003 P004 P005; do
    for s in $CHAIN; do py -3.11 "02_shared_code/$s" --paper "$p" >> "_round2_scratch/prewave_${p}_chain.log" 2>&1 || echo "$p $s FAILED"; done
    echo "chain $p done"
  done
  py -3.11 02_shared_code/registry/prune_package_evidence.py --apply --all 2>&1 | tail -3
  py -3.11 02_shared_code/registry/export_package_registry.py 2>&1 | tail -1
  py -3.11 _round2_record_resolutions.py 2>&1 | tail -1
  py -3.11 02_shared_code/registry/round2_run_all.py 2>&1 | tail -3
  py -3.11 02_shared_code/registry/package_audit.py 2>&1 | tail -2
  py -3.11 02_shared_code/registry/spec_completion_audit.py 2>&1 | tail -1
  echo "end $(date -Is)"
} > "$L" 2>&1
