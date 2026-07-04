#!/bin/bash
# Supplementary simulations — scheduled via cron
# Includes CUDA environment setup to avoid libcufft.so.11 error

export LD_LIBRARY_PATH=/home/wujiale/.local/cuda-12.8/lib64:$LD_LIBRARY_PATH
export PATH=/home/wujiale/go/bin:$PATH

LOG="/mnt/d/Research/Hopfion/04_frustrated_fm_foundation/20260105_frustrated_fm/spin_wave_dynamics/supplementary_cron_$(date +%Y%m%d_%H%M).log"

{
echo "===== Supplementary simulations start: $(date) ====="
echo "LD_LIBRARY_PATH=$LD_LIBRARY_PATH"
echo "mumax3 path: $(which mumax3)"

# --- 1. Complete freq_switch v3 (if not already done) ---
V3_OUT="/mnt/d/Research/Hopfion/04_frustrated_fm_foundation/20260105_frustrated_fm/spin_wave_dynamics/multisource_control/bidirectional_z/freq_switch_bidirectional_v3.out"
V3_DONE=$(ls "$V3_OUT"/*.ovf 2>/dev/null | wc -l)
if [ "$V3_DONE" -lt 220 ]; then
    echo ""
    echo "=== freq_switch v3: need re-run (found $V3_DONE/220 frames) ==="
    # Remove incomplete output and re-run from scratch
    rm -rf "$V3_OUT"
    cd /mnt/d/Research/Hopfion/04_frustrated_fm_foundation/20260105_frustrated_fm/spin_wave_dynamics/multisource_control/bidirectional_z
    mumax3 freq_switch_bidirectional_v3.mx3
else
    echo "=== freq_switch v3: already complete ($V3_DONE frames), skip ==="
fi

# --- 2. srcZ amplitude sweep ---
cd /mnt/d/Research/Hopfion/04_frustrated_fm_foundation/20260105_frustrated_fm/spin_wave_dynamics/amplitude_sweep/plane_wave_srcZ
for B in 0p1 0p2 0p5 1p0 1p5 2p0; do
    OUT_DIR="sw_srcZ_B${B}T.out"
    if [ -d "$OUT_DIR" ] && [ $(ls "$OUT_DIR"/*.ovf 2>/dev/null | wc -l) -ge 100 ]; then
        echo "=== srcZ B=${B}T: already complete, skip ==="
    else
        rm -rf "$OUT_DIR"
        echo ""
        echo "=== srcZ B=${B}T @1100GHz ==="
        mumax3 "sw_srcZ_B${B}T.mx3"
    fi
done

echo ""
echo "===== All supplementary simulations complete: $(date) ====="

# Self-remove cron entry
crontab -l 2>/dev/null | grep -v "run_supplementary_cron.sh" | crontab -
echo "Cron entry self-removed."

} >> "$LOG" 2>&1
