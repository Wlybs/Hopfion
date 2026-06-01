#!/usr/bin/env python3
"""redraw_fig3-4_drift_trajectory_10ns.py

按 结果图示例.png 风格重绘 fig3-4: 10ns 漂移轨迹 (x/y/z 三方向)。
m_x=+1 背景, 10ns, 来自 bg_mx_axis_x_stable/run.out (201 OVFs)。
钉扎区标注: x 方向 +4.75 nm。

数据源:
  OVFs: /mnt/d/Research/Hopfion/20260105_frustrated_fm/drift_experiments/
        bg_mx_axis_x_stable/run.out/m*.ovf
  缓存 CSV: figures/drift10ns_centroid_bg_mx_axis_x.csv (首次运行自动生成)

输出:     /mnt/d/Research/Hopfion/bishe/thesis_v2/figures/fig3-4_drift_trajectory_10ns.png

依赖: source /mnt/d/Research/Hopfion/hopfion/bin/activate
"""

import os
import sys
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
    'font.family': ['sans-serif'],
    'mathtext.fontset': 'stix',
    'axes.linewidth': 1.2,
    'xtick.direction': 'in', 'ytick.direction': 'in',
    'xtick.top': True, 'ytick.right': True,
    'xtick.minor.visible': True, 'ytick.minor.visible': True,
    'figure.dpi': 100, 'savefig.dpi': 300,
})

BLACK, RED, BLUE = 'k', '#B22222', '#003F7F'
RUN_DIR = '/mnt/d/Research/Hopfion/20260105_frustrated_fm/drift_experiments/bg_mx_axis_x_stable/run.out'
CACHE_CSV = '/mnt/d/Research/Hopfion/bishe/thesis_v2/figures/drift10ns_centroid_bg_mx_axis_x.csv'
OUT = '/mnt/d/Research/Hopfion/bishe/thesis_v2/figures/fig3-4_drift_trajectory_10ns.png'
DT_NS = 0.05

PINNING_X_NM = 4.75  # 已知钉扎位移


# ---------------- 数据加载 (含缓存) ----------------
def extract_centroids():
    """从 OVF 提取 201 帧质心, 保存 CSV 并返回 DataFrame。"""
    try:
        import discretisedfield as df_mod
    except ImportError:
        print('[ERR] 未找到 discretisedfield。请先 activate venv:')
        print('      source /mnt/d/Research/Hopfion/hopfion/bin/activate')
        sys.exit(1)

    ovfs = sorted(glob.glob(os.path.join(RUN_DIR, 'm*.ovf')))
    print(f'[INFO] {len(ovfs)} OVFs @ {RUN_DIR}')
    rows = []
    for i, path in enumerate(ovfs):
        try:
            field = df_mod.Field.from_file(path)
        except Exception as e:
            print(f'[WARN] skip {os.path.basename(path)}: {e}')
            continue
        m = field.array
        Nx, Ny, Nz = m.shape[:3]
        bg = m[Nx // 2, Ny // 2, Nz - 1, :]
        bg_norm = bg / (np.linalg.norm(bg) + 1e-12)
        dotp = np.einsum('ijkd,d->ijk', m, bg_norm)
        w = np.clip(1.0 - dotp, 0.0, None)
        tot = w.sum()
        if tot < 1e-12:
            cx = cy = cz = 0.0
        else:
            mesh = field.mesh
            xs = np.linspace(mesh.region.pmin[0] + mesh.cell[0] / 2,
                             mesh.region.pmax[0] - mesh.cell[0] / 2, Nx) * 1e9
            ys = np.linspace(mesh.region.pmin[1] + mesh.cell[1] / 2,
                             mesh.region.pmax[1] - mesh.cell[1] / 2, Ny) * 1e9
            zs = np.linspace(mesh.region.pmin[2] + mesh.cell[2] / 2,
                             mesh.region.pmax[2] - mesh.cell[2] / 2, Nz) * 1e9
            cx = float((w.sum(axis=(1, 2)) * xs).sum() / tot)
            cy = float((w.sum(axis=(0, 2)) * ys).sum() / tot)
            cz = float((w.sum(axis=(0, 1)) * zs).sum() / tot)
        rows.append({'t_ns': i * DT_NS, 'x_nm': cx, 'y_nm': cy, 'z_nm': cz})
        if i % 20 == 0:
            print(f'  [{i:3d}/{len(ovfs)}] t={i*DT_NS:5.2f}ns')
    dd = pd.DataFrame(rows)
    dd['dx_nm'] = dd['x_nm'] - dd['x_nm'].iloc[0]
    dd['dy_nm'] = dd['y_nm'] - dd['y_nm'].iloc[0]
    dd['dz_nm'] = dd['z_nm'] - dd['z_nm'].iloc[0]
    dd.to_csv(CACHE_CSV, index=False)
    print(f'[OK] cached -> {CACHE_CSV}')
    return dd


if os.path.exists(CACHE_CSV):
    print(f'[INFO] 使用已有缓存 {CACHE_CSV}')
    data = pd.read_csv(CACHE_CSV)
else:
    print('[INFO] 缓存 CSV 不存在, 从 OVF 提取...')
    data = extract_centroids()

t = data['t_ns'].values
dx = data['dx_nm'].values
dy = data['dy_nm'].values
dz = data['dz_nm'].values

# ---------------- 绘图: 3 子面板 (a)(b)(c) ----------------
fig, axes = plt.subplots(3, 1, figsize=(6.0, 6.0), sharex=True)
ax_x, ax_y, ax_z = axes

# ---- (a) x 方向 ----
ax_x.plot(t, dx, color=BLACK, linewidth=1.2, zorder=2)
ax_x.plot(t[::5], dx[::5], marker='o', linestyle='none', color=BLACK,
          markerfacecolor='white', markeredgewidth=1.0, markersize=6, zorder=3)
ax_x.axhline(0, color='k', linewidth=0.8, alpha=0.5)
ax_x.set_ylabel(r'$\Delta x$  (nm)', fontsize=15)
ax_x.set_xlim(0, 10)
ax_x.set_ylim(-1.5, 6.0)
ax_x.tick_params(axis='both', which='major', labelsize=13, length=5)
ax_x.set_title(r'(a) $x$ 方向', fontsize=14, fontweight='bold', loc='center', pad=4)

# ---- (b) y 方向 ----
ax_y.axhline(0, color='k', linewidth=0.8, alpha=0.5)
ax_y.plot(t, dy, color=RED, linewidth=1.2, zorder=2)
ax_y.plot(t[::5], dy[::5], marker='s', linestyle='none', color=RED,
          markerfacecolor=RED, markeredgecolor=RED, markeredgewidth=0.8,
          markersize=5, zorder=3)
dy_range = max(0.5, max(abs(dy.min()), abs(dy.max())) * 1.3)
ax_y.set_ylim(-dy_range, dy_range)
ax_y.set_ylabel(r'$\Delta y$  (nm)', fontsize=15)
ax_y.set_xlim(0, 10)
ax_y.tick_params(axis='both', which='major', labelsize=13, length=5)
ax_y.set_title(r'(b) $y$ 方向', fontsize=14, fontweight='bold', loc='center', pad=4)

# ---- (c) z 方向 ----
ax_z.axhline(0, color='k', linewidth=0.8, alpha=0.5)
ax_z.plot(t, dz, color=BLUE, linewidth=1.2, zorder=2)
ax_z.plot(t[::5], dz[::5], marker='^', linestyle='none', color=BLUE,
          markerfacecolor=BLUE, markeredgecolor=BLUE, markeredgewidth=0.8,
          markersize=6, zorder=3)
dz_range = max(0.5, max(abs(dz.min()), abs(dz.max())) * 1.3)
ax_z.set_ylim(-dz_range, dz_range)
ax_z.set_xlabel(r'时间  $t$  (ns)', fontsize=15)
ax_z.set_ylabel(r'$\Delta z$  (nm)', fontsize=15)
ax_z.set_xlim(0, 10)
ax_z.tick_params(axis='both', which='major', labelsize=13, length=5)
ax_z.set_title(r'(c) $z$ 方向', fontsize=14, fontweight='bold', loc='center', pad=4)

plt.tight_layout()
plt.savefig(OUT, bbox_inches='tight', dpi=300, facecolor='white')
print(f'[OK] saved {OUT}')
