"""B01 论文风格重画 — 复用 analyze_properties 的 R/r 计算。

输出:
  stability_results/fig_Rr_evolution.png — 3 个 Ku 条件下 R(t), r(t) 时间线
"""
import os, sys, glob
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import discretisedfield as df

sys.path.insert(0, "/mnt/d/Research/Hopfion/scripts")
from paper_style import (setup_paper_style, COLORS, save_paper_fig,
                          panel_label, shared_legend_above)

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, THIS_DIR)
from analyze_properties import compute_Rr, RESULTS as RESULTS_DIR, DT_OVF

setup_paper_style()
os.makedirs(RESULTS_DIR, exist_ok=True)

RUNS = [
    {"label": r"$K_{u1}=0$",                       "dir": "stability_Ku0.out",   "color": COLORS["primary"]},
    {"label": r"$K_{u1}=10\,\mathrm{kJ/m^3}$",    "dir": "stability_Ku10k.out", "color": COLORS["secondary"]},
    {"label": r"$K_{u1}=50\,\mathrm{kJ/m^3}$",    "dir": "stability_Ku50k.out", "color": COLORS["tertiary"]},
]


def main():
    all_Rr = {}
    for run in RUNS:
        out_dir = os.path.join(THIS_DIR, run["dir"])
        ovfs = sorted(glob.glob(os.path.join(out_dir, "m*.ovf")))
        ts, Rs, rs = [], [], []
        for i, fp in enumerate(ovfs):
            t_ns = i * DT_OVF * 1e9
            field = df.Field.from_file(fp)
            R, r = compute_Rr(field)
            del field
            ts.append(t_ns)
            Rs.append(R)
            rs.append(r)
        print(f"  {run['label']}: {len(ts)} frames, t={ts[0]:.2f}~{ts[-1]:.2f}ns")
        all_Rr[run["label"]] = (np.array(ts), Rs, rs, run["color"])

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))

    for label, (ts, Rs, rs, color) in all_Rr.items():
        Rs_v = [(t, R) for t, R in zip(ts, Rs) if R is not None]
        rs_v = [(t, r) for t, r in zip(ts, rs) if r is not None]
        if Rs_v:
            t_R, R_v = zip(*Rs_v)
            axes[0].plot(t_R, R_v, "o-", color=color, label=label)
        if rs_v:
            t_r, r_v = zip(*rs_v)
            axes[1].plot(t_r, r_v, "s-", color=color, label=label)

    axes[0].set_xlabel(r"时间 $t$ (ns)")
    axes[0].set_ylabel(r"大半径 $R$ (nm)")
    axes[1].set_xlabel(r"时间 $t$ (ns)")
    axes[1].set_ylabel(r"管半径 $r$ (nm)")

    shared_legend_above(fig, axes[0], ncol=3, y=1.02)
    panel_label(fig, axes[0], "(a)")
    panel_label(fig, axes[1], "(b)")

    out_path = os.path.join(RESULTS_DIR, "fig_Rr_evolution.png")
    save_paper_fig(fig, out_path)
    plt.close(fig)
    print(f"[OK] {out_path}")


if __name__ == "__main__":
    main()
