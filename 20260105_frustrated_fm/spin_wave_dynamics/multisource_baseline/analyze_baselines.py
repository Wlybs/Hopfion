"""
Multi-Source Baseline Analysis
Compare 3 independent single-source configurations:
  1. srcX_vibX @ 200GHz (from freq_sweep/02ns/)
  2. srcZ(+z)_vibX @ 200GHz (from srcZ_freq_sweep/)
  3. srcZ(-z)_vibX @ 200GHz (from multisource_baseline/)

Output: direction rose plot + trajectory comparison + Hall angle table
"""

import os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, "/mnt/d/Research/Hopfion/scripts")
from hopfion_analysis import (extract_trajectory_phase_correlation,
                               compute_hall_angle)

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = "/mnt/d/Research/Hopfion/20260105_frustrated_fm/spin_wave_dynamics"
RESULTS_DIR = os.path.join(HERE, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

CONFIGS = {
    "srcX (+x)": {
        "out_dir": os.path.join(BASE, "freq_sweep/02ns/sw_f200GHz.out"),
        "dt_ns": 0.01,
        "sw_axis": "x",
        "color": "C0",
    },
    "srcZ(+z)": {
        "out_dir": os.path.join(BASE, "srcZ_freq_sweep/sw_srcZ_f200GHz.out"),
        "dt_ns": 0.01,
        "sw_axis": "z",
        "color": "C1",
    },
    "srcZ(-z)": {
        "out_dir": os.path.join(HERE, "sw_srcZ_neg_f200GHz.out"),
        "dt_ns": 0.01,
        "sw_axis": "z",  # propagation along -z, but axis is still z
        "color": "C2",
    },
}

results = {}
for name, cfg in CONFIGS.items():
    if not os.path.isdir(cfg["out_dir"]):
        print(f"SKIP {name}: {cfg['out_dir']} not found")
        continue
    print(f"Processing {name} ...")
    traj = extract_trajectory_phase_correlation(
        cfg["out_dir"], cfg["dt_ns"], verbose=False)
    ha = compute_hall_angle(traj, sw_propagation_axis=cfg["sw_axis"])
    results[name] = {"traj": traj, "hall": ha, "cfg": cfg}

# ── Plot 1: 3D trajectory comparison ──
fig, axes = plt.subplots(1, 3, figsize=(15, 5))
comp_labels = ["dx (nm)", "dy (nm)", "dz (nm)"]

for name, r in results.items():
    traj = r["traj"]
    ts = [d[0] for d in traj]
    shifts = np.array([d[1] for d in traj])
    color = r["cfg"]["color"]
    for i, ax in enumerate(axes):
        ax.plot(ts, shifts[:, i], label=name, color=color, linewidth=1.5)

for i, ax in enumerate(axes):
    ax.set_xlabel("Time (ns)", fontsize=11)
    ax.set_ylabel(comp_labels[i], fontsize=11)
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)

fig.suptitle("Single-Source Baseline: Hopfion Displacement Components\n"
             "f=200GHz, B=1T, vibX", fontsize=13)
fig.tight_layout()
fig.savefig(os.path.join(RESULTS_DIR, "baseline_trajectories.png"), dpi=150)
plt.close(fig)
print("Saved: baseline_trajectories.png")

# ── Plot 2: Direction rose plot (polar) ──
fig, ax = plt.subplots(subplot_kw=dict(projection='polar'), figsize=(8, 8))

for name, r in results.items():
    traj = r["traj"]
    shifts = np.array([d[1] for d in traj])
    # Final displacement vector in xz plane (primary motion plane)
    dx_final = shifts[-1, 0]
    dz_final = shifts[-1, 2]
    angle = np.arctan2(dz_final, dx_final)
    magnitude = np.sqrt(dx_final**2 + dz_final**2)
    color = r["cfg"]["color"]
    ax.annotate("", xy=(angle, magnitude), xytext=(0, 0),
                arrowprops=dict(arrowstyle="->", color=color, lw=2.5))
    ax.scatter([angle], [magnitude], color=color, s=80, zorder=5)
    # Label at arrow tip
    ax.annotate(f"{name}\n({magnitude:.2f}nm)",
                xy=(angle, magnitude), fontsize=9,
                ha='center', va='bottom')

ax.set_title("Motion Direction Rose Plot (xz plane)\n"
             "Arrow = final displacement vector", fontsize=12, pad=20)
fig.tight_layout()
fig.savefig(os.path.join(RESULTS_DIR, "direction_rose_plot.png"), dpi=150)
plt.close(fig)
print("Saved: direction_rose_plot.png")

# ── Summary table ──
with open(os.path.join(RESULTS_DIR, "baseline_summary.txt"), "w") as f:
    f.write(f"{'Config':>12s} {'θ_H(deg)':>9s} {'±err':>7s} "
            f"{'v_par':>8s} {'v_perp':>8s} {'|dr|':>8s} {'valid':>6s}\n")
    f.write("-" * 62 + "\n")
    for name, r in results.items():
        h = r['hall']
        f.write(f"{name:>12s} {h['theta_H_deg']:>8.1f} "
                f"{h['theta_H_err_deg']:>7.1f} {h['v_parallel']:>8.2f} "
                f"{h['v_perp']:>8.2f} {h['displacement_total_nm']:>8.3f} "
                f"{'Y' if h['valid'] else 'N':>5s}\n")
print("Saved: baseline_summary.txt")
