"""
可视化 Hopfion 稳定态，确认拓扑结构
"""
import discretisedfield as df
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import os

BASE = os.path.dirname(os.path.abspath(__file__))
OVF  = os.path.join(BASE, 'run_analytic_relax.out', 'hopfion_analytic_final.ovf')

field = df.Field.from_file(OVF)
arr   = field.array            # (105, 105, 35, 3)
mx, my, mz = arr[..., 0], arr[..., 1], arr[..., 2]

Nx, Ny, Nz = arr.shape[:3]
iz_mid = Nz // 2       # z=0 截面
iy_mid = Ny // 2       # y=0 截面

fig, axes = plt.subplots(1, 3, figsize=(15, 5))

# ---- 图1: z=0 平面的 mz ----
im1 = axes[0].imshow(mz[:, :, iz_mid].T, origin='lower', cmap='RdBu_r',
                     vmin=-1, vmax=1, extent=[-105, 105, -105, 105])
axes[0].set_title(f'mz at z=0 plane (midplane)\nmz_mean={mz.mean():.3f}')
axes[0].set_xlabel('x (nm)'); axes[0].set_ylabel('y (nm)')
plt.colorbar(im1, ax=axes[0], label='mz')
# 圆盘边界
theta_c = np.linspace(0, 2*np.pi, 200)
axes[0].plot(105*np.cos(theta_c), 105*np.sin(theta_c), 'k--', lw=1, alpha=0.5)

# ---- 图2: y=0 平面的 mz ----
im2 = axes[1].imshow(mz[:, iy_mid, :].T, origin='lower', cmap='RdBu_r',
                     vmin=-1, vmax=1, extent=[-105, 105, -35, 35])
axes[1].set_title('mz at y=0 plane (cross-section)')
axes[1].set_xlabel('x (nm)'); axes[1].set_ylabel('z (nm)')
plt.colorbar(im2, ax=axes[1], label='mz')

# ---- 图3: z=0 平面矢量场（xy 平面内 m 方向）----
step = 5  # 每5格取一个箭头
x_idx = np.arange(0, Nx, step)
y_idx = np.arange(0, Ny, step)
X, Y  = np.meshgrid(x_idx, y_idx, indexing='ij')
U = mx[X, Y, iz_mid]
V = my[X, Y, iz_mid]
mz_sub = mz[X, Y, iz_mid]

# 用 mz 着色箭头
norm_c = mcolors.Normalize(vmin=-1, vmax=1)
cmap   = plt.cm.RdBu_r
im3 = axes[2].imshow(mz[:, :, iz_mid].T, origin='lower', cmap='RdBu_r',
                     vmin=-1, vmax=1, extent=[-105, 105, -105, 105], alpha=0.6)
axes[2].quiver((x_idx - Nx/2)*2, (y_idx - Ny/2)*2, U.T, V.T,
               mz_sub.T, cmap='RdBu_r', norm=norm_c, scale=15, alpha=0.9)
axes[2].set_title('In-plane magnetization at z=0')
axes[2].set_xlabel('x (nm)'); axes[2].set_ylabel('y (nm)')
axes[2].plot(105*np.cos(theta_c), 105*np.sin(theta_c), 'k--', lw=1, alpha=0.5)
plt.colorbar(im3, ax=axes[2], label='mz')

plt.suptitle('Bloch Hopfion in FeGe Nanocylinder (d=210nm, h=70nm)\n'
             'Sutcliffe analytic ansatz → Relax() + 2ns Run, EnableDemag=True',
             fontsize=11)
plt.tight_layout()
out = os.path.join(BASE, 'hopfion_visualization.png')
plt.savefig(out, dpi=150)
print(f"Saved: {out}")

# 打印关键统计
print(f"\nmz statistics:")
print(f"  mean = {mz.mean():.4f}")
print(f"  min  = {mz.min():.4f}")
print(f"  max  = {mz.max():.4f}")
print(f"  mz < 0  fraction: {(mz<0).mean():.4f}")
print(f"  mz < -0.5 fraction: {(mz<-0.5).mean():.4f}")
print(f"\nHopfion core ring: mz = -1 region at z=0 plane")
iz = iz_mid
mz_mid = mz[:, :, iz]
core_mask = mz_mid < -0.5
if core_mask.any():
    xi, yi = np.where(core_mask)
    x_nm = (xi - Nx/2) * 2
    y_nm = (yi - Ny/2) * 2
    r_core = np.sqrt(x_nm**2 + y_nm**2)
    print(f"  Core ring radius (approx): {r_core.mean():.1f} ± {r_core.std():.1f} nm")
