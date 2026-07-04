#!/usr/bin/env python3
"""redraw_fig4-2_drift_10ns.py

按 结果图示例.png 风格重绘 ch04 图 4-2: m_x=+1 背景 10 ns 质心轨迹 (x/y/z 三方向)。
风格: 白底 + 四面黑框 + 中文标签/图例 + 前 1ns 弛豫 inset + 4.75 nm 钉扎标注

数据缓存: /mnt/d/Research/Hopfion/09_paper_thesis_talks/bishe/thesis_v2/figures/drift10ns_centroid_bg_mx_axis_x.csv
输出 (preview): /mnt/d/Research/Hopfion/09_paper_thesis_talks/bishe/thesis_v2/figures/PREVIEW_fig4-2_drift.png
审核通过后切分为 _a/_b/_c 覆盖 fig3-4_drift_trajectory_10ns_{a,b,c}.png
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as _fm
for _fp in ('/mnt/c/Windows/Fonts/simhei.ttf', '/mnt/c/Windows/Fonts/msyh.ttc'):
    try: _fm.fontManager.addfont(_fp)
    except Exception: pass

plt.rcParams.update({
    'font.sans-serif': ['SimHei', 'Microsoft YaHei', 'Noto Sans CJK SC', 'DejaVu Sans'],
    'axes.unicode_minus': False,
    'font.family': 'sans-serif',
    'mathtext.fontset': 'stix',
    'axes.linewidth': 1.4,
    'xtick.direction': 'in', 'ytick.direction': 'in',
    'xtick.top': True, 'ytick.right': True,
    'xtick.minor.visible': True, 'ytick.minor.visible': True,
    'figure.dpi': 100, 'savefig.dpi': 300,
})

BLACK, RED, BLUE, GRAY = 'k', '#B22222', '#003F7F', '0.55'
PINNING = 4.75
CSV = '/mnt/d/Research/Hopfion/09_paper_thesis_talks/bishe/thesis_v2/figures/drift10ns_centroid_bg_mx_axis_x.csv'
OUT = '/mnt/d/Research/Hopfion/09_paper_thesis_talks/bishe/thesis_v2/figures/fig3-4_drift_trajectory_10ns.png'

df = pd.read_csv(CSV)
t  = df['t_ns'].to_numpy()
dx = df['dx_nm'].to_numpy()
dy = df['dy_nm'].to_numpy()
dz = df['dz_nm'].to_numpy()

fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.0))
ax_x, ax_y, ax_z = axes

def _frame(ax):
    for s in ax.spines.values():
        s.set_linewidth(1.4); s.set_color('k'); s.set_visible(True)
    ax.set_facecolor('white')
    ax.tick_params(which='major', length=5.5, width=1.1, labelsize=10.5)
    ax.tick_params(which='minor', length=3.0, width=0.8)
    ax.grid(False)

# ----- (a) x 方向（含 inset） -----
ax_x.plot(t, dx, color=BLACK, linewidth=1.1, zorder=2)
ax_x.plot(t[::4], dx[::4], marker='o', linestyle='none', color=BLACK,
          markerfacecolor='white', markeredgewidth=1.1, markersize=5.5, zorder=3)
ax_x.set_xlabel('时间 $t$ (ns)', fontsize=12)
ax_x.set_ylabel(r'位移 $\Delta x$ (nm)', fontsize=12)
ax_x.set_xlim(0, 10); ax_x.set_ylim(-1.3, 6.3)
ax_x.text(0.03, 0.97, '(a) $x$ 方向（轴向）', transform=ax_x.transAxes,
          fontsize=12, va='top')
_frame(ax_x)

# inset: 前 1 ns 弛豫放大
axins = ax_x.inset_axes([0.52, 0.12, 0.44, 0.35])
mask = t <= 1.2
axins.plot(t[mask], dx[mask], color=BLACK, linewidth=1.0)
axins.plot(t[mask], dx[mask], marker='o', linestyle='none',
           color=BLACK, markerfacecolor='white', markeredgewidth=0.9, markersize=4)
axins.set_xlabel('$t$ (ns)', fontsize=8.5)
axins.set_ylabel(r'位移 $\Delta x$ (nm)', fontsize=8.5)
axins.tick_params(labelsize=7.5, direction='in')
axins.set_title('前 1 ns 弛豫', fontsize=8.5, pad=2)
for s in axins.spines.values(): s.set_linewidth(0.9); s.set_color('k')

# ----- (b) y 方向 -----
ax_y.axhline(0, color=GRAY, linewidth=0.8, alpha=0.6)
ax_y.plot(t, dy, color=RED, linewidth=1.1, zorder=2)
ax_y.plot(t[::4], dy[::4], marker='s', linestyle='none', color=RED,
          markerfacecolor=RED, markersize=5, zorder=3)
ax_y.set_xlabel('时间 $t$ (ns)', fontsize=12)
ax_y.set_ylabel(r'位移 $\Delta y$ (nm)', fontsize=12)
ax_y.set_xlim(0, 10)
yr = max(0.5, max(abs(dy.min()), abs(dy.max())) * 1.4)
ax_y.set_ylim(-yr, yr)
ax_y.text(0.03, 0.97, '(b) $y$ 方向', transform=ax_y.transAxes,
          fontsize=12, va='top')
_frame(ax_y)

# ----- (c) z 方向 -----
ax_z.axhline(0, color=GRAY, linewidth=0.8, alpha=0.6)
ax_z.plot(t, dz, color=BLUE, linewidth=1.1, zorder=2)
ax_z.plot(t[::4], dz[::4], marker='^', linestyle='none', color=BLUE,
          markerfacecolor=BLUE, markersize=5.5, zorder=3)
ax_z.set_xlabel('时间 $t$ (ns)', fontsize=12)
ax_z.set_ylabel(r'位移 $\Delta z$ (nm)', fontsize=12)
ax_z.set_xlim(0, 10)
zr = max(0.5, max(abs(dz.min()), abs(dz.max())) * 1.4)
ax_z.set_ylim(-zr, zr)
ax_z.text(0.03, 0.97, '(c) $z$ 方向', transform=ax_z.transAxes,
          fontsize=12, va='top')
_frame(ax_z)

plt.tight_layout()
plt.savefig(OUT, bbox_inches='tight', dpi=300)
print(f'[OK] saved preview -> {OUT}')
