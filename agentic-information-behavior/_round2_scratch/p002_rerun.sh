#!/bin/bash
# Re-run P002's frozen pipeline from reproduce.sh lines 21, 25, 33, 26, in that order, after the bits-per-trajectory
# fix. Each step's exit code is kept so a failure is visible in the log rather than silent.
cd "G:/刘俊琦/AGENT ENGINEERING/agentic-information-behavior" || exit 9
L=_round2_scratch/p002_rerun.log
{
  echo "start $(date -Is)"
  py -3.11 02_shared_code/statistics/isp_stage_main_p002.py           2>&1 | tail -6; echo "rc(main)=$?"
  py -3.11 02_shared_code/behavior_tagger/isp_stage_codex_agenttrove.py 2>&1 | tail -6; echo "rc(agenttrove)=$?"
  py -3.11 02_shared_code/behavior_tagger/isp_stage_codex_agenttrove_second.py 2>&1 | tail -4; echo "rc(second)=$?"
  py -3.11 02_shared_code/registry/record_exp0092_p002.py             2>&1 | tail -6; echo "rc(record)=$?"
  py -3.11 papers/P002_isp_stage_measurement/scripts/build_package.py 2>&1 | tail -6; echo "rc(build)=$?"
  echo "end $(date -Is)"
} > "$L" 2>&1
