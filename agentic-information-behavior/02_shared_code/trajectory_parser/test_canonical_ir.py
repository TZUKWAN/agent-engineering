"""EXP-0109 (spec 21.4): unit tests for the canonicalisations the programme's numbers depend on.

21.4 requires a cross-schema study to keep the original schema, build one canonical intermediate representation, and give
**each transformation a unit test**. The programme kept the first two and silently skipped the third: no `test_*.py`
existed anywhere when this file was written, which is also why the completion audit never saw the requirement - it
parsed only headings labelled T/E/G/B, and 21.4 is labelled numerically.

The tests import the real functions from the real modules rather than re-implementing them, so changing a
canonicalisation breaks a test instead of quietly moving a paper's number. Several cases pin a failure mode that was
actually found and fixed: message keys differ per release and Toucan stores its whole array as a JSON string
(EXP-0029/0030); the model id sits one level deeper than the first probe read it (D18); an unparsable catalogue must
yield None rather than a short list a later step would read as "few candidates" (EXP-0005); the dev/test boundary is
keyed on prompt_id, not uuid, because a follow-up row shares its prompt_id (EXP-0008); and None, "", "null", [] and 0
are three kinds of absence, a null-text and a value.

Run:  python 02_shared_code/trajectory_parser/test_canonical_ir.py [--json out.json]
Exits non-zero if any case fails. Reads no dataset and writes nothing unless --json is given.
"""
from __future__ import annotations
import argparse, json, pathlib, sys, time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = next(a for a in (HERE, *HERE.parents) if (a / "00_program_registry").is_dir())
for _sub in ("trajectory_parser", "behavior_tagger", "data_audit"):
    sys.path.insert(0, str(ROOT / "02_shared_code" / _sub))

import build_toucan_routing_dataset as ROUTE      # noqa: E402
import isp_stage_coder as CODER                   # noqa: E402
import canonical_conformance_audit_p003 as AUD     # noqa: E402

CASES = []


def case(fn):
    CASES.append(fn)
    return fn


@case
def message_key_vocabularies_map_onto_one_reader():
    rows = [{"messages": [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "yo"}]},
            {"conversations": [{"from": "human", "value": "hi"}, {"from": "gpt", "value": "yo"}]},
            {"conversations": [{"from": "human", "loss": None, "value": "hi"}]}]
    assert AUD._msgkey(rows[0]) == "messages"
    assert AUD._msgkey(rows[2]) == "conversations"
    assert [AUD.content_of(m, "content") for m in rows[0]["messages"]] == ["hi", "yo"]
    assert [AUD.content_of(m, "value") for m in rows[1]["conversations"]] == ["hi", "yo"]
    assert AUD.role_of(rows[1]["conversations"][0], "from") == "human"
    assert AUD.role_of(rows[0]["messages"][0], "role") == "user"


@case
def json_string_message_column_is_only_counted_as_presence():
    # Toucan keeps the whole array in one string column. The audit scores that concept from the column's non-emptiness
    # (state `direct`), and the derived per-message parsers deliberately do not see turns there - a parser that
    # pretended to read it would report vocabulary it had actually torn into characters.
    raw = json.dumps([{"role": "user", "content": "question"}])
    row = {"messages": raw}
    assert AUD.non_empty(row["messages"]) is True
    items = AUD.msgs(row, "messages")
    assert items and isinstance(items[0], str) and len(items[0]) == 1
    assert AUD.role_of(items[0], "role") is None and AUD.content_of(items[0]) == ""
    assert AUD.msgs({"messages": []}, "messages") == [] and AUD.msgs({}, "messages") == []


@case
def model_id_is_read_from_the_nested_generation_configs():
    row = {"metadata": json.dumps({"synthetic_data_gen_configs": [{"model": "qwen3-coder"}, {"model": "kimi-k2"}]})}
    assert [c.get("model") for c in AUD._nested_cfgs(row)] == ["qwen3-coder", "kimi-k2"]
    assert AUD._nested_cfgs({"metadata": "not json"}) == []
    assert AUD._nested_cfgs({"metadata": json.dumps({"model": "flat"})}) == []
    assert AUD._nested_cfgs({"metadata": json.dumps({"synthetic_data_gen_configs": {"model": "one"}})}) == [{"model": "one"}]
    assert AUD._nested_cfgs({}) == []


@case
def metadata_cell_types_never_raise():
    assert AUD._meta({"metadata": json.dumps({"prompt_id": "p1"})})["prompt_id"] == "p1"
    assert AUD._meta({"metadata": {"prompt_id": "p2"}})["prompt_id"] == "p2"
    assert AUD._meta({"metadata": "{broken"}) == {}
    assert AUD._meta({"metadata": None}) == {} and AUD._meta({}) == {}
    assert AUD.P["meta_prompt_id"]({"metadata": json.dumps({"prompt_id": "p3"})}) == ["p3"]
    # a cell that parses but lacks the key yields one empty value, which non_empty() rejects: the row counts as
    # uncovered rather than as carrying an empty-string identifier
    assert AUD.P["meta_prompt_id"]({"metadata": "{}"}) == [None]


@case
def non_empty_separates_absent_blank_null_and_a_real_zero():
    assert not AUD.non_empty(None) and not AUD.non_empty("   ") and not AUD.non_empty("null")
    assert not AUD.non_empty("None") and not AUD.non_empty("{}") and not AUD.non_empty("[]")
    assert not AUD.non_empty([]) and not AUD.non_empty([None, ""])
    assert AUD.non_empty(0) and AUD.non_empty(False)
    assert AUD.non_empty("x") and AUD.non_empty([{"a": 1}])


@case
def catalogue_parsing_rejects_instead_of_truncating():
    assert ROUTE.parse_catalog("{not json") is None
    assert ROUTE.parse_catalog(json.dumps({"not": "a list"})) is None
    assert ROUTE.parse_catalog(json.dumps([{"no_name": 1}])) is None
    good = ROUTE.parse_catalog(json.dumps([{"function": {"name": "get_weather", "description": "w",
                                                         "parameters": {"properties": {"city": {}}}}},
                                           {"tool_name": "search", "description": ""}]))
    assert [d["name"] for d in good] == ["get_weather", "search"]
    assert good[0]["params"] == ["city"] and good[1]["params"] == []
    assert good[1]["desc"] == ""                    # a missing description is "", not a missing record
    assert [d["name"] for d in ROUTE.parse_catalog(json.dumps([{"name": "a"}, {"name": "a"}]))] == ["a", "a"]
    assert ROUTE.parse_catalog(json.dumps([{"name": "获取天气", "description": "描述"}]))[0]["name"] == "获取天气"


@case
def split_is_a_pure_function_of_prompt_id_with_disjoint_buckets():
    ids = [f"p{i}" for i in range(5000)]
    dev = {p2 for p2 in ids if ROUTE.bucket(p2) < ROUTE.DEV_FRACTION_BUCKET}
    test = set(ids) - dev
    assert dev and test and not (dev & test) and len(dev) + len(test) == len(ids)
    assert ROUTE.bucket("p1") == ROUTE.bucket("p1")
    assert 0 <= min(ROUTE.bucket(p2) for p2 in ids) and max(ROUTE.bucket(p2) for p2 in ids) < 1000
    assert ROUTE.DEV_FRACTION_BUCKET == 700         # the frozen 70/30 rule, not a per-run choice


@case
def turn_splitting_extracts_the_first_command_line_only():
    fence = chr(96) * 3
    body = "I will run the suite now" + chr(10) + fence + "bash" + chr(10) + "python -m pytest tests/ -q" + chr(10) + "extra" + chr(10) + fence
    thought, cmd = CODER.split_turn(body)
    assert cmd == "python -m pytest tests/ -q"
    assert fence not in thought and thought.startswith("I will run")
    assert CODER.split_turn("no fence here") == ("no fence here", "")
    second = "first" + chr(10) + fence + "sh" + chr(10) + "ls" + chr(10) + fence + chr(10) + "then " + fence + "bash" + chr(10) + "pwd" + chr(10) + fence
    t2, c2 = CODER.split_turn(second)
    # the thought is only what precedes the first fenced command: the coder reads plan-then-command, never the text
    # after it, which is why `clarification` keys on opening prose rather than on any prose in the turn
    assert c2 == "ls" and t2 == "first" + chr(10) and "pwd" not in t2


@case
def coder_priority_is_first_match_wins_and_thought_only_needs_a_command():
    assert CODER.code_turn("let me run the tests now", "pytest tests/") == "verify"
    assert CODER.code_turn("the issue asks for the file layout", "ls -R") == "exploration"
    assert CODER.code_turn("", "pip install requests") == "system"
    # the frozen rule keeps the `end` share honest: a turn with no command is either a plan or uncodable, so a thought
    # that merely contains the word "done" cannot mark the episode finished
    assert CODER.code_turn("all tests pass, done", "") == "uncodable"
    assert CODER.code_turn("I should explore the layout first", "") == "clarification"


@case
def observation_kind_keeps_three_states_apart():
    assert CODER.observation_kind("") == "empty"
    assert CODER.observation_kind("Observation: *") == "empty"
    assert CODER.observation_kind("Traceback (most recent call last):") == "error-shaped"
    assert CODER.observation_kind("42 files changed") == "informative"
    assert CODER.observation_kind(None) == "empty"


@case
def tool_call_spellings_are_extracted_per_shape():
    assert AUD.CALLBLK.search('x <tool_call>{"name":"get_weather"}</tool_call> y').group(1) == '{"name":"get_weather"}'
    assert AUD.FREECALL.search('{"name": "x"}').group(1) == "x"
    assert AUD.FREECALL.search('<lapi:search_files>').group(2) == "search_files"
    assert AUD.FREECALL.search('call-name: foo_bar').group(3) == "foo_bar"


@case
def lexical_tokenisation_is_lowercase_stopword_free_and_empty_safe():
    assert ROUTE.toks("") == []
    toks = ROUTE.toks("Get THE Weather API 获取天气")
    assert all(t == t.lower() for t in toks)
    assert "the" not in toks and "get" not in toks          # the stop list is applied at tokenisation, not later
    assert "weather" in toks and "api" in toks


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="", help="write the per-case report here")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    out, failed = [], []
    for fn in CASES:
        try:
            fn()
            ok, err = True, ""
        except AssertionError as e:
            ok, err = False, f"assertion failed: {e or str(fn.__name__)}"
        except Exception as e:                                          # noqa: BLE001
            ok, err = False, f"{type(e).__name__}: {e}"
        out.append({"test": fn.__name__, "ok": ok, "error": err,
                    "doc": (fn.__doc__ or fn.__name__).strip().splitlines()[0]})
        print(f"  {'PASS' if ok else 'FAIL'}  {fn.__name__}" + (f"  {err[:120]}" if err else ""))
    n_passed = sum(1 for o in out if o["ok"])
    print(f"  {n_passed}/{len(out)} canonicalisation tests pass "
          f"({', '.join(o['test'] for o in out if not o['ok']) or 'no failures'})")
    rep = {"exp_id": "EXP-0109", "at": time.strftime("%Y-%m-%dT%H:%M:%S"), "cases": len(out),
           "failed": [o["test"] for o in out if not o["ok"]],
           "verdict": "ALL_TESTS_PASS" if not any(not o["ok"] for o in out) else "TESTS_FAIL",
           "results": out, "wallclock_sec": round(time.time() - t0, 2)}
    if a.json:
        pathlib.Path(a.json).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(a.json).write_text(json.dumps(rep, indent=1, ensure_ascii=False), encoding="utf-8")
        print("  wrote", a.json)
    return 1 if rep["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
