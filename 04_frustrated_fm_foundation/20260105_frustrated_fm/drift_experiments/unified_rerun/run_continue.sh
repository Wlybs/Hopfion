#!/bin/bash
# run_continue.sh — Continue interrupted unified drift experiment
# bg_my_axis_y: resume from 0.9ns checkpoint, run remaining 1.1ns
# bg_mx_axis_x: full 2ns from scratch
set -eo pipefail

MUMAX=/home/wujiale/go/bin/mumax3
DIR="$(cd "$(dirname "$0")" && pwd)"
LOG="$DIR/run_continue.log"

echo "=== Continuation Runner ===" | tee "$LOG"
echo "Start: $(date)" | tee -a "$LOG"

echo "" | tee -a "$LOG"
echo ">>> bg_my_axis_y_continue.mx3 (0.9ns -> 2.0ns) at $(date)" | tee -a "$LOG"
cd "$DIR"
$MUMAX bg_my_axis_y_continue.mx3 2>&1 | tee -a "$LOG"
echo "<<< Finished bg_my_axis_y_continue at $(date)" | tee -a "$LOG"

echo "" | tee -a "$LOG"
echo ">>> bg_mx_axis_x.mx3 (full 2ns) at $(date)" | tee -a "$LOG"
cd "$DIR"
$MUMAX bg_mx_axis_x.mx3 2>&1 | tee -a "$LOG"
echo "<<< Finished bg_mx_axis_x at $(date)" | tee -a "$LOG"

echo "" | tee -a "$LOG"
echo "=== All complete: $(date) ===" | tee -a "$LOG"
