#!/bin/bash
BASEDIR="/mnt/d/Research/Hopfion/08_lif_neuron_device_application/lif_neuron_hopfion/lif_cycle_demo"
LOG="$BASEDIR/run_phase2_$(date +%Y%m%d_%H%M).log"

echo "=== Phase 2: LIF Cycle Simulations ===" >> "$LOG"
echo "Start: $(date)" >> "$LOG"

echo "[1/2] Pulse train (F1)..." >> "$LOG"
mumax3 "$BASEDIR/pulse_train_integrate/lif_pulse_train.mx3" >> "$LOG" 2>&1
echo "F1 done: $(date)" >> "$LOG"

echo "[2/2] Sub-threshold (F3, B=0.1T)..." >> "$LOG"
mumax3 "$BASEDIR/threshold_comparison/subthreshold_B0p1T.mx3" >> "$LOG" 2>&1
echo "F3 done: $(date)" >> "$LOG"

echo "=== Phase 2 complete ===" >> "$LOG"
