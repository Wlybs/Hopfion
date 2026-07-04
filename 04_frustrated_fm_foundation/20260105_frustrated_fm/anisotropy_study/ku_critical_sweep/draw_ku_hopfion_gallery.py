"""
绘制不同 Ku1 下 Hopfion 稳态构型（mz=0等值面），用于论文图。
使用 draw_afm_new.py 的 AFM 解调 + 等值面渲染管线。

输出到 ku_critical_sweep/results/ 目录。
"""
import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from matplotlib.colors import Normalize
from skimage import measure
import discretisedfield as df

# 复用共享库
sys.path.insert(0, "/mnt/d/Research/Hopfion/95_shared_scripts")
from draw_afm_new import demodulate_afm, interpolate_colors_for_vertices, angular_median

SWEEP_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(SWEEP_DIR, "results")

# 选取代表性 Ku 值：存活态梯度 + 临界前最后一帧 + 消失态
CASES = [
    # (Ku_label, out_dir, frame_idx, t_ns, note)
    ("Ku=0",   "R8r4_Ku0.out",   20, 1.0, "stable"),
    ("Ku=10k", "R8r4_Ku10k.out", 20, 1.0, "stable"),
    ("Ku=30k", "R8r4_Ku30k.out", 20, 1.0, "stable"),
    ("Ku=50k", "R8r4_Ku50k.out", 20, 1.0, "stable, near critical"),
    ("Ku=52k", "R8r4_Ku52k.out", 20, 1.0, "last alive"),
    ("Ku=55k", "R8r4_Ku55k.out", 12, 0.6, "last frame with Hopfion"),
]


def render_single(ax, ovf_path, label, afm_hint="auto"):
    """在给定的 3D axes 上渲染 Hopfion 等值面。"""
    raw = df.Field.from_file(ovf_path)
    m_demod, (mode, offsets) = demodulate_afm(raw, afm_hint=afm_hint)
    mz = m_demod.array[..., 2]

    # 检查是否有 mz=0 等值面
    if np.min(mz) >= 0 or np.max(mz) <= 0:
        ax.text(0.5, 0.5, 0.5, "Collapsed\n(uniform state)",
                transform=ax.transAxes, ha='center', va='center',
                fontsize=11, color='red', weight='bold')
        ax.set_title(label, fontsize=11, weight='bold')
        return

    cell = m_demod.mesh.cell
    pmin = np.array(m_demod.mesh.region.pmin)

    verts, faces, _, _ = measure.marching_cubes(volume=mz, level=0, spacing=cell)
    verts += pmin

    # 颜色: arctan2(my, mx) → HSV
    colors_angles = interpolate_colors_for_vertices(m_demod, verts)
    face_angles = colors_angles[faces]
    median_face_angles = angular_median(face_angles)

    norm = Normalize(vmin=-np.pi, vmax=np.pi)
    face_colors = plt.cm.hsv(norm(median_face_angles))

    mesh_coll = Poly3DCollection(verts[faces] * 1e9, linewidths=0)
    mesh_coll.set_facecolor(face_colors)
    ax.add_collection3d(mesh_coll)

    # 统一坐标范围（以系统中心为基准，±20nm）
    box_center = (np.array(m_demod.mesh.region.pmin) +
                  np.array(m_demod.mesh.region.pmax)) / 2 * 1e9
    half = 15  # nm
    ax.set_xlim(box_center[0] - half, box_center[0] + half)
    ax.set_ylim(box_center[1] - half, box_center[1] + half)
    ax.set_zlim(box_center[2] - half, box_center[2] + half)

    ax.set_xlabel("x (nm)", fontsize=8, labelpad=1)
    ax.set_ylabel("y (nm)", fontsize=8, labelpad=1)
    ax.set_zlabel("z (nm)", fontsize=8, labelpad=1)
    ax.tick_params(labelsize=7)
    ax.set_title(label, fontsize=11, weight='bold')

    # 统一视角
    ax.view_init(elev=25, azim=-60)

    del raw, m_demod


def main():
    n = len(CASES)
    fig = plt.figure(figsize=(5 * n, 5))

    for i, (label, out_dir, frame, t_ns, note) in enumerate(CASES):
        ovf = os.path.join(SWEEP_DIR, out_dir, f"m{frame:06d}.ovf")
        if not os.path.exists(ovf):
            print(f"[SKIP] {ovf} not found")
            continue

        print(f"[{i+1}/{n}] {label} (t={t_ns}ns, {note})")
        ax = fig.add_subplot(1, n, i + 1, projection='3d')
        render_single(ax, ovf, f"{label}\nt={t_ns}ns", afm_hint="none")

    # 添加全局 colorbar
    sm = plt.cm.ScalarMappable(cmap='hsv', norm=Normalize(-np.pi, np.pi))
    cbar = fig.colorbar(sm, ax=fig.axes, shrink=0.5, aspect=30,
                        pad=0.02, location='bottom')
    cbar.set_label(r'In-plane angle $\arctan(m_y/m_x)$', fontsize=10)
    cbar.set_ticks([-np.pi, -np.pi/2, 0, np.pi/2, np.pi])
    cbar.set_ticklabels([r'$-\pi$', r'$-\pi/2$', '0', r'$\pi/2$', r'$\pi$'])

    plt.suptitle("Hopfion configuration vs anisotropy $K_{u1}$ (frustrated FM, cellsize=0.5nm)",
                 fontsize=14, y=1.02)
    plt.tight_layout()
    out = os.path.join(RESULTS_DIR, "hopfion_gallery_vs_Ku.png")
    plt.savefig(out, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"\n[SAVED] {out}")


if __name__ == "__main__":
    main()
