import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from skimage import measure
from matplotlib.colors import Normalize
import os
import discretisedfield as df
from sklearn.decomposition import PCA
from scipy.optimize import least_squares
from scipy.ndimage import map_coordinates

# --- 新增的辅助函数 ---
def angular_median(angles):
    """
    正确计算一组角度的中位数，处理-pi到+pi的周期性问题。
    """
    # 将角度转换为复平面上的点
    x = np.cos(angles)
    y = np.sin(angles)
    # 计算平均点
    mean_x = np.mean(x, axis=1)
    mean_y = np.mean(y, axis=1)
    # 将平均点转换回角度
    median_angles = np.arctan2(mean_y, mean_x)
    return median_angles

# --- (circle_fit_residuals 和 calculate_hopfion_radii_topological 函数保持不变) ---
def circle_fit_residuals(params, points):
    xc, yc, R = params
    x, y = points[:, 0], points[:, 1]
    return np.sqrt((x - xc)**2 + (y - yc)**2) - R

def calculate_hopfion_radii_topological(m_field):
    print("正在使用基于拓扑的混合方法精确计算R和r...")
    mz = m_field.array[..., 2]
    preimage_mask = mz < -0.95
    if not np.any(preimage_mask):
        print("警告：未找到Hopfion的拓扑原像 (mz ≈ -1)，无法计算尺寸。")
        return None, None
    preimage_coords_grid = np.array(np.where(preimage_mask)).T
    preimage_coords_real = m_field.mesh.region.pmin + preimage_coords_grid * m_field.mesh.cell
    pca = PCA(n_components=2)
    xy_coords = pca.fit_transform(preimage_coords_real)
    center_guess = np.mean(xy_coords, axis=0)
    radius_guess = np.mean(np.sqrt(np.sum((xy_coords - center_guess)**2, axis=1)))
    res = least_squares(circle_fit_residuals, [center_guess[0], center_guess[1], radius_guess], args=(xy_coords,))
    R_hopfion = res.x[2]
    print("正在提取mz=0等值面用于计算r...")
    try:
        verts, faces, _, _ = measure.marching_cubes(volume=mz, level=0, spacing=m_field.mesh.cell)
        verts += m_field.mesh.region.pmin
    except (ValueError, RuntimeError) as e:
        print(f"提取等值面失败: {e}")
        return R_hopfion, None
    num_slices = 16
    r_estimates = []
    for i in range(num_slices):
        angle = 2 * np.pi * i / num_slices
        normal = np.array([np.cos(angle), np.sin(angle), 0])
        dist = verts @ normal
        slice_indices = np.where(np.abs(dist) < m_field.mesh.cell[0] * 1.5)[0]
        if len(slice_indices) < 10: continue
        slice_verts = verts[slice_indices]
        z_coords = slice_verts[:, 2]
        rho_coords = np.sqrt(slice_verts[:, 0]**2 + slice_verts[:, 1]**2)
        slice_2d = np.vstack([rho_coords, z_coords]).T
        center_guess = np.array([R_hopfion, 0])
        radius_guess = np.mean(np.sqrt(np.sum((slice_2d - center_guess)**2, axis=1)))
        res = least_squares(circle_fit_residuals, [center_guess[0], center_guess[1], radius_guess], args=(slice_2d,))
        r_estimates.append(res.x[2])
    r_hopfion = np.mean(r_estimates) if r_estimates else None
    print(f"拓扑方法计算完成: 大半径 R ≈ {R_hopfion*1e9:.2f} nm, 小半径 r ≈ {r_hopfion*1e9:.2f} nm")
    return R_hopfion, r_hopfion

def interpolate_colors_for_vertices(m_field, verts):
    print("正在为顶点计算颜色 (使用插值)...")
    pmin = m_field.mesh.region.pmin
    cell_size = m_field.mesh.cell
    indices = (verts - pmin) / cell_size
    indices = indices.T
    mx_interp = map_coordinates(m_field.array[..., 0], indices, order=1, mode='nearest')
    my_interp = map_coordinates(m_field.array[..., 1], indices, order=1, mode='nearest')
    colors = np.arctan2(my_interp, mx_interp)
    return colors

def draw_isosurface(ovf_filename, R_hopfion, r_hopfion):
    m_field = df.Field.from_file(ovf_filename)
    print("正在计算mz=0等值面 (Marching Cubes)...")
    verts, faces, _, _ = measure.marching_cubes(volume=m_field.array[..., 2], level=0, spacing=m_field.mesh.cell)
    verts += m_field.mesh.region.pmin
    
    vertex_colors_angles = interpolate_colors_for_vertices(m_field, verts)
    
    # --- 关键修改：使用新的中位数函数计算面片颜色 ---
    print("正在为面片计算正确的颜色...")
    face_angles = vertex_colors_angles[faces]
    median_face_angles = angular_median(face_angles)
    
    norm = Normalize(vmin=-np.pi, vmax=np.pi)
    face_colors = plt.cm.hsv(norm(median_face_angles))
    # --- 修改结束 ---

    print("正在进行三维渲染...")
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')
    mesh = Poly3DCollection(verts[faces]*1e9)
    mesh.set_facecolor(face_colors)
    ax.add_collection3d(mesh)
    
    ax.set_xlim(verts[:, 0].min()*1e9, verts[:, 0].max()*1e9)
    ax.set_ylim(verts[:, 1].min()*1e9, verts[:, 1].max()*1e9)
    ax.set_zlim(verts[:, 2].min()*1e9, verts[:, 2].max()*1e9)
    ax.set_xlabel("x (nm)")
    ax.set_ylabel("y (nm)")
    ax.set_zlabel("z (nm)")
    
    title_text = f"Hopfion Structure of {os.path.basename(ovf_filename)} (mz=0)\n"
    if R_hopfion is not None and r_hopfion is not None:
        title_text += f"Est. Major Radius R ≈ {R_hopfion*1e9:.2f} nm, Est. Minor Radius r ≈ {r_hopfion*1e9:.2f} nm"
    ax.set_title(title_text)
    
    axis_limits = np.array([ax.get_xlim(), ax.get_ylim(), ax.get_zlim()])
    ax.set_box_aspect(np.ptp(axis_limits, axis=1))

    sm = plt.cm.ScalarMappable(cmap='hsv', norm=norm)
    cbar = fig.colorbar(sm, ax=ax, shrink=0.6, aspect=20, pad=0.1)
    cbar.set_label(r'Angle $\arctan(m_y/m_x)$')
    cbar.set_ticks([-np.pi, -np.pi/2, 0, np.pi/2, np.pi])
    cbar.set_ticklabels([r'$-\pi$', r'$-\pi/2$', '0', r'$\pi/2$', r'$\pi$'])

    output_filename = os.path.splitext(ovf_filename)[0] + '.png'
    plt.savefig(output_filename, dpi=300)
    print(f"图像已成功保存为: {output_filename}")
    
    # --- 新增功能：显示可交互的图像窗口 ---
    print("正在打开可交互的三维图像窗口... (关闭此窗口后程序才会结束)")
    plt.show()

    plt.close()

def main(ovf_files):
    print("正在加载OVF文件用于绘图...")
    for ovf_file in ovf_files:
        try:
            m_field = df.Field.from_file(ovf_file)
            R, r = calculate_hopfion_radii_topological(m_field)
            draw_isosurface(ovf_file, R, r)
        except Exception as e:
            print(f"处理文件 {ovf_file} 时发生严重错误: {e}")

if __name__ == "__main__":
    filename = "hopfion_Qh=1_disk.ovf"
    if not os.path.exists(filename):
        print(f"错误：找不到文件 '{filename}'。")
    else:
        main([filename])