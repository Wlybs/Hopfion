"""
create_hopfion.py — 解析 Hopfion 初始态生成器

将解析公式写入的 Hopfion 磁化构型输出为 OOMMF OVF 2.0（Binary 4）格式文件，
供 Mumax3/OOMMF 直接读取为初始态。

支持功能：
- 任意拓扑荷 Qh = p * q（不同 p, q 组合）
- 环面轴向选择（x / y / z）
- 中心偏移
- AFM 交替背景（checker / layerX/Y/Z / sublattices）
"""

import numpy as np
import os
import struct


def generate_hopfion_ovf(
    Qh=1,
    p=1,
    q=1,
    R=12e-9,
    r=6e-9,
    xnodes=100,
    ynodes=100,
    znodes=100,
    xstepsize=5e-10,
    ystepsize=5e-10,
    zstepsize=5e-10,
    output_filename="hopfion_Qh1.ovf",
    # 环面朝向与位置
    axis='z',              # 'x' | 'y' | 'z'：环面法向轴
    center=None,           # None → (0,0,0)；或 (cx, cy, cz) 指定中心偏移（单位 m）
    # AFM 交替选项
    afm=None,              # None | "checker" | "layerX" | "layerY" | "layerZ" | "sublattices"
    output_filename_B=None,  # 仅 afm="sublattices" 时，B 子格的输出文件名
    afm_outside_only=True  # True：仅对 Hopfion 核心区外施加 AFM 交替；False：全域交替
):
    """生成解析 Hopfion 磁化构型并写入 OVF 文件。

    参数
    ----
    Qh : int
        Hopfion 拓扑荷，须满足 Qh == p * q。
    p, q : int
        环向/极向缠绕数。
    R : float
        大半径（环中心到环面中心的距离），单位 m。
    r : float
        小半径（管截面半径），单位 m。
    xnodes, ynodes, znodes : int
        三方向网格点数。
    xstepsize, ystepsize, zstepsize : float
        三方向网格步长，单位 m。
    output_filename : str
        输出 OVF 文件路径（afm="sublattices" 时为 A 子格）。
    axis : str
        Hopfion 环面的法向轴方向，'x'/'y'/'z'。
    center : tuple or None
        Hopfion 中心坐标 (cx, cy, cz)，单位 m；None 表示坐标原点。
    afm : str or None
        AFM 交替模式。None 表示纯铁磁背景。
    output_filename_B : str or None
        仅 afm="sublattices" 时使用，B 子格输出路径。
    afm_outside_only : bool
        True：仅对核心区外应用 AFM 符号交替；False：全场交替。
    """
    if p * q != Qh:
        raise ValueError(f"拓扑荷 Qh ({Qh}) 必须等于 p ({p}) 和 q ({q}) 的乘积。")
    if r <= 0:
        raise ValueError("小半径 r 必须为正数。")

    # 将目标小半径 r 转换为解析核函数的边界半径
    # 核函数 Theta = π * exp(1 - 1/(1 - ρ²))，ρ=1 处 Theta→0，
    # 实际 FWHM 半径与 r_boundary 的换算因子由 log(2) 推导得出
    CONVERSION_FACTOR = np.sqrt(np.log(2) / (1 + np.log(2)))
    r_boundary = r / CONVERSION_FACTOR

    print(f"目标参数: Qh={Qh} (p={p}, q={q}), R={R*1e9:.1f}nm, r={r*1e9:.1f}nm, axis={axis}, center={center}")
    print(f"内部计算使用的边界半径 r_boundary = {r_boundary*1e9:.2f} nm")

    # --- 网格坐标（格点中心） ---
    x_min, x_max = -xnodes * xstepsize / 2, xnodes * xstepsize / 2
    y_min, y_max = -ynodes * ystepsize / 2, ynodes * ystepsize / 2
    z_min, z_max = -znodes * zstepsize / 2, znodes * zstepsize / 2

    x_coords = np.linspace(x_min + xstepsize/2, x_max - xstepsize/2, xnodes)
    y_coords = np.linspace(y_min + ystepsize/2, y_max - ystepsize/2, ynodes)
    z_coords = np.linspace(z_min + zstepsize/2, z_max - zstepsize/2, znodes)
    xv, yv, zv = np.meshgrid(x_coords, y_coords, z_coords, indexing='ij')

    # --- 中心偏移 ---
    if center is None:
        cx, cy, cz = 0.0, 0.0, 0.0
    else:
        cx, cy, cz = center

    xv_c = xv - cx
    yv_c = yv - cy
    zv_c = zv - cz

    # --- 有效坐标变换：将选定轴映射到"z轴"等效方向 ---
    # xe, ye：环所在平面坐标；ze：环的轴向坐标
    if axis == 'x':
        xe, ye, ze = yv_c, zv_c, xv_c
    elif axis == 'y':
        xe, ye, ze = zv_c, xv_c, yv_c
    elif axis == 'z':
        xe, ye, ze = xv_c, yv_c, zv_c
    else:
        raise ValueError(f"Unknown axis: {axis}")

    # --- Hopfion 核心场（在有效坐标系中计算，背景沿 ze 方向） ---
    mx_e = np.zeros_like(xe)
    my_e = np.zeros_like(xe)
    mz_e = np.ones_like(xe)  # 背景：mz_e = +1

    psi = np.arctan2(ye, xe)                          # 环向角
    rho_cylindrical = np.sqrt(xe**2 + ye**2)
    rho_dist = np.sqrt(ze**2 + (rho_cylindrical - R)**2)
    mask = rho_dist < r_boundary                       # Hopfion 核心区掩码

    phi_poloidal = np.arctan2(ze[mask], rho_cylindrical[mask] - R)

    # 方位角 Phi：由 p（环向）和 q（极向）控制缠绕
    Phi = p * psi[mask] - q * phi_poloidal

    # 极角 Theta：平滑截断核（在 rho_dist = r_boundary 处 Theta → 0）
    rho_norm_sq = (rho_dist[mask] / r_boundary)**2
    Theta = np.pi * np.exp(1.0 - 1.0 / (1.0 - rho_norm_sq))

    mx_e[mask] = np.cos(Phi) * np.sin(Theta)
    my_e[mask] = np.sin(Phi) * np.sin(Theta)
    mz_e[mask] = np.cos(Theta)

    # --- 映射回原始坐标系 ---
    if axis == 'x':
        # (xe, ye, ze) = (y, z, x)  =>  (mx_e, my_e, mz_e) 对应 (my, mz, mx)
        mx, my, mz = mz_e, mx_e, my_e
    elif axis == 'y':
        # (xe, ye, ze) = (z, x, y)  =>  (mx_e, my_e, mz_e) 对应 (mz, mx, my)
        mx, my, mz = my_e, mz_e, mx_e
    elif axis == 'z':
        # (xe, ye, ze) = (x, y, z)  =>  直接对应
        mx, my, mz = mx_e, my_e, mz_e

    # --- AFM 交替符号场 ---
    if afm is not None:
        ix = np.arange(xnodes)[:, None, None]
        iy = np.arange(ynodes)[None, :, None]
        iz = np.arange(znodes)[None, None, :]

        if afm == "checker":
            sign = 1 - 2 * ((ix + iy + iz) % 2)
        elif afm == "layerX":
            sign = 1 - 2 * (ix % 2)
        elif afm == "layerY":
            sign = 1 - 2 * (iy % 2)
        elif afm == "layerZ":
            sign = 1 - 2 * (iz % 2)
        elif afm == "sublattices":
            # 输出 A/B 两个子格各自的 OVF
            if output_filename_B is None:
                if output_filename.lower().endswith(".ovf"):
                    output_filename_B = output_filename[:-4] + "_B.ovf"
                else:
                    output_filename_B = output_filename + "_B.ovf"
            _write_ovf_binary4(mx, my, mz, x_coords, y_coords, z_coords,
                               xstepsize, ystepsize, zstepsize,
                               xnodes, ynodes, znodes,
                               Qh, p, q, output_filename, title_suffix=" (AFM A)")
            _write_ovf_binary4(-mx, -my, -mz, x_coords, y_coords, z_coords,
                               xstepsize, ystepsize, zstepsize,
                               xnodes, ynodes, znodes,
                               Qh, p, q, output_filename_B, title_suffix=" (AFM B)")
            return
        else:
            raise ValueError(f"Unknown afm mode: {afm}")

        if afm_outside_only:
            outside = ~mask
            mx[outside] *= sign[outside]
            my[outside] *= sign[outside]
            mz[outside] *= sign[outside]
        else:
            mx *= sign
            my *= sign
            mz *= sign

    # --- 写入 OVF 文件 ---
    title_suffix = " (AFM)" if (afm and afm != "sublattices") else ""
    _write_ovf_binary4(mx, my, mz, x_coords, y_coords, z_coords,
                       xstepsize, ystepsize, zstepsize,
                       xnodes, ynodes, znodes,
                       Qh, p, q, output_filename,
                       title_suffix=title_suffix)

    print(f"Binary OVF file {output_filename} generation complete.")


def _write_ovf_binary4(mx, my, mz,
                       x_coords, y_coords, z_coords,
                       xstepsize, ystepsize, zstepsize,
                       xnodes, ynodes, znodes,
                       Qh, p, q, output_filename, title_suffix=""):
    """将磁化场写入 OOMMF OVF 2.0 Binary 4 格式文件。

    数据排列顺序：z 最慢，x 最快（与 Mumax3 读取约定一致）。
    文件头含 IEEE 754 单精度校验值 1234567.0。
    """
    with open(output_filename, "wb") as f:
        # OVF 文件头
        f.write(b"# OOMMF OVF 2.0\n")
        f.write(b"# Segment count: 1\n")
        f.write(b"# Begin: Segment\n")
        f.write(b"# Begin: Header\n")

        f.write(f"# Title: Hopfion Qh={Qh} (p={p},q={q}){title_suffix}\n".encode('utf-8'))
        f.write(b"# meshtype: rectangular\n")
        f.write(b"# meshunit: m\n")

        # 网格边界（格点中心 ± 半步长）
        xmin = x_coords[0]  - xstepsize / 2.0
        ymin = y_coords[0]  - ystepsize / 2.0
        zmin = z_coords[0]  - zstepsize / 2.0
        xmax = x_coords[-1] + xstepsize / 2.0
        ymax = y_coords[-1] + ystepsize / 2.0
        zmax = z_coords[-1] + zstepsize / 2.0

        f.write(f"# xmin: {xmin}\n".encode('utf-8'))
        f.write(f"# ymin: {ymin}\n".encode('utf-8'))
        f.write(f"# zmin: {zmin}\n".encode('utf-8'))
        f.write(f"# xmax: {xmax}\n".encode('utf-8'))
        f.write(f"# ymax: {ymax}\n".encode('utf-8'))
        f.write(f"# zmax: {zmax}\n".encode('utf-8'))

        f.write(b"# valuedim: 3\n")
        f.write(b"# valuelabels: m_x m_y m_z\n")
        f.write(b"# valueunits: 1 1 1\n")

        f.write(f"# xnodes: {xnodes}\n".encode('utf-8'))
        f.write(f"# ynodes: {ynodes}\n".encode('utf-8'))
        f.write(f"# znodes: {znodes}\n".encode('utf-8'))
        f.write(f"# xstepsize: {xstepsize}\n".encode('utf-8'))
        f.write(f"# ystepsize: {ystepsize}\n".encode('utf-8'))
        f.write(f"# zstepsize: {zstepsize}\n".encode('utf-8'))

        f.write(b"# End: Header\n")

        # 二进制数据块（单精度浮点，小端序）
        f.write(b"# Begin: Data Binary 4\n")
        f.write(struct.pack('<f', 1234567.0))  # IEEE 754 校验魔数

        for k in range(znodes):
            for j in range(ynodes):
                for i in range(xnodes):
                    f.write(struct.pack('<fff', mx[i, j, k], my[i, j, k], mz[i, j, k]))

        f.write(b"\n# End: Data Binary 4\n")
        f.write(b"# End: Segment\n")


if __name__ == "__main__":
    generate_hopfion_ovf(
        Qh=4, p=2, q=2,
        R=12e-9, r=6e-9,
        xnodes=100, ynodes=100, znodes=100,
        xstepsize=5e-10, ystepsize=5e-10, zstepsize=5e-10,
        output_filename="hopfion_Qh4.ovf",
        axis='z',
    )
