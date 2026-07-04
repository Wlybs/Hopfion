#!/bin/bash
# Run V2 drive-release test: gradient vs uniform control
BASEDIR="/mnt/d/Research/Hopfion/08_lif_neuron_device_application/lif_neuron_hopfion/gradient_ku_verification/drive_release_test"
LOG="$BASEDIR/run_v2_$(date +%Y%m%d_%H%M).log"

echo "=== V2 Drive-Release Test ===" >> "$LOG"
echo "Start: $(date)" >> "$LOG"

echo "[1/2] Running gradient Ku experiment..." >> "$LOG"
mumax3 "$BASEDIR/with_gradient/gradient_ku_drive_release.mx3" >> "$LOG" 2>&1
echo "Gradient done: $(date)" >> "$LOG"

echo "[2/2] Running uniform control..." >> "$LOG"
mumax3 "$BASEDIR/uniform_control/uniform_ku_drive_release.mx3" >> "$LOG" 2>&1
echo "Uniform done: $(date)" >> "$LOG"

echo "=== All V2 simulations complete ===" >> "$LOG"
