"""
draw_hopfion.py — Hopfion 三维等值面可视化

读取 OVF 磁化场文件，自动（或手动）解调 AFM 交替背景后：
  1. 自动识别背景磁化所沿的轴（x / y / z），适配任意朝向的 Hopfion；
  2. 提取「沿背景轴分量 = 0」的等值面（即 Hopfion 赤道预像）；
  3. 以垂直于背景轴平面内的相位角上色，输出 PNG 图像并弹出交互窗口。

背景轴自适应说明
----------------
Hopfion 的均匀背景磁化指向其环面对称轴。绘图须提取「沿该轴分量 = 0」
的等值面才能得到干净的环面预像。脚本通过全场平均磁化的主分量自动判定
背景轴，因此 axis='x'/'y'/'z' 生成的 Hopfion 都能正确渲染，无需手动指定。

用法
----
    python draw_hopfion.py <file.ovf> [--afm <mode>] [--offset ox oy oz]

    --afm    auto | checker | layerX | layerY | layerZ | none（默认 auto）
    --offset 手动指定 AFM 解调相位起点，三个整数，例如：--offset 0 0 1
"""

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


# ========== 工具函数 ==========

# 轴索引 → 名称，用于日志与图题
_AXIS_NAME = {0: 'x', 1: 'y', 2: 'z'}


def detect_background_axis(m_field):
    """自动识别 Hopfion 背景磁化所沿的轴。

    背景占据绝大多数格点且沿单一方向，因此全场平均磁化的主分量即背景轴。
    返回该轴索引及其垂直平面内的两个分量索引（按循环顺序），供等值面提取
    与相位上色使用。

    Parameters
    ----------
    m_field : df.Field
        解调后的磁化场。

    Returns
    -------
    axis_idx : int
        背景轴索引（0=x, 1=y, 2=z）。
    inplane : tuple of int
        垂直平面内两个分量索引 (p1, p2) = ((axis+1)%3, (axis+2)%3)，
        相位角约定为 arctan2(m[p2], m[p1])。
    mean_m : ndarray, shape (3,)
        全场平均磁化向量，用于日志。
    """
    mean_m = m_field.array.reshape(-1, 3).mean(axis=0)
    axis_idx = int(np.argmax(np.abs(mean_m)))
    inplane = ((axis_idx + 1) % 3, (axis_idx + 2) % 3)
    sign = '+' if mean_m[axis_idx] >= 0 else '-'
    print(f"背景磁化主方向: {sign}{_AXIS_NAME[axis_idx]} "
          f"(平均 m = [{mean_m[0]:.3f}, {mean_m[1]:.3f}, {mean_m[2]:.3f}])")
    print(f"等值面分量: m_{_AXIS_NAME[axis_idx]} = 0; "
          f"上色平面: ({_AXIS_NAME[inplane[0]]}, {_AXIS_NAME[inplane[1]]})")
    return axis_idx, inplane, mean_m


def angular_median(angles):
    """计算一组角度的"圆形均值"，避免 0/2π 边界处的相位跳变。

    将角度转换为单位圆上的向量后求均值方向，等效于循环中位数。

    Parameters
    ----------
    angles : ndarray, shape (..., N)
        最后一维为待平均的角度（弧度）。

    Returns
    -------
    ndarray
        沿最后一维平均后的角度（弧度），形状比输入少一维。
    """
    x = np.cos(angles)
    y = np.sin(angles)
    mean_x = np.mean(x, axis=1)
    mean_y = np.mean(y, axis=1)
    return np.arctan2(mean_y, mean_x)


def circle_fit_residuals(params, points):
    """圆形拟合残差函数，供 scipy.optimize.least_squares 调用。

    Parameters
    ----------
    params : array-like, shape (3,)
        [xc, yc, R]——圆心坐标与半径。
    points : ndarray, shape (N, 2)
        待拟合的二维点云。

    Returns
    -------
    ndarray, shape (N,)
        每个点到圆的有向距离。
    """
    xc, yc, R = params
    x, y = points[:, 0], points[:, 1]
    return np.sqrt((x - xc)**2 + (y - yc)**2) - R


# ========== 尺寸计算 ==========

def calculate_hopfion_radii_topological(m_field, axis_idx=2, inplane=(0, 1), core_threshold=0.02):
    """用动态阈值 + 等值面平均距离法计算 Hopfion 大半径 R 和小半径 r。

    策略一（按背景轴自适应）：
      1. 以「沿背景轴分量 < 该分量最小值 + threshold」定义核心原像区，
         对其在垂直平面内的投影做圆形拟合得 R。
      2. 提取整场「沿背景轴分量 = 0」等值面，计算各顶点到核心环的三维距离均值得 r。

    Parameters
    ----------
    m_field : df.Field
        解调后的磁化场。
    axis_idx : int
        背景轴索引（0=x, 1=y, 2=z）。
    inplane : tuple of int
        垂直平面内两个分量索引 (p1, p2)。
    core_threshold : float
        动态阈值偏移量（comp < comp_min + threshold 定义核心）。

    Returns
    -------
    R_hopfion : float or None
        大半径（m），拟合失败时返回 None。
    r_hopfion : float or None
        小半径（m），等值面提取失败时返回 None。
    """
    print("正在使用[策略一]改进的拓扑原像法计算R和r...")
    p1, p2 = inplane
    comp = m_field.array[..., axis_idx]   # 沿背景轴分量（axis=z 时即 mz）

    # --- 步骤 1：拟合大半径 R ---
    print("步骤1/2: 使用动态阈值计算大半径 R...")
    comp_min = np.min(comp)
    preimage_mask = comp < (comp_min + core_threshold)

    if not np.any(preimage_mask):
        print(f"警告：未找到Hopfion的拓扑原像 (m_axis ≈ {comp_min:.3f})，无法计算尺寸。")
        return None, None

    preimage_coords_grid = np.array(np.where(preimage_mask)).T
    preimage_coords_real = m_field.mesh.region.pmin + preimage_coords_grid * m_field.mesh.cell

    # 在垂直于背景轴的平面内拟合核心环
    plane_coords = preimage_coords_real[:, [p1, p2]]
    if len(plane_coords) < 3:
        print("警告：找到的核心点太少，无法进行圆形拟合。")
        return None, None

    center_guess = np.mean(plane_coords, axis=0)
    radius_guess = np.mean(np.sqrt(np.sum((plane_coords - center_guess)**2, axis=1)))

    try:
        res = least_squares(circle_fit_residuals, [center_guess[0], center_guess[1], radius_guess], args=(plane_coords,))
        c1, c2, R_hopfion = res.x
    except Exception as e:
        print(f"错误：对核心环的圆形拟合失败: {e}")
        return None, None

    print(f"核心环拟合完成: 中心≈({c1*1e9:.1f}, {c2*1e9:.1f})nm, R≈{R_hopfion*1e9:.2f}nm")

    # --- 步骤 2：用「沿轴分量 = 0」等值面估计小半径 r ---
    print("步骤2/2: 使用沿轴分量=0等值面到核心环的平均距离计算小半径 r...")
    try:
        verts, _, _, _ = measure.marching_cubes(volume=comp, level=0, spacing=m_field.mesh.cell)
        verts += m_field.mesh.region.pmin
    except (ValueError, RuntimeError) as e:
        print(f"提取等值面失败: {e}")
        return R_hopfion, None

    if len(verts) == 0:
        print("警告：等值面不包含任何顶点，无法计算 r。")
        return R_hopfion, None

    # 核心环沿轴坐标取核心点的轴向均值
    core_axis_center = np.mean(preimage_coords_real[:, axis_idx])

    # 各等值面顶点到核心环的三维距离：sqrt((ρ_plane - R)² + (axial - axial_core)²)
    dist_plane_from_center = np.sqrt((verts[:, p1] - c1)**2 + (verts[:, p2] - c2)**2)
    distances_to_core_ring = np.sqrt((dist_plane_from_center - R_hopfion)**2 + (verts[:, axis_idx] - core_axis_center)**2)
    r_hopfion = np.mean(distances_to_core_ring)

    print(f"计算完成: 大半径 R ≈ {R_hopfion*1e9:.2f} nm, 小半径 r ≈ {r_hopfion*1e9:.2f} nm")
    return R_hopfion, r_hopfion


# ========== 顶点配色 ==========

def interpolate_colors_for_vertices(m_field, verts, inplane=(0, 1)):
    """在等值面顶点处三线性插值平面内两分量，返回相位角 arctan2(m[p2], m[p1])。

    Parameters
    ----------
    m_field : df.Field
        磁化场。
    verts : ndarray, shape (N, 3)
        等值面顶点的世界坐标（m）。
    inplane : tuple of int
        垂直于背景轴平面内的两个分量索引 (p1, p2)。

    Returns
    -------
    ndarray, shape (N,)
        各顶点处的相位角（弧度），范围 (-π, π]。
    """
    print("正在为顶点计算颜色 (使用插值)...")
    p1, p2 = inplane
    pmin = m_field.mesh.region.pmin
    cell_size = m_field.mesh.cell
    indices = (verts - pmin) / cell_size
    indices = indices.T
    a_interp = map_coordinates(m_field.array[..., p1], indices, order=1, mode='nearest')
    b_interp = map_coordinates(m_field.array[..., p2], indices, order=1, mode='nearest')
    return np.arctan2(b_interp, a_interp)


# ========== AFM 检测与解调 ==========

def _avg_neighbor_dot(m):
    """计算三个轴方向上相邻格点的平均点积，衡量场的空间平滑度。

    Returns
    -------
    ndarray, shape (3,)
        [x方向均值, y方向均值, z方向均值]。铁磁排列约为 +1，AFM 排列约为 -1。
    """
    mx = []
    for axis in range(3):
        a = m[..., :-1] if axis == 2 else (m[:, :-1, :] if axis == 1 else m[:-1, :, :])
        b = m[..., 1:]  if axis == 2 else (m[:, 1:, :]  if axis == 1 else m[1:, :, :])
        if axis == 0:
            dots = np.sum(a * b, axis=-1)
        elif axis == 1:
            dots = np.sum(a * b, axis=-1)
        else:
            dots = np.sum(a * b, axis=-1)
        mx.append(np.mean(dots))
    return np.array(mx)


def _build_sign_field(shape, mode, offsets=(0, 0, 0)):
    """构造 (+1/-1) 交替符号场。

    Parameters
    ----------
    shape : tuple
        (nx, ny, nz[, ...])，取前三维。
    mode : str
        "checker" | "layerX" | "layerY" | "layerZ"。
    offsets : tuple of int
        (ox, oy, oz)，各方向相位起点（0 或 1）。

    Returns
    -------
    ndarray, shape (nx, ny, nz), dtype int8
    """
    nx, ny, nz = shape[:3]
    ix = np.arange(nx)[:, None, None]
    iy = np.arange(ny)[None, :, None]
    iz = np.arange(nz)[None, None, :]
    ox, oy, oz = offsets
    if mode == "checker":
        sign = 1 - 2 * (((ix+ox) + (iy+oy) + (iz+oz)) % 2)
    elif mode == "layerX":
        sign = 1 - 2 * ((ix+ox) % 2)
    elif mode == "layerY":
        sign = 1 - 2 * ((iy+oy) % 2)
    elif mode == "layerZ":
        sign = 1 - 2 * ((iz+oz) % 2)
    else:
        sign = np.ones((nx, ny, nz), dtype=np.int8)
    return sign


def _auto_detect_afm_mode(m):
    """粗略自动识别 AFM 排列模式。

    判据（经验阈值 -0.6）：
    - 三方向均 < -0.6  → checker
    - 仅 x 方向 < -0.6 → layerX（以此类推 y/z）
    - 均不满足        → None（无法识别）
    """
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
    """在所有合法相位起点中搜索使解调后场最平滑的 offsets。

    checker 测试 8 种 (ox, oy, oz ∈ {0,1})；
    layer* 测试 2 种（沿其轴 0/1）。

    Returns
    -------
    tuple of int
        最优 (ox, oy, oz)。
    """
    shape = m.shape[:3]
    if mode == "checker":
        offs = [(ox, oy, oz) for ox in (0, 1) for oy in (0, 1) for oz in (0, 1)]
    elif mode == "layerX":
        offs = [(ox, 0, 0) for ox in (0, 1)]
    elif mode == "layerY":
        offs = [(0, oy, 0) for oy in (0, 1)]
    elif mode == "layerZ":
        offs = [(0, 0, oz) for oz in (0, 1)]
    else:
        return (0, 0, 0)

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
    """将 AFM 交替场解调为连续场，便于等值面提取与配色。

    Parameters
    ----------
    m_field : df.Field
        原始磁化场。
    afm_hint : str
        "auto" | "checker" | "layerX" | "layerY" | "layerZ" | "none"。
    offset_hint : tuple of int or None
        手动指定解调相位 (ox, oy, oz)；None 时自动搜索最优相位。

    Returns
    -------
    m_demod : df.Field
        解调后的磁化场（共享原始 mesh）。
    info : tuple
        (mode, offsets)——使用的解调模式与相位。
    """
    arr = m_field.array.copy()
    if afm_hint == "none":
        return m_field, ("none", (0, 0, 0))

    # 确定解调模式
    if afm_hint == "auto":
        mode = _auto_detect_afm_mode(arr)
        if mode is None:
            print("未检测到典型AFM模式（将按 'none' 处理）。")
            return m_field, ("none", (0, 0, 0))
        print(f"检测到 AFM 模式：{mode}")
    else:
        mode = afm_hint
        print(f"使用指定的 AFM 模式：{mode}")

    # 确定相位起点
    if offset_hint is not None:
        offsets = offset_hint
        print(f"使用指定的 AFM 解调相位 offsets = {offsets}")
    else:
        offsets = _best_phase_for_mode(arr, mode)
        print(f"自动检测到 AFM 解调相位 offsets = {offsets}")

    # 应用符号场解调
    sign = _build_sign_field(arr.shape[:3], mode, offsets).astype(arr.dtype)[..., None]
    arr_demod = arr * sign

    m_demod = df.Field(mesh=m_field.mesh, nvdim=3, value=0)
    m_demod.array[...] = arr_demod
    return m_demod, (mode, offsets)


# ========== 渲染 ==========

def draw_isosurface(ovf_filename, R_hopfion, r_hopfion, m_field,
                    axis_idx=2, inplane=(0, 1), title_info=""):
    """提取「沿背景轴分量 = 0」等值面并渲染为 HSV 相位着色的三维图，保存为 PNG。

    Parameters
    ----------
    ovf_filename : str
        原始 OVF 文件路径（用于构造输出 PNG 文件名与图题）。
    R_hopfion : float or None
        大半径（m），用于图题标注。
    r_hopfion : float or None
        小半径（m），用于图题标注。
    m_field : df.Field
        解调后的磁化场。
    axis_idx : int
        背景轴索引（0=x, 1=y, 2=z）；提取 m[..., axis_idx]=0 等值面。
    inplane : tuple of int
        垂直平面内两个分量索引 (p1, p2)，用于相位上色。
    title_info : str
        附加在图题中的说明文字（如解调模式信息）。
    """
    p1, p2 = inplane
    axis_name = _AXIS_NAME[axis_idx]
    print(f"正在计算 m_{axis_name}=0 等值面 (Marching Cubes)...")
    verts, faces, _, _ = measure.marching_cubes(
        volume=m_field.array[..., axis_idx], level=0, spacing=m_field.mesh.cell
    )
    verts += m_field.mesh.region.pmin

    vertex_colors_angles = interpolate_colors_for_vertices(m_field, verts, inplane=inplane)

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

    ax.set_xlim(verts[:, 0].min() * 1e9, verts[:, 0].max() * 1e9)
    ax.set_ylim(verts[:, 1].min() * 1e9, verts[:, 1].max() * 1e9)
    ax.set_zlim(verts[:, 2].min() * 1e9, verts[:, 2].max() * 1e9)
    ax.set_xlabel("x (nm)")
    ax.set_ylabel("y (nm)")
    ax.set_zlabel("z (nm)")

    title_text = f"Hopfion ({title_info})\n{os.path.basename(ovf_filename)} (m{axis_name}=0)"
    if R_hopfion is not None and r_hopfion is not None:
        title_text += f"\nEst. R ≈ {R_hopfion*1e9:.2f} nm, r ≈ {r_hopfion*1e9:.2f} nm"
    ax.set_title(title_text)

    axis_limits = np.array([ax.get_xlim(), ax.get_ylim(), ax.get_zlim()])
    ax.set_box_aspect(np.ptp(axis_limits, axis=1))

    sm = plt.cm.ScalarMappable(cmap='hsv', norm=norm)
    cbar = fig.colorbar(sm, ax=ax, shrink=0.6, aspect=20, pad=0.1)
    cbar.set_label(rf'Angle $\arctan(m_{_AXIS_NAME[p2]}/m_{_AXIS_NAME[p1]})$')
    cbar.set_ticks([-np.pi, -np.pi/2, 0, np.pi/2, np.pi])
    cbar.set_ticklabels([r'$-\pi$', r'$-\pi/2$', '0', r'$\pi/2$', r'$\pi$'])

    output_filename = os.path.splitext(ovf_filename)[0] + '.png'
    plt.savefig(output_filename, dpi=300)
    print(f"图像已成功保存为: {output_filename}")

    print("正在打开可交互的三维图像窗口... (关闭此窗口后程序才会结束)")
    plt.show()
    plt.close()


def main(ovf_files, afm_hint="auto", offset_hint=None):
    """批量处理 OVF 文件：解调 → 计算尺寸 → 渲染。

    Parameters
    ----------
    ovf_files : list of str
        待处理的 OVF 文件路径列表。
    afm_hint : str
        AFM 解调模式提示，传递给 demodulate_afm。
    offset_hint : tuple of int or None
        手动 AFM 相位起点，传递给 demodulate_afm。
    """
    print("正在加载OVF文件用于绘图...")
    for ovf_file in ovf_files:
        try:
            # 文件名含 "afm" 时自动切换到 checker 模式
            local_afm_hint = afm_hint
            if "afm" in os.path.basename(ovf_file).lower() and local_afm_hint == "auto":
                print("文件名中检测到'AFM'，自动切换到 'checker' 解调模式。")
                local_afm_hint = "checker"

            raw = df.Field.from_file(ovf_file)
            m_demod, (mode, offsets) = demodulate_afm(raw, afm_hint=local_afm_hint, offset_hint=offset_hint)

            # 自动识别背景磁化方向，自适应任意朝向的 Hopfion
            axis_idx, inplane, _ = detect_background_axis(m_demod)

            R, r = calculate_hopfion_radii_topological(m_demod, axis_idx=axis_idx, inplane=inplane)

            axis_tag = f"axis={_AXIS_NAME[axis_idx]}"
            demod_tag = f"demod: {mode}{' '+str(offsets) if mode != 'none' else ''}"
            title_info = f"{axis_tag}, {demod_tag}"
            draw_isosurface(ovf_file, R, r, m_demod,
                            axis_idx=axis_idx, inplane=inplane, title_info=title_info)

        except Exception as e:
            print(f"处理文件 {ovf_file} 时发生严重错误: {e}")


# ========== 命令行入口 ==========

if __name__ == "__main__":
    import sys

    args = sys.argv[1:]
    files = []
    afm_hint = "auto"
    offset_hint = None

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
        filename = "hopfion_Qh4.ovf"
        if not os.path.exists(filename):
            print(f"错误：找不到文件 '{filename}'。请将OVF路径作为参数传入。")
            print("用法: python draw_hopfion.py your.ovf [--afm mode] [--offset x y z]")
            sys.exit(1)
        files = [filename]

    main(files, afm_hint=afm_hint, offset_hint=offset_hint)
