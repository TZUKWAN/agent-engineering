"""EXP-0090 (P003): correct the frozen instrument where EXP-0089 showed it silently reads nothing, and measure what moves.

EXP-0089's blind second auditor disagreed with the frozen audit on 9 of 96 cells. Six of those were the auditor's
own limits (values nested inside JSON strings, identifiers that are not UUID-shaped, outcome words outside its
keyword list). Three were not: Toucan-1.5M stores its `messages` column as a **JSON string**, and
`canonical_conformance_audit_p003.msgs()` does `list(m or [])` - on a string that yields a list of *characters*, so
every message-derived parser for that corpus returned nothing and the cells were scored `absent` with coverage 0.0
while the roles `assistant|function|system|user` sit in the file. AgentBank's observation text is carried by an
`Observation:` prefix the frozen probe set never hypothesised for that corpus, even though the parser exists in the
module and was applied to SWE-ZERO.

That is the exact failure P003 catalogues in other people's pipelines - a container/format assumption that drops data
without an error - occurring inside this paper's own instrument. It is therefore reported as a correction, not as a
robustness footnote.

What this run does, in the EXP-0030 pattern (D18): the frozen candidate order is kept and the corrected probes are
appended **after** it, so no frozen cell can be displaced by a new one; the same rows are read (sample size is
asserted against A's artefact); and three things are measured:

  1. the storage dialect of every message column in all eight corpora (list vs JSON string vs missing) - the fact
     that caused the silent loss, censused rather than illustrated;
  2. every cell that moves, with both coverage numbers;
  3. the effect on the paper's headline quantities: per-corpus `loss_ratio`, the coverage-by-concept counts and the
     kill-gate arithmetic.

Pre-declared decision rule: if any cell moves from `absent` to usable, the frozen matrix published by EXP-0029/0030
is superseded in the sense that the corrected matrix is what the paper cites, the two numbers are both reported, and
the deviation is logged. No threshold, concept list or gate is changed here.

    python canonical_conformance_corrected_p003.py

Writes results_raw/EXP0090_p003_conformance_corrected_*.json and results_processed/EXP0090_coverage_matrix.csv.
"""
from __future__ import annotations

import json
import random
import sys
import time
from collections import Counter
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import canonical_conformance_audit_p003 as pilot          # noqa: E402
import canonical_conformance_main_p003 as main_mod        # noqa: E402

OUT_RAW, OUT_PROC = pilot.OUT_RAW, pilot.OUT_PROC
CONCEPTS = pilot.CONCEPTS
R = pilot.R
D = pilot.D
JSON_STRING_KEY = "messages_or_conversations_stored_as_json_string"


# ---------------- the corrected parsers ----------------
# Registered into pilot.P because that is the dict the frozen `measure()` resolves parser names against; the frozen
# parsers themselves are not touched.

def _decoded_msgs(row):
    """Message list whether the column holds a list or a JSON-encoded string. `list(str)` was the bug."""
    v = row.get("messages")
    if v is None:
        v = row.get("conversations")
    if isinstance(v, str):
        try:
            v = json.loads(v)
        except Exception:
            return []
    return list(v or []) if isinstance(v, list) else []


def _role(m):
    return (m.get("role") or m.get("from") or m.get("author") or m.get("speaker")) if isinstance(m, dict) else None


def _content(m):
    return str((m or {}).get("content", (m or {}).get("value", "")) or "") if isinstance(m, dict) else ""


OBS_ROLES = ("tool", "function", "function_response", "observation", "environment")
pilot.P["role_vocab_json"] = lambda r: sorted({str(_role(m)).strip().lower() for m in _decoded_msgs(r)
                                               if _role(m)} - {"none"})
pilot.P["tool_role_obs_json"] = lambda r: [_content(m) for m in _decoded_msgs(r)
                                           if str(_role(m)).strip().lower() in OBS_ROLES and _content(m).strip()]
pilot.P["instruction_from_msg_json"] = lambda r: [_content(m) for m in _decoded_msgs(r)
                                                  if str(_role(m)).strip().lower() in ("user", "human")][:1]
pilot.P["observation_prefix_any"] = lambda r: [c for c in (_content(m) for m in _decoded_msgs(r))
                                               if pilot.OBS_PREFIX.match(c)]


def corrected_specs():
    specs = {k: {"path": v["path"], "cols": {c: list(cs) for c, cs in v["cols"].items()},
                 "conflicts": dict(v.get("conflicts", {}))} for k, v in pilot.SPEC.items()}
    specs["MMAT-1M"] = {"path": main_mod.MMAT_SPEC["path"],
                        "cols": {k: list(v) for k, v in main_mod.MMAT_SPEC["cols"].items()}, "conflicts": {}}
    # EXP-0030's nested Toucan probes stay in place; the JSON-decoding ones are appended after them.
    tc = specs["Toucan-1.5M"]["cols"]
    tc["C4_model_id"] = tc["C4_model_id"] + [R("meta_nested_model")]
    tc["C5_teacher_provider"] = tc["C5_teacher_provider"] + [R("meta_nested_provider")]
    for con, name in (("C7_role_vocabulary", "role_vocab_json"), ("C11_observation", "tool_role_obs_json"),
                      ("C8_user_instruction", "instruction_from_msg_json")):
        tc[con] = tc[con] + [R(name)]
    ab = specs["AgentBank"]["cols"]
    ab["C7_role_vocabulary"] = ab["C7_role_vocabulary"] + [R("role_vocab_json")]
    ab["C11_observation"] = ab["C11_observation"] + [R("observation_prefix_any"), R("tool_role_obs_json")]
    ab["C8_user_instruction"] = ab["C8_user_instruction"] + [R("instruction_from_msg_json")]
    for cname in ("SWE-ZERO-12M", "hermes-agent-reasoning-traces", "AgentTrove", "code-act", "AgentInstruct"):
        c = specs[cname]["cols"]
        c["C11_observation"] = c["C11_observation"] + [R("observation_prefix_any")]
    return specs


def selftest() -> None:
    row = {"messages": json.dumps([{"role": "system", "content": "sys"}, {"role": "user", "content": "hi there"},
                                   {"role": "function", "content": '{"results": []}'},
                                   {"role": "assistant", "content": "done"}])}
    if len(_decoded_msgs(row)) != 4:
        raise SystemExit("ABORT selftest: _decoded_msgs did not recover 4 messages from a JSON string")
    if pilot.P["role_vocab_json"](row) != ["assistant", "function", "system", "user"]:
        raise SystemExit("ABORT selftest: role_vocab_json gave " + str(pilot.P["role_vocab_json"](row)))
    if not pilot.P["tool_role_obs_json"](row):
        raise SystemExit("ABORT selftest: the `function` role is still not admitted as an observation")
    frozen = pilot.P["role_vocab"](row)
    if frozen:
        raise SystemExit("ABORT selftest: the frozen parser is not the one that was broken - nothing to correct")
    print("  selftest ok: JSON-string messages -> 4 messages, 4 roles via the new probe, 0 via the frozen one")


def dialect(rows):
    """Is the message column a list or a JSON string? Measured per corpus, not assumed."""
    kinds = Counter()
    for r in rows:
        v = r.get("messages")
        if v is None:
            v = r.get("conversations")
        if isinstance(v, str):
            try:
                json.loads(v)
                kinds["json_string"] += 1
            except Exception:
                kinds["unparseable_string"] += 1
        elif isinstance(v, list):
            kinds["native_list"] += 1
        else:
            kinds["absent"] += 1
    n = max(1, sum(kinds.values()))
    return {k: round(v / n, 4) for k, v in kinds.items()}, kinds.get("json_string", 0)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    selftest()
    arts = sorted(OUT_RAW.glob("EXP0030_p003_conformance_main_*.json"))
    if not arts:
        raise SystemExit("ABORT: no EXP-0030 artefact to compare against")
    A = json.loads(arts[-1].read_text(encoding="utf-8"))
    a_cells = {c: {k: (v["state"], v["best_coverage"]) for k, v in (d.get("cells") or {}).items()}
               for c, d in A["corpora"].items()}

    specs = corrected_specs()
    res = {"exp_id": "EXP-0090", "paper_id": "P003", "seed": pilot.SEED,
           "protocol": "papers/P003_metadata_interoperability/protocol_freeze.md",
           "triggered_by": "EXP-0089 second-auditor crossings (Toucan C7/C11, AgentBank C11)",
           "a_artefact": arts[-1].name, "probes_added": ["role_vocab_json", "tool_role_obs_json",
                                                          "instruction_from_msg_json", "observation_prefix_any"],
           "frozen_order_kept": True,
           "corpora": {}, "dialect": {}, "dependence": {}, "moved_cells": []}
    res["started_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    for name, spec in specs.items():
        if name == "MMAT-1M":
            rows, files = main_mod.sample_jsonl(pilot.DATA / spec["path"], pilot.ROWS)
            container = {"format": "jsonl", "files_read": files}
        else:
            rows, note = pilot.sample_parquet(pilot.DATA / spec["path"])
            container = {"format": "parquet", "note": note}
        n_expect = (A["corpora"].get(name) or {}).get("n_rows")
        if not rows:
            raise SystemExit(f"ABORT: {name} produced no rows - the correction cannot be measured")
        if n_expect is not None and len(rows) != n_expect:
            raise SystemExit(f"ABORT: {name} sample moved ({len(rows)} vs A's {n_expect}) - this run must read the "
                             "same rows as EXP-0030 or the delta is a sampling delta, not a parser delta")
        shares, n_json = dialect(rows)
        res["dialect"][name] = {"message_column_storage": shares, "rows_with_json_string_messages": n_json}
        cells, conflicts = pilot.measure(name, spec, rows)
        res["dependence"][name] = main_mod.dependence_census(name, spec, rows)
        cov = {}
        for con, cell in cells.items():
            best = max((e["coverage"] for e in cell["evidence"]), default=0.0)
            cov[con] = {"state": cell["state"], "best_coverage": round(best, 4),
                        "wilson95": main_mod.wilson(round(best * len(rows)), len(rows)),
                        "evidence": cell["evidence"]}
            a_state, a_cov = a_cells.get(name, {}).get(con, ("missing", None))
            if a_state != cell["state"]:
                res["moved_cells"].append({"corpus": name, "concept": con, "a_state": a_state, "a_coverage": a_cov,
                                            "new_state": cell["state"], "new_coverage": round(best, 4),
                                            "decided_by": max(cell["evidence"], key=lambda e: e["coverage"])
                                            ["source"] if cell["evidence"] else ""})
        states = Counter(v["state"] for v in cov.values())
        res["corpora"][name] = {"n_rows": len(rows), "container": container, "cells": cov,
                                "conflicts": conflicts,
                                "loss_ratio": round((states["absent"] + states["ambiguous"] + states["conflict"])
                                                    / len(CONCEPTS), 4),
                                "state_counts": dict(states)}
        if name == "MMAT-1M":
            # the paper's integrity claim reads this key, so the corrected matrix must carry it too
            res["corpora"][name]["asset_integrity"] = main_mod.broken_image_refs(rows, pilot.DATA / spec["path"])
        print(f"  {name}: rows={len(rows)} loss={res['corpora'][name]['loss_ratio']} json_string_msgs={n_json}")

    res["loss_ratios"] = {c: v["loss_ratio"] for c, v in res["corpora"].items()}
    res["n_corpora_audited"] = len(res["corpora"])
    res["sampling"] = {"rows_target": pilot.ROWS, "shards": pilot.SHARDS, "head_per_shard": pilot.HEAD,
                       "identical_to_EXP0030": True}
    res["no_usable_grouping_key"] = sorted(c for c, v in res["dependence"].items()
                                           if not any(d["usable_key"] for d in v.values()))
    res["a_loss_ratios"] = {c: v.get("loss_ratio") for c, v in A["corpora"].items()}
    res["loss_ratio_delta"] = {c: round(res["corpora"][c]["loss_ratio"] - res["a_loss_ratios"][c], 4)
                               for c in res["corpora"] if c in res["a_loss_ratios"]}
    cov_count = Counter()
    for c, v in res["corpora"].items():
        for k, cell in v["cells"].items():
            if cell["state"] in ("direct", "derived"):
                cov_count[k] += 1
    res["coverage_by_concept"] = dict(cov_count)
    a_cov_count = Counter()
    for c, v in a_cells.items():
        for k, (st, _cv) in v.items():
            if st in ("direct", "derived"):
                a_cov_count[k] += 1
    res["coverage_by_concept_delta"] = {k: cov_count.get(k, 0) - a_cov_count.get(k, 0) for k in CONCEPTS}
    n_corp = len(res["corpora"])
    res["gate"] = {"rule": A.get("gate", {}).get("rule", "drop P003 if >=10 of 12 concepts are direct|derived in "
                                                          ">=7 corpora"),
                   "concepts_passing": sum(1 for x in cov_count.values() if x >= max(7, n_corp - 1)),
                   "a_concepts_passing": A.get("gate", {}).get("concepts_passing"), "n_corpora": n_corp}
    upgraded = [m for m in res["moved_cells"] if m["a_state"] == "absent" and m["new_state"] in ("direct", "derived")]
    res["n_moved"] = len(res["moved_cells"])
    res["n_absent_to_usable"] = len(upgraded)
    res["json_string_corpora"] = sorted(c for c, d in res["dialect"].items()
                                        if d["rows_with_json_string_messages"] > 0)
    if upgraded:
        res["verdict"] = (f"CORRECTION CHANGES THE MATRIX: {len(upgraded)} cell(s) move absent -> usable "
                          f"({', '.join(m['corpus'] + ':' + m['concept'] for m in upgraded)}), caused by the frozen "
                          "parser reading a JSON-string message column as characters. The corrected matrix is what "
                          "the paper cites; both loss ratios are reported and the deviation is logged")
    elif res["moved_cells"]:
        res["verdict"] = (f"{len(res['moved_cells'])} cell(s) change state but none crosses into usable; the "
                          "headline quantities are unchanged and the movement is reported as sensitivity")
    else:
        res["verdict"] = ("no cell moves under the corrected probes: EXP-0089's crossings are attributable to its "
                          "own structural rules, and the frozen matrix stands as published")
    res["wallclock_sec"] = round(time.time() - t0, 1)
    res["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")

    OUT_PROC.mkdir(exist_ok=True)
    pd.DataFrame([{"corpus": c, "concept": k, "state": v["state"], "coverage": v["best_coverage"],
                   "wilson95": str(v["wilson95"]),
                   "a_state": a_cells.get(c, {}).get(k, ("missing", None))[0]}
                  for c, v in res["corpora"].items() for k, v in v["cells"].items()]).to_csv(
        OUT_PROC / "EXP0090_coverage_matrix.csv", index=False)
    pd.DataFrame(res["moved_cells"]).to_csv(OUT_PROC / "EXP0090_moved_cells.csv", index=False)
    out = OUT_RAW / f"EXP0090_p003_conformance_corrected_{time.strftime('%Y%m%dT%H%M%S')}.json"
    out.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    print("moved cells:", json.dumps(res["moved_cells"], ensure_ascii=False)[:900])
    print("loss ratio delta:", json.dumps(res["loss_ratio_delta"], ensure_ascii=False))
    print("gate:", json.dumps(res["gate"], ensure_ascii=False))
    print("verdict:", res["verdict"])
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
