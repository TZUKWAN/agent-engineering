#!/bin/bash
cd "G:/刘俊琦/AGENT ENGINEERING/agentic-information-behavior" || exit 9
L=_round2_scratch/last_seq.log
{
echo "start $(date -Is)"
py -3.11 02_shared_code/registry/round2_register_windows.py --apply 2>&1 | tail -1
py -3.11 02_shared_code/registry/export_package_registry.py 2>&1 | tail -1
py -3.11 02_shared_code/registry/prune_package_evidence.py --apply --all 2>&1 | tail -1
py -3.11 _round2_record_resolutions.py 2>&1 | tail -1
py -3.11 02_shared_code/registry/round2_run_all.py 2>&1 | tail -3
py -3.11 02_shared_code/registry/package_audit.py 2>&1 | tail -1
py -3.11 02_shared_code/registry/spec_completion_audit.py 2>&1 | tail -1
py -3.11 -u _estate_two_pass.py 2>&1 | tail -2
echo "final rc=$?"
echo "end $(date -Is)"
} > "$L" 2>&1
