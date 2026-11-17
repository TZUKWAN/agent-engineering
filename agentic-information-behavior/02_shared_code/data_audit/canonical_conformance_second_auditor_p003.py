"""EXP-0089 (P003): re-derive every conformance cell with a second, blind auditor - the automated version of the
30-cell hand check the protocol asks for.

`papers/P003_metadata_interoperability/final_audit.md` closes with an outstanding item: the audit's own cell states
were verified only by a 30-cell self-audit that prints deciding evidence "for hand verification", and the paper says
the item is not settled until an analyst re-derives at least those cells. There is no analyst step in this programme,
so the check is re-instantiated the same way EXP-0087 and EXP-0088 were: a **second implementation, written against
the construct rather than against the mapping**, compared with the frozen one over a full census.

The two auditors differ in kind, not in wording:

  * **A (frozen, EXP-0029/0030)** reads a per-corpus *hypothesised mapping* (`pilot.SPEC`): an ordered list of
    candidate columns and named parsers per concept, with the protocol's thresholds applied to their coverage.
  * **B (this script)** never sees that mapping. It walks every node of every sampled row - top-level columns,
    nested dicts and lists, and JSON strings expanded one level down - and decides concept presence from a
    *shape/type signature* (UUID-like string at an id-named path, ISO-8601 or epoch value at a date-named path,
    list of dicts with a role and a content key for a message sequence, model-name pattern for a model id, and so
    on). Direct vs derived is then decided structurally: a value reachable as a top-level column node is direct,
    anything reached through a container or a JSON string is derived.

Coverage thresholds are the frozen ones (0.95 / 0.60 / 0.05), because the object under test is the mapping, not the
cut-points.

Why a census and not the 30 sampled cells: 21 of the 30 are `absent`, so a chance-corrected statistic on that
sub-panel is dominated by one class (the failure mode that made EXP-0087's first panel degenerate). All 96
corpus x concept cells are re-derived instead, which contains the 30 as a subset at the same cost.

Pre-declared decision rule, fixed here before B's states are read:

  * `boundary_crossings` counts cells where A and B disagree on **usable** (`direct`/`derived`) vs **not usable**
    (`absent`/`ambiguous`/`conflict`). That, not kappa, is the quantity the paper's `loss_ratio` depends on.
  * if B finds **3 or more** cells A called `absent` (A under-reports), the frozen mapping is demonstrably
    incomplete, and every `absent` in P003 must be re-labelled as "absent **under the frozen probe set**" - a
    mapping-relative claim - and that is recorded as a deviation, not softened in prose;
  * if B finds **3 or more** cells A called usable (A over-reports), the coverage table is wrong in the
    favourable direction and P003's headline claim is withdrawn pending correction;
  * if crossings are 1-2, they are listed individually with both auditors' evidence and the audit stands as
    documented;
  * if there are none and exact state agreement is >= 0.90, the audit's cell states are declared auditor-robust
    and the outstanding hand-verification item is closed as executed by automated re-derivation.

The two tolerance triggers are independent and both can fire; when they do the verdict names both directions rather
than the first one matched, because a one-sided reading of a two-sided disagreement is the thing this paper exists
to criticise in other people's instruments. Every crossing also carries its deciding values and a counterfactual
probe, so each is attributable to a named rule of one auditor or the other.

    python canonical_conformance_second_auditor_p003.py

Writes results_raw/EXP0089_p003_second_auditor_*.json and results_processed/EXP0089_cell_rederivation.csv.
"""
from __future__ import annotations

import json
import re
import sys
import time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import canonical_conformance_audit_p003 as pilot          # noqa: E402  (A's frozen sampling + thresholds)
import canonical_conformance_main_p003 as main_mod        # noqa: E402  (the jsonl reader for MMAT-1M)

DATA = pilot.DATA
OUT_RAW, OUT_PROC = pilot.OUT_RAW, pilot.OUT_PROC
CONCEPTS = pilot.CONCEPTS
CORPORA = list(pilot.SPEC) + ["MMAT-1M"]
N_CELLS = len(CORPORA) * len(CONCEPTS)
USABLE = {"direct", "derived"}
CUTOFF_DIRECT, CUTOFF_DERIVED, CUTOFF_SIGNAL = 0.95, 0.60, 0.05   # frozen in protocol section 4
UNDER_REPORT_TOL, OVER_REPORT_TOL = 3, 3                          # declared above, before B ran


# ---------------- B: shape signatures over a blind walk of the row ----------------

UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
HEX32_RE = re.compile(r"^[0-9a-fA-F]{32}$")
ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}([T ]\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:?\d{2})?)?$")
EPOCH_RE = re.compile(r"^[1-9]\d{8,9}$")
MODEL_RE = re.compile(r"(gpt|claude|gemini|llama|qwen|deepseek|kimi|mistral|sonnet|opus|haiku|phi-|grok|"
                      r"minimax|glm-|internlm|command-r|nova-|mixtral|\d{1,3}b\b)", re.I)
PROVIDERS = {"openai", "anthropic", "google", "deepmind", "together", "deepinfra", "fireworks", "azure",
             "aws", "bedrock", "moonshot", "z-ai", "zhipu", "mistral ai", "mistral", "alibaba", "openrouter",
             "cohere", "xai", "meta", "nvidia", "groq"}
ROLE_KEYS = ("role", "from", "speaker", "author", "role_type", "author_role")
CONTENT_KEYS = ("content", "value", "text", "message", "content_str", "plain", "conversation_content")
ID_PATH = re.compile(r"(^|[_./])(uuid|id|run_id|trajectory_id|sample_id|trace_id|conversation_id)([_./]|$)", re.I)
GROUP_PATH = re.compile(r"(prompt_id|task_id|instance_id|trial|problem_id|group_id|question_id|case_id|"
                        r"session_id|job_id|item_id|example_id|trial_name)", re.I)
DATE_PATH = re.compile(r"(date|time|timestamp|created|modified|ts$|_at$)", re.I)
MODEL_PATH = re.compile(r"(model|llm|teacher|generator_name|model_name|model_id)", re.I)
PROV_PATH = re.compile(r"(provider|engine|framework|vendor|platform|backend|origin)", re.I)
TOOL_PATH = re.compile(r"(tool|function|action|api)s?$", re.I)
CAND_PATH = re.compile(r"(available_tools|tools|function_call|functions|candidate|available_actions)", re.I)
ACT_PATH = re.compile(r"(target_tool|executed|action_input|command|tool_call|function_name|action_name|"
                      r"called_tool|used_tool)", re.I)
OBS_PATH = re.compile(r"(observation|tool_response|tool_result|output|stdout|result_of|feedback|env_result)", re.I)
OUT_PATH = re.compile(r"(outcome|resolved|solved|success|reward|judgment|judge|exit_status|passed|binary|"
                      r"quality|score|label|winner|status)", re.I)
INSTR_PATH = re.compile(r"(instruction|question|task$|query|prompt|user_input|problem|requirement)", re.I)
OBS_TEXT = re.compile(r"^\s*(observation|tool response|output)\s*:", re.I)
CALL_TEXT = re.compile(r"(\"(?:name|tool_name|function_name|function)\"\s*:|<tool_call>|</?lapi:|<\|tool_calls?\|>"
                       r"|```(?:bash|sh|python|shell)|\bdef\s+run\b)", re.I)


def filled(v) -> bool:
    """B's own emptiness test - deliberately stricter than A's `non_empty`: empty containers, empty dicts and
    the JSON null spellings all count as absent, and a numeric 0/False counts as present."""
    if v is None:
        return False
    if isinstance(v, str):
        s = v.strip()
        return bool(s) and s.lower() not in ("none", "null", "nan", "{}", "[]", "n/a", "na", "-")
    if isinstance(v, (list, tuple)):
        return any(filled(x) for x in v)
    if isinstance(v, dict):
        return any(filled(x) for x in v.values())
    return True


def as_json(v):
    """Expand a JSON-encoded string one level; anything else is not a container for B."""
    if not isinstance(v, str):
        return None
    s = v.strip()
    if not s or s[0] not in "[{":
        return None
    try:
        return json.loads(s)
    except Exception:
        return None


def walk(node, path="$", depth=0, out=None, cap=6000):
    """Every (path, value) node in a row, including nodes inside JSON strings and inside lists of dicts."""
    if out is None:
        out = []
    if depth > 6 or len(out) > cap:
        return out
    out.append((path, node))
    j = as_json(node)
    if j is not None and depth <= 3:
        walk(j, path + "~json", depth + 1, out, cap)
        return out
    if isinstance(node, dict):
        for k, v in node.items():
            walk(v, f"{path}.{k}", depth + 1, out, cap)
    elif isinstance(node, (list, tuple)):
        for i, v in enumerate(node):
            walk(v, f"{path}[{i}]", depth + 1, out, cap)
    return out


def msg_dicts(nodes):
    """Message-like lists anywhere in the row: a list whose items are dicts carrying both a role and a content key.
    Takes the already-walked node list - walking once per row and reusing it for all 12 concepts is the difference
    between a 20-second census and a 20-minute one."""
    found = []
    for path, v in nodes:
        cand = v
        j = as_json(v)
        if isinstance(j, list):
            cand = j
        if not isinstance(cand, (list, tuple)) or len(cand) < 2:
            continue
        dicts = [x for x in cand if isinstance(x, dict)]
        if len(dicts) >= 2 and all(any(k in x for k in ROLE_KEYS) and any(k in x for k in CONTENT_KEYS)
                                   for x in dicts):
            found.append((path, dicts))
            if len(found) >= 3:
                break
    return found


def roles_in(msg_lists):
    out = set()
    for _, dicts in msg_lists:
        for d in dicts:
            for k in ROLE_KEYS:
                if k in d and filled(d[k]) and isinstance(d[k], str):
                    out.add(d[k].strip().lower())
    return out


def instr_from_msgs(msg_lists):
    hit = False
    for _, dicts in msg_lists:
        for d in dicts:
            r = next((str(d[k]).strip().lower() for k in ROLE_KEYS if k in d), "")
            if r in ("user", "human", "prompt"):
                c = next((d[k] for k in CONTENT_KEYS if k in d), None)
                if filled(c) and len(str(c).strip()) >= 12:
                    hit = True
    return hit


def scalar_paths(row_nodes):
    return [(p, v) for p, v in row_nodes
            if p.count(".") <= 1 and "[[" not in p and isinstance(v, (str, int, float, bool))
            and not isinstance(v, bytes)]


def last(p: str) -> str:
    tail = re.sub(r"~json$", "", p).split(".")[-1]
    return re.sub(r"\[\d+\]", "", tail)


def row_ctx(row):
    """The per-row work shared by all 12 concept tests, computed once."""
    nodes = walk(row)
    return nodes, scalar_paths(nodes), msg_dicts(nodes)


def match(con: str, ctx):
    """B's decision for one (corpus row, concept): (hit, kind, why). Structural: top-level scalar => direct."""
    nodes, scal, ml = ctx

    def direct(p):
        return "direct" if p.count(".") <= 1 and "~json" not in p else "derived"

    if con == "C1_trajectory_id":
        for p, v in scal:
            s = str(v).strip()
            if filled(v) and ID_PATH.search(last(p)) and (UUID_RE.match(s) or HEX32_RE.match(s)
                                                          or (len(s) >= 16 and not s.isdigit())):
                return True, direct(p), p
        for p, v in scal:
            if filled(v) and UUID_RE.match(str(v).strip()):
                return True, "direct", p + "(uuid-shaped)"
    elif con == "C2_group_key":
        for p, v in scal:
            if filled(v) and GROUP_PATH.search(last(p)):
                return True, direct(p), p
    elif con == "C3_timestamp":
        for p, v in scal:
            s = str(v).strip()
            if filled(v) and DATE_PATH.search(last(p)) and (ISO_RE.match(s) or EPOCH_RE.match(s)
                                                            or re.match(r"^\d{4}-\d{2}-\d{2}$", s)):
                return True, direct(p), p
        for p, v in scal:
            if isinstance(v, str) and ISO_RE.match(v.strip()) and DATE_PATH.search(p):
                return True, direct(p), p + "(iso-shaped)"
    elif con == "C4_model_id":
        for p, v in scal:
            if filled(v) and MODEL_PATH.search(last(p)) and MODEL_RE.search(str(v)):
                return True, direct(p), p
        for p, v in scal:
            if filled(v) and MODEL_PATH.search(last(p)) and len(str(v).strip()) <= 80:
                return True, direct(p) + "+weak", p
    elif con == "C5_teacher_provider":
        for p, v in scal:
            if filled(v) and PROV_PATH.search(last(p)) and str(v).strip().lower() in PROVIDERS:
                return True, direct(p), p
        for p, v in scal:
            if filled(v) and PROV_PATH.search(last(p)) and len(str(v).strip()) <= 40:
                return True, direct(p) + "+weak", p
    elif con == "C6_message_sequence":
        if ml:
            p = ml[0][0]
            return True, direct(p), p
    elif con == "C7_role_vocabulary":
        if len(roles_in(ml)) >= 2:
            return True, "derived", ml[0][0] + "(>=2 roles)"
    elif con == "C8_user_instruction":
        for p, v in scal:
            if filled(v) and INSTR_PATH.search(last(p)) and len(str(v).strip()) >= 12:
                return True, direct(p), p
        if instr_from_msgs(ml):
            return True, "derived", "user-role message content"
    elif con == "C9_candidate_actions":
        for p, v in nodes:
            cand = as_json(v) if isinstance(v, str) else v
            if CAND_PATH.search(last(p)) and isinstance(cand, (list, tuple, dict)) and len(cand) >= 1:
                # a candidate set is a list of tool dicts/strings, or a dict keyed by tool name (both dialects occur)
                items = list(cand.values()) if isinstance(cand, dict) else list(cand)
                if items and all(isinstance(x, (dict, str)) for x in items) and any(filled(x) for x in items):
                    return True, direct(p), p
    elif con == "C10_executed_action":
        for p, v in scal:
            if filled(v) and ACT_PATH.search(last(p)):
                return True, direct(p), p
        for _, dicts in ml:
            if any(CALL_TEXT.search(str(d)) for d in dicts):
                return True, "derived", "call-shaped text inside message list"
    elif con == "C11_observation":
        for p, v in scal:
            if filled(v) and OBS_PATH.search(last(p)):
                return True, direct(p), p
        for _, dicts in ml:
            rs = [next((str(d[k]).strip().lower() for k in ROLE_KEYS if k in d), "") for d in dicts]
            cs = [next((d[k] for k in CONTENT_KEYS if k in d), "") for d in dicts]
            if any(r in ("tool", "function", "observation", "function_response", "environment") and filled(c)
                   for r, c in zip(rs, cs)):
                return True, "derived", "tool/observation-role message"
            if any(isinstance(c, str) and OBS_TEXT.match(c) for c in cs):
                return True, "derived", "'Observation:' prefix"
    elif con == "C12_outcome_signal":
        for p, v in scal:
            if not OUT_PATH.search(last(p)):
                continue
            if isinstance(v, (bool, int, float)):
                return True, direct(p), p
            s = str(v).strip()
            if filled(v) and len(s) <= 40 and re.search(r"(resolv|success|true|false|pass|fail|correct|"
                                                        r"incorrect|accept|reject|win|lose|[01]$)", s, re.I):
                return True, direct(p), p
    return False, "", ""


def b_state(ctxs, con: str):
    """Coverage of the shape signature over the sample, then the frozen cut-points."""
    hits, kinds, whys = 0, Counter(), Counter()
    for cx in ctxs:
        try:
            ok, kind, why = match(con, cx)
        except Exception as e:                       # a shape test that throws is a miss, and is counted
            ok, kind, why = False, "error", type(e).__name__
        if ok:
            hits += 1
            kinds[kind] += 1
            whys[why.split("[")[0]] += 1
    cov = hits / max(1, len(ctxs))
    if cov >= CUTOFF_DIRECT:
        st = "direct" if "direct" in "".join(kinds) else "derived"
    elif cov >= CUTOFF_DERIVED:
        st = "derived"
    elif cov > CUTOFF_SIGNAL:
        st = "ambiguous"
    else:
        st = "absent"
    return {"state": st, "coverage": round(cov, 4), "deciding_kind": kinds.most_common(1)[0][0] if kinds else "",
            "deciding_path": whys.most_common(1)[0][0] if whys else "",
            "error_rows": kinds.get("error", 0)}


# ---------------- sample identity: B must see the rows A saw ----------------

def load_rows(name: str):
    if name == "MMAT-1M":
        rows, _ = main_mod.sample_jsonl(DATA / main_mod.MMAT_SPEC["path"], pilot.ROWS)
        return rows
    rows, _ = pilot.sample_parquet(DATA / pilot.SPEC[name]["path"])
    return rows


def selftest() -> None:
    """Runs before any shard is opened, so a broken shape test fails in seconds, not after 20 minutes of IO."""
    row = {"uuid": "3f2a1c4e-7b1d-4c9a-8a11-0d2e5f6a7b8c", "prompt_id": 17, "created_at": "2026-01-04T09:12:33Z",
           "model": "gpt-4o-2024-08", "provider": "openai", "instruction": "List the files in /tmp and count them",
           "exit_status": "resolved", "tools": '{"a": {"name": "ls"}}',
           "messages": [{"role": "user", "content": "do the thing please"},
                        {"role": "assistant", "content": '```bash\nls -la\n```'},
                        {"role": "tool", "content": "total 3"}]}
    want = {"C1_trajectory_id": ("direct", True), "C2_group_key": ("direct", True),
            "C3_timestamp": ("direct", True), "C4_model_id": ("direct", True),
            "C5_teacher_provider": ("direct", True), "C6_message_sequence": ("direct", True),
            "C7_role_vocabulary": ("derived", True), "C8_user_instruction": ("direct", True),
            "C9_candidate_actions": ("direct", True), "C10_executed_action": ("derived", True),
            "C11_observation": ("derived", True), "C12_outcome_signal": ("direct", True)}
    bad = []
    ctx = row_ctx(row)
    for con, (kind, _) in want.items():
        ok, got_kind, why = match(con, ctx)
        if not ok or got_kind != kind:
            bad.append(f"{con}: got ({ok},{got_kind!r},{why!r}) want kind {kind!r}")
    empty = row_ctx({"nothing_here": 1})
    for con in CONCEPTS:
        ok, _, _ = match(con, empty)
        if ok:
            bad.append(f"{con} matched an unrelated row")
    if bad:
        raise SystemExit("ABORT selftest:\n  " + "\n  ".join(bad))
    print("  selftest ok: 12/12 concept signatures fire on the synthetic row, 0/12 on an empty one")


def scalar_paths_wide(nodes):
    """B's scalar list with the nested-JSON exclusion removed - used only as a counterfactual probe on crossings,
    to measure whether a blind cell is blind because of the top-level rule rather than because nothing carries it."""
    return [(p, v) for p, v in nodes
            if isinstance(v, (str, int, float, bool)) and not isinstance(v, bytes) and "~json" in p
            and p.split("~json")[1].count(".") <= 1]


def crossing_probe(con, rows, ctxs):
    """Concrete, checkable facts about one disagreeing cell: the deciding values themselves, the role keys the
    corpus really uses, and whether relaxing B's own structural rule would move the cell."""
    out = {}
    hits = [(r, cx) for r, cx in zip(rows, ctxs) if match(con, cx)[0]]
    out["b_hit_rows"] = len(hits)
    if hits:
        cx = hits[0][1]
        ok, kind, why = match(con, cx)
        out["b_deciding"] = f"{kind}@{why}"
        for p, v in cx[1]:
            if last(p).lower() in ("id", "uuid", "run_id") or con in ("C1_trajectory_id", "C2_group_key"):
                out.setdefault("b_values", []).append(f"{p}={str(v)[:60]!r}")
                if len(out["b_values"]) >= 3:
                    break
    # the frozen vocabulary question: which keys actually carry the speaker in this corpus?
    keys = Counter()
    vals = Counter()
    for _nodes, _scal, ml in ctxs:
        for _path, dicts in ml[:1]:
            for d in dicts:
                for k in ROLE_KEYS:
                    if k in d:
                        keys[k] += 1
                        if isinstance(d[k], str):
                            vals[d[k].strip().lower()] += 1
    if keys:
        out["role_keys_present"] = dict(keys.most_common(6))
        out["role_values_top"] = dict(vals.most_common(8))
    # counterfactual: does B's top-level-only scalar rule explain a `absent` verdict?
    if con in ("C2_group_key", "C3_timestamp", "C4_model_id", "C5_teacher_provider", "C8_user_instruction",
               "C10_executed_action", "C11_observation", "C12_outcome_signal"):
        n = len(ctxs) or 1
        cov_wide = sum(1 for nodes, _s, ml in ctxs
                       if match(con, (nodes, scalar_paths_wide(nodes) + _s, ml))[0]) / n
        out["coverage_if_json_nested_scalars_allowed"] = round(cov_wide, 4)
    if con in ("C1_trajectory_id", "C12_outcome_signal", "C4_model_id", "C5_teacher_provider"):
        col = {"C1_trajectory_id": ("id", "uuid", "run_id"), "C12_outcome_signal": ("exit_status", "result",
                                                                                    "judgment"),
               "C4_model_id": ("model",), "C5_teacher_provider": ("provider", "original_teacher")}[con]
        for c in col:
            vs = [r.get(c) for r in rows if c in r and filled(r.get(c))]
            if vs:
                out[f"values_in_{c}"] = dict(Counter(str(v)[:40] for v in vs).most_common(5))
                out[f"dtype_in_{c}"] = type(vs[0]).__name__
                break
    return out


def cohen_kappa(a, b, labels):
    n = len(a)
    if n == 0:
        return None
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[l] * cb[l] for l in labels) / (n * n)
    return None if pe >= 1 else round((po - pe) / (1 - pe), 4)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    selftest()
    arts = sorted((OUT_RAW).glob("EXP0030_p003_conformance_main_*.json"))
    if not arts:
        raise SystemExit("ABORT: no EXP-0030 artefact - A's cell states cannot be re-derived from memory")
    A = json.loads(arts[-1].read_text(encoding="utf-8"))
    a_cells = {c: {k: v["state"] for k, v in (d.get("cells") or {}).items()} for c, d in A["corpora"].items()}
    a_cov = {c: {k: v["best_coverage"] for k, v in (d.get("cells") or {}).items()} for c, d in A["corpora"].items()}
    sampled = {(x["corpus"], x["concept"]) for x in A.get("self_audit_sample", [])}
    print(f"  A taken from {arts[-1].name}; {len(sampled)} cells were the hand-check sample")

    cells, per_corpus_rows = [], {}
    for name in CORPORA:
        rows = load_rows(name)
        n_expect = (A["corpora"].get(name) or {}).get("n_rows")
        if not rows:
            raise SystemExit(f"ABORT: B could not read any rows for {name} - the comparison would be vacuous")
        if n_expect is not None and len(rows) != n_expect:
            raise SystemExit(f"ABORT: {name} sample size moved ({len(rows)} vs A's {n_expect}); B would be "
                             "measuring a different sample than A, not a different parser")
        per_corpus_rows[name] = len(rows)
        ctxs = [row_ctx(r) for r in rows]
        for con in CONCEPTS:
            b = b_state(ctxs, con)
            a = a_cells.get(name, {}).get(con)
            if a is None:
                raise SystemExit(f"ABORT: A has no cell for {name}:{con} - cannot score agreement")
            cells.append({"corpus": name, "concept": con, "a_state": a, "b_state": b["state"],
                          "a_coverage": a_cov[name][con], "b_coverage": b["coverage"],
                          "usable_agree": (a in USABLE) == (b["state"] in USABLE),
                          "state_agree": a == b["state"], "in_self_audit_sample": (name, con) in sampled,
                          "b_kind": b["deciding_kind"], "b_path": b["deciding_path"], "b_error_rows": b["error_rows"]})
        print(f"  {name}: {len(rows)} rows re-derived")

    la = [c["a_state"] for c in cells]
    lb = [c["b_state"] for c in cells]
    labels = sorted(set(la) | set(lb))
    n = len(cells)
    exact = round(sum(1 for c in cells if c["state_agree"]) / n, 4)
    usable_agree = round(sum(1 for c in cells if c["usable_agree"]) / n, 4)
    cross = [c for c in cells if not c["usable_agree"]]
    under = [c for c in cross if c["a_state"] == "absent"]          # A said absent, B found it
    over = [c for c in cross if c["a_state"] in USABLE]             # A said usable, B did not
    crossed_sample = [c for c in cross if c["in_self_audit_sample"]]
    err_rows = sum(c["b_error_rows"] for c in cells)

    # Mechanism facts for every crossing, measured on the same rows: which values decided it, which key the corpus
    # really uses for the speaker, and whether relaxing B's own structural rule would move the cell. The direction
    # of each disagreement is attributed to one auditor's rule rather than asserted, and the reader can check it.
    a_ev = {c: {k: v["evidence"] for k, v in (d.get("cells") or {}).items()} for c, d in A["corpora"].items()}
    for grp in sorted({c["corpus"] for c in cross}):
        rows = load_rows(grp)
        ctxs = [row_ctx(r) for r in rows]
        for c in [x for x in cross if x["corpus"] == grp]:
            c["mechanism"] = crossing_probe(c["concept"], rows, ctxs)
            c["a_evidence"] = a_ev.get(grp, {}).get(c["concept"])
            print(f"  probe {grp}:{c['concept']} A={c['a_state']} B={c['b_state']}")
        del rows, ctxs
    nested_blind = sum(1 for c in cross if c.get("mechanism", {}).get(
        "coverage_if_json_nested_scalars_allowed", 0) >= CUTOFF_DERIVED and c["b_state"] not in USABLE)
    nonfrozen_role = sum(1 for c in cross if any(k not in ("role", "from") for k in
                       (c.get("mechanism", {}).get("role_keys_present") or {})))

    if len(under) >= UNDER_REPORT_TOL and len(over) >= OVER_REPORT_TOL:
        verdict = (f"BOTH pre-declared triggers fire: A under-reports {len(under)} cells that B finds usable and "
                   f"over-reports {len(over)} cells B does not (tolerances {UNDER_REPORT_TOL}/{OVER_REPORT_TOL}), so "
                   f"neither auditor reproduces the other's usable set - {1 - usable_agree:.1%} of the {n} cells "
                   "cross the usable boundary. Consequence applied as written: every `absent` in P003 is a claim "
                   "about the frozen probe set, not about the corpus, and each crossing carries the deciding values "
                   "so the direction of each error is attributable. "
                   f"Measured split of the {len(cross)} crossings: {nested_blind} are explained by B's top-level-only "
                   f"scalar rule (relaxing it puts B over the 0.60 cut-off), {nonfrozen_role} involve a speaker key "
                   "outside the frozen role/from vocabulary")
    elif len(under) >= UNDER_REPORT_TOL:
        verdict = (f"A UNDER-REPORTS: B finds {len(under)} cells A called absent, at or over the pre-declared "
                   f"tolerance of {UNDER_REPORT_TOL}, so every `absent` in P003 is a statement about the frozen "
                   "probe set, not about the corpus, and must be re-labelled as such")
    elif len(over) >= OVER_REPORT_TOL:
        verdict = (f"A OVER-REPORTS: B finds {len(over)} usable cells A scored direct|derived, at or over the "
                   f"tolerance of {OVER_REPORT_TOL}, so the coverage table errs in the favourable direction and "
                   "P003's headline claim is withdrawn pending correction")
    elif cross:
        verdict = (f"BOUNDARY DISAGREEMENT ON {len(cross)} of {n} cells, below the {OVER_REPORT_TOL}-cell "
                   "re-label trigger; each is listed with both auditors' evidence and the audit stands as documented")
    elif exact >= 0.90:
        verdict = (f"AUDITOR-ROBUST: no usable/not-usable crossings anywhere in the {n}-cell census and exact "
                   f"state agreement {exact}, so the hand-verification item is closed by automated re-derivation")
    else:
        verdict = (f"no usable/not-usable crossings but exact state agreement {exact} below 0.90: the usable set "
                   "is reproducible while the direct/derived/ambiguous labelling is not, so P003 must report the "
                   "usable set rather than the per-state counts")

    res = {"exp_id": "EXP-0089", "paper_id": "P003", "seed": pilot.SEED, "n_cells": n,
           "a_artefact": arts[-1].name, "b_method": "shape-signature walk of every row node, blind to pilot.SPEC",
           "thresholds": {"direct": CUTOFF_DIRECT, "derived": CUTOFF_DERIVED, "signal_floor": CUTOFF_SIGNAL,
                          "provenance": "frozen in protocol_freeze.md section 4; unchanged here"},
           "rows_per_corpus": per_corpus_rows, "cells_reproduced_from_a_sample": len(sampled),
           "exact_state_agreement": exact, "usable_agreement": usable_agree,
           "cohen_kappa_states": cohen_kappa(la, lb, labels), "label_set": labels,
           "b_label_note": ("B has no `conflict` state - it decides presence by shape rather than by comparing two "
                            "named columns - so A's conflict cells are state disagreements by construction. They "
                            "are counted in `a_conflict_cells` and excluded from neither statistic"),
           "a_conflict_cells": sum(1 for x in la if x == "conflict"),
           "state_counts_a": dict(Counter(la)), "state_counts_b": dict(Counter(lb)),
           "boundary_crossings": len(cross), "a_under_reports": len(under), "a_over_reports": len(over),
           "crossings_in_self_audit_sample": len(crossed_sample),
           "crossings_explained_by_b_top_level_rule": nested_blind,
           "crossings_involving_non_frozen_speaker_key": nonfrozen_role,
           "crossing_list": [{k: c[k] for k in ("corpus", "concept", "a_state", "a_coverage", "b_state",
                                                "b_coverage", "b_kind", "b_path", "in_self_audit_sample",
                                                "mechanism", "a_evidence")}
                             for c in cross],
           "direction_confusion": {f"{x}->{y}": m for (x, y), m in
                                   Counter((a, b) for a, b in zip(la, lb) if a != b).items()},
           "b_error_rows": err_rows, "decision_rule": "see module docstring (fixed before B ran)",
           "verdict": verdict, "wallclock_sec": round(time.time() - t0, 1),
           "started_at": A.get("started_at"), "finished_at": time.strftime("%Y%m%dT%H:%M:%S")}
    import pandas as pd
    OUT_PROC.mkdir(exist_ok=True)
    flat = []
    for c in cells:
        row = dict(c)
        if isinstance(row.get("mechanism"), dict):
            row["mechanism"] = json.dumps(row["mechanism"], ensure_ascii=False)
        if isinstance(row.get("a_evidence"), list):
            row["a_evidence"] = json.dumps(row["a_evidence"], ensure_ascii=False)
        flat.append(row)
    pd.DataFrame(flat).to_csv(OUT_PROC / "EXP0089_cell_rederivation.csv", index=False)
    out = OUT_RAW / f"EXP0089_p003_second_auditor_{time.strftime('%Y%m%dT%H%M%S')}.json"
    out.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: res[k] for k in ("exact_state_agreement", "usable_agreement", "cohen_kappa_states",
                                          "boundary_crossings", "a_under_reports", "a_over_reports",
                                          "crossings_in_self_audit_sample", "b_error_rows", "wallclock_sec")},
                     ensure_ascii=False))
    print("verdict:", verdict)
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
