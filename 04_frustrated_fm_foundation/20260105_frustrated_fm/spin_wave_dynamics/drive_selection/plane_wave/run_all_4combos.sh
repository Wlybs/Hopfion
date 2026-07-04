#!/bin/bash
# === Sequential runner for 4 spin-wave combinations (v2 fixed) ===
# Frustrated FM, Qh=1, Ku1=10k, 440 GHz, 0.5ns each
# Fixed: J2/J4 coefficient sign + centered initial state
# Estimated: ~3.5h per run, total ~14h

DIR="$(cd "$(dirname "$0")" && pwd)"
GPU=0

echo "=============================================="
echo " Spin-Wave 4-Combo Sequential Runner"
echo " Start: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=============================================="

# Combo 1: Source X, Vibration X
echo ""
echo "[$(date +%H:%M:%S)] >>> Combo 1/4: srcX_vibX"
cd "$DIR"
mumax3 -gpu=$GPU sw_srcX_vibX.mx3 > sw_srcX_vibX.log 2>&1
echo "[$(date +%H:%M:%S)] <<< Combo 1 done (exit=$?)"

# Combo 2: Source X, Vibration Z
echo ""
echo "[$(date +%H:%M:%S)] >>> Combo 2/4: srcX_vibZ"
cd "$DIR"
mumax3 -gpu=$GPU sw_srcX_vibZ.mx3 > sw_srcX_vibZ.log 2>&1
echo "[$(date +%H:%M:%S)] <<< Combo 2 done (exit=$?)"

# Combo 3: Source Z, Vibration X
echo ""
echo "[$(date +%H:%M:%S)] >>> Combo 3/4: srcZ_vibX"
cd "$DIR"
mumax3 -gpu=$GPU sw_srcZ_vibX.mx3 > sw_srcZ_vibX.log 2>&1
echo "[$(date +%H:%M:%S)] <<< Combo 3 done (exit=$?)"

# Combo 4: Source Z, Vibration Z
echo ""
echo "[$(date +%H:%M:%S)] >>> Combo 4/4: srcZ_vibZ"
cd "$DIR"
mumax3 -gpu=$GPU sw_srcZ_vibZ.mx3 > sw_srcZ_vibZ.log 2>&1
echo "[$(date +%H:%M:%S)] <<< Combo 4 done (exit=$?)"

echo ""
echo "=============================================="
echo " All 4 combos finished: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=============================================="
