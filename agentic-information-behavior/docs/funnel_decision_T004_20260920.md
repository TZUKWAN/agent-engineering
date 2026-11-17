# Funnel decision — T004 (Real Human vs Synthetic Agent Instructions), 2026-09-20 02:06

Probe: `02_shared_code/data_audit/provenance_label_feasibility_t004.py` → `results_raw/EXP0054_provenance_label_feasibility_20260920T015841.json`.

## What the topic needed, and what the data has

T004 was registered against an AgentNet file of 22,811 human instructions. Listing the tree shows AgentNet is not on this machine: the eight releases under `MATLABINTOKEN/datasets` are all there is. The re-scoped question was therefore whether any of those eight **declares** instruction provenance (human-written vs model-generated or model-rewritten) in a column usable as a label.

Exactly one release does: **Toucan-1.5M**, whose `subset_name` carries `single-turn-original` (human-authored), `single-turn-diversify` (LLM-rewritten), `multi-turn` and `irrelevant`. Releases with any categorical column at all: AgentTrove, SWE-ZERO, Toucan-1.5M, hermes. The others' columns are task taxonomies or generator identities, not provenance statements:

- **Toucan-1.5M**: ['subset_name'] → {'subset_name': ['single-turn-diversify', 'multi-turn', 'irrelevant']}
- **SWE-ZERO**: ['trajectory_format'] → {'trajectory_format': ['mini-swe-agent-1']}
- **hermes**: ['category', 'subcategory'] → {'category': ['Browser Automation', 'Repository Tasks'], 'subcategory': ['Browser Tasks', 'Environment Setup', 'Bug Fix', 'Codebase Exploration', 'Feature Implementation', 'Testing']}
- **AgentTrove**: ['agent', 'original_teacher', 'trace_source'] → {'agent': ['terminus-2'], 'original_teacher': ['GPT 5.1 Nano'], 'trace_source': ['None']}

## The separability numbers

- **Toucan-1.5M / `subset_name`** comparing ['single-turn-diversify', 'multi-turn']: n=4000, AUC=0.9579, length-only=0.7416, permutation null=0.5017 (max over 10 shuffles 0.5218), longer group **single-turn-diversify**, mean tokens {'single-turn-diversify': 192.0, 'multi-turn': 176.6}, dependence key `uuid`.
- **Toucan-1.5M / `subset_name`** comparing ['single-turn-diversify', 'irrelevant']: n=2500, AUC=0.8548, length-only=0.8305, permutation null=0.5024 (max over 10 shuffles 0.5305), longer group **single-turn-diversify**, mean tokens {'single-turn-diversify': 192.0, 'irrelevant': 93.8}, dependence key `uuid`.
- **Toucan-1.5M / `subset_name`** comparing ['multi-turn', 'irrelevant']: n=3750, AUC=1.0, length-only=0.8275, permutation null=0.4938 (max over 10 shuffles 0.5134), longer group **multi-turn**, mean tokens {'multi-turn': 176.6, 'irrelevant': 93.8}, dependence key `uuid`.

Reported but excluded from the GO count by the (repaired) rule — these are task taxonomies, and the first version of the rule let one clear the bar:
- hermes / `category`: {'Browser Automation': 964, 'Repository Tasks': 336}
- hermes / `subcategory`: {'Browser Tasks': 964, 'Environment Setup': 84, 'Bug Fix': 81, 'Codebase Exploration': 59, 'Feature Implementation': 57, 'Testing': 36, 'Documentation': 9, 'Maintenance': 9}

## Why the topic is not promoted

1. **One corpus only.** The construct is declared in a single release, so any claim would rest on n=1 corpus with no external-validity check available. That is the same wall T007 hit from the other side.
2. **It would re-slice P001.** Toucan's `subset_name` is precisely the covariate P001 had to scope its H1–H3 claims to after EXP-0034/0035 showed the published sample is one subset and the predictor does not transfer to `single-turn-diversify`. A register study on those same subsets would be a second paper over P001's own controls, which the anti-repetition rule forbids.
3. **The central contrast was never tested.** The probe's pair filter (`n >= 60` among the four most common values) dropped `single-turn-original` from the pairs it scored, so the 3 contrasts above are diversify/multi-turn/irrelevant against each other. The AUCs are high (0.85–1.00) and every one of them beats its permutation null, but they do **not** answer human-vs-synthetic. Recorded as an outstanding gap; the topic is not killed on a null it never measured.
4. **What the rule defects taught.** Two fixes belong to the next pilot, both recorded here rather than silently applied: a label allowlist (provenance statements only — a task taxonomy cleared the original bar), and stratified sampling over config directories (the first version read the first three files' first row groups and concluded Toucan declared one subset value, which is false).

**Status: `not_promoted_single_corpus_and_p001_overlap`.** Reversible by obtaining a second release that declares human-authored instructions (the blocked-data class of T015), or by a register study that is explicitly *not* built on Toucan.

---

## Correction (2026-09-20, EXP-0073)

One factual premise in this document is withdrawn: *"AgentNet is not on this machine"*. It is on this machine, at
`MATLABINTOKEN/data/raw/` - 22,625 task lines and 410,987 `last_step_correct` step labels, measured in
`results_raw/EXP0073_agentnet_reaudit_20260920T050725.json`
and written up in `docs/funnel_correction_agentnet_20260920.md`. The listing that produced the claim covered only
`MATLABINTOKEN/datasets`.

The decision itself is unchanged, and the reason matters: this document's conclusion was that only one release
**declares** instruction provenance. AgentNet has now been checked for that directly rather than assumed away, and it
declares none - no provenance field exists in the parsed sample, and the byte-level matches on `"human`/`"annotat`
sit inside free-text observation strings. The single-corpus objection therefore still holds over nine readable
releases instead of eight. What the error does cost is a topic that was parked partly behind the false premise: T029's
data blocker is removed by this measurement.
