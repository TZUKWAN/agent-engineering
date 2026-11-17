# P002 pilot report (EXP-0026) — does the frozen rule codex measure anything?

Run 2026-09-18T22:50:21 → 2026-09-18T22:56:47 (386.6 s), seed 42, 20 shards x
1000 rows = **20000 trajectories / 298359 assistant turns**, from
`AlienKevin/SWE-ZERO-12M-trajectories`. Codex frozen in `protocol_freeze.md` section 2 before this script ran.

| frozen criterion | threshold | pilot | verdict |
|---|---|---|---|
| RQ1 single-stage coverage | >= 70% | 95.47% | pass |
| RQ1 uncodable share | <= 15% | 4.53% | pass |
| RQ1 largest stage share | <= 60% | 47.22% (extraction) | pass |
| RQ2 first-order vs zero-order | >= 5 bits/trajectory | 4.449 bits/trajectory (0.2982/turn, CI [0.285, 0.31]) | **borderline, below** |
| RQ2 first-order vs position-only B4 | >= 2 bits/trajectory | 1.367 bits/trajectory (0.0916/turn) | **below** |
| RQ3 censoring sensitivity | report | exploration 49.5% at 5 steps vs 26.5% at 15 = 22.9 pp | severe |

Stage shares: {"extraction": 0.4722, "exploration": 0.2653, "documentation": 0.1191, "verify": 0.0912, "uncodable": 0.0453, "clarification": 0.0053, "system": 0.0011, "end": 0.0005}
Observation outcomes: {"informative": 0.8211, "error-shaped": 0.1772, "empty": 0.0017};
trajectories re-issuing an identical command: 30.0%.
Last observed stage: {"extraction": 0.4113, "documentation": 0.2205, "uncodable": 0.1293, "verify": 0.115, "exploration": 0.1067, "clarification": 0.0114, "system": 0.0049, "end": 0.0008}

## What this decides

1. **The codex is a usable instrument** — 95.5% of turns get exactly one auditable stage label with no model,
   so a rule-based replication of LLM-annotated stage analysis is possible.
2. **The process claim is in danger, and that is the finding.** In a corpus where the template fixes the turn
   format, knowing only the turn *index* predicts the stage almost as well as knowing the previous stage
   (-1.755 vs -1.663 bits/turn). Any "agentic search
   follows a stage process" statement must therefore be tested against a position-only null, not just against
   independence — B4 is the baseline that matters, and it is strong.
3. **Effective N is hundreds, not thousands**: 20000 trajectories come from 317
   instances and 262 repos (~63.1 rollouts each). All
   intervals must cluster on `instance_id`; reporting 20k "independent" sessions would be a statistical-unit
   error of exactly the kind P001 hit with catalogues.
4. **The 15-step cap is a measurement instrument property**, shifting stage shares by up to 22.9 pp. Any
   stage-distribution number is cap-conditional and must be published with the truncation curve.

## Correction kept visible

The first pilot run compared a per-trajectory log-likelihood *sum* against a per-turn *mean*, which made the
position-only baseline appear to win by 14.8 bits. The units bug was found and fixed (all three models now
scored per turn) before any number was written into a document; the corrected figures are above.

## Next (main experiment, still requires the frozen dev/report instance split)

Expand to 240 shards, add the second corpus (AgentTrove, different schema, uncapped turns), run the full
B0–B4 ladder including B4, report the truncation curve, perturb the lexicon, and do the intra-coder retest on
60 turns. The gate for P002 becoming a paper is now explicit: it is publishable as a **measurement-critique**
paper (what rule-based stage coding can and cannot establish under templates, caps and rollout clustering), and
it is *not* publishable as a stage-model discovery paper.
