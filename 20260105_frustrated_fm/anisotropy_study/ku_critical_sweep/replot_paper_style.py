"""B07 论文风格重画 — 复用 analyze_sweep_large 的数据加载。

输出:
  results/R_r_vs_time.png — 12 个 Ku1 条件下 R(t), r(t) 时间线
"""
import os, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, "/mnt/d/Research/Hopfion/scripts")
from paper_style import (setup_paper_style, COLORS, save_paper_fig,
                          panel_label, shared_legend_above, sweep_colors)

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, THIS_DIR)
from analyze_sweep_large import analyze_ku1, KU1_MAP, RESULTS_DIR

setup_paper_style()
os.makedirs(RESULTS_DIR, exist_ok=True)


def fmt_ku1(ku1):
    if ku1 == 0:
        return r"$K_{u1}=0$"
    return rf"$K_{{u1}}={ku1/1000:.0f}\,\mathrm{{kJ/m^3}}$"


def main():
    all_data = {}
    for ku1 in KU1_MAP:
        print(f">>> Ku1 = {ku1/1000:.0f}k J/m³")
        all_data[ku1] = analyze_ku1(ku1)
    print()

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6))
    colors = sweep_colors(len(KU1_MAP), cmap="plasma")

    for (ku1, data), color in zip(all_data.items(), colors):
        if data is None:
            continue
        ts_R = [(d[0], d[1]) for d in data if d[1] is not None]
        ts_r = [(d[0], d[2]) for d in data if d[2] is not None]
        label = fmt_ku1(ku1)
        if ts_R:
            axes[0].plot([x[0] for x in ts_R], [x[1] for x in ts_R],
                         "o-", color=color, label=label)
        if ts_r:
            axes[1].plot([x[0] for x in ts_r], [x[1] for x in ts_r],
                         "s-", color=color, label=label)

    axes[0].set_xlabel(r"时间 $t$ (ns)")
    axes[0].set_ylabel(r"大半径 $R$ (nm)")
    axes[1].set_xlabel(r"时间 $t$ (ns)")
    axes[1].set_ylabel(r"管半径 $r$ (nm)")

    # 12 条曲线 → legend 4 列 × 3 行（折成 3 行而非 12 列）
    shared_legend_above(fig, axes[0], ncol=4, y=1.02)
    panel_label(fig, axes[0], "(a)")
    panel_label(fig, axes[1], "(b)")

    out_path = os.path.join(RESULTS_DIR, "R_r_vs_time.png")
    save_paper_fig(fig, out_path)
    plt.close(fig)
    print(f"[OK] {out_path}")


if __name__ == "__main__":
    main()
