"""
生成 Néel Hopfion 初始态 OVF

参考: Khodzhaev & Turgut 2022, J. Phys.: Condens. Matter 34, 225805
      Section 3. Neel hopfion

材料: 磁多层膜（Ir/Co/Pt 类）, 界面 DMI
几何: d=64nm, h=8nm, cell=0.5nm → grid 128×128×16

方法: 先生成 Bloch 型环面 ansatz，再绕 z 轴旋转 90°（(-my, mx, mz)）得到 Néel 字符。
      原文描述: "We rotate the individual spins from the known hopfion ansatz
                 by 90 degrees around the z-axis"

背景: mz=+1（由 Ku1=1e6 PMA 保证）
环面参数: R=12nm（大半径），r_boundary=4nm（管半径），居于盘内
"""
import numpy as np
import struct
import os

# 几何参数
xnodes, ynodes, znodes = 128, 128, 16
dx = dy = dz = 0.5e-9          # 0.5nm 格点

R_torus   = 12e-9              # 环面大半径
r_boundary = 4e-9              # 管截断半径（≈ 盘高一半）

BASE = os.path.dirname(os.path.abspath(__file__))
OUTPUT = os.path.join(BASE, "neel_hopfion_init.ovf")

# 坐标（以盒子中心为原点）
x_c = (np.arange(xnodes) - xnodes/2 + 0.5) * dx
y_c = (np.arange(ynodes) - ynodes/2 + 0.5) * dy
z_c = (np.arange(znodes) - znodes/2 + 0.5) * dz
xv, yv, zv = np.meshgrid(x_c, y_c, z_c, indexing='ij')

# 柱坐标（环轴沿 z，环在 xy 平面）
rho   = np.sqrt(xv**2 + yv**2)
phi   = np.arctan2(yv, xv)     # 环向角（绕 z 轴）

# 到环管中心的距离
r_dist = np.sqrt((rho - R_torus)**2 + zv**2)
mask   = r_dist < r_boundary

# ── 先构造 Bloch 型 Hopfion ansatz ─────────────────────────────────────
mx_b = np.zeros_like(xv)
my_b = np.zeros_like(xv)
mz_b = np.ones_like(xv)        # 背景 mz=+1

phi_pol   = np.arctan2(zv[mask], rho[mask] - R_torus)   # 截面角
Phi_bloch = phi[mask] - phi_pol                           # Bloch: Φ = ψ - φ_pol

rho_norm2 = (r_dist[mask] / r_boundary)**2
Theta     = np.pi * np.exp(1.0 - 1.0 / (1.0 - rho_norm2))

mx_b[mask] = np.sin(Theta) * np.cos(Phi_bloch)
my_b[mask] = np.sin(Theta) * np.sin(Phi_bloch)
mz_b[mask] = np.cos(Theta)

# ── 绕 z 轴旋转 90°：Bloch → Néel ─────────────────────────────────────
# 旋转矩阵 Rz(90°): (mx, my) → (-my, mx)
mx = -my_b.copy()
my =  mx_b.copy()
mz =  mz_b.copy()

# 归一化（数值误差修正）
norm = np.sqrt(mx**2 + my**2 + mz**2)
norm = np.where(norm < 1e-10, 1.0, norm)
mx, my, mz = mx/norm, my/norm, mz/norm

print(f"网格: {xnodes}×{ynodes}×{znodes} @ {dx*1e9:.1f}nm → {xnodes*dx*1e9:.0f}×{ynodes*dy*1e9:.0f}×{znodes*dz*1e9:.0f} nm")
print(f"环面: R={R_torus*1e9:.0f}nm, r_boundary={r_boundary*1e9:.0f}nm")
print(f"mz mean = {mz.mean():.4f}, range = [{mz.min():.3f}, {mz.max():.3f}]")
print(f"核心 (mz<0) 占比: {(mz<0).mean()*100:.1f}%")

# ── 写 OVF Binary 4 ────────────────────────────────────────────────────
xmin = -xnodes*dx/2; xmax = -xmin
ymin = -ynodes*dy/2; ymax = -ymin
zmin = -znodes*dz/2; zmax = -zmin

header = f"""# OOMMF OVF 2.0
# Segment count: 1
# Begin: Segment
# Begin: Header
# Title: Neel Hopfion init (Bloch ansatz rotated 90deg around z)
# meshtype: rectangular
# meshunit: m
# xmin: {xmin}
# ymin: {ymin}
# zmin: {zmin}
# xmax: {xmax}
# ymax: {ymax}
# zmax: {zmax}
# valuedim: 3
# valuelabels: m_x m_y m_z
# valueunits: 1 1 1
# xnodes: {xnodes}
# ynodes: {ynodes}
# znodes: {znodes}
# xstepsize: {dx}
# ystepsize: {dy}
# zstepsize: {dz}
# End: Header
# Begin: Data Binary 4
"""

with open(OUTPUT, 'wb') as f:
    f.write(header.encode('ascii'))
    f.write(struct.pack('<f', 1234567.0))
    for iz in range(znodes):
        for iy in range(ynodes):
            for ix in range(xnodes):
                f.write(struct.pack('<fff',
                    float(mx[ix, iy, iz]),
                    float(my[ix, iy, iz]),
                    float(mz[ix, iy, iz])))
    f.write(b"\n# End: Data Binary 4\n# End: Segment\n")

print(f"已保存: {OUTPUT}")
