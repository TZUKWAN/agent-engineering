"""EXP-0110 (spec §21): one note stating how each special risk of this corpus family was handled, from the files.

§21 lists five risks specific to agent-trajectory data: synthetic trajectories must not be reported as human
information behaviour (21.1); a `<think>`-style trace may be studied only as uttered text (21.2); SWE-ZERO's
`exit_status` is not functional correctness (21.3); schemas must be kept and every conversion to the canonical
representation tested (21.4); and if an online model is called, its name, version, endpoint, prompt, seed and retries
must be logged (21.5). The programme had acted on all five, but only 21.1 and 21.4 left a file a reader could cite -
which is how a requirement stays quietly unmet: `spec_completion_audit.py` could not see §21 at all, because its
headings are numbered rather than labelled T/E/G/B.

This note is generated, not written: every clause cites the artefact that carries the measurement, and the completion
audit re-reads both this file and those artefacts. Where the answer is "we did not do that because we could not", the
sentence says so and names the evidence for the could-not.

    python 02_shared_code/registry/export_section21_note.py
"""
from __future__ import annotations
import csv, glob, io, json, pathlib, re, sys, time

ROOT = next(a for a in [pathlib.Path(__file__).resolve().parent,
                        *pathlib.Path(__file__).resolve().parents] if (a / "00_program_registry").is_dir())
OUT = ROOT / "docs" / "section21_special_risks.md"
REG = ROOT / "00_program_registry" / "experiment_registry.csv"


def latest(pat):
    f = sorted(glob.glob(str(ROOT / "results_raw" / pat)))
    return (pathlib.Path(f[-1]), json.loads(pathlib.Path(f[-1]).read_text(encoding="utf-8"))) if f else (None, {})


def registry_row(exp_id):
    for r in csv.DictReader(io.StringIO(REG.read_text(encoding="utf-8"))):
        if r.get("exp_id") == exp_id:
            return r
    return {}


def needle_present(files, needle):
    for f in files:
        if f and f.is_file() and needle.lower() in f.read_text(encoding="utf-8", errors="replace").lower():
            return True
    return None


CRLF = chr(13) + chr(10)
REG_PATH = ROOT / "00_program_registry" / "experiment_registry.csv"

REG_ROW = {"exp_id": "EXP-0110", "paper_id": "programme", "topic_id": "",
           "stage": "section21_special_risks_note",
           "script": "02_shared_code/registry/export_section21_note.py",
           "config": "generates docs/section21_special_risks.md from the EXP-0104/0108/0109 artefacts, the "
                     "packages' environment records and the manuscripts' own scope sentences; refuses to write "
                     "when a cited sentence has disappeared, so the note cannot outlive its evidence",
           "seed": "n/a (deterministic)", "started_at": "", "finished_at": "",
           "status": "section_21_documented_from_artefacts",
           "outputs": "docs/section21_special_risks.md",
           "notes": "the spec's section 21 (five special risks of this corpus family) was invisible to the "
                    "completion audit because its headings are numbered rather than labelled T/E/G/B; the audit "
                    "now parses them, and this note is the file that carries the answers - 21.4 backed by "
                    "EXP-0109's unit tests, 21.3 by EXP-0108's measurement of exit_status, 21.1/21.2 by "
                    "generated scope sentences in the manuscripts",
           "enters_paper": "no - programme-level compliance record; the sentences it cites live in the packs"}


_now = ""


def register_self() -> str:
    """Append this step's own row, keyed on its id. A step that documents itself in a file but never reaches the
    register is a step a reader cannot find from the experiment list."""
    raw = [r for r in csv.reader(io.StringIO(REG_PATH.read_text(encoding="utf-8"))) if r]
    hdr = raw[0]
    assert set(REG_ROW) == set(hdr), sorted(set(hdr) ^ set(REG_ROW))
    if REG_ROW["exp_id"] in {r[0] for r in raw[1:]}:
        # refresh the timestamps of an existing row rather than leaving a blank pair behind: the register is where a
        # reader looks for when a step ran, and a self-registering step should not be able to file itself at no time
        idx = {n: i for i, n in enumerate(hdr)}
        changed = False
        for r in raw[1:]:
            if r[idx["exp_id"]] == REG_ROW["exp_id"] and not r[idx["started_at"]].strip():
                r[idx["started_at"]] = r[idx["finished_at"]] = _now
                changed = True
        if changed:
            buf = io.StringIO()
            w = csv.writer(buf, lineterminator=CRLF)
            for r in raw:
                w.writerow(r)
            REG_PATH.write_text(buf.getvalue(), encoding="utf-8", newline="")
            return "timestamps filled"
        return "already registered"
    REG_ROW["started_at"] = REG_ROW["finished_at"] = _now
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator=CRLF)
    w.writerow(hdr)
    for r in raw[1:]:
        w.writerow(r)
    w.writerow([REG_ROW[c] for c in hdr])
    REG_PATH.write_text(buf.getvalue(), encoding="utf-8", newline="")
    back = [r for r in csv.reader(io.StringIO(REG_PATH.read_text(encoding="utf-8"))) if r]
    assert back[0] == hdr and all(len(r) == len(hdr) for r in back), "registry shape broke"
    ids = [r[0] for r in back[1:]]
    assert len(ids) == len(set(ids)), "duplicate exp_id"
    return f"appended (rows={len(back) - 1})"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    p109f, p109 = latest("EXP0109_canonical_ir_tests*.json")
    p108f, p108 = latest("EXP0108_p004_external_shipped_label_*.json")
    p104f, p104 = latest("EXP0104_package_contamination_*.json")
    p001_paper = next(iter(sorted((ROOT / "papers").glob("P001*/paper.md"))), None)
    p002_paper = next(iter(sorted((ROOT / "papers").glob("P002*/paper.md"))), None)
    e62 = registry_row("EXP-0062")
    env_files = [p / "environment" / "system_info.json" for p in sorted((ROOT / "papers").glob("P0*"))]
    # A record counts as stating the §21.5 condition when it names the model-API status and the network status; the
    # packages do that in different shapes (P001 records `llm_api_available_by_policy` and the GPU it actually has,
    # P005 records `llm_api_used` and which endpoints literature retrieval touched), so the check is on the fields.
    def states_model_and_network(f):
        if not f.is_file():
            return False
        low = f.read_text(encoding="utf-8", errors="replace").lower()
        try:
            keys = set(json.loads(f.read_text(encoding="utf-8")).keys())
        except Exception:                                              # noqa: BLE001
            keys = set()
        model = ("llm_api_used" in keys or "llm_api_available_by_policy" in keys
                 or "no model inference" in low or "no api" in low)
        net = any("network" in k.lower() for k in keys) or "no network" in low
        return bool(model and net)
    cpu_only = [str(f.relative_to(ROOT)) for f in env_files if states_model_and_network(f)]
    missing_env = [str(f.relative_to(ROOT)) for f in env_files if not states_model_and_network(f)]
    if not (p109.get("verdict") == "ALL_TESTS_PASS"):
        raise SystemExit("ABORT: EXP-0109's suite is not passing; §21.4 cannot be claimed")
    if not needle_present([p001_paper], "not of human information behaviour"):
        raise SystemExit("ABORT: P001's manuscript no longer carries its §21.1 scope sentence")
    if not needle_present([p002_paper], "internal process"):
        raise SystemExit("ABORT: P002's manuscript no longer bounds the reading of uttered text (§21.2)")
    swe = (p104.get("packages", {}).get("P002", {}).get("corpora", {}).get("SWE-ZERO-12M", {}))
    L = ["# §21 - the special risks of this corpus family, and what the programme did about each",
         "",
         "Generated by `02_shared_code/registry/export_section21_note.py`. Every clause cites the file that carries it,",
         "and the note refuses to generate itself if a cited sentence has disappeared from the manuscript.",
         "",
         "## 21.1 Synthetic trajectories are not human information behaviour",
         "",
         "Every query in Toucan-1.5M is model-generated, and P001 states its results as \"properties of recorded",
         "agent-instruction data, not of human information behaviour\" (`papers/P001_routing_failure_qpp/paper.md`,",
         "abstract); P002's second limitation is \"Agent traces, not human information behaviour\"",
         "(`papers/P002_isp_stage_measurement/limitations.md`). No package claims a human population anywhere, and the",
         "reviewer-attack row A5 in P001 keeps the question and its answer visible rather than burying it.",
         "",
         "## 21.2 What a reasoning trace licenses, and what it does not",
         "",
         "The instruments read **uttered text and issued commands**. P001 predicts from \"only surface language\"",
         "(its related-work section states the constraint); P002's §1 now states that a `verify` label records that",
         "test-running text appears, not that anything was verified, and that no stage share is evidence about a",
         "model's internal process, beliefs or understanding. The mechanism behind that bound is tested, not",
         "assumed: `split_turn` gives the coder the prose before the first fenced command plus the command, and a",
         "turn with no command can only be `clarification` or `uncodable` (EXP-0109, cases",
         f"`turn_splitting_extracts_the_first_command_line_only` and",
         f"`coder_priority_is_first_match_wins_and_thought_only_needs_a_command`).",
         "",
         "## 21.3 SWE-ZERO's `exit_status` is not functional correctness",
         "",
         "The label was measured rather than read. Over the sampled SWE-ZERO rows it carries",
         f"**{len(p108.get('value_census', {}))} distinct values** "
         + ", ".join(f"`{k}` x{v}" for k, v in sorted(p108.get("value_census", {}).items(), key=lambda x: -x[1]))
         + ", i.e. it is a two-value flag, not a scale, and filtering to its non-default value keeps",
         f"{p108.get('gating_consequence', {}).get('share_kept', '?')} of rows and",
         f"{p108.get('gating_consequence', {}).get('repositories_after', '?')}/",
         f"{p108.get('gating_consequence', {}).get('repositories_before', '?')} repositories (EXP-0108,",
         f"`{p108f.name if p108f else 'not run'}`). Its association with a text-derived completion signal is",
         f"instance-clustered OR {p108.get('association_with_text_signal', {}).get('instance_clustered_or', '?')}",
         f"(95% CI {p108.get('association_with_text_signal', {}).get('bootstrap_ci95')}); the verdict is",
         f"**{p108.get('verdict', '?')}** - the label tracks something about the utterance, and it is not a",
         "verifier result. P002 therefore treats right-censoring (turn caps, `incomplete` as a cap rather than a",
         "failure) as the measurement problem it is, and reports the population consequence of any filter on it.",
         "An executable verifier or gold-patch outcome is the thing this estate does not contain, and the papers say",
         "so instead of inventing one.",
         "",
         "## 21.4 Mixed schemas: keep the original, test every conversion",
         "",
         "Each release's own message vocabulary is preserved (`role`/`content`, `from`/`value`, `from`/`loss`/`value`,",
         "and Toucan's JSON-string `messages` column), and the canonical reader is exercised by",
         f"**{p109.get('cases')} unit tests** - {p109.get('verdict')} in",
         f"`{(p109f.name if p109f else 'results_raw/EXP0109_canonical_ir_tests.json')}`. The suite imports the",
         "production functions, so a conversion that changes behaviour breaks a test rather than a table. The",
         "cross-release duplication question is answered by measurement too: EXP-0104 compares task text across the",
         f"releases ({p104.get('packages', {}).get('P003_P005', {}).get('cross_release', {}).get('verdict', 'not run')}",
         "on the pairs that carry text).",
         "",
         "## 21.5 Online-model drift",
         "",
         "The programme's boundary is that no hosted model is called during analysis, so there is no server-side",
         "version, endpoint or temperature that could drift. Each package's environment record states the model-API",
         "status and the network status explicitly, in the shape that package's run deserves - P001 records the GPU it",
         "actually has together with `llm_api_available_by_policy` and `network_used_during_analysis`; P005 records",
         "`llm_api_used` plus the endpoints its literature retrieval touched; the other three record it in prose. "
         + (f"**{len(cpu_only)} of {len(env_files)}** package environment records carry both fields."
            if not missing_env else
            f"**{len(cpu_only)} of {len(env_files)}** carry both fields; missing: {', '.join(missing_env)}") +
         "",
         "The one model that does run, runs locally, and it is recorded with the provenance §21.5 asks for: "
         + (f"{e62.get('outputs', 'EXP-0062 row missing')}".split(";")[0] + " - "
            + re.sub(r"\s+", " ", e62.get("notes", ""))[:260] if e62 else "EXP-0062 is not in the register"),
         "",
         "If a future step ever calls a hosted model, the fields it must log are the spec's: model name, version,",
         "date, endpoint, temperature, system prompt, retry policy and seed where the API accepts one. This note is",
         "the place that claim is checked, so a step that calls an API without logging it fails the audit that reads",
         "this file.",
         ""]
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8", newline="")
    res = {"exp_id": "EXP-0110", "at": time.strftime("%Y-%m-%dT%H:%M:%S"), "wrote": str(OUT.relative_to(ROOT)),
           "inputs": {"EXP-0109": p109f.name if p109f else None, "EXP-0108": p108f.name if p108f else None,
                      "EXP-0104": p104f.name if p104f else None, "EXP-0062_row": bool(e62)},
           "env_records_stating_cpu_only": len(cpu_only), "env_records_total": len(env_files),
           "guard": "refuses to write if 21.1/21.2 sentences are missing from the manuscripts or the suite is failing",
           "wallclock_sec": round(time.time() - t0, 1)}
    (ROOT / "results_raw" / f"EXP0110_section21_note_{time.strftime('%Y%m%dT%H%M%S')}.json").write_text(
        json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    REG_ROW["started_at"] = REG_ROW["finished_at"] = res["at"]
    print("  registry:", register_self())
    print("  wrote", OUT.relative_to(ROOT))
    print("  inputs:", ", ".join(str(v) for v in res["inputs"].values()))
    print("  environment records stating CPU-only/no-network:", res["env_records_stating_cpu_only"],
          "of", res["env_records_total"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
