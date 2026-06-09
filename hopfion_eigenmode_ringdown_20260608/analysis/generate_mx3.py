#!/usr/bin/env python3
"""Generate table-only uniform sinc ringdown Mumax3 scripts."""

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
sys.path.insert(0, str(REPO / "scripts"))

from resonance_analysis import generate_sinc_ringdown_mx3  # noqa: E402


def main():
    mx3_dir = ROOT / "mx3"
    mx3_dir.mkdir(exist_ok=True)
    for axis in ("x", "z"):
        out = mx3_dir / f"ringdown_sinc_B{axis}.mx3"
        generate_sinc_ringdown_mx3(
            out,
            drive_axis=axis,
            cutoff_ghz=2000.0,
            b0_t=0.005,
            t0_ps=2.37,
            run_ns=0.5,
            table_dt_ps=0.05,
        )
        print(out)


if __name__ == "__main__":
    main()
