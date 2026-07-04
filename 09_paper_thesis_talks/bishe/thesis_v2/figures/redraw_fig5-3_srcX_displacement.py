#!/usr/bin/env python3
"""redraw_fig5-3_srcX_displacement.py

按 图4-1/4-6 风格重绘 图5-3: srcX 驱动 10 频率点的位移频率响应,
4x1 纵向堆叠 (a)|Δr|(t) (b)Δx(t) (c)Δz(t) (d)|v|(t)。

数据源: freq_sweep/plane_wave/srcX/02ns/sw_f{freq}GHz.out (10 频率)
使用 /mnt/d/Research/Hopfion/95_shared_scripts/hopfion_analysis.extract_trajectory_phase_correlation

缓存 CSV: figures/fig5-3_srcX_cache.csv
输出:     figures/fig4-3_srcX_displacement.png
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

FREQS_GHZ = list(range(100, 1100, 100))
DT_NS = 0.01
SRC_BASE = "/mnt/d/Research/Hopfion/04_frustrated_fm_foundation/20260105_frustrated_fm/spin_wave_dynamics/freq_sweep/plane_wave/srcX/02ns"
CACHE = "/mnt/d/Research/Hopfion/09_paper_thesis_talks/bishe/thesis_v2/figures/fig5-3_srcX_cache.csv"
OUT   = "/mnt/d/Research/Hopfion/09_paper_thesis_talks/bishe/thesis_v2/figures/fig4-3_srcX_displacement.png"


def extract_all():
    sys.path.insert(0, "/mnt/d/Research/Hopfion/95_shared_scripts")
    from hopfion_analysis import extract_trajectory_phase_correlation
    rows = []
    for f in FREQS_GHZ:
        out_dir = os.path.join(SRC_BASE, f"sw_f{f}GHz.out")
        if not os.path.isdir(out_dir):
            print(f"[SKIP] {out_dir}")
            continue
        print(f"  f={f}GHz extracting...", flush=True)
        traj = extract_trajectory_phase_correlation(out_dir, DT_NS, verbose=False)
        for t, shift, core in traj:
            if shift is None or np.any(np.isnan(shift)):
                continue
            rows.append({'freq': f, 't_ns': t,
                         'dx': shift[0], 'dy': shift[1], 'dz': shift[2]})
    df = pd.DataFrame(rows)
    df.to_csv(CACHE, index=False)
    print(f"[OK] cached -> {CACHE}")
    return df


if os.path.exists(CACHE):
    print(f"[INFO] 使用缓存 {CACHE}")
    data = pd.read_csv(CACHE)
else:
    print("[INFO] 无缓存, 从 OVF 提取 (约 2-5 分钟)...")
    data = extract_all()

# compute |dr| and |v|
data = data.sort_values(['freq', 't_ns']).reset_index(drop=True)
data['dr'] = np.sqrt(data['dx']**2 + data['dy']**2 + data['dz']**2)

data['speed'] = 0.0
for f in data['freq'].unique():
    mask = data['freq'] == f
    g = data.loc[mask].sort_values('t_ns')
    ts = g['t_ns'].values
    vx = np.gradient(g['dx'].values, ts)
    vy = np.gradient(g['dy'].values, ts)
    vz = np.gradient(g['dz'].values, ts)
    data.loc[g.index, 'speed'] = np.sqrt(vx**2 + vy**2 + vz**2)

# ---------------- 绘图: 4 行 x 1 列 ----------------
fig, axes = plt.subplots(4, 1, figsize=(6.5, 9.0), sharex=True)
ax_r, ax_x, ax_z, ax_v = axes

cmap = plt.get_cmap('tab10')
colors = {f: cmap(i) for i, f in enumerate(FREQS_GHZ)}

for f in FREQS_GHZ:
    sub = data[data['freq'] == f]
    if sub.empty:
        continue
    c = colors[f]
    ax_r.plot(sub['t_ns'], sub['dr'], '-', color=c, linewidth=1.0, label=f'{f} GHz')
    ax_x.plot(sub['t_ns'], sub['dx'], '-', color=c, linewidth=1.0)
    ax_z.plot(sub['t_ns'], sub['dz'], '-', color=c, linewidth=1.0)
    ax_v.plot(sub['t_ns'], sub['speed'], '-', color=c, linewidth=1.0)

for ax in (ax_x, ax_z):
    ax.axhline(0, color='k', linewidth=0.6, alpha=0.5)

ax_r.set_ylabel(r'$|\Delta r|$  (nm)', fontsize=11)
ax_x.set_ylabel(r'$\Delta x$  (nm)', fontsize=11)
ax_z.set_ylabel(r'$\Delta z$  (nm)', fontsize=11)
ax_v.set_ylabel(r'$|v|$  (nm/ns)', fontsize=11)
ax_v.set_xlabel(r'时间  $t$  (ns)', fontsize=11)

for ax, tag in zip(axes, [r'(a) $|\Delta r|(t)$', r'(b) $\Delta x(t)$',
                           r'(c) $\Delta z(t)$', r'(d) $|v|(t)$']):
    ax.tick_params(axis='both', which='major', labelsize=10, length=4.5)
    ax.set_title(tag, fontsize=12, fontweight='bold', loc='center', pad=4)

# 统一图例放到所有子图最上方, 2 行水平排列, 字体放大
handles, labels = ax_r.get_legend_handles_labels()
fig.legend(handles, labels, loc='upper center', fontsize=11,
           frameon=False, ncol=5,
           bbox_to_anchor=(0.5, 1.0),
           handlelength=1.8, columnspacing=1.6, handletextpad=0.5)

plt.tight_layout(rect=[0, 0, 1, 0.92])
plt.savefig(OUT, bbox_inches='tight', dpi=300)
print(f'[OK] saved {OUT}')
