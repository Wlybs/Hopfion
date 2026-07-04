#!/usr/bin/env python3
"""redraw_fig5-7_multisource_baseline.py

按规则重绘 图5-7: 3 种单源基线（srcX / srcZ(+z) / srcZ(-z) @ 200 GHz, vibX）
的 霍普夫子 质心轨迹对比, 3 行 x 1 列纵向堆叠
  (a) Δx(t)   (b) Δy(t)   (c) Δz(t)

数据源:
  srcX(+x):  freq_sweep/02ns/sw_f200GHz.out
  srcZ(+z):  freq_sweep/plane_wave/srcZ/sw_srcZ_f200GHz.out
  srcZ(-z):  multisource_control/baseline/sw_srcZ_neg_f200GHz.out

缓存 CSV: figures/fig5-7_baseline_cache.csv
输出:     figures/fig4-10_multisource_baseline.png
依赖: source /mnt/d/Research/Hopfion/hopfion/bin/activate
"""
import os, sys
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
    'font.family': ['sans-serif'],
    'mathtext.fontset': 'stix',
    'axes.linewidth': 1.2,
    'xtick.direction': 'in', 'ytick.direction': 'in',
    'xtick.top': True, 'ytick.right': True,
    'xtick.minor.visible': True, 'ytick.minor.visible': True,
    'figure.dpi': 100, 'savefig.dpi': 300,
})

BASE = "/mnt/d/Research/Hopfion/04_frustrated_fm_foundation/20260105_frustrated_fm/spin_wave_dynamics"
CONFIGS = [
    ('srcX (+x)', os.path.join(BASE, "freq_sweep/plane_wave/srcX/02ns/sw_f200GHz.out"),        '#1f77b4'),
    ('srcZ (+z)', os.path.join(BASE, "freq_sweep/plane_wave/srcZ/sw_srcZ_f200GHz.out"),        '#ff7f0e'),
    ('srcZ (-z)', os.path.join(BASE, "multisource_control/baseline/sw_srcZ_neg_f200GHz.out"),  '#2ca02c'),
]
DT_NS = 0.01
CACHE = "/mnt/d/Research/Hopfion/09_paper_thesis_talks/bishe/thesis_v2/figures/fig5-7_baseline_cache.csv"
OUT   = "/mnt/d/Research/Hopfion/09_paper_thesis_talks/bishe/thesis_v2/figures/fig4-10_multisource_baseline.png"


def extract_all():
    sys.path.insert(0, "/mnt/d/Research/Hopfion/95_shared_scripts")
    from hopfion_analysis import extract_trajectory_phase_correlation
    rows = []
    for name, out_dir, _ in CONFIGS:
        if not os.path.isdir(out_dir):
            print(f"[SKIP] {name}: {out_dir}")
            continue
        print(f"  {name} extracting...", flush=True)
        traj = extract_trajectory_phase_correlation(out_dir, DT_NS, verbose=False)
        for t, shift, _core in traj:
            if shift is None or np.any(np.isnan(shift)):
                continue
            rows.append({'name': name, 't_ns': t,
                         'dx': shift[0], 'dy': shift[1], 'dz': shift[2]})
    df = pd.DataFrame(rows)
    df.to_csv(CACHE, index=False)
    print(f"[OK] cached -> {CACHE}")
    return df


if os.path.exists(CACHE):
    print(f"[INFO] 使用缓存 {CACHE}")
    data = pd.read_csv(CACHE)
else:
    print("[INFO] 无缓存, 从 OVF 提取...")
    data = extract_all()

# ---------------- 绘图: 3 行 x 1 列 ----------------
fig, (ax_x, ax_y, ax_z) = plt.subplots(3, 1, figsize=(6.5, 7.5), sharex=True)

T_MAX_NS = 0.20  # 三源统一截断到 0.2 ns, 保证视觉公平对比
for name, _, color in CONFIGS:
    sub = data[(data['name'] == name) & (data['t_ns'] <= T_MAX_NS)].sort_values('t_ns')
    if sub.empty:
        continue
    ax_x.plot(sub['t_ns'], sub['dx'], '-', color=color, linewidth=1.4, label=name)
    ax_y.plot(sub['t_ns'], sub['dy'], '-', color=color, linewidth=1.4)
    ax_z.plot(sub['t_ns'], sub['dz'], '-', color=color, linewidth=1.4)

for ax in (ax_x, ax_y, ax_z):
    ax.axhline(0, color='k', linewidth=0.6, alpha=0.5)
    ax.tick_params(axis='both', which='major', labelsize=13, length=4.5)

ax_x.set_ylabel(r'$\Delta x$  (nm)', fontsize=15)
ax_y.set_ylabel(r'$\Delta y$  (nm)', fontsize=15)
ax_z.set_ylabel(r'$\Delta z$  (nm)', fontsize=15)
ax_z.set_xlabel(r'时间  $t$  (ns)', fontsize=15)

for ax, tag in ((ax_x, r'(a) $\Delta x(t)$'), (ax_y, r'(b) $\Delta y(t)$'), (ax_z, r'(c) $\Delta z(t)$')):
    ax.text(0.02, 0.92, tag, transform=ax.transAxes,
            fontsize=14, fontweight='bold',
            ha='left', va='top',
            bbox=dict(boxstyle='round,pad=0.2', fc='white', ec='none', alpha=0.7))

handles, labels = ax_x.get_legend_handles_labels()
fig.legend(handles, labels, loc='upper center', fontsize=13,
           frameon=False, ncol=3,
           bbox_to_anchor=(0.5, 0.995),
           handlelength=1.8, columnspacing=1.6, handletextpad=0.5)

plt.tight_layout(rect=[0, 0, 1, 0.95])
plt.savefig(OUT, bbox_inches='tight', dpi=300)
print(f'[OK] saved {OUT}')
