"""
freq_sweep — 运动模式分析（02ns 数据集）
对 100-1000GHz 10个频率点用相位相关法提取位移轨迹，绘制:
  1. r(t) 位移轨迹（分量 + 总位移）
  2. v(t) = dr/dt 速度（向量微分）
  3. a(t) = dv/dt 加速度
  4. 运动模式分类汇总表

数据源: freq_sweep/02ns/
输出:   freq_sweep/results/
"""

import os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, "/mnt/d/Research/Hopfion/95_shared_scripts")
from hopfion_analysis import extract_trajectory_phase_correlation

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(HERE, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

FREQS_GHZ = list(range(100, 1100, 100))
DT_NS = 0.01  # 10ps autosave


def extract_full_trajectory(out_dir):
    return extract_trajectory_phase_correlation(out_dir, DT_NS, verbose=False)


def classify_motion(ts, speed, accel_mag, dr):
    """Classify motion mode based on speed and acceleration."""
    if len(ts) < 3:
        return "insufficient_data"
    if max(dr) < 0.1:
        return "static"

    # Skip initial transient (first 1/3)
    n3 = len(ts) // 3
    speed_late = speed[n3:]
    accel_late = accel_mag[n3:]
    speed_mean = np.mean(speed_late)

    if speed_mean < 0.5:
        return "weak_response"

    # Acceleration trend: fit speed(t) to linear
    t_late = np.array(ts[n3:])
    s_late = np.array(speed_late)
    if len(t_late) > 2:
        slope = np.polyfit(t_late, s_late, 1)[0]
        rel_accel = abs(slope) / speed_mean if speed_mean > 0 else 0
        if rel_accel > 2.0:
            return "accelerating"

    # Check for oscillatory: dr goes up then down
    dr_arr = np.array(dr)
    peak_idx = np.argmax(dr_arr)
    if peak_idx < len(dr_arr) - 2 and dr_arr[-1] < 0.7 * dr_arr[peak_idx]:
        return "oscillatory"

    accel_mean = np.mean(accel_late)
    if accel_mean > 0.3 * speed_mean and speed_mean > 1.0:
        return "accelerating"

    return "steady"


def main():
    print("=" * 60)
    print("  freq_sweep: Motion Mode Analysis (phase correlation)")
    print("=" * 60)

    all_data = {}
    for freq in FREQS_GHZ:
        out_dir = os.path.join(HERE, "02ns", f"sw_f{freq}GHz.out")
        if not os.path.isdir(out_dir):
            print(f"  [SKIP] f={freq}GHz")
            continue
        print(f"  f={freq}GHz ...", end="", flush=True)
        traj = extract_full_trajectory(out_dir)
        all_data[freq] = traj
        dr_final = np.linalg.norm(traj[-1][1]) if traj else 0.0
        print(f" {len(traj)} frames, dr={dr_final:.3f} nm")

    # --- Compute derived quantities ---
    freq_profiles = {}
    for freq, traj in all_data.items():
        valid = [d for d in traj if not np.any(np.isnan(d[1]))]
        if len(valid) < 2:
            continue

        ts = np.array([d[0] for d in valid])
        shifts = np.array([d[1] for d in valid])   # (N, 3) nm
        cores = [d[2] for d in valid]

        dx = shifts[:, 0]
        dy = shifts[:, 1]
        dz = shifts[:, 2]
        dr = np.linalg.norm(shifts, axis=1)

        # v = dr/dt (向量微分)
        vx = np.gradient(dx, ts)
        vy = np.gradient(dy, ts)
        vz = np.gradient(dz, ts)
        speed = np.sqrt(vx**2 + vy**2 + vz**2)

        # a = dv/dt
        ax = np.gradient(vx, ts)
        ay = np.gradient(vy, ts)
        az = np.gradient(vz, ts)
        accel_mag = np.sqrt(ax**2 + ay**2 + az**2)

        mode = classify_motion(ts.tolist(), speed.tolist(),
                               accel_mag.tolist(), dr.tolist())
        freq_profiles[freq] = {
            "ts": ts, "dx": dx, "dy": dy, "dz": dz, "dr": dr,
            "vx": vx, "vy": vy, "vz": vz, "speed": speed,
            "ax": ax, "ay": ay, "az": az, "accel": accel_mag,
            "cores": cores, "mode": mode,
        }

    # --- Fig 1: displacement r(t) ---
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    colors = plt.cm.tab10(np.linspace(0, 1, 10))

    for (freq, p), color in zip(freq_profiles.items(), colors):
        label = f"{freq}GHz"
        axes[0, 0].plot(p["ts"], p["dr"], 'o-', color=color, label=label, ms=3, lw=1.5)
        axes[0, 1].plot(p["ts"], p["dx"], 'o-', color=color, label=label, ms=3, lw=1.5)
        axes[1, 0].plot(p["ts"], p["dz"], 'o-', color=color, label=label, ms=3, lw=1.5)
        axes[1, 1].plot(p["ts"], p["cores"], 'o-', color=color, label=label, ms=3, lw=1.5)

    for ax, title, ylabel in zip(axes.flat,
        ["|r(t)-r(0)| total displacement", "dx(t)", "dz(t)", "Core voxel count"],
        ["|dr| (nm)", "dx (nm)", "dz (nm)", "Core voxels"]):
        ax.set_xlabel("Time (ns)")
        ax.set_ylabel(ylabel)
        ax.set_title(title, fontsize=11)
        ax.legend(fontsize=7, ncol=2)
        ax.grid(True, alpha=0.3)

    plt.suptitle("Frequency Sweep: Hopfion Displacement r(t)", fontsize=13)
    plt.tight_layout()
    plt.savefig(os.path.join(RESULTS_DIR, "displacement_all_freq.png"), dpi=200)
    plt.close()
    print(f"\n[fig] results/displacement_all_freq.png")

    # --- Fig 2: speed |v|(t) and vz(t) ---
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    for (freq, p), color in zip(freq_profiles.items(), colors):
        label = f"{freq}GHz ({p['mode']})"
        axes[0].plot(p["ts"], p["speed"], 'o-', color=color, label=label, ms=3, lw=1.5)
        axes[1].plot(p["ts"], p["vz"], 'o-', color=color, label=label, ms=3, lw=1.5)

    axes[0].set_ylabel("|v| (nm/ns)")
    axes[0].set_title("Speed |v(t)| = |dr/dt|")
    axes[1].set_ylabel("vz (nm/ns)")
    axes[1].set_title("vz(t) = dz/dt (dominant component)")
    for ax in axes:
        ax.set_xlabel("Time (ns)")
        ax.legend(fontsize=7, ncol=2)
        ax.grid(True, alpha=0.3)
    axes[1].axhline(0, color='k', lw=0.5)

    plt.suptitle("Velocity Profile v(t) = dr/dt", fontsize=13)
    plt.tight_layout()
    plt.savefig(os.path.join(RESULTS_DIR, "velocity_all_freq.png"), dpi=200)
    plt.close()
    print(f"[fig] results/velocity_all_freq.png")

    # --- Fig 3: frequency map ---
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    freqs = sorted(freq_profiles.keys())
    n3 = lambda arr: arr[len(arr)//3:]

    # Mean speed (skip transient)
    mean_speed = [np.mean(n3(freq_profiles[f]["speed"])) for f in freqs]
    mean_accel = [np.mean(n3(freq_profiles[f]["accel"])) for f in freqs]
    final_dr = [freq_profiles[f]["dr"][-1] for f in freqs]
    modes = [freq_profiles[f]["mode"] for f in freqs]

    mode_colors = {
        "static": "gray", "weak_response": "lightblue",
        "steady": "green", "accelerating": "orange",
        "intermittent": "purple", "oscillatory": "red",
        "transient": "yellow"
    }
    bar_colors = [mode_colors.get(m, "black") for m in modes]

    axes[0].bar([f/1000 for f in freqs], final_dr, color=bar_colors, width=0.08, edgecolor='k')
    axes[0].set_xlabel("Frequency (THz)")
    axes[0].set_ylabel("|dr| @ 0.2ns (nm)")
    axes[0].set_title("Final displacement")

    axes[1].bar([f/1000 for f in freqs], mean_speed, color=bar_colors, width=0.08, edgecolor='k')
    axes[1].set_xlabel("Frequency (THz)")
    axes[1].set_ylabel("Mean |v| (nm/ns)")
    axes[1].set_title("Mean speed (skip 1/3 transient)")

    axes[2].bar([f/1000 for f in freqs], mean_accel, color=bar_colors, width=0.08, edgecolor='k')
    axes[2].set_xlabel("Frequency (THz)")
    axes[2].set_ylabel("Mean |a| (nm/ns²)")
    axes[2].set_title("Mean acceleration")

    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor=c, edgecolor='k', label=m)
                       for m, c in mode_colors.items() if m in modes]
    axes[0].legend(handles=legend_elements, fontsize=8, loc='upper left')

    for ax in axes:
        ax.grid(True, alpha=0.3)

    plt.suptitle("Motion Mode Frequency Map", fontsize=13)
    plt.tight_layout()
    plt.savefig(os.path.join(RESULTS_DIR, "motion_mode_map.png"), dpi=200)
    plt.close()
    print(f"[fig] results/motion_mode_map.png")

    # --- Summary table ---
    lines = [
        "freq(GHz) | |dr|(nm) |  dz(nm)  | v_mean(nm/ns) | a_mean(nm/ns²) | Core_0 | Core_f | Mode",
        "-" * 100
    ]
    for freq in freqs:
        p = freq_profiles[freq]
        n3_idx = len(p["ts"]) // 3
        lines.append(
            f"  {freq:4d}     | {p['dr'][-1]:7.3f} | {p['dz'][-1]:+8.3f} "
            f"| {np.mean(p['speed'][n3_idx:]):13.2f} | {np.mean(p['accel'][n3_idx:]):14.2f} "
            f"| {p['cores'][0]:6d} | {p['cores'][-1]:6d} | {p['mode']}"
        )

    txt = "\n".join(lines)
    with open(os.path.join(RESULTS_DIR, "motion_mode_summary.txt"), "w") as f:
        f.write(txt + "\n")
    print(f"\n[report] results/motion_mode_summary.txt")
    print("\n" + txt)


if __name__ == "__main__":
    main()
