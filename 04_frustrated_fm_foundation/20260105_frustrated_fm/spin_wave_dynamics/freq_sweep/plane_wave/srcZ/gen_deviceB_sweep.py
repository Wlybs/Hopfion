"""
生成 srcZ_vibX 频率扫描 mx3 脚本（B设备用，Windows PowerShell）
频率: 100-1000GHz, 步长100GHz, 排除200GHz(本地跑)
参数: B=1T, Ku=10k, 0.5ns, 10ps autosave
"""

import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "deviceB_package")
os.makedirs(OUT_DIR, exist_ok=True)

TEMPLATE = """\
// === srcZ_vibX: f = {freq} GHz, B=1T, 0.5ns (Device B) ===
// Source: Z boundary (-10nm ~ -9.5nm), Vibration: X direction

CellSize := 0.5e-9
SetGridSize(100, 100, 100)
SetCellSize(CellSize, CellSize, CellSize)

DefRegion(1, XRange(22.5e-9, 25e-9))
DefRegion(2, XRange(-25e-9, -22.5e-9))
DefRegion(3, YRange(22.5e-9, 25e-9))
DefRegion(4, YRange(-25e-9, -22.5e-9))
DefRegion(5, ZRange(22.5e-9, 25e-9))
DefRegion(6, ZRange(-25e-9, -22.5e-9))
DefRegion(7, ZRange(-10e-9, -9.5e-9))

EnableDemag = false
MaxErr = 1e-4

Ms     := 1.5e5
Msat    = Ms
A_base := 5e-12
Aex     = A_base
Dbulk   = 0
Dind    = 0
Ku1     = 1e4
anisU   = vector(0, 0, 1)

alpha = 0.001
alpha.setRegion(1, 100)
alpha.setRegion(2, 100)
alpha.setRegion(3, 100)
alpha.setRegion(4, 100)
alpha.setRegion(5, 100)
alpha.setRegion(6, 100)

A_J4     := A_base * (-0.082)
Coeff_J4 := A_J4 * 2.0 / (Ms * CellSize * CellSize)
sum_J4   := Add(Shifted(m, 2, 0, 0), Shifted(m, -2, 0, 0))
sum_J4    = Add(sum_J4, Shifted(m, 0, 2, 0))
sum_J4    = Add(sum_J4, Shifted(m, 0, -2, 0))
sum_J4    = Add(sum_J4, Shifted(m, 0, 0, 2))
sum_J4    = Add(sum_J4, Shifted(m, 0, 0, -2))
AddFieldTerm(Mul(Const(Coeff_J4), sum_J4))

A_J2     := A_base * (-0.164)
Coeff_J2 := A_J2 * 2.0 / (Ms * CellSize * CellSize)
sum_J2   := Add(Shifted(m, 1, 1, 0), Shifted(m, 1, -1, 0))
sum_J2    = Add(sum_J2, Shifted(m, -1, 1, 0))
sum_J2    = Add(sum_J2, Shifted(m, -1, -1, 0))
sum_J2    = Add(sum_J2, Shifted(m, 0, 1, 1))
sum_J2    = Add(sum_J2, Shifted(m, 0, 1, -1))
sum_J2    = Add(sum_J2, Shifted(m, 0, -1, 1))
sum_J2    = Add(sum_J2, Shifted(m, 0, -1, -1))
sum_J2    = Add(sum_J2, Shifted(m, 1, 0, 1))
sum_J2    = Add(sum_J2, Shifted(m, 1, 0, -1))
sum_J2    = Add(sum_J2, Shifted(m, -1, 0, 1))
sum_J2    = Add(sum_J2, Shifted(m, -1, 0, -1))
AddFieldTerm(Mul(Const(Coeff_J2), sum_J2))

m.LoadFile("initial_state.ovf")

f_sw := {freq}e9 * 2 * pi
B_ext.setRegion(7, Vector(sin(f_sw*t), 0, 0))

autosave(m, 1e-11)
tableautosave(1e-12)
TableAdd(E_Total)

run(0.5e-9)
"""

# 排除200GHz（本地跑），生成其余9个频率
freqs = [f for f in range(100, 1100, 100) if f != 200]

for freq in freqs:
    fname = f"sw_srcZ_f{freq}GHz.mx3"
    with open(os.path.join(OUT_DIR, fname), "w") as f:
        f.write(TEMPLATE.format(freq=freq))
    print(f"  [OK] {fname}")

# 生成 run_all.ps1 (PowerShell)
ps_lines = [
    '# srcZ_vibX Freq Sweep - Device B (Windows PowerShell)',
    '# Usage: Right-click -> Run with PowerShell, or: powershell -ExecutionPolicy Bypass -File run_all.ps1',
    '',
    '$LOG = "run_all.log"',
    '$timestamp = { Get-Date -Format "yyyy-MM-dd HH:mm:ss" }',
    '',
    '# Copy initial state if not present',
    'if (-not (Test-Path "initial_state.ovf")) {',
    '    Write-Host "ERROR: initial_state.ovf not found! Copy it to this directory first." -ForegroundColor Red',
    '    Write-Host "Source: centered_stability_test/stability_Ku10k.out/m000020.ovf"',
    '    pause',
    '    exit 1',
    '}',
    '',
    '$msg = "[$(& $timestamp)] === srcZ_vibX Freq Sweep Device B ==="',
    'Write-Host $msg',
    'Add-Content $LOG $msg',
    '',
]

for freq in freqs:
    mx3 = f"sw_srcZ_f{freq}GHz.mx3"
    ps_lines.extend([
        f'$msg = "[$(& $timestamp)] >>> f={freq}GHz start"',
        'Write-Host $msg -ForegroundColor Cyan',
        'Add-Content $LOG $msg',
        f'mumax3 {mx3} 2>&1 | Tee-Object -Variable output',
        f'$msg = "[$(& $timestamp)] <<< f={freq}GHz done (exit=$LASTEXITCODE)"',
        'Write-Host $msg -ForegroundColor Green',
        'Add-Content $LOG $msg',
        'Add-Content $LOG ($output | Select-Object -Last 5 | Out-String)',
        '',
    ])

ps_lines.extend([
    '$msg = "[$(& $timestamp)] === ALL COMPLETE ==="',
    'Write-Host $msg -ForegroundColor Yellow',
    'Add-Content $LOG $msg',
    '',
    'Write-Host ""',
    'Write-Host "Transfer back: all sw_srcZ_f*GHz.out/ directories" -ForegroundColor Yellow',
    'pause',
])

with open(os.path.join(OUT_DIR, "run_all.ps1"), "w", encoding="utf-8") as f:
    f.write("\n".join(ps_lines) + "\n")

print(f"\n  [OK] run_all.ps1")
print(f"\n生成完毕: {OUT_DIR}/")
print(f"频率点: {freqs}")
print(f"\n使用说明 (Windows B设备):")
print(f"  1. 将 90_external_refs/deviceB_package/ 整个目录复制到 B 设备")
print(f"  2. 将初始态 OVF 复制到 90_external_refs/deviceB_package/ 并命名为 initial_state.ovf")
print(f"     源文件: centered_stability_test/stability_Ku10k.out/m000020.ovf")
print(f"  3. 右键 run_all.ps1 -> Run with PowerShell")
print(f"     或: powershell -ExecutionPolicy Bypass -File run_all.ps1")
print(f"  4. 完成后将所有 .out/ 目录传回本地 srcZ_freq_sweep/")
