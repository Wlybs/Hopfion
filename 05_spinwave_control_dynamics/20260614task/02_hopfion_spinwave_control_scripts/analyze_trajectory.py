#!/usr/bin/env python3
"""Spatial response of a spin-wave-driven Hopfion from the OVF series.

Tracks the Hopfion with the **phase-correlation** method: each frame is
registered against the t=0 frame in Fourier space to recover the rigid
translation of the whole texture. This is robust to the propagating spin-wave
background, unlike a mass-weighted centroid. The method is ported from the
GitHub source of Zhang et al., Sci. Adv. 9, eade7439 (2023) (track.py), adapted
to a ferromagnet and refactored into the shared library.

Produces a two-panel figure:
  (a) Hopfion displacement Delta x/y/z(t) relative to t=0,
  (b) large radius R(t) and tube radius r(t).

Requires the OVF frames (50 ps spacing).

Usage:
    python3 analyze_trajectory.py                 # uses ./example_result
    python3 analyze_trajectory.py plane_wave_drive.out
"""

import os
import sys

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Shared analysis/plotting library — these routines must NOT be re-implemented.
SCRIPTS_DIR = "/mnt/d/Research/Hopfion/95_shared_scripts"
sys.path.insert(0, SCRIPTS_DIR)
from hopfion_analysis import extract_trajectory_phase_correlation, extract_Rr_series

try:
    from paper_style import setup_paper_style, save_paper_fig, COLORS

    HAVE_PAPER_STYLE = True
except Exception:
    HAVE_PAPER_STYLE = False
    COLORS = {"primary": "#1f77b4", "secondary": "#d62728", "tertiary": "#2ca02c"}

DT_NS = 0.05          # OVF autosave interval (50 ps), matches the .mx3 scripts
EXCLUDE_BOUNDARY = 5  # drop the 5-cell absorbing layer before registration


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "example_result"
    here = os.path.dirname(os.path.abspath(__file__))
    if not os.path.isabs(out_dir):
        out_dir = os.path.join(here, out_dir)

    if not os.path.isfile(os.path.join(out_dir, "m000000.ovf")):
        sys.exit(f"[ERROR] no OVF frames in {out_dir} (need m000000.ovf ...)")

    # Phase-correlation tracking: shift is already relative to the t=0 frame.
    traj = extract_trajectory_phase_correlation(
        out_dir, dt_ns=DT_NS, exclude_boundary=EXCLUDE_BOUNDARY, verbose=False
    )
    rr = extract_Rr_series(out_dir, dt_ns=DT_NS, verbose=False)

    t = np.array([p[0] for p in traj])
    disp = np.array([p[1] for p in traj])     # (N, 3) in nm, relative to t=0

    t_rr = np.array([p[0] for p in rr])
    R = np.array([p[1] for p in rr])
    r = np.array([p[2] for p in rr])

    if HAVE_PAPER_STYLE:
        setup_paper_style()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.0, 3.0))

    ax1.plot(t, disp[:, 0], "-o", ms=3, color=COLORS.get("primary", "#1f77b4"), label=r"$\Delta x$")
    ax1.plot(t, disp[:, 1], "-s", ms=3, color=COLORS.get("secondary", "#d62728"), label=r"$\Delta y$")
    ax1.plot(t, disp[:, 2], "-^", ms=3, color=COLORS.get("tertiary", "#2ca02c"), label=r"$\Delta z$")
    ax1.set_xlabel("Time (ns)")
    ax1.set_ylabel("Hopfion displacement (nm)")
    ax1.legend(frameon=False, fontsize=8)

    ax2.plot(t_rr, R, "-o", ms=3, color=COLORS.get("primary", "#1f77b4"), label=r"$R$ (large)")
    ax2.plot(t_rr, r, "-s", ms=3, color=COLORS.get("secondary", "#d62728"), label=r"$r$ (tube)")
    ax2.set_xlabel("Time (ns)")
    ax2.set_ylabel("Radius (nm)")
    ax2.legend(frameon=False, fontsize=8)

    fig.tight_layout()

    out_png = os.path.join(here, "example_result", "spatial_response.png")
    if HAVE_PAPER_STYLE:
        try:
            save_paper_fig(fig, out_png)
        except Exception:
            fig.savefig(out_png, dpi=200, bbox_inches="tight")
    else:
        fig.savefig(out_png, dpi=200, bbox_inches="tight")

    print(f"[OK] {len(t)} frames, t = {t[0]:.3f}..{t[-1]:.3f} ns (phase-correlation)")
    print(f"[OK] final displacement = ({disp[-1,0]:+.3f}, {disp[-1,1]:+.3f}, {disp[-1,2]:+.3f}) nm")
    print(f"[OK] R: {R[0]:.3f} -> {R[-1]:.3f} nm | r: {r[0]:.3f} -> {r[-1]:.3f} nm")
    print(f"[OK] figure -> {out_png}")


if __name__ == "__main__":
    main()
