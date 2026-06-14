# 边界淬火与 ringdown 归因审计

## 问题来源

当前 Hopfion 初始态由 PBC 体系在 `alpha=0.2` 下演化得到，而最初的 ringdown 脚本在载入该状态后立即切换为无 PBC、六面吸收层和 bulk `alpha=0.001`。阻尼参数本身不改变静态能量极值，但从 PBC 到开放边界会改变表面附近的交换邻接关系。载入态因而不一定是新边界问题的严格平衡态。

即使外加脉冲为零，边界条件的突然切换也可以把初态投影到新体系的一组自由模上。随后观察到的 ringdown 频率可能确实属于新体系的本征谱，但其振幅不能归因于 sinc 脉冲，更不能直接用于场强线性标度或偏振选择性分析。

## 线性响应分解

在小扰动范围内，可把某个观测量的复 Fourier 振幅写为

```text
A_raw(omega, B0) = A_quench(omega) + B0 A_drive(omega) + O(B0^2).
```

原始功率为

```text
P_raw = |A_quench + B0 A_drive|^2.
```

当 `|A_quench|` 远大于 `|B0 A_drive|` 时，1 mT 和 5 mT 的原始峰功率会近似相同。由于两项带有复相位，直接用两个功率相减也不严格。正确处理是在时间序列或复 Fourier 振幅层面减去同边界、同初态、同采样的 `B0=0` 控制

```text
A_drive,est(omega, B0) = FFT[m(t,B0) - m(t,0)].
```

再检验

```text
|A_drive,est| proportional B0,
P_drive,est proportional B0^2.
```

本项目的 `ringdown_fft_difference` 先把零场控制插值到驱动时间点，再对轨迹差做去均值和 Hann-window FFT。该处理允许 Mumax 自适应积分产生轻微不同的时间戳，同时避免在功率层面丢失相位信息。

## 当前原始谱证据

在共同 `5-112 ps` 窗口内，1 mT 与 5 mT 的 `m_z` 锁相幅值分别约为 `1.1633e-6` 和 `1.1628e-6`。两条去均值轨迹的相关系数约为 `0.9986`，相对 RMS 差约为 `5.4%`。既有 `Bx 5 mT` 与 `Bz 5 mT` 的 `m_z` 主峰功率分别约为 `1.803e-10` 和 `1.884e-10`。幅值未随场强变化，主峰也对驱动方向近似不敏感，因此必须优先检验共同边界淬火成分。

首个 1 mT 算例完整运行至 `0.5 ns` 后，使用共同 `5-500 ps` 窗口复核。1 mT 与 5 mT 的 `173.66 GHz` 锁相振幅分别为 `1.5602e-7` 和 `1.5481e-7`，振幅比为 `0.9923`，对应原始振幅标度指数 `-0.0048`。两条轨迹的相关系数为 `0.9981`，相对 RMS 差为 `6.35%`。FFT 峰位分别为 `173.66209 GHz` 和 `173.66222 GHz`，峰功率分别为 `1.8996e-10` 和 `1.8844e-10`，质量因子分别为 `40.88` 和 `40.85`。完整时间窗没有恢复弱场线性标度，反而确认两条原始自由振荡几乎重合。机器可读结果见 `results/raw_1mt_5mt_full_window_audit.json`。

这不是对 `173.66 GHz` 频率本身的直接否定。若零场控制同样出现该峰，说明它可能是由边界淬火激发的自由模。只有在空间模态显示其局域于 Hopfion 时，才能进一步称为 Hopfion 候选本征模；只有驱动减零场后的复振幅保持线性场标度时，才能讨论 sinc 脉冲对该模的耦合。

## C0 正式结果

零场控制完整运行至 `0.5 ns` 后，`173.66 GHz` 的零场、1 mT 与 5 mT 锁相振幅分别为 `1.5673e-7`、`1.5602e-7` 和 `1.5481e-7`。零场/1 mT 振幅比为 `1.0046`，远高于项目门槛 `0.5`；1→5 mT 的原始振幅指数为 `-0.0048`，也低于门槛 `0.5`。两项判据均指向同一结论，机器输出为 `quench_dominated=true`。

这确认了原始 ringdown 中存在主导性的边界淬火成分。该结果不否定 `173.66 GHz` 是开放边界体系的自由模频率，但否定了“原始峰振幅证明 sinc 脉冲线性激发”的解释。后续 C1/C2 将从目标开放边界平衡态重新出发，并在复振幅层面减去零场轨迹。

## 修正后的证据链

1. 用原初态、目标开放边界和 `B0=0` 量化边界淬火谱。
2. 在目标开放边界下先执行能量松弛，并用相对数值 Hopf 指数确认拓扑未明显改变。
3. 从同一个平衡态运行 `0/1/2/5 mT`，对轨迹做零场差分后检验功率平方律。
4. 空间模态使用 `mode(5 mT)-mode(0 mT)`，再与均匀背景驱动比较。
5. 只有上述门通过，才运行传播自旋波 CW 桥接与点源/平面源 k 谱。

## C2 最终审计

四组平衡态控制均完整到 `0.5 ns`。减去零场轨迹后，分析程序在约 `79.14 GHz` 给出候选差分峰，但 `1/2/5 mT` 的峰功率近似不变，功率标度指数为 `-0.0635`，`R^2=0.5323`；`5 mT` SNR 为 `2.64`。虽然峰位离散只有 `0.282 GHz`，场强平方律和 SNR 两项仍明确失败，机器门输出 `passed=false`。

这意味着当前脉冲幅度范围和观测量没有分离出可信的线性驱动本征响应。可能原因包括驱动差分信号低于当前数值/轨迹差异背景，或该偏振与 table-average `m_z` 对目标模式耦合过弱；现有数据不能在二者之间作唯一判定。按门控，C3 与 stage2 均停止，未用高开销结果追逐一个未通过基础线性检验的峰。

## 论文可用边界

若零场控制证明 `173.66 GHz` 为共同淬火峰，可以写：

> A prominent free-oscillation peak was observed near 173.66 GHz after switching from the periodic relaxed state to the open-boundary dynamical geometry. Its nearly drive-independent raw amplitude revealed a substantial boundary-quench contribution. We therefore subtracted a zero-field trajectory at the complex-amplitude level before assessing pulse-induced linearity and mode localization.

不能写：

> The 173.66 GHz peak is linearly excited by the sinc pulse.

除非平衡态差分谱的 C2 线性门实际通过。

C2 实际结果为失败，因此上述禁用表述继续有效。
