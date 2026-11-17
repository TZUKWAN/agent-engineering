#!/bin/bash
cd "G:/刘俊琦/AGENT ENGINEERING/agentic-information-behavior" || exit 9
L=_round2_scratch/fix2_seq.log
{
echo "start $(date -Is)"
py -3.11 02_shared_code/registry/reconcile_package_evidence.py 2>&1 | tail -3
py -3.11 02_shared_code/registry/prune_package_evidence.py --apply --all 2>&1 | tail -3
py -3.11 _round2_record_resolutions.py 2>&1 | tail -1
py -3.11 02_shared_code/registry/round2_run_all.py 2>&1 | tail -2
py -3.11 02_shared_code/registry/package_audit.py 2>&1 | tail -1
echo "end $(date -Is)"
} > "$L" 2>&1
