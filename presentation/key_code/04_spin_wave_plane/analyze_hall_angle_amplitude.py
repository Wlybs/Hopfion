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
from paper_style import (setup_paper_style, COLORS, save_paper_fig,
                          panel_label, legend_above)

setup_paper_style()

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

# ── Plot (paper style) ──
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.4))

Bs = [r['B'] for r in results]
thetas = [r['theta_H_deg'] for r in results]
errs = [r['theta_H_err_deg'] for r in results]
valids = [r['valid'] for r in results]
v_perps = [r['v_perp'] for r in results]

mask = np.array(valids, dtype=bool)
Bs, thetas, errs, v_perps = map(np.array, [Bs, thetas, errs, v_perps])

# Panel (a): theta_H vs B
if mask.any():
    ax1.errorbar(Bs[mask], thetas[mask], yerr=errs[mask],
                 fmt="o-", capsize=3, color=COLORS["primary"])
if (~mask).any():
    ax1.scatter(Bs[~mask], thetas[~mask], marker="x", color="gray", s=40)
ax1.axhline(90, ls="--", color="gray", linewidth=1.0)
ax1.set_xlabel(r"自旋波幅度 $B$ (T)")
ax1.set_ylabel(r"霍尔角 $\theta_H$ (°)")
ax1.set_xscale("log")
ax1.set_ylim(0, 95)

# Panel (b): v_perp vs B
if mask.any():
    ax2.plot(Bs[mask], np.abs(v_perps[mask]), "o-", color=COLORS["primary"],
             label=r"数据")
    log_B = np.log(Bs[mask])
    log_v = np.log(np.abs(v_perps[mask]) + 1e-10)
    if len(log_B) > 2:
        coeffs = np.polyfit(log_B, log_v, 1)
        n_exp = coeffs[0]
        B_fit = np.logspace(np.log10(Bs[mask].min()),
                            np.log10(Bs[mask].max()), 50)
        v_fit = np.exp(coeffs[1]) * B_fit**n_exp
        ax2.plot(B_fit, v_fit, "--", color=COLORS["secondary"],
                 label=rf"$v \propto B^{{{n_exp:.2f}}}$")
        legend_above(ax2, ncol=2)

ax2.set_xlabel(r"自旋波幅度 $B$ (T)")
ax2.set_ylabel(r"$|v_\perp|$ (nm$\cdot$ns$^{-1}$)")
ax2.set_xscale("log")
ax2.set_yscale("log")

panel_label(fig, ax1, "(a)")
panel_label(fig, ax2, "(b)")

out_png = os.path.join(RESULTS_DIR, "hall_angle_vs_amplitude.png")
save_paper_fig(fig, out_png)
plt.close(fig)
print(f"Saved: {out_png}")

# ── Print summary table ──
print("\n=== Summary ===")
print(f"{'B(T)':>8} {'theta_H':>10} {'err':>8} {'v_perp':>10} {'v_par':>10} {'disp_nm':>10} {'valid':>6}")
for r in results:
    print(f"{r['B']:>8.3f} {r['theta_H_deg']:>10.2f} {r['theta_H_err_deg']:>8.2f} "
          f"{r['v_perp']:>10.3f} {r['v_parallel']:>10.3f} "
          f"{r['displacement_total_nm']:>10.3f} {str(r['valid']):>6}")
