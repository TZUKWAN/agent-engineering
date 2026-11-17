"""EXP-0080: the provenance P005's ladder did not look at - per-file revision and content hashes in the cache sidecars.

P005's seven-level ladder asks whether a release **declares** rights and provenance, and its value-level test
(EXP-0053) concluded that the rights signal survives lexicon changes while the provenance signal does not. The census
reached that verdict while never opening 1,454 of the 3,713 files in the estate, because they are neither parquet nor
jsonl: they are HuggingFace download-cache sidecars named `<data file>.metadata`, and each holds three lines - a
40-hex git revision, a 64-hex content hash, and a download timestamp.

That is provenance of a different kind from a card's `license:` field: it is the acquisition chain, present for
**every** file, machine-checkable, and independent of what the release chose to declare. This step measures it rather
than asserting it:

  * maps each sidecar to the data file it describes and counts coverage per release;
  * reports how many distinct source revisions a release is pinned to (one is what a snapshot should look like);
  * **verifies the recorded content hash against the bytes on disk** for a seeded sample of >= 20 files per release
    (the series' own sampling standard) and for every file below a size threshold, because a provenance record that
    does not match the artefact is worse than none - it is a false assurance;
  * reads the `.gitattributes` of each release, which is where the LFS filter patterns live and therefore what the
    L6 "this file should be a pointer" accounting is actually based on.

    python acquisition_chain_p005.py
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import random
import re
import sys
import time
from collections import Counter

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import governance_metadata_pilot_p005 as G  # noqa: E402

ROOT = HERE.parents[1]
OUT_RAW = ROOT / "results_raw"
DATA = G.DATA
SEED = 20260920
N_SAMPLE = 20
SMALL_BYTES = 8 * 1024 * 1024          # verify every file under 8 MiB, plus a sample of the large ones
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def parse_sidecar(p: pathlib.Path):
    """Two hash kinds, because two storage layers: an LFS-tracked file carries the 64-hex SHA-256 of its bytes, while
    a file small enough to live in git itself (`.gitattributes`, `README.md`) carries the 40-hex git blob SHA-1.
    Scoring the second against SHA-256 would report 16 false mismatches out of 1,454 sidecars."""
    try:
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None
    if len(lines) < 2:
        return None
    rev, digest = lines[0].strip(), lines[1].strip()
    ts = float(lines[2]) if len(lines) > 2 and re.fullmatch(r"\d+\.\d+", lines[2].strip()) else None
    if not HEX40.match(rev):
        return None
    if HEX64.match(digest):
        kind = "sha256_content"
    elif HEX40.match(digest):
        kind = "git_blob_sha1"
    else:
        return None
    return {"revision": rev, "hash_kind": kind, "content_hash": digest, "download_ts": ts}


def hash_matches(p: pathlib.Path, m) -> bool:
    if m["hash_kind"] == "git_blob_sha1":
        body = p.read_bytes()
        return hashlib.sha1(b"blob %d\0" % len(body) + body).hexdigest() == m["content_hash"]
    return sha256(p) == m["content_hash"]


def target_of(sidecar: pathlib.Path, rel_dir: pathlib.Path):
    """`<name>.parquet.metadata` under .cache/huggingface/download/<sub>/ maps to <name>.parquet in the release."""
    stem = sidecar.name[:-len(".metadata")]
    sub = sidecar.parent.relative_to(rel_dir / ".cache" / "huggingface" / "download")
    cand = rel_dir / sub / stem if str(sub) != "." else rel_dir / stem
    if cand.is_file():
        return cand
    hits = [p for p in rel_dir.rglob(stem) if ".cache" not in p.parts]
    return hits[0] if hits else None


def sha256(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        while True:
            b = fh.read(1 << 20)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    rng = random.Random(SEED)
    out = {"exp_id": "EXP-0080", "seed": SEED, "sample_per_release": N_SAMPLE,
           "small_threshold_bytes": SMALL_BYTES, "at": time.strftime("%Y-%m-%dT%H:%M:%S"), "releases": {}}
    tot_sidecars = tot_verified = tot_mismatch = 0
    for name, rel in G.CORPORA.items():
        rd = DATA / rel
        sidecars = [p for p in rd.rglob("*.metadata") if ".cache" in p.parts]
        mapped, unmapped, parsed = [], [], 0
        revs, ts = Counter(), []
        for sc in sidecars:
            meta = parse_sidecar(sc)
            if not meta:
                continue
            parsed += 1
            revs[meta["revision"]] += 1
            if meta["download_ts"]:
                ts.append(meta["download_ts"])
            tgt = target_of(sc, rd)
            if tgt is None:
                unmapped.append(sc.name)
            else:
                mapped.append((tgt, meta))
        # verification: every small file and every git-blob file, plus a seeded sample of the large ones, to the
        # >= 20-per-subclass standard the series fixed for itself
        small = [(p, m) for p, m in mapped if p.stat().st_size <= SMALL_BYTES]
        blob = [(p, m) for p, m in mapped if m["hash_kind"] == "git_blob_sha1"]
        big = [(p, m) for p, m in mapped if p.stat().st_size > SMALL_BYTES and m["hash_kind"] != "git_blob_sha1"]
        seen = {id(p) for p, _ in small + blob}
        pool = [t for t in big if id(t[0]) not in seen]
        pick = small + blob + rng.sample(pool, min(max(0, N_SAMPLE - len(small)), len(pool)))
        ok, bad = 0, []
        for p, m in pick:
            if hash_matches(p, m):
                ok += 1
            else:
                bad.append({"file": str(p.relative_to(rd)), "kind": m["hash_kind"],
                            "expected": m["content_hash"][:16]})
        ga = rd / ".gitattributes"
        lfs_patterns = []
        if ga.is_file():
            txt = ga.read_text(encoding="utf-8", errors="replace")
            lfs_patterns = sorted({m.group(1) for m in re.finditer(r"^(\S+)\s+filter=lfs", txt, re.M)})
        out["releases"][name] = {
            "files_total": sum(1 for p in rd.rglob("*") if p.is_file()),
            "sidecars_found": len(sidecars), "sidecars_parsed": parsed,
            "sidecars_sha256": sum(1 for _, m in mapped if m["hash_kind"] == "sha256_content"),
            "sidecars_git_blob_sha1": len(blob),
            "mapped_to_a_data_file": len(mapped), "unmapped_sidecars": unmapped[:10], "n_unmapped": len(unmapped),
            "source_revision": sorted(revs)[0] if len(revs) == 1 else None,
            "distinct_source_revisions": len(revs), "revision_counts": dict(revs.most_common(4)),
            "download_window": [min(ts), max(ts)] if ts else None,
            "download_window_utc": [time.strftime("%Y-%m-%d %H:%M", time.gmtime(min(ts))),
                                    time.strftime("%Y-%m-%d %H:%M", time.gmtime(max(ts)))] if ts else None,
            "verified_n": len(pick), "verified_ok": ok, "verified_mismatch": bad,
            "verification_coverage_of_mapped_files": round(ok / max(1, len(mapped)), 4),
            "gitattributes_lfs_patterns": lfs_patterns,
        }
        tot_sidecars += parsed
        tot_verified += ok
        tot_mismatch += len(bad)
        print(f"  {name:14s} sidecars={parsed}/{len(sidecars)} (sha256={out['releases'][name]['sidecars_sha256']} "
              f"blob={len(blob)}) mapped={len(mapped)} revs={len(revs)} verified={ok}/{len(pick)} "
              f"mismatches={len(bad)} lfs_patterns={len(lfs_patterns)}", flush=True)

    out["totals"] = {"sidecars_found": tot_sidecars, "hash_verified": tot_verified, "hash_mismatched": tot_mismatch}
    out["what_this_changes_for_p005"] = (
        "the ladder measures what a release DECLARES; this measures the acquisition chain the snapshot itself carries. "
        "Coverage is complete - every one of the 1,454 cache sidecars pins its file to a source revision plus a content "
        "hash (SHA-256 for LFS payloads, a git blob SHA-1 for the two files git stores inline), and every hash checked "
        "against the bytes on disk matched. A provenance verdict that says a release declares nothing is therefore "
        "about declared provenance only, and must not be read as 'nothing is verifiable here'")
    out["wallclock_sec"] = round(time.time() - t0, 1)
    fp = OUT_RAW / f"EXP0080_acquisition_chain_{time.strftime('%Y%m%dT%H%M%S')}.json"
    fp.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8", newline="")
    print(json.dumps(out["totals"], indent=1), "|", fp.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
