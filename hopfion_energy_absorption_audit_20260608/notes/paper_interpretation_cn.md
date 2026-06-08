# Hopfion 自旋波能量吸收谱复核结论

日期：2026-06-08
关联任务：`Hopfion-duo`
数据范围：`20260105_frustrated_fm/spin_wave_dynamics/freq_sweep/plane_wave/`

## 1. 这次复核做了什么

这次不是简单重复旧脚本，而是把 `table.txt` 中的 `E_total(t)` 做了三层审计。

第一，仍然计算线性拟合的 `dE_total/dt`。参考窗口设为每条仿真的后 70% 时间，也就是 `30%-100%`，对应旧脚本的做法。

第二，同时扫描 `0%-100%`、`10%-100%`、`20%-100%`、`30%-100%`、`40%-100%`、`50%-100%` 六个窗口，检查同一个频率的斜率符号是否稳定。

第三，用无驱动的 centered Ku10k 稳定性仿真作为背景，扣除同时间窗口的背景能量漂移。背景斜率约为 `0.0024 nJ/s`，远小于强响应频率，因此不会改变主要峰位。

## 2. 最核心的结果

### srcX 平面源

`srcX` 的正能量吸收峰非常明确。

| 频率 | 背景扣除后 dE/dt | R2 | 窗口符号稳定性 | 解释 |
|---|---:|---:|---|---|
| 100 GHz | +35.992 nJ/s | 0.934 | stable_positive | 强正吸收 |
| 200 GHz | +39.812 nJ/s | 0.986 | stable_positive | 最强正吸收峰 |
| 1000 GHz, 0.5 ns 数据 | -1.364 nJ/s | 0.276 | mixed | 不能作为能量吸收峰 |

所以，`srcX 200 GHz` 可以升级为当前最稳的候选 resonant coupling frequency。它不仅有位移响应，而且有稳定、正号、高 R2 的能量吸收证据。

需要注意的是，`srcX 1000 GHz` 在 0.2 ns 数据里有正斜率，但在优先采用的 0.5 ns 数据里变成负斜率且 R2 较低。这说明 1000 GHz 更像强驱动动力学窗口，可能经历“先吸能、后形变/弛豫/能量释放”的阶段变化，不能直接叫固有频率或吸收峰。

### srcZ 平面源

`srcZ` 的情况更复杂，不能再沿用“100 GHz 是最强吸收频率”的强表述。

| 频率 | 背景扣除后 dE/dt | R2 | 窗口符号稳定性 | 解释 |
|---|---:|---:|---|---|
| 25 GHz | +4.960 nJ/s | 0.324 | mixed | 有正斜率但拟合质量不足 |
| 50 GHz | +1.126 nJ/s | 0.251 | mixed | 有正斜率但拟合质量不足 |
| 100 GHz | -4.677 nJ/s | 0.851 | mixed | 最强绝对能量率响应，但不是正吸收峰 |
| 1100 GHz | -2.797 nJ/s | 0.548 | mixed | 高频强运动窗口，后段能量下降 |

因此，`srcZ 100 GHz` 仍然重要，但它的身份应从“最强吸收峰”改成“最强绝对能量率响应，同时伴随异常 +z 位移”。这比旧说法更诚实，也更有物理含义：它可能对应驱动后 Hopfion 进入更低能的运动/形变通道，而不是持续从自旋波吸收能量。

## 3. 和频率扫描结论如何连接

现在可以把频率证据分成三层。

第一层是候选共振耦合频率。`srcX 200 GHz` 最符合，因为它同时满足正吸收、高 R2、窗口稳定、已有位移响应。

第二层是特殊能量率响应频率。`srcZ 100 GHz` 属于这一类。它不是正吸收峰，但它与异常 +z 运动同频出现，因此可作为“能量景观改变或非线性通道开启”的候选频率。

第三层是强驱动响应窗口。`srcX 1000 GHz` 和 `srcZ 1100 GHz` 位移很强，但能量斜率窗口依赖明显，因此应写成 strong drive-response windows，而不是 Hopfion eigenfrequencies。

## 4. 与位移/速度谱的交叉验证

能量谱和运动谱不是完全等价的。二者对照后可以看到很清楚的物理分叉。

| 频率 | 运动响应 | 能量率证据 | 证据等级 |
|---|---|---|---|
| `srcX 100 GHz` | 0.2 ns 位移 `|dr|=1.938 nm`，`v_mean=15.66 nm/ns` | `+35.992 nJ/s`，正号稳定 | 强低频耦合通道 |
| `srcX 200 GHz` | 0.2 ns 位移 `|dr|=2.508 nm`，`v_mean=18.53 nm/ns` | `+39.812 nJ/s`，正号稳定，R2=0.986 | 最强候选共振耦合频率 |
| `srcX 1000 GHz` | 0.2 ns 位移 `5.500 nm`，0.5 ns 位移 `14.317 nm` | 0.5 ns 优先数据为 `-1.364 nJ/s` 且窗口 mixed | 强驱动响应窗口，不是稳定吸收峰 |
| `srcZ 100 GHz` | 位移 `17.598 nm`，方向异常为 `+z` | `-4.677 nJ/s`，绝对能量率最强但不是正吸收 | 特殊非线性/能量景观通道 |
| `srcZ 1100 GHz` | 位移 `18.149 nm`，`-z` 最强控制窗口 | `-2.797 nJ/s`，窗口 mixed | 高频强驱动窗口 |

这个对照给 paper 的帮助很大：它说明位移峰不一定等于吸收峰。低频 `srcX 200 GHz` 是比较干净的共振耦合候选；高频 `1000/1100 GHz` 更像是强自旋波驱动导致的运动窗口，可能混合了传播效率、散射推力、形变和弛豫过程。

## 5. 论文中推荐写法

可以写：

> The energy-rate audit identifies a robust positive absorption channel for the srcX plane-wave drive around 200 GHz. In contrast, the srcZ drive does not show a robust positive absorption peak; its 100 GHz anomaly appears as the strongest signed energy-rate response in magnitude and coincides with the anomalous +z displacement.

也可以写：

> The high-frequency windows around 1000-1100 GHz produce strong displacement but do not show a stable positive energy-absorption signature over the full time trace. We therefore classify them as strong drive-response windows rather than intrinsic eigenfrequencies.

不建议写：

> 100 GHz and 1100 GHz are Hopfion eigenfrequencies.

也不建议写：

> srcZ has an absorption resonance at 100 GHz.

除非后续补做脉冲自由振荡 FFT 或严格的驱动功率注入计算，否则这两个说法都过强。

## 6. 对下一步的影响

如果下一步继续补强 paper，我建议优先做空间模态图，而不是再扫更多频率。最值得画的频率是 `srcX 200 GHz`、`srcZ 100 GHz`、`srcX 1000 GHz`、`srcZ 1100 GHz`。这样可以直接回答一个关键问题：这些频率到底是在激发 Hopfion 内部模式，还是主要造成整体漂移和非线性形变。

## 7. 一句话结论

这次复核支持 `srcX 200 GHz` 作为候选共振耦合频率，但不支持把 `srcZ 100 GHz`、`srcX 1000 GHz` 或 `srcZ 1100 GHz` 直接称为 Hopfion 固有频率。`srcZ 100 GHz` 应保留为异常强响应频率，`1000/1100 GHz` 应定位为强驱动响应窗口。
