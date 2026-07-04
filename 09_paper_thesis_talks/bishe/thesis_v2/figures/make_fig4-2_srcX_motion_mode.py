"""Generate fig4-2_srcX_motion_mode.png — 3x1 vertical, fig4-1 style.

Run:
    /mnt/d/Research/Hopfion/hopfion/bin/python make_fig4-2_srcX_motion_mode.py
"""
import os
import numpy as np
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
mpl.rcParams["mathtext.fontset"] = "dejavusans"

OUT = "/mnt/d/Research/Hopfion/09_paper_thesis_talks/bishe/thesis_v2/figures/fig4-2_srcX_motion_mode.png"

freq = np.array([100, 200, 300, 400, 500, 600, 700, 800, 900, 1000])
dr   = np.array([1.938, 2.508, 0.902, 0.084, 0.151, 0.077, 0.445, 0.531, 0.408, 5.500])
vbar = np.array([15.66, 18.53, 6.39, 1.53, 1.86, 1.83, 4.67, 4.13, 3.28, 41.05])
abar = np.array([506.44, 321.27, 447.98, 110.80, 130.24, 148.79, 287.28, 276.71, 252.15, 1180.34])
eff_mask = dr >= 1.0

PANELS = [
    (dr,   r"$|\Delta r|$ (nm)",             "(a) 末态位移"),
    (vbar, r"$\bar v$ (nm/ns)",              "(b) 平均速度"),
    (abar, r"$\bar a$ (nm/ns$^2$)",          "(c) 平均加速度"),
]

RED  = "#B22222"
GRAY = "0.55"

fig, axes = plt.subplots(3, 1, figsize=(8, 9), sharex=True)
fig.patch.set_facecolor("white")

for ax, (y, ylabel, tag) in zip(axes, PANELS):
    ax.axvspan(400, 600, color="#F5F5F5", alpha=0.9, zorder=0)
    ax.plot(freq, y, linestyle="--", color=GRAY, linewidth=0.9, alpha=0.6, zorder=2)
    ax.plot(freq[~eff_mask], y[~eff_mask], "o",
            markerfacecolor="white", markeredgecolor="black",
            markeredgewidth=1.2, markersize=8,
            label=r"弱响应 ($|\Delta r| < 1$ nm)", zorder=3)
    ax.plot(freq[eff_mask], y[eff_mask], "s",
            markerfacecolor=RED, markeredgecolor=RED,
            markersize=8,
            label=r"有效驱动 ($|\Delta r| \geq 1$ nm)", zorder=4)

    ax.set_ylabel(ylabel, fontsize=12)
    ax.grid(True, linestyle="-", linewidth=0.4, alpha=0.18, color="gray")
    ax.text(1.02, 0.5, tag, transform=ax.transAxes,
            fontsize=12, ha="left", va="center")
    ax.tick_params(labelsize=10, direction="in", length=4,
                   top=True, right=True, which="major")
    ax.tick_params(direction="in", length=2.5,
                   top=True, right=True, which="minor")
    ax.minorticks_on()
    ax.set_facecolor("white")
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_color("black")
        spine.set_linewidth(0.9)

axes[-1].set_xlabel(r"频率 $f$ (GHz)", fontsize=12)
axes[-1].set_xlim(50, 1050)
axes[-1].set_xticks(np.arange(100, 1001, 100))

handles, labels = axes[0].get_legend_handles_labels()
fig.legend(handles, labels, loc="upper center",
           bbox_to_anchor=(0.5, 0.995), ncol=2, frameon=False,
           fontsize=10, handlelength=1.8, columnspacing=2.0,
           handletextpad=0.5)

fig.subplots_adjust(left=0.12, right=0.86, top=0.94, bottom=0.07,
                     hspace=0.15)
fig.savefig(OUT, dpi=300, bbox_inches="tight", facecolor="white")
print(f"[OK] saved: {OUT}")
