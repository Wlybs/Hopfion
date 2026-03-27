"""
Hall Angle Analysis — freq_sweep data
Extract theta_H(f) from existing 02ns (10 freq) + 05ns (4 freq) datasets.

Data: freq_sweep/02ns/ + freq_sweep/05ns/
Output: freq_sweep/results/
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
RESULTS_DIR = os.path.join(HERE, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

# ── Data sources ──
DATASETS = {
    "02ns": {
        "dir": os.path.join(HERE, "02ns"),
        "freqs_ghz": list(range(100, 1100, 100)),
        "dt_ns": 0.01,
        "pattern": "sw_f{freq}GHz.out",
    },
    "05ns": {
        "dir": os.path.join(HERE, "05ns"),
        "freqs_ghz": [300, 400, 900, 1000],
        "dt_ns": 0.01,
        "pattern": "sw_f{freq}GHz.out",
    },
}


def analyze_one(out_dir, dt_ns, freq_ghz):
    """Extract trajectory and compute Hall angle for one frequency."""
    traj = extract_trajectory_phase_correlation(out_dir, dt_ns, verbose=False)
    if len(traj) < 3:
        return None
    ha = compute_hall_angle(traj, sw_propagation_axis='x')
    ha['freq_ghz'] = freq_ghz
    ha['traj'] = traj  # keep for time-resolved plot
    return ha


def compute_theta_h_time_series(traj, sw_axis='x'):
    """Compute theta_H(t) from cumulative displacement at each frame."""
    axis_map = {'x': 0, 'y': 1, 'z': 2}
    par_idx = axis_map[sw_axis]
    perp_indices = [i for i in range(3) if i != par_idx]

    ts, thetas = [], []
    for t_ns, shift, _ in traj:
        if t_ns == 0:
            continue
        d_par = shift[par_idx]
        d_perp = np.linalg.norm(shift[perp_indices])
        theta = np.degrees(np.arctan2(d_perp, abs(d_par)))
        ts.append(t_ns)
        thetas.append(theta)
    return np.array(ts), np.array(thetas)


# ── Main ──
all_results = {}

for ds_name, ds in DATASETS.items():
    for freq in ds["freqs_ghz"]:
        out_dir = os.path.join(ds["dir"], ds["pattern"].format(freq=freq))
        if not os.path.isdir(out_dir):
            print(f"SKIP {ds_name}/{freq}GHz: no output dir")
            continue
        print(f"Processing {ds_name}/{freq}GHz ...")
        result = analyze_one(out_dir, ds["dt_ns"], freq)
        if result:
            key = (ds_name, freq)
            all_results[key] = result

# ── Plot 1: theta_H vs frequency ──
fig, ax = plt.subplots(figsize=(10, 6))

for ds_name, marker, color in [("02ns", "o", "C0"), ("05ns", "s", "C1")]:
    freqs, angles, errs, valids = [], [], [], []
    for (dn, f), r in sorted(all_results.items()):
        if dn != ds_name:
            continue
        freqs.append(f)
        angles.append(r['theta_H_deg'])
        errs.append(r['theta_H_err_deg'])
        valids.append(r['valid'])

    freqs, angles, errs, valids = map(np.array, [freqs, angles, errs, valids])
    # Plot valid points with error bars
    mask = valids.astype(bool)
    if mask.any():
        ax.errorbar(freqs[mask], angles[mask], yerr=errs[mask],
                     fmt=marker, color=color, capsize=3,
                     label=f"{ds_name} (valid)", markersize=8)
    if (~mask).any():
        ax.scatter(freqs[~mask], angles[~mask],
                   marker='x', color='gray', s=60, zorder=5,
                   label=f"{ds_name} (|dr|<0.1nm)")

ax.set_xlabel("Frequency (GHz)", fontsize=13)
ax.set_ylabel("Hall angle θ_H (deg)", fontsize=13)
ax.set_title("Topological Hall Angle vs Spin Wave Frequency\n"
             "srcX_vibX, B=1T, Q_H=1 Frustrated FM Hopfion", fontsize=13)
ax.set_ylim(0, 95)
ax.axhline(90, ls='--', color='gray', alpha=0.5, label='θ_H = 90°')
ax.legend(fontsize=10)
ax.grid(True, alpha=0.3)
fig.tight_layout()
fig.savefig(os.path.join(RESULTS_DIR, "hall_angle_vs_freq.png"), dpi=150)
plt.close(fig)
print(f"Saved: hall_angle_vs_freq.png")

# ── Plot 2: theta_H(t) time-resolved ──
fig, axes = plt.subplots(2, 1, figsize=(12, 10), sharex=False)

for ax_i, ds_name in enumerate(["02ns", "05ns"]):
    ax = axes[ax_i]
    for (dn, f), r in sorted(all_results.items()):
        if dn != ds_name or not r['valid']:
            continue
        ts, thetas = compute_theta_h_time_series(r['traj'])
        ax.plot(ts, thetas, label=f"{f} GHz", linewidth=1.5)
    ax.set_ylabel("θ_H(t) (deg)", fontsize=12)
    ax.set_title(f"{ds_name} dataset", fontsize=12)
    ax.set_ylim(0, 100)
    ax.axhline(90, ls='--', color='gray', alpha=0.5)
    ax.legend(fontsize=9, ncol=2)
    ax.grid(True, alpha=0.3)

axes[-1].set_xlabel("Time (ns)", fontsize=12)
fig.suptitle("Time-Resolved Hall Angle θ_H(t)", fontsize=14, y=1.01)
fig.tight_layout()
fig.savefig(os.path.join(RESULTS_DIR, "hall_angle_time_resolved.png"), dpi=150)
plt.close(fig)
print(f"Saved: hall_angle_time_resolved.png")

# ── Summary table ──
with open(os.path.join(RESULTS_DIR, "hall_angle_summary.txt"), "w") as f:
    f.write(f"{'Dataset':>6s} {'Freq':>6s} {'θ_H':>8s} {'±err':>8s} "
            f"{'v_par':>8s} {'v_perp':>8s} {'|dr|':>8s} {'valid':>6s}\n")
    f.write("-" * 62 + "\n")
    for (ds, freq), r in sorted(all_results.items()):
        f.write(f"{ds:>6s} {freq:>5d}  {r['theta_H_deg']:>7.1f}  "
                f"{r['theta_H_err_deg']:>7.1f}  {r['v_parallel']:>7.2f}  "
                f"{r['v_perp']:>7.2f}  {r['displacement_total_nm']:>7.3f}  "
                f"{'Y' if r['valid'] else 'N':>5s}\n")
    print(f"Saved: hall_angle_summary.txt")
