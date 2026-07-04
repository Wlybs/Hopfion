#!/usr/bin/env python3
# Q_H=1 Hopfion core structure schematic for thesis ch02 2.3.2
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib.lines import Line2D
from mpl_toolkits.axes_grid1.inset_locator import inset_axes

from matplotlib import font_manager as _fm
for _fp in ('/mnt/c/Windows/Fonts/simhei.ttf', '/mnt/c/Windows/Fonts/msyh.ttc'):
    try: _fm.fontManager.addfont(_fp)
    except Exception: pass
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Noto Sans CJK SC', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

R = 8.0
r_tube = 3.5
r_core = 0.8

fig = plt.figure(figsize=(9.5, 7.2))
ax = fig.add_subplot(111, projection='3d')

# ---- 1. transition shell (m_z = 0 iso-surface), colour = in-plane phase ----
theta = np.linspace(0, 2*np.pi, 140)
beta = np.linspace(0, 2*np.pi, 80)
Theta, Beta = np.meshgrid(theta, beta)
X = (R + r_tube*np.cos(Beta)) * np.cos(Theta)
Y = (R + r_tube*np.cos(Beta)) * np.sin(Theta)
Z = r_tube * np.sin(Beta)
phase = Theta
colors = cm.hsv((phase / (2*np.pi)) % 1.0)
ax.plot_surface(X, Y, Z, facecolors=colors, alpha=0.22,
                linewidth=0, antialiased=True, rstride=2, cstride=2, shade=False)

# ---- 2. core preimage m_z=-1: thick torus tube on z=0, radius R ----
tc_theta = np.linspace(0, 2*np.pi, 200)
tc_beta = np.linspace(0, 2*np.pi, 40)
Tct, Tcb = np.meshgrid(tc_theta, tc_beta)
Xc = (R + r_core*np.cos(Tcb)) * np.cos(Tct)
Yc = (R + r_core*np.cos(Tcb)) * np.sin(Tct)
Zc = r_core * np.sin(Tcb)
ax.plot_surface(Xc, Yc, Zc, color='#0b2a8a', alpha=0.95,
                linewidth=0, antialiased=True, rstride=1, cstride=1, shade=True)

# ---- 3. background m_z=+1 up-arrows ----
bg_ang = np.linspace(0, 2*np.pi, 6, endpoint=False) + np.pi/12
for ang in bg_ang:
    ax.quiver(17.5*np.cos(ang), 17.5*np.sin(ang), -2, 0, 0, 5,
              color='#c21d1d', arrow_length_ratio=0.32, linewidth=2.0)
for (bx, by) in [(0, 0)]:
    ax.quiver(bx, by, 10.5, 0, 0, 4, color='#c21d1d',
              arrow_length_ratio=0.38, linewidth=2.0)
    ax.quiver(bx, by, -14.5, 0, 0, 4, color='#c21d1d',
              arrow_length_ratio=0.38, linewidth=2.0)

# ---- 4. transition-zone rotating arrows along one poloidal ring (front-facing) ----
n_arrow = 14
beta_arr = np.linspace(0, 2*np.pi, n_arrow, endpoint=False)
t_pos = -np.pi/2   # 前方最近观察者位置（y 负方向）
for b in beta_arr:
    px = (R + r_tube*np.cos(b)) * np.cos(t_pos)
    py = (R + r_tube*np.cos(b)) * np.sin(t_pos)
    pz = r_tube * np.sin(b)
    mx = np.sin(b) * np.cos(t_pos)
    my = np.sin(b) * np.sin(t_pos)
    mz = -np.cos(b)
    ax.quiver(px, py, pz, mx, my, mz, length=2.6,
              color='#111111', arrow_length_ratio=0.45, linewidth=1.4)

# ---- axes ----
ax.set_xlabel('x', fontsize=11, labelpad=2)
ax.set_ylabel('y', fontsize=11, labelpad=2)
ax.set_zlabel('z', fontsize=11, labelpad=2)
ax.set_xlim(-18, 18); ax.set_ylim(-18, 18); ax.set_zlim(-15, 15)
ax.view_init(elev=28, azim=-60)
try:
    ax.set_box_aspect([1, 1, 0.70])
except Exception:
    pass

legend_elements = [
    Line2D([0], [0], color='#0b2a8a', linewidth=7,
           label=r'$m_z = -1$ preimage（核心管）'),
    Line2D([0], [0], color='#c21d1d', linewidth=2.3,
           label=r'$m_z = +1$ 均匀背景'),
    Line2D([0], [0], color='#111111', linewidth=1.4,
           label=r'过渡区：$\mathbf{m}$ 沿 poloidal 圆旋转'),
]
ax.legend(handles=legend_elements, loc='upper left', fontsize=9.5,
          framealpha=0.9, bbox_to_anchor=(0.02, 0.98))
ax.set_title(r'$Q_H = 1$ 霍普夫子核心结构', fontsize=13, pad=6)

# ---- inset: in-plane phase colour wheel ----
ax2 = fig.add_axes([0.80, 0.13, 0.14, 0.14], projection='polar')
ax2.set_theta_zero_location('E')
ax2.set_theta_direction(1)
N = 256
t = np.linspace(0, 2*np.pi, N)
r1 = np.ones(N)
ax2.bar(t, r1, width=2*np.pi/N, color=cm.hsv(t/(2*np.pi)),
        edgecolor='none', align='edge')
ax2.set_yticks([])
ax2.set_xticks([0, np.pi/2, np.pi, 3*np.pi/2])
ax2.set_xticklabels([r'$0$', r'$\frac{\pi}{2}$', r'$\pi$', r'$\frac{3\pi}{2}$'], fontsize=7)
ax2.set_title('壳色相:\n$\\arctan(m_y/m_x)$', fontsize=7.5, pad=4)

plt.tight_layout()
out = '/mnt/d/Research/Hopfion/09_paper_thesis_talks/bishe/thesis_v2/figures/fig2-1_hopfion_core_schematic.png'
plt.savefig(out, dpi=190, bbox_inches='tight')
print(f'saved: {out}')
