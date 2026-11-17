"""Record how each round-2 problem class was resolved, into the status file the problem list reads.

`docs/ROUND2_PROBLEM_LIST.md` is generated, and the status of every item comes from
`results_raw/ROUND2_PROBLEM_STATUS.json`. This writes those statuses from a table where each entry states, in the
order the objective asks for, what was wrong, what was changed to fix it, and which registered run proves the fix.
A class is recorded once against the problem name when the fix is in the shared code every package is built from;
against the exact item key when only that artefact was affected; and as a triage when the measurement shows the
detected pattern is not a defect - which has to say what was measured, or triage is just a way to stop looking.

    python _round2_record_resolutions.py
"""
from __future__ import annotations

import datetime
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
F = ROOT / "results_raw" / "ROUND2_PROBLEM_STATUS.json"

R = {
    # ---- S3: a registered run a reader cannot open --------------------------------------------
    "cited_artefact_not_in_package|fix": (
        "68 packages cited 30 shared runs (the second auditor EXP-0089, the contamination and cost censuses "
        "EXP-0104/0105, each wave's premise census) that no package folder held. `wave_package.mirror_evidence` "
        "now copies every run the package's own register declares *and* every `EXP-0nnn` its prose, tables or "
        "scripts name, resolving each id through the master register and skipping retired generations. The scanned "
        "set deliberately excludes `results_raw/` and `results_processed/`, so the copy step cannot feed on its own "
        "output and the rebuild stays byte-identical."),
    "artefact_generation_no_registry_row_declares|fix": (
        "1,432 files in the two results folders belonged to no record. EXP-0229 re-pointed 75 registry rows at the "
        "generation a package actually cites, adopted 165 companion outputs (a CSV or verdict JSON that carries the "
        "run's own id under a different stem) into the row of the run that wrote them, and retired the rest with the "
        "field-by-field difference against the kept generation as the written reason. A re-run of the same rule now "
        "reports 0 unaccounted files, and nothing was deleted."),
    "no_kept_artefact_for_a_registered_run|fix": (
        "EXP-0008 was the only registered run with no artefact at all: an inline console probe. Its three "
        "quantities were re-measured by the promoted script `toucan_split_contamination_probe.py` (EXP-0225), the "
        "row is marked `superseded_by_EXP-0225`, and the 7.1 % prompt_id figure it carried stayed withdrawn (D61) "
        "because the promoted measurement is 0.868 of pooled prompts, not 7.1 %."),
    "run_has_no_script_that_can_be_rerun|fix": (
        "EXP-0014b's `script` cell named a module rather than a file, so its persistence audit could not be "
        "re-opened. `persistence_replication_audit_p001.py` (EXP-0227) re-ran the same population as a script and "
        "swept PYTHONHASHSEED 0/1/42: the `fail_at_3` label reproduced for all 19,198 dev rows at every seed with 0 "
        "flips, while `bm25_best_rank` differed on 2-5 rows per process, every one an exact BM25 score tie, and not "
        "the same rows from one seed to the next. Deviation D62 replaced the single-draw count in `dataset_card.md` "
        "and `final_audit.md` with that measured spread; the frozen builder was left untouched because nine shipped "
        "analyses import its BM25."),
    "declared_output_glob_matches_nothing|fix": (
        "Two causes, both real. The resolver split `outputs` cells on every comma, which cut the brace list "
        "`routing_{OSS,Qwen3,Kimi-K2}.parquet` into fragments that match nothing - `round2_run_reality.parts_of()` "
        "now splits outside braces and treats a single-token brace as the placeholder it is. And EXP-0007's row "
        "named a summary with the wrong second plus the three routing frames the builder documents but the register "
        "omitted; EXP-0228 corrected both paths against the files on disk."),
    "artefact_files_under_a_different_id|class_triage": (
        "Not a defect, and now bounded: EXP-0006b is the five-seed re-run of EXP-0006's ladder, and "
        "`analyze_routing_failure.py` named every artefact after its own hard-coded id, so the re-run's JSON and CSV "
        "carry EXP-0006's prefix. The row names the exact timestamped file, which exists and is shipped, so the run "
        "is openable. The recurrence was closed at source - the script takes `--exp-id` now - and the one file the "
        "two runs genuinely shared, `EXP0006_auc_table_fail_at_3.csv`, is named in the ledger because the bytes on "
        "disk are the later run's."),
    "package_ships_only_a_superseded_generation|fix": (
        "Four P043/P044 copies held a retired generation without the kept one beside it. `mirror_evidence` skips "
        "files the ledger retires, and the full re-assembly after EXP-0229 rewrote those folders."),
    # ---- S2: a verdict a reader cannot re-derive ----------------------------------------------
    "four_way_verdict_without_a_recorded_direction|class_fix": (
        "A four-way word (supported/opposite) asserts which side of zero the estimate fell on, and the artefact "
        "row carried no direction to check it against. `wave_lib.attach_directions()` now copies the design's frozen "
        "predicted side onto every model row at write time, so the verdict is re-derivable from the row itself; "
        "39 wave families gained the field in the re-run, and the re-pass report records that no estimate moved. "
        "The second sweep closed the two ways this could still fail: the rule was read only from a top-level "
        "`models` list, so a wave-1 summary keyed by topic (`{\"T101\": {\"models\": [...]}}`) or a design that files "
        "one hypothesis under its own name (`{\"H2\": {...}}`) normalised nothing - `wave_lib.normalise_rows()` now "
        "walks the artefact and applies the same rules to every verdict row, resolving the topic from the master "
        "register when the artefact does not state one; and the row's declared side was read only under "
        "`verdict_direction`, so EXP-0123's `direction_predicted: \"negative (retention reduces loss)\"` looked like "
        "a missing prediction while it was present under another name - all three names are read now, by the writer "
        "and by the detector alike."),
    "verdict_not_implied_by_its_own_numbers|class_fix": (
        "Six rows printed `opposite` on a hypothesis whose frozen sentence names no direction (waves 1, 3, 4, 5): "
        "the word means \"against the prediction\", and there was no prediction to go against. `finalize_models()` "
        "now re-derives a direction-free row with `magnitude_verdict()` - the estate's own direction-free rule, on "
        "the row's interval, its corrected p and the floor its design states - so the word follows from the numbers "
        "instead of from the sign the script happened to see first. The same re-derivation turned EXP-0124's "
        "displacement row from `null` into `opposite`: the estimate is -0.4849 with an interval of [-0.4914, "
        "-0.4787], which is a separation on the unexpected side, and a bespoke three-way expression had been "
        "folding it into `null`. Rows whose recorded direction contradicts the verb in its explanation are read by "
        "the declared prefix first, because \"predicted_positive: a states a result more and an exception less\" "
        "names both sides."),
    "verdict_side_of_zero_contradicts_the_interval|class_fix": (
        "Read as a defect and fixed as one, but it belongs to the row's naming rather than its arithmetic: the row "
        "printed an interval of a *different* statistic than the estimate beside it (EXP-0124's odds ratio against "
        "the bootstrap interval of a relative-selection ratio). The row now names the quantity its interval belongs "
        "to (`ci_of`), prints that quantity's own value, and states the value the hypothesis measures against "
        "(`null_value`, 1.0 for a ratio and 0.5 for a chance-level proportion); the writer and the detector both "
        "shift to the difference from that null before testing the side of zero, so a legitimate non-zero null is "
        "no longer read as a contradiction."),
    "four_way_verdict_without_an_interval|class_fix": (
        "Handled by `wave_lib.finalize_models()` at the point of writing: a row that prints a four-way word with no "
        "interval becomes `not_estimable_interval_not_reported`, one whose statistic is not a number becomes "
        "`not_estimable_interval_not_a_number`, and a statistic the freeze never gave a corrected p for is relabelled "
        "`not_estimable_no_corrected_p_in_the_frozen_family` rather than left claiming support. Nothing was promoted "
        "to a stronger word by this change - 8 wave families lost a `supported` or `null` label to a not-estimable "
        "one, and their Holm-corrected p was derived from their own p_raw values where the frozen family declared "
        "it. The second sweep found the opposite failure in the same line of work: a design that resamples files "
        "its interval under the name of the resampling (`ci_clustered`, `ci_boot`), and reading only `ci_lo`/`ci_hi` "
        "called four rows verdicts with no interval - two of them demoted to `not_estimable_*` by the writer itself "
        "before the round-2 re-run put them back. Both the writer (`wave_lib.row_interval`) and the detector now "
        "read any of the estate's interval names, so a claim the row does evidence is no longer demoted for a "
        "naming reason."),
    "four_way_verdict_row_missing_fields|class_fix": (
        "Same writer: a row missing the fields a verdict needs is relabelled to the matching `not_estimable_*` word "
        "and the reason is written into the row's `note`, so the shipped table says why it stopped being an estimate. "
        "Eight bootstrap rows in waves 9, 11 and 12 printed a blank standard error under a four-way word because "
        "nothing on the row said where its interval came from - and a cluster bootstrap has no analytic standard "
        "error to print. The helper that computed them now returns its own provenance (`ci_kind`, `p_kind`, "
        "`draws_used`) and the rows carry it, so the reader sees a resampling interval and a resampling tail count "
        "rather than a missing quantity; nothing was invented to fill the blank. A row whose declared rule is "
        "descriptive is checked for that before the missing-quantity demotions, so EXP-0125's kappa census reads "
        "`measured_descriptively_rule_declared_non_inferential` - the design asked for the disagreement to be "
        "characterised - instead of `not_estimable_no_interval`, which would have said the design failed to measure "
        "what it never claimed to test."),
    "four_way_verdict_on_a_non_finite_or_explosive_fit|class_fix": (
        "`wave_lib._drop_non_finite()` writes NaN and infinities as null, and a verdict printed on such an interval "
        "is not estimable rather than partial. Wave 1's nested-gain row, which had printed `partial` beside a NaN "
        "interval, now reads `below_the_frozen_floor_measured_0p0005` with `verdict_rule=nested_gain_partial_r2`."),
    "interval_stored_per_class_not_on_the_row|class_fix": (
        "`round2_statistical_consistency.interval_of()` now reads a per-class interval map, so a row whose interval "
        "lives in a sibling structure is no longer reported as having none; the underlying artefacts were not "
        "restructured."),
    "holm_value_not_reproducible|class_fix": (
        "`finalize_models()` derives the missing `p_holm` from the run's own p_raw values inside the Holm family its "
        "freeze names, marks the row `p_holm_derived_by_round2_finalize`, and the independent recomputation in this "
        "round's statistical-consistency detector re-runs the step-down and compares."),
    "package_copy_differs_from_the_programme_artefact|fix": (
        "The packages' evidence folders had drifted from the register they ship: `mirror_evidence` copied artefacts "
        "by name pattern and never removed what an earlier pass had put there, so 13,097 copies across the estate "
        "were generations the supersession ledger had retired or another paper's runs - P001 alone held 71 retired "
        "generations of the programme's own completion audit while the generation its register named was not in the "
        "folder. Resolution is now one function for the whole estate, `wave_package.package_evidence()`: it takes "
        "the runs the package's register declares and the runs its prose names, resolves each to the generation the "
        "ledger leaves standing, copies those in byte for byte, and deletes every copy in `results_raw/` and "
        "`results_processed/` that the same resolution does not select - refusing to delete a file whose only copy "
        "is inside the package, because the programme's own results folders must still hold what it retires. A file "
        "a shipped document points at by name is kept and reported rather than quietly removed: that is a citation "
        "the register cannot resolve. EXP-0231 ran the same function over the five hand-built packages, which the "
        "factory does not assemble, and pruned 159 copies with no unsourced loss. The rule is now applied to all 70 "
        "packages as a chain step, which also copies *in* what a package cites and never held: the ten premise-gated "
        "packages name the censuses that stopped them (EXP-0142, EXP-0190/0191/0195/0196/0197/0202/0203/0205/0206) "
        "while shipping no evidence folder at all, so a reader of `BLOCKED.md` could not open the measurement the "
        "gate rests on. 28 such citations across 10 packages resolved to real files."),
    # ---- S1: numbers that were not what the data says -----------------------------------------
    "support_matcher_accepted_any_number|fix": (
        "The round's most serious finding, and it is a finding about this round's own checking. The provenance "
        "detector asks whether a figure a package printed is a value some measurement produced, and it reported 0 "
        "unsupported table cells and 0 unsupported prose numbers across 70 packages. That result was produced by a "
        "matcher with no power: `round2_lib.Pools.derived()` accepted a share of a total by multiplying the candidate "
        "figure by every sum and every difference of any two numeric cells of any row of the package - 231 to "
        "1,130,852 candidate denominators - and passing when the product landed within half a count of anything in "
        "the pool. Measured on 1,500 random four-decimal numbers drawn across five packages, it accepted "
        "1,500 of 1,500 (87 % of them through that one branch); measured against the 1,260 figures the sampled "
        "packages' own tables print, changing the last printed digit of every one of them was still accepted "
        "1,260 of 1,260. So the two zero-results described the matcher, not the data, and the same pools are used by "
        "the claim-support detector. The fix narrows the derivation to the arithmetic a reader actually performs: "
        "a share or ratio must have both of its terms in one and the same row of a shipped table (0.4919 = "
        "605 / (605 + 625); a relative selection ratio = two cells of one row), matched at the precision the figure "
        "is printed to, while the difference and product branches keep their requirement that both terms be values "
        "the package holds. Measured after the change: of 1,985 numeric cells the five sampled packages' own tables "
        "print, 1,985 are still accepted, while unrelated four-decimal figures are now accepted 5.0 % of the time as "
        "the detector calls it (3.4 % with no sentence context) instead of 100 % - and the control is no longer a "
        "one-off probe but a field the detector writes for every package, `matcher_specificity`, so a future zero "
        "findings is published next to the rate at which the same matcher would pass a number nobody measured."),
    "value_pool_read_only_the_newest_generation|fix": (
        "P005's contamination table printed `0.129` for the AgentTrove `episode` key, and the narrowed matcher called "
        "it invented. The figure is real: EXP-0104, the contamination and leakage audit, was run once per scope "
        "(`--only P005`, `--only ROUTING`, then over everything), the register declares all four JSON records it "
        "wrote, and the supersession ledger retires none of them because none replaced another. The number pool "
        "nevertheless took only the newest file per experiment id, which happened to be a run that had not scanned "
        "P005 at all - so a package's own quoted counts were invisible to the check that is supposed to confirm them, "
        "while all four records sat in the package's evidence folder. `round2_lib.value_pool()` now reads every "
        "generation the register declares for a cited run, and only falls back to the newest when a row declares "
        "nothing that exists."),
    "freeze_document_quotes_a_retired_generation|fix": (
        "P023's `protocol_freeze.md` prints `sufficiency_marker_turn_share: 0.0464`, `inspection_call_share: 0.197` "
        "and `T123_modality_rate_after_failure_observation: 0.1782`; the kept wave-4 census generation prints "
        "0.0444, 0.1803 and 0.1535, and those last values are what the designs module carries, because "
        "`refresh_wave_premises.py` (EXP-0163) refreshed it. Nothing was wrong with the measurements - the freeze is a "
        "dated record of the census as it stood when the designs were frozen, and `freeze_wave.py` deliberately refuses "
        "to overwrite a freeze whose topic already has results, because rewriting a pre-registration to match a later "
        "re-run is exactly what pre-registration forbids. What was wrong was the checker: it scored a dated document "
        "against only the current generation and so reported honest history as an invented number. A freeze is now "
        "scored against the retired generations of the runs the package cites (JSON records, newest six per run), and "
        "every other page keeps the strict rule. The disagreement itself is on this list, with both numbers."),
    "topic_row_verdict_outside_the_estate_vocabulary|fix": (
        "The topic register is what a reader of the programme believes about a topic, and round 2 read all 86 intake "
        "rows against the files behind them. Four things held: every intake topic is present, no row names a package "
        "that does not exist, every row whose status names experiments has at least one of them among that package's "
        "kept artefacts, and no stopped row is without a written reason. Two did not. A packaged row could carry "
        "`H2:None` - indistinguishable between \"this hypothesis produced no verdict\" and \"the builder dropped one\" "
        "- and T108's row carried `H2:see ci; the two rates and their interval carry the claim`, because that is the "
        "string the design writes into its own `verdict` field, which reads correctly beside an interval in the "
        "artefact and not at all once flattened into a registry cell. `wave_package.status_word()` now writes "
        "`verdict_not_recorded` for the first and `non_vocabulary_verdict_word_see_ci_...` for the second, keeping the "
        "words the artefact used, and an unlabelled hypothesis is named `unlabelled_row` rather than printing as an "
        "empty key."),
    "cross_package_figure_misattributed|fix": (
        "P003's related-work paragraph says its sister study \"had to retract an independence assumption "
        "(prompt-grouped splits still shared 63.7-88.1% of their catalogues with training)\". Two defects in one "
        "sentence, found by following the figures to their records. It states the wrong quantity: EXP-0017b measures "
        "the share of **test rows** that sit in a catalogue which also appears among the development rows (OSS 0.8092, "
        "Qwen3 0.8805, Kimi-K2 0.6369), not a share of catalogues. And it names no run, so the numbers were "
        "unverifiable from anything P003 ships - which is why the provenance check reported them as unsupported, the "
        "one finding of this round that was not a checker defect. P001's own D13 text attributed the same three "
        "percentages to EXP-0018, which measured the straddling catalogues (887/498/837) but not the row shares: "
        "enumerating every pairwise ratio in EXP-0018's record produces none of the three figures. Both generators are "
        "corrected - P003's `write_paper.py` now states the quantity and cites `(P001, EXP-0017b)`, and "
        "`record_d13_d14_docs.py` attributes the shares to EXP-0017b in the deviation text, the A11a reviewer row and "
        "claim C13 - and the cited record is mirrored into P003 by the evidence rule, so a reader of either package can "
        "open the number rather than take it on trust."),
    "figures_never_redrawn_by_the_estate_rebuild|fix": (
        "The estate-wide rebuild that the two-pass determinism check runs re-assembles documents, tables and evidence "
        "folders, and re-runs the figure *plan* - but no step ever re-rendered a figure, so a PDF was drawn once and "
        "thereafter only copied. That is the same shape of defect as a stale document, and it was worth asking about "
        "directly because this round's design re-pass retired artefact generations: a package could ship a plot of a "
        "run the register no longer keeps. Two things say the figures were not mis-drawn, and neither is a reason to "
        "leave the hole: the re-pass report proved that across waves 1-12 no coefficient, standard error, count or "
        "coverage moved (only the words beside them), and a mtime comparison of every package's newest figure against "
        "the newest artefact it cites found only the five hand packages behind - and there the newer files are this "
        "round's own audit outputs, which no figure reads. So the fix is structural rather than corrective: "
        "`_reassemble_all_waves.py` now renders each package's figures from the artefacts the register keeps before "
        "assembling anything (blocked packages skipped, failures reported per package), which means the two-pass check "
        "now proves figure determinism too instead of leaving the plots outside the rebuild."),
    "gated_package_could_be_read_but_not_re_derived|fix": (
        "Spec item 16 makes every paper reproduce on its own, and the estate checks a `reproduce.sh` exists, resolves "
        "an interpreter and runs current generators. It had not checked the other half - whether the files a script "
        "reads are on disk, and whether a package with no script has one it needs. The first check found no real "
        "defect and two faults of my own: 55 \"missing paths\" were an optional interpreter candidate "
        "(`/d/Environment/anaconda3/python.exe`, which `reproduce.sh` probes before use) and `figures/`/`tables/`, "
        "which those scripts test relative to the package rather than the root; with both handled, all 58 scripts "
        "reference only files that exist. The second found a real one: the twelve premise-gated packages ship "
        "`BLOCKED.md`, a register, a frozen protocol and - since EXP-0231 - the evidence folders, but no "
        "`reproduce.sh`, because a blocked design owes no manuscript and none was written for it. So the measurement "
        "that stopped each design (P048 cites three: the wave-8 premise census, the turn feature frame, the E-step "
        "battery) could be read and not re-derived, which is the same half-finished claim in a different place. "
        "`write_blocked_reproduce.py` (EXP-0233) now writes one per gated package: the interpreter probe copied "
        "verbatim from a generated package's own script rather than duplicated, one line per run that package's "
        "register names, then the audit every package passes; idempotent, and a step of the closing chain."),
    "generated_document_chain_coverage_was_package_only|fix": (
        "`spec_completion_audit` asks, for every document that declares \"Generated by `X.py`\", whether some chain "
        "re-runs X - and it only ever looked at `papers/*/reproduce.sh`. The programme's own `docs/` and "
        "`00_program_registry/` were outside the question, which mattered because this round writes its reports there: "
        "the estate's closing chain is what keeps `ROUND2_PROBLEM_LIST.md`, `ROUND2_CLUSTER_UNITS.md`, "
        "`PROGRAM_STATUS.md` and the topic table current, and nothing checked that it does. The check now also walks "
        "the estate-level drivers (`_round2_final_chain.py`, `_reassemble_all_waves.py`, `_estate_two_pass.py`, "
        "`round2_run_all.py`) and reads their steps and one level of what those scripts run - 178 scripts in all - and "
        "reports 0 live programme documents whose generator no chain executes. Two programme documents do name a "
        "generator no chain runs, and both are dated records of a single past run "
        "(`funnel_correction_agentnet_20260920.md`, `literature_abstract_recovery_20260920.md`); they are listed under "
        "their own heading rather than called stale, because the defect this looks for is a *live* report drifting "
        "away from its rebuild, and a closed statement about a date is not one. Two false leads were fixed on the way, "
        "both found by controls rather than by reasoning: the check first called its own problem list stale because "
        "`round2_run_all.py` runs it as a bare filename while the document names it by path (a chain entry is now "
        "resolved to a file before it is compared - eight file names are duplicated across the estate, so a name is "
        "not an identity), and the narrowed rule was then shown still to fire, by writing a temporary document that "
        "declares a generator no chain runs, seeing it reported, seeing a dated one separated from a live one, and "
        "seeing a chained generator not reported at all."),
    "reporting_layer_arithmetic_not_readable_from_a_record|fix": (
        "P002's paper prints `B2-B1 = 4.593 bits/trajectory (0.3091 bits/turn x 14.86 turns/traj)`, and neither 14.86 "
        "nor 4.593 is anywhere in the package's records as a value: the main result file states "
        "`turns: 3566324, trajectories: 240000` beside `gains_first_minus: {zero_order: {mean: 0.3091}}`, and the "
        "reporting layer divides two of those and multiplies the third - deviation D27 says so in words. A reader of "
        "the page cannot do that arithmetic, and the checker could not either, so twelve of P002's figures were "
        "reported as invented when they are in fact computed from counts shipped in the same block. `round2_lib."
        "sibling_ops()` now reads those readings off the record: a ratio between two *named counts* in one block (or a "
        "ratio the block states itself, `mean_turns_per_trajectory`), that ratio applied to a *named statistic* of the "
        "same block, and a difference between two named statistics of comparable size. Two failures of the obvious "
        "generalisation were measured and rejected rather than papered over: products of any two pool values accepted "
        "95 % of unrelated figures, and propagating each candidate's own rounding error - mathematically correct, since "
        "a two-decimal statistic times a ratio of fifteen is only good to ±0.08 - accepted 53 %, because no band that "
        "wide leaves a check with any power. Figures are therefore matched at the precision the prose prints, and one "
        "P002 figure stays listed on that basis: the pilot's 1.367, where 0.0916 x 14.918 = 1.3663. Estate-wide the "
        "rule costs about five percentage points of specificity (87-94 % of unrelated figures still refused) and "
        "removes twelve false findings."),
    "prose_figure_signed_value_quoted_unsigned|fix": (
        "P004's paper reports `prose_restricted -0.0499`, and the number extractor hands the checker 0.0499: prose "
        "carries the sign in the words, and `round2_lib.NUM` captures digits only. The artefact stores the negative, so "
        "the figure looked invented. `support()` now tries the opposite sign after every other rule has failed and "
        "labels the answer `sign_carried_by_the_words`, which is what a reader of the sentence actually knows."),
    "unsupported_prose_number|class_fix": (
        "Two causes were closed at source rather than by editing prose: a package that quoted a figure living only "
        "in prose got it as a shipped, self-checking table (P001's census shares, EXP-0226), and a figure that could "
        "not be reproduced from disk was withdrawn with the measurement that replaced it (D61's 7.1 %). The "
        "support matcher also learned the two legitimate derivations a reader performs on a table - a share of a "
        "total and a difference within one row - restricted to a single row's own cells so that a match cannot be "
        "manufactured across a dump. P005's last unsourced figure (15,789,996 rows) was neither: it is the total of "
        "the `exact_rows_from_footers` column of the package's own release inventory, summed release by release in "
        "the sentence before it. The detector now accepts a column's total over its own rows as support only when "
        "the sentence names that column, and says which column and how many rows it added - and it reads numbers "
        "inside a cell that is not itself a number, so P005's `inputs` JSON is checked rather than skipped."),
    "unsupported_table_cell|class_fix": (
        "The remaining cases were row-level data dumps scored as statistics; the check is scoped to "
        "`tables/table*.csv` and lets a table carry a number derived from its own cells."),
    "config_not_separable_on_disk|class_triage": (
        "Not a data defect: the detector could not attribute a config to files. code-act separates its configs by "
        "file prefix inside one folder, hermes keeps its unnamed default config's two shards loose while two other "
        "configs get folders, and `hf download` leaves a `.cache/` mirror that made every config look ambiguous. "
        "`round2_corpus_remeasurement.config_files()` now resolves folder, prefix, then unclaimed remainder, and the "
        "32 dataset-configs re-measured against the manifests come back with 0 findings - the manifests' file counts, "
        "row counts and columns are exactly what the disks hold."),
    "cited_table_not_in_package|class_fix": (
        "Two detector bugs, both real mis-reads of a valid citation: a claims cell may hold two citations "
        "(`x.md; results_processed/`), which is now split before resolving, and a citation may name a directory, "
        "which is a folder a reader can open rather than a missing file. 390 claim rows across 58 packages now "
        "resolve, with 0 direction contradictions against the shipped verdict."),
    "file_count_differs|class_triage": (
        "Superseded by the config-scope fix above: the counts differed because a whole-release glob attributed every "
        "file to every config."),
    "row_count_differs|class_triage": (
        "Same cause; per-config file sets re-measured, 0 findings."),
    # ---- coverage the round itself noticed -----------------------------------------------------
    "round2_finalize_models_over_demanded|fix": (
        "The gate this round added to make four-way verdicts provable turned out to demote rows it should have "
        "left alone, and the only way to find that was to read the artefacts back after the change. Two defects. "
        "(1) `finalize_models()` computed the Holm-corrected p per hypothesis and wrote it onto *every* row carrying "
        "that label, so a descriptive share with no test of its own inherited a permutation p belonging to its "
        "sibling; the correction now follows only the row whose own test supplied the family's smallest p. "
        "(2) The denominator guard looked for the three literal keys `n`, `clusters`, `rows`, and so demoted rows "
        "that state their unit as `conversations: 4000` / `turns: 14582`. Measured across every kept wave "
        "artefact: 8 rows carried `not_estimable_denominator_not_recorded`, 5 of them (T184's H1/H2 on "
        "`conversations: 4000` / `turns: 14582`, T189's H2 on `transitions: 7717`, T161's H3 on "
        "`rows_in_random_arm: 22184`) do record a denominator and were re-promoted to their substantive verdicts - "
        "T184 H1 now reads `opposite` and H2 `supported`, each with `p_holm` derived from its own permutation p - "
        "while the 2 that remain (T115's H2 `composite_minus_length_only_auroc` rows, EXP-0139) state no count of "
        "any kind, so their demotion stands and is honest. Feature counts (`n_tokens`, `n_chars`) are deliberately "
        "not accepted as denominators, because that would let the guard pass on exactly the rows it exists to "
        "catch."),
    "four_way_verdict_classes_round_two_left|fix": (
        "Three smaller method defects, each found by a detector and each fixed in the shared code rather than in "
        "the affected file. (a) `verdict_follows_a_non_default_rule` was an instruction to a human ('read the design "
        "sentence'), which the estate does not allow: the `specificity` rule is now re-applied from the two arm "
        "values the row itself carries, and a row whose own rule is non-inferential (`descriptive`, `specificity`, "
        "`coverage_only`, `enumeration`) can no longer print a four-way word at all - those rows now read "
        "`measured_descriptively_rule_declared_non_inferential`. (b) One row printed `supported` with a confidence "
        "interval covering zero ([-0.0022, 0.0165]); an effect claim cannot survive that, whatever its rule is "
        "named, so `finalize_models()` now rewrites it to `null` and leaves the side in `verdict_direction`. "
        "(c) 27 rows in wave 1 carried no direction because no frozen hypothesis covers them - they are control and "
        "per-stratum terms - and the artefact said nothing; they now state "
        "`no_frozen_prediction_for_this_row`, which is a recorded fact rather than an empty cell a reader has to "
        "interpret. Separately, 67 blank statistical cells in 19 shipped tables became `not_recorded`, because a "
        "reviewer holding `table3_main_models.csv` cannot otherwise tell 'this bootstrap row has no analytic "
        "standard error' from 'the number went missing'."),
    "topic_row_with_no_evidence_columns|fix": (
        "24 of the 123 topic rows carried none of the four evidence columns a reader judges a topic by - 13 wave-3 "
        "folds, 8 demotions and 3 kills decided by hand on 2026-09-18, before the machine collision search "
        "(EXP-0038) and the feasibility census (EXP-0032) existed, and outside the intake rows that "
        "`record_intake_dispositions.py` covers later. EXP-0230 reconstructed each row from records that already "
        "exist: the topic's own record in each screen artefact, the graded-corpus rows whose `collision_target` "
        "names it, the host topic's evidence where the row folds into one, and the citations its own "
        "`blocking_issue` quotes looked up against 4,385 harvested literature identifiers. 17 rows now carry "
        "measured provenance; 7 (T010, T011, T022, T028, T030, T033, T035) state in the table itself that no "
        "machine record names them - the first round read those by hand, and the table now says so instead of "
        "leaving the reader to discover an empty cell."),
    "package_document_with_two_writers|fix": (
        "Found the way most of this round's method defects were found: a completion-audit row went red on its own. "
        "`E_COVERAGE.md` is emitted by `package_factory/wave_package.py` for every package the factory assembles, and "
        "it is also written by the programme-level `export_e_coverage.py` - whose package list was "
        "`papers/P0*`, i.e. all 70. The two generators do not agree on what the steps are (the factory names E06 "
        "sensitivity analysis and E07 pilot; the programme script names E06 hyperparameter sensitivity and E07 "
        "seeds), so whichever ran last decided what a package claims, and a rebuild of the waves silently flipped "
        "65 packages' statements back to a mapping their own `reproduce.sh` never regenerates. The same run printed "
        "nine OPEN steps into each of the ten blocked packages, inventing an experiment debt for designs a "
        "pre-registered premise gate retired before any data was read. Ownership is now read from the package's own "
        "files rather than from a list that drifts: a package whose `reproduce.sh` calls the factory, or that ships "
        "`BLOCKED.md`, is not this script's to write, which leaves exactly the five hand-built packages it was "
        "written for. The one file the probe clobbered during this round (`P070`) was restored by re-assembling its "
        "wave, and the generator is now a step in the closing chain."),
    "e_coverage_step_attributed_to_a_row_that_does_not_carry_it|fix": (
        "The other half of the same finding, and the reason the scope rule matters for evidence rather than for "
        "tidiness. P004's `E_COVERAGE.md` claimed E06 on `EXP-0043 ~ /sensitivity/`, and the completion audit - which "
        "re-opens the cited artefact instead of trusting the claim - read the register row back and found no "
        "sensitivity in it, turning the step OPEN. The statement was stale, not the experiment: P004's criterion "
        "sensitivity run is EXP-0044 (`stage=E6_criterion_sensitivity_DONE`), and the older statement had attributed "
        "the match to the row above it because the register had been corrected since the file was written. "
        "Re-running the generator re-attributes E06 and E11 to EXP-0044 and reports 0 OPEN steps for all five "
        "packages; because it is now a chain step that runs after the register export, a later register correction "
        "cannot leave an uncheckable claim behind."),
    "estate_rebuild_covered_only_waves_1_to_7|fix": (
        "`_reassemble_all_waves.py` - the driver the estate two-pass determinism check runs - listed its waves by "
        "hand and the list stopped at wave 7, so waves 8-12 (25 packages) had been rebuilt and audited by explicit "
        "commands but never by the estate-wide check that is supposed to prove the rebuild. The list is now derived "
        "from `02_shared_code/package_factory/topic_designs_wave*.py`, which returns 12 modules, so a future wave "
        "cannot be skipped by forgetting to edit a constant."),
    "round2_design_repass_proof|result": (
        "The second pass re-ran every wave's frozen design step, then its recorder, then its assembly: 33 command "
        "steps, all exit code 0, and 57 artefact families compared against the generation they replaced. 17 families "
        "came back with zero fields changed. Across the rest the only differences are the words beside the numbers: "
        "`verdict_direction` newly attached (39 families), `verdict`/`note` relabelled to `not_estimable_*` (8 "
        "families), and non-finite values written as null. No coefficient, standard error, count or coverage moved "
        "anywhere in waves 1-12; the fields the comparator counts as estimates that did change are 8 families' "
        "`p_holm`, which the freeze declared but the artefact never carried and which `finalize_models()` derives "
        "from that run's own p_raw values, and wave 1's three NaN intervals becoming null. The per-family record is "
        "`results_raw/ROUND2_DESIGN_RERUN_REPORT.json`, and the retired generations carry the same statement in "
        "`SUPERSEDED_ARTIFACTS.json`."),
    "interval_audit_read_fewer_rows_than_its_sibling|fix": (
        "The same self-verification failure as the Holm case, found by asking what each checker actually reaches. "
        "`round2_interval_audit.py` selected rows with `verdict` plus `beta`/`mean_difference` and read intervals "
        "from `ci_lo`/`ci_hi`/`ci`, while its sibling `round2_statistical_consistency.py` follows the estate's "
        "alias lists - so of the 403 verdict rows the kept artefacts carry, it tested 134, and its p-aliases "
        "missed `p_lr` and `p_exact`. It now borrows the sibling's `quantity_of` and `interval_of` and the shared "
        "`wave_lib.P_KEYS`, which is the point: two checkers reading the same rows must read them the same way or "
        "one silently under-covers while both report green. That unification surfaced a row - `EXP-0125` `H2` - "
        "whose `ci_clustered` [-0.1879, -0.1511] does not contain its `beta` -0.7825: the interval belongs to the "
        "row's `gap` (-0.1686), which it does contain, and the row states no `ci_of` to say so. Reporting that as "
        "an arithmetic violation would have been wrong, and the tempting repair - pair the interval with whichever "
        "value it contains - is circular, since it always selects the value that passes. Both checkers now assert "
        "centring only when the pairing is canonical (`ci_lo`/`ci_hi`) or the row names the quantity, and count the "
        "rest: one row estate-wide, named in the report. The real defect that finding points at is in the "
        "artefact's own wording - a shipped row whose interval names no subject, and a verdict of \"see ci\" "
        "instead of a machine-readable pairing - which is recorded here rather than papered over by a guess."),
    "artefact_field_names_a_unit_its_value_is_not_in|fix": (
        "Found while following P002's bits-per-trajectory chain to its source, and independent of the rounding "
        "issue: `EXP-0092`'s record block `rq2_frozen_criterion` carries "
        "`b2_minus_b1_bits_per_trajectory: 0.2041` and `b2_minus_b4_bits_per_trajectory: 0.1087` beside "
        "`floors: {b2_minus_b1: 5.0, b2_minus_b4: 2.0}` - but 0.2041 and 0.1087 are the ladder's **per-turn** means "
        "(`gains_first_minus.*.mean`, identical values), so the artefact as written invites a reader to compare a "
        "per-turn gain with a per-trajectory floor. On this corpus 116581 turns over 20524 trajectories is 5.68 "
        "turns per trajectory, so the like-for-like figures are 1.159 and 0.617 bits per trajectory against those "
        "same floors - the conclusion (the magnitude conjunct fails on the second corpus, while the CI conjunct "
        "already failed) does not move, and no shipped document quotes these keys, so nothing published was wrong. "
        "The record was still wrong about itself. `isp_stage_codex_agenttrove.py` now writes both units with names "
        "that say which is which, adds the ladder's `turns_per_trajectory` and a "
        "`floors_are_bits_per_trajectory: true`, and `isp_stage_main_p002.py` - the analyser behind P002's main and "
        "second-corpus ladders, and the pilot's block by extension - measures `mean_bits_per_trajectory` once from "
        "the unrounded difference and the exact ratio, with a `units_note` saying which numbers are per turn. The "
        "conversion therefore lives in the measurement that produced it, not in whichever document quotes it."),
    "published_number_computed_from_rounded_inputs|fix": (
        "A new detector, because two defects of this shape reached print and nothing looked for the shape. "
        "`round2_derivation_precision.py` reads the estate's own writers - every package's `scripts/` and the six "
        "programme folders that generate package content, 297 files - as syntax trees with string literals blanked "
        "(its first run reported 9 chains, 1 of them prose that merely contained the word `round(`, which the "
        "stripping removed), and reports an assignment that publishes a `round()` of values that were themselves "
        "rounded. Eight on the first run, seven now that the recorder is fixed, in three groups. The substantive one "
        "is P002's bits-per-trajectory conversion, written three times over: `register_pilot.py` (the survivorship "
        "gate, source of the 1.367 above), `build_package.py` lines 120-121 (so the *shipped* package documents, not "
        "just the pilot, carry the same chain) and `record_exp0092_p002.py` line 43 - all of them `round(gain_bits_"
        "per_turn * round(turns / trajectories, 2), 3)`, where the 2-decimal turns-per-trajectory exists in no "
        "record. The recorder now reads the measured `mean_bits_per_trajectory` and keeps the unrounded ratio only "
        "as the multiplier its table names, falling back to `mean * tpt_raw` for a record written before the field; "
        "and both package writers now take the scale factor unrounded as well (`register_pilot.py`, "
        "`build_package.py`), which moved the published pilot contrast from 1.367 to **1.366 bits/trajectory** and "
        "left the 4.449 against its 5-bit floor unchanged - both remain below their frozen thresholds, so no gate "
        "decision or verdict moved, and the register note re-ran from the same code path. The second group is P001's "
        "E08 documentation writers, three sites publishing `round(src_oof - her[...], 3)`: a "
        "difference of two 4-decimal AUROC figures, where rounding propagates at the same order as the printed digit, "
        "so the figure is a rounding of roundings even though no unit conversion is involved. They are kept: each "
        "sentence prints both operands, so a reader can redo the subtraction from the numbers the package shows, "
        "which is the estate's own `derived(...)` doctrine rather than a conversion through a value no record holds. "
        "The third is a single "
        "audit-share mean, depth 1, reported rather than flagged because its inputs are integer counts."),
    "pilot_reported_bits_per_trajectory_from_two_roundings|fix": (
        "P002's second unsupported prose figure was not a citation gap either: `pilot_report.md` and the register "
        "note quote **1.367 bits/trajectory** for the first-order-vs-B4 contrast against a frozen 2-bit threshold, "
        "and no number in the estate's records is 1.367. The report's own script computes it as "
        "`round(0.0916 * round(298359/20000, 2), 3)` - the record's 4-decimal per-turn delta times a trajectory "
        "length it rounds to 2 decimals *inside the report script*, a value the record never carries (it stores "
        "14.918). Two roundings then a third produced a published survivorship-gate number that a reader cannot "
        "reproduce from the file it comes from. `isp_stage_coder.py` now measures the per-trajectory products "
        "itself at full precision (`delta_first_minus_zero_bits_per_trajectory`, "
        "`delta_first_minus_position_only_bits_per_trajectory`, plus the length used and a note saying why the "
        "rounded pair does not reproduce them), and `register_pilot.py` now multiplies by that scale factor "
        "unrounded; the pilot was re-run (309 s) and the only published figure that moved is the contrast itself, "
        "1.367 -> 1.366, still below the frozen 2-bit gate. This matters more than the 88.1 case: there a majority "
        "was quoted a tenth of a point high, "
        "here the number decides whether a design survives its gate, and a gate decision has to be readable from "
        "one artefact rather than from an arithmetic path that exists only in a report writer."),
    "catalogue_overlap_share_was_double_rounded|fix": (
        "A published number was wrong by a tenth of a point, in ten places, and the provenance check found it by "
        "refusing the match. The catalogue-overlap share quoted across P001 (`limitations.md` L10, `deviations.md`, "
        "`protocol_freeze.md`, `reviewer_attack.md` A11/A11a, `final_audit.md`, `appendix.md`, `paper.md` twice, the "
        "claims matrix and the register note) and in P003's §1 read **63.7-88.1%**. `EXP-0018`'s recurrence record "
        "counts 3648/4508, 3941/4476 and 2786/4374 test rows whose exact candidate catalogue also appears among the "
        "development rows: 80.92%, 88.05% and 63.69%, so to one decimal 80.9 / **88.0** / 63.7. The 88.1 came from "
        "reading the record's own `share` field, which is already rounded to 0.8805, and rounding that a second time. "
        "`papers/P001_.../scripts/catalogue_shares.py` now computes the triple, the range and the exact ratios from "
        "the two integer columns, `record_d13_d14_docs.py` rewrites every stale spelling it finds in the package's "
        "documents, P003's sentence cites the run that measured it (EXP-0018, not the EXP-0017b filename it borrowed) "
        "and states the ratios, and the register note and the two scripts whose docstrings quoted the figure carry "
        "the corrected range. Nothing here rests on the difference: the claim is that a large majority of test rows "
        "share a catalogue with development, and 88.0 supports it exactly as 88.1 did. What the correction buys is "
        "that the quoted number is the measured one, and that no future document has to be typed again."),
    "run_declares_only_a_shared_overwritten_file|class_triage": (
        "Investigated and deliberately reported as shape, not as a defect. Nine output paths are named by more than "
        "one register row - `topic_registry.csv` by seven recorder rows, plus `package_audit.json`, "
        "`literature_matrix.csv`, `literature_graded.csv`, `literature_background.md`, `link_availability.md`, "
        "`funnel_correction_agentnet_20260920.md`, `literature_abstracts_v3.csv` and `routing_sample_identity.json`. "
        "Those are programme documents several runs legitimately update in place, and for a maintenance run its "
        "effect on the shared file *is* its output: `EXP-0070` writes two packages' literature matrices, which are "
        "shipped in those packages and cited by their E-coverage document, so a reader can open what it did. The "
        "case that is a defect is the one the supersession ledger already carries - `analyze_routing_failure.py` "
        "names its table after its own experiment id, so EXP-0006's 3-seed ladder and EXP-0006b's 5-seed ladder both "
        "declare one fixed path and the later run overwrote the earlier's bytes; that pair is retired as \"kept, not "
        "citable\" and excluded here. `round2_run_reality` now prints the shared names and the one row that declares "
        "nothing else, so the shape is visible; a run whose evidence a package cannot open is caught by "
        "`missing_copies` and `cited_artefact_not_in_package`, where the reader's inability is the finding."),
    "cluster_ci_without_a_cluster_count|fix": (
        "Four shipped rows state a `cluster_bootstrap_percentile` interval and a `bootstrap_two_sided_tail` p while "
        "their `clusters` field reads null, so on the page a cluster bootstrap and a row bootstrap are "
        "indistinguishable - and two of the four carry an inferential verdict (`supported`, `opposite`). The "
        "measurement itself was never in doubt: `wave_lib.cluster_boot_ci_and_p` returns the number of groups it "
        "resampled, and the same design prints that number on its neighbouring rows. What failed is the row builder: "
        "`exp_wave12_designs.py` copied `ci`, `p`, `ci_kind`, `p_kind` and `draws_used` out of the helper's result "
        "at four places and left `clusters` behind, so the recorder wrote the template's null. Those four sites now "
        "carry `clusters=b.get(\"clusters\")`, and the check reports the class whenever a row's own `ci_kind` names a "
        "resampling it cannot count. Two register labels moved with the same reading: T189's marker frame groups on "
        "`conversation_index` - one value per conversation, which is why the design counts conversations as its "
        "nunique - yet declared `cluster_unit=\"conversation_id\"`, and the experiment register copied that word into "
        "`config` for EXP-0216/0217/0218; the artefact now names the column it actually groups by and carries a note "
        "saying why that is the conversation. The corrected values appear when waves 11-12 are re-run through "
        "`_round2_rerun_designs.py --waves 11 12 --apply`, which diffs every new artefact against the kept one, so "
        "the only permitted movement is the four counts that were missing."),
    "p_holm_below_the_declared_holm_family|fix": (
        "Closed as a false positive of this round's own checker, and the data was left alone because nothing in it "
        "was wrong. `EXP-0213` `models[1]` prints `p_holm` 0.9024, equal to its raw p, and the re-derivation said "
        "1.0 - but only because the checker assembled the family from every row labelled H1/H2/H3. The design "
        "(`exp_wave11_designs.py:478`) calls `holm_and_verdict([h1, h2], {'H2': 1.0})`: H1 declares "
        "`verdict_rule=descriptive`, H3 declares `verdict_rule=specificity`, and `wave_lib.finalize_models` skips "
        "exactly those rules before it touches a row, so the frozen inferential family is {H2} - a one-test family "
        "whose correction is its own p. The checker now applies the same exclusion and counts how many rows it "
        "skipped (30 across the estate), so the reading is stated rather than assumed; a printed correction below "
        "the family that the design actually declared still fires."),
    "table_has_no_numeric_column|fix": (
        "Found by widening a checker and then corrected twice, once in each direction. Widening "
        "`round2_number_provenance.printed_tables` to every shipped summary CSV surfaced 129 tables that print a "
        "four-way verdict or a headline with no number in them - and `round2_problem_list.py` had no branch for the "
        "`degenerate_tables` key, so all 129 were being dropped on the floor: the round-2 lesson (the estate's "
        "verification under-reads) applying to the problem list itself. Two of the three groups were the checker's "
        "fault, not the packages': the numeric-column test matched only cells *starting* with a digit, so a row "
        "carrying `value = \"{'beta': -0.7825, 'ci_clustered': [-0.1879, -0.1511]}\"` read as numberless, and a row "
        "whose cells say `NOT MEASURABLE: the frame carries no config column` or `not_recorded` is the estate "
        "recording a negative result, which is required behaviour and must not be a finding. What remained was one "
        "shape in about 22 packages: `wave_package.py`'s robustness branch emitted the single word "
        "`holm_over_declared_family` whenever an artefact's `holm` block was empty - and because that one-element "
        "list is truthy, the branch below it that reads the corrected coefficients out of the model rows could "
        "never run. The rebuilder now falls through to those numbers and, where a design really froze no robustness "
        "device, prints an explicit not_recorded disclosure instead of a label."),
    "catalogue_recurrence_record_had_no_producer|fix": (
        "`results_processed/EXP0017b_catalog_split_recurrence.json` was named for a run the register has no row for "
        "while the row that claimed to produce it (EXP-0018) names a script that writes a different file. Round 2 "
        "gave it a producer: `02_shared_code/trajectory_parser/measure_catalog_split_recurrence.py` re-measures the "
        "three configs from the published frames, refuses to report unless each uuid digest still matches the "
        "manifest, reproduces every count in the old record (3648/4508, 3941/4476, 2786/4374; 887/498/837 "
        "catalogues; 0 prompts) and cross-checks them against EXP-0018's independent artefact, which agrees. It "
        "stores the share unrounded - the rounded 0.8805 in the old record is what let a document turn it into "
        "88.1% - and drops the key `test_rows_in_catalogs_shared_with_dev`, which held a proportion under a name "
        "asserting a row count. EXP-0018's outputs cell now names only what its own script writes."),
    "holm_re_derivation_read_only_the_key_p|fix": (
        "The estate's own verification was again the weak link. `round2_statistical_consistency.py` re-derived Holm "
        "over the hypotheses an artefact declares but read the raw p from the key `p` alone, and most designs state "
        "it as `p_raw`, `p_boot` or `p_perm`, so the block's guard (`all rows have p`) silently skipped the majority "
        "of families and its zero findings described a fraction of the corrections. It now takes the family the way "
        "`wave_lib.finalize_models` declares it - one entry per hypothesis label, that hypothesis's smallest p, read "
        "from any of the six keys a design states a p under - and re-derives with the checker's own step-down rather "
        "than the factory's function, so a mistake in the factory cannot make the check agree with itself. On the "
        "kept wave artefacts the sweep now reaches 44 families and 100 printed corrections (4 printed *more* "
        "conservatively than their declared family needs, 9 on a hypothesis that states no raw p at all, 1 below it) "
        "and prints those counts beside its findings. The one under-corrected row is `EXP-0213` "
        "`models[1]`: p_holm 0.9024 where the artefact's own two-member family implies 1.0. Both rows there carry a "
        "non-inferential verdict, so no support claim rests on the number, but it remains open as "
        "`p_holm_below_the_declared_holm_family` until the design is re-run with the whole family in place."),
    "registry_row_carries_no_window_kind|class_fix": (
        "Detector-only class, opened by this round's timeline check and closed by the step that precedes it in the "
        "closing chain: `round2_register_windows.py --apply` labels every register row's time claim, so a row that "
        "carries no label is one added since the labeler last ran, which is exactly what the finding is for."),
    "registered_window_not_corroborated_by_any_output|class_fix": (
        "Twelve rows stated a window that none of their own generations falls inside - `EXP-0011` claimed "
        "18:56:00-18:57:00 for a run whose registered output is stamped 19:04:25, and `EXP-0099` claimed a "
        "2026-09-21 morning for a row whose only surviving generation is from 2026-09-26. "
        "`round2_register_windows.py` re-anchors such a row to the timestamp its own designated artefact prints and "
        "keeps the value it had in `window_was=`, so the register now claims only what an artefact proves; the run "
        "itself was never in doubt, since each of these rows' script, seed, artefact digest and command line pass "
        "the rest of this detector."),
    "registered_instant_not_corroborated_by_any_output|class_fix": (
        "The companion case for rows that state one clock reading rather than a window: the reading must match a "
        "generation of the row's own within two minutes. 111 rows pass this way - they are the recorders that "
        "registered a run just after it finished and stored one reading twice, which is a real instant and not a "
        "duration, and `window_kind=instant_recorded` now says so in the row."),
    "register_time_columns_stated_more_than_the_artefacts_support|coverage_gap": (
        "Recorded as a limit, not closed. The register carries 231 rows and only 80 of them state a *duration* that "
        "one of their own generations falls inside; 111 state a single clock reading that an artefact agrees with, "
        "25 of those having stated one end only and had the other filled from the generation that matches it; 12 "
        "stated a window nothing supports and were re-anchored to their artefact's stamp; 6 have unstamped outputs "
        "so their window cannot be checked at all; 20 state no time; and 2 are retired console probes. The estate "
        "therefore cannot claim measured run durations for most of its runs - the recorders stored the clock only "
        "when they wrote the row, and no earlier time survives anywhere on disk for those runs. What round 2 did "
        "instead is make each row say which of these it is, so the claim a reader can check is stated rather than "
        "implied, and `round2_run_reality.py` reports the per-class counts beside its findings."),
    "rebuild_determinism_excludes_P001_to_P005|coverage_gap": (
        "Partly closed, rest recorded as a limit rather than hidden. The five pre-wave packages' *evidence* is now "
        "mirrored by `_mirror_pre_wave_runs.py`, which does for them what the factory does for the waves - 39 "
        "byte-for-byte copies of the kept generation of every run their own register declares, nothing renamed or "
        "deleted - so a reader of P001 can open every run P001 cites. What the estate's two-pass determinism check "
        "still does not do is *regenerate* their prose deliverables: P001-P005 are hand-assembled, and their "
        "regeneration path is each package's `reproduce.sh`, which re-runs the analyses themselves rather than only "
        "the document builders. The wave packages, which are generated, are covered by the two-pass check."),
}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    d = json.loads(F.read_text(encoding="utf-8")) if F.is_file() else {}
    added = 0
    for k, why in R.items():
        if d.get(k, {}).get("status") == "fixed" and d.get(k, {}).get("resolution") == why:
            continue
        # a coverage gap is a stated limit, not a fix: it stays open in the list so the round cannot read as
        # more complete than it is
        d[k] = {"status": "open" if k.endswith("|coverage_gap") else "fixed", "resolution": why,
                "at": datetime.datetime.now().isoformat(timespec="seconds")}
        added += 1
    F.write_text(json.dumps(d, indent=1, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    print(f"{added} of {len(R)} resolution(s) (re)written; {F.name} now holds {len(d)} keys")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
