"""
amplitude_sweep 分析脚本
对 B=0.05~2.0T (440GHz, srcX_vibX, 0.5ns) 提取 Hopfion 轨迹和结构完整性。

输出 (amplitude_sweep/results/):
  - trajectory_vs_B.png     : 各 B 下的 |dr|(t) 和分量
  - velocity_vs_B.png       : v(t) 速度剖面
  - summary_table.txt       : 末帧汇总
"""

import os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, "/mnt/d/Research/Hopfion/scripts")
from hopfion_analysis import hopfion_centroid, core_count
from paper_style import (setup_paper_style, COLORS, save_paper_fig,
                          panel_label, shared_legend_above, legend_above,
                          sweep_colors)

setup_paper_style()

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(HERE, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

import discretisedfield as df

B_LIST = [0.05, 0.1, 0.2, 0.5, 1.0, 2.0]
DT_NS = 0.05  # autosave = 50ps


def amp_to_str(b):
    s = f"{b:.1f}".replace(".", "p")
    if b < 1:
        s = f"{b:.2f}".rstrip("0").replace(".", "p")
    return s


def extract_trajectory(out_dir, dt_ns=DT_NS):
    ovf_files = sorted(
        f for f in os.listdir(out_dir)
        if f.startswith("m") and f.endswith(".ovf")
    )
    results = []
    for ovf in ovf_files:
        idx = int(ovf.replace("m", "").replace(".ovf", ""))
        t_ns = idx * dt_ns
        field = df.Field.from_file(os.path.join(out_dir, ovf))
        c = hopfion_centroid(field, method="weighted")
        cc = core_count(field)
        del field
        results.append((t_ns, c, cc))
    return results


def main():
    all_data = {}
    for b in B_LIST:
        label = amp_to_str(b)
        out_dir = os.path.join(HERE, f"sw_B{label}T.out")
        if not os.path.isdir(out_dir):
            print(f"  [SKIP] {out_dir} not found")
            continue
        print(f"  B={b}T ...", end="", flush=True)
        traj = extract_trajectory(out_dir)
        all_data[b] = traj
        print(f" {len(traj)} frames")

    if not all_data:
        print("No data found.")
        return

    # --- Plot 1: trajectory 4 panels (paper style) ---
    fig, axes = plt.subplots(2, 2, figsize=(11, 7.5))
    colors = sweep_colors(len(all_data), cmap="viridis")

    for (b, traj), color in zip(all_data.items(), colors):
        ts = [d[0] for d in traj if d[1] is not None]
        cs = [d[1] for d in traj if d[1] is not None]
        if len(cs) < 2:
            continue
        c0 = cs[0]
        dx = [c[0] - c0[0] for c in cs]
        dy = [c[1] - c0[1] for c in cs]
        dz = [c[2] - c0[2] for c in cs]
        dr = [np.sqrt(x**2 + y**2 + z**2) for x, y, z in zip(dx, dy, dz)]
        label = rf"$B={b}$ T"
        axes[0, 0].plot(ts, dr, "o-", color=color, label=label)
        axes[0, 1].plot(ts, dx, "o-", color=color)
        axes[1, 0].plot(ts, dz, "o-", color=color)
        cores = [d[2] for d in traj if d[1] is not None]
        axes[1, 1].plot(ts, cores, "o-", color=color)

    ylabels = [
        r"总位移 $|\Delta r|$ (nm)",
        r"$x$ 位移 $\Delta x$ (nm)",
        r"$z$ 位移 $\Delta z$ (nm)",
        r"核心体素数 $N_c$",
    ]
    plabels = ["(a)", "(b)", "(c)", "(d)"]
    for ax, ylab, plab in zip(axes.flat, ylabels, plabels):
        ax.set_xlabel(r"时间 $t$ (ns)")
        ax.set_ylabel(ylab)
        panel_label(fig, ax, plab)

    shared_legend_above(fig, axes[0, 0], ncol=min(len(all_data), 5), y=1.0)
    out_png = os.path.join(RESULTS_DIR, "trajectory_vs_B.png")
    save_paper_fig(fig, out_png)
    plt.close(fig)
    print(f"[fig] {out_png}")

    # --- Plot 2: velocity profile ---
    fig, ax = plt.subplots(figsize=(8, 4.4))
    for (b, traj), color in zip(all_data.items(), colors):
        ts = [d[0] for d in traj if d[1] is not None]
        cs = [d[1] for d in traj if d[1] is not None]
        if len(cs) < 3:
            continue
        c0 = cs[0]
        dr = [np.sqrt((c[0]-c0[0])**2 + (c[1]-c0[1])**2 + (c[2]-c0[2])**2)
              for c in cs]
        v = np.gradient(dr, ts)
        ax.plot(ts, v, "o-", color=color, label=rf"$B={b}$ T")

    ax.set_xlabel(r"时间 $t$ (ns)")
    ax.set_ylabel(r"速度 $v$ (nm$\cdot$ns$^{-1}$)")
    legend_above(ax, ncol=min(len(all_data), 5))
    out_png = os.path.join(RESULTS_DIR, "velocity_vs_B.png")
    save_paper_fig(fig, out_png)
    plt.close(fig)
    print(f"[fig] {out_png}")

    # --- Summary table ---
    lines = ["B (T)  |  |dr|@0.5ns (nm)  |  dz (nm)  |  Core_0  |  Core_f  |  Direction"]
    lines.append("-" * 75)
    for b, traj in all_data.items():
        cs = [d[1] for d in traj if d[1] is not None]
        cores = [d[2] for d in traj if d[1] is not None]
        if len(cs) < 2:
            lines.append(f"{b:5.2f}  |  NO DATA")
            continue
        c0, cf = cs[0], cs[-1]
        dx = cf[0] - c0[0]
        dz = cf[2] - c0[2]
        dr = np.sqrt((cf[0]-c0[0])**2 + (cf[1]-c0[1])**2 + (cf[2]-c0[2])**2)
        direction = "+z" if dz > 0.01 else ("-z" if dz < -0.01 else "~0")
        lines.append(f"{b:5.2f}  |  {dr:14.3f}  |  {dz:8.3f}  |  {cores[0]:7d}  |  {cores[-1]:7d}  |  {direction}")

    txt = "\n".join(lines)
    with open(os.path.join(RESULTS_DIR, "summary_table.txt"), "w") as f:
        f.write(txt + "\n")
    print(f"\n[report] results/summary_table.txt")
    print("\n" + txt)


if __name__ == "__main__":
    main()
