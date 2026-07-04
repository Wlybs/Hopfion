#!/bin/bash
# srcX 点源幅度扫描 @ 1100GHz
LOG="run_1100GHz_sweep.log"
echo "[$(date)] === start ===" | tee -a $LOG

echo "[$(date)] >>> B=100T" | tee -a $LOG
mumax3 ps_srcX_vibX_1100GHz_B100.mx3 2>&1 | tee -a $LOG
echo "[$(date)] <<< B=100T done" | tee -a $LOG

echo "[$(date)] >>> B=200T" | tee -a $LOG
mumax3 ps_srcX_vibX_1100GHz_B200.mx3 2>&1 | tee -a $LOG
echo "[$(date)] <<< B=200T done" | tee -a $LOG

echo "[$(date)] >>> B=300T" | tee -a $LOG
mumax3 ps_srcX_vibX_1100GHz_B300.mx3 2>&1 | tee -a $LOG
echo "[$(date)] <<< B=300T done" | tee -a $LOG

echo "[$(date)] >>> B=400T" | tee -a $LOG
mumax3 ps_srcX_vibX_1100GHz_B400.mx3 2>&1 | tee -a $LOG
echo "[$(date)] <<< B=400T done" | tee -a $LOG

echo "[$(date)] >>> B=500T" | tee -a $LOG
mumax3 ps_srcX_vibX_1100GHz_B500.mx3 2>&1 | tee -a $LOG
echo "[$(date)] <<< B=500T done" | tee -a $LOG

echo "[$(date)] >>> B=700T" | tee -a $LOG
mumax3 ps_srcX_vibX_1100GHz_B700.mx3 2>&1 | tee -a $LOG
echo "[$(date)] <<< B=700T done" | tee -a $LOG

echo "[$(date)] >>> B=1000T" | tee -a $LOG
mumax3 ps_srcX_vibX_1100GHz_B1000.mx3 2>&1 | tee -a $LOG
echo "[$(date)] <<< B=1000T done" | tee -a $LOG

echo "[$(date)] >>> B=2000T" | tee -a $LOG
mumax3 ps_srcX_vibX_1100GHz_B2000.mx3 2>&1 | tee -a $LOG
echo "[$(date)] <<< B=2000T done" | tee -a $LOG

echo "[$(date)] === ALL DONE ===" | tee -a $LOG
