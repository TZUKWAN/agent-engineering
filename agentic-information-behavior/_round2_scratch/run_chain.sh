#!/bin/bash
cd "G:/刘俊琦/AGENT ENGINEERING/agentic-information-behavior" || exit 9
py -3.11 -u _round2_final_chain.py > _round2_scratch/chain_run.log 2>&1
echo "chain rc=$?" >> _round2_scratch/chain_run.log
