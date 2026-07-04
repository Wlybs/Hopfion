# -*- coding: utf-8 -*-
"""
draw_accurate.py

使用策略三（拓扑荷密度矩方法）精确计算Hopfion的R和r。
这是理论上最鲁棒的计算方法。
"""
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from skimage import measure
from matplotlib.colors import Normalize
import os
import discretisedfield as df
from scipy.optimize import least_squares
from scipy.ndimage import map_coordinates
import sys

# =================== 绘图和AFM解调的辅助函数 (从draw_afm.py复制) ===================

def angular_median(angles):
    x = np.cos(angles)
    y = np.sin(angles)
    mean_x = np.mean(x, axis=1)
    mean_y = np.mean(y, axis=1)
    median_angles = np.arctan2(mean_y, mean_x)
    return median_angles

def circle_fit_residuals(params, points):
    xc, yc, R = params
    x, y = points[:, 0], points[:, 1]
    return np.sqrt((x - xc)**2 + (y - yc)**2) - R

def interpolate_colors_for_vertices(m_field, verts):
    pmin = m_field.mesh.region.pmin
    cell_size = m_field.mesh.cell
    indices = (verts - pmin) / cell_size
    indices = indices.T
    mx_interp = map_coordinates(m_field.array[..., 0], indices, order=1, mode='nearest')
    my_interp = map_coordinates(m_field.array[..., 1], indices, order=1, mode='nearest')
    colors = np.arctan2(my_interp, mx_interp)
    return colors

# (AFM解调相关函数 _avg_neighbor_dot, _build_sign_field, 等等, 在此省略以保持简洁)
# 注意：为运行此脚本，完整的AFM解调函数需要被复制到这里。
# 为了聚焦于策略三，我们暂时假定输入的OVF是已经解调的或非AFM的。
# =========================== AFM检测与解调 (来自 draw_afm_new.py) ===========================
def _avg_neighbor_dot(m):
    """平均相邻单元点积（x/y/z 三方向各一位），衡量场的平滑程度。"""
    mx = []
    for axis in range(3):
        a = m[..., :-1] if axis == 2 else (m[:, :-1, :] if axis == 1 else m[:-1, :, :])
        b = m[..., 1:]  if axis == 2 else (m[:, 1:, :]  if axis == 1 else m[1:, :, :])
        dots = np.sum(a * b, axis=-1)
        mx.append(np.mean(dots))
    return np.array(mx)

def _build_sign_field(shape, mode, offsets=(0,0,0)):
    """根据AFM模式构建(+1/-1)的交替符号场；offsets∈{0,1}^3 允许不同相位起点。"""
    nx, ny, nz = shape[:3]
    ix = np.arange(nx)[:, None, None]
    iy = np.arange(ny)[None, :, None]
    iz = np.arange(nz)[None, None, :]
    ox, oy, oz = offsets
    if mode == "checker":
        sign = 1 - 2 * (((ix+ox) + (iy+oy) + (iz+oz)) % 2)
    elif mode == "layerX":
        sign = 1 - 2 * (((ix+ox) % 2))
    elif mode == "layerY":
        sign = 1 - 2 * (((iy+oy) % 2))
    elif mode == "layerZ":
        sign = 1 - 2 * (((iz+oz) % 2))
    else:
        sign = np.ones((nx, ny, nz), dtype=np.int8)
    return sign

def _auto_detect_afm_mode(m):
    """粗略自动识别AFM样式"""
    avg = _avg_neighbor_dot(m)
    thr_neg = -0.6
    is_neg = avg < thr_neg
    if np.all(is_neg):
        return "checker"
    if is_neg[0] and not is_neg[1] and not is_neg[2]:
        return "layerX"
    if is_neg[1] and not is_neg[0] and not is_neg[2]:
        return "layerY"
    if is_neg[2] and not is_neg[0] and not is_neg[1]:
        return "layerZ"
    return None

def _best_phase_for_mode(m, mode):
    """在所有可能的相位起点中搜索，使“解调后”的场最平滑。"""
    shape = m.shape[:3]
    if mode == "checker":
        offs = [(ox,oy,oz) for ox in (0,1) for oy in (0,1) for oz in (0,1)]
    elif mode == "layerX":
        offs = [(ox,0,0) for ox in (0,1)]
    elif mode == "layerY":
        offs = [(0,oy,0) for oy in (0,1)]
    elif mode == "layerZ":
        offs = [(0,0,oz) for oz in (0,1)]
    else:
        return (0,0,0)

    best_off = None
    best_score = -1e9
    for off in offs:
        sign = _build_sign_field(shape, mode, off).astype(m.dtype)[..., None]
        md = m * sign
        score = _avg_neighbor_dot(md).mean()
        if score > best_score:
            best_score = score
            best_off = off
    return best_off

def demodulate_afm(m_field, afm_hint="auto", offset_hint=None):
    """将AFM场“解调”为连续场，便于分析。"""
    arr = m_field.array.copy()
    if afm_hint == "none":
        return m_field, ("none",(0,0,0))

    if afm_hint == "auto":
        mode = _auto_detect_afm_mode(arr)
        if mode is None:
            print("未检测到典型AFM模式（将按 'none' 处理）。")
            return m_field, ("none",(0,0,0))
        print(f"自动检测到 AFM 模式：{mode}")
    else:
        mode = afm_hint
        print(f"使用指定的 AFM 模式：{mode}")

    if offset_hint is not None:
        offsets = offset_hint
        print(f"使用指定的 AFM 解调相位 offsets = {offsets}")
    else:
        offsets = _best_phase_for_mode(arr, mode)
        print(f"自动检测到 AFM 解调相位 offsets = {offsets}")

    sign = _build_sign_field(arr.shape[:3], mode, offsets).astype(arr.dtype)[..., None]
    arr_demod = arr * sign
    
    m_demod = df.Field(mesh=m_field.mesh, nvdim=3, value=arr_demod)
    return m_demod, (mode, offsets)


# =================== 策略三：拓扑荷密度计算 ===================

def calculate_topological_charge_density(m_field):
    """
    计算三维拓扑荷密度 q。
    q = (1 / 4π) * ∇ ⋅ B, 其中 B_i = (1/2) * ε_ijk * m ⋅ (∂_j m × ∂_k m)
    [修正版：正确处理矢量场的梯度]
    """
    print("正在计算三维拓扑荷密度...")
    m = m_field.array  # 获取矢量场 (nx, ny, nz, 3)
    cell = m_field.mesh.cell
    
    # 1. 将磁化场分解为标量分量
    mx, my, mz = m[..., 0], m[..., 1], m[..., 2]

    # 2. 计算每个分量对每个坐标的偏导数（总共9个）
    # Gradient along x
    dmx_dx = np.gradient(mx, cell[0], axis=0)
    dmy_dx = np.gradient(my, cell[0], axis=0)
    dmz_dx = np.gradient(mz, cell[0], axis=0)
    # Gradient along y
    dmx_dy = np.gradient(mx, cell[1], axis=1)
    dmy_dy = np.gradient(my, cell[1], axis=1)
    dmz_dy = np.gradient(mz, cell[1], axis=1)
    # Gradient along z
    dmx_dz = np.gradient(mx, cell[2], axis=2)
    dmy_dz = np.gradient(my, cell[2], axis=2)
    dmz_dz = np.gradient(mz, cell[2], axis=2)

    # 3. 重建梯度矢量场
    # dm/dx = (dmx/dx, dmy/dx, dmz/dx)
    dm_dx = np.stack([dmx_dx, dmy_dx, dmz_dx], axis=-1)
    dm_dy = np.stack([dmx_dy, dmy_dy, dmz_dy], axis=-1)
    dm_dz = np.stack([dmx_dz, dmy_dz, dmz_dz], axis=-1)

    # 4. 计算所谓的“应急磁场” B (emergent magnetic field)
    # Bx = m ⋅ (∂y m × ∂z m)
    # By = m ⋅ (∂z m × ∂x m)
    # Bz = m ⋅ (∂x m × ∂y m)
    # np.sum(A * B, axis=-1) 用于计算点积
    B_x = np.sum(m * np.cross(dm_dy, dm_dz, axisa=-1, axisb=-1), axis=-1)
    B_y = np.sum(m * np.cross(dm_dz, dm_dx, axisa=-1, axisb=-1), axis=-1)
    B_z = np.sum(m * np.cross(dm_dx, dm_dy, axisa=-1, axisb=-1), axis=-1)
    
    # 5. 计算 B 场的散度 ∇ ⋅ B
    dBx_dx = np.gradient(B_x, cell[0], axis=0)
    dBy_dy = np.gradient(B_y, cell[1], axis=1)
    dBz_dz = np.gradient(B_z, cell[2], axis=2)
    
    div_B = dBx_dx + dBy_dy + dBz_dz
    
    # 6. 计算拓扑荷密度 q
    # 预因子是 1/(4*pi)，但有时为了数值稳定性或方便，会省略。这里保留以保证物理意义正确。
    q = div_B / (4 * np.pi)
    
    print("拓扑荷密度计算完成。")
    return q


def calculate_radii_from_charge_density(m_field):
    """
    [策略三] 基于拓扑荷密度q的矩来计算R，并结合mz=0等值面计算r。
    [v2: 增加q值过滤以提高鲁棒性]
    """
    print("正在使用[策略三]拓扑荷密度矩方法计算R和r...")
    
    # --- 1. 计算拓扑荷密度 q ---
    q = calculate_topological_charge_density(m_field)
    
    # 获取网格坐标
    coord_array = m_field.mesh.coordinate_field().array
    xv, yv, zv = coord_array[..., 0], coord_array[..., 1], coord_array[..., 2]

    # --- 1.5. 过滤q以处理数值噪音 ---
    print("步骤1.5/3: 过滤拓扑荷密度以消除数值噪音...")
    q_pos_sum = np.sum(q[q > 0])
    q_neg_sum = np.abs(np.sum(q[q < 0]))

    # 假设主导符号是正确的Hopfion核心符号
    if q_pos_sum >= q_neg_sum:
        print("主荷密度为正。将忽略负值区域。")
        q_filtered = np.where(q > 0, q, 0)
    else:
        print("主荷密度为负。将忽略正值区域。")
        q_filtered = np.where(q < 0, q, 0)
    
    # --- 2. 将 q_filtered 作为权重, 计算 R ---
    print("步骤2/3: 使用过滤后的荷密度的一阶和二阶矩计算大半径 R...")
    q_total = np.sum(q_filtered)
    
    if np.abs(q_total) < 1e-3:
        print(f"警告：过滤后的总拓扑荷 ({q_total:.4f}) 接近于零，无法进行可靠计算。")
        return None, None
        
    # 计算Hopfion的中心 (x, y)
    xc = np.sum(xv * q_filtered) / q_total
    yc = np.sum(yv * q_filtered) / q_total
    
    # 计算 R^2 = <(x-xc)^2 + (y-yc)^2>_q
    moment_xy = np.sum(((xv - xc)**2 + (yv - yc)**2) * q_filtered)
    R_hopfion_sq = moment_xy / q_total
    
    if R_hopfion_sq < 0:
        print(f"警告：即使在过滤后，计算出的 R^2 仍为负数 ({R_hopfion_sq:.4f})。计算失败。")
        return None, None
        
    R_hopfion = np.sqrt(R_hopfion_sq)
    
    print(f"拓扑荷中心≈({xc*1e9:.1f}, {yc*1e9:.1f})nm, R≈{R_hopfion*1e9:.2f}nm")

    # --- 3. 使用混合方法计算 r ---
    print("步骤3/3: 使用mz=0等值面到核心环的平均距离计算小半径 r...")
    try:
        mz = m_field.array[..., 2]
        verts, _, _, _ = measure.marching_cubes(volume=mz, level=0, spacing=m_field.mesh.cell)
        verts += m_field.mesh.region.pmin
    except (ValueError, RuntimeError) as e:
        print(f"提取mz=0等值面失败: {e}")
        return R_hopfion, None

    if len(verts) == 0:
        print("警告：mz=0等值面不包含任何顶点，无法计算 r。")
        return R_hopfion, None

    # 核心环的z坐标假定为拓扑荷密度的z坐标质心
    zc = np.sum(zv * q_filtered) / q_total
    
    dist_xy_from_center = np.sqrt((verts[:, 0] - xc)**2 + (verts[:, 1] - yc)**2)
    distances_to_core_ring = np.sqrt((dist_xy_from_center - R_hopfion)**2 + (verts[:, 2] - zc)**2)
    
    r_hopfion = np.mean(distances_to_core_ring)

    print(f"计算完成: 大半径 R ≈ {R_hopfion*1e9:.2f} nm, 小半径 r ≈ {r_hopfion*1e9:.2f} nm")
    return R_hopfion, r_hopfion


# =================== 主函数和绘图 ===================

def draw_isosurface(ovf_filename, R_hopfion, r_hopfion, m_field, title_info=""):
    """修改过的绘图函数，直接接收m_field对象和标题信息"""
    print("正在计算mz=0等值面 (Marching Cubes)...")
    verts, faces, _, _ = measure.marching_cubes(volume=m_field.array[..., 2], level=0, spacing=m_field.mesh.cell)
    verts += m_field.mesh.region.pmin

    vertex_colors_angles = interpolate_colors_for_vertices(m_field, verts)

    print("正在为面片计算正确的颜色...")
    face_angles = vertex_colors_angles[faces]
    median_face_angles = angular_median(face_angles)
    norm = Normalize(vmin=-np.pi, vmax=np.pi)
    face_colors = plt.cm.hsv(norm(median_face_angles))

    print("正在进行三维渲染...")
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')
    mesh = Poly3DCollection(verts[faces] * 1e9)
    mesh.set_facecolor(face_colors)
    ax.add_collection3d(mesh)

    ax.set_xlim(verts[:, 0].min()*1e9, verts[:, 0].max()*1e9)
    ax.set_ylim(verts[:, 1].min()*1e9, verts[:, 1].max()*1e9)
    ax.set_zlim(verts[:, 2].min()*1e9, verts[:, 2].max()*1e9)

    ax.set_xlabel("x (nm)")
    ax.set_ylabel("y (nm)")
    ax.set_zlabel("z (nm)")
    ax.set_box_aspect(np.ptp(np.array([ax.get_xlim(), ax.get_ylim(), ax.get_zlim()]), axis=1))

    title_text = f"Hopfion (Accurate method: {title_info})\n{os.path.basename(ovf_filename)}"
    if R_hopfion is not None and r_hopfion is not None:
        title_text += f"\nEst. R ≈ {R_hopfion*1e9:.2f} nm, r ≈ {r_hopfion*1e9:.2f} nm"
    ax.set_title(title_text)
    
    # Colorbar
    sm = plt.cm.ScalarMappable(cmap='hsv', norm=norm)
    cbar = fig.colorbar(sm, ax=ax, shrink=0.6, aspect=20, pad=0.1)
    cbar.set_label(r'Angle $\arctan(m_y/m_x)$')
    cbar.set_ticks([-np.pi, -np.pi/2, 0, np.pi/2, np.pi])
    cbar.set_ticklabels([r'$-\pi$', r'$-\pi/2$', '0', r'$\pi/2$', r'$\pi$'])

    output_filename = os.path.splitext(ovf_filename)[0] + '_accurate.png'
    plt.savefig(output_filename, dpi=300)
    print(f"图像已成功保存为: {output_filename}")
    plt.show()

def main(ovf_files, afm_hint="auto", offset_hint=None):
    print("正在加载OVF文件用于精确绘图...")
    for ovf_file in ovf_files:
        try:
            # 智能AFM模式提示
            local_afm_hint = afm_hint
            if "afm" in os.path.basename(ovf_file).lower() and local_afm_hint == "auto":
                print("文件名中检测到'AFM'，自动切换到 'checker' 解调模式。")
                local_afm_hint = "checker"

            raw_field = df.Field.from_file(ovf_file)
            # 执行一次解调
            m_demod, (mode, offsets) = demodulate_afm(raw_field, afm_hint=local_afm_hint, offset_hint=offset_hint)
            
            # 将解调后的场用于计算
            R, r = calculate_radii_from_charge_density(m_demod)
            
            if R is not None:
                # 将解调后的场和信息用于绘图
                title_info = f"demod: {mode}{' '+str(offsets) if mode!='none' else ''}"
                draw_isosurface(ovf_file, R, r, m_demod, title_info=title_info)
            else:
                print(f"未能计算文件 {ovf_file} 的尺寸，跳过绘图。")

        except Exception as e:
            print(f"处理文件 {ovf_file} 时发生严重错误: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    args = sys.argv[1:]
    files = []
    afm_hint = "auto"
    offset_hint = None

    # 命令行参数解析器
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--afm":
            if i + 1 < len(args):
                afm_hint = args[i+1].lower()
                i += 1
            else:
                print("错误: --afm 参数后需要一个模式 (例如 'checker')")
                sys.exit(1)
        elif arg == "--offset":
            if i + 3 < len(args):
                try:
                    offset_hint = (int(args[i+1]), int(args[i+2]), int(args[i+3]))
                    i += 3
                except ValueError:
                    print("错误: --offset 参数需要三个整数 (例如 '0 0 0')")
                    sys.exit(1)
            else:
                print("错误: --offset 参数需要三个整数 (例如 '0 0 0')")
                sys.exit(1)
        else:
            files.append(arg)
        i += 1

    if not files:
        filename = "hopfion_Qh2_AFM_test_stable.ovf"
        if os.path.exists(filename):
            print(f"未提供文件，将尝试使用默认文件: {filename}")
            files = [filename]
        else:
            print(f"错误：找不到默认文件 '{filename}'。请将OVF路径作为参数传入。")
            print("用法: python draw_accurate.py your.ovf [--afm mode] [--offset x y z]")
            sys.exit(1)

    main(files, afm_hint=afm_hint, offset_hint=offset_hint)
