# gen_afm_bg_hopfion_data_height.py
# 输出：纯文本磁矩行（x最快→y→z），可直接粘贴进 MuMax3 生成的 OVF 的 Data Text 区
# 形状控制：输入 hopfion_height (米)，函数内自动换算 aspect_z = hopfion_height / (2*lam)

import numpy as np

def gen_afm_bg_hopfion_data_height(
    lam,                    # 主半径 (m)，控制甜甜圈横向半径
    hopfion_height,         # 目标“高度” (m) ≈ 甜甜圈在 z 方向的总高度
    Nx, Ny, Nz,             # 网格节点数（必须与目标 OVF 一致）
    dx=None, dy=None, dz=None,     # 步长(米)；None 则按默认范围推算
    out_path="AFM_hopfion_data.txt",
    pattern="checker"       # AFM 背景交替方式: "checker" | "layerX" | "layerY" | "layerZ"
):
    # --- 步长默认：x,y ∈ [-lam, +lam]；z ∈ [-lam/2, +lam/2] ---
    if dx is None: dx = (2*lam)/Nx
    if dy is None: dy = (2*lam)/Ny
    if dz is None: dz = (lam)/Nz

    # 纵横比：高度与基准高度(=2*lam)之比；>1 更“高”，<1 更“扁”
    aspect_z = max(float(hopfion_height) / (2.0*float(lam)), 1e-12)

    # --- 构建网格坐标（cell 中心） ---
    xs = (np.arange(Nx)+0.5)*dx - (Nx*dx)/2
    ys = (np.arange(Ny)+0.5)*dy - (Ny*dy)/2
    zs = (np.arange(Nz)+0.5)*dz - (Nz*dz)/2
    X, Y, Z = np.meshgrid(xs, ys, zs, indexing='ij')

    # --- Hopfion 连续场（Q≈+1 的环面构型），远场 ~ +ez ---
    r   = np.sqrt(X**2 + Y**2) + 1e-30
    phi = np.arctan2(Y, X)

    # 用 Z' = Z / aspect_z 实现“高度”控制（aspect_z 越大，允许的 |Z| 越大 → 更“高”）
    Zp    = Z / aspect_z
    rho_x = r - lam
    rho_y = Zp
    rho   = np.sqrt(rho_x**2 + rho_y**2) + 1e-30

    # 环面核判定（inside=True 为 Hopfion 核心区，不做 AFM 交替）
    inside = np.sqrt((X - lam*np.cos(phi))**2 + (Y - lam*np.sin(phi))**2 + Zp**2) < lam

    # 初始化背景：+ez
    mx = np.zeros_like(X); my = np.zeros_like(X); mz = np.ones_like(X)

    # 在核心区内用 Hopfion 公式替换
    s    = np.sin(np.pi*rho/lam)
    c    = np.cos(np.pi*rho/lam)
    rrho = (r*rho) + 1e-30
    mx_in = s * ((X*rho_y - Y*rho_x)/rrho)
    my_in = s * ((X*rho_x + Y*rho_y)/rrho)
    mz_in = -c

    mx[inside] = mx_in[inside]
    my[inside] = my_in[inside]
    mz[inside] = mz_in[inside]

    # 归一化（数值稳健）
    nrm = np.sqrt(mx*mx + my*my + mz*mz) + 1e-30
    mx /= nrm; my /= nrm; mz /= nrm

    # --- AFM 背景：仅对“非 Hopfion 区域”施加交替符号 ---
    ix = np.arange(Nx)[:, None, None]
    iy = np.arange(Ny)[None, :, None]
    iz = np.arange(Nz)[None, None, :]

    if pattern == "checker":
        sign = 1 - 2 * ((ix + iy + iz) % 2)  # (+1,-1) 棋盘格
    elif pattern == "layerX":
        sign = 1 - 2 * (ix % 2)
    elif pattern == "layerY":
        sign = 1 - 2 * (iy % 2)
    elif pattern == "layerZ":
        sign = 1 - 2 * (iz % 2)
    else:
        raise ValueError(f"Unknown pattern: {pattern}")

    outside = ~inside
    mx[outside] *= sign[outside]
    my[outside] *= sign[outside]
    mz[outside] *= sign[outside]

    # --- 以 x最快→y→z 的顺序写出纯数据行 ---
    with open(out_path, "w") as f:
        for k in range(Nz):
            for j in range(Ny):
                for i in range(Nx):
                    f.write(f"{float(mx[i,j,k])} {float(my[i,j,k])} {float(mz[i,j,k])}\n")

    # 简要信息
    Lx, Ly, Lz = Nx*dx, Ny*dy, Nz*dz
    print(f"Saved: {out_path}")
    print(f"Grid: {Nx} x {Ny} x {Nz} ; Step: dx={dx:.3e}, dy={dy:.3e}, dz={dz:.3e}")
    print(f"Box size: {Lx:.3e} x {Ly:.3e} x {Lz:.3e} m")
    print(f"lam={lam:.3e} m ; target height={hopfion_height:.3e} m ; aspect_z={aspect_z:.3f}")
    print(f"AFM pattern: {pattern} ; Hopfion core kept unflipped.")

if __name__ == "__main__":
    # ⚠️ 把这些参数改成与你将要粘贴的 OVF 完全一致！
    gen_afm_bg_hopfion_data_height(
        lam=3e-9,                 # 横向半径 ~40 nm
        hopfion_height=1.5e-9,      # 目标高度 ~80 nm（等于基准 2*lam → aspect_z=1）
        Nx=100, Ny=100, Nz=100,
        dx=5e-10, dy=5e-10, dz=5e-10,  # 或置为 None 让脚本按 lam/N 自动推算
        out_path="AFM_hopfion_data.txt",
        pattern="checker"          # 或 "layerZ" 等
    )
