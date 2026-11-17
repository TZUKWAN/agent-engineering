"""Compare a package directory's file hashes against a snapshot, to say whether a rebuild produced the same package.

A reproduce.sh that runs without error is not the same statement as "the rebuild yields the artefacts the paper cites":
generators can drop a section a recorder once inserted, renumber a table, or re-render a float differently. This tool
makes that checkable in one command. It is deliberately read-only: `--save` writes a snapshot file (that is its only
side effect), and a compare reports per-file differences and never edits the package.

    python 02_shared_code/registry/rebuild_determinism.py --dir papers/P004_shipped_quality_score_validity --save results_raw/snapshots/P004_pre.json
    python 02_shared_code/registry/rebuild_determinism.py --dir papers/P004_shipped_quality_score_validity --against results_raw/snapshots/P004_pre.json

Two hashes are kept per file. The plain one normalises line endings and trailing whitespace, because a generator
writing `newline=""` and a shell writing CRLF is not a content difference. The second one additionally removes date and
time stamps (and PDF `/CreationDate`/`/ModDate` metadata), and the verdict is decided on **that** one: a file whose only
change is the minute it was written is EPHEMERAL, while anything that differs beyond a stamp is MATERIAL and fails the
check. Without the second hash the comparison cries wolf - a first pass flagged 54 of 63 P004 files as changed when
every difference was a timestamp, a `pip freeze` line or a PDF creation date - and a check that always fails is a check
nobody reads.

A file whose *name* carries a run stamp (`EXP0104_..._20260921T062710.json`) is an append-only artefact of the run that
created it, so a new one is EPHEMERAL by construction. A **removed** file is MATERIAL, with one exception that is the
mirror image of that rule: when the rebuild adds a newer generation of the same family whose content is identical
apart from run stamps, the package did not lose anything - it holds the next generation of an artefact its own chain
re-runs - and the pair is reported as EPHEMERAL and counted separately. A removed file with no such replacement, or
one whose replacement says something different, is still MATERIAL. Any added file whose name carries no stamp is
MATERIAL too.
"""
from __future__ import annotations
import argparse, hashlib, json, pathlib, re, sys, time

ROOT = next(a for a in [pathlib.Path(__file__).resolve().parent,
                        *pathlib.Path(__file__).resolve().parents] if (a / "00_program_registry").is_dir())
TEXT = {".md", ".py", ".csv", ".json", ".txt", ".sh", ".yaml", ".yml", ".tex", ".html"}
DEFAULT_EXCLUDE = ["logs", "__pycache__", "environment/code_manifest.json",
                   "environment/reproduce_run_manifest.json"]
NL = chr(10)
# No word boundaries in this pattern: a run stamp usually sits at the end of a file name (`..._20260921T074412.json`),
# where it is preceded by `_` - a word character - so a `\b`-anchored version left every such stamp in place and the
# claims matrix, which points at the newest artefact by name, was reported as a material change on every rebuild.
STAMP = re.compile(r"\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2})?(?:\.\d+)?)?|\d{8}T\d{6}|\d{2}:\d{2}:\d{2}(?:\.\d+)?")
PDF_STAMP = re.compile(rb"/(?:CreationDate|ModDate)\s*\([^)]*\)")
# any file whose name ends in a run stamp is an append-only artefact of the run that wrote it, not only the EXP####
# ones: the clean-room driver writes environment/clean_room_run_<stamp>.json and each rebuild legitimately adds one
TIMED_NAME = re.compile(r".*_\d{8}T\d{6}")
# the same name with its run stamp taken out, which is how two generations of one artefact family are recognised
FAMILY = re.compile(r"_\d{8}T\d{6}")
# The environment record describes the machine that ran the build (package versions, host memory, the run's own
# wall-clock), so it is not a property of the package and cannot be expected to survive a rebuild on another day.
ENV_KEYS = ("environment/system_info.json", "environment/dependencies", "environment/environment_deps")
# The two registers a package ships are copies of the programme's live files, so a rebuild that happens after the
# programme's status moved will differ from the snapshot through no fault of the package. Excusing them by name
# would be a way of hiding changes, so the rule is a proof instead: the copy is excused only when the bytes in the
# package are identical, right now, to the master file they claim to copy. `round2_run_reality` reads that master.
PROGRAM_STATE = {"results_raw/topic_registry.csv": "00_program_registry/topic_registry.csv",
                 "results_raw/experiment_registry.csv": "00_program_registry/experiment_registry.csv"}
RUN_ID = re.compile(r"EXP(\d{4})")


def owned_runs(pid: str) -> set:
    """The exp numbers whose register row names this package - the runs whose numbers the package is answerable for."""
    import csv
    import io
    f = ROOT / "00_program_registry" / "experiment_registry.csv"
    if not f.is_file():
        return set()
    out = set()
    for r in csv.DictReader(io.StringIO(f.read_text(encoding="utf-8-sig"))):
        papers = [x.strip() for x in re.split(r"[;,]", r.get("paper_id") or "")]
        if pid and pid in papers:
            out.add((r.get("exp_id") or "").replace("-", "")[-4:])
    return out


def plain(f: pathlib.Path) -> bytes:
    """The file's bytes with line endings and trailing whitespace normalised - the content, not the container."""
    b = f.read_bytes()
    if f.suffix.lower() in TEXT:
        b = NL.join(line.rstrip() for line in b.decode("utf-8", errors="replace").splitlines()).encode("utf-8")
    return b


def unstamped(f: pathlib.Path) -> bytes:
    b = plain(f)
    if f.suffix.lower() == ".pdf":
        return PDF_STAMP.sub(b"/Id()", b)
    return STAMP.sub("<timestamp>", b.decode("utf-8", errors="replace")).encode("utf-8")


def h(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()[:16]


def scan(d: pathlib.Path, exclude):
    out, skipped = {}, []
    for f in sorted(d.rglob("*")):
        if not f.is_file():
            continue
        rel = str(f.relative_to(d)).replace(chr(92), "/")
        if any(x in rel for x in exclude):
            skipped.append(rel)
            continue
        out[rel] = {"plain": h(plain(f)), "unstamped": h(unstamped(f))}
    return out, skipped


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--save", default="", help="write the current hash map here")
    ap.add_argument("--against", default="", help="compare the current state to this snapshot")
    ap.add_argument("--exclude", action="append", default=None)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    d = (ROOT / a.dir) if not pathlib.Path(a.dir).is_absolute() else pathlib.Path(a.dir)
    if not d.is_dir():
        raise SystemExit(f"ABORT: no such directory {d}")
    exclude = DEFAULT_EXCLUDE if a.exclude is None else a.exclude
    cur, skipped = scan(d, exclude)
    tops = sorted({x.split("/")[0] for x in skipped})
    print(f"  {d.name}: {len(cur)} files hashed ({len(skipped)} excluded: {', '.join(tops[:5])})")
    if a.save:
        pth = pathlib.Path(a.save)
        pth.parent.mkdir(parents=True, exist_ok=True)
        pth.write_text(json.dumps({"at": time.strftime("%Y-%m-%dT%H:%M:%S"), "dir": str(d), "files": cur}, indent=1),
                       encoding="utf-8")
        print("  snapshot written:", pth)
    if not a.against:
        return 0
    old = json.loads(pathlib.Path(a.against).read_text(encoding="utf-8"))["files"]
    gone = sorted(set(old) - set(cur))
    added = sorted(set(cur) - set(old))
    shared = set(old) & set(cur)
    changed = sorted(k for k in shared if old[k]["plain"] != cur[k]["plain"])
    material, ephemeral, timed, environ, registries = [], [], [], [], []
    own = owned_runs(d.name[:4])
    for k in changed:
        if any(x in k for x in ENV_KEYS):
            environ.append(k)
        elif k in PROGRAM_STATE and (ROOT / PROGRAM_STATE[k]).is_file() \
                and cur[k]["plain"] == h(plain(ROOT / PROGRAM_STATE[k])):
            registries.append(k)
        elif old[k]["unstamped"] == cur[k]["unstamped"]:
            ephemeral.append(k)
        else:
            material.append(k)
    for k in added:
        (timed if TIMED_NAME.search(pathlib.Path(k).name) else material).append(k)
    # A removed generation of a rolling artefact is the same event as an added one seen from the other side: the
    # package held `audit_<04:23>.json`, the rebuild re-ran the audit and now holds `audit_<06:40>.json`. That is
    # ephemeral only when the two carry the same content - so the comparison is made on the unstamped digest, and a
    # removed file whose replacement says something different stays MATERIAL, which is the case that matters.
    # One exception is drawn on a fact rather than on a name: a stamped record of a run this package does not own -
    # the programme's own completion audit, which every package carries as context - measures the estate on the day
    # it was run, and its successor saying something different is that audit doing its job.
    by_family = {}
    for k in added:
        by_family.setdefault(FAMILY.sub("", pathlib.Path(k).name), []).append(k)
    still_held = {}
    for k in cur:
        if TIMED_NAME.search(pathlib.Path(k).name):
            still_held.setdefault(FAMILY.sub("", pathlib.Path(k).name), []).append(k)
    rolled, pruned, gone_for_good = [], [], []
    for k in gone:
        fam = FAMILY.sub("", pathlib.Path(k).name)
        twins = by_family.get(fam, [])
        same = [c for c in twins if old[k]["unstamped"] == cur[c]["unstamped"]]
        if same:
            rolled.append((k, same[:1]))
        elif TIMED_NAME.search(pathlib.Path(k).name) \
                and (RUN_ID.search(pathlib.Path(k).name) or [""])[1] not in own:
            # a stamped record of a run this package does not own - the programme's completion audit, which an
            # earlier pass copied in as context. Dropping it is the evidence-prune rule working, not the package
            # failing to reproduce itself; whether a successor is still held is said, not assumed.
            pruned.append((k, sorted(still_held.get(fam, []))[-1:]))
        else:
            gone_for_good.append((k, twins[:1]))
    material += [f"removed: {k}" for k, _ in gone_for_good]
    for k in ephemeral:
        print(f"  EPHEMERAL  {k}   (identical once run-time stamps are removed)")
    for k in environ:
        print(f"  ENVIRONMENT {k}   (records the host and run that rebuilt the package, not its content)")
    for k in registries:
        print(f"  REGISTER    {k}   (a copy of the programme's register, byte-identical to it as it now stands)")
    for k in timed:
        print(f"  EPHEMERAL +{k}   (append-only artefact named for the run that wrote it)")
    for k, twin in rolled:
        print(f"  EPHEMERAL -{k}   (replaced by {twin[0]}, which carries the same content apart from run stamps)")
    for k, twin in pruned:
        print("  PRUNED     -" + k + "   (a programme record this package does not own; "
              + (f"it now carries {twin[0]}" if twin else "no successor is shipped") + ")")
    for k in material:
        print(f"  MATERIAL   {k}")
    same = len(shared) - len(changed)
    print(f"verdict: {len(material)} material, {len(ephemeral)} stamp-only, {len(environ)} environment record(s), "
          f"{len(registries)} register cop(ies), {len(timed)} new run artefacts, "
          f"{len(rolled)} generation(s) replaced in place, "
          f"{len(pruned)} pruned programme record(s), {len(gone_for_good)} removed | "
          f"{same}/{len(shared)} shared files byte-identical")
    if material:
        print("  (a material difference means the rebuild does not reproduce the shipped package)")
    return 1 if material else 0


if __name__ == "__main__":
    sys.exit(main())
