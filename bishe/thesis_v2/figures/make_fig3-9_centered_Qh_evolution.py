"""Generate fig3-9 — Hopf index Q_H time series for centered stability.

Data source: /mnt/d/Research/Hopfion/20260105_frustrated_fm/centered_stability_test/qh_timeseries.npy
Shape (3, 21): Ku0, Ku10k, Ku50k, 21 snapshots at dt=0.05ns (0 to 1 ns).

Run:
    /mnt/d/Research/Hopfion/hopfion/bin/python make_fig3-9_centered_core_count.py
"""
import os
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib import font_manager

_FONT_CANDIDATES = [
    "/mnt/c/Windows/Fonts/simsun.ttc",
    "/mnt/c/Windows/Fonts/simhei.ttf",
    "/mnt/c/Windows/Fonts/msyh.ttc",
]
for _fp in _FONT_CANDIDATES:
    if os.path.exists(_fp):
        font_manager.fontManager.addfont(_fp)
        _name = font_manager.FontProperties(fname=_fp).get_name()
        mpl.rcParams["font.sans-serif"] = [_name] + mpl.rcParams["font.sans-serif"]
        mpl.rcParams["font.family"] = "sans-serif"
        break
mpl.rcParams["axes.unicode_minus"] = False
mpl.rcParams["mathtext.fontset"] = "stix"

FIG_DIR = "/mnt/d/Research/Hopfion/bishe/thesis_v2/figures"
OUT = os.path.join(FIG_DIR, "fig3-9_centered_Qh_evolution.png")
DATA = "/mnt/d/Research/Hopfion/20260105_frustrated_fm/centered_stability_test/qh_timeseries.npy"

qh = np.load(DATA)
t = np.linspace(0, 1.0, qh.shape[1])

SERIES = [
    (0, r"$K_{u1} = 0$",                    "o", "#1f77b4", "white"),
    (1, r"$K_{u1} = 10\,\mathrm{kJ/m^3}$",  "s", "#B22222", "#B22222"),
    (2, r"$K_{u1} = 50\,\mathrm{kJ/m^3}$",  "^", "#003F7F", "#003F7F"),
]

fig, ax = plt.subplots(figsize=(8, 5))
fig.patch.set_facecolor("white")

for idx, label, marker, edge, face in SERIES:
    ax.plot(t, qh[idx],
            linestyle="-", color=edge, linewidth=1.0, alpha=0.8)
    ax.plot(t, qh[idx],
            marker=marker, linestyle="none",
            markerfacecolor=face, markeredgecolor=edge,
            markeredgewidth=1.0, markersize=6,
            label=label)

ax.axhline(1.0, color="gray", linestyle="--", linewidth=0.7, alpha=0.5)

ax.grid(True, linestyle="-", linewidth=0.4, alpha=0.18, color="gray")
ax.set_xlabel(r"时间 $t$ (ns)", fontsize=15)
ax.set_ylabel(r"Hopf 指数 $Q_H$", fontsize=15)
ax.set_ylim(0.99, 1.005)
ax.tick_params(labelsize=13, direction="in", length=4,
               top=True, right=True, which="major")
ax.tick_params(direction="in", length=2.5,
               top=True, right=True, which="minor")
ax.minorticks_on()
ax.set_facecolor("white")
for spine in ax.spines.values():
    spine.set_visible(True)
    spine.set_color("black")
    spine.set_linewidth(0.9)

handles, labels = ax.get_legend_handles_labels()
fig.legend(handles, labels, loc="upper center",
           bbox_to_anchor=(0.5, 0.995), ncol=3, frameon=False,
           fontsize=13, handlelength=1.8, columnspacing=2.0,
           handletextpad=0.5)

fig.subplots_adjust(left=0.11, right=0.97, top=0.90, bottom=0.12)
fig.savefig(OUT, dpi=300, bbox_inches="tight", facecolor="white")
print(f"[OK] saved: {OUT}")
