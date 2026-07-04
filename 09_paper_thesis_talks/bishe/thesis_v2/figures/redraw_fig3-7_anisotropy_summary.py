#!/usr/bin/env python3
"""redraw_fig3-7_anisotropy_summary.py

按 结果图示例.png 风格重绘 fig3-7: R/r 对 Ku1 的依赖, 标出临界区 (52k,55k)。
数据源: /mnt/d/Research/Hopfion/04_frustrated_fm_foundation/20260105_frustrated_fm/anisotropy_study/
        ku_critical_sweep/results/survival_table.txt
输出:    /mnt/d/Research/Hopfion/09_paper_thesis_talks/bishe/thesis_v2/figures/fig3-7_anisotropy_summary.png
"""

import numpy as np
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


def _frame(ax):
    for s in ax.spines.values():
        s.set_linewidth(1.4); s.set_color('k'); s.set_visible(True)
    ax.set_facecolor('white')
    ax.tick_params(which='major', length=5.5, width=1.1, labelsize=13)
    ax.tick_params(which='minor', length=3.0, width=0.8)
    ax.grid(False)

BLACK, RED, BLUE = 'k', '#B22222', '#003F7F'
OUT = '/mnt/d/Research/Hopfion/09_paper_thesis_talks/bishe/thesis_v2/figures/fig3-7_anisotropy_summary.png'

# ---------- 数据 (来自 survival_table.txt @ t=1ns) ----------
Ku_alive = np.array([0, 5000, 10000, 20000, 30000, 40000, 50000, 52000]) / 1000.0
R_alive = np.array([2.63, 2.35, 2.17, 1.82, 1.82, 1.69, 1.56, 1.46])
r_alive = np.array([2.22, 1.85, 1.64, 1.54, 1.38, 1.30, 1.24, 1.27])

Ku_dead = np.array([55000, 56000, 57000, 58000]) / 1000.0

Ku_c_lo, Ku_c_hi = 52.0, 55.0

# ---------- 布局: 双面板 (a) R vs Ku, (b) r vs Ku ----------
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9.0, 10.0))

# --- (a) R vs Ku ---
ax1.axvspan(Ku_c_lo, Ku_c_hi, color=RED, alpha=0.18, zorder=0,
            label=fr'临界区 $K_{{u,c}} \in$ ({Ku_c_lo:.0f}, {Ku_c_hi:.0f}) kJ/m$^3$')

ax1.plot(Ku_alive, R_alive,
         marker='o', linestyle='none', color=BLACK,
         markerfacecolor='white', markeredgewidth=1.4,
         markersize=9, label='$R$ (大半径)', zorder=4)

# 虚线趋势
from numpy.polynomial import polynomial as P
coef_R = np.polyfit(Ku_alive, R_alive, 2)
Ku_dense = np.linspace(0, 52, 200)
R_smooth = np.polyval(coef_R, Ku_dense)
ax1.plot(Ku_dense, R_smooth, linestyle='--', color=BLACK, linewidth=1.0, alpha=0.8)

# 坍塌点 × 灰色
ax1.plot(Ku_dead, np.full_like(Ku_dead, 0.2),
         marker='x', color='#666', markersize=11, markeredgewidth=2,
         linestyle='none', label='坍塌 (core = 0)', zorder=4)

ax1.set_ylabel(r'大半径  $R$  (nm)', fontsize=15)
ax1.set_xlim(-2, 60)
ax1.set_ylim(0, 3.0)
_frame(ax1)
ax1.legend(loc='upper right', ncol=2,
           fontsize=13, frameon=False,
           handlelength=1.8, columnspacing=1.8, handletextpad=0.5)
ax1.set_title(r'(a) 大半径 $R$', fontsize=14, fontweight='bold', loc='center', pad=4)

# --- (b) r vs Ku ---
ax2.axvspan(Ku_c_lo, Ku_c_hi, color=RED, alpha=0.18, zorder=0,
            label=f'临界区')

ax2.plot(Ku_alive, r_alive,
         marker='s', linestyle='none', color=RED,
         markerfacecolor=RED, markeredgewidth=1.2,
         markersize=8, label='$r$ (管半径)', zorder=4)

coef_r = np.polyfit(Ku_alive, r_alive, 2)
r_smooth = np.polyval(coef_r, Ku_dense)
ax2.plot(Ku_dense, r_smooth, linestyle='--', color=RED, linewidth=1.0, alpha=0.8)

ax2.plot(Ku_dead, np.full_like(Ku_dead, 0.2),
         marker='x', color='#666', markersize=11, markeredgewidth=2,
         linestyle='none', label='坍塌 (core = 0)', zorder=4)

ax2.set_xlabel(r'$K_{u,1}$  (kJ/m$^3$)', fontsize=15)
ax2.set_ylabel(r'管半径  $r$  (nm)', fontsize=15)
ax2.set_xlim(-2, 60)
ax2.set_ylim(0, 2.6)
_frame(ax2)
ax2.legend(loc='upper right', ncol=2,
           fontsize=13, frameon=False,
           handlelength=1.8, columnspacing=1.8, handletextpad=0.5)
ax2.set_title(r'(b) 管半径 $r$', fontsize=14, fontweight='bold', loc='center', pad=4)

plt.tight_layout()
plt.savefig(OUT, bbox_inches='tight', dpi=300)
print(f'[OK] saved {OUT}')
