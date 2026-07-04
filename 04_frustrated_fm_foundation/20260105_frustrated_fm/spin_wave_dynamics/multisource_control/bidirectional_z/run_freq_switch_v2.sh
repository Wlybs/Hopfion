#!/bin/bash
# Run freq_switch_bidirectional_v2 simulation
# Scheduled to run 3h after creation (via at/cron)
set -e

BASEDIR="/mnt/d/Research/Hopfion/04_frustrated_fm_foundation/20260105_frustrated_fm/spin_wave_dynamics/multisource_control/bidirectional_z"
MUMAX="/home/wujiale/go/bin/mumax3"
LOG="$BASEDIR/freq_switch_v2_$(date +%Y%m%d_%H%M).log"

echo "=== freq_switch_bidirectional_v2 start: $(date) ===" | tee "$LOG"
$MUMAX "$BASEDIR/freq_switch_bidirectional_v2.mx3" 2>&1 | tee -a "$LOG"
echo "=== freq_switch_bidirectional_v2 complete: $(date) ===" | tee -a "$LOG"
