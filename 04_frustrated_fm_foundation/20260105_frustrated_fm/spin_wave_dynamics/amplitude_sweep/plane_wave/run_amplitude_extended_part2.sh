#!/bin/bash
# ================================================================
# run_amplitude_extended_part2.sh — PART 2: 剩余 6 sim
# 顺序串行 0.5ns/srcX_vibX (单 GPU)
#   - 2 × 440 GHz  B 扩展:   B = 3.0 / 5.0 T
#   - 2 × 200 GHz  多频交叉: B = 0.5 / 2.0 T
#   - 2 × 1000 GHz 多频交叉: B = 0.5 / 2.0 T
# 日志: run_amplitude_extended_part2.log
# 调度: 由 scheduler.sh 在 2026-05-15 00:00 启动
# ================================================================

set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

MUMAX="${MUMAX:-/home/wujiale/go/bin/mumax3}"
export LD_LIBRARY_PATH="${LD_LIBRARY_PATH:-/home/wujiale/.local/cuda-12.8/lib64}"

LOG=run_amplitude_extended_part2.log
{
    echo "=============================================="
    echo "PART 2 Started: $(date '+%F %T')"
    echo "mumax3 : $MUMAX"
    echo "LD     : $LD_LIBRARY_PATH"
    echo "DIR    : $DIR"
    echo "=============================================="
} >> "$LOG"

SIMS=(
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

echo "=== [$(date '+%F %T')] PART 2 all 6 sims done ===" >> "$LOG"
