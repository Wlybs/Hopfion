import os
import glob
import subprocess
import time
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import discretisedfield as df

# ==============================================================================
# --- 1. 参数定义 ---
# ==============================================================================

L_helical = 70e-9         
A_exchange = 8.78e-12     
D_bulk = 4 * np.pi * A_exchange / L_helical

DIAMETER = 3 * L_helical  
HEIGHT = L_helical        
CELL_SIZE = 2e-9          

Nx = int(DIAMETER / CELL_SIZE)
Ny = int(DIAMETER / CELL_SIZE)
Nz = int(HEIGHT / CELL_SIZE)

MUMAX_EXEC = "mumax3"
INIT_OVF_NAME = "init_hopfion.ovf"

# ==============================================================================
# --- 2. 核心功能: Python 生成初始态 (修复版) ---
# ==============================================================================

def generate_hopfion_ovf(filename):
    print(f"--> [Python] 正在计算 Hopfion 初始态...")
    
    # 1. 创建网格
    p1 = (-DIAMETER/2, -DIAMETER/2, -HEIGHT/2)
    p2 = (DIAMETER/2,  DIAMETER/2,  HEIGHT/2)
    cell = (CELL_SIZE, CELL_SIZE, CELL_SIZE)
    
    try:
        mesh = df.Mesh(p1=p1, p2=p2, cell=cell)
    except TypeError:
        region = df.Region(p1=p1, p2=p2)
        mesh = df.Mesh(region=region, cell=cell)
    
    # 2. 定义 Ansatz (确保返回单位矢量)
    k = 2 * np.pi / L_helical
    z_top_limit = HEIGHT/2 - CELL_SIZE * 1.01
    z_bottom_limit = -HEIGHT/2 + CELL_SIZE * 1.01
    R_cutoff = L_helical 

    def ansatz(point):
        x, y, z = point
        rho = np.sqrt(x**2 + y**2)
        phi = np.arctan2(y, x)
        
        # 几何裁切 & 边界钉扎
        if rho > DIAMETER/2 or z > z_top_limit or z < z_bottom_limit or rho > R_cutoff:
            return (0, 0, 1) # 背景向 +z
            
        # 内部 Sutcliffe Ansatz
        mx = np.sin(k * rho) * np.sin(phi)
        my = -np.sin(k * rho) * np.cos(phi)
        mz = np.cos(k * rho)
        return (mx, my, mz)

    # 3. 生成场
    # [关键修复1] norm=None。生成单位矢量场，不要乘以 Msat (384e3)。
    # Mumax3 的 m.LoadFile 期望的是单位矢量。
    try:
        field = df.Field(mesh, nvdim=3, value=ansatz, norm=None)
    except TypeError:
        field = df.Field(mesh, dim=3, value=ansatz, norm=None)
    
    # 4. 保存为 OVF (文本格式)
    # [关键修复2] 强制使用 representation='txt' 避免二进制乱码
    if os.path.exists(filename):
        os.remove(filename)
    
    try:
        # 新版 discretisedfield
        field.to_file(filename, representation='txt')
    except:
        try:
            # 旧版兼容
            field.write(filename, representation='txt')
        except:
            # 最坏情况，如果不接受参数，就直接保存
            field.to_file(filename)
            
    print(f"--> [Python] 初始态已保存: {filename} (Text Format)")

    # 5. [新增] 立即画图自检
    # 这一步是为了确认 Python 生成的数据本身是对的
    try:
        print("--> [自检] 正在生成初始态切片预览 check_init_python.png ...")
        # 取 z=0 切面
        plane = field.plane('z')
        # 绘制 mz
        fig, ax = plt.subplots(figsize=(6, 5))
        plane.z.mpl.scalar(ax=ax, cmap='coolwarm', filter_field=plane.norm)
        plt.title("Python Generated Initial State (Mz @ z=0)")
        plt.savefig("check_init_python.png", dpi=150)
        plt.close()
        print("--> [自检] 预览图已保存，请查看 check_init_python.png 是否平滑。")
    except Exception as e:
        print(f"--> [自检警告] 绘图失败: {e}")


# ==============================================================================
# --- 3. Mumax3 脚本模板 ---
# ==============================================================================

MX3_TEMPLATE = f"""
// --- 1. 网格与几何 ---
Nx := {Nx}
Ny := {Ny}
Nz := {Nz}
SetGridSize(Nx, Ny, Nz)
SetCellSize({CELL_SIZE}, {CELL_SIZE}, {CELL_SIZE})

Diameter := {DIAMETER}
Height   := {HEIGHT}
Cyl      := Cylinder(Diameter, Height)
SetGeom(Cyl)

// --- 2. 材料参数 ---
Msat  = 384e3  // Msat 在这里定义，OVF 里只存方向
Aex   = {A_exchange}
Dbulk = {D_bulk}
Ku1   = 0
EnableDemag = false 

// --- 3. 边界条件 ---
LayerThick := {CELL_SIZE}
TopLayer    := Layer(Nz-1)
BottomLayer := Layer(0)
Caps        := TopLayer.add(BottomLayer)
defRegion(1, Caps)
frozenspins.setRegion(1, 1)

// --- 4. 初始状态 ---
LoadFile("{INIT_OVF_NAME}")
// 此时加载的是单位矢量场，Mumax3 会自动将其应用到 Msat

// --- 5. 弛豫 ---
TableAutoSave(1e-11)
alpha = 0.5
Run(1e-9)

saveas(m, "hopfion_final")
"""

# ==============================================================================
# --- 4. 运行流程 ---
# ==============================================================================

def run_simulation():
    mx3_filename = "Sutcliffe_Bloch_Hopfion.mx3"
    
    # 1. 生成初始态
    try:
        generate_hopfion_ovf(INIT_OVF_NAME)
    except Exception as e:
        print(f"终止: {e}")
        return

    # 2. 写入脚本
    with open(mx3_filename, "w", encoding="utf-8") as f:
        f.write(MX3_TEMPLATE)
    
    print(f"--> 生成脚本: {mx3_filename}")
    
    # 3. 运行 Mumax3
    try:
        subprocess.run([MUMAX_EXEC, mx3_filename], check=True)
        print("--> Mumax3 运行完成")
    except Exception as e:
        print(f"🔴 运行失败: {e}")

if __name__ == "__main__":
    run_simulation()