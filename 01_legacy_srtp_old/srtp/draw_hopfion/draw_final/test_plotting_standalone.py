import os
import sys
import glob
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from skimage import measure
from matplotlib.colors import Normalize
import discretisedfield as df
from scipy.optimize import least_squares
from scipy.ndimage import map_coordinates

# ==============================================================================
# --- 绘图与分析功能模块 (提取自 run_full_workflow.py) --- 
# ==============================================================================

def angular_median(angles):
    """计算角度的中位数，避免颜色在-pi到pi跳变时出现问题"""
    x = np.cos(angles)
    y = np.sin(angles)
    mean_x = np.mean(x, axis=1)
    mean_y = np.mean(y, axis=1)
    return np.arctan2(mean_y, mean_x)

def circle_fit_residuals(params, points):
    """用于圆形拟合的残差函数"""
    xc, yc, R = params
    x, y = points[:, 0], points[:, 1]
    return np.sqrt((x - xc)**2 + (y - yc)**2) - R

def calculate_hopfion_radii_topological(m_field, core_mz_threshold=0.02):
    """使用拓扑原像法计算R和r (来自 AFM/draw_afm_new.py 的正确算法)"""
    print("  [分析] 正在使用拓扑原像法计算R和r...")
    mz = m_field.array[..., 2]
    mz_min = np.min(mz)
    preimage_mask = mz < (mz_min + core_mz_threshold)

    if not np.any(preimage_mask):
        print("  [分析警告] 未找到拓扑原像，无法计算尺寸。")
        return None, None

    preimage_coords_grid = np.array(np.where(preimage_mask)).T
    preimage_coords_real = m_field.mesh.region.pmin + preimage_coords_grid * m_field.mesh.cell
    xy_coords = preimage_coords_real[:, :2]

    if len(xy_coords) < 3:
        print("  [分析警告] 核心点太少，无法进行圆形拟合。")
        return None, None
        
    center_guess = np.mean(xy_coords, axis=0)
    radius_guess = np.mean(np.sqrt(np.sum((xy_coords - center_guess)**2, axis=1)))
    
    try:
        res = least_squares(circle_fit_residuals, [center_guess[0], center_guess[1], radius_guess], args=(xy_coords,))
        xc, yc, R_hopfion = res.x
    except Exception as e:
        print(f"  [分析错误] 核心环圆形拟合失败: {e}")
        return None, None

    try:
        verts, _, _, _ = measure.marching_cubes(volume=mz, level=0, spacing=m_field.mesh.cell)
        verts += m_field.mesh.region.pmin
    except (ValueError, RuntimeError):
        return R_hopfion, None

    if len(verts) == 0:
        return R_hopfion, None

    core_z_center = np.mean(preimage_coords_real[:, 2])
    dist_xy_from_center = np.sqrt((verts[:, 0] - xc)**2 + (verts[:, 1] - yc)**2)
    distances_to_core_ring = np.sqrt((dist_xy_from_center - R_hopfion)**2 + (verts[:, 2] - core_z_center)**2)
    r_hopfion = np.mean(distances_to_core_ring)
    
    print(f"  [分析] 计算完成: R≈{R_hopfion*1e9:.2f}nm, r≈{r_hopfion*1e9:.2f}nm")
    return R_hopfion, r_hopfion

def interpolate_colors_for_vertices(m_field, verts):
    """为等值面顶点插值计算颜色"""
    indices = (verts - m_field.mesh.region.pmin) / m_field.mesh.cell
    mx_interp = map_coordinates(m_field.array[..., 0], indices.T, order=1, mode='nearest')
    my_interp = map_coordinates(m_field.array[..., 1], indices.T, order=1, mode='nearest')
    return np.arctan2(my_interp, mx_interp)

def _build_sign_field(shape, mode, offsets=(0,0,0)):
    """构建AFM解调用的符号场"""
    nx, ny, nz = shape[:3]
    ix, iy, iz = np.ogrid[0:nx, 0:ny, 0:nz]
    ox, oy, oz = offsets
    if mode == "checker": return 1 - 2 * (((ix+ox) + (iy+oy) + (iz+oz)) % 2)
    if mode == "layerX": return 1 - 2 * ((ix+ox) % 2)
    if mode == "layerY": return 1 - 2 * ((iy+oy) % 2)
    if mode == "layerZ": return 1 - 2 * ((iz+oz) % 2)
    return np.ones((nx, ny, nz), dtype=np.int8)

def demodulate_afm(m_field, afm_hint="auto"):
    """简化的AFM解调逻辑 (来自 run_full_workflow.py)"""
    if afm_hint == "none": return m_field, ("none", (0,0,0))
    mode = "checker" 
    sign = _build_sign_field(m_field.array.shape[:3], mode, (0,0,0)).astype(m_field.dtype)[..., None]
    m_demod = df.Field(mesh=m_field.mesh, nvdim=3, value=m_field.array * sign)
    return m_demod, (mode, (0,0,0))

def draw_isosurface(ovf_filename, R_hopfion, r_hopfion, m_field, title_info=""):
    """
    核心绘图函数，包含 step_size=2 优化和已修复的标签
    """
    print("  [绘图] 正在生成等值面 (使用 step_size=2 快速模式)...")
    try:
        verts, faces, _, _ = measure.marching_cubes(
            volume=m_field.array[..., 2], 
            level=0, 
            spacing=m_field.mesh.cell,
            step_size=2  # 快速绘图的关键
        )
        verts += m_field.mesh.region.pmin
    except Exception as e:
        print(f"  [绘图错误] Marching Cubes 执行失败: {e}")
        return

    if len(verts) == 0:
        print("  [绘图警告] Marching Cubes 未生成任何顶点。")
        return

    face_angles = interpolate_colors_for_vertices(m_field, verts)[faces]
    median_face_angles = angular_median(face_angles)
    norm = Normalize(vmin=-np.pi, vmax=np.pi)
    face_colors = plt.cm.hsv(norm(median_face_angles))

    print("  [绘图] 正在渲染3D图像...")
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')
    mesh = Poly3DCollection(verts[faces]*1e9)
    mesh.set_facecolor(face_colors)
    ax.add_collection3d(mesh)

    ax.set_xlim(verts[:, 0].min()*1e9, verts[:, 0].max()*1e9)
    ax.set_ylim(verts[:, 1].min()*1e9, verts[:, 1].max()*1e9)
    ax.set_zlim(verts[:, 2].min()*1e9, verts[:, 2].max()*1e9)
    ax.set_xlabel("x (nm)"), ax.set_ylabel("y (nm)"), ax.set_zlabel("z (nm)")

    title_text = f"Hopfion (mz=0) - {title_info}\n{os.path.basename(ovf_filename)}"
    if R_hopfion is not None:
        r_str = f"{r_hopfion*1e9:.2f}" if r_hopfion is not None else "?"
        title_text += f"\nEst. R≈{R_hopfion*1e9:.2f}nm, r≈{r_str}nm"
    ax.set_title(title_text)

    ax.set_box_aspect(np.ptp(np.array([ax.get_xlim(), ax.get_ylim(), ax.get_zlim()]), axis=1))
    sm = plt.cm.ScalarMappable(cmap='hsv', norm=norm)
    cbar = fig.colorbar(sm, ax=ax, shrink=0.6, aspect=20, pad=0.1)
    cbar.set_label('Angle arctan(my/mx)')
    cbar.set_ticks([-np.pi, -np.pi/2, 0, np.pi/2, np.pi])
    # 使用已修复的纯文本标签
    cbar.set_ticklabels(['-pi', '-pi/2', '0', 'pi/2', 'pi'])
    
    # 新的文件名逻辑：保存在当前运行目录，并用源文件夹和文件名组合以避免覆盖
    out_dir_name = os.path.basename(os.path.dirname(ovf_filename))
    ovf_stem = os.path.splitext(os.path.basename(ovf_filename))[0]
    output_filename = f"{out_dir_name}_{ovf_stem}.png"
    
    plt.savefig(output_filename, dpi=250)
    print(f"  [绘图] 图像已保存到: {output_filename}")
    # plt.show() # 在测试脚本中，我们打开交互窗口方便查看
    plt.close(fig)

# ==============================================================================
# --- 主控制流程 (用于独立运行) --- 
# ==============================================================================

def main(ovf_files_to_process):
    """主函数，循环处理传入的OVF文件列表"""
    print("==============================================")
    print("====== 独立绘图功能测试脚本 ======")
    print("==============================================")
    
    if not ovf_files_to_process:
        print("错误: 没有提供任何 .ovf 文件进行处理。")
        print("用法: python test_plotting_standalone.py <文件1.ovf> [文件2.ovf] ...")
        return

    for ovf_file in ovf_files_to_process:
        if not os.path.exists(ovf_file):
            print(f"\n--- 跳过: 文件不存在 '{ovf_file}' ---")
            continue

        print(f"\n--- 正在处理文件: {ovf_file} ---")
        try:
            raw_field = df.Field.from_file(ovf_file)
            
            # 假设需要AFM解调，如果你的测试文件是铁磁的，可以注释掉下面这行
            print("  [预处理] 正在执行AFM解调...")
            demod_field, (mode, offsets) = demodulate_afm(raw_field)
            
            # 使用解调后的场进行计算和绘图
            R, r = calculate_hopfion_radii_topological(demod_field)
            title = f"demod: {mode}{' '+str(offsets) if mode!='none' else 'none'}"
            draw_isosurface(ovf_file, R, r, demod_field, title_info=title)

        except Exception as e:
            print(f"  *** 在处理 {ovf_file} 时发生严重错误: {e}")
            # 可以在这里打印更详细的堆栈跟踪信息用于调试
            # import traceback
            # traceback.print_exc()

    print("\n==============================================")
    print("=== 所有文件处理完毕。 ===")
    print("==============================================")

if __name__ == "__main__":
    files_to_process = sys.argv[1:]
    
    # 如果没有从命令行传入任何文件，则启动自动搜索模式
    if not files_to_process:
        print("未提供文件参数，将自动搜索当前目录下的 *.out 文件夹...")
        
        # 在当前目录下查找所有 .out 文件夹
        out_directories = sorted(glob.glob('*.out'))
        
        if not out_directories:
            print("在当前目录下没有找到任何 .out 文件夹。")
        else:
            print(f"找到了 {len(out_directories)} 个 .out 文件夹，正在查找最新的 .ovf 文件...")
            for out_dir in out_directories:
                # 查找文件夹内所有的 .ovf 文件并排序
                ovf_files = sorted(glob.glob(os.path.join(out_dir, '*.ovf')))
                if ovf_files:
                    # 将最后一个（序号最大）的 .ovf 文件路径添加到处理列表
                    latest_ovf = ovf_files[-1]
                    files_to_process.append(latest_ovf)
                    print(f"  + 已添加: {latest_ovf}")
                else:
                    print(f"  - 在 {out_dir} 中未找到 .ovf 文件，已跳过。")
    
    # 使用最终确定的文件列表调用主处理函数
    main(files_to_process)
