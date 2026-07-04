#!/usr/bin/env python3
"""_extract_drift10ns_centroids.py

从 bg_mx_axis_x_stable/run.out 的 201 个 OVF 提取质心 (x,y,z) 随时间,
缓存为 CSV 供 redraw_fig3-4_drift_trajectory_10ns.py 读取。

运行一次即可, CSV 生成后可直接删除本脚本的调用需求。

前置: source /mnt/d/Research/Hopfion/hopfion/bin/activate
"""

import os
import glob
import numpy as np
import pandas as pd
import discretisedfield as df  # noqa: F401

RUN_DIR = '/mnt/d/Research/Hopfion/04_frustrated_fm_foundation/20260105_frustrated_fm/drift_experiments/bg_mx_axis_x_stable/run.out'
OUT_CSV = '/mnt/d/Research/Hopfion/09_paper_thesis_talks/bishe/thesis_v2/figures/drift10ns_centroid_bg_mx_axis_x.csv'
DT_NS = 0.05  # 10 ns / 200 帧 = 0.05 ns/帧


def hopfion_centroid_nm(field):
    """Hopfion 质心 (nm): 对 |1 - m_bg·m| 加权求平均坐标。
    bg 方向使用 z=boundary 层的 m 作为估计, 避免硬编码。"""
    m = field.array  # shape (Nx, Ny, Nz, 3)
    # 取 z=Nz-1 层中心点作为背景估计 (远离 hopfion 核心)
    Nx, Ny, Nz = m.shape[:3]
    bg = m[Nx // 2, Ny // 2, Nz - 1, :]
    bg_norm = bg / (np.linalg.norm(bg) + 1e-12)
    # 权重 = 1 - m·bg (核心偏离背景的程度)
    dotp = np.einsum('ijkd,d->ijk', m, bg_norm)
    w = np.clip(1.0 - dotp, 0.0, None)
    total = w.sum()
    if total < 1e-12:
        return 0.0, 0.0, 0.0

    # 格点坐标 (nm)
    mesh = field.mesh
    # 使用 cell 中心
    xs = np.linspace(mesh.region.pmin[0] + mesh.cell[0] / 2,
                     mesh.region.pmax[0] - mesh.cell[0] / 2, Nx) * 1e9
    ys = np.linspace(mesh.region.pmin[1] + mesh.cell[1] / 2,
                     mesh.region.pmax[1] - mesh.cell[1] / 2, Ny) * 1e9
    zs = np.linspace(mesh.region.pmin[2] + mesh.cell[2] / 2,
                     mesh.region.pmax[2] - mesh.cell[2] / 2, Nz) * 1e9

    wx = w.sum(axis=(1, 2))
    wy = w.sum(axis=(0, 2))
    wz = w.sum(axis=(0, 1))
    cx = float((wx * xs).sum() / total)
    cy = float((wy * ys).sum() / total)
    cz = float((wz * zs).sum() / total)
    return cx, cy, cz


def main():
    ovfs = sorted(glob.glob(os.path.join(RUN_DIR, 'm*.ovf')))
    print(f'[INFO] {len(ovfs)} OVFs found')

    rows = []
    for i, path in enumerate(ovfs):
        try:
            field = df.Field.from_file(path)
        except Exception as e:
            print(f'[WARN] skip {os.path.basename(path)}: {e}')
            continue
        cx, cy, cz = hopfion_centroid_nm(field)
        t = i * DT_NS
        rows.append({'t_ns': t, 'x_nm': cx, 'y_nm': cy, 'z_nm': cz})
        if i % 20 == 0:
            print(f'  [{i:3d}/{len(ovfs)}] t={t:5.2f}ns  (x,y,z)=({cx:+.2f},{cy:+.2f},{cz:+.2f}) nm')

    df_out = pd.DataFrame(rows)
    # 相对 t=0 位移
    df_out['dx_nm'] = df_out['x_nm'] - df_out['x_nm'].iloc[0]
    df_out['dy_nm'] = df_out['y_nm'] - df_out['y_nm'].iloc[0]
    df_out['dz_nm'] = df_out['z_nm'] - df_out['z_nm'].iloc[0]
    df_out.to_csv(OUT_CSV, index=False)
    print(f'[OK] saved {OUT_CSV}  (rows={len(df_out)})')


if __name__ == '__main__':
    main()
