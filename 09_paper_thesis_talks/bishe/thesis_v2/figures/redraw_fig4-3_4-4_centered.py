#!/usr/bin/env python3
"""redraw_fig4-3_4-4_centered.py

按 结果图示例.png 风格重绘 ch04:
  图 4-3 居中 霍普夫子 z 方向漂移 (fig:centered-z-drift)
  图 4-4 核心体素数 (fig:centered-core-count)
风格: 白底 + 四面黑框 + 中文标签/图例 + 3 个 Ku 配置对比
去除: 原图中的 ±2 nm 阈值线 (用户要求)

数据源: /mnt/d/Research/Hopfion/04_frustrated_fm_foundation/20260105_frustrated_fm/centered_stability_test/
        stability_Ku{0,10k,50k}.out/m*.ovf  (21 帧/组)

CSV 缓存: figures/centered_stability_Ku{0,10k,50k}.csv
输出 (preview):
  figures/PREVIEW_fig4-3_centered_z.png
  figures/PREVIEW_fig4-4_centered_core.png
"""

import os
import glob
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

BLACK, RED, BLUE = 'k', '#B22222', '#003F7F'
BASE = '/mnt/d/Research/Hopfion/04_frustrated_fm_foundation/20260105_frustrated_fm/centered_stability_test'
OUT_DIR = '/mnt/d/Research/Hopfion/09_paper_thesis_talks/bishe/thesis_v2/figures'

CONFIGS = [
    ('Ku=0',   'stability_Ku0.out',   BLACK),
    ('Ku=10k', 'stability_Ku10k.out', RED),
    ('Ku=50k', 'stability_Ku50k.out', BLUE),
]
K_LABEL = {
    'Ku=0':   r'$K_{u1}$ = 0',
    'Ku=10k': r'$K_{u1}$ = 10 kJ/m$^3$',
    'Ku=50k': r'$K_{u1}$ = 50 kJ/m$^3$',
}
DT_NS = 0.05


def extract(cfg_label, dirname):
    csv = os.path.join(OUT_DIR, f"centered_stability_{cfg_label.replace('=','').replace('k','k')}.csv")
    if os.path.exists(csv):
        print(f'[cache] {csv}')
        return pd.read_csv(csv)
    import discretisedfield as df_mod
    out_dir = os.path.join(BASE, dirname)
    ovfs = sorted(glob.glob(os.path.join(out_dir, 'm*.ovf')))
    rows = []
    for i, ov in enumerate(ovfs):
        f = df_mod.Field.from_file(ov)
        mz = f.array[:, :, :, 2]
        weight = np.maximum(1 - mz, 0)
        wsum = weight.sum()
        zcoords = np.linspace(
            f.mesh.region.pmin[2] + f.mesh.cell[2]/2,
            f.mesh.region.pmax[2] - f.mesh.cell[2]/2,
            mz.shape[2]
        )
        z_centroid_nm = (zcoords.reshape(1, 1, -1) * weight).sum() / wsum * 1e9
        core = int((mz < 0).sum())
        rows.append({'t_ns': i * DT_NS, 'z_nm': z_centroid_nm, 'core': core})
        del f
    pd.DataFrame(rows).to_csv(csv, index=False)
    print(f'[write] {csv}')
    return pd.read_csv(csv)


def _frame(ax):
    for s in ax.spines.values():
        s.set_linewidth(1.4); s.set_color('k'); s.set_visible(True)
    ax.set_facecolor('white')
    ax.tick_params(which='major', length=5.5, width=1.1, labelsize=10.5)
    ax.tick_params(which='minor', length=3.0, width=0.8)
    ax.grid(False)


data = {lab: extract(lab, dn) for lab, dn, _ in CONFIGS}

# ---------- 图 4-3: z 方向漂移 ----------
# 规则: |y| 范围在 [0.1, 1] -> 乘 10, 单位标 x10^-1
Z_SCALE = 10.0  # dz_nm * 10 -> 单位 x10^-1 nm, 数值约 -8.5 ~ 8.5
fig, ax = plt.subplots(figsize=(8.5, 5.0))
markers = {'Ku=0': 'o', 'Ku=10k': 's', 'Ku=50k': '^'}
faces = {'Ku=0': 'white', 'Ku=10k': RED, 'Ku=50k': BLUE}
for lab, _, color in CONFIGS:
    d = data[lab]
    dz = (d['z_nm'].to_numpy() - d['z_nm'].iloc[0]) * Z_SCALE
    ax.plot(d['t_ns'], dz, linestyle='-', color=color, linewidth=1.0, alpha=0.6, zorder=2)
    ax.plot(d['t_ns'], dz, linestyle='none', marker=markers[lab],
            markerfacecolor=faces[lab], markeredgecolor=color,
            markeredgewidth=1.1, markersize=6.5,
            label=K_LABEL[lab],
            zorder=3)
ax.axhline(0, color='0.55', linewidth=0.8, alpha=0.6, zorder=1)
ax.set_xlabel('时间 $t$ (ns)', fontsize=12)
ax.set_ylabel(r'位移 $\Delta z$ ($\times 10^{-1}$ nm)', fontsize=12)
ax.set_xlim(0, 1.02)
_frame(ax)
ax.legend(loc='upper left', fontsize=10, frameon=True,
          framealpha=0.95, edgecolor='k', fancybox=False)
plt.tight_layout()
OUT1 = os.path.join(OUT_DIR, 'PREVIEW_fig4-3_centered_z.png')
plt.savefig(OUT1, bbox_inches='tight', dpi=300)
print(f'[OK] saved preview -> {OUT1}')
plt.close(fig)

# ---------- 图 4-4: 核心体素数 ----------
fig, ax = plt.subplots(figsize=(8.5, 5.0))
for lab, _, color in CONFIGS:
    d = data[lab]
    core_s = d['core'] / 100.0
    ax.plot(d['t_ns'], core_s, linestyle='-', color=color, linewidth=1.0, alpha=0.6, zorder=2)
    ax.plot(d['t_ns'], core_s, linestyle='none', marker=markers[lab],
            markerfacecolor=faces[lab], markeredgecolor=color,
            markeredgewidth=1.1, markersize=6.5,
            label=K_LABEL[lab],
            zorder=3)
ax.set_xlabel('时间 $t$ (ns)', fontsize=12)
ax.set_ylabel(r'核心体素数 $N_c$（$m_z < 0$，$\times 10^2$）', fontsize=12)
ax.set_xlim(0, 1.02)
ax.set_yscale('log')
ax.set_ylim(3, 60)
_frame(ax)
ax.legend(loc='upper right', fontsize=10, frameon=True,
          framealpha=0.95, edgecolor='k', fancybox=False)
plt.tight_layout()
OUT2 = os.path.join(OUT_DIR, 'PREVIEW_fig4-4_centered_core.png')
plt.savefig(OUT2, bbox_inches='tight', dpi=300)
print(f'[OK] saved preview -> {OUT2}')
