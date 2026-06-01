"""
anisotropy_sweep_large 分析脚本
对 R8r4 初始态，Ku1=[0, 5k, 10k, 20k, 30k] 各 1ns 的结果分析 Hopfion 存活与尺寸变化。

输出（就近存放于本目录 sweep_results/）：
  - R_r_vs_time.png      : 各 Ku1 下 R(t), r(t) 时间演化
  - summary_Rr_vs_Ku1.png: 末帧 R, r vs Ku1 汇总
  - survival_table.txt    : 文本存活报告
"""

import os
import sys
import glob
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.optimize import least_squares
from skimage import measure
import discretisedfield as df

# ── 配置 ──
SWEEP_DIR   = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(SWEEP_DIR, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

# Ku1 -> 目录名映射（粗扫 + 细化）
KU1_MAP = {
    0:     "R8r4_Ku0.out",
    5000:  "R8r4_Ku5k.out",
    10000: "R8r4_Ku10k.out",
    20000: "R8r4_Ku20k.out",
    30000: "R8r4_Ku30k.out",
    40000: "R8r4_Ku40k.out",
    50000: "R8r4_Ku50k.out",
    52000: "R8r4_Ku52k.out",
    55000: "R8r4_Ku55k.out",
    56000: "R8r4_Ku56k.out",
    57000: "R8r4_Ku57k.out",
    58000: "R8r4_Ku58k.out",
}

# 21 帧, autosave=0.05ns, 共 1ns
N_FRAMES = 21
DT_NS    = 0.05

# 采样帧: t=0, 0.1, 0.2, 0.4, 0.6, 0.8, 1.0 ns
SAMPLE_INDICES = [0, 2, 4, 8, 12, 16, 20]
SAMPLE_TIMES   = [i * DT_NS for i in SAMPLE_INDICES]

CORE_THRESHOLD = 0.05
BAD_FIT_NM     = 3.0


# ── 工具函数 ──

def _circle_residuals(params, pts):
    xc, yc, R = params
    return np.sqrt((pts[:, 0] - xc)**2 + (pts[:, 1] - yc)**2) - R


def _pbc_unwrap_xy(xy, box_L):
    centroid = np.mean(xy, axis=0)
    delta = xy - centroid
    delta -= box_L * np.round(delta / box_L)
    return centroid + delta


def compute_hopfion_Rr(field):
    """返回 (R_nm, r_nm, status)"""
    mz   = field.array[..., 2]
    cell = np.array(field.mesh.cell)
    pmin = np.array(field.mesh.region.pmin)
    box_L = np.array(field.mesh.region.pmax) - pmin

    mz_min = float(np.min(mz))
    core_mask = mz < (mz_min + CORE_THRESHOLD)

    if not np.any(core_mask):
        return None, None, "no_core"

    idx = np.array(np.where(core_mask)).T
    coords = pmin + idx * cell
    xy = coords[:, :2]

    if len(xy) < 4:
        return None, None, "no_core"

    xy_unwrapped = _pbc_unwrap_xy(xy, box_L[:2])
    center_guess = np.mean(xy_unwrapped, axis=0)
    r_guess = np.mean(np.linalg.norm(xy_unwrapped - center_guess, axis=1))

    try:
        res = least_squares(
            _circle_residuals,
            [center_guess[0], center_guess[1], r_guess],
            args=(xy_unwrapped,), method='lm'
        )
        xc, yc, R_fit = res.x
        fit_error_nm = np.sqrt(res.cost / len(xy_unwrapped)) * 1e9
    except Exception:
        return None, None, "fit_failed"

    if fit_error_nm > BAD_FIT_NM:
        return R_fit * 1e9, None, "fit_failed"

    R_nm = abs(R_fit) * 1e9

    try:
        verts, _, _, _ = measure.marching_cubes(
            volume=mz, level=0, spacing=tuple(cell)
        )
        verts += pmin
    except (ValueError, RuntimeError):
        return R_nm, None, "no_isosurface"

    if len(verts) == 0:
        return R_nm, None, "no_isosurface"

    core_z_center = float(np.mean(coords[:, 2]))
    dist_xy = np.sqrt((verts[:, 0] - xc)**2 + (verts[:, 1] - yc)**2)
    dist_to_ring = np.sqrt((dist_xy - abs(R_fit))**2 + (verts[:, 2] - core_z_center)**2)
    r_nm = float(np.mean(dist_to_ring)) * 1e9

    return R_nm, r_nm, "alive"


# ── 主流程 ──

def analyze_ku1(ku1):
    dirname = KU1_MAP[ku1]
    out_dir = os.path.join(SWEEP_DIR, dirname)
    if not os.path.isdir(out_dir):
        print(f"  [WARN] missing: {out_dir}")
        return None

    results = []
    for idx in SAMPLE_INDICES:
        ovf = os.path.join(out_dir, f"m{idx:06d}.ovf")
        if not os.path.exists(ovf):
            results.append((idx * DT_NS, None, None, "missing"))
            continue
        field = df.Field.from_file(ovf)
        R, r, status = compute_hopfion_Rr(field)
        del field
        t_ns = idx * DT_NS
        results.append((t_ns, R, r, status))
        print(f"    t={t_ns:.2f}ns  R={f'{R:.2f}' if R else 'N/A':>6s}  "
              f"r={f'{r:.2f}' if r else 'N/A':>6s}  [{status}]")
    return results


def plot_Rr_vs_time(all_data):
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    colors = plt.cm.plasma(np.linspace(0.1, 0.9, len(KU1_MAP)))

    for (ku1, data), color in zip(all_data.items(), colors):
        if data is None:
            continue
        label = f"Ku1={ku1/1000:.0f}k" if ku1 > 0 else "Ku1=0"
        ts_R = [(d[0], d[1]) for d in data if d[1] is not None]
        ts_r = [(d[0], d[2]) for d in data if d[2] is not None]
        if ts_R:
            axes[0].plot([x[0] for x in ts_R], [x[1] for x in ts_R],
                         'o-', color=color, label=label, markersize=5)
        if ts_r:
            axes[1].plot([x[0] for x in ts_r], [x[1] for x in ts_r],
                         's-', color=color, label=label, markersize=5)

    for ax, ylabel, title in zip(axes, ["R (nm)", "r (nm)"],
        ["Major radius R vs time", "Tube radius r vs time"]):
        ax.set_xlabel("Time (ns)")
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)

    plt.suptitle("Frustrated FM Hopfion: Anisotropy Sweep (R8r4, 1ns)", fontsize=12)
    plt.tight_layout()
    out = os.path.join(RESULTS_DIR, "R_r_vs_time.png")
    plt.savefig(out, dpi=200)
    plt.close()
    print(f"\n[fig] {out}")


def plot_summary(all_data):
    fig, ax = plt.subplots(figsize=(8, 5))
    ku1s, Rs, rs, sts, complete = [], [], [], [], []

    for ku1, data in all_data.items():
        if data is None:
            continue
        # Check if Hopfion survived: last frame must be "alive"
        is_complete = (data[-1][3] == "alive") if data else False
        last = None
        for d in reversed(data):
            if d[3] == "alive" and d[1] is not None:
                last = d
                break
        ku1s.append(ku1)
        Rs.append(last[1] if last else None)
        rs.append(last[2] if last else None)
        sts.append(last[3] if last else "missing")
        complete.append(is_complete)

    for i, (ku1, R, r, st, comp) in enumerate(zip(ku1s, Rs, rs, sts, complete)):
        if not comp:
            # Incomplete run: mark with X
            if R is not None:
                ax.scatter(ku1/1000, R, marker='x', s=120, color='gray',
                           zorder=5, linewidths=2,
                           label='Collapsed (incomplete)' if i == len(ku1s)-1 else "")
            ax.axvline(x=ku1/1000, color='red', linestyle='--', alpha=0.4)
            continue
        if R is not None:
            ax.scatter(ku1/1000, R, marker='o', s=80, color='steelblue', zorder=5,
                       label='R (major)' if i == 0 else "")
        if r is not None:
            ax.scatter(ku1/1000, r, marker='s', s=80, color='tomato', zorder=5,
                       label='r (tube)' if i == 0 else "")

    ku1_valid = [k/1000 for k, R, c in zip(ku1s, Rs, complete)
                 if R is not None and c]
    R_valid = [R for R, c in zip(Rs, complete) if R is not None and c]
    r_ku1 = [k/1000 for k, r, c in zip(ku1s, rs, complete)
             if r is not None and c]
    r_valid = [r for r, c in zip(rs, complete) if r is not None and c]
    if len(ku1_valid) > 1:
        ax.plot(ku1_valid, R_valid, '--', color='steelblue', alpha=0.5)
    if len(r_ku1) > 1:
        ax.plot(r_ku1, r_valid, '--', color='tomato', alpha=0.5)

    # Mark Ku_c region
    ax.axvspan(52, 55, alpha=0.15, color='red', label=r'$K_{u,c}$ region (52–55k)')

    ax.set_xlabel(r"$K_{u1}$ (kJ/m$^3$)", fontsize=12)
    ax.set_ylabel("Size (nm)", fontsize=12)
    ax.set_title(r"Hopfion size at $t=1$ ns vs anisotropy", fontsize=13)
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    out = os.path.join(RESULTS_DIR, "summary_Rr_vs_Ku1.png")
    plt.savefig(out, dpi=200)
    plt.close()
    print(f"[fig] {out}")


def write_survival_table(all_data):
    lines = [
        "Ku1 (J/m³)  |  t=0 R/r (nm)  |  t=1ns R/r (nm)  |  Status",
        "-" * 65
    ]
    for ku1, data in all_data.items():
        if data is None:
            lines.append(f"{ku1:10.0f}  |  NO DATA")
            continue
        d0 = data[0]
        dl = None
        for d in reversed(data):
            if d[1] is not None:
                dl = d
                break
        r0 = f"{d0[1]:.2f}/{d0[2]:.2f}" if (d0[1] and d0[2]) else "N/A"
        rl = f"{dl[1]:.2f}/{dl[2]:.2f}" if (dl and dl[1] and dl[2]) else "N/A"
        st = dl[3] if dl else "missing"
        lines.append(f"{ku1:10.0f}  |  {r0:>14s}  |  {rl:>16s}  |  {st}")
    txt = "\n".join(lines)
    out = os.path.join(RESULTS_DIR, "survival_table.txt")
    with open(out, "w") as f:
        f.write(txt + "\n")
    print(f"\n[report] {out}")
    print("\n" + txt)


def main():
    print("=" * 55)
    print("  Anisotropy Sweep Large: Hopfion Survival Analysis")
    print("=" * 55)

    all_data = {}
    for ku1 in KU1_MAP:
        print(f"\n>>> Ku1 = {ku1} J/m³")
        all_data[ku1] = analyze_ku1(ku1)

    print("\n" + "=" * 55)
    plot_Rr_vs_time(all_data)
    plot_summary(all_data)
    write_survival_table(all_data)
    print("\nDone.")


if __name__ == "__main__":
    main()
