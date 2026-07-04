#!/usr/bin/env python3
"""Plot the global response of a spin-wave-driven Hopfion run.

Reads a mumax3 ``table.txt`` (columns: t, mx, my, mz, E_total) and produces a
two-panel figure:
  (a) total energy E_total(t) — net energy injected by the spin-wave source,
  (b) net out-of-plane magnetization <m_z>(t) — global Hopfion response.

This is the lightweight analysis path: it needs only the plain-text table, no
OVF frames. For the spatial / trajectory analysis (centroid drift, R/r, Hall
angle) load the OVF series with the shared library — see README.

Usage:
    python3 analyze_energy.py                 # uses ./example_result
    python3 analyze_energy.py plane_wave_drive.out
"""

import os
import sys

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Shared analysis/plotting library (do NOT re-implement — project rule C-7).
SCRIPTS_DIR = "/mnt/d/Research/Hopfion/95_shared_scripts"
sys.path.insert(0, SCRIPTS_DIR)
try:
    from paper_style import setup_paper_style, save_paper_fig, COLORS

    HAVE_PAPER_STYLE = True
except Exception:  # graceful fallback if the shared module is unavailable
    HAVE_PAPER_STYLE = False
    COLORS = {"primary": "#1f77b4", "secondary": "#d62728"}


def load_table(table_path):
    """Return (t_ns, mz, E_total) arrays from a mumax3 table.txt."""
    t, mz, e = [], [], []
    with open(table_path) as fh:
        for line in fh:
            if line.startswith("#") or not line.strip():
                continue
            parts = line.split()
            # columns: t(s)  mx  my  mz  E_total(J)
            t.append(float(parts[0]) * 1e9)   # s -> ns
            mz.append(float(parts[3]))
            e.append(float(parts[4]))
    return np.array(t), np.array(mz), np.array(e)


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "example_result"
    here = os.path.dirname(os.path.abspath(__file__))
    if not os.path.isabs(out_dir):
        out_dir = os.path.join(here, out_dir)

    table_path = os.path.join(out_dir, "table.txt")
    if not os.path.isfile(table_path):
        sys.exit(f"[ERROR] table.txt not found: {table_path}")

    t, mz, e = load_table(table_path)
    de = (e - e[0]) * 1e18  # energy change relative to t=0, in aJ (1e-18 J)

    if HAVE_PAPER_STYLE:
        setup_paper_style()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.0, 3.0))

    ax1.plot(t, de, color=COLORS.get("primary", "#1f77b4"), lw=1.5)
    ax1.set_xlabel("Time (ns)")
    ax1.set_ylabel(r"$E_{\mathrm{total}} - E_0$ (aJ)")

    ax2.plot(t, mz, color=COLORS.get("secondary", "#d62728"), lw=1.5)
    ax2.set_xlabel("Time (ns)")
    ax2.set_ylabel(r"$\langle m_z \rangle$")

    fig.tight_layout()

    out_png = os.path.join(here, "example_result", "energy_evolution.png")
    if HAVE_PAPER_STYLE:
        try:
            save_paper_fig(fig, out_png)
        except Exception:
            fig.savefig(out_png, dpi=200, bbox_inches="tight")
    else:
        fig.savefig(out_png, dpi=200, bbox_inches="tight")

    print(f"[OK] {len(t)} time points, t = {t[0]:.3f}..{t[-1]:.3f} ns")
    print(f"[OK] dE_total = {de[-1]:+.4f} aJ over the run")
    print(f"[OK] figure -> {out_png}")


if __name__ == "__main__":
    main()
