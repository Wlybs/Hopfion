#!/usr/bin/env python3
"""redraw_fig4-6_size_convergence.py

按 图4-1 风格重绘 图4-6: 尺寸收敛测试 (a) R(t), (b) r(t)。
三组初始尺寸 (Small R~3, R8r4, R12r5) 的 R/r 时间演化收敛至同一吸引子。

数据源 (OVF):
  Small: anisotropy_study/size_vs_ku/Ku1_0.0e+00_Ms_1.5000e+05.out (dt=100ps)
  R8r4:  size_sweep/R8r4_Ku0.out                                   (dt=50ps)
  R12r5: size_sweep/R12r5_Ku0.out                                  (dt=50ps)

缓存 CSV: figures/size_convergence_cache.csv (首次运行自动生成)
输出:     figures/fig3-3_size_convergence.png

依赖: source /mnt/d/Research/Hopfion/hopfion/bin/activate
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
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

REF_R, REF_r = 2.60, 2.16
CORE_THRESHOLD = 0.05
BAD_FIT_NM = 3.0

BASE_SWEEP = "/mnt/d/Research/Hopfion/04_frustrated_fm_foundation/20260105_frustrated_fm/size_sweep"
SMALL_DIR  = "/mnt/d/Research/Hopfion/04_frustrated_fm_foundation/20260105_frustrated_fm/anisotropy_study/size_vs_ku/Ku1_0.0e+00_Ms_1.5000e+05.out"
CACHE_CSV  = "/mnt/d/Research/Hopfion/09_paper_thesis_talks/bishe/thesis_v2/figures/size_convergence_cache.csv"
OUT_PNG    = "/mnt/d/Research/Hopfion/09_paper_thesis_talks/bishe/thesis_v2/figures/fig3-3_size_convergence.png"


def _circle_residuals(params, pts):
    xc, yc, R = params
    return np.sqrt((pts[:, 0] - xc)**2 + (pts[:, 1] - yc)**2) - R


def _pbc_unwrap_xy(xy, box_L):
    centroid = np.mean(xy, axis=0)
    delta = xy - centroid
    delta -= box_L * np.round(delta / box_L)
    return centroid + delta


def compute_Rr(field):
    from scipy.optimize import least_squares
    from skimage import measure
    mz   = field.array[..., 2]
    cell = np.array(field.mesh.cell)
    pmin = np.array(field.mesh.region.pmin)
    box_L = np.array(field.mesh.region.pmax) - pmin
    mz_min = float(np.min(mz))
    core_mask = mz < (mz_min + CORE_THRESHOLD)
    if not np.any(core_mask):
        return None, None
    idx    = np.array(np.where(core_mask)).T
    coords = pmin + idx * cell
    xy     = coords[:, :2]
    if len(xy) < 4:
        return None, None
    xy_uw = _pbc_unwrap_xy(xy, box_L[:2])
    cg    = np.mean(xy_uw, axis=0)
    rg    = np.mean(np.linalg.norm(xy_uw - cg, axis=1))
    try:
        res = least_squares(_circle_residuals, [cg[0], cg[1], rg],
                            args=(xy_uw,), method='lm')
        xc, yc, R_fit = res.x
    except Exception:
        return None, None
    R_nm = abs(R_fit) * 1e9
    try:
        verts, _, _, _ = measure.marching_cubes(mz, level=0, spacing=tuple(cell))
        verts += pmin
    except (ValueError, RuntimeError):
        return R_nm, None
    if len(verts) == 0:
        return R_nm, None
    xy_v  = verts[:, :2]
    xy_v_uw = _pbc_unwrap_xy(xy_v, box_L[:2])
    rho   = np.sqrt((xy_v_uw[:,0]-xc)**2 + (xy_v_uw[:,1]-yc)**2)
    z_v   = verts[:, 2]
    dist  = np.sqrt((rho - abs(R_fit))**2 + (z_v - np.mean(coords[:,2]))**2)
    r_nm  = float(np.median(dist)) * 1e9
    return R_nm, r_nm


def extract_series(out_dir, dt, group):
    try:
        import discretisedfield as df
    except ImportError:
        print('[ERR] activate venv: source /mnt/d/Research/Hopfion/hopfion/bin/activate')
        sys.exit(1)
    ovfs = sorted(f for f in os.listdir(out_dir) if f.endswith('.ovf') and f.startswith('m'))
    rows = []
    for ovf in ovfs:
        idx = int(ovf.replace('m','').replace('.ovf',''))
        t_ns = idx * dt
        field = df.Field.from_file(os.path.join(out_dir, ovf))
        R, r = compute_Rr(field)
        rows.append({'group': group, 't_ns': t_ns, 'R_nm': R, 'r_nm': r})
        sys.stdout.write(f"\r  [{group}] {ovf}: R={R}, r={r}    ")
    print()
    return rows


if os.path.exists(CACHE_CSV):
    print(f'[INFO] 使用缓存 {CACHE_CSV}')
    data = pd.read_csv(CACHE_CSV)
else:
    print('[INFO] 无缓存, 从 OVF 提取...')
    rows = []
    rows += extract_series(SMALL_DIR, dt=0.1, group='Small')
    rows += extract_series(os.path.join(BASE_SWEEP, 'R8r4_Ku0.out'),  dt=0.05, group='R8r4')
    rows += extract_series(os.path.join(BASE_SWEEP, 'R12r5_Ku0.out'), dt=0.05, group='R12r5')
    data = pd.DataFrame(rows)
    data.to_csv(CACHE_CSV, index=False)
    print(f'[OK] cached -> {CACHE_CSV}')


# ---------------- 绘图: 2 子面板 (a)(b) 纵向堆叠 ----------------
fig, (ax_R, ax_r) = plt.subplots(2, 1, figsize=(6.0, 5.0), sharex=True)

styles = {
    'Small':  dict(color='#2ca02c', marker='o', label=r'初始 $R \approx \SI{3.1}{nm}$'.replace('\\SI{3.1}{nm}', '3.1 nm').replace('$\\approx$', '≈')),
    'R8r4':   dict(color='#1f77b4', marker='s', label='初始 R=8, r=4 nm'),
    'R12r5':  dict(color='#d62728', marker='^', label='初始 R=12, r=5 nm'),
}
# 纯 mathtext 标签（避免 \SI 未定义）
styles['Small']['label'] = r'初始 $R \approx 3.1$ nm'
styles['R8r4']['label']  = r'初始 $R=8$, $r=4$ nm'
styles['R12r5']['label'] = r'初始 $R=12$, $r=5$ nm'

for group, st in styles.items():
    sub = data[data['group'] == group].sort_values('t_ns')
    sR = sub.dropna(subset=['R_nm'])
    sr = sub.dropna(subset=['r_nm'])
    ax_R.plot(sR['t_ns'], sR['R_nm'], linestyle='-', linewidth=1.2,
              color=st['color'], marker=st['marker'], markersize=4,
              markerfacecolor='white', markeredgecolor=st['color'],
              markeredgewidth=1.0, label=st['label'])
    ax_r.plot(sr['t_ns'], sr['r_nm'], linestyle='-', linewidth=1.2,
              color=st['color'], marker=st['marker'], markersize=4,
              markerfacecolor='white', markeredgecolor=st['color'],
              markeredgewidth=1.0)

# 吸引子参考线
ax_R.axhline(REF_R, color='k', linestyle='--', linewidth=1.0, alpha=0.6,
             label=f'吸引子 {REF_R:.2f} nm')
ax_r.axhline(REF_r, color='k', linestyle='--', linewidth=1.0, alpha=0.6)

ax_R.set_ylabel(r'$R$  (nm)', fontsize=15)
ax_r.set_ylabel(r'$r$  (nm)', fontsize=15)
ax_r.set_xlabel(r'时间  $t$  (ns)', fontsize=15)
for ax in (ax_R, ax_r):
    ax.tick_params(axis='both', which='major', labelsize=13, length=5)

ax_R.set_title(r'(a) 大半径 $R(t)$', fontsize=14, fontweight='bold', loc='center', pad=4)
ax_r.set_title(r'(b) 管半径 $r(t)$', fontsize=14, fontweight='bold', loc='center', pad=4)

ax_R.legend(loc='center right', fontsize=13, frameon=False, ncol=1)

plt.tight_layout()
plt.savefig(OUT_PNG, bbox_inches='tight', dpi=300)
print(f'[OK] saved {OUT_PNG}')
