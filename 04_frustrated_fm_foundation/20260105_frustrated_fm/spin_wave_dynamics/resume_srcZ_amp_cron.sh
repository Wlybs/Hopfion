#!/bin/bash
# Resume srcZ amplitude sweep — scheduled via cron
# Remaining: B=1.5T (incomplete), B=2.0T (not started)

export LD_LIBRARY_PATH=/home/wujiale/.local/cuda-12.8/lib64:$LD_LIBRARY_PATH
export PATH=/home/wujiale/go/bin:$PATH

LOG="/mnt/d/Research/Hopfion/04_frustrated_fm_foundation/20260105_frustrated_fm/spin_wave_dynamics/srcZ_amp_resume_$(date +%Y%m%d_%H%M).log"

{
echo "===== srcZ amplitude sweep resume: $(date) ====="
echo "LD_LIBRARY_PATH=$LD_LIBRARY_PATH"
echo "mumax3 path: $(which mumax3)"

cd /mnt/d/Research/Hopfion/04_frustrated_fm_foundation/20260105_frustrated_fm/spin_wave_dynamics/amplitude_sweep/plane_wave_srcZ

for B in 1p5 2p0; do
    OUT_DIR="sw_srcZ_B${B}T.out"
    if [ -d "$OUT_DIR" ] && [ $(ls "$OUT_DIR"/m*.ovf 2>/dev/null | wc -l) -ge 100 ]; then
        echo "=== srcZ B=${B}T: already complete, skip ==="
    else
        rm -rf "$OUT_DIR"
        echo ""
        echo "=== srcZ B=${B}T @1100GHz ==="
        mumax3 "sw_srcZ_B${B}T.mx3"
    fi
done

echo ""
echo "===== All done: $(date) ====="

# Self-remove cron entry
crontab -l 2>/dev/null | grep -v "resume_srcZ_amp_cron.sh" | crontab -
echo "Cron entry self-removed."

} >> "$LOG" 2>&1
