"""Generate fig4-3_srcX_displacement.png — 4x1 vertical, fig4-1 style.

Reads cache: figures/fig5-3_srcX_cache.csv
Run:
    /mnt/d/Research/Hopfion/hopfion/bin/python make_fig4-3_srcX_displacement.py
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

CACHE = "/mnt/d/Research/Hopfion/09_paper_thesis_talks/bishe/thesis_v2/figures/fig5-3_srcX_cache.csv"
OUT   = "/mnt/d/Research/Hopfion/09_paper_thesis_talks/bishe/thesis_v2/figures/fig4-3_srcX_displacement.png"

data = pd.read_csv(CACHE)
data = data.sort_values(["freq", "t_ns"]).reset_index(drop=True)
data["dr"] = np.sqrt(data["dx"] ** 2 + data["dy"] ** 2 + data["dz"] ** 2)
data["speed"] = 0.0
for f in data["freq"].unique():
    mask = data["freq"] == f
    g = data.loc[mask].sort_values("t_ns")
    ts = g["t_ns"].values
    vx = np.gradient(g["dx"].values, ts)
    vy = np.gradient(g["dy"].values, ts)
    vz = np.gradient(g["dz"].values, ts)
    data.loc[g.index, "speed"] = np.sqrt(vx ** 2 + vy ** 2 + vz ** 2)

FREQS = sorted(data["freq"].unique())

fig, axes = plt.subplots(4, 1, figsize=(8, 11), sharex=True)
fig.patch.set_facecolor("white")
ax_r, ax_x, ax_z, ax_v = axes

cmap = plt.get_cmap("tab10")
colors = {f: cmap(i % 10) for i, f in enumerate(FREQS)}

for f in FREQS:
    sub = data[data["freq"] == f]
    if sub.empty:
        continue
    c = colors[f]
    ax_r.plot(sub["t_ns"], sub["dr"],    "-", color=c, linewidth=1.0,
              label=f"{int(f)} GHz")
    ax_x.plot(sub["t_ns"], sub["dx"],    "-", color=c, linewidth=1.0)
    ax_z.plot(sub["t_ns"], sub["dz"],    "-", color=c, linewidth=1.0)
    ax_v.plot(sub["t_ns"], sub["speed"], "-", color=c, linewidth=1.0)

for ax in (ax_x, ax_z):
    ax.axhline(0, color="gray", linestyle="--", linewidth=0.8, alpha=0.5)

panels = [
    (ax_r, r"$|\Delta r|$ (nm)",    "(a) $|\\Delta r|(t)$"),
    (ax_x, r"$\Delta x$ (nm)",      "(b) $\\Delta x(t)$"),
    (ax_z, r"$\Delta z$ (nm)",      "(c) $\\Delta z(t)$"),
    (ax_v, r"$|v|$ (nm/ns)",        "(d) $|v|(t)$"),
]

for ax, ylabel, tag in panels:
    ax.set_ylabel(ylabel, fontsize=15)
    ax.grid(True, linestyle="-", linewidth=0.4, alpha=0.18, color="gray")
    ax.text(1.02, 0.5, tag, transform=ax.transAxes,
            fontsize=15, ha="left", va="center")
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

ax_v.set_xlabel(r"时间 $t$ (ns)", fontsize=15)

handles, labels = ax_r.get_legend_handles_labels()
fig.legend(handles, labels, loc="upper center",
           bbox_to_anchor=(0.5, 0.995), ncol=5, frameon=False,
           fontsize=13, handlelength=1.8, columnspacing=1.8,
           handletextpad=0.5)

fig.subplots_adjust(left=0.13, right=0.86, top=0.93, bottom=0.06,
                     hspace=0.18)
fig.savefig(OUT, dpi=300, bbox_inches="tight", facecolor="white")
print(f"[OK] saved: {OUT}")
