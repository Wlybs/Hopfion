#!/bin/bash
# 串行运行 4 个 bulk 稳定性测试仿真
# 顺序: pbc_demag → pbc_nodemag → nopbc_demag → nopbc_nodemag
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CACHE_DIR="/mnt/d/Research/Hopfion/.mumax3_cache"
LOG_DIR="$SCRIPT_DIR/run_logs"
mkdir -p "$LOG_DIR"

SIMS=(
    "run_pbc_demag"
    "run_pbc_nodemag"
    "run_nopbc_demag"
    "run_nopbc_nodemag"
)

for SIM in "${SIMS[@]}"; do
    echo "=============================="
    echo "Starting: $SIM"
    echo "Time: $(date)"
    echo "=============================="
    cd "$SCRIPT_DIR"
    mumax3 -cache "$CACHE_DIR" -s "${SIM}.mx3" > "$LOG_DIR/${SIM}.log" 2>&1
    echo "Done: $SIM at $(date)"
    echo ""
done

echo "All simulations completed."
