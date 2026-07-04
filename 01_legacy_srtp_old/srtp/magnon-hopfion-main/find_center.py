# find_center.py
import sys
import numpy as np
import discretisedfield as df

# ... (其他代码部分不变) ...

def find_hopfion_center(m_field):
    """
    通过定位拓扑原像(mz ≈ -1)的几何中心来精确计算Hopfion的中心点。
    --- 使用加权质心法以获得亚网格精度 ---
    """
    # 1. 定位原像 (mz ≈ -1 的区域)
    mz = m_field.array[..., 2]
    preimage_mask = mz < -0.95 
    
    if not np.any(preimage_mask):
        return None # 如果找不到原像，则返回None
        
    # 获取满足条件的原像的网格坐标 [z_idx, y_idx, x_idx]
    preimage_coords_grid = np.argwhere(preimage_mask)
    
    # --- 新增代码：获取这些点的 mz 值 ---
    # np.argwhere返回的坐标顺序是(z,y,x)，而array的索引顺序也是(z,y,x)，所以可以直接用
    mz_values_in_preimage = mz[preimage_mask]
    
    # --- 新增代码：计算权重，mz越接近-1，权重越大 ---
    # 我们使用 w = 1 - mz 作为权重
    weights = 1.0 - mz_values_in_preimage

    # 2. 将网格坐标转换为物理坐标 (单位: 米)
    dx, dy, dz = m_field.mesh.cell
    preimage_coords_m = np.stack([
        preimage_coords_grid[:, 2] * dx,
        preimage_coords_grid[:, 1] * dy,
        preimage_coords_grid[:, 0] * dz
    ], axis=1)

    # 3. --- 修改核心：计算点云的“加权”几何中心 ---
    # 使用 np.average 代替之前的 np.mean
    # np.average可以接收一个weights参数
    center_point_m = np.average(preimage_coords_m, axis=0, weights=weights)
    
    return center_point_m

# ... (main 函数等其他部分完全不用变) ...

def main(argv):
    """
    主函数：
    用法1: python find_center.py <filename.ovf>
        -> 输出绝对坐标 (x, y, z)
    用法2: python find_center.py <filename.ovf> <x0> <y0> <z0>
        -> 输出相对位移 (x-x0, y-y0, z-z0)
    """
    if not (len(argv) == 2 or len(argv) == 5):
        print("用法: python find_center.py <filename.ovf> [x0 y0 z0]", file=sys.stderr)
        return

    ovf_file = argv[1]
    try:
        field = df.Field.from_file(ovf_file)
        center = find_hopfion_center(field)
        
        if center is not None:
            # 如果提供了初始坐标，则计算位移
            if len(argv) == 5:
                initial_pos = np.array([float(argv[2]), float(argv[3]), float(argv[4])])
                displacement = center - initial_pos
                print(f"{displacement[0]:.9e} {displacement[1]:.9e} {displacement[2]:.9e}")
            # 否则，打印绝对坐标
            else:
                print(f"{center[0]:.9e} {center[1]:.9e} {center[2]:.9e}")
        else:
            print("NaN NaN NaN") # 如果找不到，输出NaN

    except Exception as e:
        # 打印错误到标准错误流，这样shell可以继续运行
        print(f"处理文件 {ovf_file} 时出错: {e}", file=sys.stderr)
        print("NaN NaN NaN")

if __name__ == '__main__':
    main(sys.argv)