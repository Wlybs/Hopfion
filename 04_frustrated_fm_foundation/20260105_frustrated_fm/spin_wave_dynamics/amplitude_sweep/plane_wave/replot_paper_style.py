"""440GHz 幅度扫描 v(B) 标度律重画（合并旧 6 点 + 新 4 点 = 10 点）

输入: plane_wave/sw_B*.out × 10
  B = 0.05 / 0.1 / 0.2 / 0.3 / 0.5 / 0.7 / 1.0 / 2.0 / 3.0 / 5.0 T
  全部 @ 440GHz srcX_vibX, 0.5ns, 初始态 centered_stability_Ku10k

输出:
  results/v_B_scaling.png — (a) v(B) log-log + 双拟合;  (b) dz_final vs B linear
  results/v_B_scaling.txt — 数值汇总 + 拟合参数

风格: 严格遵循 feedback_paper_figure_style v2-2026-05 (paper_style.py helpers)。
"""

from __future__ import annotations

import os
import sys

import numpy as np
import matplotlib.pyplot as plt

sys.path.insert(0, "/mnt/d/Research/Hopfion/95_shared_scripts")
from paper_style import (
    setup_paper_style,
    COLORS,
    save_paper_fig,
    panel_label,
    legend_above,
)
from hopfion_analysis import extract_trajectory_phase_correlation

setup_paper_style()

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(HERE, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

AMPS = [0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0, 2.0, 3.0, 5.0]  # Tesla
DT_NS = 0.05  # 50ps autosave


def amp_to_filename(b: float) -> str:
    """0.05 -> '0p05', 1.0 -> '1p0', 5.0 -> '5p0'"""
    s = f"{b}".rstrip("0").rstrip(".")
    if "." not in s:
        s = s + ".0"
    return s.replace(".", "p") + "T"


def collect_rows():
    rows = []
    for b in AMPS:
        out_dir = os.path.join(HERE, f"sw_B{amp_to_filename(b)}.out")
        if not os.path.isdir(out_dir):
            print(f"  [SKIP] B={b}T missing: {out_dir}")
            continue
        traj = extract_trajectory_phase_correlation(out_dir, DT_NS, verbose=False)
        if len(traj) < 3:
            print(f"  [SKIP] B={b}T too few frames ({len(traj)})")
            continue
        ts = np.array([r[0] for r in traj])
        dx = np.array([r[1][0] for r in traj])
        dy = np.array([r[1][1] for r in traj])
        dz = np.array([r[1][2] for r in traj])
        dr = np.sqrt(dx ** 2 + dy ** 2 + dz ** 2)
        cores = np.array([r[2] for r in traj])

        vx = np.gradient(dx, ts)
        vy = np.gradient(dy, ts)
        vz = np.gradient(dz, ts)
        speed = np.sqrt(vx ** 2 + vy ** 2 + vz ** 2)
        skip = max(1, len(ts) // 3)
        v_mean = float(np.mean(speed[skip:]))

        rows.append(
            dict(
                B=b,
                v_mean=v_mean,
                dr_final=float(dr[-1]),
                dz_final=float(dz[-1]),
                core0=int(cores[0]),
                core_f=int(cores[-1]),
            )
        )
        print(
            f"  B={b:6.2f}T  |dr|={dr[-1]:6.3f}nm  dz={dz[-1]:+7.3f}nm  "
            f"v̄={v_mean:7.3f}nm/ns  core={int(cores[0])}→{int(cores[-1])}"
        )
    return rows


def power_law_fit(B_arr, v_arr):
    """log-log linear fit, return (n, c, R²)."""
    log_B = np.log(B_arr)
    log_v = np.log(v_arr)
    n, log_c = np.polyfit(log_B, log_v, 1)
    log_v_pred = n * log_B + log_c
    ss_res = float(np.sum((log_v - log_v_pred) ** 2))
    ss_tot = float(np.sum((log_v - np.mean(log_v)) ** 2))
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    return float(n), float(np.exp(log_c)), float(r2)


def main():
    rows = collect_rows()
    if not rows:
        print("no data")
        return

    Bs = np.array([r["B"] for r in rows])
    vs = np.array([r["v_mean"] for r in rows])
    dzs = np.array([r["dz_final"] for r in rows])

    n_all, c_all, r2_all = power_law_fit(Bs, vs)

    mask_high = Bs >= 0.5
    n_h, c_h, r2_h = power_law_fit(Bs[mask_high], vs[mask_high])

    # --- 2-panel figure ---
    fig, (ax0, ax1) = plt.subplots(1, 2, figsize=(9.5, 4.2))

    # (a) v vs B (log-log) + two fits
    ax0.scatter(Bs, vs, marker="o", s=24, color=COLORS["primary"],
                zorder=4, label=fr"data ($n$={len(rows)})")
    B_line = np.logspace(np.log10(Bs.min() * 0.7),
                         np.log10(Bs.max() * 1.4), 100)
    ax0.plot(B_line, c_all * B_line ** n_all, "--",
             color=COLORS["secondary"], linewidth=1.3,
             label=fr"全拟合 $\bar v \propto B^{{{n_all:.2f}}}$ ($R^2$={r2_all:.3f})")
    ax0.plot(B_line, c_h * B_line ** n_h, ":",
             color=COLORS["tertiary"], linewidth=1.3,
             label=fr"$B\geq0.5$ T: $B^{{{n_h:.2f}}}$ ($R^2$={r2_h:.3f})")
    ax0.set_xscale("log")
    ax0.set_yscale("log")
    ax0.set_xlabel(r"自旋波幅度 $B$ (T)")
    ax0.set_ylabel(r"平均速度 $\bar v$ (nm$\cdot$ns$^{-1}$)")
    legend_above(ax0, ncol=1)
    panel_label(fig, ax0, "(a)", loc="top_left_outside")

    # (b) dz_final vs B (linear y, log x to align with (a))
    ax1.scatter(Bs, dzs, marker="o", s=24, color=COLORS["primary"], zorder=4)
    ax1.axhline(0, color="gray", linewidth=0.6, linestyle="--")
    ax1.set_xscale("log")
    ax1.set_xlabel(r"自旋波幅度 $B$ (T)")
    ax1.set_ylabel(r"末态 $z$ 位移 $\Delta z_\mathrm{f}$ (nm)")
    panel_label(fig, ax1, "(b)", loc="top_left_outside")

    fig.tight_layout()
    out_png = os.path.join(RESULTS_DIR, "v_B_scaling.png")
    save_paper_fig(fig, out_png)
    plt.close(fig)
    print(f"\nSaved figure: {out_png}")

    # --- text summary ---
    lines = [
        f"=== 440GHz srcX_vibX 幅度扫描 v(B) 标度律（10 点合并）===",
        f"运行时长: 0.5 ns/sim  autosave: 50 ps  "
        f"初始态: centered_stability_test/stability_Ku10k.out/m000020.ovf",
        "",
        f"{'B (T)':<8} {'v̄ (nm/ns)':<14} {'|dr| (nm)':<14} "
        f"{'dz_f (nm)':<14} {'core0→core_f'}",
        "-" * 72,
    ]
    for r in rows:
        lines.append(
            f"{r['B']:<8} {r['v_mean']:<14.4f} {r['dr_final']:<14.4f} "
            f"{r['dz_final']:<+14.4f} {r['core0']}→{r['core_f']}"
        )
    lines += [
        "",
        f"=== 拟合 ===",
        f"全 {len(rows)} 点:  v̄ = {c_all:.4f} × B^{n_all:.3f}    R² = {r2_all:.4f}",
        f"B ≥ 0.5 T  ({mask_high.sum()} 点):  v̄ = {c_h:.4f} × B^{n_h:.3f}    "
        f"R² = {r2_h:.4f}",
        "",
        f"=== 历史对比 ===",
        f"旧 3 点拟合 (B=0.5/1.0/2.0): v̄ = 6.0103 × B^1.9881  R² = 0.9976",
        f"新 {mask_high.sum()} 点高 B 拟合:        v̄ = {c_h:.4f} × B^{n_h:.4f}  R² = {r2_h:.4f}",
    ]
    out_txt = os.path.join(RESULTS_DIR, "v_B_scaling.txt")
    with open(out_txt, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"Saved text:   {out_txt}\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
