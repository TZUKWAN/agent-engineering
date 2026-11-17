"""E08 docs 2a: remove sentences duplicated by the interrupted run, and tighten one summary line."""

from __future__ import annotations

import glob
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PAP = ROOT / "papers" / "P001_routing_failure_qpp"
f21 = sorted(glob.glob(str(ROOT / "results_raw" / "EXP0021_cross_pipeline_transfer_*.json")))[-1]
f23 = sorted(glob.glob(str(ROOT / "results_raw" / "EXP0023_hermes_transfer_*.json")))[-1]
E21 = json.loads(Path(f21).read_text(encoding="utf-8"))
E23 = json.loads(Path(f23).read_text(encoding="utf-8"))
a1b, her = E21["arm1b_catalogue_disjoint"], E23["transfer"]
src_oof = round(sum(E21["arm1_external_pipeline"]["auc_source_reference_oof_dev"]) / 5, 4)

pm = PAP / "paper.md"
lines = pm.read_text(encoding="utf-8").split("\n")
for marker in ("E08 replaces that bound", "E08 (EXP-0020..0023) then measured"):
    for i, l in enumerate(lines):
        if l.count(marker) > 1:
            lines[i] = l[:l.index(marker, l.index(marker) + 1)].rstrip()
            print(f"deduplicated {marker!r} on line {i + 1}")
pm.write_text("\n".join(lines), encoding="utf-8")

ra = PAP / "reviewer_attack.md"
t = ra.read_text(encoding="utf-8")
t = t.replace("catalogue composition costs nothing, tool vocabulary costs ~0.12 AUROC (0.694 cross-corpus)",
              f"catalogue composition alone costs nothing detectable ({a1b['n_rows']} disjoint rows at "
              f"{a1b['auc_transfer_disjoint_catalogues']}), while unseen tool vocabulary costs "
              f"{round(src_oof - her['auc_source_dev_to_hermes'], 3)} AUROC "
              f"({her['auc_source_dev_to_hermes']} cross-corpus vs {src_oof} in domain)")
ra.write_text(t, encoding="utf-8")
print("2a done")
