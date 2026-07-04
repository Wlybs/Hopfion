"""
Generate 8 extended amplitude-sweep mx3 files in this directory.

Purpose: extend the existing 6-point amplitude sweep (B=0.05/0.1/0.2/0.5/1.0/2.0T
@ 440GHz, 0.5ns, srcX_vibX) with:
  - 4 new B points @ 440GHz in log-spaced positions (0.3 / 0.7 / 3.0 / 5.0 T)
    so the merged 10-point sweep covers ~2 decades for power-law fitting.
  - 4 multi-freq cross-validation points (200/1000 GHz × 0.5/2.0 T).

All simulations: 0.5ns runtime, autosave 50ps (matches plane_wave existing),
initial state = centered_stability_test/stability_Ku10k.out/m000020.ovf
(Linux absolute path — fixes the legacy Windows path in old plane_wave mx3 files).

Template parameters strictly copied from plane_wave/sw_B1p0T.mx3 except
header / f_sw / B amplitude / initial-state path.
"""

from pathlib import Path

OUT_DIR = Path(__file__).parent
INIT_OVF = "/mnt/d/Research/Hopfion/04_frustrated_fm_foundation/20260105_frustrated_fm/centered_stability_test/stability_Ku10k.out/m000020.ovf"

SIMS = [
    # (filename,                f_GHz, B_T,  desc)
    ("sw_B0p3T.mx3",            440,   0.3,  "Amplitude Sweep: B = 0.3 T, f = 440 GHz, srcX_vibX (extension)"),
    ("sw_B0p7T.mx3",            440,   0.7,  "Amplitude Sweep: B = 0.7 T, f = 440 GHz, srcX_vibX (extension)"),
    ("sw_B3p0T.mx3",            440,   3.0,  "Amplitude Sweep: B = 3.0 T, f = 440 GHz, srcX_vibX (extension)"),
    ("sw_B5p0T.mx3",            440,   5.0,  "Amplitude Sweep: B = 5.0 T, f = 440 GHz, srcX_vibX (extension)"),
    ("sw_f200GHz_B0p5T.mx3",    200,   0.5,  "Amplitude Sweep: B = 0.5 T, f = 200 GHz, srcX_vibX (multi-freq cross)"),
    ("sw_f200GHz_B2p0T.mx3",    200,   2.0,  "Amplitude Sweep: B = 2.0 T, f = 200 GHz, srcX_vibX (multi-freq cross)"),
    ("sw_f1000GHz_B0p5T.mx3",   1000,  0.5,  "Amplitude Sweep: B = 0.5 T, f = 1000 GHz, srcX_vibX (multi-freq cross)"),
    ("sw_f1000GHz_B2p0T.mx3",   1000,  2.0,  "Amplitude Sweep: B = 2.0 T, f = 1000 GHz, srcX_vibX (multi-freq cross)"),
]


def b_to_mx3_literal(b: float) -> str:
    """Render B value with the same style as existing mx3 files (e.g. 0.05, 0.5, 1.0, 2.0)."""
    s = f"{b:.6f}".rstrip("0").rstrip(".")
    return s if "." in s else s + ".0"


TEMPLATE = """// === {desc} ===

CellSize := 0.5e-9
SetGridSize(100, 100, 100)
SetCellSize(CellSize, CellSize, CellSize)

DefRegion(1, XRange(22.5e-9, 25e-9))
DefRegion(2, XRange(-25e-9, -22.5e-9))
DefRegion(3, YRange(22.5e-9, 25e-9))
DefRegion(4, YRange(-25e-9, -22.5e-9))
DefRegion(5, ZRange(22.5e-9, 25e-9))
DefRegion(6, ZRange(-25e-9, -22.5e-9))

DefRegion(7, XRange(-10e-9, -9.5e-9))

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

m.LoadFile("{init_ovf}")

f_sw := {f_ghz}e9 * 2 * pi
B_ext.setRegion(7, Vector({b_lit}*sin(f_sw*t), 0, 0))

autosave(m, 5e-11)
tableautosave(1e-12)
TableAdd(E_Total)

run(0.5e-9)
"""


def main() -> None:
    for fname, f_ghz, b_t, desc in SIMS:
        body = TEMPLATE.format(
            desc=desc,
            init_ovf=INIT_OVF,
            f_ghz=f_ghz,
            b_lit=b_to_mx3_literal(b_t),
        )
        out_path = OUT_DIR / fname
        out_path.write_text(body)
        print(f"wrote {out_path.name}  (f={f_ghz}GHz, B={b_t}T)")


if __name__ == "__main__":
    main()
