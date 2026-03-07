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
    # ---- AFM 选项（新增，最小改动） ----
    afm=None,                  # None | "checker" | "layerX" | "layerY" | "layerZ" | "sublattices"
    output_filename_B=None,    # 仅 afm="sublattices" 时使用；若 None 自动生成
    afm_outside_only=True      # True: 仅对 Hopfion 核心区外交替；False: 全域交替
):
    if p * q != Qh:
        raise ValueError(f"拓扑荷 Qh ({Qh}) 必须等于 p ({p}) 和 q ({q}) 的乘积。")
    if r <= 0:
        raise ValueError("小半径 r 必须为正数。")

    # --- 半径换算 (无变化) ---
    CONVERSION_FACTOR = np.sqrt(np.log(2) / (1 + np.log(2)))
    r_boundary = r / CONVERSION_FACTOR
    
    print(f"目标参数: Qh={Qh} (p={p}, q={q}), R={R*1e9:.1f}nm, r={r*1e9:.1f}nm")
    print(f"内部计算使用的边界半径 r_boundary = {r_boundary*1e9:.2f} nm")

    # --- 网格设置 (无变化) ---
    x_min, x_max = -xnodes * xstepsize / 2, xnodes * xstepsize / 2
    y_min, y_max = -ynodes * ystepsize / 2, ynodes * ystepsize / 2
    z_min, z_max = -znodes * zstepsize / 2, znodes * zstepsize / 2
    
    x_coords = np.linspace(x_min + xstepsize/2, x_max - xstepsize/2, xnodes)
    y_coords = np.linspace(y_min + ystepsize/2, y_max - ystepsize/2, ynodes)
    z_coords = np.linspace(z_min + zstepsize/2, z_max - zstepsize/2, znodes)
    xv, yv, zv = np.meshgrid(x_coords, y_coords, z_coords, indexing='ij')

    # --- Hopfion 核心逻辑 (无变化) ---
    mx, my, mz = np.zeros_like(xv), np.zeros_like(xv), np.ones_like(xv)
    
    psi = np.arctan2(yv, xv)                         # toroidal angle
    rho_cylindrical = np.sqrt(xv**2 + yv**2)
    rho_dist = np.sqrt(zv**2 + (rho_cylindrical - R)**2)
    mask = rho_dist < r_boundary                      # Hopfion 核心区域

    phi_poloidal = np.arctan2(zv[mask], rho_cylindrical[mask] - R)
    
    # 方位角 Phi：由 p,q 控制缠绕
    Phi = p * psi[mask] - q * phi_poloidal
    
    # 极角 Theta：平滑核
    rho_norm_sq = (rho_dist[mask] / r_boundary)**2
    Theta = np.pi * np.exp(1.0 - 1.0 / (1.0 - rho_norm_sq))
    
    # 写入核心区的 Hopfion 场
    mx[mask], my[mask], mz[mask] = np.cos(Phi) * np.sin(Theta), np.sin(Phi) * np.sin(Theta), np.cos(Theta)

    # -------- AFM 功能（新增，尽量少改动你的逻辑） --------
    # 目标：在不改变你 Hopfion 的 R/r/高度控制的前提下，仅通过索引图样做交替。
    if afm is not None:
        ix = np.arange(xnodes)[:, None, None]
        iy = np.arange(ynodes)[None, :, None]
        iz = np.arange(znodes)[None, None, :]

        if afm == "checker":
            sign = 1 - 2 * ((ix + iy + iz) % 2)   # (+1,-1) 棋盘格
        elif afm == "layerX":
            sign = 1 - 2 * (ix % 2)
        elif afm == "layerY":
            sign = 1 - 2 * (iy % 2)
        elif afm == "layerZ":
            sign = 1 - 2 * (iz % 2)
        elif afm == "sublattices":
            # A：原文件，B：整场取反为另一子晶格
            if output_filename_B is None:
                if output_filename.lower().endswith(".ovf"):
                    output_filename_B = output_filename[:-4] + "_B.ovf"
                else:
                    output_filename_B = output_filename + "_B.ovf"
            # 先写 A，后面写 B（B 只需要整体取反再写一遍即可）
            _write_ovf_binary4(mx, my, mz, x_coords, y_coords, z_coords,
                               xstepsize, ystepsize, zstepsize,
                               xnodes, ynodes, znodes,
                               Qh, p, q, output_filename, title_suffix=" (AFM A)")
            _write_ovf_binary4(-mx, -my, -mz, x_coords, y_coords, z_coords,
                               xstepsize, ystepsize, zstepsize,
                               xnodes, ynodes, znodes,
                               Qh, p, q, output_filename_B, title_suffix=" (AFM B)")
            print(f"Binary OVF A/B files written:\n  {output_filename}\n  {output_filename_B}")
            return
        else:
            raise ValueError(f"Unknown afm mode: {afm}")

        # 单文件 AFM：根据 afm_outside_only 选择只对外部交替或全域交替
        if afm_outside_only:
            outside = ~mask
            mx[outside] *= sign[outside]
            my[outside] *= sign[outside]
            mz[outside] *= sign[outside]
        else:
            mx *= sign
            my *= sign
            mz *= sign
    # ------------------ AFM 结束 ------------------

    # --- 写入单个 OVF（二进制 Binary 4；保持你的写法） ---
    _write_ovf_binary4(mx, my, mz, x_coords, y_coords, z_coords,
                       xstepsize, ystepsize, zstepsize,
                       xnodes, ynodes, znodes,
                       Qh, p, q, output_filename,
                       title_suffix=(" (AFM)" if afm and afm != "sublattices" else ""))

    print("Binary OVF file generation complete.")


def _write_ovf_binary4(mx, my, mz,
                       x_coords, y_coords, z_coords,
                       xstepsize, ystepsize, zstepsize,
                       xnodes, ynodes, znodes,
                       Qh, p, q, output_filename, title_suffix=""):
    with open(output_filename, "wb") as f:
        # 头
        f.write(b"# OOMMF OVF 2.0\n")
        f.write(b"# Segment count: 1\n")
        f.write(b"# Begin: Segment\n")
        f.write(b"# Begin: Header\n")
        
        f.write(f"# Title: Hopfion Qh={Qh} (p={p},q={q}){title_suffix}\n".encode('utf-8'))
        f.write(b"# meshtype: rectangular\n")
        f.write(b"# meshunit: m\n")
        
        xmin = x_coords[0] - xstepsize / 2.0
        ymin = y_coords[0] - ystepsize / 2.0
        zmin = z_coords[0] - zstepsize / 2.0
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

        # 数据
        f.write(b"# Begin: Data Binary 4\n")
        f.write(struct.pack('<f', 1234567.0))  # 校验码

        for k in range(znodes):
            for j in range(ynodes):
                for i in range(xnodes):
                    f.write(struct.pack('<fff', mx[i, j, k], my[i, j, k], mz[i, j, k]))
        
        f.write(b"\n# End: Data Binary 4\n")
        f.write(b"# End: Segment\n")


if __name__ == "__main__":
    

    # 示例：单文件 AFM（背景棋盘格，核心不交替）
    generate_hopfion_ovf(
        Qh=1, p=1, q=1,
        R=100e-9, r=80e-9,
        xnodes=200, ynodes=200, znodes=100,
        xstepsize=2e-9, ystepsize=2e-9, zstepsize=2e-9,
        output_filename="hopfion_Qh1.ovf",
        afm=None,
        afm_outside_only=False
    )

    
