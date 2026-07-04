import os
import subprocess
import time

# --- 1. 在这里设置你要尝试的参数 ---

# 各向异性 Ku1 的候选值 (单位: J/m^3)
Ku1_values = [5e2]

# Bex 系数 beta 的候选值 (无单位, Bex = A * beta)
beta_values = [0.2511,0.2512,0.2513,0.2514,0.2515,0.2516,0.2517,0.2518,0.2519,0.2521,0.2522,0.2523,0.2524,0.2525,0.2526,0.2527,0.2528,0.2529]

# --- 2. 仿真和文件设置 ---

# Mumax3 可执行文件的路径。如果已经添加到系统路径，保留 "mumax3" 即可
MUMAX_EXEC = "mumax3"

# 用于仿真的 Hopfion 初始态文件 (请确保此文件存在)
OVF_FILE = "hopfion_Qh1_AFM_bigger.ovf"

# 模拟的总时长
RUN_TIME = 5e-9  # 运行 1 ns
SAVE_INTERVAL = 1e-10 # 每 0.1 ns 保存一次

# --- 3. Mumax3 脚本模板 (使用你修正后的版本) ---
MX3_TEMPLATE = """
CellSize	:= 0.5e-9
SetGridSize(100, 100, 100)
SetCellSize(CellSize, CellSize, CellSize)
DefRegion(1, XRange(24.5e-9, 25e-9))
DefRegion(2, XRange(-25e-9, -24.5e-9))
OpenBC		= true
EnableDemag	= false

// MnSi parameters
Ms		:= 1.51e5
Msat		= Ms
A		:= 0.5e-12
Aex		= -A
//Kc1		= 1e3
//anisC1	= vector(1, 0, 0)
//anisC2	= vector(0, 1, 0)
Ku1		= __KU1__
anisU		= vector(0, 0, 1)
alpha		= 0.005
//Dbulk		= 0.115e-3
Bex_coeff	:= __BETA__

// Extra Exchange Field (J4)
mx2	:= Shifted(m,2,0,0)
mx_2	:= Shifted(m,-2,0,0)
my2	:= Shifted(m,0,2,0)
my_2	:= Shifted(m,0,-2,0)
mz2	:= Shifted(m,0,0,2)
mz_2	:= Shifted(m,0,0,-2)
laplacian2 := Add(Add(Add(Add(Add(mx2, mx_2), my2), my_2), mz2), mz_2)

Bex    := A*Bex_coeff
BField	:= Mul( Const(-2.0/Ms * Bex/(CellSize*CellSize)), laplacian2)
BEdens	:= Mul( Const(Bex/(CellSize*CellSize)), Dot(laplacian2, m))

AddFieldTerm(BField)
AddEdensTerm(BEdens)

// Spin Configuration
m.LoadFile("__OVF_FILE__")

autosave(m, __SAVE_INTERVAL__)
tableautosave(1e-11)

run(__RUN_TIME__)
"""

# --- 脚本主体部分 ---

def run_single_simulation(ku1, beta):
    """生成一个mx3文件并运行Mumax3"""
    run_name = f"Ku1_{ku1:.1e}_beta_{beta:.4f}"
    mx3_filename = run_name + ".mx3"
    
    print(f"--- 处理: {run_name} ---")

    # 填充模板
    mx3_content = MX3_TEMPLATE.replace("__KU1__", str(ku1))
    mx3_content = mx3_content.replace("__BETA__", str(beta))
    mx3_content = mx3_content.replace("__OVF_FILE__", OVF_FILE)
    mx3_content = mx3_content.replace("__RUN_TIME__", str(RUN_TIME))
    mx3_content = mx3_content.replace("__SAVE_INTERVAL__", str(SAVE_INTERVAL))

    # 写入mx3文件
    with open(mx3_filename, "w", encoding="utf-8") as f:
        f.write(mx3_content)

    # 运行Mumax3
    try:
        print(f"  运行 Mumax3: {mx3_filename}")
        process = subprocess.run(
            [MUMAX_EXEC, mx3_filename],
            capture_output=True,
            text=True,
            check=True,
            cwd="." # 在当前目录执行
        )
        print(f"  成功: 结果在 {run_name}.out/ 文件夹中")
    except FileNotFoundError:
        print(f"  ***错误: 未找到 '{MUMAX_EXEC}'。请检查 MUMAX_EXEC 变量或确保 mumax3 在系统路径中。")
        return False
    except subprocess.CalledProcessError as e:
        print(f"  ***错误: Mumax3 在执行 {mx3_filename} 时出错。")
        print(f"  ***Mumax3 输出:\n{e.stderr}")
        return False
    return True

def main():
    print("=================================================")
    print("=== Mumax3 参数扫描自动化脚本 (无分析) ===")
    print("=================================================")
    
    total_runs = len(Ku1_values) * len(beta_values)
    run_count = 0

    for ku1 in Ku1_values:
        for beta in beta_values:
            run_count += 1
            print(f"\n[任务 {run_count}/{total_runs}]")
            run_single_simulation(ku1, beta)
            time.sleep(1) # 短暂延时，避免CPU/GPU过载

    print("\n=================================================")
    print("=== 所有仿真任务完成。请手动检查 .out 文件夹 ===")
    print("=================================================")

if __name__ == "__main__":
    main()