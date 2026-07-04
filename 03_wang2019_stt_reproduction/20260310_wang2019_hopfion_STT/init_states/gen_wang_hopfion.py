"""
Wang ansatz Hopfion 初始态生成器
论文: Wang XS, Qaiumzadeh A, Brataas A, PRL 123, 147203 (2019)
公式: Eq. 4 (H=+1 Néel Hopfion)

Bloch Hopfion: 令 φ_B = φ + π/2 即可从 Néel 公式转换
"""

import numpy as np
import struct
import os

# ─── Wang ansatz 参数（论文拟合值）───
R_fit  = 8.3e-9    # m，Hopfion 环半径
wR_fit = 5.6e-9    # m，径向非线性尺度
h_fit  = 6.3e-9    # m，轴向半高
wh_fit = 1.6e-9    # m，轴向非线性尺度

# ─── 几何参数（128nm × 128nm × 16nm 纳米带，PBC-x）───
Lx = 128e-9  # m
Ly = 128e-9  # m
Lz = 16e-9   # m
dx = 0.5e-9  # 格点大小 0.5nm
Nx = int(Lx / dx)   # 256
Ny = int(Ly / dx)   # 256
Nz = int(Lz / dx)   # 32


def rescale_r(rho, R=R_fit, wR=wR_fit):
    """
    径向非线性重标定 (Wang Eq.4)
    r' = (e^(R/wR) - 1) / (e^(rho/wR) - 1)
    当 rho→0 时 r'→∞（核心正上方极点），避免除零加 eps
    """
    eps = 1e-30
    numerator   = np.exp(R / wR) - 1.0
    denominator = np.exp(rho / wR) - 1.0 + eps
    return numerator / denominator


def rescale_z(z, h=h_fit, wh=wh_fit):
    """
    轴向非线性重标定 (Wang Eq.4)
    z' = sign(z) × (e^(|z|/wh) - 1) / (e^(h/wh) - 1)
    """
    eps = 1e-30
    denominator = np.exp(h / wh) - 1.0 + eps
    return np.sign(z) * (np.exp(np.abs(z) / wh) - 1.0) / denominator


def wang_hopfion_neel(x, y, z, cx=0.0, cy=0.0, cz=0.0,
                      R=R_fit, wR=wR_fit, h=h_fit, wh=wh_fit):
    """
    H=+1 Néel Hopfion 磁矩分量（Wang 2019, Eq. 4）

    参数
    ----
    x, y, z : 坐标（m），支持 ndarray
    cx, cy, cz : Hopfion 中心坐标

    返回
    ----
    mx, my, mz : 单位矢量分量（未额外归一化，公式本身满足 |m|=1）
    """
    dx_ = x - cx
    dy_ = y - cy
    dz  = z - cz

    rho = np.sqrt(dx_**2 + dy_**2)
    phi = np.arctan2(dy_, dx_)   # 方位角

    rp = rescale_r(rho, R, wR)   # r'
    zp = rescale_z(dz,  h, wh)   # z'

    denom = (1.0 + rp**2 + zp**2)**2

    # Wang Eq. 4 — Néel 型（DMI 界面型）
    mx = 4.0 * rp * (2.0 * zp * np.sin(phi) + np.cos(phi) * (rp**2 + zp**2 - 1.0)) / denom
    my = 4.0 * rp * (-2.0 * zp * np.cos(phi) + np.sin(phi) * (rp**2 + zp**2 - 1.0)) / denom
    mz = 1.0 - 8.0 * rp**2 / denom

    # 归一化（数值误差校正）
    norm = np.sqrt(mx**2 + my**2 + mz**2)
    norm = np.where(norm < 1e-10, 1.0, norm)
    return mx / norm, my / norm, mz / norm


def wang_hopfion_bloch(x, y, z, cx=0.0, cy=0.0, cz=0.0,
                       R=R_fit, wR=wR_fit, h=h_fit, wh=wh_fit):
    """
    H=+1 Bloch Hopfion：在 Néel 基础上 φ → φ + π/2
    等价于 (mx, my) → (-my, mx)
    """
    mx_n, my_n, mz = wang_hopfion_neel(x, y, z, cx, cy, cz, R, wR, h, wh)
    return -my_n, mx_n, mz


def write_ovf(mx, my, mz, filename, dx=dx, Nx=Nx, Ny=Ny, Nz=Nz):
    """
    将磁化数组写成 Mumax3 兼容的 OVF2 二进制文件（float32）
    数组布局: (Nz, Ny, Nx) — 与 Mumax3 内存顺序一致
    """
    with open(filename, 'wb') as f:
        def wl(s):
            f.write((s + '\n').encode('ascii'))

        wl('# OOMMF OVF 2.0')
        wl('#')
        wl('# Segment count: 1')
        wl('#')
        wl('# Begin: Segment')
        wl('# Begin: Header')
        wl('# Title: Wang Hopfion')
        wl('# meshtype: rectangular')
        wl('# meshunit: m')
        wl(f'# xmin: 0')
        wl(f'# ymin: 0')
        wl(f'# zmin: 0')
        wl(f'# xmax: {Nx * dx:.6e}')
        wl(f'# ymax: {Ny * dx:.6e}')
        wl(f'# zmax: {Nz * dx:.6e}')
        wl(f'# xstepsize: {dx:.6e}')
        wl(f'# ystepsize: {dx:.6e}')
        wl(f'# zstepsize: {dx:.6e}')
        wl(f'# xnodes: {Nx}')
        wl(f'# ynodes: {Ny}')
        wl(f'# znodes: {Nz}')
        wl('# valuedim: 3')
        wl('# valuelabels: mx my mz')
        wl('# valueunits: 1 1 1')
        wl('# End: Header')
        wl('#')
        wl('# Begin: Data Binary 4')

        # 写入校验数  1234567.0（OVF2 float32 标准）
        f.write(struct.pack('<f', 1234567.0))

        # 写入磁化数据：Mumax3 顺序 z→y→x（内循环 x 最快）
        data = np.stack([mx, my, mz], axis=-1).astype(np.float32)
        # shape: (Nz, Ny, Nx, 3) — 已正确排列
        f.write(data.tobytes())

        wl('# End: Data Binary 4')
        wl('# End: Segment')

    print(f'写入 {filename}  ({Nx}×{Ny}×{Nz}, {os.path.getsize(filename)/1024:.1f} KB)')


def build_coordinate_grids(Nx=Nx, Ny=Ny, Nz=Nz, dx=dx):
    """构建格点中心坐标网格，原点在盒子中心"""
    ix = np.arange(Nx); iy = np.arange(Ny); iz = np.arange(Nz)
    xc = (ix + 0.5) * dx - 0.5 * Nx * dx
    yc = (iy + 0.5) * dx - 0.5 * Ny * dx
    zc = (iz + 0.5) * dx - 0.5 * Nz * dx
    ZZ, YY, XX = np.meshgrid(zc, yc, xc, indexing='ij')   # (Nz, Ny, Nx)
    return XX, YY, ZZ


def main():
    out_dir = os.path.dirname(os.path.abspath(__file__))

    print('构建坐标网格...')
    XX, YY, ZZ = build_coordinate_grids()

    # ── Néel Hopfion ──
    print('计算 Néel Hopfion ansatz (Wang Eq. 4)...')
    mx_n, my_n, mz_n = wang_hopfion_neel(XX, YY, ZZ)
    neel_path = os.path.join(out_dir, 'wang_neel_hopfion_init.ovf')
    write_ovf(mx_n, my_n, mz_n, neel_path)

    # ── Bloch Hopfion ──
    print('计算 Bloch Hopfion ansatz (φ → φ+π/2)...')
    mx_b, my_b, mz_b = wang_hopfion_bloch(XX, YY, ZZ)
    bloch_path = os.path.join(out_dir, 'wang_bloch_hopfion_init.ovf')
    write_ovf(mx_b, my_b, mz_b, bloch_path)

    # ── 简单验证 ──
    print('\n--- 验证 ---')
    for name, mz in [('Néel', mz_n), ('Bloch', mz_b)]:
        print(f'{name}: mz_min={mz.min():.4f}, mz_max={mz.max():.4f}, '
              f'mz_center={mz[Nz//2, Ny//2, Nx//2]:.4f}')

    print('\n完成。OVF 文件已写入 init_states/ 目录。')


if __name__ == '__main__':
    main()
