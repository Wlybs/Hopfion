import numpy as np
import os
import re
from skimage import measure
from sklearn.decomposition import PCA
from scipy.optimize import least_squares
import discretisedfield as df

# 只从您的生成脚本中导入我们需要的函数
from generate_hopfion import generate_hopfion_ovf

# --- 以下是为解决所有已知兼容性问题而内置的、独立的分析函数 ---

def parse_ovf_and_create_field_final(filename):
    """
    (最终测试通过版) 一个可以正确解析 OVF 2.0 并稳健地构建 Field 对象的解析器。
    它能智能处理头部信息中缺失 xmin/xmax 的情况。
    """
    print(f"启动最终版手动解析模式 for '{filename}'...")
    header = {}
    data_lines = []
    
    with open(filename, 'r', errors='ignore') as f:
        in_header = False
        in_data = False
        for line in f:
            line_lower = line.lower().strip()
            if line_lower.startswith("# begin: header"): in_header = True; continue
            if line_lower.startswith("# end: header"): in_header = False; continue
            if line_lower.startswith("# begin: data text"): in_data = True; continue
            if line_lower.startswith("# end: data text"): in_data = False; continue

            if in_header:
                line_to_parse = line.strip('# ').strip()
                parts = line_to_parse.split(':', 1)
                if len(parts) == 2:
                    header[parts[0].strip().lower()] = parts[1].strip()
            
            if in_data and not line.strip().startswith('#'):
                data_lines.append(line)

    try:
        xnodes = int(header['xnodes'])
        ynodes = int(header['ynodes'])
        znodes = int(header['znodes'])
        xstepsize = float(header['xstepsize'])
        ystepsize = float(header['ystepsize'])
        zstepsize = float(header['zstepsize'])
        meshunit = header.get('meshunit', 'm')
    except KeyError as e:
        raise RuntimeError(f"手动解析失败：OVF文件头部缺少关键信息 {e}")

    if meshunit.lower() == 'nm':
        xstepsize *= 1e-9; ystepsize *= 1e-9; zstepsize *= 1e-9

    # --- 最终修复：智能处理边界信息 ---
    # 如果文件明确提供了 xmin/max，则使用它们
    if 'xmin' in header and 'xmax' in header:
        xmin = float(header['xmin']); xmax = float(header['xmax'])
        ymin = float(header['ymin']); ymax = float(header['ymax'])
        zmin = float(header['zmin']); zmax = float(header['zmax'])
        if meshunit.lower() == 'nm':
            xmin *= 1e-9; xmax *= 1e-9
            ymin *= 1e-9; ymax *= 1e-9
            zmin *= 1e-9; zmax *= 1e-9
    # 否则，假设区域以原点为中心，并自动计算边界
    else:
        print("未在头部找到xmin/xmax，将假设模拟区域以原点为中心。")
        xmin = -xnodes * xstepsize / 2; xmax = xnodes * xstepsize / 2
        ymin = -ynodes * ystepsize / 2; ymax = ynodes * ystepsize / 2
        zmin = -znodes * zstepsize / 2; zmax = znodes * zstepsize / 2
    # --- 修复结束 ---

    p1 = (xmin, ymin, zmin)
    p2 = (xmax, ymax, zmax)
    n = (xnodes, ynodes, znodes)

    mesh = df.Mesh(p1=p1, p2=p2, n=n)
    field = df.Field(mesh, dim=3)

    data = np.loadtxt(data_lines)
    value = data.reshape(znodes, ynodes, xnodes, 3)
    field.value = np.transpose(value, (2, 1, 0, 3))

    print("手动解析并成功构建Field对象！")
    return field

def calculate_radii_topological_standalone(m_field):
    """
    一个独立的、使用您原版逻辑的半径计算器。
    """
    print("正在使用您原来的算法计算R和r...")
    mz = m_field.array[..., 2]
    preimage_mask = mz < -0.95
    if not np.any(preimage_mask): return None, None
        
    preimage_coords_grid = np.array(np.where(preimage_mask)).T
    preimage_coords_real = m_field.mesh.index2point(preimage_coords_grid)
    
    pca = PCA(n_components=2)
    xy_coords = pca.fit_transform(preimage_coords_real)
    center_guess = np.mean(xy_coords, axis=0)
    radius_guess = np.mean(np.sqrt(np.sum((xy_coords - center_guess)**2, axis=1)))
    res = least_squares(circle_fit_residuals, [center_guess[0], center_guess[1], radius_guess], args=(xy_coords,))
    R_hopfion = res.x[2]

    try:
        verts, _, _, _ = measure.marching_cubes(volume=m_field.array.transpose(2, 1, 0), level=0, spacing=m_field.mesh.cell)
        verts += m_field.mesh.region.pmin
    except (ValueError, RuntimeError): return R_hopfion, None

    num_slices, r_estimates = 16, []
    for i in range(num_slices):
        angle = 2 * np.pi * i / num_slices
        normal = np.array([np.cos(angle), np.sin(angle), 0])
        dist = verts @ normal
        slice_indices = np.where(np.abs(dist) < m_field.mesh.cell[0] * 1.5)[0]
        if len(slice_indices) < 10: continue
        
        slice_verts = verts[slice_indices]
        slice_2d = np.vstack([np.sqrt(slice_verts[:, 0]**2 + slice_verts[:, 1]**2), slice_verts[:, 2]]).T
        center_guess = np.array([R_hopfion, 0])
        radius_guess = np.mean(np.sqrt(np.sum((slice_2d - center_guess)**2, axis=1)))
        res = least_squares(circle_fit_residuals, [center_guess[0], center_guess[1], radius_guess], args=(slice_2d,))
        r_estimates.append(res.x[2])

    r_hopfion = np.mean(r_estimates) if r_estimates else None
    print(f"计算完成: 大半径 R ≈ {R_hopfion*1e9:.2f} nm, 小半径 r ≈ {r_hopfion*1e9:.2f} nm")
    return R_hopfion, r_hopfion

def circle_fit_residuals(params, points):
    xc, yc, R = params
    return np.sqrt((points[:, 0] - xc)**2 + (points[:, 1] - yc)**2) - R

def create_Qh1_analog(reference_ovf_file):
    print(f"--- 步骤 1: 分析参考文件 '{reference_ovf_file}' 的几何尺寸 ---")
    if not os.path.exists(reference_ovf_file): print(f"错误：找不到参考文件 '{reference_ovf_file}'。"); return

    try:
        ref_field = parse_ovf_and_create_field_final(reference_ovf_file)
        R_measured, r_measured = calculate_radii_topological_standalone(ref_field)
        if R_measured is None or r_measured is None: print("无法计算出 R 和 r。"); return
    except Exception as e:
        print(f"分析参考文件时发生致命错误: {e}"); import traceback; traceback.print_exc(); return

    print(f"\n--- 步骤 2: 生成新的 Qh=1 Hopfion ---")
    print(f"将使用测量出的尺寸: R={R_measured*1e9:.2f} nm, r={r_measured*1e9:.2f} nm")
    output_filename = f"hopfion_Qh=1_analog_R{R_measured*1e9:.1f}_r{r_measured*1e9:.1f}.ovf"
    box_size = (R_measured + r_measured) * 2.2; nodes = 100; stepsize = box_size / nodes

    generate_hopfion_ovf(
        Qh=1, p=1, q=1, R=R_measured, r=r_measured, xnodes=nodes, ynodes=nodes,
        znodes=nodes, xstepsize=stepsize, ystepsize=stepsize, zstepsize=stepsize,
        output_filename=output_filename
    )

if __name__ == "__main__":
    reference_file = "stable-state-h+1+2_trans_q=2.ovf"
    create_Qh1_analog(reference_file)