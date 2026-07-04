#!/bin/bash
# Run all supplementary simulations sequentially
# 1. freq_switch v3 (1.1ns)
# 2. srcZ amplitude sweep (6 × 0.5ns)

set -e
echo "===== Starting supplementary simulations: $(date) ====="

# --- 1. freq_switch v3 ---
echo ""
echo "=== [1/7] freq_switch_bidirectional_v3 (1.1ns) ==="
cd /mnt/d/Research/Hopfion/04_frustrated_fm_foundation/20260105_frustrated_fm/spin_wave_dynamics/multisource_control/bidirectional_z
mumax3 freq_switch_bidirectional_v3.mx3

# --- 2. srcZ amplitude sweep ---
cd /mnt/d/Research/Hopfion/04_frustrated_fm_foundation/20260105_frustrated_fm/spin_wave_dynamics/amplitude_sweep/plane_wave_srcZ

for B in 0p1 0p2 0p5 1p0 1p5 2p0; do
    echo ""
    echo "=== srcZ B=${B}T @1100GHz ==="
    mumax3 "sw_srcZ_B${B}T.mx3"
done

echo ""
echo "===== All supplementary simulations complete: $(date) ====="
