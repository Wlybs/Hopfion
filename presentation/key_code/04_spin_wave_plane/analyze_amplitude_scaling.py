"""
440GHz 幅度扫描 v-B 标度律分析

输入: amplitude_sweep/sw_B*T.out/ (6组, 440GHz)
输出: results/scaling_440GHz.png + results/scaling_440GHz.txt

物理量:
  - v̄ = 稳态平均速度（跳过前1/3暂态）
  - dr_final = 最终总位移大小
  - 噪声地板: |dr_final| < 0.1nm 的点排除出拟合

拟合: log(v) = n*log(B) + log(c)  =>  v = c * B^n
"""

import sys
import os
import numpy as np
import matplotlib.pyplot as plt

sys.path.insert(0, "/mnt/d/Research/Hopfion/scripts")
from hopfion_analysis import extract_trajectory_phase_correlation
from paper_style import (setup_paper_style, COLORS, save_paper_fig, legend_above)

setup_paper_style()

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(HERE, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

AMPS = [0.05, 0.1, 0.2, 0.5, 1.0, 2.0]  # Tesla
DT_NS = 0.05   # 50ps autosave
NOISE_FLOOR_NM = 0.1  # nm


def amp_to_label(b):
    """0.05 -> '0p05', 0.1 -> '0p1', 1.0 -> '1p0'"""
    s = f"{b:.2f}".rstrip("0")
    if s.endswith("."):
        s += "0"
    return s.replace(".", "p")


def analyze_440GHz():
    print("=== 440GHz 幅度扫描分析 ===\n")

    results = []  # (B, v_mean, dr_final, core0, core_f)

    for b in AMPS:
        label = amp_to_label(b)
        out_dir = os.path.join(HERE, f"sw_B{label}T.out")

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
        speed = np.sqrt(vx**2 + vy**2 + vz**2)  # nm/ns

        # Skip first 1/3 transient
        skip = max(1, len(ts) // 3)
        v_mean = float(np.mean(speed[skip:]))
        dr_final = float(dr[-1])
        core0 = int(cores[0])
        core_f = int(cores[-1])

        print(f"|dr|={dr_final:.3f}nm  v̄={v_mean:.3f}nm/ns  core={core0}→{core_f}")
        results.append((b, v_mean, dr_final, core0, core_f))

    if not results:
        print("ERROR: no data found")
        return

    Bs = np.array([r[0] for r in results])
    vs = np.array([r[1] for r in results])
    drs = np.array([r[2] for r in results])
    core0s = np.array([r[3] for r in results])
    corefs = np.array([r[4] for r in results])

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
        # R²
        log_v_pred = np.polyval(coeffs, log_B)
        ss_res = np.sum((log_v - log_v_pred)**2)
        ss_tot = np.sum((log_v - np.mean(log_v))**2)
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else np.nan
        fit_ok = True
        print(f"\n拟合结果: v = {c_fit:.4f} × B^{n_fit:.3f}")
        print(f"  R² = {r2:.4f}")

    # Core count stability check
    print("\n核心计数稳定性检查 (阈值 15%):")
    all_stable = True
    for i, (b, _, _, c0, cf) in enumerate(results):
        if c0 > 0:
            frac = abs(cf - c0) / c0
            status = "OK" if frac < 0.15 else "WARN"
            if frac >= 0.15:
                all_stable = False
            print(f"  B={b}T: {c0} → {cf}  ({frac*100:.1f}%)  [{status}]")
    if all_stable:
        print("  全部PASS: 结构完整性良好")

    # --- Plot (paper style) ---
    fig, ax = plt.subplots(figsize=(7, 4.4))

    excl_mask = ~above_floor
    if np.any(excl_mask):
        ax.scatter(Bs[excl_mask], vs[excl_mask], marker="x", s=50, color="gray",
                   label=r"低于噪声地板", zorder=3)

    ax.scatter(fit_Bs, fit_vs, marker="o", s=40, color=COLORS["primary"],
               label=r"440 GHz 数据", zorder=4)

    if fit_ok:
        B_line = np.logspace(np.log10(fit_Bs.min() * 0.8),
                             np.log10(fit_Bs.max() * 1.2), 100)
        v_line = c_fit * B_line**n_fit
        ax.plot(B_line, v_line, "--", color=COLORS["secondary"], linewidth=1.3,
                label=rf"$\bar v = {c_fit:.3f}\,B^{{{n_fit:.2f}}}$ ($R^2={r2:.3f}$)")

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel(r"自旋波幅度 $B$ (T)")
    ax.set_ylabel(r"平均速度 $\bar v$ (nm$\cdot$ns$^{-1}$)")
    legend_above(ax, ncol=3)

    out_png = os.path.join(RESULTS_DIR, "scaling_440GHz.png")
    save_paper_fig(fig, out_png)
    plt.close(fig)
    print(f"\n图片已保存: {out_png}")

    # --- Text summary ---
    lines = [
        "=== 440GHz Amplitude Sweep v-B Scaling Summary ===",
        "",
        f"{'B (T)':<10} {'v̄ (nm/ns)':<14} {'|dr| (nm)':<12} {'core0':<8} {'core_f':<8} {'note'}",
        "-" * 65,
    ]
    for i, (b, v, dr, c0, cf) in enumerate(results):
        note = "below_noise_floor" if not above_floor[i] else ""
        lines.append(f"{b:<10} {v:<14.4f} {dr:<12.4f} {c0:<8} {cf:<8} {note}")
    lines.append("")
    if fit_ok:
        lines.append(f"Power-law fit (points above noise floor):")
        lines.append(f"  v = {c_fit:.6f} * B^{n_fit:.4f}")
        lines.append(f"  R² = {r2:.4f}")
        lines.append(f"  Fitted points: B = {list(fit_Bs)} T")
    if excluded:
        lines.append(f"Excluded (noise floor |dr| < {NOISE_FLOOR_NM}nm): B = {excluded} T")
    lines.append("")

    out_txt = os.path.join(RESULTS_DIR, "scaling_440GHz.txt")
    with open(out_txt, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"文本摘要已保存: {out_txt}")

    return n_fit, c_fit, r2


if __name__ == "__main__":
    analyze_440GHz()
