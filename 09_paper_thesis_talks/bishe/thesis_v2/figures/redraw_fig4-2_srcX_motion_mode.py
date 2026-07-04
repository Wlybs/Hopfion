#!/usr/bin/env python3
"""redraw_fig4-2_srcX_motion_mode.py

按 结果图示例.png 风格重绘 fig4-2: srcX 驱动 10 频率点运动模式。
3 子面板: (a)末态位移 |Δr|  (b)平均速度 v̄  (c)平均加速度 ā
风格: 白底 + 四面黑框 + 中文标签/图例 + 数据点按运动模式分色
数据源: /mnt/d/Research/Hopfion/04_frustrated_fm_foundation/20260105_frustrated_fm/spin_wave_dynamics/
        freq_sweep/plane_wave/srcX/results/motion_mode_summary.txt

输出 (preview):  /mnt/d/Research/Hopfion/09_paper_thesis_talks/bishe/thesis_v2/figures/PREVIEW_fig4-2.png
审核通过后: 由主脚本切成 _a/_b/_c 三张子 png 覆盖原图
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

BLACK, RED, BLUE, GRAY = 'k', '#B22222', '#003F7F', '0.55'

freq = np.array([100, 200, 300, 400, 500, 600, 700, 800, 900, 1000])
dr   = np.array([1.938, 2.508, 0.902, 0.084, 0.151, 0.077, 0.445, 0.531, 0.408, 5.500])
vbar = np.array([15.66, 18.53, 6.39, 1.53, 1.86, 1.83, 4.67, 4.13, 3.28, 41.05])
abar = np.array([506.44, 321.27, 447.98, 110.80, 130.24, 148.79, 287.28, 276.71, 252.15, 1180.34])
mode_is_static = np.array([False, False, False, True, False, True, False, False, False, False])

eff_mask = dr >= 1.0
death_mask = (freq >= 400) & (freq <= 600)

fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.0))

def _frame(ax):
    for s in ax.spines.values():
        s.set_linewidth(1.4); s.set_color('k'); s.set_visible(True)
    ax.set_facecolor('white')
    ax.tick_params(which='major', length=5.5, width=1.1, labelsize=10.5)
    ax.tick_params(which='minor', length=3.0, width=0.8)
    ax.grid(False)

def _plot_panel(ax, y, ylab, ylim=None, unit=None, peak_label=True):
    ax.axvspan(400, 600, color='#F5F5F5', alpha=0.9, zorder=0)
    ax.text(500, ax.get_ylim()[1]*0.95 if ylim else y.max()*1.05,
            '死区', color=GRAY, ha='center', va='top', fontsize=10)

    ax.plot(freq[~eff_mask], y[~eff_mask], 'o', markerfacecolor='white',
            markeredgecolor=BLACK, markeredgewidth=1.4, markersize=9,
            label='弱响应 ($|\\Delta r| < 1$ nm)', zorder=3)
    ax.plot(freq[eff_mask & ~mode_is_static], y[eff_mask & ~mode_is_static],
            's', markerfacecolor=RED, markeredgecolor=RED,
            markersize=8.5, label='有效驱动 ($|\\Delta r| \\geq 1$ nm)', zorder=4)

    ax.plot(freq, y, '--', color=GRAY, linewidth=0.9, alpha=0.6, zorder=2)

    if peak_label:
        imax = int(np.argmax(y))
        ax.annotate(f'峰值 {freq[imax]} GHz\n{y[imax]:.1f}'+(unit or ''),
                    xy=(freq[imax], y[imax]), xytext=(freq[imax]-320, y[imax]*0.7),
                    color=RED, fontsize=10, ha='center',
                    arrowprops=dict(arrowstyle='->', color=RED, lw=1.0))

    ax.set_xlabel('频率 $f$ (GHz)', fontsize=12)
    ax.set_ylabel(ylab, fontsize=12)
    ax.set_xlim(50, 1050)
    ax.set_xticks(np.arange(100, 1001, 200))
    if ylim: ax.set_ylim(*ylim)
    _frame(ax)

_plot_panel(axes[0], dr,   '末态位移 $|\\Delta r|$  (nm)',     ylim=(-0.3, 6.5),  unit=' nm')
_plot_panel(axes[1], vbar, '平均速度 $\\bar v$  (nm/ns)',      ylim=(-2, 48),     unit=' nm/ns')
_plot_panel(axes[2], abar, '平均加速度 $\\bar a$  (nm/ns$^2$)', ylim=(-50, 1350), unit=' nm/ns$^2$')

for i, (ax, lab) in enumerate(zip(axes, ['(a)', '(b)', '(c)'])):
    ax.text(0.03, 0.97, lab, transform=ax.transAxes,
            fontsize=13, va='top', ha='left')

axes[0].legend(loc='upper left', bbox_to_anchor=(0.02, 0.88),
               fontsize=9, frameon=True, framealpha=0.95,
               edgecolor='k', fancybox=False)

plt.tight_layout()
OUT = '/mnt/d/Research/Hopfion/09_paper_thesis_talks/bishe/thesis_v2/figures/PREVIEW_fig4-2.png'
plt.savefig(OUT, bbox_inches='tight', dpi=300)
print(f'[OK] saved preview -> {OUT}')
