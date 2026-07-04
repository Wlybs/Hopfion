"""
生成 200GHz 幅度扫描 mx3 脚本（B设备用，Windows PowerShell）
固定: f = 200 GHz, srcX_vibX
扫描: B 振幅 = 0.05, 0.1, 0.2, 0.5, 1.0, 2.0 T (共 6 个点)
运行: 0.5 ns / 点，autosave = 10ps
初始态: initial_state.ovf（相对路径，B设备本地放置）
"""

import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "deviceB_200GHz")
os.makedirs(OUT_DIR, exist_ok=True)

AMPS = [0.05, 0.1, 0.2, 0.5, 1.0, 2.0]  # Tesla

TEMPLATE = """\
// === Amplitude Sweep: B = {b_amp} T, f = 200 GHz, srcX_vibX (Device B) ===

CellSize := 0.5e-9
SetGridSize(100, 100, 100)
SetCellSize(CellSize, CellSize, CellSize)

// Absorbing boundary regions (5-cell thick slabs on all 6 faces)
DefRegion(1, XRange(22.5e-9, 25e-9))
DefRegion(2, XRange(-25e-9, -22.5e-9))
DefRegion(3, YRange(22.5e-9, 25e-9))
DefRegion(4, YRange(-25e-9, -22.5e-9))
DefRegion(5, ZRange(22.5e-9, 25e-9))
DefRegion(6, ZRange(-25e-9, -22.5e-9))

// Spin wave source: thin slab at x = -10 nm
DefRegion(7, XRange(-10e-9, -9.5e-9))

EnableDemag = false
MaxErr = 1e-4

// -- Frustrated FM parameters --
Ms     := 1.5e5
Msat    = Ms
A_base := 5e-12
Aex     = A_base
Dbulk   = 0
Dind    = 0
Ku1     = 1e4
anisU   = vector(0, 0, 1)

// Damping: low in bulk, absorbing at boundaries
alpha = 0.001
alpha.setRegion(1, 100)
alpha.setRegion(2, 100)
alpha.setRegion(3, 100)
alpha.setRegion(4, 100)
alpha.setRegion(5, 100)
alpha.setRegion(6, 100)

// -- J4: 4th nearest-neighbor --
A_J4     := A_base * (-0.082)
Coeff_J4 := A_J4 * 2.0 / (Ms * CellSize * CellSize)
sum_J4   := Add(Shifted(m, 2, 0, 0), Shifted(m, -2, 0, 0))
sum_J4    = Add(sum_J4, Shifted(m, 0, 2, 0))
sum_J4    = Add(sum_J4, Shifted(m, 0, -2, 0))
sum_J4    = Add(sum_J4, Shifted(m, 0, 0, 2))
sum_J4    = Add(sum_J4, Shifted(m, 0, 0, -2))
AddFieldTerm(Mul(Const(Coeff_J4), sum_J4))

// -- J2: Next-nearest-neighbor --
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

// -- Load initial state (relative path, copy to this directory on B-device) --
m.LoadFile("initial_state.ovf")

// -- Spin wave: f = 200 GHz, B = {b_amp} T, srcX_vibX --
f_sw := 200e9 * 2 * pi
B_ext.setRegion(7, Vector({b_amp}*sin(f_sw*t), 0, 0))

// -- Output --
autosave(m, 1e-11)
tableautosave(1e-12)
TableAdd(E_Total)

run(0.5e-9)
"""


def amp_to_label(b):
    """0.05 -> '0p05', 0.1 -> '0p1', 1.0 -> '1p0'"""
    s = f"{b:.2f}".rstrip("0")
    if s.endswith("."):
        s += "0"
    return s.replace(".", "p")


def main():
    print(f"Generating {len(AMPS)} .mx3 files for 200GHz amplitude sweep ...")
    for b in AMPS:
        label = amp_to_label(b)
        fname = f"sw_B{label}T.mx3"
        fpath = os.path.join(OUT_DIR, fname)
        with open(fpath, "w") as fp:
            fp.write(TEMPLATE.format(b_amp=b))
        print(f"  [OK] {fname}  (B = {b} T)")

    # Generate PowerShell run_all.ps1
    ps_lines = [
        "# srcX_vibX Amplitude Sweep 200GHz - Device B (Windows PowerShell)",
        "# Usage: Right-click -> Run with PowerShell, or: powershell -ExecutionPolicy Bypass -File run_all.ps1",
        "",
        '$LOG = "run_all.log"',
        '$timestamp = { Get-Date -Format "yyyy-MM-dd HH:mm:ss" }',
        "",
        "# Check initial state",
        'if (-not (Test-Path "initial_state.ovf")) {',
        '    Write-Host "ERROR: initial_state.ovf not found! Copy it to this directory first." -ForegroundColor Red',
        '    Write-Host "Source: centered_stability_test/stability_Ku10k.out/m000020.ovf"',
        "    pause",
        "    exit 1",
        "}",
        "",
        '$msg = "[$(& $timestamp)] === srcX_vibX 200GHz Amplitude Sweep ==="',
        "Write-Host $msg",
        "Add-Content $LOG $msg",
        "",
    ]

    for b in AMPS:
        label = amp_to_label(b)
        mx3 = f"sw_B{label}T.mx3"
        ps_lines.extend([
            f'$msg = "[$(& $timestamp)] >>> B={b}T start"',
            "Write-Host $msg -ForegroundColor Cyan",
            "Add-Content $LOG $msg",
            f"mumax3 {mx3} 2>&1 | Tee-Object -Variable output",
            f'$msg = "[$(& $timestamp)] <<< B={b}T done (exit=$LASTEXITCODE)"',
            "Write-Host $msg -ForegroundColor Green",
            "Add-Content $LOG $msg",
            "Add-Content $LOG ($output | Select-Object -Last 5 | Out-String)",
            "",
        ])

    ps_lines.extend([
        '$msg = "[$(& $timestamp)] === ALL COMPLETE ==="',
        "Write-Host $msg -ForegroundColor Yellow",
        "Add-Content $LOG $msg",
        "",
        'Write-Host ""',
        'Write-Host "Transfer back: all sw_B*T.out/ directories" -ForegroundColor Yellow',
        "pause",
    ])

    ps_path = os.path.join(OUT_DIR, "run_all.ps1")
    with open(ps_path, "w", encoding="utf-8") as f:
        f.write("\n".join(ps_lines) + "\n")
    print(f"  [OK] run_all.ps1")

    print(f"\n生成完毕: {OUT_DIR}/")
    print(f"B幅度点: {AMPS}")
    print(f"\n使用说明 (Windows B设备):")
    print(f"  1. 将 deviceB_200GHz/ 整个目录复制到 B 设备")
    print(f"  2. 将初始态 OVF 复制到 deviceB_200GHz/ 并命名为 initial_state.ovf")
    print(f"     源文件: centered_stability_test/stability_Ku10k.out/m000020.ovf")
    print(f"  3. 右键 run_all.ps1 -> Run with PowerShell")
    print(f"  4. 完成后将所有 .out/ 目录传回本地 amplitude_sweep/deviceB_200GHz/")


if __name__ == "__main__":
    main()
