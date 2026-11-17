"""EXP-0163: regenerate a wave module's PREMISES block from its census artefact, so no premise number is typed.

The wave freezes record their premise census as a `PREMISES` literal - it is the text a reviewer reads to see what
was known before any outcome. That literal was transcribed by hand from the census, which means every rebuild of a
census (wave 4's deduplication, D14) leaves the freeze stating numbers that no longer match the artefact, and the
only defence against that is to stop transcribing. This tool rewrites the block from the artefact by an explicit
key map and refuses on any mapped key the census does not carry, so a renamed measurement surfaces here rather than
silently becoming `null` in a frozen document.

The numbers it writes are the census's own, and the census is a structure-and-prevalence pass: no dependent variable
of any design enters it. A refresh after a rebuild is therefore not a re-reading of outcomes, and the tool prints
which premise values moved so the amendment can be recorded with its reason.

    python 02_shared_code/registry/refresh_wave_premises.py --designs topic_designs_wave4 [--dry-run]
"""
from __future__ import annotations

import argparse
import datetime
import glob
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = next(a for a in (HERE, *HERE.parents) if (a / "00_program_registry").is_dir())
sys.path.insert(0, str(ROOT / "02_shared_code" / "package_factory"))

EXP = "EXP-0163"
NL = chr(10)

# census key -> the name the freeze uses for it. Names are the freeze's, values are the artefact's.
MAP = {
    "G8_hedged_turns_followed_by_inspection": "T123_hedged_turns_followed_by_inspection",
    "plain_turns_followed_by_inspection": "T123_plain_turns_followed_by_inspection",
    "G10_turns_after_error_observation": "T123_turns_after_failure_marked_observation",
    "modality_rate_after_error_observation": "T123_modality_rate_after_failure_observation",
    "G9_discordant_hedge_turns": "T124_discordant_hedge_turns",
    "concordant_hedge_turns": "T124_concordant_hedge_turns",
    "body_only_hedge_turns": "T124_body_only_hedge_turns",
    "G5_contradiction_cell": "T126_trajectories_with_same_tool_content_change",
    "G11_stops_preceded_by_sufficiency_claim": "T127_stops_preceded_by_sufficiency_claim",
    "stops_total": "T127_stops_total",
    "mean_prior_inspections_at_stop": "T127_mean_prior_inspections_at_stop",
    "mean_prior_non_inspections_at_stop": "T127_mean_prior_non_inspections_at_stop",
    "G2_modality_prevalence": "modality_prevalence_whole_turn",
    "modality_prevalence_in_body_only": "modality_prevalence_body_only",
    "modality_prevalence_in_reasoning_block": "modality_prevalence_reasoning_block",
    "sufficiency_marker_turn_share": "sufficiency_marker_turn_share",
    "G3_inspection_action_prevalence": "inspection_call_share",
    "execution_family_call_share": "execution_call_share",
    "write_only_call_share": "write_only_call_share",
    "G7_outcome_label_available": "outcome_label_coverage",
    "trajectories_sampled": "rows_census_actual",
}


def newest_census(pattern: str) -> pathlib.Path:
    fs = sorted(glob.glob(str(ROOT / pattern)), key=lambda f: pathlib.Path(f).stat().st_mtime)
    if not fs:
        raise SystemExit(f"ABORT: no census artefact matches {pattern!r}, so the freeze has nothing to cite")
    return pathlib.Path(fs[-1])


def _lit(v) -> str:
    """A Python literal. `json.dumps(True)` is `true`, which would make the rewritten module unimportable - and the
    same happens one level down, where a gate block carries `"fires": false`. Anything structured therefore goes
    through `repr`, which is a Python literal and keeps the insertion order of the dict it renders.
    """
    if isinstance(v, (bool, dict, list, tuple)):
        return repr(v)
    return json.dumps(v, ensure_ascii=False)


def _blk(d: dict, indent: str) -> str:
    inner = ("," + NL).join(f'{indent}    "{k}": {_lit(v)}' for k, v in d.items())
    return "{" + NL + inner + "," + NL + indent + "}"


def render(new: dict, census: pathlib.Path, blocked_designs) -> str:
    verdict = {"blocked_gates": new["verdict"]["blocked_gates"],
               "blocked_whole_design": list(blocked_designs),
               "claim_limited": new["verdict"]["claim_limited"]}
    who = "02_shared_code/registry/" + pathlib.Path(__file__).name
    L = ["PREMISES = {",
         '    "census": "%s (%s)",' % (new["exp_id"], census.name),
         '    "transcribed_by": "%s (%s); no number in this block is typed by hand",' % (who, EXP),
         '    "measured": ' + _blk(new["measured"], "    ") + ",",
         '    "gates": ' + _blk(new["gates"], "      ") + ",",
         '    "verdict": ' + _blk(verdict, "      ") + ",",
         '    "note": "a fired gate is a result, not an obstacle: it stops exactly what its frozen sentence '
         'scopes",',
         '    "runnable": list(RUNNABLE),',
         '}']
    return NL.join(L)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--designs", default="topic_designs_wave4")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    mod = __import__(a.designs)
    cen = newest_census(getattr(mod, "PREMISE_GLOB", ""))
    art = json.loads(cen.read_text(encoding="utf-8"))
    m = art.get("measured") or {}
    kmap = getattr(mod, "PREMISE_MAP", None) or MAP

    def get(dotted):
        v = m
        for part in dotted.split("."):
            v = v.get(part) if isinstance(v, dict) else None
        return v

    miss = [k for k in kmap if get(k) is None]
    if miss:
        raise SystemExit(f"ABORT: the census {cen.name} no longer carries {miss}; update the key map rather than "
                         f"writing nulls into a frozen document")
    new = {"exp_id": art.get("exp_id") or "EXP-0152",
           "measured": {kmap[k]: get(k) for k in kmap},
           "gates": dict(art.get("gates") or {}),
           "verdict": dict(art.get("verdict") or {})}
    blocked = new["verdict"].get("blocked_whole_design") or []
    bad = [b for b in blocked if not re.fullmatch(r"T\d{3}", str(b))]
    if bad:
        raise SystemExit(f"ABORT: the census names {bad} as a blocked design and those are not topic ids")
    text = render(new, cen, blocked)

    f = ROOT / "02_shared_code" / "package_factory" / (a.designs + ".py")
    src = f.read_text(encoding="utf-8")
    marker = '"runnable": list(RUNNABLE)'
    start = src.index("PREMISES = {")
    r = src.index(marker, start) + len(marker)
    end = r
    skip = set([",", " ", chr(9), chr(10)])            # a trailing comma and the line break before the brace
    while end < len(src) and src[end] in skip:
        end += 1
    closed_at = end
    while end < len(src) and src[end] == "}":
        end += 1
    if end == closed_at:
        raise SystemExit("ABORT: the PREMISES block does not close after its `runnable` entry, so the freeze was "
                         "not rewritten - a hand edit would be worse than no edit")
    old_block = src[start:end]
    old_measured = dict(re.findall(r'"([A-Za-z0-9_]+)":\s*([^,{}\n]+)',
                                   old_block[old_block.index('"measured"'):old_block.index('"gates"')]))
    moved = {}
    for k, v in new["measured"].items():
        was = str(old_measured.get(k, "")).strip()
        if was != _lit(v).strip():
            moved[k] = [was, _lit(v)]
    for k, (o, n) in sorted(moved.items()):
        print(f"  {k}: {o} -> {n}")
    print(f"{len(moved)} premise number(s) moved; census {cen.name}; {len(new['gates'])} gates; "
          f"{len(blocked)} design(s) stopped by a fired gate")
    payload = {"exp_id": EXP, "designs": a.designs, "census": cen.name, "keys_mapped": len(kmap),
               "moved": moved, "new_measured": new["measured"], "gates": new["gates"],
               "verdict": new["verdict"], "at": datetime.datetime.now().isoformat(timespec="seconds"),
               "invocation": " ".join([sys.executable] + sys.argv)}
    stamp = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
    dest = ROOT / "results_raw" / ("EXP0163_premise_transcription_" + stamp + ".json")
    if a.dry_run:
        print("dry run: module untouched")
        return 0
    f.write_text(src[:start] + text + src[end:], encoding="utf-8")
    import py_compile
    py_compile.compile(str(f), doraise=True)
    dest.write_text(json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"rewrote PREMISES in {f.name}; artefact {dest.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
