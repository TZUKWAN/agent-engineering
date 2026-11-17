"""Close the markdown table row broken by a CRLF edit, and refresh final_audit.md for D13/D14/E17."""
import pathlib

R = pathlib.Path(__file__).resolve().parents[1]

ra = R / "reviewer_attack.md"
lines = ra.read_text(encoding="utf-8").split("\n")
for i, ln in enumerate(lines):
    if ln.rstrip("\r").endswith("is supplied; none was given.") and ln.rstrip("\r").startswith("| A11 |"):
        lines[i] = ln.rstrip("\r") + " |"
        print("closed A11 table row on line", i + 1)
ra.write_text("\n".join(lines), encoding="utf-8")

f = R / "final_audit.md"
s = f.read_text(encoding="utf-8")
subs = [
 ("| robustness | PASS | EXP-0011 (alternative DV, label noise, subsampling) + EXP-0014/0015 "
  "(alternative DV *definition* via equivalence relabelling) |",
  "| robustness | PASS | EXP-0011 (alternative DV, label noise, subsampling) + EXP-0014/0015 "
  "(alternative DV *definition* via equivalence relabelling) + EXP-0016 (controlled catalog "
  "interventions with a sham control) |"),
 ("| intervention / counterfactual | **FAILED / OPEN** | catalog now persisted losslessly, so E17 is "
  "runnable; not yet done |",
  "| intervention / counterfactual | PASS | EXP-0016: decoy ladder, gold enrichment, **sham** control, "
  "namespace and order controls; the mechanism is now identified by manipulation, not correlation |"),
 ("Multi-seed PASS (seeds 42-46 everywhere", "Multi-seed PASS (seeds 42-46 everywhere"),
 ("CIs PASS (1000-resample\n`prompt_id` cluster bootstrap).",
  "CIs **AMENDED** (D14): re-run with the **catalogue** as resampling unit (EXP-0019) - widths up to "
  "2.955x larger, and 9/9 headline contrasts still exclude zero. The prompt_id-only intervals were too "
  "narrow: GEE showed naive SEs up to 7.33x too small.\n\nEffect sizes PASS (AAUROC, OR per SD, Spearman rho, bits over chance)."),
 ("| clean-environment rerun | **OPEN** |",
  "| catalogue-disjoint held-out check | **IMPOSSIBLE, disclosed** | EXP-0018: one connected component "
  "of the catalogue-prompt graph holds 86-98% of rows, so no disjoint split exists; 63.7-88.1% of test "
  "rows share a catalogue with dev. The held-out AUROC is reported as an upper bound and the "
  "catalogue-grouped CV figure (0.807/0.718/0.790) as the conservative estimate. No second test "
  "evaluation was run. |"),
]
for old, new in subs:
    if old in s:
        s = s.replace(old, new)
    else:
        print("NOTE: final_audit anchor missing ->", old[:60].replace("\n", " "))
s = s.replace(
 "**Not submittable yet.** The empirical core is sound and the H4 hole is closed, but items 1-2 of G18-B",
 "**Not submittable yet, for a changed reason.** E17 and the dependence problem are now closed: the "
 "mechanism is identified by intervention with a sham control, and the inference is clustered on the unit "
 "that actually binds. Two results changed the paper rather than adding to it - H4 came back null, and the "
 "split was found to leak **catalogues** rather than prompts, so the held-out AUROC is now labelled an "
 "upper bound for unseen catalogues. Remaining blockers are items 1-2 of G18-B")
f.write_text(s, encoding="utf-8")
print("final_audit refreshed")
