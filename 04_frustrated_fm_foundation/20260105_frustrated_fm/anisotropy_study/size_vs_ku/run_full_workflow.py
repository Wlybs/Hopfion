import os
import glob
import subprocess
import time
import sys
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from skimage import measure
from matplotlib.colors import Normalize
import discretisedfield as df
from scipy.optimize import least_squares
from scipy.ndimage import map_coordinates

# ==============================================================================
# --- 1. 参数配置区 ---
# ==============================================================================

# 各向异性 Ku1 的候选值 (单位: J/m^3)
Ku1_values = [0, 2500, 5000, 7500, 10000]

# 固定饱和磁化强度 Ms (单位: A/m)
FIXED_MS = 1.5e5

# Mumax3 可执行文件的路径
MUMAX_EXEC = "mumax3"

# 用于仿真的 Hopfion 初始态文件 (请确保此文件在运行目录下)
OVF_FILE = "hopfion_Qh1_FM_SMALL.ovf"

# 模拟的总时长和保存间隔
RUN_TIME = 3e-9
SAVE_INTERVAL = 1e-10

# Mumax3 脚本模板
MX3_TEMPLATE = """
// 1. 基础物理参数设定
cellsize   := 0.5e-9
Ms_val := __BETA__
A_base := 5e-12

SetGridSize(100, 100, 100)
SetCellSize(cellsize, cellsize, cellsize)
SetPBC(1, 1, 1) 

Msat  = Ms_val
Aex = A_base
Dbulk = 0
Dind  = 0
Ku1   = __KU1__
anisU = vector(0, 0, 1)
EnableDemag = false
alpha		= 0.2

// 2. 计算场强系数因子
factor := 2.0 / (Ms_val * cellsize * cellsize)

// 3. 实现 J4 (第四近邻, 距离 2a, 6个邻居)
A_J4 := A_base * (-0.082)
Coeff_J4 := A_J4 * factor

sum_J4 :=     Add(Shifted(m, 2, 0, 0), Shifted(m, -2, 0, 0))
sum_J4 = Add(sum_J4, Shifted(m, 0, 2, 0))
sum_J4 = Add(sum_J4, Shifted(m, 0, -2, 0))
sum_J4 = Add(sum_J4, Shifted(m, 0, 0, 2))
sum_J4 = Add(sum_J4, Shifted(m, 0, 0, -2))

B_J4 := Mul(Const(Coeff_J4), sum_J4)
AddFieldTerm(B_J4)

// 4. 实现 J2 (次近邻, 距离 sqrt(2)a, 12个邻居)
A_J2 := A_base * (-0.164)
Coeff_J2 := A_J2 * factor

sum_J2 :=     Add(Shifted(m, 1, 1, 0), Shifted(m, 1, -1, 0))
sum_J2 = Add(sum_J2, Shifted(m, -1, 1, 0))
sum_J2 = Add(sum_J2, Shifted(m, -1, -1, 0))
sum_J2 = Add(sum_J2, Shifted(m, 0, 1, 1))
sum_J2 = Add(sum_J2, Shifted(m, 0, 1, -1))
sum_J2 = Add(sum_J2, Shifted(m, 0, -1, 1))
sum_J2 = Add(sum_J2, Shifted(m, 0, -1, -1))
sum_J2 = Add(sum_J2, Shifted(m, 1, 0, 1))
sum_J2 = Add(sum_J2, Shifted(m, 1, 0, -1))
sum_J2 = Add(sum_J2, Shifted(m, -1, 0, 1))
sum_J2 = Add(sum_J2, Shifted(m, -1, 0, -1))

B_J2 := Mul(Const(Coeff_J2), sum_J2)
AddFieldTerm(B_J2)

m.LoadFile("__OVF_FILE__")

autosave(m, __SAVE_INTERVAL__)
tableautosave(1e-11)
TableAdd(E_Total)
run(__RUN_TIME__)
"""

# ==============================================================================
# --- 2. 绘图与分析模块 (源自 AFM/draw_afm_new.py) ---
# ==============================================================================

def angular_median(angles):
    x = np.cos(angles)
    y = np.sin(angles)
    mean_x = np.mean(x, axis=1)
    mean_y = np.mean(y, axis=1)
    return np.arctan2(mean_y, mean_x)

def circle_fit_residuals(params, points):
    xc, yc, R = params
    x, y = points[:, 0], points[:, 1]
    return np.sqrt((x - xc)**2 + (y - yc)**2) - R

def calculate_hopfion_radii_topological(m_field, core_mz_threshold=0.02):
    print("  [绘图] 正在使用拓扑原像法计算R和r...")
    mz = m_field.array[..., 2]
    mz_min = np.min(mz)
    preimage_mask = mz < (mz_min + core_mz_threshold)

    if not np.any(preimage_mask):
        print("  [绘图警告] 未找到拓扑原像，无法计算尺寸。")
        return None, None

    preimage_coords_grid = np.array(np.where(preimage_mask)).T
    preimage_coords_real = m_field.mesh.region.pmin + preimage_coords_grid * m_field.mesh.cell
    xy_coords = preimage_coords_real[:, :2]

    if len(xy_coords) < 3:
        print("  [绘图警告] 核心点太少，无法进行圆形拟合。")
        return None, None
        
    center_guess = np.mean(xy_coords, axis=0)
    radius_guess = np.mean(np.sqrt(np.sum((xy_coords - center_guess)**2, axis=1)))
    
    try:
        res = least_squares(circle_fit_residuals, [center_guess[0], center_guess[1], radius_guess], args=(xy_coords,))
        xc, yc, R_hopfion = res.x
    except Exception as e:
        print(f"  [绘图错误] 核心环圆形拟合失败: {e}")
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
    
    print(f"  [绘图] 计算完成: R≈{R_hopfion*1e9:.2f}nm, r≈{r_hopfion*1e9:.2f}nm")
    return R_hopfion, r_hopfion

def interpolate_colors_for_vertices(m_field, verts):
    indices = (verts - m_field.mesh.region.pmin) / m_field.mesh.cell
    mx_interp = map_coordinates(m_field.array[..., 0], indices.T, order=1, mode='nearest')
    my_interp = map_coordinates(m_field.array[..., 1], indices.T, order=1, mode='nearest')
    return np.arctan2(my_interp, mx_interp)

def _build_sign_field(shape, mode, offsets=(0,0,0)):
    nx, ny, nz = shape[:3]
    ix, iy, iz = np.ogrid[0:nx, 0:ny, 0:nz]
    ox, oy, oz = offsets
    if mode == "checker": return 1 - 2 * (((ix+ox) + (iy+oy) + (iz+oz)) % 2)
    if mode == "layerX": return 1 - 2 * ((ix+ox) % 2)
    if mode == "layerY": return 1 - 2 * ((iy+oy) % 2)
    if mode == "layerZ": return 1 - 2 * ((iz+oz) % 2)
    return np.ones((nx, ny, nz), dtype=np.int8)

def demodulate_afm(m_field, afm_hint="auto"):
    if afm_hint == "none": return m_field, ("none", (0,0,0))
    # 简化的AFM解调，这里我们假设它总是 'checker' 模式，因为初始文件是AFM
    # 在更复杂的场景中，可以加入完整的自动检测
    mode = "checker" 
    sign = _build_sign_field(m_field.array.shape[:3], mode, (0,0,0)).astype(m_field.dtype)[..., None]
    m_demod = df.Field(mesh=m_field.mesh, nvdim=3, value=m_field.array * sign)
    return m_demod, (mode, (0,0,0))

def draw_isosurface(ovf_filename, R_hopfion, r_hopfion, m_field, title_info=""):
    print("  [绘图] 正在生成等值面...")
    verts, faces, _, _ = measure.marching_cubes(volume=m_field.array[..., 2], level=0, spacing=m_field.mesh.cell)
    verts += m_field.mesh.region.pmin
    
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
    cbar.set_label('Angle arctan(my/mx)'), cbar.set_ticks([-np.pi, -np.pi/2, 0, np.pi/2, np.pi])
    cbar.set_ticklabels([r'$-\pi$', r'$-\pi/2$', '0', r'$\\\pi/2$', r'$\\\pi$'])
    
    # 保存图像到 .out 文件夹内
    output_filename = os.path.join(os.path.dirname(ovf_filename), f"plot_{os.path.basename(ovf_filename)}.png")
    plt.savefig(output_filename, dpi=250)
    print(f"  [绘图] 图像已保存到: {output_filename}")
    plt.close(fig) # 关闭图像，释放内存

# ==============================================================================
# --- 3. 仿真与主控制流程 ---
# ==============================================================================

def run_single_simulation(ku1):
    """生成一个mx3文件并运行Mumax3"""
    run_name = f"Ku1_{ku1:.1e}_Ms_{FIXED_MS:.4e}"
    mx3_filename = run_name + ".mx3"
    
    print(f"--- 正在处理: {run_name} ---")

    mx3_content = MX3_TEMPLATE.replace("__KU1__", str(ku1))
    mx3_content = mx3_content.replace("__BETA__", str(FIXED_MS))
    mx3_content = mx3_content.replace("__OVF_FILE__", OVF_FILE)
    mx3_content = mx3_content.replace("__RUN_TIME__", str(RUN_TIME))
    mx3_content = mx3_content.replace("__SAVE_INTERVAL__", str(SAVE_INTERVAL))

    with open(mx3_filename, "w", encoding="utf-8") as f:
        f.write(mx3_content)

    try:
        print(f"  [仿真] 正在运行 Mumax3: {mx3_filename}")
        subprocess.run(
            [MUMAX_EXEC, mx3_filename],
            capture_output=True, text=True, check=True, cwd="."
        )
        print(f"  [仿真] 成功: 结果保存在 {run_name}.out/ 文件夹中")
        return True, run_name + ".out"
    except FileNotFoundError:
        print(f"  *** [仿真错误] 未找到 '{MUMAX_EXEC}'。请检查 MUMAX_EXEC 变量或确保 mumax3 在系统路径中。")
        return False, None
    except subprocess.CalledProcessError as e:
        print(f"  *** [仿真错误] Mumax3 在执行 {mx3_filename} 时出错。")
        print(f"  *** Mumax3 输出:\n{e.stderr}")
        return False, None

def main():
    """主函数：循环执行仿真和绘图"""
    print("=================================================")
    print("====== 一体化工作流：参数扫描 -> 仿真 -> 绘图 ======")
    print("=================================================")
    
    if not os.path.exists(OVF_FILE):
        print(f"*** 错误: 找不到初始状态文件 '{OVF_FILE}'。请确保它在当前目录下。")
        sys.exit(1)

    total_runs = len(Ku1_values)
    run_count = 0

    for ku1 in Ku1_values:
        run_count += 1
        print(f"\n[任务 {run_count}/{total_runs}]")
        
        # --- 步骤 1: 运行仿真 ---
        sim_success, out_dir = run_single_simulation(ku1)
        
        # --- 步骤 2: 如果仿真成功，立即进行绘图 ---
        if sim_success:
            print(f"  [后处理] 开始为 {out_dir} 绘图...")
            
            ovf_files = sorted(glob.glob(os.path.join(out_dir, '*.ovf')))
            if not ovf_files:
                print(f"  [后处理警告] 在 {out_dir} 中找不到 .ovf 文件，跳过绘图。")
                continue
            
            latest_ovf = ovf_files[-1]
            print(f"  [后处理] 找到最新文件: {os.path.basename(latest_ovf)}")

            try:
                raw_field = df.Field.from_file(latest_ovf)
                # 现在的模板是 FM 态，跳过 AFM 解调
                demod_field, (mode, offsets) = demodulate_afm(raw_field, afm_hint="none")
                R, r = calculate_hopfion_radii_topological(demod_field)
                title = f"Ku1={ku1:.1e}, Ms={FIXED_MS:.4e}"
                draw_isosurface(latest_ovf, R, r, demod_field, title_info=title)
            except Exception as e:
                    print(f"  *** [后处理错误] 在为 {latest_ovf} 绘图时发生严重错误: {e}")
            
            time.sleep(1)

    print("\n=================================================")
    print("=== 所有任务完成。 ===")
    print("=================================================")

if __name__ == "__main__":
    main()
