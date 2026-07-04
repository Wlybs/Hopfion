"""
srcZ@1100GHz 幅度扫描 v-B 标度律分析

输入: plane_wave_srcZ/sw_srcZ_B*T.out/ (6组, 1100GHz)
输出: results/scaling_srcZ_1100GHz.png + results/scaling_srcZ_1100GHz.txt

物理量:
  - v̄ = 稳态平均速度（跳过前1/3暂态）
  - dr_final = 最终总位移大小
  - 噪声地板: |dr_final| < 0.1nm 的点排除出拟合

拟合: log(v) = n*log(B) + log(c)  =>  v = c * B^n
"""

import sys
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, "/mnt/d/Research/Hopfion/95_shared_scripts")
from hopfion_analysis import extract_trajectory_phase_correlation

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(HERE, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

AMPS = [0.1, 0.2, 0.5, 1.0, 1.5, 2.0]  # Tesla
DT_NS = 0.005   # 5ps autosave
NOISE_FLOOR_NM = 0.1  # nm


def amp_to_label(b):
    """0.1 -> '0p1', 1.0 -> '1p0', 1.5 -> '1p5'"""
    return f"{b:.1f}".replace(".", "p")


def main():
    print("=== srcZ@1100GHz 幅度扫描分析 ===\n")

    results = []  # (B, v_mean, dz_final, dr_final, core0, core_f)

    for b in AMPS:
        label = amp_to_label(b)
        out_dir = os.path.join(HERE, f"sw_srcZ_B{label}T.out")

        if not os.path.isdir(out_dir):
            print(f"  [SKIP] B={b}T: {out_dir} not found")
            continue

        print(f"  B={b}T ...", end=" ", flush=True)
        traj = extract_trajectory_phase_correlation(out_dir, DT_NS, verbose=False)

        if len(traj) < 3:
            print(f"too few frames ({len(traj)}), skip")
            continue

        ts = np.array([r[0] for r in traj])
        dx = np.array([r[1][0] for r in traj])
        dy = np.array([r[1][1] for r in traj])
        dz = np.array([r[1][2] for r in traj])
        dr = np.sqrt(dx**2 + dy**2 + dz**2)
        cores = np.array([r[2] for r in traj])

        # Vector velocity
        vx = np.gradient(dx, ts)
        vy = np.gradient(dy, ts)
        vz = np.gradient(dz, ts)
        speed = np.sqrt(vx**2 + vy**2 + vz**2)

        # Skip first 1/3 transient
        skip = max(1, len(ts) // 3)
        v_mean = float(np.mean(speed[skip:]))
        dz_final = float(dz[-1])
        dr_final = float(dr[-1])
        core0 = int(cores[0])
        core_f = int(cores[-1])

        print(f"dz={dz_final:+.3f}nm  |dr|={dr_final:.3f}nm  v̄={v_mean:.3f}nm/ns  core={core0}→{core_f}")
        results.append((b, v_mean, dz_final, dr_final, core0, core_f))

    if not results:
        print("ERROR: no data found")
        return

    Bs = np.array([r[0] for r in results])
    vs = np.array([r[1] for r in results])
    dzs = np.array([r[2] for r in results])
    drs = np.array([r[3] for r in results])
    core0s = np.array([r[4] for r in results])
    corefs = np.array([r[5] for r in results])

    # Noise floor filtering
    above_floor = drs >= NOISE_FLOOR_NM
    excluded = [results[i][0] for i in range(len(results)) if not above_floor[i]]
    fit_Bs = Bs[above_floor]
    fit_vs = vs[above_floor]

    print(f"\n噪声地板过滤 (|dr| < {NOISE_FLOOR_NM}nm):")
    if excluded:
        print(f"  排除: B = {excluded} T")
    else:
        print(f"  无排除点")
    print(f"  拟合点数: {len(fit_Bs)}")

    # Power-law fit in log space
    fit_ok = False
    n_fit = c_fit = r2 = np.nan
    if len(fit_Bs) >= 2:
        log_B = np.log(fit_Bs)
        log_v = np.log(fit_vs)
        coeffs = np.polyfit(log_B, log_v, 1)
        n_fit = coeffs[0]
        c_fit = np.exp(coeffs[1])
        log_v_pred = np.polyval(coeffs, log_B)
        ss_res = np.sum((log_v - log_v_pred)**2)
        ss_tot = np.sum((log_v - np.mean(log_v))**2)
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else np.nan
        fit_ok = True
        print(f"\n拟合结果: v = {c_fit:.4f} × B^{n_fit:.3f}")
        print(f"  R² = {r2:.4f}")

    # Core count stability
    print("\n核心计数稳定性检查 (阈值 15%):")
    for i, (b, _, _, _, c0, cf) in enumerate(results):
        if c0 > 0:
            frac = abs(cf - c0) / c0
            status = "OK" if frac < 0.15 else "WARN"
            print(f"  B={b}T: {c0} → {cf}  ({frac*100:.1f}%)  [{status}]")

    # --- Figure: dual panel (scaling + dz trajectory) ---
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.5))

    # Panel 1: v-B scaling
    excl_mask = ~above_floor
    if np.any(excl_mask):
        ax1.scatter(Bs[excl_mask], vs[excl_mask], marker='x', s=80, color='gray',
                    label=f'below noise floor', zorder=3)
    ax1.scatter(fit_Bs, fit_vs, marker='o', s=80, color='C1',
                label='1100GHz data', zorder=4)
    if fit_ok:
        B_line = np.logspace(np.log10(fit_Bs.min() * 0.8),
                             np.log10(fit_Bs.max() * 1.2), 100)
        v_line = c_fit * B_line**n_fit
        ax1.plot(B_line, v_line, '--', color='C1', linewidth=1.5,
                 label=f'fit: v ∝ B$^{{{n_fit:.2f}}}$  (R²={r2:.3f})')
    ax1.set_xscale('log')
    ax1.set_yscale('log')
    ax1.set_xlabel('Spin wave amplitude B₀ (T)', fontsize=12)
    ax1.set_ylabel('Mean speed v̄ (nm/ns)', fontsize=12)
    ax1.set_title('v–B Scaling @ 1100 GHz (srcZ_vibX)', fontsize=13)
    ax1.legend(fontsize=10)
    ax1.grid(True, which='both', alpha=0.3)

    # Panel 2: dz vs B bar chart
    colors = ['#ff7f0e' if above_floor[i] else '#cccccc' for i in range(len(Bs))]
    ax2.bar(range(len(Bs)), dzs, color=colors, edgecolor='black', linewidth=0.5)
    ax2.set_xticks(range(len(Bs)))
    ax2.set_xticklabels([f'{b:.1f}' for b in Bs])
    ax2.set_xlabel('B₀ (T)', fontsize=12)
    ax2.set_ylabel('Final z-displacement dz (nm)', fontsize=12)
    ax2.set_title('z-Displacement vs Amplitude @ 1100 GHz', fontsize=13)
    ax2.axhline(0, color='k', linewidth=0.8)
    ax2.grid(True, axis='y', alpha=0.3)

    plt.tight_layout()
    out_png = os.path.join(RESULTS_DIR, "scaling_srcZ_1100GHz.png")
    fig.savefig(out_png, dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f"\nSaved: {out_png}")

    # --- Text summary ---
    lines = [
        "=" * 70,
        "srcZ@1100GHz Amplitude Sweep v-B Scaling Summary",
        "=" * 70, "",
        f"{'B (T)':<10} {'v̄ (nm/ns)':<14} {'dz (nm)':<12} {'|dr| (nm)':<12} {'core0':<8} {'core_f':<8} {'note'}",
        "-" * 75,
    ]
    for i, (b, v, dz, dr, c0, cf) in enumerate(results):
        note = "below_noise_floor" if not above_floor[i] else ""
        lines.append(f"{b:<10.1f} {v:<14.4f} {dz:<+12.4f} {dr:<12.4f} {c0:<8} {cf:<8} {note}")
    lines.append("")
    if fit_ok:
        lines.append(f"Power-law fit (above noise floor):")
        lines.append(f"  v = {c_fit:.6f} * B^{n_fit:.4f}")
        lines.append(f"  R² = {r2:.4f}")
        lines.append(f"  Fitted points: B = {list(fit_Bs)} T")
    if excluded:
        lines.append(f"Excluded: B = {excluded} T")
    lines.append("")

    out_txt = os.path.join(RESULTS_DIR, "scaling_srcZ_1100GHz.txt")
    with open(out_txt, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"Saved: {out_txt}")

    return n_fit, c_fit, r2


if __name__ == "__main__":
    main()
