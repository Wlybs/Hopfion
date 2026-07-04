"""
各向异性扩展扫描：Ku1 = [12500, 15000, 17500, 20000, 25000, 30000] J/m³
前置条件: 当前目录为 anisotropy_sweep/, hopfion_Qh1_FM_SMALL.ovf 存在
用法: python run_extended_sweep.py
"""

import os
import subprocess

# ─────────────────────────────────────────────
KU1_EXTENDED = [12500, 15000, 17500, 20000, 25000, 30000]
FIXED_MS     = 1.5e5
OVF_FILE     = "hopfion_Qh1_FM_SMALL.ovf"
RUN_TIME     = 3e-9
SAVE_INTERVAL = 1e-10
MUMAX_EXEC   = "mumax3"

MX3_TEMPLATE = """\
// Ku1 = {ku1} J/m3  (extended anisotropy sweep)
cellsize   := 0.5e-9
Ms_val     := {ms}
A_base     := 5e-12

SetGridSize(100, 100, 100)
SetCellSize(cellsize, cellsize, cellsize)
SetPBC(1, 1, 1)

Msat  = Ms_val
Aex   = A_base
Dbulk = 0
Dind  = 0
Ku1   = {ku1}
anisU = vector(0, 0, 1)
EnableDemag = false
alpha = 0.2

// J4: 第四近邻 (距离 2a)
A_J4    := A_base * (-0.082)
Coeff_J4 := A_J4 * 2.0 / (Ms_val * cellsize * cellsize)
sum_J4  := Add(Shifted(m, 2,0,0), Shifted(m,-2,0,0))
sum_J4   = Add(sum_J4, Shifted(m,0,2,0))
sum_J4   = Add(sum_J4, Shifted(m,0,-2,0))
sum_J4   = Add(sum_J4, Shifted(m,0,0,2))
sum_J4   = Add(sum_J4, Shifted(m,0,0,-2))
B_J4    := Mul(Const(Coeff_J4), sum_J4)
AddFieldTerm(B_J4)

// J2: 次近邻 (距离 sqrt(2)a)
A_J2    := A_base * (-0.164)
Coeff_J2 := A_J2 * 2.0 / (Ms_val * cellsize * cellsize)
sum_J2  := Add(Shifted(m,1,1,0),  Shifted(m,1,-1,0))
sum_J2   = Add(sum_J2, Shifted(m,-1,1,0))
sum_J2   = Add(sum_J2, Shifted(m,-1,-1,0))
sum_J2   = Add(sum_J2, Shifted(m,0,1,1))
sum_J2   = Add(sum_J2, Shifted(m,0,1,-1))
sum_J2   = Add(sum_J2, Shifted(m,0,-1,1))
sum_J2   = Add(sum_J2, Shifted(m,0,-1,-1))
sum_J2   = Add(sum_J2, Shifted(m,1,0,1))
sum_J2   = Add(sum_J2, Shifted(m,1,0,-1))
sum_J2   = Add(sum_J2, Shifted(m,-1,0,1))
sum_J2   = Add(sum_J2, Shifted(m,-1,0,-1))
B_J2    := Mul(Const(Coeff_J2), sum_J2)
AddFieldTerm(B_J2)

m.LoadFile("{ovf}")

autosave(m, {save_interval})
tableautosave(1e-11)
TableAdd(E_Total)
run({run_time})
"""
# ─────────────────────────────────────────────

def run_one(ku1):
    run_name  = f"Ku1_{ku1:.1e}_Ms_{FIXED_MS:.4e}"
    mx3_file  = run_name + ".mx3"

    content = MX3_TEMPLATE.format(
        ku1=ku1, ms=FIXED_MS,
        ovf=OVF_FILE,
        save_interval=SAVE_INTERVAL,
        run_time=RUN_TIME,
    )
    with open(mx3_file, "w") as f:
        f.write(content)

    print(f"[仿真] 运行 {mx3_file} ...")
    try:
        result = subprocess.run(
            [MUMAX_EXEC, mx3_file],
            capture_output=True, text=True, check=True
        )
        print(f"  完成 -> {run_name}.out/")
        return True
    except FileNotFoundError:
        print(f"  错误: 找不到 '{MUMAX_EXEC}'")
        return False
    except subprocess.CalledProcessError as e:
        print(f"  错误: mumax3 失败\n{e.stderr[-500:]}")
        return False


def main():
    assert os.path.exists(OVF_FILE), f"找不到 {OVF_FILE}"
    print("=" * 50)
    print(f"  扩展各向异性扫描  Ku1 = {KU1_EXTENDED}")
    print("=" * 50)
    for ku1 in KU1_EXTENDED:
        out_dir = f"Ku1_{ku1:.1e}_Ms_{FIXED_MS:.4e}.out"
        if os.path.isdir(out_dir):
            print(f"[跳过] {out_dir} 已存在")
            continue
        run_one(ku1)
    print("\n所有仿真完成，请运行 analyze_ani_sweep.py 更新分析结果。")


if __name__ == "__main__":
    main()
