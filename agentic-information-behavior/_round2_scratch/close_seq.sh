#!/bin/bash
cd "G:/刘俊琦/AGENT ENGINEERING/agentic-information-behavior" || exit 9
L=_round2_scratch/close_seq.log
{
echo "start $(date -Is)"
ls -l --time-style=+%H:%M results_raw/ESTATE_TWO_PASS_REBUILD.json
py -3.11 02_shared_code/registry/record_exp0103_0105_docs.py 2>&1 | tail -4
for p in P001 P002 P003 P004 P005; do py -3.11 02_shared_code/registry/reconcile_package_evidence.py --paper $p 2>&1 | tail -1; done
py -3.11 02_shared_code/registry/prune_package_evidence.py --apply --all 2>&1 | tail -1
py -3.11 _round2_record_resolutions.py 2>&1 | tail -1
py -3.11 02_shared_code/registry/round2_run_all.py 2>&1 | tail -2
py -3.11 02_shared_code/registry/package_audit.py 2>&1 | tail -1
py -3.11 02_shared_code/registry/spec_completion_audit.py 2>&1 | tail -1
py -3.11 -u _estate_two_pass.py 2>&1 | tail -2
echo "twopass rc=$?"
echo "end $(date -Is)"
} > "$L" 2>&1
