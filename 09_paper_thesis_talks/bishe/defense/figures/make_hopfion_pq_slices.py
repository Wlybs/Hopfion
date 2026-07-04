"""
Hopfion p, q 双切面 — 回到 1.png 风格（光滑色块），去除箭头，添加 R/r 标注

布局 2×3：
  Row 0: [3D 纵切参考] [p=1] [p=2]
  Row 1: [3D 横切参考] [q=1] [q=2]
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import hsv_to_rgb
from matplotlib import font_manager as fm

font_path = '/tmp/simhei.ttf'
fm.fontManager.addfont(font_path)
plt.rcParams['font.family'] = 'SimHei'
plt.rcParams['axes.unicode_minus'] = False

R_CORE = 2.5
R_SHOW = 1.30
LAMBDA = 0.85


def hopfion_meridian(X, Z, p, q):
    rho = np.abs(X)
    dx = rho - R_CORE
    eta = np.sqrt(dx**2 + Z**2)
    beta = np.where(X >= 0,
                    np.arctan2(Z, X - R_CORE),
                    np.arctan2(Z, -(X + R_CORE)))
    phi = np.where(X >= 0, 0.0, np.pi)
    zeta = (np.pi/2) * np.exp(-eta / LAMBDA)
    perp = np.sin(2*zeta)
    angle = p*beta + q*phi
    return perp*np.cos(angle), perp*np.sin(angle), np.cos(2*zeta)


def hopfion_equatorial(X, Y, p, q):
    rho = np.sqrt(X**2 + Y**2)
    dx = rho - R_CORE
    eta = np.abs(dx)
    beta = np.where(rho >= R_CORE, 0.0, np.pi)
    phi = np.arctan2(Y, X)
    zeta = (np.pi/2) * np.exp(-eta / LAMBDA)
    perp = np.sin(2*zeta)
    angle = p*beta + q*phi
    return perp*np.cos(angle), perp*np.sin(angle), np.cos(2*zeta)


def hopfion_rgba(mx, my, mz, region_mask):
    H = (np.arctan2(my, mx) / (2*np.pi)) % 1.0
    perp = np.sqrt(mx**2 + my**2)
    S = np.clip(perp ** 0.7, 0, 1)
    V = np.full_like(H, 0.95)
    rgb = hsv_to_rgb(np.stack([H, S, V], axis=-1))
    rgba = np.zeros((*rgb.shape[:2], 4))
    rgba[..., :3] = rgb
    rgba[..., 3] = region_mask.astype(float)
    return rgba


def draw_meridian(ax, p, q):
    """光滑色块 + r 标注（无箭头）"""
    nx, nz = 320, 200
    XF, ZF = np.meshgrid(np.linspace(-5, 5, nx), np.linspace(-3, 3, nz))
    mxf, myf, mzf = hopfion_meridian(XF, ZF, p, q)
    dr = np.sqrt((XF - R_CORE)**2 + ZF**2)
    dl = np.sqrt((XF + R_CORE)**2 + ZF**2)
    mask = (dr < R_SHOW) | (dl < R_SHOW)
    rgba = hopfion_rgba(mxf, myf, mzf, mask)
    ax.imshow(rgba, extent=[-5, 5, -3, 3], origin='lower',
              aspect='equal', interpolation='bilinear')

    th = np.linspace(0, 2*np.pi, 200)
    for xc in [R_CORE, -R_CORE]:
        ax.plot(xc + R_SHOW*np.cos(th), R_SHOW*np.sin(th),
                color='#d4332b', linewidth=1.6, alpha=0.85)
        ax.plot(xc, 0, '.', color='#333', markersize=3)

    # r 标注（右管）：水平双箭头从圆心到边缘
    ax.annotate('', xy=(R_CORE + R_SHOW, 0), xytext=(R_CORE, 0),
                arrowprops=dict(arrowstyle='<->', color='black', lw=1.8))
    ax.text(R_CORE + R_SHOW*0.55, 0.32, 'r',
            fontsize=22, fontweight='bold', ha='center', color='black',
            bbox=dict(boxstyle='round,pad=0.15', facecolor='white',
                      edgecolor='none', alpha=0.85))

    ax.set_xlim(-4.0, 4.0)
    ax.set_ylim(-1.5, 1.5)
    ax.set_aspect('equal')
    ax.set_xticks([]); ax.set_yticks([])


def draw_equatorial(ax, p, q):
    """光滑色块 + R 标注（无箭头）"""
    nx = 320
    XF, YF = np.meshgrid(np.linspace(-5, 5, nx), np.linspace(-5, 5, nx))
    mxf, myf, mzf = hopfion_equatorial(XF, YF, p, q)
    rho = np.sqrt(XF**2 + YF**2)
    mask = np.abs(rho - R_CORE) < R_SHOW
    rgba = hopfion_rgba(mxf, myf, mzf, mask)
    ax.imshow(rgba, extent=[-5, 5, -5, 5], origin='lower',
              aspect='equal', interpolation='bilinear')

    th = np.linspace(0, 2*np.pi, 200)
    for rr in [R_CORE - R_SHOW, R_CORE + R_SHOW]:
        ax.plot(rr*np.cos(th), rr*np.sin(th),
                color='#1f77b4', linewidth=1.6, alpha=0.85)
    ax.plot(R_CORE*np.cos(th), R_CORE*np.sin(th),
            color='#d4332b', linewidth=1.0, linestyle=':', alpha=0.6)

    # R 标注：从中心到核心环的径向双箭头
    ang = np.pi / 4
    tip_x, tip_y = R_CORE*np.cos(ang), R_CORE*np.sin(ang)
    ax.annotate('', xy=(tip_x, tip_y), xytext=(0, 0),
                arrowprops=dict(arrowstyle='<->', color='black', lw=1.8))
    ax.text(tip_x*0.55 - 0.25, tip_y*0.55 + 0.25, 'R',
            fontsize=22, fontweight='bold', color='black',
            bbox=dict(boxstyle='round,pad=0.15', facecolor='white',
                      edgecolor='none', alpha=0.85))

    ax.set_xlim(-4.2, 4.2)
    ax.set_ylim(-4.2, 4.2)
    ax.set_aspect('equal')
    ax.set_xticks([]); ax.set_yticks([])


# ---------- 3D 参考 ----------
def _make_torus(R=2.5, r=1.0, nb=60, np_=120):
    bg = np.linspace(0, 2*np.pi, nb)
    pg = np.linspace(0, 2*np.pi, np_)
    B, P = np.meshgrid(bg, pg)
    X = (R + r*np.cos(B)) * np.cos(P)
    Y = (R + r*np.cos(B)) * np.sin(P)
    Z = r*np.sin(B)
    return X, Y, Z


def draw_3d_ref_meridian(ax):
    R, r = R_CORE, 1.0
    X, Y, Z = _make_torus(R, r)
    ax.plot_surface(X, Y, Z, color='#bbbbbb', alpha=0.30,
                    rstride=2, cstride=2, antialiased=True,
                    linewidth=0, shade=True, edgecolor='none')
    pe = 0.5
    px = np.array([[-(R+r+pe), R+r+pe], [-(R+r+pe), R+r+pe]])
    py = np.zeros_like(px)
    pz = np.array([[-(r+pe), -(r+pe)], [r+pe, r+pe]])
    ax.plot_surface(px, py, pz, color='#ffaa00', alpha=0.20,
                    linewidth=0, shade=False)
    th = np.linspace(0, 2*np.pi, 100)
    for xc in [R, -R]:
        ax.plot(xc + r*np.cos(th), np.zeros_like(th), r*np.sin(th),
                color='#d4332b', linewidth=3, zorder=10)

    # R, r 标注（3D 视图里）
    ax.plot([0, R], [0, 0], [0, 0], color='black', linewidth=1.8)
    ax.text(R*0.5, -0.6, 0, 'R', fontsize=18, fontweight='bold', color='black')
    ax.plot([R, R + r], [0, 0], [0, 0], color='black', linewidth=1.8)
    ax.text(R + r*0.4, 0.35, 0.35, 'r', fontsize=18, fontweight='bold', color='black')

    ax.view_init(elev=22, azim=-60)
    ax.set_xlim(-4, 4); ax.set_ylim(-4, 4); ax.set_zlim(-1.8, 1.8)
    ax.set_box_aspect((2, 2, 0.85))
    ax.set_axis_off()


def draw_3d_ref_equatorial(ax):
    R, r = R_CORE, 1.0
    X, Y, Z = _make_torus(R, r)
    ax.plot_surface(X, Y, Z, color='#bbbbbb', alpha=0.30,
                    rstride=2, cstride=2, antialiased=True,
                    linewidth=0, shade=True, edgecolor='none')
    pe = 0.5
    px = np.array([[-(R+r+pe), R+r+pe], [-(R+r+pe), R+r+pe]])
    py = np.array([[-(R+r+pe), -(R+r+pe)], [R+r+pe, R+r+pe]])
    pz = np.zeros_like(px)
    ax.plot_surface(px, py, pz, color='#0099ff', alpha=0.18,
                    linewidth=0, shade=False)
    th = np.linspace(0, 2*np.pi, 200)
    for rho_ring in [R - r, R + r]:
        ax.plot(rho_ring*np.cos(th), rho_ring*np.sin(th), np.zeros_like(th),
                color='#1f77b4', linewidth=3, zorder=10)
    ax.plot(R*np.cos(th), R*np.sin(th), np.zeros_like(th),
            color='#d4332b', linewidth=1.8, linestyle='--', zorder=11)

    # R, r 标注（3D 视图里）
    ax.plot([0, R*0.7], [0, R*0.7], [0, 0], color='black', linewidth=1.8)
    ax.text(R*0.30, R*0.42, 0.4, 'R', fontsize=18, fontweight='bold', color='black')
    ax.plot([R, R + r], [0, 0], [0, 0], color='black', linewidth=1.8)
    ax.text(R + r*0.4, -0.55, 0.35, 'r', fontsize=18, fontweight='bold', color='black')

    ax.view_init(elev=22, azim=-60)
    ax.set_xlim(-4, 4); ax.set_ylim(-4, 4); ax.set_zlim(-1.8, 1.8)
    ax.set_box_aspect((2, 2, 0.85))
    ax.set_axis_off()


# ---------- 主图 ----------
fig = plt.figure(figsize=(11, 6), facecolor='white')
gs = fig.add_gridspec(
    2, 3,
    width_ratios=[1.05, 1.0, 1.0],
    height_ratios=[0.58, 1.0],
    hspace=0.12, wspace=0.02,
    left=0.01, right=0.99, top=0.98, bottom=0.02
)

ax_ref0 = fig.add_subplot(gs[0, 0], projection='3d')
draw_3d_ref_meridian(ax_ref0)
ax_ref0.text2D(0.5, 0.08, '纵切 y = 0',
               ha='center', va='top', fontsize=15, fontweight='bold',
               color='#d4332b', transform=ax_ref0.transAxes)

for i, p in enumerate([1, 2]):
    ax = fig.add_subplot(gs[0, i+1])
    draw_meridian(ax, p, 1)
    ax.set_title(f'p = {p}', fontsize=18, fontweight='bold',
                 color='#d4332b', pad=2)

ax_ref1 = fig.add_subplot(gs[1, 0], projection='3d')
draw_3d_ref_equatorial(ax_ref1)
ax_ref1.text2D(0.5, 0.08, '横切 z = 0',
               ha='center', va='top', fontsize=15, fontweight='bold',
               color='#1f77b4', transform=ax_ref1.transAxes)

for i, q in enumerate([1, 2]):
    ax = fig.add_subplot(gs[1, i+1])
    draw_equatorial(ax, 1, q)
    ax.set_title(f'q = {q}', fontsize=18, fontweight='bold',
                 color='#1f77b4', pad=2)

out = '/mnt/d/Research/Hopfion/09_paper_thesis_talks/bishe/defense/figures/hopfion_pq_slices.png'
plt.savefig(out, dpi=200, bbox_inches='tight', pad_inches=0.05, facecolor='white')
plt.close()
print('Saved:', out)
