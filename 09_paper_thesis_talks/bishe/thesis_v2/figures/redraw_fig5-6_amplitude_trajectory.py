#!/usr/bin/env python3
"""redraw_fig5-6_amplitude_trajectory.py

按 图5-2 (fig4-3_srcX_displacement) 风格重绘 图5-6: 自旋波幅度扫描下
霍普夫子 轨迹 4x1 纵向堆叠 (a)|Δr|(t) (b)Δx(t) (c)Δz(t) (d)核心体素数 N_c(t)。

数据源: amplitude_sweep/plane_wave/sw_B{amp}T.out (6 振幅: 0.05, 0.1, 0.2, 0.5, 1.0, 2.0 T)
使用 95_shared_scripts/hopfion_analysis.extract_trajectory_phase_correlation

缓存 CSV: figures/fig5-6_amplitude_cache.csv
输出:     figures/fig4-8_amplitude_trajectory.png
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

AMPS = [('0p05', 0.05), ('0p1', 0.1), ('0p2', 0.2),
        ('0p5', 0.5), ('1p0', 1.0), ('2p0', 2.0)]
DT_NS = 0.01
SRC_BASE = "/mnt/d/Research/Hopfion/04_frustrated_fm_foundation/20260105_frustrated_fm/spin_wave_dynamics/amplitude_sweep/plane_wave"
CACHE = "/mnt/d/Research/Hopfion/09_paper_thesis_talks/bishe/thesis_v2/figures/fig5-6_amplitude_cache.csv"
OUT   = "/mnt/d/Research/Hopfion/09_paper_thesis_talks/bishe/thesis_v2/figures/fig4-8_amplitude_trajectory.png"


def extract_all():
    sys.path.insert(0, "/mnt/d/Research/Hopfion/95_shared_scripts")
    from hopfion_analysis import extract_trajectory_phase_correlation
    rows = []
    for tag, B in AMPS:
        out_dir = os.path.join(SRC_BASE, f"sw_B{tag}T.out")
        if not os.path.isdir(out_dir):
            print(f"[SKIP] {out_dir}")
            continue
        print(f"  B={B}T extracting...", flush=True)
        traj = extract_trajectory_phase_correlation(out_dir, DT_NS, verbose=False)
        for t, shift, core in traj:
            if shift is None or np.any(np.isnan(shift)):
                continue
            rows.append({'B': B, 't_ns': t,
                         'dx': shift[0], 'dy': shift[1], 'dz': shift[2],
                         'core': core})
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

data = data.sort_values(['B', 't_ns']).reset_index(drop=True)
data['dr'] = np.sqrt(data['dx']**2 + data['dy']**2 + data['dz']**2)

# ---------------- 绘图: 2 行 x 1 列 (|Δr|, Δz) ----------------
fig, (ax_r, ax_z) = plt.subplots(2, 1, figsize=(9.0, 8.0), sharex=True)

cmap = plt.get_cmap('viridis')
amps_list = [B for _, B in AMPS]
colors = {B: cmap(i / max(len(amps_list) - 1, 1)) for i, B in enumerate(amps_list)}

for B in amps_list:
    sub = data[data['B'] == B]
    if sub.empty:
        continue
    c = colors[B]
    label = f'$B_0$ = {B:g} T'
    ax_r.plot(sub['t_ns'], sub['dr'], '-', color=c, linewidth=1.4, label=label)
    ax_z.plot(sub['t_ns'], sub['dz'], '-', color=c, linewidth=1.4)

ax_z.axhline(0, color='k', linewidth=0.6, alpha=0.5)

ax_r.set_ylabel(r'总位移 $|\Delta r|$ (nm)', fontsize=15)
ax_z.set_ylabel(r'位移 $\Delta z$ (nm)', fontsize=15)
ax_z.set_xlabel(r'时间 $t$ (ns)', fontsize=15)

_frame(ax_r)
_frame(ax_z)
ax_r.text(1.02, 0.5, '(a)', transform=ax_r.transAxes,
          fontsize=14, va='center', ha='left')
ax_z.text(1.02, 0.5, '(b)', transform=ax_z.transAxes,
          fontsize=14, va='center', ha='left')

handles, labels = ax_r.get_legend_handles_labels()
fig.legend(handles, labels, loc='upper center',
           bbox_to_anchor=(0.5, 0.995), ncol=3,
           fontsize=13, frameon=False,
           handlelength=1.8, columnspacing=1.8, handletextpad=0.5)

plt.tight_layout(rect=[0, 0, 1, 0.92])
plt.savefig(OUT, bbox_inches='tight', dpi=300)
print(f'[OK] saved {OUT}')
