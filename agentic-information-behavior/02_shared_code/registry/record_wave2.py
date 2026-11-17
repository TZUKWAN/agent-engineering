"""Register the wave-2 experiments, composing every status string from the artefact rather than from memory.

Run after the wave-2 designs: `python 02_shared_code/registry/record_wave2.py`. It is idempotent (the recorder
upserts by exp_id), so re-running an experiment and then this file re-registers whatever the artefact now says.

A status typed by hand is a number that can drift from the file it describes; each string here is built from the
loaded JSON, so re-running this after a re-run of the experiment re-registers whatever the artefact now says.
"""
import glob
import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = next(a for a in (HERE, *HERE.parents) if (a / "00_program_registry").is_dir())
PY = sys.executable
REC = str(ROOT / "02_shared_code" / "registry" / "record_experiment.py")


def latest(pat):
    f = sorted(glob.glob(str(ROOT / pat)), key=lambda x: pathlib.Path(x).stat().st_mtime)
    if not f:
        raise SystemExit(f"ABORT: no artefact matches {pat}; the experiment has not run")
    return f[-1]


def load(pat):
    return json.loads(pathlib.Path(latest(pat)).read_text(encoding="utf-8"))


def rel(pat):
    return "results_raw/" + pathlib.Path(pat).name


def verdicts(a):
    return "_".join(f"{m.get('hypothesis') or m.get('stratum') or m.get('term')}:{m.get('verdict')}"
                    for m in (a.get("models") or []) if isinstance(m, dict) and m.get("verdict"))


def call(exp, paper, topic, stage, script, config, status, artefacts, seed, notes, enters):
    cmd = [PY, REC, "--exp", exp, "--paper", paper, "--topic", topic, "--stage", stage, "--script", script,
           "--config", config[:300], "--status", status[:300], "--seed", seed, "--notes", notes[:300],
           "--enters-paper", enters[:200]]
    for a in artefacts:
        cmd += ["--artefact", a]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    tail = (r.stdout + r.stderr).strip().splitlines()
    print(f"{exp}: rc={r.returncode} {tail[-1][:150] if tail else ''}")


census = load("results_raw/EXP0135_wave2_premise_census_*.json")
M, G = census.get("measured", {}), census.get("kill_gates", {})
# In this artefact a gate value is the answer to "is the premise measurable?", so False is the blocked case - the
# first version of this line looked for a `fires` key that does not exist and registered "no_gate_fired" for a
# census that blocked two of its six topics.
blocked = [k for k, v in G.items() if v is False]
satisfied = [k for k, v in G.items() if v is True]
call("EXP-0135", "P012;P013;P014;P015;P016;P017", "T111;T112;T114;T115;T116;T117", "wave2_premise_census",
     "02_shared_code/package_factory/probe_wave2_premises.py",
     "candidate descriptions and parameters of the same 24,000 dev queries; rules fixed before any outcome read",
     f"premise_blocked_{'+'.join(sorted(blocked)) or 'none'}__premise_satisfied_{'+'.join(sorted(satisfied)) or 'none'}",
     [rel("results_raw/EXP0135_wave2_premise_census_*.json")], "n/a (deterministic)",
     "structure census that decides whether a wave-2 construct is identifiable before a protocol is relied on: "
     "negation in 2.9% of descriptions, centring dominant bin 89.0%, second centring rule kappa 0.414, "
     "specificity 43.97%, parameter enumeration 85.01%",
     "yes - the sample-and-substrate section of each package and the blocked record for T112/T117")

mx = load("results_raw/EXP0136_wave2_metadata_matrix_*.json")
call("EXP-0136", "P012;P014;P015;P016", "T111;T114;T115;T116", "wave2_feature_matrix",
     "02_shared_code/package_factory/exp_wave2_features.py",
     f"rows={mx.get('n_query_rows')} candidate_rows={mx.get('n_candidate_rows')} seed=42 bucket=dev; "
     "description-side rules only, no outcome read",
     f"matrix_built_{mx.get('n_query_rows')}_queries_{mx.get('n_candidate_rows')}_candidate_rows",
     [rel("results_raw/EXP0136_wave2_metadata_matrix_*.json")], "42",
     "the shared wave-2 substrate: agreement, description-size, enumeration, verb-coverage, specificity and "
     "prototype-centrality columns for every query and candidate",
     "yes - the sample, instruments and provenance tables of all four packages")

for exp, pkg, topic, key in (("EXP-0137", "P012", "T111", "0137"), ("EXP-0138", "P014", "T114", "0138"),
                             ("EXP-0139", "P015", "T115", "0139"), ("EXP-0140", "P016", "T116", "0140")):
    a = load(f"results_raw/EXP{key}_wave2_design_{key}_*.json")
    n = a.get("n_rows") or a.get("n_query_rows")
    call(exp, pkg, topic, "wave2_main", "02_shared_code/package_factory/exp_wave2_designs.py",
         f"seed=42; clustered on query_id; Holm over the design's three declared hypotheses; effect bands "
         f".05/.15/.30; n_rows={n}; invocation recorded in the artefact",
         f"{verdicts(a)[:250] or 'reported_as_thresholded_statistics'}",
         [rel(f"results_raw/EXP{key}_wave2_design_{key}_*.json")], "42",
         "the pre-registered test for this topic, with the amendment fields the artefact names (sign of the "
         "coefficient beside the frozen delta-AUROC verdict for T111; the frozen pattern requirement beside the "
         "band-only label for T116; explicit H1-H3 rows for T115; the non-gold displacement frame for T114's H2)",
         "yes - the whole result set")


g = load("results_raw/EXP0127_wave_literature_grading_*.json")
pp = g.get("papers") or []
papers = sorted(str(r.get("paper")) for r in pp)
tot = sum(int(r.get("rows", 0) or 0) for r in pp)
l4 = {str(r.get("paper")): int((r.get("levels") or {}).get("L4", 0)) for r in pp
      if (r.get("levels") or {}).get("L4")}
call("EXP-0127", ";".join(papers), "T101;T103;T106;T108;T109;T110;T111;T114;T115;T116",
     "wave1_wave2_collision_grading", "02_shared_code/literature/grade_wave_literature.py",
     "four-family rule imported from grade_collisions; ten wave lexicons authored from each design's construct; "
     "no outcome of any package read",
     f"levels_rederived_rows={tot}_across_{len(papers)}_papers_L4_{l4}",
     [rel("results_raw/EXP0127_wave_literature_grading_*.json")], "n/a (deterministic rule)",
     "re-derives overlap_level for every harvested record from the abstract text already in the matrix, for all ten "
     "wave packages at once; a level with no re-derived counterpart is reported as a weakness by package_audit",
     "yes - novelty_audit.md and the topic table collision column")


bat = load("results_raw/EXP0141_wave2_battery_0141_*.json")
sh = bat.get("_shared") or {}
e19 = (sh.get("e19_contamination") or {})
e17 = (sh.get("e17_counterfactual") or {})
call("EXP-0141", "P012;P014;P015;P016", "T111;T114;T115;T116",
     "e04_ablation_e06_second_instrument_e08_external_e12_scaling_e15_16_errors_e17_counterfactual_e18_replication_e19_contamination",
     "02_shared_code/package_factory/exp_wave2_battery.py",
     "spec 9 E-step battery; the same frozen covariates, clustering unit and bands; single-frame steps imported from "
     "exp_wave1_battery.py rather than rewritten; E17 rewrites the gold *description*, E08 re-estimates on HERMES",
     f"battery_executed_across_four_topics_e19_cross_config_description_share_{e19.get('share_of_descriptions_shared_across_configs')}_e17_rows_{e17.get('rows')}",
     [rel("results_raw/EXP0141_wave2_battery_0141_*.json")], "42",
     "the E00-E19 package requirement is owed to every paper: ablation, scaling, replication under seed 7, error "
     "taxonomy and quoted cases, second instrument, external transfer, counterfactual rewrite, cost and contamination",
     "yes - E_COVERAGE.md and tables/table8..table17")
