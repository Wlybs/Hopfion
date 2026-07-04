"""Generate fig4-1_direction_selectivity.png

Single combined PNG, 4x1 vertical layout, Chinese labels.
Mimics the style of fig3-4 / fig3-8.

Run:
    /mnt/d/Research/Hopfion/hopfion/bin/python make_fig4-1_direction_selectivity.py
"""
import os
import sys
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.ticker import ScalarFormatter
import discretisedfield as df

# ---- Chinese font ----
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

DATA_ROOT = (
    "/mnt/d/Research/Hopfion/04_frustrated_fm_foundation/20260105_frustrated_fm/"
    "spin_wave_dynamics/drive_selection/plane_wave"
)
OUT = "/mnt/d/Research/Hopfion/09_paper_thesis_talks/bishe/thesis_v2/figures/fig4-1_direction_selectivity.png"

COMBOS = [
    ("srcX_vibX", "sw_srcX_vibX.out", "#2196F3"),
    ("srcX_vibZ", "sw_srcX_vibZ.out", "#4CAF50"),
    ("srcY_vibX", "sw_srcY_vibX.out", "#9C27B0"),
    ("srcZ_vibX", "sw_srcZ_vibX.out", "#FF9800"),
    ("srcZ_vibZ", "sw_srcZ_vibZ.out", "#E91E63"),
]
N_FRAMES = 11
DT_NS = 0.05


def hopfion_center(field):
    mz = field.array[:, :, :, 2]
    weight = np.maximum(1 - mz, 0)
    w_sum = np.sum(weight)
    centers = []
    for i in range(3):
        coords = np.linspace(
            field.mesh.region.pmin[i] + field.mesh.cell[i] / 2,
            field.mesh.region.pmax[i] - field.mesh.cell[i] / 2,
            mz.shape[i],
        )
        shape = [1, 1, 1]
        shape[i] = mz.shape[i]
        c = np.sum(coords.reshape(shape) * weight) / w_sum * 1e9
        centers.append(c)
    return centers


def load_trajectory(out_dir):
    ts, xs, ys, zs = [], [], [], []
    for i in range(N_FRAMES):
        ovf = os.path.join(out_dir, f"m{i:06d}.ovf")
        if not os.path.exists(ovf):
            break
        f = df.Field.from_file(ovf)
        c = hopfion_center(f)
        ts.append(i * DT_NS)
        xs.append(c[0])
        ys.append(c[1])
        zs.append(c[2])
        del f
    ts = np.array(ts)
    xs = np.array(xs)
    ys = np.array(ys)
    zs = np.array(zs)
    return ts, xs - xs[0], ys - ys[0], zs - zs[0]


def main():
    data = {}
    for name, dirname, color in COMBOS:
        out_dir = os.path.join(DATA_ROOT, dirname)
        if not os.path.isdir(out_dir):
            print(f"[ERROR] missing: {out_dir}", file=sys.stderr)
            sys.exit(1)
        print(f"loading {name} ...")
        ts, dx, dy, dz = load_trajectory(out_dir)
        dr = np.sqrt(dx ** 2 + dy ** 2 + dz ** 2)
        data[name] = {"ts": ts, "dx": dx, "dy": dy, "dz": dz, "dr": dr, "color": color}

    fig, axes = plt.subplots(4, 1, figsize=(8, 11), sharex=True)
    fig.patch.set_facecolor("white")
    components = [
        ("dx", r"\Delta x", "(a) $x$ 方向"),
        ("dy", r"\Delta y", "(b) $y$ 方向"),
        ("dz", r"\Delta z", "(c) $z$ 方向"),
        ("dr", r"|\Delta \mathbf{r}|", "(d) 总位移"),
    ]

    def pick_exponent(peak):
        if peak <= 0 or not np.isfinite(peak):
            return 0
        k = int(np.floor(np.log10(peak)))
        if 0 <= k <= 1:
            return 0
        return k

    for ax, (key, sym, tag) in zip(axes, components):
        peak = max(
            float(np.max(np.abs(data[name][key]))) for name, _, _ in COMBOS
        )
        k = pick_exponent(peak)
        scale = 10.0 ** k
        for name, _, color in COMBOS:
            d = data[name]
            ax.plot(d["ts"], d[key] / scale, marker="o", markersize=4,
                    linewidth=1.2, color=color,
                    markerfacecolor="white", markeredgecolor=color,
                    markeredgewidth=1.0, label=name)
        if k == 0:
            ylabel = f"${sym}$ (nm)"
        else:
            ylabel = rf"${sym}$ ($\times 10^{{{k}}}$ nm)"
        ax.set_ylabel(ylabel, fontsize=15)

        ax.grid(True, linestyle="-", linewidth=0.4, alpha=0.18, color="gray")
        ax.set_title(tag, fontsize=14, fontweight='bold', loc='center', pad=4)
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

    axes[-1].set_xlabel(r"时间 $t$ (ns)", fontsize=15)

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center",
               bbox_to_anchor=(0.5, 1.0), ncol=5, frameon=False,
               fontsize=13, handlelength=1.8, columnspacing=1.6,
               handletextpad=0.5)

    fig.subplots_adjust(left=0.13, right=0.86, top=0.92, bottom=0.06,
                         hspace=0.22)
    fig.savefig(OUT, dpi=300, bbox_inches="tight", facecolor="white")
    print(f"[OK] saved: {OUT}")


if __name__ == "__main__":
    main()
