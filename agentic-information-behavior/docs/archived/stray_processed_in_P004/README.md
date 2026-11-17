# Processed tables that were sitting in P004's folder but belong to other papers

Moved out of `papers/P004_shipped_quality_score_validity/results_processed/` on 2026-09-21, not deleted: each file is
byte-identical to the copy that remains in the package whose experiment produced it, so nothing is lost and the record
of how they got here is kept.

| file | owning experiment | where the live copy is |
|---|---|---|
| `EXP0045_data_derived_units.csv` | EXP-0045 (P003's concept-inventory sensitivity) | `papers/P003_metadata_interoperability/results_processed/` |
| `EXP0046_bridge_contingency.csv` | EXP-0046 (P001's error analysis) | `papers/P001_routing_failure_qpp/results_processed/` |
| `EXP0046_error_taxonomy.csv` | EXP-0046 (P001) | `papers/P001_routing_failure_qpp/results_processed/` |
| `EXP0046_read_cases.csv` | EXP-0046 (P001) | `papers/P001_routing_failure_qpp/results_processed/` |
| `EXP0048_governance_presence.csv` | EXP-0048 (P005's pilot) | `papers/P005_governance_metadata_verifiability/results_processed/` |
| `EXP0049_disagreement_instances.csv` | EXP-0049 (P005) | `papers/P005_governance_metadata_verifiability/results_processed/` |
| `EXP0049_level_census.csv` | EXP-0049 (P005) | `papers/P005_governance_metadata_verifiability/results_processed/` |

**Why they were wrong to keep.** Spec §0 item 9 defines `results_processed/` as the summaries a package's own scripts
generate from its own `results_raw/`. Seven files here summarise other papers' experiments, so a reader of P004's folder
would have taken another construct's measurement - P001's routing-failure taxonomy, P005's rights census - as evidence
about shipped quality scores. It already had one consequence: the first version of
`02_shared_code/plotting/p004_roles.py` drew P004's §15 data schematic from `EXP0045_data_derived_units.csv`. The figure
is now drawn from P004's own EXP-0041 presence scan (`tables/table_presence_scan.csv`), and no P004 document cites these
paths any more.

**How they arrived.** A historical gap-filling step copied related tables into package folders; the scripts that produce
these files today write to the workspace-level `results_processed/` or to their own package, and none of them is in
P004's `reproduce.sh`, so a rebuild does not restore these copies. `package_audit.py` now flags any
`results_processed/EXP*.csv` whose registry `paper_id` names a different paper, and any path cited by a package's
`paper.md` / `appendix.md` / `FIGURE_PLAN.md` that does not resolve inside that package.
