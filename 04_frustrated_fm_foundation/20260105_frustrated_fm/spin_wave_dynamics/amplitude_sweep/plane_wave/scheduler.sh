#!/bin/bash
# ================================================================
# scheduler.sh — sleep until 2026-05-15 00:00:00 +0800, then launch part2
# 由用户手动 nohup 启动, session 死后仍跑
#
# ⚠️ WSL 限制: 电脑睡眠会冻结 sleep, 唤醒后 sleep 可能延迟启动而不立即.
#    确保电脑整夜开机不睡眠, 或预期最多延迟 = 睡眠时长.
# ================================================================

TARGET_TS=1778774400      # 2026-05-15 00:00:00 +0800 (Unix epoch)
PLANE_DIR=/mnt/d/Research/Hopfion/04_frustrated_fm_foundation/20260105_frustrated_fm/spin_wave_dynamics/amplitude_sweep/plane_wave
LOG=$PLANE_DIR/scheduler.log
PART2=$PLANE_DIR/run_amplitude_extended_part2.sh
SENTINEL=$PLANE_DIR/.part2_launched

# 防重复启动
if [ -f "$SENTINEL" ]; then
    echo "[$(date '+%F %T')] sentinel exists, part2 already launched, exit" >> $LOG
    exit 0
fi

NOW=$(date +%s)
DELAY=$(( TARGET_TS - NOW ))
echo "[$(date '+%F %T')] scheduler started: PID $$, target=2026-05-15 00:00, delay=${DELAY}s" >> $LOG

if [ $DELAY -gt 0 ]; then
    sleep $DELAY
fi

# 二次确认时间已到 (防止 WSL 睡眠跳过)
NOW2=$(date +%s)
if [ $NOW2 -lt $TARGET_TS ]; then
    REMAINING=$(( TARGET_TS - NOW2 ))
    echo "[$(date '+%F %T')] sleep underran (likely WSL suspend), still need ${REMAINING}s, second sleep..." >> $LOG
    sleep $REMAINING
fi

touch "$SENTINEL"
echo "[$(date '+%F %T')] launching part2.sh" >> $LOG
bash $PART2 >> $LOG 2>&1
echo "[$(date '+%F %T')] part2.sh returned" >> $LOG
