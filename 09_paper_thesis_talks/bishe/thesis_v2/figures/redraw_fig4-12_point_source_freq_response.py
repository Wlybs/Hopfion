"""Generate fig4-12_point_source_freq_response.png (fig4-1 canonical style)

点源驱动下的频率响应谱：上 srcX，下 srcZ；柱状图 |Δr| 按 Δz 符号着色。
数据源: freq_sweep/point_source/results/point_source_summary.txt
输出:  fig4-12_point_source_freq_response.png
"""
import os
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Patch

mpl.use("Agg")

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

OUT = "/mnt/d/Research/Hopfion/09_paper_thesis_talks/bishe/thesis_v2/figures/fig4-12_point_source_freq_response.png"

FREQS = np.array([100, 200, 300, 400, 500, 600, 700, 800, 900, 1000])

# srcX: 全部 +z
SRCX_DR = np.array([3.0178, 1.2680, 4.1963, 1.3651, 2.6644, 2.8242, 5.7105, 0.9697, 2.0235, 2.8839])
SRCX_DZ = np.array([+2.98, +1.12, +4.17, +1.36, +2.63, +2.82, +5.69, +0.89, +2.01, +2.87])

# srcZ: 含方向反转
SRCZ_DR = np.array([1.6594, 2.7878, 4.1872, 1.8298, 0.2476, 3.8685, 0.7161, 7.3142, 3.4245, 0.4526])
SRCZ_DZ = np.array([+1.66, +2.79, +4.19, +1.83, -0.22, +3.87, -0.70, -7.30, +3.42, +0.45])

GREEN = "#2CA02C"
ORANGE = "#FF7F0E"
BAR_WIDTH = 60


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


def draw_bars(ax, freqs, dr_vals, dz_vals, title_tag):
    colors = [GREEN if dz > 0 else ORANGE for dz in dz_vals]
    ax.bar(freqs, dr_vals, width=BAR_WIDTH, color=colors,
           edgecolor="black", linewidth=0.6, alpha=0.9, zorder=2)
    # 峰值标注
    i_peak = int(np.argmax(dr_vals))
    ax.annotate(f"{int(freqs[i_peak])} GHz\n$|\\Delta r|$ = {dr_vals[i_peak]:.2f} nm",
                xy=(freqs[i_peak], dr_vals[i_peak]),
                xytext=(freqs[i_peak], dr_vals[i_peak] + 1.2),
                ha="center", fontsize=12, color="black",
                arrowprops=dict(arrowstyle="->", color="black", lw=0.9))
    ax.set_ylabel(r"位移 $|\Delta r|$ (nm)", fontsize=15)
    ax.set_xlim(50, 1050)
    ax.set_xticks(np.arange(100, 1001, 100))
    ymax = max(dr_vals.max() * 1.35, 8.5)
    ax.set_ylim(0, ymax)
    ax.set_title(title_tag, fontsize=14, fontweight="bold", loc="center", pad=4)
    style_axes(ax)


fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 7), sharex=True,
                               gridspec_kw={"hspace": 0.18})
fig.patch.set_facecolor("white")

draw_bars(ax1, FREQS, SRCX_DR, SRCX_DZ, r"(a) srcX: $|\Delta r|(f)$")
draw_bars(ax2, FREQS, SRCZ_DR, SRCZ_DZ, r"(b) srcZ: $|\Delta r|(f)$")

ax2.set_xlabel(r"频率 $f$ (GHz)", fontsize=15)

legend_handles = [
    Patch(facecolor=GREEN, edgecolor="black", linewidth=0.6, label=r"$+z$ 方向"),
    Patch(facecolor=ORANGE, edgecolor="black", linewidth=0.6, label=r"$-z$ 方向"),
]
fig.legend(handles=legend_handles, loc="upper center",
           bbox_to_anchor=(0.5, 1.02), ncol=2, frameon=False,
           fontsize=13, handlelength=1.8, columnspacing=2.0,
           handletextpad=0.5)

fig.subplots_adjust(left=0.12, right=0.97, top=0.88, bottom=0.08, hspace=0.22)
fig.savefig(OUT, dpi=300, bbox_inches="tight", facecolor="white")
print(f"[OK] saved: {OUT}")
