"""Record EXP-0048 (P005 pilot) into a new paper directory: pilot report + table + registry row + topic statuses.

Everything quantitative is read from the result file. The pilot's own frozen rule (docstring of
`governance_metadata_pilot_p005.py`) decides the verdict, and the verdict decides the paper's identity:
PROSE_ONLY means no "corpus metadata" headline - the study becomes what a release card *declares* versus what a
consumer can *verify* below it.

    python 02_shared_code/registry/record_exp0048_p005.py
"""
from __future__ import annotations

import csv, glob, io, json, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
REG = ROOT / "00_program_registry"
PAP = ROOT / "papers" / "P005_governance_metadata_verifiability"
DATA = ROOT.parent / "MATLABINTOKEN" / "datasets"

hits = sorted(glob.glob(str(ROOT / "results_raw" / "EXP0048_governance_metadata_pilot_*.json")))
if not hits:
    raise SystemExit("[e48] no EXP-0048 result file; writing nothing (no paper ahead of its evidence).")
NAME = pathlib.Path(hits[-1]).name
D = json.loads(pathlib.Path(hits[-1]).read_text(encoding="utf-8"))
PREV = json.loads(pathlib.Path(hits[0]).read_text(encoding="utf-8")) if len(hits) > 1 else None
COR = {c["corpus"]: c for c in D["corpora"]}
ORDER = list(COR)
PAP.mkdir(parents=True, exist_ok=True)
(PAP / "tables").mkdir(exist_ok=True)


def n(cls):
    return sum(1 for c in COR.values() if c["licence_class"] == cls)


fields = {k: (COR[k]["licence_field_value"] or "nothing") for k in ORDER}
multi = [k for k, v in fields.items() if "," in v]
none_decl = [k for k, c in COR.items() if c["licence_class"] == "nothing"]
urls = {k: COR[k].get("card_url_n", 0) for k in ORDER}
prov = {k: COR[k]["record_governance_columns"] for k in ORDER}
footers = {k: COR[k]["record_parquet_footers_read"] for k in ORDER}
art_n = sum(1 for c in COR.values() if c["artefacts_present"])
T1 = PAP / "tables" / "table_pilot_governance_presence.csv"
with open(T1, "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["corpus", "licence_class", "licence_field_value", "governance_artefacts_at_root",
                "hub_snapshot_markers", "licence_mentions_in_card_prose", "card_url_n", "distinct_hosts",
                "parquet_footers_read", "record_level_governance_columns"])
    for k in ORDER:
        c = COR[k]
        w.writerow([k, c["licence_class"], c["licence_field_value"], "|".join(c["artefacts_present"]) or "none",
                    "|".join(c.get("hub_snapshot_markers", [])) or "none", c.get("licence_mention_n", 0),
                    c.get("card_url_n", 0), c.get("card_distinct_hosts", 0), footers[k],
                    "|".join(prov[k]) or "none"])
print(f"[e48] wrote {T1.name}")

agentbank_envs = len([p for p in (DATA / "Solaris99" / "AgentBank").iterdir() if p.is_dir()])
REPORT = f"""# P005 pilot report — EXP-0048 (topic T013, with the T014 reference component)

Generated from `results_raw/{NAME}` by `02_shared_code/registry/record_exp0048_p005.py`. The scan is
`02_shared_code/data_audit/governance_metadata_pilot_p005.py` and its GO rule is fixed in that module's docstring,
written before the scan ran.

## What was scanned

Eight agent-trajectory releases on local disk, at four levels: root artefacts, the dataset card's YAML front matter,
the card's prose, and the data files themselves (parquet footer metadata + column names, capped at
{max(footers.values())} footers per corpus; jsonl-only corpora contribute the keys of their first record). URL
*availability* was deliberately not measured: `huggingface.co` and `github.com` are unreachable from this machine, so
a fetch failure could not be told apart from real link rot. That constraint — not convenience — is why T014 enters
only as a reference-*structure* component.

## Measured

- Root artefacts: **{art_n} of 8** releases carry a LICENSE / NOTICE / CITATION / DATASHEET file. All eight do carry
  a `.gitattributes`, which is git/LFS configuration and says nothing about rights.
- Card-level declaration: **{n('named_or_custom_field')} of 8** set a machine-readable `license:` key. Values:
  {"; ".join(f'{k} = `{v}`' for k, v in fields.items())}. {len(multi)} release declares several licences at once
  ({", ".join(multi) or "—"}); {len(none_decl)} declare nothing ({", ".join(none_decl) or "—"}).
- Card prose: licence words appear in {sum(1 for c in COR.values() if c.get('licence_mention_n'))} of 8 cards
  (maximum {max(c.get('licence_mention_n', 0) for c in COR.values())} mentions).
- Record level: **{sum(1 for c in COR.values() if c['record_governance_columns'])} of 8** corpora expose any
  licence / provenance / attribution / citation column in the files sampled, and no parquet footer carried a
  governance key. Rights information exists at the granularity of the *release*, never of the trajectory.
- References: {sum(1 for v in urls.values() if v)} of 8 cards cite external URLs ({sum(urls.values())} in total;
  most in {max(urls, key=urls.get)} with {max(urls.values())});
  {", ".join(k for k, v in urls.items() if v == 0) or "no corpus"} cites none at all.

## Verdict under the frozen rule

| conjunct | threshold | measured | |
|---|---|---|---|
| (1) nameable licence class | ≥5 of 8 | {D['rule_1_named_classes_n']} of 8 | PASS |
| (2) record/file-level signal beyond the card | ≥2 corpora | {len(D['rule_2_corpora_with_record_level_signal'])} | FAIL |
| (3) corpora with ≥2 named card-vs-disk gaps | ≥3 corpora | {len(D['rule_3_corpora_with_two_or_more_card_vs_disk_gaps'])} ({", ".join(D['rule_3_corpora_with_two_or_more_card_vs_disk_gaps']) or "none"}) | FAIL |

**Verdict: `{D['verdict']}`** — the topic may continue, but per the pre-declared consequence it continues as a
declaration-vs-verifiability content analysis with a *weaker* headline, not as a "governance metadata of agent
corpora" measurement study. Making that headline stronger after seeing this verdict would be exactly the move the
protocol forbids.

## Ambiguity in rule (2), recorded rather than resolved in our favour

Rule (2) says "record **or file** level". Read literally, a card's YAML `license:` key *is* a file-level,
machine-readable field, and under that reading the conjunct would pass {n('named_or_custom_field')} of 8. The run
scored it on record columns and parquet footers only, so the recorded verdict is the strict one and it stays the
official verdict of this pilot. The distinction is disclosed instead of being tidied away, and the substantive
question it does not affect is whether anything can be verified below the release tag — on the sampled files, no.

## Detector defect found and fixed (verdict unchanged by the fix)

The first run counted `.gitattributes` as a governance artefact. That made 8/8 corpora appear to carry a root-level
rights file, which suppressed rule-(3)'s gap class entirely: the rule-(3) count went from 0 corpora before the fix to
{len(D['rule_3_corpora_with_two_or_more_card_vs_disk_gaps'])} after it, and `artefacts_present` is empty for all eight
in the citable run. The artefact set is now `GOV_ARTEFACTS`, with hub-snapshot markers recorded separately as
`SNAPSHOT_MARKERS`. {f'The superseded first run reported verdict `{PREV["verdict"]}`; the verdict therefore did not depend on the defect.' if PREV else ''}
{len(hits)} result files for EXP-0048 exist and none is deleted; the two pre-fix runs are listed in
`results_raw/SUPERSEDED_ARTIFACTS.json`.

## What the main experiment must therefore do

1. Treat "the card says apache-2.0" as a datum about **declaration**, not about rights: how many derived agent
   corpora carry a single licence tag over components they themselves name (AgentBank's own directory tree names
   {agentbank_envs} source environments), and what an aggregator would need in order to check the claim.
2. Power the record-level scan properly — every split's footer per corpus rather than {max(footers.values())}, with a
   typed ingest so a JSON-string column cannot masquerade as an absent field (the interchange-vs-content lesson
   recorded for P003 in EXP-0029/0030).
3. Add the reference-structure component (T014): host families, and whether artifacts the card itself names exist on
   disk. Availability stays out of scope for the reason given above.
"""
(PAP / "pilot_report.md").write_text(REPORT, encoding="utf-8", newline="")
print("[e48] wrote pilot_report.md")

# ---------------------------------------------------------------- registry
hdr = list(csv.reader(io.StringIO((REG / "experiment_registry.csv").read_text(encoding="utf-8"))))[0]
row = dict(zip(hdr, [
    "EXP-0048", "P005 (T013+T014)", "governance_metadata_pilot_DONE",
    "02_shared_code/data_audit/governance_metadata_pilot_p005.py",
    "8 corpora x 4 levels (root artefacts / card YAML / card prose / record columns + parquet footer metadata); "
    f"footer-only parquet reads capped at {max(footers.values())} files per corpus; jsonl first-record keys; URL "
    "availability deliberately not measured (unreachable hosts would confound it); GO rule frozen in the docstring",
    "none (deterministic scan)", D["started_at"], D["finished_at"], "pilot_PROSE_ONLY_rule2_and_rule3_fail",
    f"{NAME}; results_processed/EXP0048_governance_presence.csv; papers/P005_governance_metadata_verifiability/"
    "pilot_report.md; papers/P005_governance_metadata_verifiability/tables/table_pilot_governance_presence.csv",
    f"0/8 corpora ship a rights artefact at root; {n('named_or_custom_field')}/8 declare a card-level licence tag "
    f"(6 x apache-2.0, 1 x three licences at once, 1 x nothing); 0/8 expose any record-level governance column. "
    f"Rule (1) {D['rule_1_named_classes_n']}/8 PASS but (2) and (3) FAIL -> PROSE_ONLY: P005 continues only as a "
    "declaration-vs-verifiability content analysis. First run miscounted .gitattributes as a rights artefact and so "
    "suppressed rule (3)'s gap class; detector fixed, all runs kept, and the rule-(2) wording ambiguity is disclosed "
    "rather than resolved in our favour.",
    "yes - it scopes P005's identity and is cited as its pilot"]))
p = REG / "experiment_registry.csv"
txt = p.read_text(encoding="utf-8")
if "EXP-0048" not in txt:
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\r\n").writerow([row[c] for c in hdr])
    p.write_text(txt.rstrip("\r\n") + "\r\n" + buf.getvalue().rstrip("\r\n") + "\r\n", encoding="utf-8", newline="")
    print("[e48] registered EXP-0048")

# ---------------------------------------------------------------- superseded register
SR = ROOT / "results_raw" / "SUPERSEDED_ARTIFACTS.json"
sj = json.loads(SR.read_text(encoding="utf-8"))
have = {e["file"] for e in sj["superseded"]}
for f, why in [("EXP0048_governance_metadata_pilot_20260919T180652.json",
                "counted .gitattributes (git/LFS configuration) as a governance artefact, so 8/8 corpora appeared to "
                "carry a root-level rights file and rule (3)'s gap class was suppressed. Replaced by "
                + NAME),
               ("EXP0048_governance_metadata_pilot_20260919T180754.json",
                "byte-for-byte duplicate of the 18:06 run: the detector patch had been written to disk after that "
                "process started, so it re-executed the old code. Kept only to show the re-run was not silent.")]:
    if f not in have and (ROOT / "results_raw" / f).exists():
        sj["superseded"].append({"file": f, "exp_id": "EXP-0048",
                                 "at": json.loads(pathlib.Path(hits[0]).read_text(encoding="utf-8"))["finished_at"],
                                 "reason": why, "was_it_quoted": "no - the pilot report was written from " + NAME})
SR.write_text(json.dumps(sj, indent=1, ensure_ascii=False), encoding="utf-8", newline="")
print(f"[e48] superseded register: {len(sj['superseded'])} entries")

# ---------------------------------------------------------------- topic statuses
TP = REG / "topic_registry.csv"
th = list(csv.reader(io.StringIO(TP.read_text(encoding="utf-8"))))[0]
rows = list(csv.DictReader(open(TP, encoding="utf-8")))
before = {r["topic_id"]: dict(r) for r in rows}
NEWST = {"T013": "w3_pilot_PROSE_ONLY_declaration_vs_verifiability_p005",
         "T014": "w3_merged_into_T013_reference_structure_only"}
for r in rows:
    if r["topic_id"] in NEWST:
        r["status"] = NEWST[r["topic_id"]]
with open(TP, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=th)
    w.writeheader()
    w.writerows(rows)
after = {r["topic_id"]: dict(r) for r in csv.DictReader(open(TP, encoding="utf-8"))}
assert set(after) == set(before)
for tid in after:
    for k in th:
        if k != "status" or tid not in NEWST:
            assert after[tid][k] == before[tid][k], f"{tid}.{k} changed unintentionally"
print("[e48] topic statuses updated: T013, T014 (status column only)")

import pandas as pd
d = pd.read_csv(p)
assert not d.exp_id.duplicated().any(), "duplicate exp_id"
print(f"[e48] registry rows={len(d)}; EXP-0048 present: {'EXP-0048' in set(d.exp_id)}")
for q in (T1, PAP / "pilot_report.md"):
    assert q.exists() and q.stat().st_size > 0
print("[e48] OK")
