"""Mark superseded raw artifacts (never deleted) and finish the G18-B inference row."""
import json
import pathlib
import time

R = pathlib.Path(__file__).resolve().parents[1]

f = R / "final_audit.md"
s = f.read_text(encoding="utf-8")
s = s.replace("| statistical inference | PASS | cluster bootstrap ΔAUC, 5 seeds, Holm-corrected ORs, "
              "chance-corrected LLR in bits |",
              "| statistical inference | **AMENDED (D14)** | cluster bootstrap ΔAUC re-run on the "
              "catalogue as resampling unit (EXP-0019); 5 seeds; Holm-corrected ORs; chance-corrected "
              "LLR in bits. Earlier prompt_id-only intervals were too narrow |")
f.write_text(s, encoding="utf-8")

sup = [
 {"file": "results_raw/EXP0014_equivalence_relabel_20260918T194417.json",
  "superseded_by": "results_raw/EXP0014_equivalence_relabel_*.json (latest)",
  "why": "verdict wording averaged AUROC survival across all three rules, which credits the degenerate "
         "liberal rule; EXP-0014 was re-run with survival judged on the conservative rule only"},
 {"file": "results_raw/EXP0016_catalog_intervention_20260918T201036.json",
  "superseded_by": "results_raw/EXP0016_catalog_intervention_20260918T202157.json",
  "why": "harness overwrote the instruction-only n_tokens, so the control arm did not reproduce the "
         "published dev AUROC (0.8238 vs 0.8233), and a zero-variance bootstrap correlation was "
         "written as a bare NaN literal. Numbers in the superseded file are otherwise unchanged"},
 {"file": "results_raw/EXP0013_toucan_routing_dataset_20260918T192345.json",
  "superseded_by": "results_raw/EXP0013_toucan_routing_dataset_20260918T193847.json",
  "why": "built with the builder default --shards-per-config 8, i.e. a different sample (deviation D11); "
         "the published row set was restored and rebuilt under the frozen invocation"},
]
existing = {p["file"] for p in sup}
out = R / "results_raw/SUPERSEDED_ARTIFACTS.json"
prior = json.loads(out.read_text(encoding="utf-8")) if out.exists() else []
merged = {p["file"]: p for p in prior}
for p in sup:
    merged[p["file"]] = p
rows = sorted(merged.values(), key=lambda r: r["file"])
out.write_text(json.dumps({"note": "Failed and superseded runs are kept, never deleted (spec T01.03). "
                                   "Cite only the file named in superseded_by, or the file named in "
                                   "00_program_registry/experiment_registry.csv.",
                            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "artifacts": rows},
                            indent=1), encoding="utf-8")
print("superseded manifest:", len(rows), "entries")
