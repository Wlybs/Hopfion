#!/bin/bash
# ================================================================
# run_amplitude_sweep.sh — 振幅扫描一键运行脚本
# 固定: f = 440 GHz, srcX_vibX
# 扫描: B = 0.05, 0.1, 0.2, 0.5, 1.0, 2.0 T (共 6 个点)
#
# 用法:
#   bash run_amplitude_sweep.sh <init_ovf路径> [mumax3路径]
#
# 示例:
#   bash run_amplitude_sweep.sh /data/m000020.ovf
#   bash run_amplitude_sweep.sh /data/m000020.ovf /opt/mumax3/mumax3
# ================================================================

INIT_OVF="${1:?错误: 请提供初始态 OVF 路径。用法: bash $0 <init_ovf路径> [mumax3路径]}"
MUMAX="${2:-mumax3}"
DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=============================================="
echo " Amplitude Sweep: 440 GHz, srcX_vibX"
echo " B = 0.05 / 0.1 / 0.2 / 0.5 / 1.0 / 2.0 T"
echo " Init OVF : $INIT_OVF"
echo " Mumax3   : $MUMAX"
echo " Start    : $(date)"
echo "=============================================="
echo ""

# 验证文件存在
if [ ! -f "$INIT_OVF" ]; then
    echo "错误: 找不到 OVF 文件: $INIT_OVF"
    exit 1
fi
if ! command -v "$MUMAX" &>/dev/null && [ ! -x "$MUMAX" ]; then
    echo "错误: 找不到 mumax3 可执行文件: $MUMAX"
    exit 1
fi

# ── 内嵌 .mx3 生成函数 ──────────────────────────────────────────
gen_mx3() {
    local b_amp=$1
    local label=$2
    local outfile="$DIR/sw_B${label}T.mx3"

    cat > "$outfile" << ENDMX3
// === Amplitude Sweep: B = ${b_amp} T, f = 440 GHz, srcX_vibX ===

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
m.LoadFile("${INIT_OVF}")

// -- Spin wave: f = 440 GHz, B = ${b_amp} T, from region 7 --
f_sw := 440e9 * 2 * pi
B_ext.setRegion(7, Vector(${b_amp}*sin(f_sw*t), 0, 0))

// -- Output --
autosave(m, 5e-11)
tableautosave(1e-12)
TableAdd(E_Total)

run(0.5e-9)
ENDMX3
}

# ── 生成并逐个运行 ───────────────────────────────────────────────
declare -A AMPS=( [0p05]=0.05 [0p1]=0.1 [0p2]=0.2 [0p5]=0.5 [1p0]=1.0 [2p0]=2.0 )

for label in 0p05 0p1 0p2 0p5 1p0 2p0; do
    b_amp="${AMPS[$label]}"
    mx3="$DIR/sw_B${label}T.mx3"

    gen_mx3 "$b_amp" "$label"
    echo ">>> B=${b_amp} T — $(date)"
    "$MUMAX" "$mx3" 2>&1 | tail -3
    echo "<<< B=${b_amp} T done (exit=$?) — $(date)"
    echo ""
done

echo "=============================================="
echo " All done: $(date)"
echo "=============================================="
