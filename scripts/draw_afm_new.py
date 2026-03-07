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

# =============== 原有：角度中位数，避免相位跳变 ===============
def angular_median(angles):
    x = np.cos(angles)
    y = np.sin(angles)
    mean_x = np.mean(x, axis=1)
    mean_y = np.mean(y, axis=1)
    median_angles = np.arctan2(mean_y, mean_x)
    return median_angles

# =============== 原有：圆拟合与 R/r 估计 ===============
def circle_fit_residuals(params, points):
    xc, yc, R = params
    x, y = points[:, 0], points[:, 1]
    return np.sqrt((x - xc)**2 + (y - yc)**2) - R

def calculate_hopfion_radii_topological(m_field, core_mz_threshold=0.02):
    """
    [策略一] 使用动态阈值和全等值面平均距离法, 更精确地计算R和r。
    core_mz_threshold: 用于定义核心的动态阈值 (mz < mz_min + threshold)。
    """
    print("正在使用[策略一]改进的拓扑原像法计算R和r...")
    mz = m_field.array[..., 2]

    # --- 1. 精确计算 R ---
    print("步骤1/2: 使用动态阈值计算大半径 R...")
    mz_min = np.min(mz)
    preimage_mask = mz < (mz_min + core_mz_threshold)

    if not np.any(preimage_mask):
        print(f"警告：未找到Hopfion的拓扑原像 (mz ≈ {mz_min:.3f})，无法计算尺寸。")
        return None, None

    # 获取核心点的真实世界坐标
    preimage_coords_grid = np.array(np.where(preimage_mask)).T
    preimage_coords_real = m_field.mesh.region.pmin + preimage_coords_grid * m_field.mesh.cell

    # 对核心的XY投影进行圆形拟合
    xy_coords = preimage_coords_real[:, :2]
    if len(xy_coords) < 3:
        print("警告：找到的核心点太少，无法进行圆形拟合。")
        return None, None
        
    center_guess = np.mean(xy_coords, axis=0)
    radius_guess = np.mean(np.sqrt(np.sum((xy_coords - center_guess)**2, axis=1)))
    
    try:
        res = least_squares(circle_fit_residuals, [center_guess[0], center_guess[1], radius_guess], args=(xy_coords,))
        xc, yc, R_hopfion = res.x
    except Exception as e:
        print(f"错误：对核心环的圆形拟合失败: {e}")
        return None, None

    print(f"核心环拟合完成: 中心≈({xc*1e9:.1f}, {yc*1e9:.1f})nm, R≈{R_hopfion*1e9:.2f}nm")

    # --- 2. 精确计算 r ---
    print("步骤2/2: 使用mz=0等值面到核心环的平均距离计算小半径 r...")
    try:
        # 提取 mz=0 等值面的所有顶点
        verts, _, _, _ = measure.marching_cubes(volume=mz, level=0, spacing=m_field.mesh.cell)
        verts += m_field.mesh.region.pmin
    except (ValueError, RuntimeError) as e:
        print(f"提取mz=0等值面失败: {e}")
        return R_hopfion, None

    if len(verts) == 0:
        print("警告：mz=0等值面不包含任何顶点，无法计算 r。")
        return R_hopfion, None

    # 计算等值面上每个点到核心环的3D距离
    # 核心环的z坐标假定为所有核心点的z坐标平均值
    core_z_center = np.mean(preimage_coords_real[:, 2])
    
    # 计算每个顶点在XY平面上离环心的距离
    dist_xy_from_center = np.sqrt((verts[:, 0] - xc)**2 + (verts[:, 1] - yc)**2)
    
    # 计算每个顶点到核心环的3D距离
    # dist = sqrt( (dist_from_center_in_plane - R)^2 + (z_vert - z_core)^2 )
    distances_to_core_ring = np.sqrt((dist_xy_from_center - R_hopfion)**2 + (verts[:, 2] - core_z_center)**2)
    
    # r 是所有这些距离的平均值
    r_hopfion = np.mean(distances_to_core_ring)

    print(f"计算完成: 大半径 R ≈ {R_hopfion*1e9:.2f} nm, 小半径 r ≈ {r_hopfion*1e9:.2f} nm")
    return R_hopfion, r_hopfion

# =============== 原有：为顶点插值颜色（mx,my → 相位） ===============
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

# =========================== NEW: AFM检测与解调 ===========================
def _avg_neighbor_dot(m):
    """平均相邻单元点积（x/y/z 三方向各一位），衡量场的平滑程度。"""
    mx = []
    for axis in range(3):
        # 与向正方向的邻居点积
        a = m[..., :-1] if axis == 2 else (m[:, :-1, :] if axis == 1 else m[:-1, :, :])
        b = m[..., 1:]  if axis == 2 else (m[:, 1:, :]  if axis == 1 else m[1:, :, :])
        # 对齐到共同子块
        if axis == 0:
            dots = np.sum(a * b, axis=-1)
        elif axis == 1:
            dots = np.sum(a * b, axis=-1)
        else:
            dots = np.sum(a * b, axis=-1)
        mx.append(np.mean(dots))
    return np.array(mx)  # [mean_x, mean_y, mean_z]

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
    """
    粗略自动识别AFM样式：
    - 如果三方向平均邻点点积均 ~ -1 → checker
    - 如果只有某一方向 ~ -1 → layerX/Y/Z
    - 否则返回 None
    """
    avg = _avg_neighbor_dot(m)
    thr_neg = -0.6  # 经验阈值
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
    """
    针对给定mode在8/2种相位起点中搜索，使“解调后”的邻点平均点积最大（最平滑）。
    checker 测 8种 (ox,oy,oz ∈ {0,1}); layer* 测 2种 (沿其轴 0/1)。
    """
    shape = m.shape[:3]
    choices = []
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
    """
    === NEW ===
    将AFM棋盘格/分层交替的场“解调”为连续场，便于等值面与配色。
    afm_hint: "auto" | "checker" | "layerX" | "layerY" | "layerZ" | "none"
    offset_hint: None | (int, int, int) 手动指定相位
    返回：新的 Field（array 已解调），以及使用的 (mode, offsets)
    """
    arr = m_field.array.copy()  # (nx,ny,nz,3)
    if afm_hint == "none":
        return m_field, ("none",(0,0,0))

    # 1) 确定模式
    if afm_hint == "auto":
        mode = _auto_detect_afm_mode(arr)
        if mode is None:
            print("未检测到典型AFM模式（将按 'none' 处理）。")
            return m_field, ("none",(0,0,0))
        print(f"检测到 AFM 模式：{mode}")
    else:
        mode = afm_hint
        print(f"使用指定的 AFM 模式：{mode}")

    # 2) 搜索或使用指定的相位起点
    if offset_hint is not None:
        offsets = offset_hint
        print(f"使用指定的 AFM 解调相位 offsets = {offsets}")
    else:
        offsets = _best_phase_for_mode(arr, mode)
        print(f"自动检测到 AFM 解调相位 offsets = {offsets}")

    # 3) 构建符号场并解调
    sign = _build_sign_field(arr.shape[:3], mode, offsets).astype(arr.dtype)[..., None]
    arr_demod = arr * sign

    # 4) 生成新的 Field（同 mesh，换 array）
    m_demod = df.Field(mesh=m_field.mesh, nvdim=3, value=0)
    m_demod.array[...] = arr_demod
    return m_demod, (mode, offsets)

# =========================== 绘制（改为对解调后字段） ===========================
def draw_isosurface(ovf_filename, R_hopfion, r_hopfion, m_field, title_info=""):
    # 读取原始AFM场
    # raw_field = df.Field.from_file(ovf_filename)

    # === NEW: AFM 解调 ===
    # m_field, (mode, offsets) = demodulate_afm(raw_field, afm_hint=afm_hint, offset_hint=offset_hint)

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
    mesh = Poly3DCollection(verts[faces]*1e9)
    mesh.set_facecolor(face_colors)
    ax.add_collection3d(mesh)

    ax.set_xlim(verts[:, 0].min()*1e9, verts[:, 0].max()*1e9)
    ax.set_ylim(verts[:, 1].min()*1e9, verts[:, 1].max()*1e9)
    ax.set_zlim(verts[:, 2].min()*1e9, verts[:, 2].max()*1e9)
    ax.set_xlabel("x (nm)")
    ax.set_ylabel("y (nm)")
    ax.set_zlabel("z (nm)")

    title_text = f"Hopfion ({title_info})\n{os.path.basename(ovf_filename)} (mz=0)"
    if R_hopfion is not None and r_hopfion is not None:
        title_text += f"\nEst. R ≈ {R_hopfion*1e9:.2f} nm, r ≈ {r_hopfion*1e9:.2f} nm"
    ax.set_title(title_text)

    axis_limits = np.array([ax.get_xlim(), ax.get_ylim(), ax.get_zlim()])
    ax.set_box_aspect(np.ptp(axis_limits, axis=1))

    sm = plt.cm.ScalarMappable(cmap='hsv', norm=norm)
    cbar = fig.colorbar(sm, ax=ax, shrink=0.6, aspect=20, pad=0.1)
    cbar.set_label(r'Angle $\arctan(m_y/m_x)$')
    cbar.set_ticks([-np.pi, -np.pi/2, 0, np.pi/2, np.pi])
    cbar.set_ticklabels([r'$-\pi$', r'$-\pi/2$', '0', r'$\pi/2$', r'$\pi$'])

    output_filename = os.path.splitext(ovf_filename)[0] + '_strategy1.png'
    plt.savefig(output_filename, dpi=300)
    print(f"图像已成功保存为: {output_filename}")

    print("正在打开可交互的三维图像窗口... (关闭此窗口后程序才会结束)")
    plt.show()
    plt.close()

def main(ovf_files, afm_hint="auto", offset_hint=None):
    print("正在加载OVF文件用于绘图...")
    for ovf_file in ovf_files:
        try:
            # 智能AFM模式提示
            local_afm_hint = afm_hint
            if "afm" in os.path.basename(ovf_file).lower() and local_afm_hint == "auto":
                print("文件名中检测到'AFM'，自动切换到 'checker' 解调模式。")
                local_afm_hint = "checker"

            raw = df.Field.from_file(ovf_file)
            # 执行一次解调
            m_demod, (mode, offsets) = demodulate_afm(raw, afm_hint=local_afm_hint, offset_hint=offset_hint)
            
            # 将解调后的场用于计算
            R, r = calculate_hopfion_radii_topological(m_demod)
            
            # 将解调后的场和信息用于绘图
            title_info = f"demod: {mode}{' '+str(offsets) if mode!='none' else ''}"
            draw_isosurface(ovf_file, R, r, m_demod, title_info=title_info)

        except Exception as e:
            print(f"处理文件 {ovf_file} 时发生严重错误: {e}")

if __name__ == "__main__":
    import sys
    args = sys.argv[1:]
    files = []
    afm_hint = "auto"
    offset_hint = None

    # Simple parser
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--afm":
            if i + 1 < len(args):
                afm_hint = args[i+1].lower()
                i += 1 # Consume next arg
            else:
                print("错误: --afm 参数后需要一个模式 (例如 'checker')")
                sys.exit(1)
        elif arg == "--offset":
            if i + 3 < len(args):
                try:
                    offset_hint = (int(args[i+1]), int(args[i+2]), int(args[i+3]))
                    i += 3 # Consume next 3 args
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
        filename = "m000099.ovf"
        if not os.path.exists(filename):
            print(f"错误：找不到文件 '{filename}'。请将OVF路径作为参数传入。")
            print("用法: python draw_afm.py your.ovf [--afm mode] [--offset x y z]")
            sys.exit(1)
        files = [filename]

    main(files, afm_hint=afm_hint, offset_hint=offset_hint)
