"""
用 Sutcliffe 2018 解析近似公式（eq. 3.3）生成 Hopfion OVF
J. Phys. A: Math. Theor. 51, 375401 (2018)

公式:
  Omega = tan(pi*z/L)
  Xi    = (1 + (2z/L)^2) * sec(pi*rho/(2L)) / L
  Lambda = Xi^2*rho^2 + Omega^2/4

  mx = 4*Xi*rho*(Omega*cos(theta) - (Lambda-1)*sin(theta)) / (1+Lambda)^2
  my = 4*Xi*rho*(Omega*sin(theta) + (Lambda-1)*cos(theta)) / (1+Lambda)^2
  mz = 1 - 8*Xi^2*rho^2 / (1+Lambda)^2

几何: 圆柱 d=3L=210nm, h=L=70nm (Sutcliffe 原始几何)
网格: 105x105x35 @ 2nm
"""
import numpy as np
import struct
import os

L = 70e-9          # FeGe helical period (m)
xnodes, ynodes, znodes = 105, 105, 35
dx, dy, dz = 2e-9, 2e-9, 2e-9

# 坐标系: 以盒子中心为原点
x_coords = (np.arange(xnodes) - xnodes/2 + 0.5) * dx
y_coords = (np.arange(ynodes) - ynodes/2 + 0.5) * dy
z_coords = (np.arange(znodes) - znodes/2 + 0.5) * dz

# 建立三维网格 (x, y, z)
xv, yv, zv = np.meshgrid(x_coords, y_coords, z_coords, indexing='ij')

# 柱坐标
rho   = np.sqrt(xv**2 + yv**2)
theta = np.arctan2(yv, xv)

# 防止 z = ±L/2 时 tan 溢出，做截断
z_clip = np.clip(zv, -L/2 * 0.9999, L/2 * 0.9999)

# Sutcliffe 解析公式 (eq. 3.3)
Omega  = np.tan(np.pi * z_clip / L)
sec    = 1.0 / np.cos(np.pi * rho / (2 * L))    # sec(pi*rho/(2L))
sec    = np.clip(sec, -1e6, 1e6)                 # 防止 rho→L 时溢出
Xi     = (1.0 + (2 * zv / L)**2) * sec / L
Lambda = Xi**2 * rho**2 + Omega**2 / 4.0

denom  = (1.0 + Lambda)**2

mx = 4 * Xi * rho * (Omega * np.cos(theta) - (Lambda - 1) * np.sin(theta)) / denom
my = 4 * Xi * rho * (Omega * np.sin(theta) + (Lambda - 1) * np.cos(theta)) / denom
mz = 1.0 - 8 * Xi**2 * rho**2 / denom

# 归一化 (公式已是单位向量，但数值精度可能偏离)
norm = np.sqrt(mx**2 + my**2 + mz**2)
norm = np.where(norm < 1e-10, 1.0, norm)
mx, my, mz = mx/norm, my/norm, mz/norm

# 在圆柱外 (rho > 3L/2) 或顶底层，设置 mz=1 (FM 背景/边界)
R_cyl = 3 * L / 2   # 105nm
mask_outside = rho > R_cyl
mx[mask_outside] = 0.0
my[mask_outside] = 0.0
mz[mask_outside] = 1.0

# 顶底层强制 mz=1 (对应 frozenspins 边界条件)
mx[:, :, 0]  = 0.0; my[:, :, 0]  = 0.0; mz[:, :, 0]  = 1.0
mx[:, :, -1] = 0.0; my[:, :, -1] = 0.0; mz[:, :, -1] = 1.0

print(f"mz mean  = {mz.mean():.4f}")
print(f"mz range = [{mz.min():.4f}, {mz.max():.4f}]")
print(f"Core (mz<0) fraction: {(mz<0).mean():.3f}")

# 写 OVF 文件
OUTPUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hopfion_sutcliffe_analytic.ovf")

xmin = -xnodes * dx / 2; xmax = -xmin
ymin = -ynodes * dy / 2; ymax = -ymin
zmin = -znodes * dz / 2; zmax = -zmin

header = f"""# OOMMF OVF 2.0
# Segment count: 1
# Begin: Segment
# Begin: Header
# Title: Hopfion Sutcliffe Analytic (eq.3.3)
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
    # OVF binary magic number
    f.write(struct.pack('<f', 1234567.0))
    # Data: iterate z, y, x (OVF order)
    for iz in range(znodes):
        for iy in range(ynodes):
            for ix in range(xnodes):
                f.write(struct.pack('<fff',
                    float(mx[ix, iy, iz]),
                    float(my[ix, iy, iz]),
                    float(mz[ix, iy, iz])
                ))
    f.write(b"\n# End: Data Binary 4\n# End: Segment\n")

print(f"Saved: {OUTPUT}")
