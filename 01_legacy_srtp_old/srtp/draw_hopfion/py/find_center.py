# find_center.py
import sys
import numpy as np
import discretisedfield as df
from sklearn.decomposition import PCA
from scipy.optimize import least_squares

def circle_fit_residuals(params, points):
    """用于圆形拟合的残差函数"""
    xc, yc, R = params
    x, y = points[:, 0], points[:, 1]
    return np.sqrt((x - xc)**2 + (y - yc)**2) - R

def find_hopfion_center(m_field):
    """
    通过定位拓扑原像(mz ≈ -1)的几何中心来精确计算Hopfion的中心点。
    """
    # 1. 定位原像 (mz ≈ -1 的区域)
    mz = m_field.array[..., 2]
    preimage_mask = mz < -0.95 
    
    if not np.any(preimage_mask):
        return None # 如果找不到原像，则返回None
        
    preimage_coords_grid = np.argwhere(preimage_mask)
    dx, dy, dz = m_field.mesh.cell
    
    # 转换为物理坐标 (单位: 米)
    preimage_coords_m = np.stack([
        preimage_coords_grid[:, 2] * dx,
        preimage_coords_grid[:, 1] * dy,
        preimage_coords_grid[:, 0] * dz
    ], axis=1)

    # 2. 计算点云的几何中心 (质心)
    center_point_m = np.mean(preimage_coords_m, axis=0)
    
    # 3. 将结果转换为纳米并返回
    center_point_nm = center_point_m * 1e9
    return center_point_nm

def main(argv):
    """
    主函数，接收一个OVF文件名，计算中心点并打印。
    """
    if len(argv) < 2:
        print("用法: python find_center.py <filename.ovf>")
        return

    ovf_file = argv[1]
    try:
        field = df.Field.from_file(ovf_file)
        center = find_hopfion_center(field)
        
        if center is not None:
            # 以固定的格式打印坐标，方便shell脚本解析
            print(f"{center[0]:.4f} {center[1]:.4f} {center[2]:.4f}")
        else:
            print("NaN NaN NaN") # 如果找不到，输出NaN

    except Exception as e:
        # 打印错误到标准错误流，这样shell可以继续运行
        print(f"处理文件 {ovf_file} 时出错: {e}", file=sys.stderr)
        print("NaN NaN NaN")

if __name__ == '__main__':
    main(sys.argv)