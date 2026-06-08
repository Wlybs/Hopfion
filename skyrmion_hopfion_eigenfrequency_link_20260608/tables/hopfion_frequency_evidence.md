# 本项目 Hopfion 频率证据表

本表来自当前项目文件和 memory，而非新仿真。

## 公共初态

| 项 | 值 |
|---|---|
| 系统 | Frustrated FM Hopfion |
| 拓扑荷 | `Q_H=1` |
| 初态 | `centered_stability_test/stability_Ku10k.out/m000020.ovf` |
| 尺寸 | `R ~ 2.17 nm`, `r ~ 1.64 nm` |
| 稳定性 | Ku=10k 下 1 ns z 漂移约 `-0.019 nm` |

## 平面源频率扫描

| 几何 | 频率证据 | 当前解释 |
|---|---|---|
| `srcX_vibX` | 0.2 ns 扫描中 `200 GHz` 位移 `2.508 nm`，`1000 GHz` 位移 `5.500 nm`；0.5 ns 中 `1000 GHz` 位移 `14.317 nm` | `200 GHz` 更接近能量吸收支持的候选内禀耦合；`1000 GHz` 是强驱动窗口 |
| `srcX_vibX` 能量斜率 | `200 GHz` 的 `dE/dt = 39.814 nJ/s`, `R^2=0.9857`，摘要标为最强吸收频率 | 支持 `200 GHz` 作为优先本征模候选 |
| `srcZ_vibX` | `100 GHz` 为 +z 异常强响应 `17.598 nm`；`1100 GHz` 为 -z 强响应 `18.149 nm`；`1000 GHz` 也强 | `100/1100 GHz` 分别可用作双向 z 控制，但本征模归属未定 |
| `srcZ_vibX` 能量斜率 | 复核后 `100 GHz` 为最强绝对能量率响应，但拟合 `dE/dt<0` | 不是正吸收峰；暂列为特殊非平衡响应窗口 |

## 点源频率扫描

| 几何 | 峰位 | 与平面源对比 | 当前解释 |
|---|---:|---:|---|
| 点源 `srcX` | `700 GHz`, `|dr|=5.710 nm` | 平面源主峰约 `1000 GHz` | 红移，可能来自点源宽 `k` 谱 |
| 点源 `srcZ` | `800 GHz`, `|dr|=7.314 nm` | 平面源主峰约 `1100 GHz` | 红移，且方向分布更复杂 |

## 方向选择与非线性

| 现象 | 数据 | 理论联系 |
|---|---|---|
| 极化选择 | `vibX` 强，`vibZ` 几乎无耦合 | 类似 skyrmion 面内/面外场选择不同模式 |
| 双向 z 控制 | `srcZ@100GHz` 推 +z，`srcZ@1100GHz` 推 -z | 不同频率耦合到不同有效模式/散射通道 |
| 1100 GHz 坍塌 | `freq_switch v3` 在 t≈0.91 ns 后 core=0 | 类似强共振激发导致 redshift/collapse |

## 证据等级建议

| 频率 | 建议称呼 | 理由 |
|---:|---|---|
| `200 GHz srcX` | 候选 resonant coupling frequency | 位移和能量吸收均支持 |
| `100 GHz srcZ` | 特殊非平衡响应窗口 | 位移异常 +z；能量吸收复核为最强绝对能量率响应但 `dE/dt<0`，非正吸收峰 |
| `700 GHz point srcX` | point-source drive-response peak | 点源红移峰，未做自由振荡谱 |
| `800 GHz point srcZ` | point-source drive-response peak | 点源红移峰，方向复杂 |
| `1000 GHz srcX` | strong drive-response window | 位移强，但能量吸收未同步支持 |
| `1100 GHz srcZ` | strong drive-response window | 控制有效但强激发会导致坍塌 |
