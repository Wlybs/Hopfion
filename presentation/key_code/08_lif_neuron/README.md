# 08_lif_neuron — Hopfion 作 LIF 神经元（基于 Skyrmion 专利 CN 118284316 A 改写）

## Phase 1: 梯度 Ku 恢复力验证 (PASS, 2026-04-19)

drive-release 实验：100 GHz 驱动 0.3 ns → 关掉 2 ns 自由弛豫，对比 gradient Ku vs uniform Ku。

**结论：PASS** — 梯度 Ku 提供恢复力，gradient 在 +7.8 nm 收敛（near-critical damping），uniform 在原点附近振荡（underdamped）。

**意外发现**：Hopfion 偏好低 Ku 区（gradient 平衡在 Ku≈7500 端），与初始假设"Hopfion 趋向高 Ku 区"相反。Phase 2 设计因此反转。

## Phase 2: 完整 LIF 循环 (F1 FAILED, 2026-04-19)

`lif_pulse_train.mx3`：4 脉冲 @1100 GHz integrate（0.15 ns on / 0.25 ns gap） + 100 GHz fire + 不应期。

**FAILED**：t=1.089 ns kill。失败原因：
1. 1100 GHz 推 -z 方向与梯度 Ku 恢复力 +z 同向（不是反向），integrate 期持续 overshoot
2. Phase1 V2 在 100 GHz 下的"低 Ku 偏好"不能外推到 1100 GHz

## Phase 2 重设计候选（未开工）

- 方案 A：反转源-初态相对位置（initial 在 -z 端，100 GHz integrate +z, 梯度自然回拉）
- 方案 B：降 1100 GHz 幅度 + 延长 gap
- 方案 C：缩短 pulse 宽（0.15 → 0.05 ns）
- 方案 D：双频叠加抑制残余自旋波

## 脚本清单

| 文件 | 功能 |
|---|---|
| `gradient_ku_drive_release.mx3` | Phase 1 V2 (梯度版)，PASS |
| `uniform_ku_drive_release.mx3` | Phase 1 V2 (均匀版)，对照 |
| `lif_pulse_train.mx3` | Phase 2 F1，FAILED（保留作设计迭代样本）|
| `subthreshold_B0p1T.mx3` | Phase 2 F3 sub-threshold (B=0.1T) 对照 |
| `analyze_leaky_drift.py` | drive-release 轨迹对比 |
| `analyze_lif_cycle.py` | LIF 循环分析（--compare F1 vs F3）|

## 原始数据位置

`lif_neuron_hopfion/{gradient_ku_verification, lif_cycle_demo}/`
