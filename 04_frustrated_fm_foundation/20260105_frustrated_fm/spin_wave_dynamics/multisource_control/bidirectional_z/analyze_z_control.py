"""
Z轴双向控制演示分析 (Fig 4-4)

输入: z_bidirectional_control.out/ (101帧, 1.0ns, 10ps autosave)
4个阶段:
  Phase 1 [0.00-0.25ns]: srcX ON  → +z 运动
  Phase 2 [0.25-0.50ns]: all OFF  → 自由弛豫
  Phase 3 [0.50-0.75ns]: srcZ ON  → -z 运动
  Phase 4 [0.75-1.00ns]: all OFF  → 自由弛豫

输出: results/z_control_demo.png (Fig 4-4)
"""

import sys
import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, "/mnt/d/Research/Hopfion/95_shared_scripts")
from hopfion_analysis import extract_trajectory_phase_correlation

RESULTS_DIR = os.path.join(HERE, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

OUT_DIR = os.path.join(HERE, "z_bidirectional_control.out")
DT_NS = 0.01  # 10ps autosave

# Phase boundary times (ns) — v3: 0.5ns total
PHASES = [
    (0.00, 0.10, "Phase 1\nsrcX → +z",        "#b3e0b3"),   # light green
    (0.10, 0.40, "Phase 2\nsrcZ → brake/-z",  "#b3ccf0"),   # light blue
    (0.40, 0.50, "Phase 3\nfree",              "#f0f0f0"),   # light gray
]


def main():
    print(f"加载轨迹: {OUT_DIR}")
    traj = extract_trajectory_phase_correlation(OUT_DIR, DT_NS, verbose=False)

    n = len(traj)
    print(f"  帧数: {n}")
    if n < 2:
        print("ERROR: 帧数不足")
        return

    ts     = np.array([r[0] for r in traj])
    dx     = np.array([r[1][0] for r in traj])
    dy     = np.array([r[1][1] for r in traj])
    dz     = np.array([r[1][2] for r in traj])
    dr     = np.sqrt(dx**2 + dy**2 + dz**2)
    cores  = np.array([r[2] for r in traj])

    # Vector velocity (nm/ns)
    vx = np.gradient(dx, ts)
    vy = np.gradient(dy, ts)
    vz = np.gradient(dz, ts)

    # --- Phase boundary statistics ---
    print("\n各阶段 dz 统计:")
    boundaries_t = [0.10, 0.40, 0.50]
    phase_labels_short = ["srcX ON (0→0.10ns)",
                          "srcZ ON (0.10→0.40ns)",
                          "free (0.40→0.50ns)"]
    prev_t = 0.0
    phase_dz_ends = []
    for label, bt in zip(phase_labels_short, boundaries_t):
        mask = (ts >= prev_t) & (ts <= bt)
        if np.any(mask):
            dz_start = dz[mask][0]
            dz_end   = dz[mask][-1]
            ddz = dz_end - dz_start
            print(f"  {label}: dz {dz_start:+.3f} → {dz_end:+.3f} nm  (Δ={ddz:+.3f} nm)")
            phase_dz_ends.append(dz_end)
        prev_t = bt

    print(f"\n总 dz 范围: {dz.min():.3f} ~ {dz.max():.3f} nm")

    # --- Core count stability ---
    print("\n核心计数稳定性:")
    for label, bt in zip(phase_labels_short, boundaries_t):
        mask = (ts >= 0) & (ts <= bt)
        if np.any(mask):
            c0 = int(cores[0])
            cf = int(cores[mask][-1])
            frac = abs(cf - c0) / c0 if c0 > 0 else 0
            status = "OK" if frac < 0.15 else "WARN"
            print(f"  t={bt:.2f}ns: core={c0}→{cf} ({frac*100:.1f}%) [{status}]")

    # --- Fig 4-4: 2-panel ---
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 6), sharex=True)
    fig.subplots_adjust(hspace=0.08)

    for ax in (ax1, ax2):
        for t_start, t_end, label, color in PHASES:
            ax.axvspan(t_start, t_end, color=color, alpha=0.85, zorder=0)
        for tb in [0.25, 0.50, 0.75]:
            ax.axvline(tb, color='gray', linestyle='--', linewidth=0.8, zorder=1)

    # Panel 1: dz(t)
    ax1.plot(ts, dz, color='C0', linewidth=1.8, zorder=2)
    ax1.axhline(0, color='k', linewidth=0.6, linestyle='-', zorder=1)
    ax1.set_ylabel('z-displacement dz (nm)', fontsize=11)
    ax1.set_title('Z-Axis Bidirectional Control Demo: dz(t)', fontsize=12)

    # Phase labels on top panel
    for t_start, t_end, label, _ in PHASES:
        t_mid = (t_start + t_end) / 2
        y_top = ax1.get_ylim()[1] if ax1.get_ylim()[1] != 0 else 1
        ax1.text(t_mid, ax1.get_ylim()[1] * 0.92 if ax1.get_ylim()[1] != 0 else 0.9,
                 label, ha='center', va='top', fontsize=8.5,
                 transform=ax1.get_xaxis_transform(),
                 bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.7, edgecolor='none'))

    # Panel 2: vz(t)
    ax2.plot(ts, vz, color='C1', linewidth=1.5, zorder=2)
    ax2.axhline(0, color='k', linewidth=0.8, linestyle='-', zorder=1)
    ax2.set_ylabel('z-velocity vz (nm/ns)', fontsize=11)
    ax2.set_xlabel('Time (ns)', fontsize=11)

    ax1.set_xlim(ts[0], ts[-1])
    ax1.grid(True, alpha=0.25, zorder=0)
    ax2.grid(True, alpha=0.25, zorder=0)

    # Legend patches
    p1 = mpatches.Patch(color='#b3e0b3', label='Phase 1: srcX ON (+z)')
    p2 = mpatches.Patch(color='#f0f0f0', label='Phase 2/4: free relax')
    p3 = mpatches.Patch(color='#b3ccf0', label='Phase 3: srcZ ON (-z)')
    ax1.legend(handles=[p1, p2, p3], loc='lower left', fontsize=8.5, framealpha=0.8)

    plt.tight_layout()
    out_png = os.path.join(RESULTS_DIR, "z_control_demo.png")
    fig.savefig(out_png, dpi=150)
    plt.close(fig)
    print(f"\nFig 4-4 已保存: {out_png}")

    # Success criterion check
    print("\n成功判据:")
    # v3: 期望 dz 先升(Phase1)后降(Phase2 srcZ逆转)，Phase2结束时 dz < Phase1结束
    reversal_ok = (phase_dz_ends[0] > 0.2) and (phase_dz_ends[1] < phase_dz_ends[0])
    print(f"  srcX驱动+z: {'PASS' if phase_dz_ends[0] > 0.2 else 'WARN'} (Phase1结束 dz={phase_dz_ends[0]:+.3f} nm)")
    print(f"  srcZ逆转:   {'PASS' if phase_dz_ends[1] < phase_dz_ends[0] else 'WARN'} (Phase2结束 dz={phase_dz_ends[1]:+.3f} nm, 预期 < {phase_dz_ends[0]:+.3f})")
    print(f"  整体逆转量: {phase_dz_ends[1] - phase_dz_ends[0]:+.3f} nm")


def make_fallback_fig():
    """
    备选 Fig 4-4: 两张独立单相仿真并列展示双向z控制
      左: srcX_vibX @ 200GHz → +z motion (freq_sweep/02ns/sw_f200GHz.out)
      右: srcZ_vibX @ 200GHz → -z motion (srcZ_freq_sweep/sw_srcZ_f200GHz.out)
    """
    import os

    srcX_out = os.path.join(HERE, "..", "srcX", "02ns", "sw_f200GHz.out")
    srcZ_out = os.path.join(HERE, "sw_srcZ_f200GHz.out")
    srcX_out = os.path.normpath(srcX_out)

    print("\n=== 备选 Fig 4-4: 双向z控制并列图 ===")
    print(f"  srcX: {srcX_out}")
    print(f"  srcZ: {srcZ_out}")

    traj_x = extract_trajectory_phase_correlation(srcX_out, 0.01, verbose=False)
    traj_z = extract_trajectory_phase_correlation(srcZ_out, 0.01, verbose=False)

    def parse(traj):
        ts  = np.array([r[0] for r in traj])
        dz  = np.array([r[1][2] for r in traj])
        return ts, dz

    ts_x, dz_x = parse(traj_x)
    ts_z, dz_z = parse(traj_z)

    print(f"  srcX  t=0→{ts_x[-1]:.2f}ns  dz: {dz_x[0]:+.3f} → {dz_x[-1]:+.3f} nm")
    print(f"  srcZ  t=0→{ts_z[-1]:.2f}ns  dz: {dz_z[0]:+.3f} → {dz_z[-1]:+.3f} nm")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.5))
    fig.suptitle("Z-Axis Bidirectional Control: srcX vs srcZ @ 200 GHz, B = 1 T",
                 fontsize=12, fontweight='bold')

    # --- Left: srcX → +z ---
    ax1.fill_between(ts_x, dz_x, 0, where=(dz_x >= 0),
                     color='#b3e0b3', alpha=0.6, label='+z region')
    ax1.plot(ts_x, dz_x, color='#2ca02c', linewidth=2.0)
    ax1.axhline(0, color='k', linewidth=0.8)
    ax1.set_xlabel('Time (ns)', fontsize=11)
    ax1.set_ylabel('z-displacement dz (nm)', fontsize=11)
    ax1.set_title('(a) srcX_vibX  →  +z motion', fontsize=11)
    ax1.set_ylim(bottom=min(-0.5, dz_x.min() - 0.3))
    ax1.annotate(f'Δdz = {dz_x[-1] - dz_x[0]:+.2f} nm',
                 xy=(ts_x[-1]*0.6, dz_x[-1]*0.7),
                 fontsize=10, color='#2ca02c',
                 arrowprops=dict(arrowstyle='->', color='#2ca02c'),
                 xytext=(ts_x[-1]*0.3, dz_x[-1]*0.4))
    ax1.grid(True, alpha=0.3)

    # --- Right: srcZ → -z ---
    ax2.fill_between(ts_z, dz_z, 0, where=(dz_z <= 0),
                     color='#b3ccf0', alpha=0.6, label='-z region')
    ax2.plot(ts_z, dz_z, color='#1f77b4', linewidth=2.0)
    ax2.axhline(0, color='k', linewidth=0.8)
    ax2.set_xlabel('Time (ns)', fontsize=11)
    ax2.set_ylabel('z-displacement dz (nm)', fontsize=11)
    ax2.set_title('(b) srcZ_vibX  →  -z motion', fontsize=11)
    ax2.set_ylim(top=max(0.5, dz_z.max() + 0.3))
    ax2.annotate(f'Δdz = {dz_z[-1] - dz_z[0]:+.2f} nm',
                 xy=(ts_z[-1]*0.6, dz_z[-1]*0.7),
                 fontsize=10, color='#1f77b4',
                 arrowprops=dict(arrowstyle='->', color='#1f77b4'),
                 xytext=(ts_z[-1]*0.3, dz_z[-1]*0.4))
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    out_png = os.path.join(RESULTS_DIR, "z_control_demo.png")
    fig.savefig(out_png, dpi=150)
    plt.close(fig)
    print(f"  备选 Fig 4-4 已保存: {out_png}")


if __name__ == "__main__":
    main()
    make_fallback_fig()
