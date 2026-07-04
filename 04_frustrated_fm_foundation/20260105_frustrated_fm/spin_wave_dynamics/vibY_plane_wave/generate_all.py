"""
Generate all vibY plane-wave .mx3 scripts.
3 source combos × 4 frequencies × 3 amplitudes = 36 simulations.
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))

SOURCES = {
    "srcX": 'DefRegion(7, XRange(-10e-9, -9.5e-9))',
    "srcY": 'DefRegion(7, YRange(-10e-9, -9.5e-9))',
    "srcZ": 'DefRegion(7, ZRange(-10e-9, -9.5e-9))',
}

FREQS_GHZ = [200, 440, 700, 1100]
AMPS_T = [0.5, 1.0, 2.0]

TEMPLATE = r"""// === vibY Plane Wave: {src}_vibY, f={freq}GHz, B={amp}T ===
// Grid: 100^3, 0.5nm/cell, PBC off (absorbing boundaries)
// Oscillation: Y-polarized (vibY)

CellSize := 0.5e-9
SetGridSize(100, 100, 100)
SetCellSize(CellSize, CellSize, CellSize)

// Absorbing boundary (5-cell slabs, all 6 faces)
DefRegion(1, XRange( 22.5e-9,  25e-9))
DefRegion(2, XRange(-25e-9,  -22.5e-9))
DefRegion(3, YRange( 22.5e-9,  25e-9))
DefRegion(4, YRange(-25e-9,  -22.5e-9))
DefRegion(5, ZRange( 22.5e-9,  25e-9))
DefRegion(6, ZRange(-25e-9,  -22.5e-9))

// Spin wave source
{source_def}

EnableDemag = false

// ── Frustrated FM parameters ──
Ms     := 1.5e5
Msat    = Ms
A_base := 5e-12
Aex     = A_base
Dbulk   = 0
Dind    = 0
Ku1     = 1e4
anisU   = vector(0, 0, 1)

// Damping: low bulk, absorbing boundaries
alpha = 0.001
alpha.setRegion(1, 100)
alpha.setRegion(2, 100)
alpha.setRegion(3, 100)
alpha.setRegion(4, 100)
alpha.setRegion(5, 100)
alpha.setRegion(6, 100)

// ── J4: 4th nearest-neighbor (6 neighbors at 2a) ──
A_J4     := A_base * (-0.082)
Coeff_J4 := A_J4 * 2.0 / (Ms * CellSize * CellSize)
sum_J4   := Add(Shifted(m, 2, 0, 0), Shifted(m, -2, 0, 0))
sum_J4    = Add(sum_J4, Shifted(m, 0, 2, 0))
sum_J4    = Add(sum_J4, Shifted(m, 0, -2, 0))
sum_J4    = Add(sum_J4, Shifted(m, 0, 0, 2))
sum_J4    = Add(sum_J4, Shifted(m, 0, 0, -2))
AddFieldTerm(Mul(Const(Coeff_J4), sum_J4))

// ── J2: Next-nearest-neighbor (12 neighbors at sqrt(2)*a) ──
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

// ── Load centered equilibrated Hopfion ──
m.LoadFile("centered_Ku10k.ovf")

// ── Spin wave: {freq}GHz, Y-polarized (vibY), B={amp}T ──
f_sw  := {freq}e9 * 2 * pi
B_amp := {amp}
B_ext.setRegion(7, Vector(0, B_amp*sin(f_sw*t), 0))

// ── Output: 5ps autosave, 1ns run ──
autosave(m, 5e-12)
tableautosave(1e-11)
TableAdd(E_Total)

run(1e-9)
"""


def amp_str(a):
    return f"{a:.1f}".replace(".", "p").rstrip("0").rstrip("p") or "0"


def main():
    count = 0
    for src, src_def in SOURCES.items():
        for freq in FREQS_GHZ:
            for amp in AMPS_T:
                fname = f"sw_{src}_vibY_f{freq}_B{amp_str(amp)}T.mx3"
                content = TEMPLATE.format(
                    src=src, freq=freq, amp=amp,
                    source_def=src_def,
                )
                path = os.path.join(HERE, fname)
                with open(path, "w", newline="\n") as f:
                    f.write(content)
                count += 1
    print(f"Generated {count} .mx3 scripts in {HERE}")


if __name__ == "__main__":
    main()
