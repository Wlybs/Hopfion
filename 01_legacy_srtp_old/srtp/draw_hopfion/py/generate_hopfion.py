import numpy as np

def generate_simple_hopfion_ovf(
    lam=40e-9,  # 环体尺度 λ，决定 Hopfion 尺寸与默认单胞
    Nx=160, Ny=160, Nz=80,  # 网格数
    dx=None, dy=None, dz=None,  # 步长(可留空按单胞尺寸自动设)
    output="hopfion_Qh1_simple.ovf"
):
    """
    最简单的 Qh=1 hopfion（均匀背景），实现自 Göbel & Lounis (2025) Eq.(1)。
    单胞默认 ~ (2λ, 2λ, λ)；环体外 m = +ez。
    """
    # --- 网格与空间 ---
    if dx is None: dx = (2*lam)/Nx
    if dy is None: dy = (2*lam)/Ny
    if dz is None: dz = (lam)/Nz

    xs = (np.arange(Nx)+0.5)*dx - (Nx*dx)/2
    ys = (np.arange(Ny)+0.5)*dy - (Ny*dy)/2
    zs = (np.arange(Nz)+0.5)*dz - (Nz*dz)/2
    X, Y, Z = np.meshgrid(xs, ys, zs, indexing='ij')

    r = np.sqrt(X**2 + Y**2) + 1e-30
    phi = np.arctan2(Y, X)

    # 论文中的变换坐标 ρx, ρy 与 ρ
    rho_x = r - lam
    rho_y = Z
    rho = np.sqrt(rho_x**2 + rho_y**2) + 1e-30

    # 环体体积判定：sqrt((x-λ cosφ)^2 + (y-λ sinφ)^2 + z^2) < λ
    inside = np.sqrt((X - lam*np.cos(phi))**2 + (Y - lam*np.sin(phi))**2 + Z**2) < lam

    # 初始化为均匀背景 +ez
    mx = np.zeros_like(X); my = np.zeros_like(X); mz = np.ones_like(X)

    # Eq.(1)：环体内的 m(r)
    s = np.sin(np.pi*rho/lam)
    c = np.cos(np.pi*rho/lam)
    rrho = (r*rho) + 1e-30
    mx_in = s * ((X*rho_y - Y*rho_x)/rrho)
    my_in = s * ((X*rho_x + Y*rho_y)/rrho)
    mz_in = -c

    mx[inside] = mx_in[inside]
    my[inside] = my_in[inside]
    mz[inside] = mz_in[inside]

    # 归一化
    nrm = np.sqrt(mx*mx + my*my + mz*mz) + 1e-30
    mx /= nrm; my /= nrm; mz /= nrm

    # 写 OVF v1 文本
    with open(output, 'w') as f:
        f.write("# OOMMF: rectangular mesh v1.0\n")
        f.write("# Segment count: 1\n# Begin: Segment\n# Begin: Header\n")
        f.write("# Title: Simple Qh=1 hopfion (Goebel & Lounis 2025 Eq.(1))\n")
        f.write("# meshtype: rectangular\n# xbase: 0\n# ybase: 0\n# zbase: 0\n")
        f.write(f"# xnodes: {Nx}\n# ynodes: {Ny}\n# znodes: {Nz}\n")
        f.write(f"# xstepsize: {dx}\n# ystepsize: {dy}\n# zstepsize: {dz}\n")
        f.write("# valuedim: 3\n# valuelabels: m_x m_y m_z\n# valueunits: 1 1 1\n")
        f.write("# End: Header\n# Begin: Data Text\n")
        for k in range(Nz):
            for j in range(Ny):
                for i in range(Nx):
                    f.write(f"{mx[i,j,k]} {my[i,j,k]} {mz[i,j,k]}\n")
        f.write("# End: Data Text\n# End: Segment\n")
    print(f"Wrote {output}")
    return output

if __name__ == "__main__":
    generate_simple_hopfion_ovf(
        lam=40e-9,  # 这里 40 nm 是个稳妥的起点，可按你的材料 / 单胞改
        Nx=160, Ny=160, Nz=80
    )
