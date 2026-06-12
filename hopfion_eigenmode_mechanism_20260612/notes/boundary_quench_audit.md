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

## 当前初步证据

在共同 `5-112 ps` 窗口内，1 mT 与 5 mT 的 `m_z` 锁相幅值分别约为 `1.1633e-6` 和 `1.1628e-6`。两条去均值轨迹的相关系数约为 `0.9986`，相对 RMS 差约为 `5.4%`。既有 `Bx 5 mT` 与 `Bz 5 mT` 的 `m_z` 主峰功率分别约为 `1.803e-10` 和 `1.884e-10`。幅值未随场强变化，主峰也对驱动方向近似不敏感，因此必须优先检验共同边界淬火成分。

这不是对 `173.66 GHz` 频率本身的直接否定。若零场控制同样出现该峰，说明它可能是由边界淬火激发的自由模。只有在空间模态显示其局域于 Hopfion 时，才能进一步称为 Hopfion 候选本征模；只有驱动减零场后的复振幅保持线性场标度时，才能讨论 sinc 脉冲对该模的耦合。

## 修正后的证据链

1. 用原初态、目标开放边界和 `B0=0` 量化边界淬火谱。
2. 在目标开放边界下先执行能量松弛，并用相对数值 Hopf 指数确认拓扑未明显改变。
3. 从同一个平衡态运行 `0/1/2/5 mT`，对轨迹做零场差分后检验功率平方律。
4. 空间模态使用 `mode(5 mT)-mode(0 mT)`，再与均匀背景驱动比较。
5. 只有上述门通过，才运行传播自旋波 CW 桥接与点源/平面源 k 谱。

## 论文可用边界

若零场控制证明 `173.66 GHz` 为共同淬火峰，可以写：

> A prominent free-oscillation peak was observed near 173.66 GHz after switching from the periodic relaxed state to the open-boundary dynamical geometry. Its nearly drive-independent raw amplitude revealed a substantial boundary-quench contribution. We therefore subtracted a zero-field trajectory at the complex-amplitude level before assessing pulse-induced linearity and mode localization.

不能写：

> The 173.66 GHz peak is linearly excited by the sinc pulse.

除非平衡态差分谱的 C2 线性门实际通过。
