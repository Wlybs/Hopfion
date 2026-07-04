"""
Generate srcZ@1100GHz amplitude sweep .mx3 scripts.
6 amplitudes: 0.1, 0.2, 0.5, 1.0, 1.5, 2.0 T
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))

TEMPLATE = r"""// === srcZ Amplitude Sweep: B = {B_val} T, f = 1100 GHz, srcZ_vibX ===

CellSize := 0.5e-9
SetGridSize(100, 100, 100)
SetCellSize(CellSize, CellSize, CellSize)

// Absorbing boundary regions (alpha=100)
DefRegion(1, XRange(22.5e-9, 25e-9))
DefRegion(2, XRange(-25e-9, -22.5e-9))
DefRegion(3, YRange(22.5e-9, 25e-9))
DefRegion(4, YRange(-25e-9, -22.5e-9))
DefRegion(5, ZRange(22.5e-9, 25e-9))
DefRegion(6, ZRange(-25e-9, -22.5e-9))

// srcZ source at z = -10nm
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

// J4 (4th neighbor)
A_J4     := A_base * (-0.082)
Coeff_J4 := A_J4 * 2.0 / (Ms * CellSize * CellSize)
sum_J4   := Add(Shifted(m, 2, 0, 0), Shifted(m, -2, 0, 0))
sum_J4    = Add(sum_J4, Shifted(m, 0, 2, 0))
sum_J4    = Add(sum_J4, Shifted(m, 0, -2, 0))
sum_J4    = Add(sum_J4, Shifted(m, 0, 0, 2))
sum_J4    = Add(sum_J4, Shifted(m, 0, 0, -2))
AddFieldTerm(Mul(Const(Coeff_J4), sum_J4))

// J2 (2nd neighbor)
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

// Load initial state
m.LoadFile("/mnt/d/Research/Hopfion/04_frustrated_fm_foundation/20260105_frustrated_fm/centered_stability_test/stability_Ku10k.out/m000020.ovf")

f_sw := 1100e9 * 2 * pi
B_ext.setRegion(7, Vector({B_val}*sin(f_sw*t), 0, 0))

autosave(m, 5e-12)    // 5ps
tableautosave(1e-12)
TableAdd(E_Total)

run(0.5e-9)
"""

AMPLITUDES = [0.1, 0.2, 0.5, 1.0, 1.5, 2.0]

for B in AMPLITUDES:
    label = f"{B:.1f}".replace(".", "p")
    fname = f"sw_srcZ_B{label}T.mx3"
    path = os.path.join(HERE, fname)
    with open(path, "w") as f:
        f.write(TEMPLATE.format(B_val=B).lstrip("\n"))
    print(f"Generated: {fname}")

# Generate runner script
run_script = os.path.join(HERE, "run_srcZ_amplitude_sweep.sh")
with open(run_script, "w") as f:
    f.write("#!/bin/bash\n")
    f.write("# srcZ@1100GHz amplitude sweep\n")
    f.write(f"cd {HERE}\n\n")
    for B in AMPLITUDES:
        label = f"{B:.1f}".replace(".", "p")
        fname = f"sw_srcZ_B{label}T.mx3"
        f.write(f'echo "=== Running {fname} ==="\n')
        f.write(f"mumax3 {fname}\n\n")
    f.write('echo "All srcZ amplitude sweep simulations complete!"\n')
os.chmod(run_script, 0o755)
print(f"\nGenerated runner: {run_script}")
