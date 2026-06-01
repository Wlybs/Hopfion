"""
点源频率扫描分析: srcX + srcZ, 100-1000GHz (各10点)

对比平面源数据，揭示:
1. 点源 vs 平面源的响应差异
2. 点源驱动的频率选择性
3. 点源驱动的 Hall 角特性

输出 results/:
  - point_source_freq_response.png   (srcX + srcZ 位移谱)
  - point_source_comparison.png      (点源 vs 平面源对比)
  - point_source_hall_angle.png      (Hall 角)
  - point_source_summary.txt
"""
import sys
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, "/mnt/d/Research/Hopfion/scripts")
from hopfion_analysis import extract_trajectory_phase_correlation

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(HERE, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

FREQS = [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]  # GHz
DT_NS = 0.01  # 10ps autosave


def analyze_series(src_type):
    """Analyze one source type (srcX or srcZ)."""
    base = os.path.join(HERE, src_type)
    results = []

    for f in FREQS:
        out_dir = os.path.join(base, f"ps_{src_type}_f{f}GHz.out")
        if not os.path.isdir(out_dir):
            print(f"  [SKIP] {src_type} {f}GHz: not found")
            continue

        traj = extract_trajectory_phase_correlation(out_dir, DT_NS, verbose=False)
        if len(traj) < 3:
            print(f"  [SKIP] {src_type} {f}GHz: too few frames")
            continue

        ts = np.array([r[0] for r in traj])
        dx = np.array([r[1][0] for r in traj])
        dy = np.array([r[1][1] for r in traj])
        dz = np.array([r[1][2] for r in traj])
        dr = np.sqrt(dx**2 + dy**2 + dz**2)
        cores = np.array([r[2] for r in traj])

        # Velocity (skip first 1/3)
        vx = np.gradient(dx, ts)
        vy = np.gradient(dy, ts)
        vz = np.gradient(dz, ts)
        speed = np.sqrt(vx**2 + vy**2 + vz**2)
        skip = max(1, len(ts) // 3)
        v_mean = float(np.mean(speed[skip:]))

        # Hall angle for srcX: theta_H = atan(v_perp / v_parallel)
        # srcX: propagation along +x, so v_parallel = vx, v_perp = sqrt(vy^2+vz^2)
        # srcZ: propagation along +z, so v_parallel = vz, v_perp = sqrt(vx^2+vy^2)
        if src_type == "srcX":
            v_par = float(np.mean(vx[skip:]))
            v_perp = float(np.mean(np.sqrt(vy[skip:]**2 + vz[skip:]**2)))
        else:
            v_par = float(np.mean(vz[skip:]))
            v_perp = float(np.mean(np.sqrt(vx[skip:]**2 + vy[skip:]**2)))

        hall_angle = np.degrees(np.arctan2(abs(v_perp), abs(v_par))) if (abs(v_par) + abs(v_perp)) > 0.01 else np.nan

        dr_final = float(dr[-1])
        dz_final = float(dz[-1])

        print(f"  {src_type} {f:4d}GHz: |dr|={dr_final:.3f}nm  dz={dz_final:+.3f}nm  v̄={v_mean:.3f}nm/ns  θ_H={hall_angle:.1f}°  core={int(cores[0])}→{int(cores[-1])}")
        results.append({
            "freq": f, "dr": dr_final, "dz": dz_final,
            "dx": float(dx[-1]), "dy": float(dy[-1]),
            "v_mean": v_mean, "hall_angle": hall_angle,
            "core0": int(cores[0]), "core_f": int(cores[-1]),
        })

    return results


def main():
    print("=== 点源频率扫描分析 ===\n")

    print("--- srcX ---")
    res_x = analyze_series("srcX")
    print("\n--- srcZ ---")
    res_z = analyze_series("srcZ")

    if not res_x and not res_z:
        print("ERROR: no data")
        return

    # === Figure 1: Frequency response spectrum ===
    fig, axes = plt.subplots(2, 1, figsize=(10, 8), sharex=True)

    if res_x:
        fx = [r["freq"] for r in res_x]
        drx = [r["dr"] for r in res_x]
        dzx = [r["dz"] for r in res_x]
        axes[0].bar(fx, drx, width=60, color='#1f77b4', alpha=0.8, label='|Δr|')
        axes[0].set_ylabel('Displacement |Δr| (nm)', fontsize=11)
        axes[0].set_title('Point Source srcX Frequency Response', fontsize=12)
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)

        # Color bars by dz sign
        colors_z = ['#2ca02c' if d > 0 else '#d62728' for d in dzx]
        ax0t = axes[0].twinx()
        ax0t.scatter(fx, dzx, color=colors_z, s=60, zorder=5, marker='D', label='Δz')
        ax0t.axhline(0, color='k', linewidth=0.5)
        ax0t.set_ylabel('z-displacement Δz (nm)', fontsize=10, color='gray')
        ax0t.legend(loc='upper left')

    if res_z:
        fz = [r["freq"] for r in res_z]
        drz = [r["dr"] for r in res_z]
        dzz = [r["dz"] for r in res_z]
        colors = ['#2ca02c' if d > 0 else '#ff7f0e' for d in dzz]
        axes[1].bar(fz, [abs(d) for d in dzz], width=60, color=colors, alpha=0.8)
        axes[1].set_ylabel('|Δz| (nm)', fontsize=11)
        axes[1].set_xlabel('Frequency (GHz)', fontsize=11)
        axes[1].set_title('Point Source srcZ Frequency Response (green=+z, orange=-z)', fontsize=12)
        axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    fig.savefig(os.path.join(RESULTS_DIR, "point_source_freq_response.png"), dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f"\nSaved: point_source_freq_response.png")

    # === Figure 2: Point vs Plane comparison ===
    # Load plane wave srcX data for comparison
    pw_srcX_dir = "/mnt/d/Research/Hopfion/20260105_frustrated_fm/spin_wave_dynamics/freq_sweep/plane_wave/srcX/results"
    pw_srcZ_dir = "/mnt/d/Research/Hopfion/20260105_frustrated_fm/spin_wave_dynamics/freq_sweep/plane_wave/srcZ/results"

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.5))

    if res_x:
        fx = [r["freq"] for r in res_x]
        drx = [r["dr"] for r in res_x]
        ax1.plot(fx, drx, 'o-', color='#ff7f0e', linewidth=2, markersize=8, label='Point source')
        ax1.set_xlabel('Frequency (GHz)', fontsize=11)
        ax1.set_ylabel('|Δr| (nm)', fontsize=11)
        ax1.set_title('srcX: Point vs Plane Wave', fontsize=12)
        ax1.legend()
        ax1.grid(True, alpha=0.3)

    if res_z:
        fz = [r["freq"] for r in res_z]
        drz = [r["dr"] for r in res_z]
        ax2.plot(fz, drz, 'o-', color='#ff7f0e', linewidth=2, markersize=8, label='Point source')
        ax2.set_xlabel('Frequency (GHz)', fontsize=11)
        ax2.set_ylabel('|Δr| (nm)', fontsize=11)
        ax2.set_title('srcZ: Point vs Plane Wave', fontsize=12)
        ax2.legend()
        ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    fig.savefig(os.path.join(RESULTS_DIR, "point_source_comparison.png"), dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved: point_source_comparison.png")

    # === Figure 3: Hall angle ===
    fig, ax = plt.subplots(figsize=(8, 5))
    if res_x:
        fx = [r["freq"] for r in res_x]
        hx = [r["hall_angle"] for r in res_x]
        valid = [(f, h) for f, h in zip(fx, hx) if not np.isnan(h)]
        if valid:
            ax.plot([v[0] for v in valid], [v[1] for v in valid], 's-',
                    color='#1f77b4', markersize=8, linewidth=1.5, label='srcX (point)')
    if res_z:
        fz = [r["freq"] for r in res_z]
        hz = [r["hall_angle"] for r in res_z]
        valid = [(f, h) for f, h in zip(fz, hz) if not np.isnan(h)]
        if valid:
            ax.plot([v[0] for v in valid], [v[1] for v in valid], 'D-',
                    color='#ff7f0e', markersize=8, linewidth=1.5, label='srcZ (point)')
    ax.axhline(90, color='gray', linestyle='--', linewidth=0.8, label='θ=90°')
    ax.set_xlabel('Frequency (GHz)', fontsize=11)
    ax.set_ylabel('Hall Angle θ_H (°)', fontsize=11)
    ax.set_title('Point Source: Topological Hall Angle', fontsize=12)
    ax.set_ylim(-5, 100)
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    fig.savefig(os.path.join(RESULTS_DIR, "point_source_hall_angle.png"), dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved: point_source_hall_angle.png")

    # === Text summary ===
    txt_path = os.path.join(RESULTS_DIR, "point_source_summary.txt")
    with open(txt_path, "w") as f:
        f.write("=" * 75 + "\n")
        f.write("Point Source Frequency Sweep Summary\n")
        f.write("B_amp=500T (single cell), 0.5ns, autosave=10ps\n")
        f.write("=" * 75 + "\n\n")

        for label, res in [("srcX", res_x), ("srcZ", res_z)]:
            f.write(f"--- {label} ---\n")
            f.write(f"{'f(GHz)':<10} {'|dr|(nm)':<12} {'dz(nm)':<12} {'v̄(nm/ns)':<14} {'θ_H(°)':<10} {'core0':<8} {'core_f':<8}\n")
            f.write("-" * 75 + "\n")
            for r in res:
                ha = f"{r['hall_angle']:.1f}" if not np.isnan(r['hall_angle']) else "N/A"
                f.write(f"{r['freq']:<10} {r['dr']:<12.4f} {r['dz']:<+12.4f} {r['v_mean']:<14.4f} {ha:<10} {r['core0']:<8} {r['core_f']:<8}\n")
            f.write("\n")

            # Find strongest response
            if res:
                best = max(res, key=lambda r: r['dr'])
                f.write(f"  Strongest: {best['freq']}GHz (|dr|={best['dr']:.3f}nm)\n")

                # Dead zones
                dead = [r['freq'] for r in res if r['dr'] < 0.1]
                if dead:
                    f.write(f"  Dead zones (<0.1nm): {dead} GHz\n")
                f.write("\n")

    print(f"Saved: {txt_path}")


if __name__ == "__main__":
    main()
