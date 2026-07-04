#!/usr/bin/env python3
# Hopf-link illustration of Q_H = 1 preimage structure
# Uses manual front/back segment split to produce real over/under occlusion
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from matplotlib import font_manager as _fm
for _fp in ('/mnt/c/Windows/Fonts/simhei.ttf', '/mnt/c/Windows/Fonts/msyh.ttc'):
    try: _fm.fontManager.addfont(_fp)
    except Exception: pass
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Noto Sans CJK SC', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

def torus_segment(center, plane, R, tube, theta_range, n_th=160, n_u=22):
    """Generate surface mesh of a tube along an arc in specified plane."""
    cx, cy, cz = center
    t = np.linspace(theta_range[0], theta_range[1], n_th)
    u = np.linspace(0, 2*np.pi, n_u)
    T, U = np.meshgrid(t, u)
    if plane == 'xy':
        X = cx + (R + tube*np.cos(U)) * np.cos(T)
        Y = cy + (R + tube*np.cos(U)) * np.sin(T)
        Z = cz + tube * np.sin(U)
    elif plane == 'xz':
        X = cx + (R + tube*np.cos(U)) * np.cos(T)
        Y = cy + tube * np.sin(U)
        Z = cz + (R + tube*np.cos(U)) * np.sin(T)
    return X, Y, Z

fig = plt.figure(figsize=(4.8, 4.4))
ax = fig.add_subplot(111, projection='3d')

R_a, R_b = 3.0, 2.3
tube = 0.22

# We want: blue ring in xy-plane (center origin, R_a), red ring in xz-plane (center (R_a,0,0), R_b).
# They link once. Red ring passes through the disk of blue ring at (R_a - R_b, 0, 0).
# For proper over/under: in the chosen view (azim=28, elev=22) camera is roughly at +x,-y,+z direction.
# Sort by approximate "depth" toward camera -> draw back first, then alternating.

# Draw order (from far to near):
# 1. Back half of RED (away from camera, roughly cos(azim) * x + sin(azim) * y < 0 in world)
# 2. BLUE whole ring
# 3. Front half of RED (wraps over the blue ring on the near side)

# Red ring is in xz-plane centred at (R_a, 0, 0). Its world x = R_a + R_b cos(t).
# "Back" piece: t in [pi/2, 3*pi/2] -> x = R_a + R_b*cos(t) <= R_a (closer to blue ring's plane near interior)
# but camera in +x direction => larger x is closer. So back = smaller x = cos(t) < 0 => t in (pi/2, 3pi/2)

# Actually simpler: we want the red ring's left arc (x<R_a, through blue ring's interior) to appear BEHIND blue ring segment,
# and right arc (x>R_a, outside blue ring) to appear IN FRONT of blue ring outer rim.
# Since we view from +x,+z direction, outer parts of blue ring (x>0 side) appear close.
# Let's split:
#   RED back arc: t in [pi/2, 3pi/2]  (the x<R_a side)
#   BLUE ring whole
#   RED front arc: t in [-pi/2, pi/2] (the x>R_a side — in front of blue)

# 1. back half of RED
Xrb, Yrb, Zrb = torus_segment((R_a, 0, 0), 'xz', R_b, tube, (np.pi/2, 3*np.pi/2))
ax.plot_surface(Xrb, Yrb, Zrb, color='#c21d1d', alpha=1.0,
                linewidth=0, antialiased=True, shade=True)

# 2. blue full ring
Xb, Yb, Zb = torus_segment((0, 0, 0), 'xy', R_a, tube, (0, 2*np.pi))
ax.plot_surface(Xb, Yb, Zb, color='#0b2a8a', alpha=1.0,
                linewidth=0, antialiased=True, shade=True)

# 3. front half of RED
Xrf, Yrf, Zrf = torus_segment((R_a, 0, 0), 'xz', R_b, tube, (-np.pi/2, np.pi/2))
ax.plot_surface(Xrf, Yrf, Zrf, color='#c21d1d', alpha=1.0,
                linewidth=0, antialiased=True, shade=True)

ax.set_xlim(-4.5, 6.5); ax.set_ylim(-4.5, 4.5); ax.set_zlim(-3.0, 3.0)
ax.view_init(elev=22, azim=28)
try:
    ax.set_box_aspect([1.1, 1.0, 0.60])
except Exception:
    pass
ax.set_axis_off()

legend_elements = [
    Line2D([0], [0], color='#0b2a8a', linewidth=5, label=r'$m_z = -1$'),
    Line2D([0], [0], color='#c21d1d', linewidth=5, label=r'$m_\perp$ (如 $m_x = 1$)'),
]
ax.legend(handles=legend_elements, loc='lower center', fontsize=8.5,
          framealpha=0.92, ncol=2, bbox_to_anchor=(0.5, -0.02))

plt.subplots_adjust(left=0, right=1, top=1, bottom=0.08)
out = '/mnt/d/Research/Hopfion/09_paper_thesis_talks/bishe/thesis_v2/figures/fig2-1c_preimage_linking.png'
plt.savefig(out, dpi=200, bbox_inches='tight')
print(f'saved: {out}')
