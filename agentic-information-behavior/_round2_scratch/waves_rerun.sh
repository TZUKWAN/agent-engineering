#!/bin/bash
cd "G:/刘俊琦/AGENT ENGINEERING/agentic-information-behavior" || exit 9
py -3.11 -u _round2_rerun_designs.py --waves 11 12 --apply > _round2_scratch/waves11_12.log 2>&1
echo "rc=$?" >> _round2_scratch/waves11_12.log
