#!/bin/bash
# ================================================================
# watch_then_stop.sh — 监控 sw_B0p7T 完成, kill wrapper bash 阻止 #3-#8 自动启动
# 由用户手动 nohup 启动, session 死后仍跑
# ================================================================

WRAPPER_PID=38216
PLANE_DIR=/mnt/d/Research/Hopfion/04_frustrated_fm_foundation/20260105_frustrated_fm/spin_wave_dynamics/amplitude_sweep/plane_wave
LOG=$PLANE_DIR/watch_then_stop.log
RUN_LOG=$PLANE_DIR/run_amplitude_extended.log
TARGET_SIM=sw_B0p7T

# 接下来要阻止启动的 sims (#3-#8)
BLOCKED_SIMS=(sw_B3p0T sw_B5p0T sw_f200GHz_B0p5T sw_f200GHz_B2p0T sw_f1000GHz_B0p5T sw_f1000GHz_B2p0T)

echo "[$(date '+%F %T')] watcher started: PID $$, monitoring $TARGET_SIM in $RUN_LOG, target wrapper PID $WRAPPER_PID" >> $LOG

while true; do
    # wrapper 已经死了
    if ! kill -0 $WRAPPER_PID 2>/dev/null; then
        echo "[$(date '+%F %T')] wrapper $WRAPPER_PID already dead, no action needed, exit" >> $LOG
        exit 0
    fi

    # sw_B0p7T 完成检测
    if grep -q "finished sw_B0p7T" $RUN_LOG 2>/dev/null; then
        echo "[$(date '+%F %T')] $TARGET_SIM finished detected" >> $LOG
        # 先 SIGTERM wrapper
        kill $WRAPPER_PID 2>/dev/null && echo "[$(date '+%F %T')] sent SIGTERM to wrapper" >> $LOG
        sleep 1
        # kill 任何已经启动的 #3-#8 mumax3 子进程
        for sim in "${BLOCKED_SIMS[@]}"; do
            pids=$(pgrep -f "mumax3 ${sim}.mx3" 2>/dev/null || true)
            if [ -n "$pids" ]; then
                echo "[$(date '+%F %T')] killing mumax3 ${sim} (pids=$pids)" >> $LOG
                kill -9 $pids 2>/dev/null
            fi
        done
        # 确保 wrapper 死
        sleep 1
        kill -9 $WRAPPER_PID 2>/dev/null
        # 清理可能已建的部分 .out (帧数 <=3 才删，保险)
        for sim in "${BLOCKED_SIMS[@]}"; do
            if [ -d "$PLANE_DIR/${sim}.out" ]; then
                nframes=$(ls $PLANE_DIR/${sim}.out/m*.ovf 2>/dev/null | wc -l)
                if [ $nframes -le 3 ]; then
                    rm -rf "$PLANE_DIR/${sim}.out"
                    echo "[$(date '+%F %T')] removed partial $PLANE_DIR/${sim}.out (had $nframes frames)" >> $LOG
                else
                    echo "[$(date '+%F %T')] KEEPING $PLANE_DIR/${sim}.out ($nframes frames, suspect more done)" >> $LOG
                fi
            fi
        done
        echo "[$(date '+%F %T')] watcher done, exit" >> $LOG
        exit 0
    fi

    sleep 2
done
