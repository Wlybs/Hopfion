import numpy as np
import os
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import discretisedfield as df
from scipy.ndimage import center_of_mass
from scipy.interpolate import RegularGridInterpolator

def analyze_and_plot_vorticity_normalized(ovf_filename):
    """
    (最终版) 读取OVF，生成一张包含“3D扭转丝带”和标准化的“路径角度图”的
    组合分析图，以最全面、最清晰的方式可视化极向涡旋度 m。
    """
    print(f"--- 正在加载文件 '{ovf_filename}' 以进行最终的组合分析 ---")
    if not os.path.exists(ovf_filename):
        print(f"错误：找不到文件 '{ovf_filename}'。"); return

    try:
        # 使用与您 draw.py 中完全相同的、经过验证的加载方法
        field = df.Field.from_file(ovf_filename)
        print("OVF 文件加载成功！")
    except Exception as e:
        print(f"加载 OVF 文件时发生未知错误: {e}"); return

    # --- 1. 数据提取与插值准备 (公共步骤) ---
    nx, ny, nz = field.mesh.n
    pmin, pmax = field.mesh.region.pmin, field.mesh.region.pmax
    x = np.linspace(pmin[0], pmax[0], nx)
    y = np.linspace(pmin[1], pmax[1], ny)
    z = np.linspace(pmin[2], pmax[2], nz)
    
    interpolator_mx = RegularGridInterpolator((x, y, z), field.array[..., 0])
    interpolator_my = RegularGridInterpolator((x, y, z), field.array[..., 1])
    interpolator_mz = RegularGridInterpolator((x, y, z), field.array[..., 2])

    # --- 2. 自动定位涡旋核并创建路径 (公共步骤) ---
    print("正在自动识别涡旋核并创建分析路径...")
    x_center_index = nx // 2
    m_slice = field.array[x_center_index, :, :, :]
    core_mask = np.abs(m_slice[:, :, 0]) > 0.5
    right_mask = np.copy(core_mask); right_mask[:ny//2, :] = False
    if not np.any(right_mask):
        print("警告：无法清晰地分离出涡旋核。"); return
        
    cy_idx, cz_idx = center_of_mass(right_mask)
    vortex_center_y, vortex_center_z = y[int(cy_idx)], z[int(cz_idx)]
    
    radius = (pmax[1] - pmin[1]) / 6
    num_points = 256
    path_angles_rad = np.linspace(0, 2 * np.pi, num_points)
    path_points_3d = np.zeros((num_points, 3))
    path_points_3d[:, 0] = x[x_center_index]
    path_points_3d[:, 1] = vortex_center_y + radius * np.cos(path_angles_rad)
    path_points_3d[:, 2] = vortex_center_z + radius * np.sin(path_angles_rad)

    # --- 3. 采样磁矩并计算角度 (公共步骤) ---
    print("正在沿路径采样磁矩并计算角度...")
    mx_path = interpolator_mx(path_points_3d)
    my_path = interpolator_my(path_points_3d)
    mz_path = interpolator_mz(path_points_3d)
    m_vectors = np.vstack([mx_path, my_path, mz_path]).T
    
    magnetization_angles_rad = np.arctan2(mz_path, my_path)
    unwrapped_angles_rad = np.unwrap(magnetization_angles_rad)
    
    # --- 核心修改：标准化角度曲线，使其从0开始 ---
    unwrapped_angles_deg = np.rad2deg(unwrapped_angles_rad)
    normalized_angles_deg = unwrapped_angles_deg - unwrapped_angles_deg[0]
    # --- 修改结束 ---
    
    total_rotation_deg = normalized_angles_deg[-1]
    m_vorticity = total_rotation_deg / 360.0

    # --- 4. 开始绘图 ---
    print("正在绘制组合分析图...")
    fig = plt.figure(figsize=(22, 10))
    fig.patch.set_facecolor('white')

    # --- 子图1: 3D 扭转丝带 ---
    ax1 = fig.add_subplot(1, 2, 1, projection='3d')
    ax1.set_facecolor('white')
    ribbon_width = radius / 8
    ribbon_vertices = []
    for i in range(num_points):
        p1 = path_points_3d[i]; m = m_vectors[i]
        path_tangent = path_points_3d[(i + 1) % num_points] - path_points_3d[i]
        width_vector = np.cross(m, path_tangent)
        if np.linalg.norm(width_vector) < 1e-9:
             width_vector = np.cross(m, np.array([1.0, 0.0, 0.0])) if np.abs(m[0]) > 0.9 else np.array([0.0, 1.0, 0.0])
        width_vector /= np.linalg.norm(width_vector)
        v1 = p1 - ribbon_width / 2 * width_vector; v2 = p1 + ribbon_width / 2 * width_vector
        ribbon_vertices.append((v1, v2))
        
    faces = [[ribbon_vertices[i][0], ribbon_vertices[i][1], ribbon_vertices[(i + 1) % num_points][1], ribbon_vertices[(i + 1) % num_points][0]] for i in range(num_points)]
    ribbon_angles_color = np.arctan2(m_vectors[:, 1], m_vectors[:, 0])
    normalized_colors_for_ribbon = (ribbon_angles_color + np.pi) / (2 * np.pi)
    face_colors = plt.cm.hsv(normalized_colors_for_ribbon)
    
    collection = Poly3DCollection(faces, facecolors=face_colors, edgecolor='k', linewidth=0.1)
    ax1.add_collection3d(collection)
    ax1.set_title("3D Twisted Ribbon (Visual Intuition)", fontsize=16)
    ax1.set_xlabel("x (nm)"); ax1.set_ylabel("y (nm)"); ax1.set_zlabel("z (nm)")
    ax1.view_init(elev=30, azim=45)
    all_verts = np.array(ribbon_vertices).reshape(-1, 3)
    xmin, xmax = all_verts[:,0].min(), all_verts[:,0].max()
    ymin, ymax = all_verts[:,1].min(), all_verts[:,1].max()
    zmin, zmax = all_verts[:,2].min(), all_verts[:,2].max()
    padding = radius * 0.2
    ax1.set_xlim(xmin-padding, xmax+padding); ax1.set_ylim(ymin-padding, ymax+padding); ax1.set_zlim(zmin-padding, zmax+padding)
    ax1.set_box_aspect((np.ptp(ax1.get_xlim()), np.ptp(ax1.get_ylim()), np.ptp(ax1.get_zlim())))
    
    # --- 子图2: 标准化的路径角度图 ---
    ax2 = fig.add_subplot(1, 2, 2)
    path_angles_deg = np.rad2deg(path_angles_rad)
    ax2.plot(path_angles_deg, normalized_angles_deg, '-', linewidth=2.5, color='royalblue')
    ax2.set_title(f"Normalized Path Angle Plot (Quantitative Analysis)\nFinal Rotation = {total_rotation_deg:.1f}°  (m ≈ {m_vorticity:.2f})", fontsize=16)
    ax2.set_xlabel("Path Angle along circular loop (°)", fontsize=14)
    ax2.set_ylabel("Total Magnetization Rotation (°)", fontsize=14)
    ax2.grid(True, linestyle='--')
    ax2.set_xticks(np.arange(0, 361, 90))
    y_max = np.ceil(np.abs(total_rotation_deg) / 360) * 360 * np.sign(total_rotation_deg) if total_rotation_deg != 0 else 360
    ax2.set_yticks(np.arange(0, y_max + 1, 360))
    ax2.tick_params(axis='both', which='major', labelsize=12)

    fig.suptitle(f"Comprehensive Poloidal Vorticity (m) Analysis for {os.path.basename(ovf_filename)}", fontsize=20)
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    
    output_filename = os.path.splitext(ovf_filename)[0] + '_comprehensive_analysis.png'
    plt.savefig(output_filename, dpi=300, facecolor='white')
    print(f"组合分析图像已成功保存为: {output_filename}")
    plt.close()

if __name__ == "__main__":
    filename_to_draw = "stable-state-h+1+2_trans_q=2.ovf"
    analyze_and_plot_vorticity_normalized(filename_to_draw)