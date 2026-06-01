"""
hopfion_analysis.py — Hopfion 核心分析工具库
=============================================
共享函数库，供所有子项目 import 使用。
禁止在子项目脚本中复制这些函数，直接 import 本模块。

用法示例：
    import sys
    sys.path.insert(0, "/mnt/d/Research/Hopfion/scripts")
    from hopfion_analysis import hopfion_centroid, compute_Rr, extract_series
"""

import os
import numpy as np
from scipy.optimize import least_squares
from skimage import measure
import discretisedfield as df


# ──────────────────────────────────────────────
# 1. 质心 / 位移追踪
# ──────────────────────────────────────────────

def hopfion_centroid(field, method="weighted"):
    """
    计算 Hopfion 质心坐标（单位：nm）。

    Parameters
    ----------
    field : discretisedfield.Field
        已加载的磁化场。
    method : str
        "weighted" — 加权质心，权重 = max(1 - mz, 0)，亚格点精度，推荐。
        "threshold" — 二值阈值质心，取 mz < min(mz)+0.05 的格点均值，精度较低。

    Returns
    -------
    centroid : np.ndarray, shape (3,), 单位 nm
        [cx, cy, cz]
    """
    mz = field.array[:, :, :, 2]
    cell = np.array(field.mesh.cell)
    pmin = np.array(field.mesh.region.pmin)
    nx, ny, nz = mz.shape

    if method == "weighted":
        weight = np.maximum(1.0 - mz, 0.0)
        w_sum = np.sum(weight)
        if w_sum == 0:
            return None
        centers = []
        for i, n in enumerate([nx, ny, nz]):
            coords = pmin[i] + cell[i] * (np.arange(n) + 0.5)
            shape = [1, 1, 1]
            shape[i] = n
            c = np.sum(coords.reshape(shape) * weight) / w_sum * 1e9
            centers.append(float(c))
        return np.array(centers)

    elif method == "threshold":
        mz_min = float(np.min(mz))
        mask = mz < (mz_min + 0.05)
        if not np.any(mask):
            return None
        idx = np.array(np.where(mask)).T          # (N, 3)
        coords = pmin + idx * cell                # 真实坐标（m）
        return np.mean(coords, axis=0) * 1e9      # nm

    else:
        raise ValueError(f"method must be 'weighted' or 'threshold', got '{method}'")


def core_count(field):
    """
    返回 mz < 0 的格点数（Hopfion 核心体积的代理量）。

    Parameters
    ----------
    field : discretisedfield.Field

    Returns
    -------
    int
    """
    return int(np.sum(field.array[:, :, :, 2] < 0))


# ──────────────────────────────────────────────
# 2. 大半径 R 与管半径 r
# ──────────────────────────────────────────────

_CORE_THRESHOLD = 0.05   # mz < min(mz) + 0.05 定义核心
_BAD_FIT_NM = 3.0        # 圆拟合残差超过此值视为失败


def _circle_residuals(params, pts):
    xc, yc, R = params
    return np.sqrt((pts[:, 0] - xc) ** 2 + (pts[:, 1] - yc) ** 2) - R


def _pbc_unwrap_xy(xy, box_L):
    """将 PBC 体系中散落在边界两侧的 xy 坐标折叠到同一侧。"""
    centroid = np.mean(xy, axis=0)
    delta = xy - centroid
    delta -= box_L * np.round(delta / box_L)
    return centroid + delta


def compute_Rr(field):
    """
    计算 Hopfion 的大半径 R 和管半径 r（单位：nm）。

    原理
    ----
    R：对核心格点（mz < min+0.05）的 xy 坐标做最小二乘圆拟合，拟合结果为 R。
    r：对 mz=0 等值面（marching cubes）计算每个顶点到环中轴的距离，取中位数为 r。

    Parameters
    ----------
    field : discretisedfield.Field

    Returns
    -------
    R_nm : float or None
    r_nm : float or None
    """
    mz = field.array[..., 2]
    cell = np.array(field.mesh.cell)
    pmin = np.array(field.mesh.region.pmin)
    box_L = np.array(field.mesh.region.pmax) - pmin

    # ── Step 1: 核心格点 ──
    mz_min = float(np.min(mz))
    core_mask = mz < (mz_min + _CORE_THRESHOLD)
    if not np.any(core_mask):
        return None, None

    idx = np.array(np.where(core_mask)).T          # (N, 3) 格点索引
    coords = pmin + idx * cell                      # 真实坐标（m）
    xy = coords[:, :2]
    if len(xy) < 4:
        return None, None

    # ── Step 2: PBC 展开 + 圆拟合 → R ──
    xy_uw = _pbc_unwrap_xy(xy, box_L[:2])
    cg = np.mean(xy_uw, axis=0)
    rg = np.mean(np.linalg.norm(xy_uw - cg, axis=1))
    try:
        res = least_squares(
            _circle_residuals, [cg[0], cg[1], rg],
            args=(xy_uw,), method="lm"
        )
        xc, yc, R_fit = res.x
    except Exception:
        return None, None

    R_nm = abs(R_fit) * 1e9

    # ── Step 3: mz=0 等值面 → r ──
    try:
        verts, _, _, _ = measure.marching_cubes(mz, level=0, spacing=tuple(cell))
        verts += pmin
    except (ValueError, RuntimeError):
        return R_nm, None
    if len(verts) == 0:
        return R_nm, None

    xy_v = _pbc_unwrap_xy(verts[:, :2], box_L[:2])
    rho = np.sqrt((xy_v[:, 0] - xc) ** 2 + (xy_v[:, 1] - yc) ** 2)
    z_center = float(np.mean(coords[:, 2]))
    dist = np.sqrt((rho - abs(R_fit)) ** 2 + (verts[:, 2] - z_center) ** 2)
    r_nm = float(np.median(dist)) * 1e9

    return R_nm, r_nm


# ──────────────────────────────────────────────
# 3. OVF 序列批量加载
# ──────────────────────────────────────────────

def load_ovf_series(out_dir, dt_ns, func, verbose=True):
    """
    遍历 out_dir 中所有 m*.ovf 文件，对每帧调用 func(field) 并收集结果。

    Parameters
    ----------
    out_dir : str
        包含 m000000.ovf … 的目录。
    dt_ns : float
        相邻帧的时间间隔（ns），由仿真 autosave 参数决定。
    func : callable
        接受 discretisedfield.Field，返回任意值（通常是 tuple）。
    verbose : bool
        是否打印进度。

    Returns
    -------
    list of (t_ns, *func_result)
        按帧顺序排列的结果列表。
    """
    ovf_files = sorted(
        f for f in os.listdir(out_dir)
        if f.startswith("m") and f.endswith(".ovf")
    )
    results = []
    for ovf in ovf_files:
        idx = int(ovf.replace("m", "").replace(".ovf", ""))
        t_ns = idx * dt_ns
        path = os.path.join(out_dir, ovf)
        field = df.Field.from_file(path)
        result = func(field)
        del field
        results.append((t_ns, result))
        if verbose:
            import sys
            sys.stdout.write(f"\r  {ovf}: {result}    ")
            sys.stdout.flush()
    if verbose:
        print()
    return results


def extract_Rr_series(out_dir, dt_ns, verbose=True):
    """
    对整个 out_dir 序列提取 (t_ns, R_nm, r_nm)。

    Parameters
    ----------
    out_dir : str
    dt_ns : float

    Returns
    -------
    list of (t_ns, R_nm, r_nm)
        R_nm / r_nm 可能为 None（Hopfion 消解帧）。
    """
    def _func(field):
        return compute_Rr(field)

    raw = load_ovf_series(out_dir, dt_ns, _func, verbose=verbose)
    return [(t, r[0], r[1]) for t, r in raw]


def extract_trajectory(out_dir, dt_ns, method="weighted", verbose=True):
    """
    对整个 out_dir 序列提取 Hopfion 质心轨迹。

    Parameters
    ----------
    out_dir : str
    dt_ns : float
    method : str
        传递给 hopfion_centroid() 的 method 参数。

    Returns
    -------
    list of (t_ns, centroid_nm)
        centroid_nm 为 np.ndarray([cx, cy, cz])，单位 nm；
        None 表示该帧 Hopfion 已消解。
    """
    def _func(field):
        return hopfion_centroid(field, method=method)

    raw = load_ovf_series(out_dir, dt_ns, _func, verbose=verbose)
    return [(t, r) for t, r in raw]


# ──────────────────────────────────────────────
# 4. 相位相关追踪 (Phase Correlation Tracking)
# ──────────────────────────────────────────────
# 比加权质心法对自旋波背景噪声更鲁棒：通过 FFT 互相关检测
# 拓扑纹理的刚体平移，而非依赖 mz 绝对值质心。
#
# 移植自 magnon-hopfion track.py（原 AFM 版本）：
#   保留: ② 源区排除  ③ 相位相关核心  ④ PBC 折叠
#   去除: ① AFM 子晶格翻转  ⑤ φ 方位角旋转追踪
# ──────────────────────────────────────────────

def hopfion_phase_correlation(field1, field2, exclude_boundary=5):
    """
    通过相位相关法（FFT）测量两帧之间 Hopfion 的平移量。

    Parameters
    ----------
    field1 : discretisedfield.Field
        参考帧（通常为 t=0 帧）。
    field2 : discretisedfield.Field
        当前帧。
    exclude_boundary : int
        排除吸收边界层的格点数（默认 5，对应 frustrated FM 2.5nm 边界）。

    Returns
    -------
    shift_nm : np.ndarray, shape (3,)
        [dx, dy, dz]（nm），field2 相对于 field1 的平移量。
        返回 None 表示计算失败。
    """
    mz1 = field1.array[:, :, :, 2].copy()
    mz2 = field2.array[:, :, :, 2].copy()
    cell = np.array(field1.mesh.cell)   # 单位：m

    # 排除吸收边界层（alpha=100 区域）
    e = exclude_boundary
    if e > 0:
        mz1 = mz1[e:-e, e:-e, e:-e]
        mz2 = mz2[e:-e, e:-e, e:-e]

    # 归一化互相关（相位相关）
    Z1 = np.fft.fftn(mz1)
    Z2 = np.fft.fftn(mz2)
    R = Z1.conj() * Z2
    abs_R = np.abs(R)
    abs_R[abs_R == 0.0] = 1.0
    R /= abs_R
    R = np.where(np.isnan(R), 0.0, R)
    r = np.abs(np.fft.ifftn(R))

    # 整数峰值位置
    peak = np.array(np.unravel_index(np.argmax(r), r.shape), dtype=int)

    # 3×3×3 加权质心 → 亚格点精度（保留原 track.py 的 √2 缩放系数）
    nx, ny, nz = r.shape
    w_sum = 0.0
    w_off = np.zeros(3)
    for di in range(-1, 2):
        for dj in range(-1, 2):
            for dk in range(-1, 2):
                ii = (peak[0] + di) % nx
                jj = (peak[1] + dj) % ny
                kk = (peak[2] + dk) % nz
                w = float(r[ii, jj, kk])
                w_sum += w
                w_off += np.array([di, dj, dk], dtype=float) * w

    if w_sum == 0.0:
        return None

    shift = peak.astype(float) + w_off / w_sum * np.sqrt(2.0)

    # PBC 折叠到 [-N/2, N/2)
    shape = np.array([nx, ny, nz], dtype=float)
    shift = (shift + shape / 2.0) % shape - shape / 2.0

    return shift * cell * 1e9   # nm


def extract_trajectory_phase_correlation(out_dir, dt_ns,
                                          exclude_boundary=5, verbose=True):
    """
    用相位相关法提取 Hopfion 累积位移轨迹（相对于第一帧）。

    每帧与第 0 帧比较（非逐帧累加），避免误差积累。

    Parameters
    ----------
    out_dir : str
    dt_ns : float
    exclude_boundary : int

    Returns
    -------
    list of (t_ns, shift_nm, core_cnt)
        shift_nm : np.ndarray([dx, dy, dz])（nm），相对于 t=0 帧。
        core_cnt : int，mz<0 格点数。
    """
    ovf_files = sorted(
        f for f in os.listdir(out_dir)
        if f.startswith("m") and f.endswith(".ovf")
    )
    if not ovf_files:
        return []

    ref_field = df.Field.from_file(os.path.join(out_dir, ovf_files[0]))
    ref_cc = core_count(ref_field)
    results = [(0.0, np.zeros(3), ref_cc)]

    for ovf in ovf_files[1:]:
        idx = int(ovf.replace("m", "").replace(".ovf", ""))
        t_ns = idx * dt_ns
        cur_field = df.Field.from_file(os.path.join(out_dir, ovf))
        shift = hopfion_phase_correlation(ref_field, cur_field,
                                          exclude_boundary=exclude_boundary)
        cc = core_count(cur_field)
        del cur_field
        if shift is None:
            shift = np.full(3, np.nan)
        results.append((t_ns, shift, cc))
        if verbose:
            import sys
            sys.stdout.write(
                f"\r  {ovf}: dr={np.linalg.norm(shift):.3f}nm    "
            )
            sys.stdout.flush()

    if verbose:
        print()
    return results


# ──────────────────────────────────────────────
# 5. Hall 角计算
# ──────────────────────────────────────────────

def compute_hall_angle(trajectory_data, sw_propagation_axis="x",
                       skip_fraction=0.33):
    """
    从位移轨迹计算拓扑 Hall 角 theta_H。

    Parameters
    ----------
    trajectory_data : list of (t_ns, shift_nm, core_cnt)
        extract_trajectory_phase_correlation() 的输出。
    sw_propagation_axis : str
        自旋波传播方向：'x', 'y', 或 'z'。
        v_parallel 沿此轴，v_perp 为其余分量。
    skip_fraction : float
        跳过前 N% 帧以避免瞬态。

    Returns
    -------
    dict with keys:
        'theta_H_deg': float — Hall 角（度），0=沿SW方向，90=完全垂直
        'theta_H_err_deg': float — 基于位移不确定度的估计误差
        'v_parallel': float — 平行速度 (nm/ns)
        'v_perp': float — 垂直速度 (nm/ns)
        'displacement_total_nm': float — 总位移
        'valid': bool — 位移是否足够大以给出可靠 Hall 角
    """
    ts = np.array([d[0] for d in trajectory_data])
    shifts = np.array([d[1] for d in trajectory_data])  # (N, 3) in nm

    # Skip initial transient
    n_skip = max(1, int(len(ts) * skip_fraction))
    ts_late = ts[n_skip:]
    shifts_late = shifts[n_skip:]

    # Map axis to index
    axis_map = {'x': 0, 'y': 1, 'z': 2}
    par_idx = axis_map[sw_propagation_axis]
    perp_indices = [i for i in range(3) if i != par_idx]

    # Displacement components (late-time)
    d_par = shifts_late[-1, par_idx] - shifts_late[0, par_idx]
    d_perp_vec = shifts_late[-1, perp_indices] - shifts_late[0, perp_indices]
    d_perp = np.linalg.norm(d_perp_vec)
    d_total = np.linalg.norm(shifts[-1] - shifts[0])

    # Time span
    dt = ts_late[-1] - ts_late[0]
    v_par = d_par / dt if dt > 0 else 0.0
    v_perp = d_perp / dt if dt > 0 else 0.0

    # Hall angle
    theta_H = np.degrees(np.arctan2(d_perp, abs(d_par)))

    # Validity check: displacement must exceed grid resolution (~0.05nm)
    valid = d_total > 0.1  # nm

    # Error estimate from grid resolution (0.5nm cell -> ~0.05nm subpixel)
    dx_err = 0.05  # nm
    if valid and abs(d_par) > dx_err:
        theta_H_err = np.degrees(dx_err / max(abs(d_par), dx_err))
    else:
        theta_H_err = 90.0  # meaningless

    return {
        'theta_H_deg': theta_H,
        'theta_H_err_deg': theta_H_err,
        'v_parallel': v_par,
        'v_perp': v_perp,
        'displacement_total_nm': d_total,
        'valid': valid,
    }
