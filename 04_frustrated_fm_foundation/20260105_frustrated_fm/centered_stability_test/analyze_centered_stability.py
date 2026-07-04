"""
居中稳态验证分析脚本
分析 stability_Ku0/Ku10k/Ku50k 的 Hopfion 位置-时间演化。

输出（就近存放于 stability_results/）：
  - hopfion_z_drift.png       : z方向漂移随时间演化（三组对比）
  - hopfion_xyz_drift.png     : xyz三分量漂移（每Ku一行）
  - hopfion_mz_core_count.png : mz<0核心细胞数随时间
  - stability_summary.txt     : 数值总结表
"""

import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import discretisedfield as df

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(HERE, "stability_results")
os.makedirs(RESULTS_DIR, exist_ok=True)

CONFIGS = {
    "Ku=0":   ("stability_Ku0.out",   21, 0.05e-9),
    "Ku=10k": ("stability_Ku10k.out", 21, 0.05e-9),
    "Ku=50k": ("stability_Ku50k.out", 21, 0.05e-9),
}


def hopfion_center(field):
    """加权质心法定位 Hopfion (weight = max(1-mz, 0))"""
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


def count_core(field):
    """统计 mz<0 的核心细胞数"""
    return int(np.sum(field.array[:, :, :, 2] < 0))


def analyze_config(name, dirname, n_frames, dt):
    out_dir = os.path.join(HERE, dirname)
    ts, xs, ys, zs, cores = [], [], [], [], []
    for i in range(n_frames):
        ovf = os.path.join(out_dir, f"m{i:06d}.ovf")
        if not os.path.exists(ovf):
            break
        field = df.Field.from_file(ovf)
        c = hopfion_center(field)
        nc = count_core(field)
        del field
        ts.append(i * dt * 1e9)
        xs.append(c[0])
        ys.append(c[1])
        zs.append(c[2])
        cores.append(nc)
        if i % 5 == 0:
            print(f"  [{name}] frame {i:02d} t={ts[-1]:.2f}ns "
                  f"z={zs[-1]:.3f}nm core={nc}")
    return (np.array(ts), np.array(xs), np.array(ys),
            np.array(zs), np.array(cores))


def plot_z_drift(all_data):
    """三组 z 漂移对比图"""
    fig, ax = plt.subplots(figsize=(8, 5))
    colors = {"Ku=0": "#2196F3", "Ku=10k": "#4CAF50", "Ku=50k": "#FF5722"}

    for name, (ts, xs, ys, zs, cores) in all_data.items():
        dz = zs - zs[0]
        ax.plot(ts, dz, "o-", color=colors[name], markersize=4, label=name)

    ax.axhline(y=0, color="gray", linestyle="--", alpha=0.5)
    ax.axhline(y=2.0, color="red", linestyle=":", alpha=0.4,
               label="Threshold (2 nm)")
    ax.axhline(y=-2.0, color="red", linestyle=":", alpha=0.4)
    ax.set_xlabel("Time (ns)", fontsize=12)
    ax.set_ylabel(r"$\Delta z$ (nm)", fontsize=12)
    ax.set_title("Centered Hopfion Stability: z-drift vs Time", fontsize=13)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    out = os.path.join(RESULTS_DIR, "hopfion_z_drift.png")
    plt.savefig(out, dpi=200)
    plt.close()
    print(f"[fig] {out}")


def plot_xyz_drift(all_data):
    """每组 Ku 的 xyz 三分量漂移"""
    names = list(all_data.keys())
    fig, axes = plt.subplots(len(names), 3, figsize=(15, 4 * len(names)))
    if len(names) == 1:
        axes = axes[np.newaxis, :]
    comp_labels = ["x", "y", "z"]
    comp_colors = ["#2196F3", "#4CAF50", "#FF5722"]

    for row, name in enumerate(names):
        ts, xs, ys, zs, _ = all_data[name]
        for col, (vals, label, color) in enumerate(
            zip([xs, ys, zs], comp_labels, comp_colors)
        ):
            dv = vals - vals[0]
            axes[row, col].plot(ts, dv, "o-", markersize=3, color=color)
            axes[row, col].axhline(y=0, color="gray", linestyle="--", alpha=0.4)
            axes[row, col].set_xlabel("Time (ns)")
            axes[row, col].set_ylabel(f"$\\Delta {label}$ (nm)")
            axes[row, col].set_title(f"{name}: $\\Delta {label}$")
            axes[row, col].grid(True, alpha=0.3)
            slope = (dv[-1] - dv[0]) / (ts[-1] - ts[0]) if ts[-1] > 0 else 0
            axes[row, col].text(
                0.05, 0.90,
                f"slope={slope:+.3f} nm/ns",
                transform=axes[row, col].transAxes, fontsize=9,
            )

    plt.suptitle("Centered Hopfion: Position Drift (xyz)", fontsize=13)
    plt.tight_layout()
    out = os.path.join(RESULTS_DIR, "hopfion_xyz_drift.png")
    plt.savefig(out, dpi=200)
    plt.close()
    print(f"[fig] {out}")


def plot_core_count(all_data):
    """核心细胞数时间演化"""
    fig, ax = plt.subplots(figsize=(8, 5))
    colors = {"Ku=0": "#2196F3", "Ku=10k": "#4CAF50", "Ku=50k": "#FF5722"}

    for name, (ts, _, _, _, cores) in all_data.items():
        ax.plot(ts, cores, "s-", color=colors[name], markersize=4, label=name)

    ax.set_xlabel("Time (ns)", fontsize=12)
    ax.set_ylabel("Core cells ($m_z < 0$)", fontsize=12)
    ax.set_title("Hopfion Core Size Evolution", fontsize=13)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    out = os.path.join(RESULTS_DIR, "hopfion_mz_core_count.png")
    plt.savefig(out, dpi=200)
    plt.close()
    print(f"[fig] {out}")


def write_summary(all_data):
    lines = [
        "Config     | z0 (nm)  | z_final (nm) | dz (nm)  | Core_0 | Core_final | Status",
        "-" * 80,
    ]
    for name, (ts, xs, ys, zs, cores) in all_data.items():
        dz = zs[-1] - zs[0]
        status = "PASS" if abs(dz) < 2.0 else "FAIL"
        lines.append(
            f"{name:10s} | {zs[0]:8.3f} | {zs[-1]:12.3f} | {dz:+8.3f} | "
            f"{cores[0]:6d} | {cores[-1]:10d} | {status}"
        )
    txt = "\n".join(lines)
    out = os.path.join(RESULTS_DIR, "stability_summary.txt")
    with open(out, "w") as f:
        f.write(txt + "\n")
    print(f"\n[report] {out}")
    print("\n" + txt)


def main():
    print("=" * 60)
    print("  Centered Hopfion Stability Analysis")
    print("=" * 60)

    all_data = {}
    for name, (dirname, n_frames, dt) in CONFIGS.items():
        print(f"\n>>> {name}")
        all_data[name] = analyze_config(name, dirname, n_frames, dt)

    print("\n" + "=" * 60)
    plot_z_drift(all_data)
    plot_xyz_drift(all_data)
    plot_core_count(all_data)
    write_summary(all_data)
    print("\nDone.")


if __name__ == "__main__":
    main()
