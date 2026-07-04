"""
Wang 2019 PRL 动力学分析脚本
- 追踪 Hopfion 质心轨迹
- 计算速度（沿 x / 横向霍尔偏转）
- 复现 Fig. 3 轨迹图
"""

import os
import sys
import numpy as np
import matplotlib.pyplot as plt
import glob

# 激活虚拟环境后才能 import discretisedfield
try:
    import discretisedfield as df
except ImportError:
    print("错误：请先激活虚拟环境：source /mnt/d/Research/Hopfion/hopfion/bin/activate")
    sys.exit(1)


def find_hopfion_center(field: df.Field):
    """
    通过 mz 最小值区域质心定位 Hopfion 中心
    Hopfion 核心: mz → -1
    """
    mz = field.z.array.squeeze()   # shape (Nx, Ny, Nz) 或 (Nz, Ny, Nx)
    # 阈值: mz < -0.5
    mask = mz < -0.5
    if mask.sum() == 0:
        return None

    # 格点坐标
    mesh = field.mesh
    cx = np.average(mesh.cells.x, weights=mask.sum(axis=(1,2)) if mz.ndim==3 else mask)

    # 用质心公式
    iz, iy, ix = np.indices(mz.shape)
    total = mask.sum()
    cx_idx = (ix * mask).sum() / total
    cy_idx = (iy * mask).sum() / total
    cz_idx = (iz * mask).sum() / total

    # 转换为物理坐标
    dx = mesh.cell[0]; dy = mesh.cell[1]; dz = mesh.cell[2]
    x0 = mesh.region.pmin[0]; y0 = mesh.region.pmin[1]; z0 = mesh.region.pmin[2]
    return (x0 + (cx_idx + 0.5) * dx,
            y0 + (cy_idx + 0.5) * dy,
            z0 + (cz_idx + 0.5) * dz)


def load_ovf_sequence(pattern):
    """加载 OVF 序列，返回 (时间列表, 场列表)"""
    files = sorted(glob.glob(pattern))
    if not files:
        print(f"未找到文件: {pattern}")
        return [], []

    print(f"找到 {len(files)} 个 OVF 文件")
    fields = []
    for fp in files:
        try:
            fields.append(df.Field.from_file(fp))
        except Exception as e:
            print(f"  跳过 {fp}: {e}")
    return files, fields


def extract_time_from_table(table_path):
    """从 Mumax3 table.txt 提取时间列"""
    if not os.path.exists(table_path):
        return None
    data = np.loadtxt(table_path, skiprows=1)
    return data[:, 0] if data.ndim == 2 else None


def main():
    # 输出目录（STT 仿真的 .out 目录）
    sim_dir = sys.argv[1] if len(sys.argv) > 1 else "."

    ovf_pattern = os.path.join(sim_dir, "m*.ovf")
    table_path  = os.path.join(sim_dir, "table.txt")

    print(f"分析目录: {sim_dir}")
    files, fields = load_ovf_sequence(ovf_pattern)

    if not fields:
        print("未加载到有效的 OVF 文件，退出。")
        return

    # 质心追踪
    times  = []
    cx_arr = []
    cy_arr = []

    for i, fld in enumerate(fields):
        center = find_hopfion_center(fld)
        if center is not None:
            cx_arr.append(center[0] * 1e9)   # nm
            cy_arr.append(center[1] * 1e9)   # nm
        else:
            cx_arr.append(np.nan)
            cy_arr.append(np.nan)
        times.append(i * 0.05)  # 每 50ps 一帧（与 autosave 对应）

    cx_arr = np.array(cx_arr)
    cy_arr = np.array(cy_arr)
    t_arr  = np.array(times)   # ns

    # 计算速度（线性拟合）
    valid = ~np.isnan(cx_arr)
    if valid.sum() >= 2:
        vx = np.polyfit(t_arr[valid], cx_arr[valid], 1)[0]  # nm/ns = m/s
        vy = np.polyfit(t_arr[valid], cy_arr[valid], 1)[0]
        print(f"\nHopfion 速度: vx = {vx:.2f} nm/ns,  vy(Hall) = {vy:.2f} nm/ns")
        print(f"霍尔角: θ_H = {np.degrees(np.arctan2(abs(vy), abs(vx))):.2f}°  (Wang 预期 ≈ 0°)")
    else:
        print("有效数据点不足，无法拟合速度。")

    # ── 绘图 ──
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    axes[0].plot(t_arr, cx_arr, 'b-o', ms=3, label='x 坐标')
    axes[0].set_xlabel('时间 (ns)'); axes[0].set_ylabel('质心 x (nm)')
    axes[0].set_title('Hopfion 沿 x 方向传播 (Wang Fig. 3)')
    axes[0].legend()

    axes[1].plot(cx_arr, cy_arr, 'r-o', ms=3)
    axes[1].set_xlabel('x (nm)'); axes[1].set_ylabel('y (nm)')
    axes[1].set_title('轨迹 (无霍尔效应 → 直线)')
    axes[1].set_aspect('equal')

    plt.tight_layout()
    out_path = os.path.join(os.path.dirname(__file__), '../results/STT_trajectory.png')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    plt.savefig(out_path, dpi=150)
    print(f"\n图已保存: {out_path}")
    plt.show()


if __name__ == '__main__':
    main()
