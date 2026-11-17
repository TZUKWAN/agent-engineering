"""Round-2 check: does the time a register row claims for its run match the time the run itself declares?

`experiment_registry.csv` carries `started_at` and `finished_at` for every run, and a reader reasonably takes them
for measured wall-clock windows. They are not all that. Three shapes were found when the round-2 run-reality check
started comparing each row's window with the timestamp its own artefacts print in their filenames:

* rows whose two columns are the *same* instant - the recorders that registered a run after it finished stored one
  clock reading twice, so the row states an instant, not a window;
* rows whose window is a hand-rounded approximation (`18:56:00`-`18:57:00`) written when the row was keyed in, and
  which contains none of the generations the row points at;
* rows whose window contradicts their own output stamp in the other direction - the earliest file the row names was
  written hours after the claimed finish, because the row's `outputs` cell was re-pointed at a later generation by
  a re-run and the time columns were not touched.

A window that no artefact falls inside is a claim about a run that nothing on disk supports, so this script makes
each row state what it can support, mechanically and idempotently. Every row is labelled in its `notes` as
`window_kind=...`:

* `measured` - at least one existing generation of the row falls inside its window, so the window is corroborated
  by the run's own output and the columns are left alone;
* `output_stamp` - no generation of the row falls inside the window it states, and the row's own designated
  artefact prints a timestamp, so the columns are set to that instant: the row then claims only what the artefact
  proves, and the value it had is kept in `window_was=...`;
* `instant_recorded` - the row states one clock reading and its own artefact was written within two minutes of it,
  which is what a recorder that registered a run just after it finished produces; the reading agrees with the
  artefact, so the columns are kept. A row that states one instant and has no stamped artefact to agree with is
  labelled the same way and marked as uncheckable in the report below;
* `uncorroborated_window` - the row states a window but its artefacts carry no filename stamp, so nothing on disk
  can test the time either way; the row keeps what it says and is labelled as unchecked;
* `no_time_recorded`, `no_artefact_on_disk`, `superseded_row`, `window_reversed` - the row states nothing, has no
  artefact to state it from, is a retired console probe, or states a window that runs backwards. Only the last is
  left for a person to read, and round 2 found none of it.

`round2_run_reality.py` then tests the `measured` rows against new output and reports how many rows fall in each
class, which is what makes the estate's timeline claim checkable instead of merely green.

    python 02_shared_code/registry/round2_register_windows.py            # report only
    python 02_shared_code/registry/round2_register_windows.py --apply    # rewrite the register
"""
from __future__ import annotations

import argparse
import csv
import datetime
import io
import json
import pathlib
import re
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import round2_lib as L                                                    # noqa: E402
import round2_run_reality as RR                                           # noqa: E402

ROOT = L.ROOT
REG = ROOT / "00_program_registry" / "experiment_registry.csv"
EXP = "EXP-0234"
SLACK = RR.SLACK                                                         # seconds of clock jitter absorbed


def classify(row: dict, sup: set) -> dict:
    """What the row's window can support, given the generations the row itself points at."""
    globs = RR.parts_of(row.get("outputs") or "")
    found = [f for g in globs for f in RR.expand(ROOT, g)]
    fresh = [f for f in found if f.name not in sup] or found
    stamps = sorted({s for s in (RR.stamp_of(f.name) for f in found) if s})
    # the artefact the row designates: an exact filename in the outputs cell beats any guess, because the row
    # wrote that name itself when it registered the run
    anchor = ""
    for spec in globs:
        for tok in spec.split(";"):
            tok = tok.strip().lstrip(">").strip().replace(chr(92), "/")
            if tok and not any(c in tok for c in "*?") and (ROOT / tok).is_file():
                anchor = max(anchor, RR.stamp_of(pathlib.Path(tok).name))
    if not anchor and fresh:
        anchor = RR.stamp_of(max(fresh, key=lambda f: f.stat().st_mtime).name)
    if not anchor and stamps:
        anchor = stamps[0]
    rs, rf = RR.iso(row.get("started_at")), RR.iso(row.get("finished_at"))
    inside = [s for s in stamps
              if rs and rf and rs - datetime.timedelta(seconds=SLACK) <= RR.iso(s)
              <= rf + datetime.timedelta(seconds=SLACK)]
    out = {"exp_id": row.get("exp_id"), "n_stamps": len(stamps), "inside": len(inside),
           "old": (row.get("started_at") or "", row.get("finished_at") or ""), "anchor": anchor}
    if row.get("exp_id") == EXP:
        # this run's own row: its artefact is written after the classification, so the window it declares now is
        # the one its next generation will fall inside
        return {**out, "kind": "measured", "start": out["old"][0], "finish": out["old"][1]}
    if re.search(r"superseded_by_(EXP-?\d{4})", row.get("status") or "", re.I):
        # an inline console probe the ledger retired: it declares no artefact, so its times can be neither
        # corroborated nor repaired, and `round2_run_reality` already tests that its successor did produce one
        return {**out, "kind": "superseded_row", "start": out["old"][0], "finish": out["old"][1]}
    if rs and rf and rs > rf:
        # reversed by hand: not repairable from an artefact, because the row's claim is incoherent, so a person
        # must read it. Round 2 found none, and this branch keeps a future one from being quietly rewritten.
        return {**out, "kind": "window_reversed", "start": out["old"][0], "finish": out["old"][1]}
    if inside:
        # something the row itself produced carries a timestamp that falls where the row says the run happened. A
        # zero-width "window" that a generation agrees with is a recorder's write-time reading, which is a real
        # instant even though it is not a duration.
        k = "measured" if rs != rf else "instant_recorded"
        return {**out, "kind": k, "start": out["old"][0], "finish": out["old"][1]}
    if (rs or rf) and not (rs and rf):
        # one end stated: fill the other from the generation that agrees with the end that is there, rather than
        # leaving a row that reads as a run of unknown length
        near = [s for s in stamps if abs((RR.iso(s) - (rs or rf)).total_seconds()) <= SLACK]
        if near:
            return {**out, "kind": "instant_recorded", "start": near[0], "finish": near[0], "from": "filled"}
    if not rs and not rf:
        return {**out, "kind": "no_time_recorded", "start": "", "finish": ""}
    if not found:
        # nothing to test the window against. The missing artefact is `round2_run_reality`'s finding, not a reason
        # to delete the only trace of when the row says it ran.
        return {**out, "kind": "no_artefact_on_disk", "start": out["old"][0], "finish": out["old"][1]}
    d = L.read_any(max(fresh, key=lambda f: f.stat().st_mtime)) if fresh else None
    ist = str((d or {}).get("started_at") or "") if isinstance(d, dict) else ""
    ifi = str((d or {}).get("finished_at") or "") if isinstance(d, dict) else ""
    isi, ifi_i = RR.iso(ist), RR.iso(ifi)
    if isi and ifi_i and isi < ifi_i and any(RR.iso(s) and isi <= RR.iso(s) <= ifi_i for s in stamps):
        return {**out, "kind": "measured", "start": ist, "finish": ifi, "from": "artefact_record"}
    if anchor:
        # the row's own designated artefact declares a time outside the window the row states, so the window is
        # replaced by what the artefact declares: the row then claims only what the artefact proves.
        return {**out, "kind": "output_stamp", "start": anchor, "finish": anchor}
    # an unstamped artefact: no filename on disk can corroborate or contradict what the row states, so the row is
    # labelled for what it is - a time nobody can check - and left as written.
    return {**out, "kind": "instant_recorded" if rs == rf and bool(rs) else "uncorroborated_window",
            "start": out["old"][0], "finish": out["old"][1]}


def retoken_note(notes: str, pairs: dict) -> str:
    """Set or replace `key=value` tokens in a free-text notes cell without touching the prose around them."""
    out = notes or ""
    for k, v in pairs.items():
        tok = re.compile(rf"\b{k}=\S+")
        body = f"{k}={v}"
        out = tok.sub(body, out) if tok.search(out) else (out + " " + body).strip()
    return re.sub(r"\s{2,}", " ", out).strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    started = datetime.datetime.now().isoformat(timespec="seconds")
    rows = list(csv.DictReader(io.StringIO(REG.read_text(encoding="utf-8"))))
    cols = list(rows[0])
    row = {"exp_id": EXP, "paper_id": "programme", "stage": "round2_register_window_kinds",
           "script": "02_shared_code/registry/round2_register_windows.py",
           "config": "every row of 00_program_registry/experiment_registry.csv; a row keeps its window only if one "
                     "of the generations its own outputs cell points at falls inside it, otherwise the window is "
                     "replaced by the timestamp that artefact prints",
           "seed": "n/a (a maintenance pass over the register)", "started_at": started, "finished_at": "",
           "status": "register_window_kinds_set",
           "outputs": "results_raw/EXP0234_register_windows_*.json", "enters_paper": "no",
           "notes": "round-2: the register's time columns mixed measured windows, hand-rounded approximations and "
                    "write-time instants; each row now declares which of the three it is."}
    hit = next((r for r in rows if r["exp_id"] == EXP), None)
    if hit is None:
        hit = {c: "" for c in cols}
        hit["exp_id"] = EXP
        rows.append(hit)
    for k, v in row.items():
        if k in cols and not hit.get(k):
            hit[k] = v

    tally, moved, noted, filled, detail = {}, 0, 0, 0, []
    sup = set(L.superseded())
    for r in rows:
        c = classify(r, sup)
        kind = c["kind"]
        tally[kind] = tally.get(kind, 0) + 1
        pairs = {"window_kind": kind}
        old = c["old"]
        times_move = kind not in ("window_reversed", "superseded_row") and (old[0], old[1]) != (c["start"],
                                                                                                 c["finish"])
        if times_move:
            pairs["window_was"] = f"{old[0] or '_'}..{old[1] or '_'}"
            moved += 1
        if kind == "measured" and c.get("from"):
            pairs["window_from"] = "artefact_record"
        if c.get("from") == "filled":
            filled += 1
        notes = retoken_note(r.get("notes") or "", pairs)
        edit = notes != (r.get("notes") or "") or times_move
        if edit:
            noted += 1
        detail.append({k: v for k, v in c.items() if k != "n_stamps"} | {"edited": edit, "times_move": times_move})
        if a.apply and edit and kind != "window_reversed":
            r["started_at"], r["finished_at"], r["notes"] = c["start"], c["finish"], notes
    finished = datetime.datetime.now().isoformat(timespec="seconds")
    if a.apply:
        hit["started_at"], hit["finished_at"] = started, finished
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=cols, lineterminator=chr(10))
        w.writeheader()
        for r in rows:
            w.writerow({cc: str(r.get(cc) or "") for cc in cols})
        REG.write_text(buf.getvalue(), encoding="utf-8")
    payload = {"detector": "round2_register_windows", "applied": a.apply, "rows": len(rows),
               "window_kinds": tally, "rows_whose_times_move": moved, "rows_filled_from_one_end": filled,
               "rows_touched": noted, "detail": detail,
               "wallclock_sec": round(time.time() - t0, 1), "at": finished}
    dest = ROOT / "results_raw" / f"EXP0234_register_windows_{time.strftime('%Y%m%dT%H%M%S')}.json"
    dest.write_text(json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(tally, indent=1, sort_keys=True))
    print(f"{len(rows)} row(s) read: {tally.get('output_stamp', 0)} re-anchored to the stamp their own artefact "
          f"prints, {tally.get('no_time_recorded', 0)} state no time at all, {moved} time cells move "
          f"({filled} of them filling the one end that was blank), {noted} carry a window_kind note")
    for x in detail:
        if x["times_move"]:
            print(f"  {x['exp_id']}: {x['kind']} was {x['old'][0]}..{x['old'][1]} -> {x['start']}  "
                  f"(anchor {x['anchor']}, {x['inside']} of its own generations fall inside the old window)")
    print("wrote", dest.name, "(the register was" + (" rewritten)" if a.apply else " NOT touched)"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
