#!/bin/bash
# run_drift_unified.sh — Sequential runner for 4 unified drift experiments
# All share: Ku1=0, alpha=0.2, R3r2 initial, 2ns, autosave=100ps, table=10ps
set -e

MUMAX=/home/wujiale/go/bin/mumax3
DIR="$(cd "$(dirname "$0")" && pwd)"
LOG="$DIR/run_drift_unified.log"

echo "=== Unified Drift Experiment Runner ===" | tee "$LOG"
echo "Start time: $(date)" | tee -a "$LOG"
echo "Working dir: $DIR" | tee -a "$LOG"
echo "" | tee -a "$LOG"

for mx3 in bg_mz_axis_z.mx3 bg_mz_axis_x.mx3 bg_my_axis_y.mx3 bg_mx_axis_x.mx3; do
    echo ">>> Running $mx3 at $(date)" | tee -a "$LOG"
    cd "$DIR"
    $MUMAX "$mx3" 2>&1 | tee -a "$LOG"
    echo "<<< Finished $mx3 at $(date)" | tee -a "$LOG"
    echo "" | tee -a "$LOG"
done

echo "=== All 4 simulations complete ===" | tee -a "$LOG"
echo "End time: $(date)" | tee -a "$LOG"
