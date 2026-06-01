# 06_multisource_freq_switch — 双向 z 控制 / 多源 freq_switch

## 物理主题

- **baseline (srcX + srcZ 同时)**：双源仅 +z，未实现反转
- **bidirectional_z v1**：双源叠加，同样未逆转
- **v2 (freq_switch, Phase1=0.10ns/Phase2=0.40ns)**：Phase1 仅 +0.04 nm（太短）/ Phase2 -18.7 nm → **双向 FAILED**
- **v3 (Phase1=0.50ns/Phase2=0.50ns)**：
  - Phase1 100 GHz: 0 → +17.6 nm **PASS**
  - Phase2 1100 GHz: +17.6 → -12.9 nm 反转 **SUCCESS**
  - **t ≈ 0.91 ns Hopfion 拓扑结构坍塌 core=0**
  - 毕设展示截到 0.80 ns，未提坍塌（叙事截断）
  - 本汇报完整呈现到 1.00 ns

## 失败根因（v3）

1. 1100 GHz 推 -z 力量过强（耦合 ~74 nm/ns vs Phase1 ~35 nm/ns）
2. Phase2 持续 0.30 ns 太久，形变累积过临界

## 后续未实施候选方案 A

- Phase2 脉宽 0.30 → 0.05/0.10 ns 扫描
- Phase2 振幅 1 T → 0.5/0.3 T
- Phase2 后接 0 场维持 0.5 ns
- 验证 LIF 充放电循环

## 脚本清单

| 文件 | 功能 |
|---|---|
| `baseline_dual_src.mx3` | 双源基线（srcX + srcZ 同时）|
| `freq_switch_v1.mx3` | 双源叠加版（z_bidirectional_control）|
| `freq_switch_v2.mx3` | freq_switch v2（Phase1 太短）|
| `freq_switch_v3.mx3` | freq_switch v3（**0.91 ns 坍塌案例**）|
| `analyze_freq_switch.py` | v1/v2 切换序列分析 |
| `analyze_freq_switch_v3.py` | v3 专用分析（含 core_count 追踪）|

## 原始数据位置

`20260105_frustrated_fm/spin_wave_dynamics/multisource_control/{baseline, bidirectional_z}/`
