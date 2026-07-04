#!/bin/bash
# Run srcZ(-z) baseline simulation
# Created: 2026-04-07
set -e

BASEDIR="/mnt/d/Research/Hopfion/04_frustrated_fm_foundation/20260105_frustrated_fm/spin_wave_dynamics/multisource_control/baseline"
MUMAX="/home/wujiale/go/bin/mumax3"
LOG="$BASEDIR/run_srcZ_neg_$(date +%Y%m%d_%H%M).log"

echo "=== srcZ(-z) baseline start: $(date) ===" | tee "$LOG"
$MUMAX "$BASEDIR/sw_srcZ_neg_f200GHz.mx3" 2>&1 | tee -a "$LOG"
echo "=== srcZ(-z) baseline complete: $(date) ===" | tee "$LOG"
