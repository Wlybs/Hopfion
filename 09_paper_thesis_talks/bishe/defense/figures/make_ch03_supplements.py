"""
为 ch03 补充 PPT 生成 3 张配图：
  1. construction_concept.png — 均匀背景 → 局部旋转 → Hopfion
  2. torus_coords.png — 环面坐标 (η, β, φ) 标注
  3. viz_examples.png — 不同 (p, q) 可视化样例
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import hsv_to_rgb
from matplotlib.patches import FancyArrowPatch
from matplotlib import font_manager as fm

font_path = '/tmp/simhei.ttf'
fm.fontManager.addfont(font_path)
plt.rcParams['font.family'] = 'SimHei'
plt.rcParams['axes.unicode_minus'] = False


# ============================================================
# 通用 hopfion 模型
# ============================================================
R_CORE = 2.5
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


# ============================================================
# Figure 1: 构造概念图 — 三阶段渐变
# ============================================================
def make_construction_concept():
    fig, axes = plt.subplots(1, 3, figsize=(13, 5), facecolor='white')

    # 左：均匀背景 m = ẑ
    ax = axes[0]
    Xg, Zg = np.meshgrid(np.linspace(-1.5, 1.5, 8), np.linspace(-1.5, 1.5, 8))
    # 全部向上
    ax.quiver(Xg, Zg, np.zeros_like(Xg), np.ones_like(Zg),
              color='#1f77b4', scale=18, width=0.012,
              headwidth=4, headlength=4)
    ax.set_xlim(-2, 2); ax.set_ylim(-2, 2)
    ax.set_aspect('equal'); ax.set_axis_off()
    ax.set_title('① 均匀背景 m₀ = ẑ', fontsize=20, fontweight='bold',
                 color='#1f77b4', pad=10)

    # 中：局部旋转 R(r) — 部分扭转
    ax = axes[1]
    Xg, Zg = np.meshgrid(np.linspace(-1.5, 1.5, 8), np.linspace(-1.5, 1.5, 8))
    # 让中心区域有旋转，外围保持向上
    rr = np.sqrt(Xg**2 + Zg**2)
    weight = np.exp(-rr**2 / 1.2)
    angle = weight * np.pi * 0.7  # 中心旋转角度大
    mx = np.sin(angle) * np.cos(np.arctan2(Zg, Xg))
    mz = np.cos(angle)
    H = (np.arctan2(mz, mx) / (2*np.pi)) % 1.0
    S = np.clip(np.sin(angle)*1.2, 0, 1)
    V = np.full_like(H, 0.85)
    rgb = hsv_to_rgb(np.stack([H, S, V], axis=-1))
    for i in range(Xg.shape[0]):
        for j in range(Xg.shape[1]):
            c = rgb[i, j]
            xv, zv = Xg[i, j], Zg[i, j]
            dx_ = mx[i, j] * 0.30
            dz_ = mz[i, j] * 0.30
            ax.arrow(xv - dx_/2, zv - dz_/2, dx_, dz_,
                     head_width=0.10, head_length=0.10,
                     fc=c, ec=c, linewidth=1.6,
                     length_includes_head=True)
    ax.set_xlim(-2, 2); ax.set_ylim(-2, 2)
    ax.set_aspect('equal'); ax.set_axis_off()
    ax.set_title('② 施加局部旋转 R(r)', fontsize=20, fontweight='bold',
                 color='#d4a017', pad=10)

    # 右：完整 Hopfion (用 equatorial 切面渲染 — 看起来像甜甜圈)
    ax = axes[2]
    nx = 200
    XF, YF = np.meshgrid(np.linspace(-2, 2, nx), np.linspace(-2, 2, nx))
    # 缩放成局部 hopfion
    R_local = 1.0
    rho = np.sqrt(XF**2 + YF**2)
    dxe = rho - R_local
    eta = np.abs(dxe)
    beta = np.where(rho >= R_local, 0.0, np.pi)
    phi = np.arctan2(YF, XF)
    zeta = (np.pi/2) * np.exp(-eta / 0.5)
    perp = np.sin(2*zeta)
    angle = 1*beta + 1*phi
    mxf = perp*np.cos(angle); myf = perp*np.sin(angle); mzf = np.cos(2*zeta)
    H = (np.arctan2(myf, mxf) / (2*np.pi)) % 1.0
    S = np.clip(perp ** 0.7, 0, 1)
    V = np.full_like(H, 0.95)
    rgb = hsv_to_rgb(np.stack([H, S, V], axis=-1))
    rgba = np.zeros((*rgb.shape[:2], 4))
    rgba[..., :3] = rgb
    rgba[..., 3] = (np.abs(rho - R_local) < 0.5).astype(float)
    ax.imshow(rgba, extent=[-2, 2, -2, 2], origin='lower',
              aspect='equal', interpolation='bilinear')
    ax.set_xlim(-2, 2); ax.set_ylim(-2, 2)
    ax.set_aspect('equal'); ax.set_axis_off()
    ax.set_title('③ 任意拓扑荷 Hopfion', fontsize=20, fontweight='bold',
                 color='#d4332b', pad=10)

    # 阶段之间的箭头：用 FancyArrowPatch
    from matplotlib.patches import FancyArrowPatch
    arrow1 = FancyArrowPatch((0.345, 0.50), (0.385, 0.50),
                              transform=fig.transFigure,
                              arrowstyle='->,head_width=0.8,head_length=0.8',
                              mutation_scale=30, color='#666', lw=4)
    arrow2 = FancyArrowPatch((0.665, 0.50), (0.705, 0.50),
                              transform=fig.transFigure,
                              arrowstyle='->,head_width=0.8,head_length=0.8',
                              mutation_scale=30, color='#666', lw=4)
    fig.patches.extend([arrow1, arrow2])

    plt.subplots_adjust(left=0.02, right=0.98, top=0.92, bottom=0.04,
                        wspace=0.25)
    out = '/mnt/d/Research/Hopfion/09_paper_thesis_talks/bishe/defense/figures/ch03_construction_concept.png'
    plt.savefig(out, dpi=200, bbox_inches='tight', pad_inches=0.1,
                facecolor='white')
    plt.close()
    print('Saved:', out)


# ============================================================
# Figure 2: 环面坐标系
# ============================================================
def make_torus_coords():
    fig = plt.figure(figsize=(8, 6), facecolor='white')
    ax = fig.add_subplot(111, projection='3d')

    R, r = 2.5, 0.9
    bg = np.linspace(0, 2*np.pi, 80)
    pg = np.linspace(0, 2*np.pi, 160)
    B, P = np.meshgrid(bg, pg)
    X = (R + r*np.cos(B)) * np.cos(P)
    Y = (R + r*np.cos(B)) * np.sin(P)
    Z = r*np.sin(B)
    ax.plot_surface(X, Y, Z, color='#dde7f0', alpha=0.55,
                    rstride=2, cstride=2, antialiased=True,
                    linewidth=0, shade=True, edgecolor='none')

    # η 方向：从核心环径向往外（在右侧管子上画一条）
    eta_arrow_x = [R, R + r + 0.3]
    eta_arrow_y = [0, 0]
    eta_arrow_z = [0, 0]
    ax.plot(eta_arrow_x, eta_arrow_y, eta_arrow_z,
            color='#d4332b', linewidth=4)
    ax.scatter([eta_arrow_x[1]], [eta_arrow_y[1]], [eta_arrow_z[1]],
               color='#d4332b', s=80, marker='>')
    ax.text(R + r - 0.4, 1.0, 0.5, 'η 径向',
            fontsize=18, fontweight='bold', color='#d4332b')

    # β 方向：绕管子小圈（在右侧管子上）
    b_arc = np.linspace(0, 1.7*np.pi, 60)
    bx = R + (r + 0.12)*np.cos(b_arc)
    by = np.zeros_like(b_arc)
    bz = (r + 0.12)*np.sin(b_arc)
    ax.plot(bx, by, bz, color='#d4a017', linewidth=4)
    ax.scatter([bx[-1]], [by[-1]], [bz[-1]], color='#d4a017', s=80, marker='>')
    ax.text(R - 0.3, 2.0, 1.0, 'β 小圈',
            fontsize=18, fontweight='bold', color='#d4a017')

    # φ 方向：绕大圈
    p_arc = np.linspace(0.1, 1.75*np.pi, 100)
    rad = R + r + 0.55
    fx = rad * np.cos(p_arc)
    fy = rad * np.sin(p_arc)
    fz = np.full_like(p_arc, 0.05)
    ax.plot(fx, fy, fz, color='#1f77b4', linewidth=4)
    ax.scatter([fx[-1]], [fy[-1]], [fz[-1]], color='#1f77b4', s=80, marker='>')
    ax.text(-1.5, -rad - 0.3, 0.5, 'φ 大圈',
            fontsize=18, fontweight='bold', color='#1f77b4')

    ax.view_init(elev=24, azim=-58)
    ax.set_xlim(-3.5, 3.5); ax.set_ylim(-3.5, 3.5); ax.set_zlim(-2, 2)
    ax.set_box_aspect((2, 2, 0.85))
    ax.set_axis_off()

    out = '/mnt/d/Research/Hopfion/09_paper_thesis_talks/bishe/defense/figures/ch03_torus_coords.png'
    plt.savefig(out, dpi=200, bbox_inches='tight', pad_inches=0.1,
                facecolor='white')
    plt.close()
    print('Saved:', out)


# ============================================================
# Figure 3: 可视化样例 (4 种 (p, q))
# ============================================================
def make_viz_examples():
    fig, axes = plt.subplots(1, 4, figsize=(16, 4.5), facecolor='white')

    cases = [(1, 1), (2, 1), (1, 2), (2, 2)]
    labels = ['Q_H = 1', 'Q_H = 2  (p=2, q=1)', 'Q_H = 2  (p=1, q=2)', 'Q_H = 4']

    for ax, (p, q), lab in zip(axes, cases, labels):
        nx = 320
        XF, YF = np.meshgrid(np.linspace(-4.5, 4.5, nx),
                             np.linspace(-4.5, 4.5, nx))
        # 用 equatorial 切面作为可视化代表（顶视）
        rho = np.sqrt(XF**2 + YF**2)
        dxe = rho - R_CORE
        eta = np.abs(dxe)
        beta = np.where(rho >= R_CORE, 0.0, np.pi)
        phi = np.arctan2(YF, XF)
        zeta = (np.pi/2) * np.exp(-eta / LAMBDA)
        perp = np.sin(2*zeta)
        ang = p*beta + q*phi
        mx = perp*np.cos(ang)
        my = perp*np.sin(ang)
        mz = np.cos(2*zeta)

        H = (np.arctan2(my, mx) / (2*np.pi)) % 1.0
        S = np.clip(perp ** 0.7, 0, 1)
        V = np.full_like(H, 0.95)
        rgb = hsv_to_rgb(np.stack([H, S, V], axis=-1))
        rgba = np.zeros((*rgb.shape[:2], 4))
        rgba[..., :3] = rgb
        rgba[..., 3] = (np.abs(rho - R_CORE) < 1.3).astype(float)
        ax.imshow(rgba, extent=[-4.5, 4.5, -4.5, 4.5], origin='lower',
                  aspect='equal', interpolation='bilinear')

        # 环带边界
        th = np.linspace(0, 2*np.pi, 200)
        for rr in [R_CORE - 1.3, R_CORE + 1.3]:
            ax.plot(rr*np.cos(th), rr*np.sin(th),
                    color='#888', linewidth=1.0, alpha=0.5)

        ax.set_xlim(-4.5, 4.5); ax.set_ylim(-4.5, 4.5)
        ax.set_aspect('equal'); ax.set_axis_off()
        ax.set_title(lab, fontsize=15, fontweight='bold',
                     color='#222', pad=8)

    plt.subplots_adjust(left=0.01, right=0.99, top=0.90, bottom=0.02,
                        wspace=0.05)
    out = '/mnt/d/Research/Hopfion/09_paper_thesis_talks/bishe/defense/figures/ch03_viz_examples.png'
    plt.savefig(out, dpi=200, bbox_inches='tight', pad_inches=0.1,
                facecolor='white')
    plt.close()
    print('Saved:', out)


if __name__ == '__main__':
    make_construction_concept()
    make_torus_coords()
    make_viz_examples()
