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

    # --- mumax3 Hopfion 核心逻辑 ---
    mx, my, mz = np.zeros_like(xv), np.zeros_like(xv), np.ones_like(xv)
    
    # psi: 空间位置的环向角 (toroidal angle)
    psi = np.arctan2(yv, xv)
    rho_cylindrical = np.sqrt(xv**2 + yv**2)
    rho_dist = np.sqrt(zv**2 + (rho_cylindrical - R)**2)
    mask = rho_dist < r_boundary

    # phi_poloidal: 空间位置的极向角 (poloidal angle)
    phi_poloidal = np.arctan2(zv[mask], rho_cylindrical[mask] - R)
    
    # --- 关键修改：引入 p 和 q 来计算磁矩方位角 Phi ---
    # 磁矩的方位角 Phi 由空间位置的两个角度 (psi, phi_poloidal) 和两个涡旋度 (p, q) 共同决定。
    # Phi = p * (环向空间角) - q * (极向空间角)
    # 这个公式确保了磁矩按照 p 和 q 指定的方式进行缠绕。
    Phi = p * psi[mask] - q * phi_poloidal
    # --- 修改结束 ---
    
    # 极角 Theta 的计算方式不变
    rho_norm_sq = (rho_dist[mask] / r_boundary)**2
    Theta = np.pi * np.exp(1.0 - 1.0 / (1.0 - rho_norm_sq))

    mx[mask], my[mask], mz[mask] = np.cos(Phi) * np.sin(Theta), np.sin(Phi) * np.sin(Theta), np.cos(Theta)
    
    # --- 写入 OVF 文件 (无变化) ---
    with open(output_filename, "wb") as f:
        # 3. 写入二进制OVF头信息 (所有字符串都需编码为字节)
        f.write(b"# OOMMF OVF 2.0\n")
        f.write(b"# Segment count: 1\n")
        f.write(b"# Begin: Segment\n")
        f.write(b"# Begin: Header\n")
        
        f.write(f"# Title: Hopfion Qh={Qh} (p={p},q={q})\n".encode('utf-8'))
        f.write(b"# meshtype: rectangular\n")
        f.write(b"# meshunit: m\n")
        
        # 使用 xmin/xmax 格式，更受 mumax3 欢迎
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

        # 4. 写入二进制数据
        f.write(b"# Begin: Data Binary 4\n")
        
        # 写入4字节的校验码 (1234567.0的二进制表示)
        f.write(struct.pack('<f', 1234567.0))

        # 按照 z, y, x 的顺序循环写入数据
        for k in range(znodes):
            for j in range(ynodes):
                for i in range(xnodes):
                    # 将三个浮点数打包成12字节的二进制数据并写入
                    f.write(struct.pack('<fff', mx[i, j, k], my[i, j, k], mz[i, j, k]))
        
        # 写入文件尾
        f.write(b"\n# End: Data Binary 4\n")
        f.write(b"# End: Segment\n")

    print("Binary OVF file generation complete.")
    
if __name__ == "__main__":
    # --- 现在您可以生成任意 Qh 的 Hopfion 了 ---

    # 示例1: 生成标准的 Qh = 1 (p=1, q=1)
    generate_hopfion_ovf(
        Qh=1,
        p=1,
        q=1,
        R=20e-9,
        r=10e-9,
        xnodes=100,
        ynodes=100,
        znodes=50,
        xstepsize=2e-9,
        ystepsize=2e-9,
        zstepsize=2e-9,
        output_filename="hopfion_Qh1.ovf",
    )
    
    generate_hopfion_ovf(
        Qh=2,
        p=2,
        q=1,
        R=3e-9,
        r=1.5e-9,
        xnodes=100,
        ynodes=100,
        znodes=100,
        xstepsize=0.5e-9,
        ystepsize=0.5e-9,
        zstepsize=0.5e-9,
        output_filename="stable-state-h+1+2_my.ovf",
    )
    