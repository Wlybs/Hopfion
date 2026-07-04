"""
freq_sweep_dense — 加密帧版频率扫描 .mx3 生成脚本

与 freq_sweep_coarse 参数完全一致（0.2ns, B=1T, srcX_vibX），
唯一区别：autosave 从 200ps 改为 10ps（20帧/点），支持 r(t) 轨迹分析。

生成全部 10 个频率点的脚本，本地跑 500-900GHz，设备B跑 100-400+1000GHz。
"""

import os

HERE = os.path.dirname(os.path.abspath(__file__))
FREQS_GHZ = list(range(100, 1100, 100))
INIT_OVF = ("/mnt/d/Research/Hopfion/04_frustrated_fm_foundation/20260105_frustrated_fm/"
             "centered_stability_test/stability_Ku10k.out/m000020.ovf")

TEMPLATE = """\
// === Frequency Sweep (Dense): f = {freq_ghz} GHz, srcX_vibX ===

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

// -- J4: 4th nearest-neighbor (6 neighbors at 2a) --
A_J4     := A_base * (-0.082)
Coeff_J4 := A_J4 * 2.0 / (Ms * CellSize * CellSize)
sum_J4   := Add(Shifted(m, 2, 0, 0), Shifted(m, -2, 0, 0))
sum_J4    = Add(sum_J4, Shifted(m, 0, 2, 0))
sum_J4    = Add(sum_J4, Shifted(m, 0, -2, 0))
sum_J4    = Add(sum_J4, Shifted(m, 0, 0, 2))
sum_J4    = Add(sum_J4, Shifted(m, 0, 0, -2))
AddFieldTerm(Mul(Const(Coeff_J4), sum_J4))

// -- J2: Next-nearest-neighbor (12 neighbors at sqrt(2)*a) --
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

// -- Load centered equilibrated Hopfion (Ku10k, 1ns relaxed) --
m.LoadFile("{init_ovf}")

// -- Spin wave: x-direction, {freq_ghz} GHz, from region 7 --
f_sw := {freq_ghz}e9 * 2 * pi
B_ext.setRegion(7, Vector(sin(f_sw*t), 0, 0))

// -- Output: 10ps autosave for trajectory analysis --
autosave(m, 1e-11)    // 10ps -> 20 frames over 0.2ns
tableautosave(1e-12)   // 1ps resolution
TableAdd(E_Total)

run(0.2e-9)
"""


def main():
    print(f"Generating {len(FREQS_GHZ)} dense .mx3 scripts ...")
    for f in FREQS_GHZ:
        fname = f"sw_f{f}GHz.mx3"
        fpath = os.path.join(HERE, fname)
        with open(fpath, "w") as fp:
            fp.write(TEMPLATE.format(freq_ghz=f, init_ovf=INIT_OVF))
        print(f"  {fname}")
    print("Done.")


if __name__ == "__main__":
    main()
