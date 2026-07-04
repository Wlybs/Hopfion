"""
点源 vs 平面源 基准对照分析（三组）
对比薄膜源B=1、点源B=1、点源B=100（等功率）的 Hopfion 响应。

输出（存放于 results/）：
  - position_comparison.png    : 位置漂移对比
  - core_comparison.png        : 核心细胞数对比
  - energy_comparison.png      : 能量演化对比
  - perturbation_comparison.png: 扰动增长对比
  - perturbation_profiles.png  : 空间扰动剖面对比
  - analysis_summary.txt       : 数值总结
"""

import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import discretisedfield as df

HERE = os.path.dirname(os.path.abspath(__file__))
PLANE_DIR = os.path.join(
    HERE, "..", "..", "..", "drive_selection", "plane_wave", "sw_srcX_vibX.out")
POINT_DIR = os.path.join(HERE, "ps_srcX_vibX.out")
POINT_AMP_DIR = os.path.join(HERE, "ps_srcX_vibX_amp100.out")
RESULTS_DIR = os.path.join(HERE, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

N_FRAMES = 11
DT_NS = 0.05  # 50 ps per frame

CASES = {
    "plane_B1":    (PLANE_DIR,     "#2196F3", "Plane src, B=1"),
    "point_B1":    (POINT_DIR,     "#4CAF50", "Point src, B=1"),
    "point_B100":  (POINT_AMP_DIR, "#E91E63", "Point src, B=100"),
}


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
        centers.append(np.sum(coords.reshape(shape) * weight) / w_sum * 1e9)
    return centers


def count_core(field):
    return int(np.sum(field.array[:, :, :, 2] < 0))


def compute_perturbation(field, field0):
    dm = field.array - field0.array
    return (
        np.sqrt(np.mean(dm[:, :, :, 0] ** 2)),
        np.sqrt(np.mean(dm[:, :, :, 1] ** 2)),
        np.sqrt(np.mean(dm[:, :, :, 2] ** 2)),
        np.sqrt(np.mean(np.sum(dm ** 2, axis=-1))),
    )


def spatial_profile(field, field0, axis):
    dm = np.sqrt(np.sum((field.array - field0.array) ** 2, axis=-1))
    if axis == 0:
        return np.mean(dm, axis=(1, 2))
    elif axis == 1:
        return np.mean(dm, axis=(0, 2))
    else:
        return np.mean(dm, axis=(0, 1))


def load_table(out_dir):
    ts, es = [], []
    with open(os.path.join(out_dir, "table.txt")) as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            parts = line.strip().split("\t")
            try:
                ts.append(float(parts[0]) * 1e9)
                es.append(float(parts[-1]))
            except (ValueError, IndexError):
                continue
    return np.array(ts), np.array(es)


def analyze(name, out_dir):
    print(f"\n>>> {name}")
    f0 = df.Field.from_file(os.path.join(out_dir, "m000000.ovf"))
    ts, xs, ys, zs, cores, perturbs = [], [], [], [], [], []

    for i in range(N_FRAMES):
        ovf = os.path.join(out_dir, f"m{i:06d}.ovf")
        if not os.path.exists(ovf):
            break
        field = df.Field.from_file(ovf)
        c = hopfion_center(field)
        nc = count_core(field)
        p = compute_perturbation(field, f0)
        ts.append(i * DT_NS)
        xs.append(c[0]); ys.append(c[1]); zs.append(c[2])
        cores.append(nc); perturbs.append(p)
        if i == 0 or i == N_FRAMES - 1:
            print(f"  frame {i:02d} t={i*DT_NS:.2f}ns "
                  f"pos=({c[0]:.3f},{c[1]:.3f},{c[2]:.3f})nm "
                  f"core={nc} dm={p[3]:.4e}")
        if i != 0:
            del field

    f_final = df.Field.from_file(
        os.path.join(out_dir, f"m{N_FRAMES-1:06d}.ovf"))
    prof_x = spatial_profile(f_final, f0, 0)
    prof_y = spatial_profile(f_final, f0, 1)
    prof_z = spatial_profile(f_final, f0, 2)
    del f0, f_final

    t_tab, e_tab = load_table(out_dir)
    return {
        "ts": np.array(ts), "xs": np.array(xs),
        "ys": np.array(ys), "zs": np.array(zs),
        "cores": np.array(cores),
        "perturbs": np.array(perturbs),
        "prof_x": prof_x, "prof_y": prof_y, "prof_z": prof_z,
        "t_tab": t_tab, "e_tab": e_tab,
    }


def plot_position(data):
    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
    for name, d in data.items():
        c = CASES[name][1]
        lbl = CASES[name][2]
        dx = d["xs"] - d["xs"][0]
        dy = d["ys"] - d["ys"][0]
        dz = d["zs"] - d["zs"][0]
        dr = np.sqrt(dx**2 + dy**2 + dz**2)
        kw = dict(color=c, marker="o", markersize=4, label=lbl)
        axes[0,0].plot(d["ts"], dx, **kw)
        axes[0,1].plot(d["ts"], dy, **kw)
        axes[1,0].plot(d["ts"], dz, **kw)
        axes[1,1].plot(d["ts"], dr, **kw)

    for ax, ylabel, title in zip(
        axes.flat,
        [r"$\Delta x$ (nm)", r"$\Delta y$ (nm)",
         r"$\Delta z$ (nm)", r"$|\Delta\mathbf{r}|$ (nm)"],
        ["x-drift", "y-drift", "z-drift", "Total displacement"],
    ):
        ax.set_xlabel("Time (ns)"); ax.set_ylabel(ylabel)
        ax.set_title(title); ax.legend(fontsize=9)
        ax.grid(True, alpha=0.3); ax.axhline(0, color="gray", ls="--", alpha=0.4)

    plt.suptitle("Hopfion Position: Point Source vs Plane Source", fontsize=13)
    plt.tight_layout()
    out = os.path.join(RESULTS_DIR, "position_comparison.png")
    plt.savefig(out, dpi=200); plt.close(); print(f"[fig] {out}")


def plot_core(data):
    fig, ax = plt.subplots(figsize=(8, 5))
    for name, d in data.items():
        ax.plot(d["ts"], d["cores"], "s-",
                color=CASES[name][1], markersize=4, label=CASES[name][2])
    ax.set_xlabel("Time (ns)"); ax.set_ylabel("Core cells ($m_z < 0$)")
    ax.set_title("Hopfion Core Size: Point Source vs Plane Source")
    ax.legend(); ax.grid(True, alpha=0.3)
    plt.tight_layout()
    out = os.path.join(RESULTS_DIR, "core_comparison.png")
    plt.savefig(out, dpi=200); plt.close(); print(f"[fig] {out}")


def plot_energy(data):
    fig, ax = plt.subplots(figsize=(8, 5))
    for name, d in data.items():
        ax.plot(d["t_tab"], d["e_tab"], "-",
                color=CASES[name][1], linewidth=1.2,
                label=CASES[name][2], alpha=0.85)
    ax.set_xlabel("Time (ns)"); ax.set_ylabel("$E_{\\rm total}$ (J)")
    ax.set_title("Total Energy: Point Source vs Plane Source")
    ax.legend(); ax.grid(True, alpha=0.3)
    plt.tight_layout()
    out = os.path.join(RESULTS_DIR, "energy_comparison.png")
    plt.savefig(out, dpi=200); plt.close(); print(f"[fig] {out}")


def plot_perturbation_growth(data):
    fig, ax = plt.subplots(figsize=(8, 5))
    for name, d in data.items():
        ax.plot(d["ts"], d["perturbs"][:, 3], "o-",
                color=CASES[name][1], markersize=4, label=CASES[name][2])
    ax.set_xlabel("Time (ns)")
    ax.set_ylabel(r"$\langle|\Delta\mathbf{m}|\rangle$ (RMS)")
    ax.set_title("Spin Wave Perturbation Growth: Point Source vs Plane Source")
    ax.legend(); ax.grid(True, alpha=0.3)
    plt.tight_layout()
    out = os.path.join(RESULTS_DIR, "perturbation_comparison.png")
    plt.savefig(out, dpi=200); plt.close(); print(f"[fig] {out}")


def plot_profiles(data):
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    coords = np.linspace(-25, 25, 100, endpoint=False) + 0.25
    axis_labels = ["x", "y", "z"]
    prof_keys = ["prof_x", "prof_y", "prof_z"]

    for ax, axis_lbl, pkey in zip(axes, axis_labels, prof_keys):
        for name, d in data.items():
            ax.plot(coords, d[pkey], "-",
                    color=CASES[name][1], linewidth=1.5,
                    label=CASES[name][2])
        ax.axvline(x=-10, color="red", ls=":", alpha=0.6, label="Source x=-10nm")
        ax.axvline(x=0, color="gray", ls=":", alpha=0.5, label="Hopfion center")
        ax.axvspan(-25, -22.5, alpha=0.1, color="black")
        ax.axvspan(22.5, 25, alpha=0.1, color="black")
        ax.set_xlabel(f"Position along {axis_lbl} (nm)")
        ax.set_ylabel(r"$|\Delta\mathbf{m}|$ (RMS)")
        ax.set_title(f"Profile along {axis_lbl}")
        ax.legend(fontsize=8); ax.grid(True, alpha=0.3)

    plt.suptitle("Perturbation Profiles at t=0.5ns", fontsize=13)
    plt.tight_layout()
    out = os.path.join(RESULTS_DIR, "perturbation_profiles.png")
    plt.savefig(out, dpi=200); plt.close(); print(f"[fig] {out}")


def write_summary(data):
    lines = [
        "=" * 70,
        "Point Source vs Plane Source — Baseline Comparison",
        "=" * 70,
        "",
        f"{'Case':<22} | {'dx':>7} | {'dy':>7} | {'dz':>7} | "
        f"{'|dr|':>7} | {'Core0':>5} | {'CoreF':>5} | {'dm_rms':>10}",
        "-" * 70,
    ]
    for name, d in data.items():
        dx = d["xs"][-1] - d["xs"][0]
        dy = d["ys"][-1] - d["ys"][0]
        dz = d["zs"][-1] - d["zs"][0]
        dr = np.sqrt(dx**2 + dy**2 + dz**2)
        dm = d["perturbs"][-1, 3]
        lines.append(
            f"{name:<22} | {dx:+7.4f} | {dy:+7.4f} | {dz:+7.4f} | "
            f"{dr:7.4f} | {d['cores'][0]:5d} | {d['cores'][-1]:5d} | {dm:10.4e}"
        )

    lines += ["", "Energy change (t=0 → t=0.5ns):", "-" * 50]
    for name, d in data.items():
        dE = d["e_tab"][-1] - d["e_tab"][0]
        lines.append(
            f"  {name:<22}: {d['e_tab'][0]:.4e} → {d['e_tab'][-1]:.4e} J"
            f"  (dE={dE:+.4e})"
        )

    txt = "\n".join(lines)
    out = os.path.join(RESULTS_DIR, "analysis_summary.txt")
    with open(out, "w") as f:
        f.write(txt + "\n")
    print(f"\n[report] {out}\n\n{txt}")


def main():
    print("=" * 60)
    print("  Point Source vs Plane Source Baseline Analysis")
    print("=" * 60)

    all_data = {name: analyze(name, CASES[name][0]) for name in CASES}

    print("\n" + "=" * 60)
    print("Generating figures...")
    plot_position(all_data)
    plot_core(all_data)
    plot_energy(all_data)
    plot_perturbation_growth(all_data)
    plot_profiles(all_data)
    write_summary(all_data)
    print("\nDone.")


if __name__ == "__main__":
    main()
