"""Generate fig3-8_centered_z_drift.png — single panel, fig4-1 style.

Reads CSVs: centered_stability_Ku{0,10k,50k}.csv
Run:
    /mnt/d/Research/Hopfion/hopfion/bin/python make_fig3-8_centered_z_drift.py
"""
import os
import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib import font_manager

_FONT_CANDIDATES = [
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

FIG_DIR = "/mnt/d/Research/Hopfion/09_paper_thesis_talks/bishe/thesis_v2/figures"
OUT = os.path.join(FIG_DIR, "fig3-8_centered_z_drift.png")

SERIES = [
    ("Ku0",   "$K_{u1} = 0$",                    "o", "#1f77b4", "white"),
    ("Ku10k", "$K_{u1} = 10$ kJ/m$^3$",          "s", "#B22222", "#B22222"),
    ("Ku50k", "$K_{u1} = 50$ kJ/m$^3$",          "^", "#003F7F", "#003F7F"),
]


def load(tag):
    df = pd.read_csv(os.path.join(FIG_DIR, f"centered_stability_{tag}.csv"))
    df["dz_nm"] = df["z_nm"] - df["z_nm"].iloc[0]
    return df


fig, ax = plt.subplots(figsize=(8, 5))
fig.patch.set_facecolor("white")

peak = 0.0
for tag, label, marker, edge, face in SERIES:
    df = load(tag)
    peak = max(peak, float(df["dz_nm"].abs().max()))

if peak > 0 and peak < 1.0:
    k = int(np.floor(np.log10(peak)))
    scale = 10.0 ** k
    ylabel = rf"$\Delta z$ ($\times 10^{{{k}}}$ nm)"
else:
    scale = 1.0
    ylabel = r"$\Delta z$ (nm)"

for tag, label, marker, edge, face in SERIES:
    df = load(tag)
    ax.plot(df["t_ns"], df["dz_nm"] / scale,
            linestyle="-", color=edge, linewidth=1.0, alpha=0.8)
    ax.plot(df["t_ns"], df["dz_nm"] / scale,
            marker=marker, linestyle="none",
            markerfacecolor=face, markeredgecolor=edge,
            markeredgewidth=1.0, markersize=6,
            label=label)

ax.axhline(0, color="gray", linestyle="--", linewidth=0.8, alpha=0.5)
ax.grid(True, linestyle="-", linewidth=0.4, alpha=0.18, color="gray")
ax.set_xlabel(r"时间 $t$ (ns)", fontsize=15)
ax.set_ylabel(ylabel, fontsize=15)
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
