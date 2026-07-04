"""
自旋波 5-combo 综合分析脚本
分析 Hopfion 在不同自旋波构型下的响应：位置漂移、核心变化、能量演化。

5 个组合：
  - srcX_vibX: 源在 x=-10nm, 振荡沿 X
  - srcX_vibZ: 源在 x=-10nm, 振荡沿 Z
  - srcY_vibX: 源在 y=-10nm, 振荡沿 X
  - srcZ_vibX: 源在 z=-10nm, 振荡沿 X
  - srcZ_vibZ: 源在 z=-10nm, 振荡沿 Z

输出（存放于 results/）：
  - hopfion_position_5combos.png  : 位置漂移对比
  - hopfion_core_5combos.png      : 核心细胞数对比
  - energy_5combos.png            : 能量演化
  - sw_perturbation_profiles.png  : 各combo磁化扰动空间分布
  - sw_perturbation_growth.png    : 扰动幅度时间演化
  - analysis_summary.txt          : 数值总结
"""

import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import discretisedfield as df

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(HERE, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

COMBOS = {
    "srcX_vibX": ("sw_srcX_vibX.out", "x=-10nm, B along X"),
    "srcX_vibZ": ("sw_srcX_vibZ.out", "x=-10nm, B along Z"),
    "srcY_vibX": ("sw_srcY_vibX.out", "y=-10nm, B along X"),
    "srcZ_vibX": ("sw_srcZ_vibX.out", "z=-10nm, B along X"),
    "srcZ_vibZ": ("sw_srcZ_vibZ.out", "z=-10nm, B along Z"),
}

N_FRAMES = 11
DT_NS = 0.05  # autosave every 50ps, 0.5ns total


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


def count_core(field):
    return int(np.sum(field.array[:, :, :, 2] < 0))


def compute_perturbation(field, field0):
    """Compute spin wave perturbation relative to initial state."""
    dm = field.array - field0.array
    # RMS per component
    dmx_rms = np.sqrt(np.mean(dm[:, :, :, 0] ** 2))
    dmy_rms = np.sqrt(np.mean(dm[:, :, :, 1] ** 2))
    dmz_rms = np.sqrt(np.mean(dm[:, :, :, 2] ** 2))
    dm_total = np.sqrt(np.mean(np.sum(dm ** 2, axis=-1)))
    return dmx_rms, dmy_rms, dmz_rms, dm_total


def spatial_perturbation_profile(field, field0, axis, src_axis):
    """Compute perturbation amplitude as function of position along axis."""
    dm = field.array - field0.array
    dm_mag = np.sqrt(np.sum(dm ** 2, axis=-1))
    # Average over the two non-profile axes
    if axis == 0:  # profile along x
        profile = np.mean(dm_mag, axis=(1, 2))
    elif axis == 1:  # profile along y
        profile = np.mean(dm_mag, axis=(0, 2))
    else:  # profile along z
        profile = np.mean(dm_mag, axis=(0, 1))
    return profile


def load_table(out_dir):
    """Load table.txt and return time and E_total arrays."""
    table_path = os.path.join(out_dir, "table.txt")
    ts, es = [], []
    with open(table_path) as f:
        for line in f:
            if line.startswith("#") or line.strip() == "":
                continue
            parts = line.strip().split("\t")
            try:
                ts.append(float(parts[0]) * 1e9)  # to ns
                es.append(float(parts[-1]))
            except (ValueError, IndexError):
                continue
    return np.array(ts), np.array(es)


def analyze_combo(name, dirname):
    out_dir = os.path.join(HERE, dirname)
    print(f"\n>>> {name} ({dirname})")

    # Load initial frame
    f0 = df.Field.from_file(os.path.join(out_dir, "m000000.ovf"))

    ts, xs, ys, zs, cores = [], [], [], [], []
    perturbations = []

    for i in range(N_FRAMES):
        ovf = os.path.join(out_dir, f"m{i:06d}.ovf")
        if not os.path.exists(ovf):
            break
        field = df.Field.from_file(ovf)
        c = hopfion_center(field)
        nc = count_core(field)
        p = compute_perturbation(field, f0)

        t = i * DT_NS
        ts.append(t)
        xs.append(c[0])
        ys.append(c[1])
        zs.append(c[2])
        cores.append(nc)
        perturbations.append(p)

        if i == 0 or i == N_FRAMES - 1:
            print(f"  frame {i:02d} t={t:.2f}ns "
                  f"pos=({c[0]:.3f},{c[1]:.3f},{c[2]:.3f})nm "
                  f"core={nc} dm_rms={p[3]:.4e}")

        if i != 0:
            del field

    # Spatial profile at final frame
    f_final = df.Field.from_file(
        os.path.join(out_dir, f"m{N_FRAMES - 1:06d}.ovf"))
    src_axis = 0 if "srcX" in name else (1 if "srcY" in name else 2)
    perp_axis = 0 if src_axis == 1 else 1  # y as perp unless src is already y
    profile_along_src = spatial_perturbation_profile(
        f_final, f0, src_axis, src_axis)
    profile_perp = spatial_perturbation_profile(
        f_final, f0, perp_axis, src_axis)

    del f0, f_final

    # Load energy
    t_table, e_table = load_table(out_dir)

    return {
        "ts": np.array(ts),
        "xs": np.array(xs),
        "ys": np.array(ys),
        "zs": np.array(zs),
        "cores": np.array(cores),
        "perturbations": np.array(perturbations),
        "profile_src": profile_along_src,
        "profile_perp": profile_perp,
        "src_axis": src_axis,
        "t_table": t_table,
        "e_table": e_table,
    }


COLORS = {
    "srcX_vibX": "#2196F3",
    "srcX_vibZ": "#4CAF50",
    "srcY_vibX": "#9C27B0",
    "srcZ_vibX": "#FF9800",
    "srcZ_vibZ": "#E91E63",
}


def plot_position(all_data):
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    colors = COLORS

    for name, data in all_data.items():
        dx = data["xs"] - data["xs"][0]
        dy = data["ys"] - data["ys"][0]
        dz = data["zs"] - data["zs"][0]
        dr = np.sqrt(dx**2 + dy**2 + dz**2)
        ts = data["ts"]
        c = colors[name]

        axes[0, 0].plot(ts, dx, "o-", color=c, markersize=4, label=name)
        axes[0, 1].plot(ts, dy, "o-", color=c, markersize=4, label=name)
        axes[1, 0].plot(ts, dz, "o-", color=c, markersize=4, label=name)
        axes[1, 1].plot(ts, dr, "o-", color=c, markersize=4, label=name)

    labels = [r"$\Delta x$ (nm)", r"$\Delta y$ (nm)",
              r"$\Delta z$ (nm)", r"$|\Delta \mathbf{r}|$ (nm)"]
    titles = ["x-drift", "y-drift", "z-drift", "Total displacement"]
    for ax, ylabel, title in zip(axes.flat, labels, titles):
        ax.set_xlabel("Time (ns)")
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
        ax.axhline(y=0, color="gray", linestyle="--", alpha=0.4)

    plt.suptitle("Hopfion Position Response to Spin Waves (5 combos)",
                 fontsize=13)
    plt.tight_layout()
    out = os.path.join(RESULTS_DIR, "hopfion_position_5combos.png")
    plt.savefig(out, dpi=200)
    plt.close()
    print(f"[fig] {out}")


def plot_core(all_data):
    fig, ax = plt.subplots(figsize=(8, 5))
    for name, data in all_data.items():
        ax.plot(data["ts"], data["cores"], "s-", color=COLORS[name],
                markersize=4, label=name)

    ax.set_xlabel("Time (ns)", fontsize=12)
    ax.set_ylabel("Core cells ($m_z < 0$)", fontsize=12)
    ax.set_title("Hopfion Core Size Under Spin Wave Driving", fontsize=13)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    out = os.path.join(RESULTS_DIR, "hopfion_core_5combos.png")
    plt.savefig(out, dpi=200)
    plt.close()
    print(f"[fig] {out}")


def plot_energy(all_data):
    fig, ax = plt.subplots(figsize=(8, 5))
    for name, data in all_data.items():
        ax.plot(data["t_table"], data["e_table"], "-", color=COLORS[name],
                linewidth=1, label=name, alpha=0.8)

    ax.set_xlabel("Time (ns)", fontsize=12)
    ax.set_ylabel("$E_{\\rm total}$ (J)", fontsize=12)
    ax.set_title("Total Energy Evolution Under Spin Wave Driving", fontsize=13)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    out = os.path.join(RESULTS_DIR, "energy_5combos.png")
    plt.savefig(out, dpi=200)
    plt.close()
    print(f"[fig] {out}")


def plot_perturbation_profiles(all_data):
    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    axes_flat = axes.flat

    coords_nm = np.linspace(-25, 25, 100, endpoint=False) + 0.25
    axis_labels = {0: "x", 1: "y", 2: "z"}

    for idx, (name, data) in enumerate(all_data.items()):
        ax = axes_flat[idx]
        src_label = axis_labels[data["src_axis"]]
        perp_label = "x" if data["src_axis"] == 1 else "y"

        ax.plot(coords_nm, data["profile_src"], "-",
                color=COLORS[name], linewidth=1.5,
                label=f"Along {src_label} (source axis)")
        ax.plot(coords_nm, data["profile_perp"], "--",
                color=COLORS[name], linewidth=1.5, alpha=0.6,
                label=f"Along {perp_label} (perp)")

        src_pos = -10
        ax.axvline(x=src_pos, color="red", linestyle=":", alpha=0.5,
                   label=f"Source ({src_label}={src_pos}nm)")
        ax.axvline(x=0, color="gray", linestyle=":", alpha=0.5,
                   label="Hopfion center")
        ax.axvspan(-25, -22.5, alpha=0.1, color="black")
        ax.axvspan(22.5, 25, alpha=0.1, color="black")

        ax.set_xlabel("Position (nm)")
        ax.set_ylabel(r"$|\Delta \mathbf{m}|$ (RMS)")
        ax.set_title(f"{name}: {COMBOS[name][1]}")
        ax.legend(fontsize=7)
        ax.grid(True, alpha=0.3)

    # Hide unused 6th subplot
    axes_flat[5].set_visible(False)

    plt.suptitle("Spin Wave Perturbation Profiles at t=0.5ns", fontsize=13)
    plt.tight_layout()
    out = os.path.join(RESULTS_DIR, "sw_perturbation_profiles.png")
    plt.savefig(out, dpi=200)
    plt.close()
    print(f"[fig] {out}")


def plot_perturbation_growth(all_data):
    fig, ax = plt.subplots(figsize=(8, 5))
    for name, data in all_data.items():
        dm_total = data["perturbations"][:, 3]
        ax.plot(data["ts"], dm_total, "o-", color=COLORS[name],
                markersize=4, label=name)

    ax.set_xlabel("Time (ns)", fontsize=12)
    ax.set_ylabel(r"$\langle|\Delta \mathbf{m}|\rangle$ (RMS)", fontsize=12)
    ax.set_title("Spin Wave Perturbation Growth", fontsize=13)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    out = os.path.join(RESULTS_DIR, "sw_perturbation_growth.png")
    plt.savefig(out, dpi=200)
    plt.close()
    print(f"[fig] {out}")


def write_summary(all_data):
    lines = [
        "=" * 80,
        "Spin Wave 4-Combo Analysis Summary",
        "=" * 80,
        "",
        f"{'Combo':<12} | {'dx(nm)':>8} | {'dy(nm)':>8} | {'dz(nm)':>8} | "
        f"{'|dr|(nm)':>8} | {'Core_0':>6} | {'Core_f':>6} | {'dm_rms':>10}",
        "-" * 80,
    ]

    for name, data in all_data.items():
        dx = data["xs"][-1] - data["xs"][0]
        dy = data["ys"][-1] - data["ys"][0]
        dz = data["zs"][-1] - data["zs"][0]
        dr = np.sqrt(dx**2 + dy**2 + dz**2)
        dm = data["perturbations"][-1, 3]
        lines.append(
            f"{name:<12} | {dx:+8.4f} | {dy:+8.4f} | {dz:+8.4f} | "
            f"{dr:8.4f} | {data['cores'][0]:6d} | {data['cores'][-1]:6d} | "
            f"{dm:10.4e}"
        )

    lines.extend([
        "",
        "E_total at t=0 and t=0.5ns:",
        "-" * 50,
    ])
    for name, data in all_data.items():
        lines.append(
            f"  {name:<12}: {data['e_table'][0]:.4e} -> "
            f"{data['e_table'][-1]:.4e} J  "
            f"(dE = {data['e_table'][-1] - data['e_table'][0]:+.4e})"
        )

    txt = "\n".join(lines)
    out = os.path.join(RESULTS_DIR, "analysis_summary.txt")
    with open(out, "w") as f:
        f.write(txt + "\n")
    print(f"\n[report] {out}")
    print("\n" + txt)


def main():
    print("=" * 60)
    print("  Spin Wave 5-Combo Comprehensive Analysis")
    print("=" * 60)

    all_data = {}
    for name, (dirname, desc) in COMBOS.items():
        all_data[name] = analyze_combo(name, dirname)

    print("\n" + "=" * 60)
    print("Generating figures...")
    plot_position(all_data)
    plot_core(all_data)
    plot_energy(all_data)
    plot_perturbation_profiles(all_data)
    plot_perturbation_growth(all_data)
    write_summary(all_data)
    print("\nDone.")


if __name__ == "__main__":
    main()
