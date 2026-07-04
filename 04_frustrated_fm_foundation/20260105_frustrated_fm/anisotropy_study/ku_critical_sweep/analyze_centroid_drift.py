"""
分析 ku_critical_sweep 各 Ku 下 Hopfion 质心漂移
初始态均为居中的 hopfion_z_R8_r4.ovf（z=0nm），追踪弛豫至平衡的质心轨迹。

输出（results/）：
  - centroid_z_vs_time.png   : 各 Ku 下 z 质心随时间演化（主图）
  - centroid_xyz_vs_time.png : x/y/z 全分量（仅存活 Ku）
  - centroid_drift_summary.txt
"""

import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import discretisedfield as df

HERE    = os.path.dirname(os.path.abspath(__file__))
OUTDIR  = os.path.join(HERE, "results")
os.makedirs(OUTDIR, exist_ok=True)

# 存活的 Ku（0~52k），消解的跳过
KU_ALIVE = {
    0:     "R8r4_Ku0.out",
    5000:  "R8r4_Ku5k.out",
    10000: "R8r4_Ku10k.out",
    20000: "R8r4_Ku20k.out",
    30000: "R8r4_Ku30k.out",
    40000: "R8r4_Ku40k.out",
    50000: "R8r4_Ku50k.out",
    52000: "R8r4_Ku52k.out",
}
N_FRAMES = 21
DT_NS    = 0.05   # autosave 间隔 ns


def hopfion_centroid(field):
    """加权质心：weight = max(1 - mz, 0)，坐标单位 nm"""
    mz     = field.array[:, :, :, 2]
    weight = np.maximum(1.0 - mz, 0.0)
    w_sum  = np.sum(weight)
    centers = []
    for i in range(3):
        coords = np.linspace(
            field.mesh.region.pmin[i] + field.mesh.cell[i] / 2,
            field.mesh.region.pmax[i] - field.mesh.cell[i] / 2,
            mz.shape[i],
        )
        shape = [1, 1, 1]; shape[i] = mz.shape[i]
        c = np.sum(coords.reshape(shape) * weight) / w_sum * 1e9
        centers.append(c)
    return centers   # [x_nm, y_nm, z_nm]


def load_trajectory(dirname):
    out_dir = os.path.join(HERE, dirname)
    ts, xs, ys, zs = [], [], [], []
    for i in range(N_FRAMES):
        ovf = os.path.join(out_dir, f"m{i:06d}.ovf")
        if not os.path.exists(ovf):
            break
        field = df.Field.from_file(ovf)
        c = hopfion_centroid(field)
        del field
        ts.append(i * DT_NS)
        xs.append(c[0]); ys.append(c[1]); zs.append(c[2])
        print(f"  t={ts[-1]:.2f}ns  x={xs[-1]:.3f}  y={ys[-1]:.3f}  z={zs[-1]:.3f} nm")
    return np.array(ts), np.array(xs), np.array(ys), np.array(zs)


# ── 主循环 ──
all_traj = {}
for ku, dirname in KU_ALIVE.items():
    print(f"\n=== Ku={ku} ===")
    t, x, y, z = load_trajectory(dirname)
    all_traj[ku] = (t, x, y, z)


# ── 图1：z 质心 vs 时间（全 Ku 对比）──
colors = plt.cm.plasma(np.linspace(0.1, 0.9, len(KU_ALIVE)))
fig, ax = plt.subplots(figsize=(9, 5))
for (ku, (t, x, y, z)), col in zip(all_traj.items(), colors):
    dz = z - z[0]
    ax.plot(t, dz, '-o', ms=4, color=col,
            label=f"Ku={ku//1000}k" if ku > 0 else "Ku=0")
ax.axhline(0, color='gray', lw=0.8, ls='--')
ax.set_xlabel("Time (ns)", fontsize=12)
ax.set_ylabel("Δz (nm)  [= z(t) − z(0)]", fontsize=12)
ax.set_title("Hopfion z-centroid drift during relaxation\n(all start from centered R8r4 state)", fontsize=12)
ax.legend(fontsize=8, ncol=2)
ax.grid(True, alpha=0.3)
plt.tight_layout()
fig.savefig(os.path.join(OUTDIR, "centroid_z_vs_time.png"), dpi=150)
plt.close()
print("\nSaved: centroid_z_vs_time.png")


# ── 图2：x/y/z 全分量（每 Ku 一行，仅前4个方便比较）──
SHOW_KU = [0, 10000, 30000, 52000]
fig, axes = plt.subplots(len(SHOW_KU), 3, figsize=(13, 3*len(SHOW_KU)), sharex=True)
labels = ['x', 'y', 'z']
for row, ku in enumerate(SHOW_KU):
    t, x, y, z = all_traj[ku]
    for col, (coord, lab) in enumerate(zip([x, y, z], labels)):
        ax = axes[row, col]
        dc = coord - coord[0]
        ax.plot(t, dc, '-o', ms=3, color='steelblue')
        ax.axhline(0, color='gray', lw=0.7, ls='--')
        ax.set_ylabel(f"Δ{lab} (nm)", fontsize=10)
        if row == 0:
            ax.set_title(f"{lab}-direction drift", fontsize=11)
        if row == len(SHOW_KU)-1:
            ax.set_xlabel("Time (ns)", fontsize=10)
        ax.text(0.98, 0.95, f"Ku={'0' if ku==0 else str(ku//1000)+'k'}",
                transform=ax.transAxes, ha='right', va='top', fontsize=9)
        ax.grid(True, alpha=0.3)
plt.suptitle("Hopfion centroid drift per direction (selected Ku)", fontsize=12, y=1.01)
plt.tight_layout()
fig.savefig(os.path.join(OUTDIR, "centroid_xyz_vs_time.png"), dpi=150, bbox_inches='tight')
plt.close()
print("Saved: centroid_xyz_vs_time.png")


# ── 文字总结 ──
lines = ["Ku_critical_sweep: Hopfion centroid drift during relaxation (R8r4 -> equilibrium)\n",
         f"Initial state: hopfion_z_R8_r4.ovf  (centered at z=0 nm)\n",
         f"Box: 100^3 cells x 0.5nm, PBC(1,1,1)\n\n",
         f"{'Ku (J/m3)':>12}  {'x0':>7}  {'y0':>7}  {'z0':>7}  "
         f"{'dx':>8}  {'dy':>8}  {'dz':>8}  {'|dr|':>8}\n",
         "-"*75 + "\n"]
for ku, (t, x, y, z) in all_traj.items():
    dx = x[-1]-x[0]; dy = y[-1]-y[0]; dz = z[-1]-z[0]
    dr = np.sqrt(dx**2+dy**2+dz**2)
    lines.append(f"{ku:>12}  {x[0]:>7.3f}  {y[0]:>7.3f}  {z[0]:>7.3f}  "
                 f"{dx:>+8.3f}  {dy:>+8.3f}  {dz:>+8.3f}  {dr:>8.3f}\n")

summary_path = os.path.join(OUTDIR, "centroid_drift_summary.txt")
with open(summary_path, "w") as f:
    f.writelines(lines)
print("Saved: centroid_drift_summary.txt")
print("\n" + "".join(lines))
