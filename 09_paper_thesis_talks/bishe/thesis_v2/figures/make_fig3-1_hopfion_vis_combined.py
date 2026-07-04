"""Generate fig3-1_hopfion_vis_combined.png

2x2 subplots of four Hopfion configurations with a shared right-side colorbar.
No super-title. Colorbar label in Chinese.

Run:
    source /mnt/d/Research/Hopfion/hopfion/bin/activate
    python make_fig3-1_hopfion_vis_combined.py
"""
import os
import sys
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.colors import Normalize
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from scipy.ndimage import map_coordinates
from skimage import measure
import discretisedfield as df

# ---- Chinese font ----
_FONT_CANDIDATES = [
    "/mnt/c/Windows/Fonts/simhei.ttf",
    "/mnt/c/Windows/Fonts/msyh.ttc",
]
for _fp in _FONT_CANDIDATES:
    if os.path.exists(_fp):
        font_manager.fontManager.addfont(_fp)
        _name = font_manager.FontProperties(fname=_fp).get_name()
        mpl.rcParams["font.sans-serif"] = [_name] + mpl.rcParams["font.sans-serif"]
        mpl.rcParams["font.family"] = "sans-serif"
        break
mpl.rcParams["axes.unicode_minus"] = False
mpl.rcParams["mathtext.fontset"] = "stix"

OVF_DIR = "/mnt/d/Research/Hopfion/95_shared_scripts"
OUT = "/mnt/d/Research/Hopfion/09_paper_thesis_talks/bishe/thesis_v2/figures/fig3-1_hopfion_vis_combined.png"
PANELS = [
    ("hopfion_Qh1_p1q1.ovf", "(a) $Q_H=1$, $p=1$, $q=1$"),
    ("hopfion_Qh2_p2q1.ovf", "(b) $Q_H=2$, $p=2$, $q=1$"),
    ("hopfion_Qh2_p1q2.ovf", "(c) $Q_H=2$, $p=1$, $q=2$"),
    ("hopfion_Qh4_p2q2.ovf", "(d) $Q_H=4$, $p=2$, $q=2$"),
]


def angular_median(angles):
    x = np.cos(angles)
    y = np.sin(angles)
    return np.arctan2(np.mean(y, axis=1), np.mean(x, axis=1))


def interpolate_colors(m_field, verts):
    pmin = m_field.mesh.region.pmin
    cell = m_field.mesh.cell
    idx = ((verts - pmin) / cell).T
    mx = map_coordinates(m_field.array[..., 0], idx, order=1, mode="nearest")
    my = map_coordinates(m_field.array[..., 1], idx, order=1, mode="nearest")
    return np.arctan2(my, mx)


def render_panel(ax, ovf_path, subtitle):
    m = df.Field.from_file(ovf_path)
    verts, faces, _, _ = measure.marching_cubes(
        volume=m.array[..., 2], level=0, spacing=m.mesh.cell
    )
    verts += m.mesh.region.pmin
    vertex_angles = interpolate_colors(m, verts)
    face_angles = angular_median(vertex_angles[faces])
    norm = Normalize(vmin=-np.pi, vmax=np.pi)
    face_colors = plt.cm.hsv(norm(face_angles))

    mesh = Poly3DCollection(verts[faces] * 1e9)
    mesh.set_facecolor(face_colors)
    ax.add_collection3d(mesh)
    ax.set_xlim(verts[:, 0].min() * 1e9, verts[:, 0].max() * 1e9)
    ax.set_ylim(verts[:, 1].min() * 1e9, verts[:, 1].max() * 1e9)
    ax.set_zlim(verts[:, 2].min() * 1e9, verts[:, 2].max() * 1e9)
    ax.set_xlabel("x (nm)", fontsize=14)
    ax.set_ylabel("y (nm)", fontsize=14)
    ax.set_zlabel("z (nm)", fontsize=14)
    ax.tick_params(axis="both", which="major", labelsize=12)
    for pane_axis in (ax.xaxis, ax.yaxis, ax.zaxis):
        pane_axis.pane.set_facecolor("white")
        pane_axis.pane.set_edgecolor("white")
        pane_axis.pane.set_alpha(1.0)
    ax.set_facecolor("white")
    axis_limits = np.array([ax.get_xlim(), ax.get_ylim(), ax.get_zlim()])
    ax.set_box_aspect(np.ptp(axis_limits, axis=1))
    ax.text2D(0.5, -0.05, subtitle, transform=ax.transAxes,
              ha="center", va="top", fontsize=20)


def main():
    fig = plt.figure(figsize=(13, 11))
    for i, (fname, subtitle) in enumerate(PANELS):
        ax = fig.add_subplot(2, 2, i + 1, projection="3d")
        ovf_path = os.path.join(OVF_DIR, fname)
        if not os.path.exists(ovf_path):
            print(f"[ERROR] missing OVF: {ovf_path}", file=sys.stderr)
            sys.exit(1)
        render_panel(ax, ovf_path, subtitle)

    norm = Normalize(vmin=-np.pi, vmax=np.pi)
    sm = plt.cm.ScalarMappable(cmap="hsv", norm=norm)
    sm.set_array([])
    cax = fig.add_axes([0.88, 0.20, 0.022, 0.60])
    cbar = fig.colorbar(sm, cax=cax)
    cbar.set_label(r"面内磁化方向角 $\varphi = \arctan(m_y/m_x)$", fontsize=22, labelpad=14)
    cbar.set_ticks([-np.pi, -np.pi / 2, 0, np.pi / 2, np.pi])
    cbar.set_ticklabels([r"$-\pi$", r"$-\pi/2$", "0", r"$\pi/2$", r"$\pi$"])
    cbar.ax.tick_params(labelsize=17)

    fig.subplots_adjust(left=0.03, right=0.86, top=0.97, bottom=0.04,
                         wspace=0.05, hspace=0.15)
    fig.savefig(OUT, dpi=300, bbox_inches="tight")
    print(f"[OK] saved: {OUT}")


if __name__ == "__main__":
    main()
