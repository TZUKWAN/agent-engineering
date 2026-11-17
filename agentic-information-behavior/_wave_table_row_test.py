"""Scratch test: does the rebuilt battery-table reader produce a row with a value for every wave package?

The factory used to write four-byte CSVs for ten tables across thirteen packages because the reader understood
only one artefact shape per step. This exercises `battery_step_rows` against the real artefacts of all three waves
before any package is rebuilt, so the fix is proved on the data rather than on a rebuild log.
"""
import importlib
import sys

sys.path.insert(0, "02_shared_code/package_factory")
import wave_package as WP  # noqa: E402

WAVES = {"wave1": "topic_designs_wave1", "wave2": "topic_designs_wave2", "wave3": "topic_designs_wave3"}
bad = []
for wname, mod in WAVES.items():
    WP.TD = importlib.import_module(mod)
    for topic in list(getattr(WP.TD, "RUNNABLE", WP.TD.DESIGNS)):
        B, BS = WP.battery(topic), WP.battery_shared()
        if not B:
            print(f"{wname}/{topic}: NO BATTERY BLOCK (reader returned empty)")
            bad.append(f"{wname}/{topic}")
            continue
        line = []
        for name in WP.BATTERY_TABLES:
            try:
                rows = WP.battery_step_rows(name, B, BS)
            except SystemExit as e:
                print(f"{wname}/{topic} {name}: SystemExit {e}")
                bad.append(f"{wname}/{topic}/{name}")
                continue
            df_ok = bool(rows) and any(str(v).strip() not in ("", "None", "nan") for r in rows for v in r.values())
            na = any(isinstance(r, dict) and "applicability" in r for r in rows)
            line.append(f"{name[6:-4]}={len(rows)}{'/NA' if na else ''}{'' if df_ok else '!EMPTY'}")
            if not df_ok:
                bad.append(f"{wname}/{topic}/{name}")
        print(f"{wname}/{topic}: " + " ".join(line))
print()
print("FAILURES:", bad or "none")
