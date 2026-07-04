#!/bin/bash
# Sequential stability tests for centered Hopfion (Ku=0, 10k, 50k)
# Each ~7h on frustrated FM, total ~21h

DIR="/mnt/d/Research/Hopfion/04_frustrated_fm_foundation/20260105_frustrated_fm/centered_stability_test"
LOG="$DIR/run_log.txt"

echo "=== Centered Hopfion Stability Tests ===" | tee "$LOG"
echo "Started: $(date)" | tee -a "$LOG"

for script in stability_Ku0.mx3 stability_Ku10k.mx3 stability_Ku50k.mx3; do
    echo "" | tee -a "$LOG"
    echo "--- Running $script ---" | tee -a "$LOG"
    echo "Start: $(date)" | tee -a "$LOG"

    mumax3 -gpu=0 "$DIR/$script" 2>&1 | tee -a "$LOG"

    echo "End: $(date)" | tee -a "$LOG"
    echo "Exit code: $?" | tee -a "$LOG"
done

echo "" | tee -a "$LOG"
echo "=== All tests completed: $(date) ===" | tee -a "$LOG"
