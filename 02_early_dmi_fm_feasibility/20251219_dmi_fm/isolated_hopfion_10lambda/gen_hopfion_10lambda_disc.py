"""
生成 d=5λ=350nm 圆柱盘的 Hopfion 初始态 OVF

与 successful_simulation/gen_sutcliffe_hopfion.py 的唯一区别:
  - 圆柱直径 3λ=210nm → 5λ=350nm（更孤立，不贴边界）
  - 网格 105×105×35 → 175×175×35

Hopfion 本体不变（由 λ=70nm 决定），新增的区域是纯 FM 背景 mz=+1。
Sutcliffe eq.3.3 公式仍只覆盖 rho < 3λ/2 内的区域。
"""
import numpy as np
import struct
import os

L = 70e-9                        # FeGe 螺旋周期
xnodes, ynodes, znodes = 350, 350, 35   # 700nm / 2nm = 350
dx, dy, dz = 2e-9, 2e-9, 2e-9

x_coords = (np.arange(xnodes) - xnodes/2 + 0.5) * dx
y_coords = (np.arange(ynodes) - ynodes/2 + 0.5) * dy
z_coords = (np.arange(znodes) - znodes/2 + 0.5) * dz

xv, yv, zv = np.meshgrid(x_coords, y_coords, z_coords, indexing='ij')

rho   = np.sqrt(xv**2 + yv**2)
theta = np.arctan2(yv, xv)

z_clip = np.clip(zv, -L/2 * 0.9999, L/2 * 0.9999)

# Sutcliffe 解析公式 (eq. 3.3)
Omega  = np.tan(np.pi * z_clip / L)
sec    = 1.0 / np.cos(np.pi * rho / (2 * L))
sec    = np.clip(sec, -1e6, 1e6)
Xi     = (1.0 + (2 * zv / L)**2) * sec / L
Lambda = Xi**2 * rho**2 + Omega**2 / 4.0
denom  = (1.0 + Lambda)**2

mx = 4 * Xi * rho * (Omega * np.cos(theta) - (Lambda - 1) * np.sin(theta)) / denom
my = 4 * Xi * rho * (Omega * np.sin(theta) + (Lambda - 1) * np.cos(theta)) / denom
mz = 1.0 - 8 * Xi**2 * rho**2 / denom

norm = np.sqrt(mx**2 + my**2 + mz**2)
norm = np.where(norm < 1e-10, 1.0, norm)
mx, my, mz = mx/norm, my/norm, mz/norm

# Sutcliffe 公式有效范围: rho < 3L/2 = 105nm
# 超出范围（包括新增的 105nm→175nm 区域）全部设为 FM 背景 mz=+1
R_formula = 3 * L / 2
mask_outside = rho > R_formula
mx[mask_outside] = 0.0
my[mask_outside] = 0.0
mz[mask_outside] = 1.0

# 顶底层强制 mz=1（与 frozenspins 一致）
mx[:, :, 0]  = 0.0; my[:, :, 0]  = 0.0; mz[:, :, 0]  = 1.0
mx[:, :, -1] = 0.0; my[:, :, -1] = 0.0; mz[:, :, -1] = 1.0

print(f"网格: {xnodes}x{ynodes}x{znodes} @ {dx*1e9:.0f}nm  →  盒子 {xnodes*dx*1e9:.0f}x{ynodes*dy*1e9:.0f}x{znodes*dz*1e9:.0f} nm")
print(f"圆柱直径: {xnodes*dx*1e9:.0f}nm = {xnodes*dx/L:.0f}λ")
print(f"mz mean  = {mz.mean():.4f}")
print(f"mz range = [{mz.min():.4f}, {mz.max():.4f}]")
print(f"Hopfion 核心 (mz<0) 占比: {(mz<0).mean()*100:.1f}%")

OUTPUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hopfion_10lambda_init.ovf")

xmin = -xnodes * dx / 2; xmax = -xmin
ymin = -ynodes * dy / 2; ymax = -ymin
zmin = -znodes * dz / 2; zmax = -zmin

header = f"""# OOMMF OVF 2.0
# Segment count: 1
# Begin: Segment
# Begin: Header
# Title: Hopfion Sutcliffe eq.3.3 in 5lambda disc
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
                    float(mz[ix, iy, iz])
                ))
    f.write(b"\n# End: Data Binary 4\n# End: Segment\n")

print(f"已保存: {OUTPUT}")
