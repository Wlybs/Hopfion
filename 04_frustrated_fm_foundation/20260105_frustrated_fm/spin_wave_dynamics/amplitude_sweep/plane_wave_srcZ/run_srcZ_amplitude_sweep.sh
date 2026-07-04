#!/bin/bash
# srcZ@1100GHz amplitude sweep
cd /mnt/d/Research/Hopfion/04_frustrated_fm_foundation/20260105_frustrated_fm/spin_wave_dynamics/amplitude_sweep/plane_wave_srcZ

echo "=== Running sw_srcZ_B0p1T.mx3 ==="
mumax3 sw_srcZ_B0p1T.mx3

echo "=== Running sw_srcZ_B0p2T.mx3 ==="
mumax3 sw_srcZ_B0p2T.mx3

echo "=== Running sw_srcZ_B0p5T.mx3 ==="
mumax3 sw_srcZ_B0p5T.mx3

echo "=== Running sw_srcZ_B1p0T.mx3 ==="
mumax3 sw_srcZ_B1p0T.mx3

echo "=== Running sw_srcZ_B1p5T.mx3 ==="
mumax3 sw_srcZ_B1p5T.mx3

echo "=== Running sw_srcZ_B2p0T.mx3 ==="
mumax3 sw_srcZ_B2p0T.mx3

echo "All srcZ amplitude sweep simulations complete!"
