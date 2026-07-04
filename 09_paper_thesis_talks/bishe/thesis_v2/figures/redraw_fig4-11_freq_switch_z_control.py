#!/usr/bin/env python3
"""redraw_fig4-11_freq_switch_z_control.py (fig4-1 canonical style)

频率切换下双向 z 控制：上 Δz(t)，下 v_z(t)。
数据源：freq_switch_v3_z_control.txt
输出：fig4-11_freq_switch_z_control.png
"""

import os
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Patch

mpl.use('Agg')

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

BLACK = "k"
RED = "#B22222"
BLUE = "#003F7F"
GREEN = "#2A7A2A"
PHASE1_COLOR = "#CFE8CF"
PHASE2_COLOR = "#CFDBEF"
PHASE_OFF_COLOR = "#EEEEEE"

OUT = "/mnt/d/Research/Hopfion/09_paper_thesis_talks/bishe/thesis_v2/figures/fig4-11_freq_switch_z_control.png"

t_ns = np.array([
    0.000, 0.035, 0.070, 0.105, 0.140, 0.175, 0.210, 0.245, 0.280, 0.315,
    0.350, 0.385, 0.420, 0.455, 0.490, 0.525, 0.560, 0.595, 0.630, 0.665,
    0.700, 0.735, 0.770, 0.805, 0.840, 0.875, 0.910, 0.945, 0.980, 1.015,
    1.050, 1.085,
])
dz_nm = np.array([
    +0.0000, +0.0092, +0.0368, +0.1188, +0.3656, +1.1824, +2.5026, +4.4383, +6.7554, +9.2079,
    +11.7445, +14.5060, +17.1475, +18.5792, +17.8086, +17.0914, +16.5065, +15.6559, +14.4034, +12.5967,
    +10.1927, +7.2342, +4.0277, +0.4328, -3.4822, -7.3425, -11.8002, -11.5154, -10.5281, -9.0170,
    -10.3827, -10.2965,
])
v_z = np.gradient(dz_nm, t_ns)

T_SWITCH1 = 0.50
T_SWITCH2 = 1.00
T_END = 1.10

fig, (ax1, ax2) = plt.subplots(
    2, 1, figsize=(8, 7), sharex=True,
    gridspec_kw={"height_ratios": [3, 2], "hspace": 0.10})
fig.patch.set_facecolor("white")


def style_axes(ax):
    ax.set_facecolor("white")
    ax.grid(True, linestyle="-", linewidth=0.4, alpha=0.18, color="gray")
    ax.tick_params(labelsize=13, direction="in", length=4,
                   top=True, right=True, which="major")
    ax.tick_params(direction="in", length=2.5,
                   top=True, right=True, which="minor")
    ax.minorticks_on()
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_color("black")
        spine.set_linewidth(0.9)


# ---- (a) Δz(t) ----
ax1.axvspan(0, T_SWITCH1, color=PHASE1_COLOR, alpha=0.85, zorder=0)
ax1.axvspan(T_SWITCH1, T_SWITCH2, color=PHASE2_COLOR, alpha=0.85, zorder=0)
ax1.axvspan(T_SWITCH2, T_END, color=PHASE_OFF_COLOR, alpha=0.85, zorder=0)

for t_sw in (T_SWITCH1, T_SWITCH2):
    ax1.axvline(t_sw, color=BLACK, linestyle="--", linewidth=1.2, alpha=0.75, zorder=1)

ax1.plot(t_ns, dz_nm, color=BLACK, linewidth=1.5, zorder=2)
ax1.plot(t_ns, dz_nm, marker="o", linestyle="none", color=BLACK,
         markerfacecolor="white", markeredgewidth=1.2, markersize=6, zorder=3)

ax1.axhline(0, color="gray", linestyle="--", linewidth=0.8, alpha=0.5)
ax1.set_ylabel(r"$z$ 方向位移 $\Delta z$ (nm)", fontsize=15)
ax1.set_ylim(-18, 22)
ax1.set_title(r"(a) $\Delta z(t)$", fontsize=14, fontweight="bold", loc="center", pad=4)
style_axes(ax1)

# ---- (b) v_z(t) ----
ax2.axvspan(0, T_SWITCH1, color=PHASE1_COLOR, alpha=0.85, zorder=0)
ax2.axvspan(T_SWITCH1, T_SWITCH2, color=PHASE2_COLOR, alpha=0.85, zorder=0)
ax2.axvspan(T_SWITCH2, T_END, color=PHASE_OFF_COLOR, alpha=0.85, zorder=0)
ax2.axvline(T_SWITCH1, color=BLACK, linestyle="--", linewidth=1.2, alpha=0.75)
ax2.axvline(T_SWITCH2, color=BLACK, linestyle="--", linewidth=1.2, alpha=0.75)
ax2.axhline(0, color="gray", linestyle="--", linewidth=0.8, alpha=0.5)

ax2.plot(t_ns, v_z, color=RED, linewidth=1.5, zorder=2)
ax2.plot(t_ns, v_z, marker="s", linestyle="none", color=RED,
         markerfacecolor=RED, markeredgecolor=RED, markeredgewidth=0.8,
         markersize=6, zorder=3)

ax2.set_xlabel(r"时间 $t$ (ns)", fontsize=15)
ax2.set_ylabel(r"$v_z$ (nm/ns)", fontsize=15)
ax2.set_xlim(0, T_END + 0.02)
ax2.set_title(r"(b) $v_z(t)$", fontsize=14, fontweight="bold", loc="center", pad=4)
style_axes(ax2)

# ---- 顶部统一 legend：3 个相位色块 ----
legend_handles = [
    Patch(facecolor=PHASE1_COLOR, edgecolor="0.6", label=r"srcZ @ 100 GHz  ($+z$)"),
    Patch(facecolor=PHASE2_COLOR, edgecolor="0.6", label=r"srcZ @ 1100 GHz  ($-z$)"),
    Patch(facecolor=PHASE_OFF_COLOR, edgecolor="0.6", label=r"OFF (弛豫)"),
]
fig.legend(handles=legend_handles, loc="upper center",
           bbox_to_anchor=(0.5, 1.02), ncol=3, frameon=False,
           fontsize=13, handlelength=1.8, columnspacing=2.0,
           handletextpad=0.5)

fig.subplots_adjust(left=0.11, right=0.97, top=0.88, bottom=0.09, hspace=0.14)
fig.savefig(OUT, dpi=300, bbox_inches="tight", facecolor="white")
print(f"[OK] saved {OUT}")
