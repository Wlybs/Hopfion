"""
Hopfion p, q 缠绕数解释图 v5

关键修复（相对 v4）：
- 顶部甜甜圈改用纯 2D 画法（椭圆 + 路径），不再因 3D 内边距导致小小一坨
- p 环 / q 环用相同的子图坐标范围（fixed_lim），让 q 环真正"看起来更大"
- 标签全部放在图形外围，避免被遮挡
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import hsv_to_rgb
from matplotlib.patches import Ellipse, PathPatch
from matplotlib.path import Path
from matplotlib import font_manager as fm

font_path = '/tmp/simhei.ttf'
fm.fontManager.addfont(font_path)
plt.rcParams['font.family'] = 'SimHei'
plt.rcParams['axes.unicode_minus'] = False


# ---------- 箭头环 ----------
def draw_arrow_ring(ax, n_wind, ring_r=1.0, n_arrows=12,
                    arrow_len=None, fixed_lim=2.4):
    if arrow_len is None:
        arrow_len = ring_r * 0.55
    # 底色环
    th = np.linspace(0, 2*np.pi, 200)
    ax.plot(ring_r*np.cos(th), ring_r*np.sin(th),
            color='#aaa', lw=2.0, alpha=0.45, zorder=0)
    # 箭头
    angles = np.linspace(0, 2*np.pi, n_arrows, endpoint=False)
    for a in angles:
        cx = ring_r * np.cos(a)
        cy = ring_r * np.sin(a)
        arrow_dir = n_wind * a
        dx = arrow_len * np.cos(arrow_dir)
        dy = arrow_len * np.sin(arrow_dir)
        c = hsv_to_rgb([(arrow_dir / (2*np.pi)) % 1.0, 0.82, 0.95])
        ax.arrow(cx - dx/2, cy - dy/2, dx, dy,
                 head_width=arrow_len*0.32, head_length=arrow_len*0.34,
                 fc=c, ec=c, linewidth=2.2,
                 length_includes_head=True, zorder=3)
    # 起点
    ax.plot([ring_r], [0], 'o', color='black', markersize=6, zorder=5)
    # 固定的坐标范围 → p 环（小）和 q 环（大）视觉上有区别
    ax.set_xlim(-fixed_lim, fixed_lim)
    ax.set_ylim(-fixed_lim, fixed_lim)
    ax.set_aspect('equal')
    ax.set_axis_off()


# ---------- 2D 甜甜圈参考图 ----------
def draw_donut_2d(ax):
    Rx, Ry = 4.5, 1.7        # 外椭圆
    rx, ry = 1.5, 0.55       # 内椭圆（洞）

    # 填充环形主体
    theta = np.linspace(0, 2*np.pi, 200)
    outer = np.column_stack([Rx*np.cos(theta), Ry*np.sin(theta)])
    inner = np.column_stack([rx*np.cos(theta[::-1]), ry*np.sin(theta[::-1])])
    verts = np.vstack([outer, inner])
    codes = (
        [Path.MOVETO] + [Path.LINETO]*(len(outer)-1) +
        [Path.MOVETO] + [Path.LINETO]*(len(inner)-1)
    )
    patch = PathPatch(Path(verts, codes),
                      facecolor='#dde7f0', edgecolor='#666', linewidth=1.8)
    ax.add_patch(patch)

    # 阴影（增强 3D 感）
    shadow = Ellipse((0, -Ry - 0.15), width=Rx*1.8, height=Ry*0.35,
                     fill=True, facecolor='gray', alpha=0.15, zorder=-1)
    ax.add_patch(shadow)

    # === β 标注：小圈截面（左侧）===
    cx_tube = -(Rx + rx) / 2          # 管道中心
    tube_h = Ry - ry + 0.3
    # 椭圆代表管道截面
    tube = Ellipse((cx_tube, 0), width=0.7, height=tube_h,
                   fill=False, edgecolor='#d4332b', linewidth=2.5, zorder=2)
    ax.add_patch(tube)
    # 顺时针箭头沿椭圆走
    arc_t = np.linspace(np.pi*0.20, np.pi*1.80, 60)
    ax_t = cx_tube + 0.30 * np.cos(arc_t)
    ay_t = (tube_h/2) * np.sin(arc_t)
    ax.plot(ax_t, ay_t, color='#d4332b', linewidth=3, zorder=3)
    ax.annotate('',
                xy=(ax_t[-1], ay_t[-1]),
                xytext=(ax_t[-4], ay_t[-4]),
                arrowprops=dict(arrowstyle='->', color='#d4332b', lw=3))
    ax.text(cx_tube - 0.8, 0, 'β\n小圈方向',
            color='#d4332b', fontsize=16, fontweight='bold',
            ha='right', va='center')

    # === φ 标注：大圈方向（外侧弧）===
    phi_arc_t = np.linspace(np.pi*0.18, np.pi*0.82, 100)
    phi_R = Rx + 0.55
    phi_r = Ry + 0.35
    fx = phi_R * np.cos(phi_arc_t)
    fy = phi_r * np.sin(phi_arc_t)
    ax.plot(fx, fy, color='#1f77b4', linewidth=3, zorder=3)
    ax.annotate('',
                xy=(fx[-1], fy[-1]),
                xytext=(fx[-4], fy[-4]),
                arrowprops=dict(arrowstyle='->', color='#1f77b4', lw=3))
    ax.text(0, Ry + 0.95, 'φ  大圈方向',
            color='#1f77b4', fontsize=16, fontweight='bold',
            ha='center', va='bottom')

    ax.set_xlim(-Rx - 2.6, Rx + 1.5)
    ax.set_ylim(-Ry - 1.0, Ry + 1.6)
    ax.set_aspect('equal')
    ax.set_axis_off()


# ---------- 主图 ----------
fig = plt.figure(figsize=(15, 15), facecolor='white')

gs = fig.add_gridspec(
    6, 3,
    height_ratios=[1.20, 0.18, 1.00, 0.18, 1.00, 0.55],
    hspace=0.20, wspace=0.05,
    left=0.04, right=0.96, top=0.93, bottom=0.03
)

# === Row 0：2D 甜甜圈参考 ===
ax_top = fig.add_subplot(gs[0, :])
draw_donut_2d(ax_top)

# === Row 1：p 章节标签 ===
ax_lbl_p = fig.add_subplot(gs[1, :])
ax_lbl_p.axis('off')
ax_lbl_p.set_xlim(0, 1); ax_lbl_p.set_ylim(0, 1)
ax_lbl_p.text(0.5, 0.5,
              'p：沿 β（小圈）走一圈时，磁矩旋转 p 次',
              ha='center', va='center', fontsize=16,
              fontweight='bold', color='#d4332b',
              bbox=dict(boxstyle='round,pad=0.55', facecolor='#fdecec',
                        edgecolor='#d4332b', linewidth=1.8))

# === Row 2：p = 1, 2, 3 ===
for i, p in enumerate([1, 2, 3]):
    ax = fig.add_subplot(gs[2, i])
    draw_arrow_ring(ax, p, ring_r=0.85, fixed_lim=2.4)
    ax.set_title(f'p = {p}　箭头转 {p} 圈',
                 fontsize=15, fontweight='bold', color='#d4332b', pad=4)

# === Row 3：q 章节标签 ===
ax_lbl_q = fig.add_subplot(gs[3, :])
ax_lbl_q.axis('off')
ax_lbl_q.set_xlim(0, 1); ax_lbl_q.set_ylim(0, 1)
ax_lbl_q.text(0.5, 0.5,
              'q：沿 φ（大圈）走一圈时，磁矩旋转 q 次',
              ha='center', va='center', fontsize=16,
              fontweight='bold', color='#1f77b4',
              bbox=dict(boxstyle='round,pad=0.55', facecolor='#e8effa',
                        edgecolor='#1f77b4', linewidth=1.8))

# === Row 4：q = 1, 2, 3 ===
for i, q in enumerate([1, 2, 3]):
    ax = fig.add_subplot(gs[4, i])
    draw_arrow_ring(ax, q, ring_r=1.70, fixed_lim=2.4)
    ax.set_title(f'q = {q}　箭头转 {q} 圈',
                 fontsize=15, fontweight='bold', color='#1f77b4', pad=4)

# === Row 5：Q_H 公式 ===
ax_bot = fig.add_subplot(gs[5, :])
ax_bot.axis('off')
ax_bot.set_xlim(0, 1)
ax_bot.set_ylim(0, 1)
ax_bot.text(0.5, 0.78,
            r'$Q_H \; = \; p \, \times \, q$',
            ha='center', va='center', fontsize=32, color='#222',
            bbox=dict(boxstyle='round,pad=0.55', facecolor='#fff9e0',
                      edgecolor='#d4a017', linewidth=2.5))
ax_bot.text(0.5, 0.38,
            '拓扑荷 = 两个方向上旋转次数的乘积',
            ha='center', va='center', fontsize=13, color='#666', style='italic')
ax_bot.text(0.5, 0.10,
            '例：(p=1,q=1)→Q_H=1     (p=2,q=1)→Q_H=2     '
            '(p=1,q=2)→Q_H=2     (p=2,q=2)→Q_H=4     (p=2,q=3)→Q_H=6',
            ha='center', va='center', fontsize=11, color='#555')

fig.suptitle('Hopfion 的两个缠绕数：p 和 q',
             fontsize=22, fontweight='bold', y=0.98)

out = '/mnt/d/Research/Hopfion/09_paper_thesis_talks/bishe/defense/figures/hopfion_pq_explained.png'
plt.savefig(out, dpi=200, bbox_inches='tight', facecolor='white')
plt.close()
print('Saved:', out)
