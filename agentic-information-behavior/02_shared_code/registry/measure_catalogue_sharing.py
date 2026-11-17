"""EXP-0150: how much of the tool catalogue's *text* is shared between the Toucan configs.

Why this is a programme-level measurement rather than one more step of one wave's battery: every package in this
programme reads the same three configs of the same release, and six of them report a "consistent across OSS, Qwen3 and
Kimi-K2" robustness result. That sentence means something different depending on whether the three configs were shown
different tool descriptions or the same ones three times, and until now no artefact said which. A per-wave battery
step would leave the wave-1 packages citing a number nobody measured.

The unit is a digest of one catalogue entry's description text, counted over a seeded sample of dev rows. Sharing is
not a leak - the split isolation is a separate check - it is about *independence of the material*: two configs whose
catalogues carry the same sentences are not two samples of catalogue text.

    python 02_shared_code/registry/measure_catalogue_sharing.py [--rows 12000]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = next(a for a in (HERE, *HERE.parents) if (a / "00_program_registry").is_dir())
sys.path.insert(0, str(ROOT / "02_shared_code" / "package_factory"))
import wave_lib as W                                              # noqa: E402
import exp_wave2_battery as B2                                    # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=12000)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    inner = B2.e19_description_duplication(a.rows)
    art = {"exp_id": "EXP-0150", "seed": W.SEED, "question": "how much catalogue description text is shared between "
                                                             "the configs this programme treats as separate?",
           "measurement": inner,
           "consequence_for_the_programme":
               "a per-config robustness result is reported as heterogeneity across the same instruments, not as "
               "replication on independent material, wherever the share below is high",
           "cited_by": "every wave package's limitations.md, through wave_package.limitations_md",
           "invocation": " ".join([sys.executable] + sys.argv),
           "run_cost": W.run_cost_row("EXP-0150", t0, int(inner.get("sample_rows") or 0), 0),
           "started_at": W.now(), "finished_at": W.now()}
    dest = W.write_raw("EXP-0150", "catalogue_sharing", art)
    print(json.dumps({k: inner.get(k) for k in ("distinct_descriptions_in_sample",
                                                "descriptions_in_more_than_one_config",
                                                "share_of_descriptions_shared_across_configs",
                                                "most_reused_description_row_count", "sample_rows")}, indent=1))
    print("wrote", dest.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
