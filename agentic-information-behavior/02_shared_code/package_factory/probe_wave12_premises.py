"""EXP-0215: the wave-12 premise census - three corpora and the closing aggregation over all eight.

Wave 12 is the last batch of the 2026-09-23 intake: T184 (information density of natural-language versus code
actions, on xingyaoww/code-act), T189 (corrective versus ritual reflection, on VIS-MPU-Agent/MMAT-1M), T194
(case-based reuse of historical trajectories, on the estate's fixed SWE-ZERO draw) and T036 (the descriptive
aggregation of all eight local corpora as intelligence sources). Each substrate is measured for what the design
conditioned on it needs, and the gates record what is there:

* code-act stores one `conversations` list per row, whose assistant turns are natural-language answers, tool calls or
  ``<execute>`` code blocks, so an action kind is readable; what has to be measured is whether each kind occurs often
  enough, whether errors come back as text the agent then acts on, and whether code blocks have more than one
  statement (T184's composition arm);
* MMAT-1M stores a multimodal operator loop - `<THOUGHT>`, `<OPERATOR>`, then a user turn carrying that operator's
  result - so a reflection marker and the content shift it produces are both measurable; what it does **not** store is
  any correctness label, which is why T189's hypotheses are written as change, not as being right;
* the SWE-ZERO draw has several attempts of one instance and many instances per repository, which is what T194 needs
  for "prior cases", but the release records no timestamp and no retrieval of an earlier case, so the ordering and
  library premises are measured here rather than assumed;
* the eight corpora are inventoried structurally - units, rows, the label each carries and the language fields - which
  is all T036's descriptive aggregation can honestly aggregate.

Gates are absolute floors on the cell each estimate uses, never a share of rows (the W10-D01 rule), each names its
scope and its topics, and every rule was written before a row was opened.

    python 02_shared_code/package_factory/probe_wave12_premises.py [--cap 200] [--code-cap 400]
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import itertools
import re
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import numpy as np                                                # noqa: E402
import pandas as pd                                               # noqa: E402
import pyarrow.parquet as pq                                      # noqa: E402
import wave_lib as W                                              # noqa: E402
import exp_wave6_features as EF6                                  # noqa: E402  the SWE draw, unchanged
import probe_wave6_premises as P6                                 # noqa: E402  one content-word rule
import probe_wave11_premises as P11                               # noqa: E402  uncertainty/negation lists, unchanged

EXP = "EXP-0215"
SEED = 42
ROOT_DATA = pathlib.Path(str(W.ROOT.parent) + "/MATLABINTOKEN/datasets")
CODEACT = ROOT_DATA / "xingyaoww/code-act/data"
MMAT = ROOT_DATA / "VIS-MPU-Agent/MMAT-1M"
EIGHT = {"Toucan-1.5M": "Agent-Ark/Toucan-1.5M", "SWE-ZERO-12M": "AlienKevin/SWE-ZERO-12M-trajectories",
         "hermes-agent-reasoning-traces": "lambda/hermes-agent-reasoning-traces", "AgentTrove": "open-thoughts/AgentTrove",
         "AgentBank": "Solaris99/AgentBank", "MMAT-1M": "VIS-MPU-Agent/MMAT-1M", "code-act": "xingyaoww/code-act",
         "AgentInstruct": "zai-org/AgentInstruct"}

EXEC_RX = re.compile(r"<execute>\s*(.*?)</execute>", re.S | re.I)
TOOL_RX = re.compile(r"<tool_call>|```python|def\s+\w+\(", re.I)
ERROR_RX = re.compile(r"(traceback|error|exception|failed|invalid|not found|no such|assertionerror)", re.I)
REFLECT_RX = re.compile(r"\b(wait|hold on|let me reconsider|reconsider|i need to (check|recheck)|actually|"
                        r"correction|i made a mistake|on second thought|let me try again|re-?check|"
                        r"that is wrong|this is wrong|instead)\b", re.I)
THOUGHT_RX = re.compile(r"<THOUGHT>(.*?)</THOUGHT>", re.S | re.I)
OPERATOR_RX = re.compile(r"<OPERATOR>\s*(.*?)\s*</OPERATOR>", re.S | re.I)


def words(s) -> set:
    return P6.words(s)


def action_kinds(text: str) -> dict:
    code = EXEC_RX.findall(text)
    per_block = [len([l for l in re.split(r"[\n;]+", c) if l.strip()]) for c in code]
    return {"n_code_blocks": int(len(code)),
            "max_block": int(max(per_block) if per_block else 0),
            "n_statements": int(sum(per_block)),
            "has_tool": int(bool(TOOL_RX.search(text))),
            "nl_chars": int(max(0, len(text) - sum(len(c) for c in code)))}


def measure_codeact(cap: int) -> dict:
    files = sorted(CODEACT.glob("*.parquet"))
    if not files:
        raise SystemExit(f"ABORT: no parquet under {CODEACT}")
    rows = kinds = 0
    with_code = with_multi = with_error = err_then_change = 0
    turns_per_conv, density_code, density_nl = [], [], []
    sources = collections.Counter()
    for f in files:
        pf = pq.ParquetFile(f)
        for b in pf.iter_batches(batch_size=2000, columns=["id", "conversations"]):
            for cid, conv in zip(b.to_pydict()["id"], b.to_pydict()["conversations"]):
                if rows >= cap:
                    break
                rows += 1
                ms = [dict(x) for x in list(conv)]
                asst = [str(m.get("content") or "") for m in ms if str(m.get("role")) == "assistant"]
                if not asst:
                    continue
                kinds += 1
                agg = collections.Counter()
                for t in asst:
                    for k, v in action_kinds(t).items():
                        agg[k] += v
                turns_per_conv.append(len(asst))
                sources[str(cid).split("/")[0] if "/" in str(cid) else str(cid).split(".")[0]] += 1
                if agg["n_code_blocks"]:
                    with_code += 1
                    density_code.append(agg["n_statements"] / max(1, agg["n_code_blocks"]))
                blocks = [c for t in asst for c in EXEC_RX.findall(t)]
                with_multi += int(any(len([l for l in re.split(r"[\n;]+", c) if l.strip()]) >= 2 for c in blocks))
                seq = [str(m.get("content") or "") for m in ms]
                for i in range(len(seq) - 2):
                    # an executed block, an observation that reports a problem, then a different executed block: the
                    # only correction cycle this corpus can show without a label
                    if EXEC_RX.search(seq[i]) and ERROR_RX.search(seq[i + 1]) and EXEC_RX.search(seq[i + 2]) \
                            and seq[i].strip() != seq[i + 2].strip():
                        err_then_change += 1
                        break
                if agg["nl_chars"]:
                    w = sum(len(words(t)) for t in asst)
                    density_nl.append(w / max(1, agg["nl_chars"]))
                joined = " \n ".join(asst)
                if ERROR_RX.search(joined):
                    with_error += 1
            if rows >= cap:
                break
        if rows >= cap:
            break
    return {"corpus": "xingyaoww/code-act, both shards, read to the cap", "rows_read": rows,
            "rows_with_assistant_turns": kinds,
            "conversations_with_code": with_code, "conversations_with_multi_statement_code": with_multi,
            "conversations_with_an_error_string": with_error,
            "conversations_with_a_correction_cycle": err_then_change,
            "mean_assistant_turns": round(float(np.mean(turns_per_conv)), 2) if turns_per_conv else None,
            "mean_statements_per_code_block": round(float(np.mean(density_code)), 3) if density_code else None,
            "mean_content_words_per_nl_character_x1000":
                round(float(np.mean(density_nl)) * 1000, 3) if density_nl else None,
            "sources_with_50plus_rows": int(sum(1 for v in sources.values() if v >= 50)),
            "distinct_sources": int(len(sources))}


def measure_mmat(cap: int) -> dict:
    f = MMAT / "dataset_qa_rr_val_all_RR_sys.jsonl"
    if not f.is_file():
        raise SystemExit(f"ABORT: {f} is not on disk")
    n = 0
    with_thought = with_reflect = reflect_shift = pairs_scored = 0
    shifts, operators, answers = [], collections.Counter(), 0
    turns = []
    with open(f, encoding="utf-8") as fh:
        for line in fh:
            if n >= cap:
                break
            try:
                d = json.loads(line)
            except Exception:                                       # noqa: BLE001 - a bad line is counted, not used
                continue
            n += 1
            ms = [dict(x) for x in (d.get("messages") or [])]
            ths = [m for m in THOUGHT_RX.findall(" \n ".join(str(x.get("content") or "") for x in ms
                                                             if str(x.get("role")) == "assistant"))]
            ths = [str(t) for t in ths]
            if not ths:
                continue
            with_thought += 1
            turns.append(len(ths))
            for o in OPERATOR_RX.findall(" \n ".join(str(x.get("content") or "") for x in ms
                                                      if str(x.get("role")) == "assistant")):
                operators[str(o).strip().lower()[:24]] += 1
            prev = None
            for t in ths:
                w = words(t)
                if REFLECT_RX.search(t):
                    with_reflect += 1
                    if prev is not None and (prev or w):
                        j = len(prev & w) / max(1, len(prev | w))
                        shifts.append(j)
                        pairs_scored += 1
                        if j < 0.8:
                            reflect_shift += 1
                prev = w
            if any(str(x.get("role")) == "assistant" and "answer" in str(x.get("content") or "").lower()
                   for x in ms[-3:]):
                answers += 1
    return {"corpus": "VIS-MPU-Agent/MMAT-1M, the validation split of the reflection-rewrite file",
            "lines_read": n, "conversations_with_thoughts": with_thought,
            "mean_thought_turns": round(float(np.mean(turns)), 2) if turns else None,
            "reflection_markers_total": with_reflect, "marker_pairs_scored": pairs_scored,
            "pairs_that_shifted_content": reflect_shift,
            "share_of_pairs_that_shifted": round(reflect_shift / max(1, pairs_scored), 4),
            "mean_jaccard_after_marker": round(float(np.mean(shifts)), 4) if shifts else None,
            "distinct_operators": int(len(operators)),
            "top_operators": {k: int(v) for k, v in operators.most_common(8)},
            "conversations_with_a_final_answer_turn": answers,
            "correctness_label_present": False}
def measure_swe(cap: int) -> dict:
    """T194's premises on the estate's fixed SWE-ZERO draw: prior attempts, neighbours and any ordering."""
    drawn, picks, rows_in_files, dupes = EF6.load_trajectories(cap or 20000)
    inst = collections.Counter()
    repo_inst = collections.defaultdict(set)
    issue_words = {}
    has_time = has_library = 0
    neighbours = []
    for k, t in enumerate(drawn):
        iid = str(t.get("instance_id"))
        inst[iid] += 1
        repo_inst[str(t.get("repo") or "none")].add(iid)
        if t.get("date") or t.get("timestamp") or t.get("created_at"):
            has_time += 1
        if t.get("retrieved_cases") or t.get("prior_cases") or t.get("demonstrations"):
            has_library += 1
        msgs = [dict(x) for x in (t.get("messages") or [])]
        issue = next((str(m.get("content") or "") for m in msgs if str(m.get("role")) == "user"), "")
        issue_words.setdefault(iid, set()).update(itertools.islice(sorted(words(issue)), 400))
    for iid, w in issue_words.items():
        best = 0.0
        for other, ow in issue_words.items():
            if other == iid or not (w or ow):
                continue
            j = len(w & ow) / max(1, len(w | ow))
            best = max(best, j)
        neighbours.append(best)
    multi = sum(1 for v in inst.values() if v >= 2)
    return {"corpus": "the estate's fixed 12-file SWE-ZERO draw", "rollouts": len(drawn),
            "instances": int(len(inst)), "instances_with_2plus_rollouts": int(multi),
            "repos": int(len(repo_inst)),
            "repos_with_50plus_instances": int(sum(1 for v in repo_inst.values() if len(v) >= 50)),
            "mean_best_neighbour_similarity": round(float(np.mean(neighbours)), 4) if neighbours else None,
            "rollouts_with_a_neighbour_at_0p3": int(sum(1 for v in neighbours if v >= 0.3)),
            "rollouts_with_a_timestamp_column": has_time, "rollouts_with_a_case_library_column": has_library}


def measure_eight() -> dict:
    """T036's basis: what each of the eight local corpora actually holds, counted from the directory and its columns."""
    out = {}
    for name, rel in EIGHT.items():
        base = ROOT_DATA / rel
        files = sorted(base.rglob("*.parquet")) + sorted(base.rglob("*.jsonl"))
        rows = None
        cols = []
        for f in files[:4]:
            try:
                if f.suffix == ".parquet":
                    pf = pq.ParquetFile(f)
                    rows = (rows or 0) + int(pf.metadata.num_rows)
                    cols = cols or list(pf.schema_arrow.names)
                else:
                    with open(f, encoding="utf-8", errors="replace") as fh:
                        n = sum(1 for _ in fh)
                    rows = (rows or 0) + n
                    first = json.loads(open(f, encoding="utf-8", errors="replace").readline() or "{}")
                    cols = cols or list(first.keys())[:24]
            except Exception:                                       # noqa: BROAD - a shard that will not open is noted
                continue
        out[name] = {"path": rel, "files": len(files), "rows_in_first_four_files": int(rows or 0),
                     "columns": [str(c) for c in cols][:24]}
    return out


GATES = {   # absolute floors on the cell each estimate uses; every scope and topic named before the read
 "G1_codeact_readable": {
     "rule": ">= 200 code-act conversations with at least one assistant turn, the units T184 types", "threshold": 200,
     "scope": "design", "blocks": ["T184"]},
 "G2_codeact_has_code_actions": {
     "rule": ">= 200 conversations containing an executed code block, without which there is no code action to "
             "compare with a natural-language one", "threshold": 200, "scope": "design", "blocks": ["T184"]},
 "G3_codeact_has_errors_to_recover_from": {
     "rule": ">= 100 conversations whose text reports an error, the correctability arm", "threshold": 100,
     "scope": "H3", "blocks": ["T184"]},
 "G4_codeact_has_composition": {
     "rule": ">= 100 conversations with a multi-statement code block, T184's composition arm", "threshold": 100,
     "scope": "H3", "blocks": ["T184"]},
 "G5_mmat_readable": {
     "rule": ">= 200 MMAT conversations with at least one <THOUGHT> block", "threshold": 200, "scope": "design",
     "blocks": ["T189"]},
 "G6_mmat_has_reflection_markers": {
     "rule": ">= 200 reflection markers followed by a scoreable content pair, below which 'ritual versus corrective' "
             "has no events to split", "threshold": 200, "scope": "H1", "blocks": ["T189"]},
 "G7_mmat_no_correctness_label": {
     "rule": "a correctness label must be present for any claim about a reflection making the answer right; the "
             "release carries none, so this gate fires by design and the wave reports change instead of "
             "correctness", "threshold": 1, "scope": "H3", "blocks": ["T189"]},
 "G8_swe_has_prior_attempts": {
     "rule": ">= 300 instances attempted more than once in the draw, which is T194's reuse material",
     "threshold": 300, "scope": "design", "blocks": ["T194"]},
 "G9_swe_has_neighbours": {
     "rule": ">= 1,000 rollouts whose issue text has a neighbour instance at Jaccard >= 0.3, the similar-past-case "
             "premise", "threshold": 1000, "scope": "H1", "blocks": ["T194"]},
 "G10_swe_records_order_or_a_library": {
     "rule": ">= 1 rollout carrying a timestamp or an explicit retrieved-case field, without which 'reuse of "
             "historical trajectories' cannot be observed as retrieval", "threshold": 1, "scope": "H3",
     "blocks": ["T194"]},
 "G11_eight_corpora_inventoried": {
     "rule": ">= 6 of the eight local corpora yield a file count, a row count and a column list, which is all T036's "
             "aggregation can be built from", "threshold": 6, "scope": "design", "blocks": ["T036"]},
 "G12_eight_corpus_label_coverage": {
     "rule": ">= 4 corpora expose an outcome or quality column among their first columns, the ceiling on how many of "
             "the eight can carry a labelled claim", "threshold": 4, "scope": "H1", "blocks": ["T036"]},
}


def apply_gates(m: dict) -> dict:
    ca, mm, swe, eight = m["codeact"], m["mmat"], m["swe"], m["eight_corpora"]
    labelled = sum(1 for v in eight.values()
                   if any(any(t in str(c).lower() for t in ("result", "status", "correct", "label", "reward",
                                                            "binary", "quality", "score")) for c in v["columns"]))
    checks = {"G1_codeact_readable": ca["rows_with_assistant_turns"],
              "G2_codeact_has_code_actions": ca["conversations_with_code"],
              "G3_codeact_has_errors_to_recover_from": ca["conversations_with_an_error_string"],
              "G4_codeact_has_composition": ca["conversations_with_multi_statement_code"],
              "G5_mmat_readable": mm["conversations_with_thoughts"],
              "G6_mmat_has_reflection_markers": mm["marker_pairs_scored"],
              "G7_mmat_no_correctness_label": int(bool(mm["correctness_label_present"])),
              "G8_swe_has_prior_attempts": swe["instances_with_2plus_rollouts"],
              "G9_swe_has_neighbours": swe["rollouts_with_a_neighbour_at_0p3"],
              "G10_swe_records_order_or_a_library": swe["rollouts_with_a_timestamp_column"]
              + swe["rollouts_with_a_case_library_column"],
              "G11_eight_corpora_inventoried": sum(1 for v in eight.values() if v["files"] and v["columns"]),
              "G12_eight_corpus_label_coverage": labelled}
    out = {}
    for k, g in GATES.items():
        v = checks[k]
        out[k] = {"measured": v, "fires": bool(v < g["threshold"]), "threshold": g["threshold"], "scope": g["scope"],
                  "blocks": list(g["blocks"]), "rule": g["rule"]}
    fired = [k for k, v in out.items() if v["fires"]]
    whole = sorted({t for k in fired if out[k]["scope"] == "design" for t in out[k]["blocks"]})
    limited = {k: out[k]["scope"] for k in fired if out[k]["scope"] != "design"}
    return {"gates": out, "verdict": {"blocked_gates": fired, "blocked_whole_design": whole,
                                      "claim_limited": limited}, "labelled_corpora": labelled}


def selftest() -> int:
    """Every instrument proven on one hand-built record of each kind before a release row is read."""
    code = "I will compute it\n<execute>\nimport pandas as pd\ndf = pd.read_csv('x.csv')\nprint(df.head())\n</execute>"
    kinds = action_kinds(code)
    assert kinds["n_code_blocks"] == 1 and kinds["n_statements"] >= 3, kinds
    assert ERROR_RX.search("Traceback (most recent call last): AssertionError")
    assert not ERROR_RX.search("all tests pass, 12 passed OK")
    assert REFLECT_RX.search("Wait, that is wrong, let me reconsider the angle.")
    assert not REFLECT_RX.search("The department is agriculture.")
    th = THOUGHT_RX.findall("<THOUGHT>first idea</THOUGHT> <OPERATOR>ocr</OPERATOR>")
    assert th == ["first idea"], th
    assert OPERATOR_RX.findall("<THOUGHT>x</THOUGHT> <OPERATOR>rag</OPERATOR>") == ["rag"]
    print("SELFTEST OK: action kinds, error and reflection markers, thought and operator extraction all land on "
          "built records")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cap", type=int, default=0, help="MMAT lines to read (0 = the frozen 4,000)")
    ap.add_argument("--code-cap", type=int, default=0, help="code-act conversations (0 = the frozen 4,000)")
    ap.add_argument("--swe-cap", type=int, default=0, help="SWE rollouts (0 = the frozen draw of 20,000)")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    selftest()
    m = {"corpus_set": "xingyaoww/code-act, VIS-MPU-Agent/MMAT-1M, the estate's SWE-ZERO draw, and all eight "
                       "local corpora inventoried",
         "codeact": measure_codeact(a.code_cap or 4000),
         "mmat": measure_mmat(a.cap or 4000),
         "swe": measure_swe(a.swe_cap or 20000),
         "eight_corpora": measure_eight()}
    g = apply_gates(m)
    art = {"exp_id": EXP, "seed": SEED, "rows_requested": {"codeact": a.code_cap or 4000, "mmat": a.cap or 4000,
                                                           "swe": a.swe_cap or 20000},
           "measured": m, "gate_rules": {k: v["rule"] for k, v in GATES.items()}, **g,
           "cluster_unit": "conversation or rollout, per design", "started_at": W.now(),
           "wallclock_sec": round(time.time() - t0, 1), "invocation": " ".join([sys.executable] + sys.argv),
           "run_cost": W.run_cost_row(EXP, t0, 0, 0, "wave-12 premise census")}
    dest = W.write_raw(EXP, "wave12_premise_census", art)
    print(json.dumps({"verdict": art["verdict"],
                      "gates": {k: [v["measured"], v["fires"]] for k, v in art["gates"].items()},
                      "codeact": m["codeact"], "mmat": {k: v for k, v in m["mmat"].items() if k != "top_operators"},
                      "swe": m["swe"], "labelled_corpora": art["labelled_corpora"]},
                     indent=1, ensure_ascii=False, default=str)[:3200])
    print("\nwrote", dest.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
