"""
频率切换双向z控制分析 (v3 — balanced timing)

单srcZ源，通过切换频率实现 +z/-z 反转：
  Phase 1 (0.00-0.50ns): srcZ @ 100GHz  → +z (anomalous mode)
  Phase 2 (0.50-1.00ns): srcZ @ 1100GHz → -z (normal mode)
  Phase 3 (1.00-1.10ns): OFF            → free relaxation

输出 results/:
  - freq_switch_v3_z_control.png
  - freq_switch_v3_z_control.txt
"""
import sys
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, "/mnt/d/Research/Hopfion/scripts")
from hopfion_analysis import extract_trajectory_phase_correlation

RESULTS_DIR = os.path.join(HERE, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

OUT_DIR = os.path.join(HERE, "freq_switch_bidirectional_v3.out")
DT_NS = 0.005  # 5ps autosave

PHASES = [
    (0.00, 0.50, "Phase 1\nsrcZ@100GHz\n→ +z",   "#b3e0b3"),
    (0.50, 1.00, "Phase 2\nsrcZ@1100GHz\n→ -z",  "#b3ccf0"),
    (1.00, 1.10, "Phase 3\nOFF\nrelax",           "#f0f0f0"),
]

PHASE_BOUNDARIES = [0.50, 1.00, 1.10]
PHASE_LABELS = [
    "srcZ@100GHz (0→0.50ns)",
    "srcZ@1100GHz (0.50→1.00ns)",
    "OFF (1.00→1.10ns)",
]


def main():
    print(f"加载轨迹: {OUT_DIR}")
    traj = extract_trajectory_phase_correlation(OUT_DIR, DT_NS, verbose=False)
    n = len(traj)
    print(f"  帧数: {n}")
    if n < 2:
        print("ERROR: 帧数不足")
        return

    ts    = np.array([r[0] for r in traj])
    dx    = np.array([r[1][0] for r in traj])
    dy    = np.array([r[1][1] for r in traj])
    dz    = np.array([r[1][2] for r in traj])
    cores = np.array([r[2] for r in traj])

    vz = np.gradient(dz, ts)

    # --- Phase statistics ---
    print("\n各阶段 dz 统计:")
    prev_t = 0.0
    phase_dz = []
    for label, bt in zip(PHASE_LABELS, PHASE_BOUNDARIES):
        mask = (ts >= prev_t - 1e-6) & (ts <= bt + 1e-6)
        if np.any(mask):
            dz_s = dz[mask][0]
            dz_e = dz[mask][-1]
            ddz = dz_e - dz_s
            print(f"  {label}: dz {dz_s:+.3f} → {dz_e:+.3f} nm  (Δ={ddz:+.3f} nm)")
            phase_dz.append({"start": dz_s, "end": dz_e, "delta": ddz})
        prev_t = bt

    print(f"\n总 dz 范围: {dz.min():.3f} ~ {dz.max():.3f} nm")
    print(f"净位移: dz(0)={dz[0]:+.3f} → dz(end)={dz[-1]:+.3f} nm")

    # Peak +z position
    iz_max = np.argmax(dz)
    print(f"最大 +z 位移: dz={dz[iz_max]:+.3f} nm @ t={ts[iz_max]:.3f} ns")

    # Core stability
    print("\n核心计数:")
    for label, bt in zip(PHASE_LABELS, PHASE_BOUNDARIES):
        idx = np.argmin(np.abs(ts - bt))
        c = int(cores[idx])
        frac = abs(c - int(cores[0])) / int(cores[0]) * 100
        status = "OK" if frac < 15 else "WARN"
        print(f"  t={bt:.2f}ns: core={c} (Δ={frac:.1f}%) [{status}]")

    # --- Success criteria ---
    print("\n=== 成功判据 ===")
    if len(phase_dz) >= 2:
        p1_up   = phase_dz[0]["delta"] > 0.5   # need substantial +z
        p2_down = phase_dz[1]["delta"] < -0.5   # need substantial -z
        reversal = p1_up and p2_down
        print(f"  Phase1 +z: {'PASS' if p1_up else 'FAIL'} (Δdz={phase_dz[0]['delta']:+.3f} nm)")
        print(f"  Phase2 -z: {'PASS' if p2_down else 'FAIL'} (Δdz={phase_dz[1]['delta']:+.3f} nm)")
        print(f"  双向逆转: {'SUCCESS' if reversal else 'FAILED'}")
        if len(phase_dz) >= 3:
            net = phase_dz[0]["delta"] + phase_dz[1]["delta"]
            print(f"  净位移(Phase1+2): {net:+.3f} nm")

    # --- Text summary ---
    txt_path = os.path.join(RESULTS_DIR, "freq_switch_v3_z_control.txt")
    with open(txt_path, "w") as f:
        f.write("=" * 70 + "\n")
        f.write("Freq-Switch Bidirectional Z Control (v3 — balanced) Summary\n")
        f.write("srcZ@100GHz(+z, 0.50ns) → srcZ@1100GHz(-z, 0.50ns) → OFF, B=1T\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"{'t(ns)':>8}  {'dz(nm)':>9}  {'core':>6}\n")
        f.write("-" * 30 + "\n")
        for i in range(0, n, max(1, n // 30)):
            f.write(f"{ts[i]:8.3f}  {dz[i]:+9.4f}  {int(cores[i]):6d}\n")
        f.write(f"\nPhase summary:\n")
        for label, pd in zip(PHASE_LABELS, phase_dz):
            f.write(f"  {label}: Δdz = {pd['delta']:+.4f} nm\n")
        if len(phase_dz) >= 2:
            f.write(f"\n  Reversal: {'SUCCESS' if reversal else 'FAILED'}\n")
            f.write(f"  Peak +z: {dz[iz_max]:+.3f} nm @ {ts[iz_max]:.3f} ns\n")
    print(f"\nSaved: {txt_path}")

    # --- Figure ---
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
    fig.subplots_adjust(hspace=0.08)

    for ax in (ax1, ax2):
        for t_s, t_e, _, color in PHASES:
            ax.axvspan(t_s, t_e, color=color, alpha=0.8, zorder=0)
        for tb in PHASE_BOUNDARIES[:-1]:
            ax.axvline(tb, color='gray', linestyle='--', linewidth=0.8, zorder=1)

    # Panel 1: dz(t)
    ax1.plot(ts, dz, color='#1f77b4', linewidth=2.0, zorder=2)
    ax1.axhline(0, color='k', linewidth=0.6, zorder=1)
    ax1.set_ylabel('z-displacement dz (nm)', fontsize=11)
    ax1.set_title('Freq-Switch Bidirectional Z Control (v3): srcZ@100GHz(+z) → srcZ@1100GHz(-z)',
                  fontsize=12)

    # Mark peak
    ax1.plot(ts[iz_max], dz[iz_max], 'r*', markersize=12, zorder=5)
    ax1.annotate(f'peak: {dz[iz_max]:+.1f} nm',
                 xy=(ts[iz_max], dz[iz_max]),
                 xytext=(ts[iz_max]+0.05, dz[iz_max]+1),
                 fontsize=9, color='red',
                 arrowprops=dict(arrowstyle='->', color='red', lw=1))

    for t_s, t_e, label, _ in PHASES:
        t_mid = (t_s + t_e) / 2
        ax1.text(t_mid, 0.92, label, ha='center', va='top', fontsize=8,
                 transform=ax1.get_xaxis_transform(),
                 bbox=dict(boxstyle='round,pad=0.2', facecolor='white',
                           alpha=0.8, edgecolor='none'))

    # Panel 2: vz(t)
    ax2.plot(ts, vz, color='#ff7f0e', linewidth=1.5, zorder=2)
    ax2.axhline(0, color='k', linewidth=0.8, zorder=1)
    ax2.set_ylabel('z-velocity vz (nm/ns)', fontsize=11)
    ax2.set_xlabel('Time (ns)', fontsize=11)

    ax1.set_xlim(ts[0], ts[-1])
    ax1.grid(True, alpha=0.25, zorder=0)
    ax2.grid(True, alpha=0.25, zorder=0)

    p1 = mpatches.Patch(color='#b3e0b3', label='100GHz → +z')
    p2 = mpatches.Patch(color='#b3ccf0', label='1100GHz → -z')
    p3 = mpatches.Patch(color='#f0f0f0', label='OFF (relax)')
    ax1.legend(handles=[p1, p2, p3], loc='best', fontsize=9, framealpha=0.8)

    plt.tight_layout()
    out_png = os.path.join(RESULTS_DIR, "freq_switch_v3_z_control.png")
    fig.savefig(out_png, dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved: {out_png}")


if __name__ == "__main__":
    main()
