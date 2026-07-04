#!/bin/bash
# ================================================================
# run_amplitude_extended.sh — 扩展振幅扫描 + 多频交叉
# 8 sim @ 0.5ns srcX_vibX (单 GPU 顺序串行)
#   - 4 × 440 GHz  B 扩展:   B = 0.3 / 0.7 / 3.0 / 5.0 T
#   - 2 × 200 GHz  多频交叉: B = 0.5 / 2.0 T
#   - 2 × 1000 GHz 多频交叉: B = 0.5 / 2.0 T
# 日志: run_amplitude_extended.log
# ================================================================

set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

MUMAX="${MUMAX:-/home/wujiale/go/bin/mumax3}"
export LD_LIBRARY_PATH="${LD_LIBRARY_PATH:-/home/wujiale/.local/cuda-12.8/lib64}"

LOG=run_amplitude_extended.log
{
    echo "=============================================="
    echo "Started: $(date '+%F %T')"
    echo "mumax3 : $MUMAX"
    echo "LD     : $LD_LIBRARY_PATH"
    echo "DIR    : $DIR"
    echo "=============================================="
} >> "$LOG"

SIMS=(
    sw_B0p3T
    sw_B0p7T
    sw_B3p0T
    sw_B5p0T
    sw_f200GHz_B0p5T
    sw_f200GHz_B2p0T
    sw_f1000GHz_B0p5T
    sw_f1000GHz_B2p0T
)

for f in "${SIMS[@]}"; do
    echo "--- [$(date '+%F %T')] starting $f.mx3 ---" >> "$LOG"
    if "$MUMAX" "${f}.mx3" >> "$LOG" 2>&1; then
        echo "--- [$(date '+%F %T')] finished $f OK ---" >> "$LOG"
    else
        rc=$?
        echo "--- [$(date '+%F %T')] $f FAILED rc=$rc ---" >> "$LOG"
    fi
done

echo "=== [$(date '+%F %T')] all 8 sims done ===" >> "$LOG"
