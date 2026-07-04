import os
import random

def generate_mif_file(filepath, randomSeed_value1, randomSeed_value2, f_sw):
    content = f"""
print(now())
CellSize	:= 0.5e-9
SetGridSize(100, 100, 100)
SetCellSize(CellSize, CellSize, CellSize)
DefRegion(1, XRange(22.5e-9, 25e-9))
DefRegion(2, XRange(-25e-9, -22.5e-9))
DefRegion(3, YRange(22.5e-9, 25e-9))
DefRegion(4, YRange(-25e-9, -22.5e-9))
DefRegion(5, ZRange(22.5e-9, 25e-9))
DefRegion(6, ZRange(-25e-9, -22.5e-9))
DefRegion(7, XRange(-10e-9,-9.5e-9))
OpenBC		= false
EnableDemag	= false

// MnSi parameters
Ms		:= 1.51e5
Msat		= Ms
A		:= 0.5e-12
Aex		= A
//Kc1		= 1e3
//anisC1	= vector(1, 0, 0)
//anisC2	= vector(0, 1, 0)
Ku1		= 1e4
anisU		= vector(0, 0, 1)
alpha		= 0.001
alpha.setRegion(1,100)
alpha.setRegion(2,100)
alpha.setRegion(3,100)
alpha.setRegion(4,100)
alpha.setRegion(5,100)
alpha.setRegion(6,100)
//Dbulk		= 0.115e-3

// Extra Exchange Field (J4)
mx2	:= Shifted(m,2,0,0)
mx_2	:= Shifted(m,-2,0,0)
my2	:= Shifted(m,0,2,0)
my_2	:= Shifted(m,0,-2,0)
mz2	:= Shifted(m,0,0,2)
mz_2	:= Shifted(m,0,0,-2)
laplacian2 := Add(Add(Add(Add(Add(mx2, mx_2), my2), my_2), mz2), mz_2)

Bex	:= A*0.248
BField	:= Mul( Const(-2.0/Ms * Bex/(CellSize*CellSize)), laplacian2)
BEdens	:= Mul( Const(Bex/(CellSize*CellSize)), Dot(laplacian2, m))

AddFieldTerm(BField)
AddEdensTerm(BEdens)

// Spin Configuration
m.LoadFile("stable-state-h+1+2_trans11.ovf")

// Spin Wave
// Start the Simulation
B_sw1	:= 2.0
B_sw2	:= 2.0
f_sw	:= 440e9 * 2*pi
f_curve := 2*pi / 10e-9
phi_shift := pi*25./180
B_ext.setRegion(7, Vector(sin(f_sw*t),0, 0))

autosave(m, 1e-10)
run(25e-9)
print(now())
"""
    with open(filepath, 'w') as file:
        file.write(content)

# 定义保存文件的目录
output_dir = os.getcwd()

# 生成多个 .mx3 文件，每个文件具有不同的自旋波频率
for f_sw_ghz in range(443, 470, 3):  # 频率范围从 100 GHz 到 1000 GHz，每次增加 100 GHz
    f_sw_hz = f_sw_ghz * 1e9  # 转换为 Hz
    filename = f"spinwave_x_f_sw_{f_sw_ghz}e9.mx3"
    filepath = os.path.join(output_dir, filename)

    seven_digit_number1 = random.randint(100000, 999999)
    seven_digit_number2 = random.randint(100000, 999999)
    generate_mif_file(filepath, seven_digit_number1, seven_digit_number2, f_sw_hz)