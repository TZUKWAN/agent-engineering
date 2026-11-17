"""EXP-0048 (P005 candidate, topic T013 + T014): pilot - is there anything measurable about the governance
metadata that agent trajectory corpora ship?

T013 survived the novelty screen as the only L1 (one relevant record in four arXiv queries, EXP-0047): the licence
and provenance metadata OF AGENT TRAJECTORY CORPORA is not itself the object of any retrieved paper, even though
model-card / dataset-card work exists for models. This pilot decides whether that gap is *measurable* here before
any protocol is frozen.

What is scanned (all local, no network, no LLM):
  A. artefacts   - LICENSE/LICENCE/COPYING/NOTICE/.gitattributes/CITATION/DATASHEET/MODEL_CARD files, and whether
                   the copy on disk is a snapshot of a hub repo (which is itself a governance fact).
  B. card claims - the README's YAML front matter (hub metadata) and, separately, prose mentions of licence words
                   with verbatim context, because the spec forbids treating README claims as data facts: the paper
                   must distinguish "the card says X" from "the files carry X".
  C. record level- column names and parquet key/value metadata searched for licence/provenance/attribution fields.
                   Parquet metadata is read from the footer only; a multi-GB file is never loaded.
  D. references  - URLs in the card, classified by host family, plus local-path references and whether they resolve.
                   Availability of a URL is deliberately NOT measured: huggingface.co and github.com are unreachable
                   from this machine, so a fetch failure here cannot be distinguished from real link rot
                   (PROGRAM_STATUS §3). That constraint is why T014 enters as a structural component only.

Frozen GO rule, fixed in this docstring before the scan runs. GO iff all three hold:
  (1) >= 5 of 8 corpora yield a comparable licence statement of a class the scan can name
      (named licence / custom terms / prose mention only / nothing);
  (2) >= 2 corpora carry a licence or provenance signal at record or file level, not only in prose;
  (3) >= 3 corpora show at least two named card-vs-disk gaps each - the gap classes are exactly the ones this scan
      can name: no YAML front matter, no licence/CITATION artefact at the repository root, no external references in
      the card, no README at all. These are absences of expected governance structure, not legal conclusions.
If (1) holds but (2) fails, the study is a prose-content analysis and must be framed as such (weaker claim, no
"corpus metadata" headline). If (1) fails, the topic dies as unmeasurable, not as uninteresting.
The pilot measures prevalence only; it makes no legal conclusion and must not be written up as legal advice.

    python 02_shared_code/data_audit/governance_metadata_pilot_p005.py
"""
from __future__ import annotations

import json, pathlib, re, sys, time
from collections import Counter

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA = ROOT.parent / "MATLABINTOKEN" / "datasets"
OUT = ROOT / "results_raw"
PROC = ROOT / "results_processed"

CORPORA = {                                        # the same eight the other audits use
    "Toucan-1.5M": "Agent-Ark/Toucan-1.5M",
    "SWE-ZERO": "AlienKevin/SWE-ZERO-12M-trajectories",
    "AgentBank": "Solaris99/AgentBank",
    "MMAT-1M": "VIS-MPU-Agent/MMAT-1M",
    "hermes": "lambda/hermes-agent-reasoning-traces",
    "AgentTrove": "open-thoughts/AgentTrove",
    "code-act": "xingyaoww/code-act",
    "AgentInstruct": "zai-org/AgentInstruct",
}
GOV_ARTEFACTS = {"LICENSE", "LICENSE.md", "LICENCE", "LICENCE.md", "COPYING", "NOTICE", "CITATION.cff",
                 "CITATION", "DATASHEET.md", "MODEL_CARD.md", "DATASET_CARD.md"}
# .gitattributes is git/LFS configuration, not a governance artefact. The first version of this scan listed it as
# one, which made all eight repositories look like they carried a root-level rights file and silently suppressed the
# gap class rule (3) counts. Hub-snapshot provenance is recorded separately.
SNAPSHOT_MARKERS = {".gitattributes", ".gitignore"}
LIC_WORDS = re.compile(r"\b(licen[cs]e|licen[cs]ed|apache|mit|cc[- ]?(by|nc|sa|0)|bsd|gpl|odc|custom terms)\b", re.I)
URL = re.compile(r"https?://[^\s)\]\"'<>]+")
PROV_KEYS = re.compile(r"(licen[cs]e|attribut|provenance|source_dataset|created_by|generated_by|model_version|"
                       r"annotator|consent|redistribut|copyright|citation)", re.I)
MAX_PARQUET_FILES = 2          # footer-only, but still bounded on purpose
MAX_JSONL_LINE = 2_000_000     # read at most the first line of a jsonl shard


def front_matter(text):
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    if not m:
        return None, text
    try:
        return yaml.safe_load(m.group(1)), text[m.end():]
    except Exception as e:
        return {"_parse_error": type(e).__name__}, text[m.end():]


def licence_class(fm, prose, artefacts):
    """Named licence / custom terms / prose mention only / nothing - the comparable classes of rule (1)."""
    v = ""
    if isinstance(fm, dict):
        lic = fm.get("license") or fm.get("license_name") or ""
        if isinstance(lic, list):
            lic = ",".join(map(str, lic))
        v = str(lic).strip()
    if v and re.search(r"(apache|mit|bsd|gpl|cc[- ]|odc|other|custom)", v, re.I):
        return "named_or_custom_field", v
    if v:
        return "field_unnamed", v
    if any(a.startswith(("LICENSE", "LICENCE", "COPYING")) for a in artefacts):
        return "artefact_only", ""
    if LIC_WORDS.search(prose):
        return "prose_mention_only", ""
    return "nothing", ""


def parquet_fields(p):
    import pyarrow.parquet as pq
    f = pq.ParquetFile(p)
    cols = [x.name for x in f.schema_arrow]
    kv = {k.decode(): v.decode()[:200] for k, v in (f.metadata.metadata or {}).items()} if f.metadata else {}
    return cols, kv


def scan(name, rel):
    d = DATA / rel
    r = {"corpus": name, "path": rel, "exists": d.is_dir(), "error": None}
    if not d.is_dir():
        r["error"] = "directory absent"
        return r
    root_files = sorted(p.name for p in d.iterdir() if p.is_file())
    r["root_files"] = root_files
    r["artefacts_present"] = sorted(a for a in GOV_ARTEFACTS if a in root_files)
    r["hub_snapshot_markers"] = sorted(a for a in SNAPSHOT_MARKERS if a in root_files)
    rd = d / "README.md"
    fm, prose = (None, "")
    if rd.exists():
        text = rd.read_text(encoding="utf-8", errors="replace")
        fm, prose = front_matter(text)
        r["card_bytes"] = len(text)
        r["card_has_yaml_front_matter"] = fm is not None
        r["card_yaml_keys"] = sorted(str(k) for k in fm) if isinstance(fm, dict) else []
        hits = [m.group(0) for m in LIC_WORDS.finditer(prose)]
        r["licence_mention_n"] = len(hits)
        r["licence_mention_kinds"] = sorted({h.lower() for h in hits})[:12]
        snips = []
        for m in list(LIC_WORDS.finditer(prose))[:6]:
            snips.append(re.sub(r"\s+", " ", prose[max(0, m.start() - 90):m.end() + 90]).strip())
        r["licence_context_snippets"] = snips
        urls = URL.findall(prose)
        hosts = Counter(re.sub(r"^www\.", "", u.split("/")[2].lower()) for u in urls if "//" in u)
        r["card_url_n"] = len(urls)
        r["card_distinct_hosts"] = len(hosts)
        r["card_top_hosts"] = hosts.most_common(6)
        r["card_family_counts"] = {
            fam: sum(n for h, n in hosts.items() if pat.search(h))
            for fam, pat in [("huggingface", re.compile(r"huggingface|hf\.co", re.I)),
                             ("github", re.compile(r"github", re.I)), ("arxiv_doi", re.compile(r"arxiv|doi\.org", re.I)),
                             ("paper_or_site", re.compile(r"^(?!.*(huggingface|github|arxiv|doi)).+$", re.I))]}
    else:
        r["card_missing"] = True
    cls, val = licence_class(fm, prose, r["artefacts_present"])
    r["licence_class"], r["licence_field_value"] = cls, val

    # C. record-level signals: column names + parquet footer metadata, from at most MAX_PARQUET_FILES footers.
    prov_cols, kv_keys, files_seen = set(), set(), 0
    sample_fields = []
    for p in sorted(d.rglob("*.parquet"))[:MAX_PARQUET_FILES]:
        try:
            cols, kv = parquet_fields(p)
        except Exception as e:
            sample_fields.append({"file": p.name, "error": type(e).__name__})
            continue
        files_seen += 1
        prov_cols |= {c for c in cols if PROV_KEYS.search(c)}
        kv_keys |= set(kv)
        sample_fields.append({"file": p.name, "n_columns": len(cols), "columns": cols[:40]})
    if not files_seen:                                  # jsonl-only corpora (MMAT-1M) - first line only
        for p in sorted(d.rglob("*.jsonl"))[:1]:
            try:
                with open(p, encoding="utf-8", errors="replace") as fh:
                    line = fh.readline()[:MAX_JSONL_LINE]
                keys = list(json.loads(line).keys()) if line.strip().startswith("{") else []
                prov_cols |= {k for k in keys if PROV_KEYS.search(k)}
                sample_fields.append({"file": p.name, "kind": "jsonl_first_record", "columns": keys[:40]})
            except Exception as e:
                sample_fields.append({"file": p.name, "error": type(e).__name__})
    r["record_parquet_footers_read"] = files_seen
    r["record_governance_columns"] = sorted(prov_cols)
    r["record_parquet_metadata_keys"] = sorted(kv_keys)[:12]
    r["record_field_sample"] = sample_fields
    return r


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    res = {"exp_id": "EXP-0048", "topic": "T013 (+T014 component)", "paper_id": "P005 (candidate)",
           "scan_root": str(DATA), "rule": "GO iff (1) and (2) and (3); see module docstring",
           "availability_deliberately_unmeasured": "huggingface.co and github.com are unreachable from this host, "
                                                   "so a fetch failure could not be distinguished from link rot",
           "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "corpora": []}
    for name, rel in CORPORA.items():
        r = scan(name, rel)
        res["corpora"].append(r)
        print(f"  {name:12s} artefacts={('|'.join(r['artefacts_present']) or '-'):42s} "
              f"licence_class={r['licence_class']:22s} "
              f"mentions={r.get('licence_mention_n','-'):>3} urls={r.get('card_url_n','-'):>4} "
              f"prov_cols={len(r['record_governance_columns'])}")
    classes = Counter(c["licence_class"] for c in res["corpora"])
    t1 = classes.get("named_or_custom_field", 0) + classes.get("field_unnamed", 0) \
        + classes.get("artefact_only", 0) + classes.get("prose_mention_only", 0)
    t2 = [c["corpus"] for c in res["corpora"] if c["record_governance_columns"]
          or any(k.lower().startswith(("licence", "license")) for k in c["record_parquet_metadata_keys"])]
    dis = {c["corpus"]: [d for d in (
        ([] if c.get("card_has_yaml_front_matter") else ["no YAML front matter (hub metadata absent)"]),
        ([] if c["artefacts_present"] else ["no licence/CITATION artefact at repository root"]),
        ([] if c.get("card_url_n", 0) else ["no external references in the card"]),
        ([] if not c.get("card_missing") else ["no README.md at all"]),
    ) if d] for c in res["corpora"]}
    t3 = [k for k, v in dis.items() if len(v) >= 2]
    res["rule_1_named_classes_n"] = t1
    res["rule_1_classes"] = dict(classes)
    res["rule_2_corpora_with_record_level_signal"] = t2
    res["rule_3_corpora_with_two_or_more_card_vs_disk_gaps"] = t3
    res["per_corpus_gaps"] = dis
    res["verdict"] = "GO" if (t1 >= 5 and len(t2) >= 2 and len(t3) >= 3) else \
                     ("PROSE_ONLY" if t1 >= 5 else "NO_GO_UNMEASURABLE")
    res["wallclock_sec"] = round(time.time() - t0, 1)
    res["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    out = OUT / f"EXP0048_governance_metadata_pilot_{time.strftime('%Y%m%dT%H%M%S')}.json"
    out.write_text(json.dumps(res, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    PROC.mkdir(exist_ok=True)
    rows = ["corpus,licence_class,licence_field_value,artefacts,yaml_front_matter,licence_mentions,card_urls,"
            "distinct_hosts,record_governance_columns,footer_metadata_keys,n_gaps"]
    for c in res["corpora"]:
        rows.append(",".join(str(x).replace(",", ";") for x in [
            c["corpus"], c["licence_class"], c["licence_field_value"], "|".join(c["artefacts_present"]),
            c.get("card_has_yaml_front_matter"), c.get("licence_mention_n", 0), c.get("card_url_n", 0),
            c.get("card_distinct_hosts", 0), ";".join(c["record_governance_columns"])[:120],
            len(c["record_parquet_metadata_keys"]), len(dis[c["corpus"]])]))
    (PROC / "EXP0048_governance_presence.csv").write_text("\n".join(rows) + "\n", encoding="utf-8", newline="")
    print(json.dumps({"rule_1": t1, "classes": dict(classes), "rule_2": t2, "rule_3": t3,
                      "verdict": res["verdict"]}, ensure_ascii=False))
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
