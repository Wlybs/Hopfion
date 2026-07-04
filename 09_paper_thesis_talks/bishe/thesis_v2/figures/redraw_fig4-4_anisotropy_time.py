#!/usr/bin/env python3
"""redraw_fig4-4_anisotropy_time.py

按 结果图示例.png 风格重绘 ch04 图 4-4: 不同 Ku_u1 下 R(t)、r(t) 时间演化。
风格: 白底 + 四面黑框 + 中文轴标签 + 8 条 Ku 配置 (plasma 渐变)

数据源: /mnt/d/Research/Hopfion/04_frustrated_fm_foundation/20260105_frustrated_fm/anisotropy_study/
        ku_critical_sweep/R8r4_Ku{0,5k,10k,20k,30k,40k,50k,52k}.out/m*.ovf

缓存: figures/anisotropy_Rr_vs_time.csv  (21 frames x 8 Ku)
输出: figures/fig3-6_anisotropy_Rr_vs_time_a.png  (R vs t)
      figures/fig3-6_anisotropy_Rr_vs_time_b.png  (r vs t)
"""

import os
import sys
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

OUT_DIR = '/mnt/d/Research/Hopfion/09_paper_thesis_talks/bishe/thesis_v2/figures'
CSV = os.path.join(OUT_DIR, 'anisotropy_Rr_vs_time.csv')
OUT = os.path.join(OUT_DIR, 'fig3-6_anisotropy_Rr_vs_time.png')

BASE = '/mnt/d/Research/Hopfion/04_frustrated_fm_foundation/20260105_frustrated_fm/anisotropy_study/ku_critical_sweep'
KU1_LIST = [0, 5000, 10000, 20000, 30000, 40000, 50000, 52000]
KU1_DIR = {
    0: 'R8r4_Ku0.out', 5000: 'R8r4_Ku5k.out', 10000: 'R8r4_Ku10k.out',
    20000: 'R8r4_Ku20k.out', 30000: 'R8r4_Ku30k.out', 40000: 'R8r4_Ku40k.out',
    50000: 'R8r4_Ku50k.out', 52000: 'R8r4_Ku52k.out',
}
SAMPLE_INDICES = [0, 2, 4, 8, 12, 16, 20]
DT_NS = 0.05
CORE_THRESHOLD = 0.05
BAD_FIT_NM = 3.0


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
    mz = field.array[..., 2]
    cell = np.array(field.mesh.cell)
    pmin = np.array(field.mesh.region.pmin)
    box_L = np.array(field.mesh.region.pmax) - pmin
    mz_min = float(np.min(mz))
    core_mask = mz < (mz_min + CORE_THRESHOLD)
    if not np.any(core_mask):
        return None, None
    idx = np.array(np.where(core_mask)).T
    coords = pmin + idx * cell
    xy = coords[:, :2]
    if len(xy) < 4:
        return None, None
    xy_u = _pbc_unwrap_xy(xy, box_L[:2])
    cen = np.mean(xy_u, axis=0)
    r0 = np.mean(np.linalg.norm(xy_u - cen, axis=1))
    try:
        res = least_squares(_circle_residuals, [cen[0], cen[1], r0],
                            args=(xy_u,), method='lm')
        xc, yc, R_fit = res.x
        err_nm = np.sqrt(res.cost / len(xy_u)) * 1e9
    except Exception:
        return None, None
    if err_nm > BAD_FIT_NM:
        return R_fit * 1e9, None
    R_nm = abs(R_fit) * 1e9
    try:
        verts, _, _, _ = measure.marching_cubes(volume=mz, level=0, spacing=tuple(cell))
        verts += pmin
    except (ValueError, RuntimeError):
        return R_nm, None
    if len(verts) == 0:
        return R_nm, None
    z_c = float(np.mean(coords[:, 2]))
    dxy = np.sqrt((verts[:, 0] - xc)**2 + (verts[:, 1] - yc)**2)
    dist = np.sqrt((dxy - abs(R_fit))**2 + (verts[:, 2] - z_c)**2)
    return R_nm, float(np.mean(dist)) * 1e9


def extract_all():
    if os.path.exists(CSV):
        print(f'[cache] {CSV}')
        return pd.read_csv(CSV)
    import discretisedfield as df_mod
    rows = []
    for ku1 in KU1_LIST:
        sub = os.path.join(BASE, KU1_DIR[ku1])
        print(f'>>> Ku1={ku1}', flush=True)
        for idx in SAMPLE_INDICES:
            ovf = os.path.join(sub, f'm{idx:06d}.ovf')
            if not os.path.exists(ovf):
                continue
            fld = df_mod.Field.from_file(ovf)
            R, r = compute_Rr(fld)
            del fld
            rows.append({'ku1': ku1, 't_ns': idx * DT_NS, 'R_nm': R, 'r_nm': r})
            print(f'  t={idx * DT_NS:.2f}ns  R={R}  r={r}', flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(CSV, index=False)
    print(f'[write] {CSV}')
    return df


def _frame(ax):
    for s in ax.spines.values():
        s.set_linewidth(1.4); s.set_color('k'); s.set_visible(True)
    ax.set_facecolor('white')
    ax.tick_params(which='major', length=5.5, width=1.1, labelsize=13)
    ax.tick_params(which='minor', length=3.0, width=0.8)
    ax.grid(False)


def _label(ku1):
    if ku1 == 0:
        return r'$K_{u1}$ = 0'
    return fr'$K_{{u1}}$ = {ku1//1000} kJ/m$^3$'


def _draw_on(ax, df, y_col, marker, ylabel, panel_tag):
    cmap = plt.cm.plasma(np.linspace(0.05, 0.88, len(KU1_LIST)))
    for i, ku1 in enumerate(KU1_LIST):
        sub = df[df['ku1'] == ku1].dropna(subset=[y_col]).sort_values('t_ns')
        if sub.empty:
            continue
        ax.plot(sub['t_ns'], sub[y_col], linestyle='-', color=cmap[i],
                linewidth=1.2, alpha=0.85, zorder=2)
        ax.plot(sub['t_ns'], sub[y_col], linestyle='none', marker=marker,
                markerfacecolor=cmap[i], markeredgecolor='k',
                markeredgewidth=0.8, markersize=7.2,
                label=_label(ku1), zorder=3)
    ax.set_xlabel('时间 $t$ (ns)', fontsize=15)
    ax.set_ylabel(ylabel, fontsize=15)
    ax.set_xlim(-0.02, 1.04)
    _frame(ax)
    # (a)(b) 面板标签: 图表外右侧竖直中间
    ax.text(1.02, 0.5, panel_tag, transform=ax.transAxes,
            fontsize=14, va='center', ha='left')


def main():
    df = extract_all()
    fig, (axT, axB) = plt.subplots(2, 1, figsize=(9.0, 10.5))
    _draw_on(axT, df, 'R_nm', 'o', r'大半径 $R$ (nm)', '(a)')
    _draw_on(axB, df, 'r_nm', 's', r'管半径 $r$ (nm)', '(b)')
    # 图例: 整图顶部横排, 两列
    handles, labels = axT.get_legend_handles_labels()
    fig.legend(handles, labels, loc='upper center',
               bbox_to_anchor=(0.5, 0.995), ncol=4,
               fontsize=13, frameon=False,
               handlelength=1.8, columnspacing=1.8, handletextpad=0.5)
    plt.tight_layout(rect=[0, 0, 1, 0.86])
    plt.savefig(OUT, bbox_inches='tight', dpi=300)
    plt.close(fig)
    print(f'[OK] saved -> {OUT}')


if __name__ == '__main__':
    main()
