#!/bin/bash
# Auto-generated runner for Unified drift experiment
set -e
MUMAX=/home/wujiale/go/bin/mumax3
DIR="$(cd "$(dirname "$0")" && pwd)"
LOG="$DIR/run_sweep.log"

echo "=== Sweep Runner ===" | tee "$LOG"
echo "Start: $(date)" | tee -a "$LOG"

echo ">>> bg_mz_axis_z.mx3 at $(date)" | tee -a "$LOG"
cd "$DIR" && $MUMAX "bg_mz_axis_z.mx3" 2>&1 | tee -a "$LOG"

echo ">>> bg_mz_axis_x.mx3 at $(date)" | tee -a "$LOG"
cd "$DIR" && $MUMAX "bg_mz_axis_x.mx3" 2>&1 | tee -a "$LOG"

echo ">>> bg_my_axis_y.mx3 at $(date)" | tee -a "$LOG"
cd "$DIR" && $MUMAX "bg_my_axis_y.mx3" 2>&1 | tee -a "$LOG"

echo ">>> bg_mx_axis_x.mx3 at $(date)" | tee -a "$LOG"
cd "$DIR" && $MUMAX "bg_mx_axis_x.mx3" 2>&1 | tee -a "$LOG"

echo "=== Complete: $(date) ===" | tee -a "$LOG"
