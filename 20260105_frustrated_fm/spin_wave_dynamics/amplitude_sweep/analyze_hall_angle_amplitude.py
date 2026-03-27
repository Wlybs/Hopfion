"""
Hall Angle vs Amplitude — amplitude_sweep data
Extract theta_H(B) from existing 440GHz amplitude sweep (6 points).

Data: amplitude_sweep/sw_B*.out/
Output: amplitude_sweep/results/
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

# B values and corresponding output directories
B_VALUES = [0.05, 0.1, 0.2, 0.5, 1.0, 2.0]
B_LABELS = ["0p05T", "0p1T", "0p2T", "0p5T", "1p0T", "2p0T"]
# Autosave = 50ps, runtime = 0.5ns -> 11 frames, dt = 0.05 ns
DT_NS = 0.05

results = []
for B, label in zip(B_VALUES, B_LABELS):
    out_dir = os.path.join(HERE, f"sw_B{label}.out")
    if not os.path.isdir(out_dir):
        print(f"SKIP B={B}T: not found")
        continue

    n_ovf = len([f for f in os.listdir(out_dir)
                 if f.startswith("m") and f.endswith(".ovf")])
    print(f"Processing B={B}T ({n_ovf} frames, dt={DT_NS}ns) ...")
    traj = extract_trajectory_phase_correlation(out_dir, DT_NS, verbose=False)
    ha = compute_hall_angle(traj, sw_propagation_axis='x')
    ha['B'] = B
    results.append(ha)

# ── Plot ──
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

Bs = [r['B'] for r in results]
thetas = [r['theta_H_deg'] for r in results]
errs = [r['theta_H_err_deg'] for r in results]
valids = [r['valid'] for r in results]
v_perps = [r['v_perp'] for r in results]

mask = np.array(valids, dtype=bool)
Bs, thetas, errs, v_perps = map(np.array, [Bs, thetas, errs, v_perps])

# Panel 1: theta_H vs B
if mask.any():
    ax1.errorbar(Bs[mask], thetas[mask], yerr=errs[mask],
                 fmt='o-', capsize=4, markersize=8, color='C0')
if (~mask).any():
    ax1.scatter(Bs[~mask], thetas[~mask], marker='x', color='gray', s=80)
ax1.set_xlabel("Spin Wave Amplitude B (T)", fontsize=12)
ax1.set_ylabel("Hall Angle θ_H (deg)", fontsize=12)
ax1.set_xscale('log')
ax1.set_ylim(0, 95)
ax1.axhline(90, ls='--', color='gray', alpha=0.5)
ax1.set_title("θ_H vs Amplitude (440 GHz)", fontsize=12)
ax1.grid(True, alpha=0.3)

# Panel 2: v_perp vs B (speed scaling)
if mask.any():
    ax2.plot(Bs[mask], np.abs(v_perps[mask]), 'o-', markersize=8, color='C1')
    # Fit power law v = a * B^n
    log_B = np.log(Bs[mask])
    log_v = np.log(np.abs(v_perps[mask]) + 1e-10)
    if len(log_B) > 2:
        coeffs = np.polyfit(log_B, log_v, 1)
        n_exp = coeffs[0]
        B_fit = np.logspace(np.log10(Bs[mask].min()), np.log10(Bs[mask].max()), 50)
        v_fit = np.exp(coeffs[1]) * B_fit**n_exp
        ax2.plot(B_fit, v_fit, '--', color='C1', alpha=0.7,
                 label=f"fit: v ∝ B^{n_exp:.2f}")
        ax2.legend(fontsize=11)

ax2.set_xlabel("Spin Wave Amplitude B (T)", fontsize=12)
ax2.set_ylabel("|v_perp| (nm/ns)", fontsize=12)
ax2.set_xscale('log')
ax2.set_yscale('log')
ax2.set_title("Perpendicular Speed vs Amplitude", fontsize=12)
ax2.grid(True, alpha=0.3)

fig.suptitle("Hall Angle & Speed Scaling — Amplitude Sweep", fontsize=14)
fig.tight_layout()
fig.savefig(os.path.join(RESULTS_DIR, "hall_angle_vs_amplitude.png"), dpi=150)
plt.close(fig)
print("Saved: hall_angle_vs_amplitude.png")

# ── Print summary table ──
print("\n=== Summary ===")
print(f"{'B(T)':>8} {'theta_H':>10} {'err':>8} {'v_perp':>10} {'v_par':>10} {'disp_nm':>10} {'valid':>6}")
for r in results:
    print(f"{r['B']:>8.3f} {r['theta_H_deg']:>10.2f} {r['theta_H_err_deg']:>8.2f} "
          f"{r['v_perp']:>10.3f} {r['v_parallel']:>10.3f} "
          f"{r['displacement_total_nm']:>10.3f} {str(r['valid']):>6}")
