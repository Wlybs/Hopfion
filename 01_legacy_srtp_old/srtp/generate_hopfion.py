import numpy as np
import os

def generate_hopfion_ovf(
    Qh=1,    
    n=1,# n: 环向涡旋度 (Azimuthal vorticity)
    m=1,# m: 极向涡旋度 (Poloidal vorticity)
    a=12e-9,# a: Hopfion 大半径 (米), 对应您代码中的 R
    p_polarity=1,# p_polarity: 中心极性 (p = +/-1)
    xnodes=100,
    ynodes=100,
    znodes=100,
    xstepsize=5e-10,
    ystepsize=5e-10,
    zstepsize=5e-10,
    output_filename="hopfion_Qh1.ovf",
):
    
    x_min, x_max = -xnodes * xstepsize / 2, xnodes * xstepsize / 2
    y_min, y_max = -ynodes * ystepsize / 2, ynodes * ystepsize / 2
    z_min, z_max = -znodes * zstepsize / 2, znodes * zstepsize / 2
    
    x_coords = np.linspace(x_min + xstepsize/2, x_max - xstepsize/2, xnodes)
    y_coords = np.linspace(y_min + ystepsize/2, y_max - ystepsize/2, ynodes)
    z_coords = np.linspace(z_min + zstepsize/2, z_max - zstepsize/2, znodes)
    xv, yv, zv = np.meshgrid(x_coords, y_coords, z_coords, indexing='ij')

    # --- mumax3 Hopfion 核心逻辑  ---
    mx, my, mz = np.zeros_like(xv), np.zeros_like(xv), np.ones_like(xv)
    
    # 1. 从笛卡尔坐标 (x,y,z) 计算柱坐标 (rho, psi, z)
    # psi: 空间位置的环向角 (toroidal angle), 对应论文的 φ
    psi = np.arctan2(yv, xv)
    rho_cylindrical = np.sqrt(xv**2 + yv**2)

    # 1: 计算环面坐标 eta 和 beta ---
    # 根据论文, 从柱坐标 (rho, z) 计算环面坐标 (eta, beta)
    # 为避免分母为0, 增加一个极小值 epsilon
    epsilon = 1e-15
    rho_sq_z_sq = rho_cylindrical**2 + zv**2
    
    # eta: 环面坐标 η
    eta_arg = (2 * a * rho_cylindrical) / (rho_sq_z_sq + a**2)
    # 使用 np.clip 防止浮点误差导致参数超出 atanh 的定义域 [-1, 1]
    eta = np.arctanh(np.clip(eta_arg, -1.0 + epsilon, 1.0 - epsilon))

    # beta: 极向角 (poloidal angle), 对应论文的 β
    beta = np.arctan2(2 * a * zv, rho_sq_z_sq - a**2)

    # --- 关键修改 2: 根据论文 Eq. (6) 计算磁矩方位角 Phi ---
    # 论文公式: Φ(r) = nφ + mβ 
    # 对应变量: Phi = n*psi + m*beta
    Phi = n * psi + m * beta

    # --- 关键修改 3: 根据论文 Eq. (7) 计算磁矩极角 Theta ---
    # 论文公式: m_z = cos(2ζ) = p * (1 - term) / (1 + term) 
    # 其中 term = cosh(η)^(2m) * tanh(η)^(2n)
    # 磁矩极角 Theta = 2ζ = arccos(m_z)
    # 注意：这里只在环内部有效，但公式本身覆盖了全空间，无需 mask
    
    # 为防止 tanh(0) 和 cosh(inf) 导致的计算问题，进行数值稳定处理
    # tanh(eta) 在 eta=0 时为0, 在 eta->inf 时为1
    # cosh(eta) 在 eta=0 时为1, 在 eta->inf 时趋于无穷
    tanh_eta = np.tanh(eta)
    cosh_eta = np.cosh(eta)
    
    # 分别计算幂次，处理可能出现的 0^0 情况 (定义为1)
    # np.power(0,0) -> 1, 这里是安全的
    term = np.power(cosh_eta, 2 * m) * np.power(tanh_eta, 2 * n)

    cos_2zeta = p_polarity * (1 - term) / (1 + term + epsilon)
    
    # 使用 np.clip 防止浮点误差导致参数超出 arccos 的定义域 [-1, 1]
    Theta = np.arccos(np.clip(cos_2zeta, -1.0, 1.0))

    # 2. 从球坐标 (Theta, Phi) 转换回笛卡尔坐标 (mx, my, mz)
    mx, my, mz = np.cos(Phi) * np.sin(Theta), np.sin(Phi) * np.sin(Theta), np.cos(Theta)
    
    # --- 写入 OVF 文件 (无变化) ---
    with open(output_filename, "w") as f:
        f.write("# OOMMF: rectangular mesh v1.0\n")
        f.write("# Segment count: 1\n")
        f.write("# Begin: Segment\n")
        f.write("# Begin: Header\n")
        f.write(f"# Title: Hopfion Qh={Qh} (n={n},m={m}) from Guslienko paper\n")
        f.write("# meshtype: rectangular\n")
        f.write("# meshunit: m\n")
        f.write(f"# xbase: {x_coords[0]}\n")
        f.write(f"# ybase: {y_coords[0]}\n")
        f.write(f"# zbase: {z_coords[0]}\n")
        f.write(f"# xstepsize: {xstepsize}\n")
        f.write(f"# ystepsize: {ystepsize}\n")
        f.write(f"# zstepsize: {zstepsize}\n")
        f.write(f"# xmin: {x_min}\n")
        f.write(f"# ymin: {y_min}\n")
        f.write(f"# zmin: {z_min}\n")
        f.write(f"# xmax: {x_max}\n")
        f.write(f"# ymax: {y_max}\n")
        f.write(f"# zmax: {z_max}\n")
        f.write(f"# xnodes: {xnodes}\n")
        f.write(f"# ynodes: {ynodes}\n")
        f.write(f"# znodes: {znodes}\n")
        f.write("# End: Header\n")
        f.write("# Begin: Data Text\n")
        for k in range(znodes):
            for j in range(ynodes):
                for i in range(xnodes):
                    f.write(f"{mx[i, j, k]} {my[i, j, k]} {mz[i, j, k]}\n")
        f.write("# End: Data Text\n")
        f.write("# End: Segment\n")

    print(f"成功生成 Hopfion (Guslienko paper model) 并保存至 '{output_filename}'")

if __name__ == "__main__":
    # --- 示例: 生成与论文一致的 Hopfion ---
    # 生成 Qh = 2 (n=2, m=1), 与论文 Figure 2B 类似
    generate_hopfion_ovf(
        Qh=2, n=2, m=1,
        a=3e-9, p_polarity=1,
        xnodes=100, ynodes=100, znodes=100,
        xstepsize=5e-10, ystepsize=5e-10, zstepsize=5e-10,
        output_filename="hopfion_Qh=2_n=2m=1_paper.ovf"
    )