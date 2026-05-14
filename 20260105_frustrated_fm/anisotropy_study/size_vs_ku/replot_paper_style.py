"""B11/B12 论文风格重画 — 复用 analyze_ani_sweep 的数据加载，输出到 results/。

输出（覆盖旧版）:
  results/R_r_vs_time.png         — B11: 各 Ku1 下 R(t), r(t) 时间线
  results/summary_Rr_vs_Ku1.png   — B12: 末帧 R, r vs Ku1 汇总
"""
import os, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, "/mnt/d/Research/Hopfion/scripts")
from paper_style import (setup_paper_style, COLORS, save_paper_fig,
                          add_ref_line, panel_label, shared_legend_above,
                          legend_above, sweep_colors)

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, THIS_DIR)
from analyze_ani_sweep import analyze_ku1, KU1_LIST, RESULTS_DIR

setup_paper_style()
os.makedirs(RESULTS_DIR, exist_ok=True)


def fmt_ku1(ku1):
    """Ku1 数值 → LaTeX 风格 legend label."""
    if ku1 == 0:
        return r"$K_{u1}=0$"
    if ku1 >= 1000:
        return rf"$K_{{u1}}={ku1/1000:.1f}\,\mathrm{{kJ/m^3}}$"
    return rf"$K_{{u1}}={ku1}\,\mathrm{{J/m^3}}$"


def plot_Rr_vs_time(all_data):
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
    colors = sweep_colors(len(KU1_LIST), cmap="plasma")

    for (ku1, data), color in zip(all_data.items(), colors):
        if data is None:
            continue
        ts = [d[0] for d in data]
        Rs = [d[1] for d in data]
        rs = [d[2] for d in data]
        label = fmt_ku1(ku1)

        ts_R = [t for t, R in zip(ts, Rs) if R is not None]
        Rs_v = [R for R in Rs if R is not None]
        ts_r = [t for t, r in zip(ts, rs) if r is not None]
        rs_v = [r for r in rs if r is not None]

        if ts_R:
            axes[0].plot(ts_R, Rs_v, "o-", color=color, label=label)
        if ts_r:
            axes[1].plot(ts_r, rs_v, "s-", color=color, label=label)

    axes[0].set_xlabel(r"时间 $t$ (ns)")
    axes[0].set_ylabel(r"大半径 $R$ (nm)")
    axes[1].set_xlabel(r"时间 $t$ (ns)")
    axes[1].set_ylabel(r"管半径 $r$ (nm)")

    # 两个 panel 数据线完全一致（同一组 Ku1 sweep），用 figure-level 共享 legend
    shared_legend_above(fig, axes[0], ncol=min(len(KU1_LIST), 3), y=1.02)
    panel_label(fig, axes[0], "(a)")
    panel_label(fig, axes[1], "(b)")

    out_path = os.path.join(RESULTS_DIR, "R_r_vs_time.png")
    save_paper_fig(fig, out_path)
    plt.close(fig)
    print(f"[OK] {out_path}")


def plot_summary(all_data):
    """末帧 R, r vs Ku1 — 单 ax 同时画 R 和 r。"""
    ku1_arr, R_arr, r_arr = [], [], []
    for ku1, data in all_data.items():
        if data is None:
            continue
        # 取最后一个有效帧（R 有值）
        last = None
        for d in reversed(data):
            if d[1] is not None:
                last = d
                break
        if last is None:
            continue
        ku1_arr.append(ku1)
        R_arr.append(last[1])
        r_arr.append(last[2])

    fig, ax = plt.subplots(figsize=(7, 4.4))

    # 转 Ku1 为 kJ/m³
    ku1_k = [k / 1000 for k in ku1_arr]
    R_pts = [(k, R) for k, R in zip(ku1_k, R_arr) if R is not None]
    r_pts = [(k, r) for k, r in zip(ku1_k, r_arr) if r is not None]

    if R_pts:
        kk, RR = zip(*R_pts)
        ax.plot(kk, RR, "o-", color=COLORS["primary"], label=r"大半径 $R$")
    if r_pts:
        kk, rr = zip(*r_pts)
        ax.plot(kk, rr, "s-", color=COLORS["secondary"], label=r"管半径 $r$")

    ax.set_xlabel(r"各向异性 $K_{u1}$ ($\mathrm{kJ/m^3}$)")
    ax.set_ylabel(r"尺寸 (nm)")
    legend_above(ax, ncol=2)

    out_path = os.path.join(RESULTS_DIR, "summary_Rr_vs_Ku1.png")
    save_paper_fig(fig, out_path)
    plt.close(fig)
    print(f"[OK] {out_path}")


def main():
    all_data = {}
    for ku1 in KU1_LIST:
        print(f">>> Ku1 = {ku1:.0f} J/m³")
        all_data[ku1] = analyze_ku1(ku1)
    print()
    plot_Rr_vs_time(all_data)
    plot_summary(all_data)


if __name__ == "__main__":
    main()
