"""One-off patcher: write the round-2 (behaviour-side) literature-audit verdicts into the topic
registry generator. Kept as a script so the registry stays regenerable and never hand-patched."""

import re
import pathlib

P = pathlib.Path(__file__).resolve().parents[0] / "build_topic_registry.py"

VERD = {
 "T005": ("w3_fold_into_T037",
   "lit audit 2026-09-18 (round 2, behaviour side): a cross-context construct-transfer study of "
   "'explicitness' adds no test beyond P001's three-config design, which already re-estimates the "
   "same feature battery per corpus -> folded in as its E09/E10 evidence"),
 "T008": ("w1_repositioned_as_P002",
   "lit audit 2026-09-18 (round 2): ISP-stage-in-agent-trajectory is no longer an open gap, so any "
   "'first at scale' framing is withdrawn; survives ONLY as a measurement study (rule-based stage "
   "markers + first-order Markov null + human-coded subset at kappa>=0.75) and must not claim a new "
   "stage model"),
 "T009": ("w3_fold_into_T008",
   "lit audit 2026-09-18 (round 2): agent query-reformulation taxonomies already exist and edit-based "
   "typing is a known move set -> no standalone gap; becomes the reformulation-marker family inside P002"),
 "T010": ("killed_L4_and_unidentifiable",
   "closed 2026-09-18: (a) lit audit round 2 puts code-vs-natural-language task expression at L3-L4; "
   "(b) the identifying assumption is unfixable here - expression mode is a property of the config, not "
   "randomly assigned, and the data audit measured the two sub-corpora differing on turns (7-11 vs 2-234) "
   "as well as on mode, so no matched comparison recovers a causal contrast"),
 "T011": ("demoted_L3_crowded",
   "lit audit 2026-09-18 (round 2): verbalised-confidence/hedging-as-failure-prediction is crowded, and as "
   "a Type B paper it owes strong neural baselines the project's no-API constraint cannot run; kept only as "
   "a secondary predictor inside P001/P002 feature batteries"),
 "T016": ("w3_fold_into_T037",
   "lit audit 2026-09-18 (round 2): register variation across agent task domains is descriptive while the "
   "outcome labels are unusable (data audit: judgment 0%, result 13.7%); P001 already reports per-domain "
   "robustness -> folded in as its E10 stratum"),
 "T017": ("w3_fold_into_T037",
   "lit audit 2026-09-18 (round 2): config/provenance fingerprinting overlaps distillation-fingerprint work "
   "and needs the T020 de-dup first; P001's leave-one-config-out transfer already measures the same "
   "cross-config stylistic distance -> folded in"),
 "T035": ("demoted_L3_crowded",
   "lit audit 2026-09-18 (round 2): repetition/foraging measures on agent traces are established, and the "
   "32-turn right-censoring measured in the data audit makes the late-stage claim fragile -> not a standalone paper"),
}


def blocks(s: str):
    starts = [m.start() for m in re.finditer(r'dict\(topic_id="T\d{3}"', s)]
    ends = starts[1:] + [s.index("\n]", starts[-1])]
    return list(zip(starts, ends))


def main() -> int:
    src = P.read_text(encoding="utf-8")
    done = []
    for tid, (status, reason) in VERD.items():
        hit = False
        for a, b in blocks(src):
            blk = src[a:b]
            if f'topic_id="{tid}"' not in blk:
                continue
            nb, n1 = re.subn(r'status="[^"]*"', f'status="{status}"', blk, count=1)
            nb, n2 = re.subn(r'blocking_issue="[^"]*"', f'blocking_issue="{reason}"', nb, count=1)
            assert n1 == 1 and n2 == 1, (tid, n1, n2)
            assert '"' not in reason, f"{tid}: reason text must not contain a double quote"
            src = src[:a] + nb + src[b:]
            hit = True
            break
        assert hit, f"block not found for {tid}"
        done.append(tid)
    P.write_text(src, encoding="utf-8")
    print("patched:", ",".join(sorted(done)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
