#!/bin/bash
# Run remaining point_source simulations sequentially on local GPU
# Created: 2026-04-07
set -e

BASEDIR="/mnt/d/Research/Hopfion/04_frustrated_fm_foundation/20260105_frustrated_fm/spin_wave_dynamics/amplitude_sweep/point_source"
MUMAX="/home/wujiale/go/bin/mumax3"
LOG="$BASEDIR/run_remaining_$(date +%Y%m%d_%H%M).log"

echo "=== Simulation batch start: $(date) ===" | tee "$LOG"

# -------------------------------------------------------
# 1. B500 continuation (HIGH priority, ~7 frames)
# -------------------------------------------------------
echo "[1/4] B500 continuation (0.43ns → 0.50ns)..." | tee -a "$LOG"
$MUMAX "$BASEDIR/ps_srcX_vibX_1100GHz_B500_continue.mx3" 2>&1 | tee -a "$LOG"

# Merge continuation frames into original .out
ORIG="$BASEDIR/ps_srcX_vibX_1100GHz_B500.out"
CONT="$BASEDIR/ps_srcX_vibX_1100GHz_B500_continue.out"
if [ -d "$CONT" ]; then
    echo "  Merging continuation frames into original .out..." | tee -a "$LOG"
    # Skip m000000 (duplicate of original m000043), copy m000001-m000007 as m000044-m000050
    for i in $(seq 1 7); do
        src_idx=$(printf "m%06d.ovf" $i)
        dst_idx=$(printf "m%06d.ovf" $((43 + i)))
        if [ -f "$CONT/$src_idx" ]; then
            cp -f "$CONT/$src_idx" "$ORIG/$dst_idx"
            echo "    Copied $src_idx → $dst_idx" | tee -a "$LOG"
        fi
    done
    # Append table data (skip header line from continuation)
    if [ -f "$CONT/table.txt" ]; then
        tail -n +2 "$CONT/table.txt" >> "$ORIG/table.txt"
        echo "  Table data appended." | tee -a "$LOG"
    fi
    echo "  B500 merge complete. Total frames: $(ls "$ORIG"/m*.ovf | wc -l)" | tee -a "$LOG"
fi
echo "[1/4] B500 DONE at $(date)" | tee -a "$LOG"

# -------------------------------------------------------
# 2. B700 (MEDIUM priority)
# -------------------------------------------------------
echo "[2/4] B700 (0.5ns, full run)..." | tee -a "$LOG"
$MUMAX "$BASEDIR/ps_srcX_vibX_1100GHz_B700.mx3" 2>&1 | tee -a "$LOG"
echo "[2/4] B700 DONE at $(date)" | tee -a "$LOG"

# -------------------------------------------------------
# 3. B1000 (MEDIUM priority)
# -------------------------------------------------------
echo "[3/4] B1000 (0.5ns, full run)..." | tee -a "$LOG"
$MUMAX "$BASEDIR/ps_srcX_vibX_1100GHz_B1000.mx3" 2>&1 | tee -a "$LOG"
echo "[3/4] B1000 DONE at $(date)" | tee -a "$LOG"

# -------------------------------------------------------
# 4. B2000 (MEDIUM priority)
# -------------------------------------------------------
echo "[4/4] B2000 (0.5ns, full run)..." | tee -a "$LOG"
$MUMAX "$BASEDIR/ps_srcX_vibX_1100GHz_B2000.mx3" 2>&1 | tee -a "$LOG"
echo "[4/4] B2000 DONE at $(date)" | tee -a "$LOG"

echo "=== All amplitude_sweep sims complete: $(date) ===" | tee -a "$LOG"
