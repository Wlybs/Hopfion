# A/B/C 汇总与 paper 主线建议

## 1. 总结论

三条线可以合成一篇逻辑自洽的 paper，但必须采用“证据等级”写法。

最稳的主线是：

> We demonstrate frequency-selective spin-wave driving of a frustrated-ferromagnetic Hopfion and interpret the response through magnon-Hopfion coupling, source-dependent k-spectrum, and generalized collective-coordinate dynamics.

不要写成：

> We have determined the eigenfrequencies of the Hopfion.

原因是当前还没有脉冲自由振荡 FFT、线性本征值分析和空间模态图。因此我们已经有强频率响应和候选共振耦合，但还没有严格 eigenfrequency 结论。

## 2. A 线：频率扫描

### 可成立的结论

- Hopfion 自旋波驱动响应具有明确频率选择性。
- `srcX 200 GHz` 是当前最值得作为候选 resonant coupling frequency 的频点，因为位移响应和能量吸收摘要都支持它。
- `srcZ 100 GHz` 是候选特殊耦合频点，因为它既有方向反常，也有能量吸收提示。
- `srcX 1000 GHz` 和 `srcZ 1100 GHz` 是强 drive-response windows，可用于运动控制，但不能直接叫固有频率。

### 当前失败/不足

- 无 Hopfion 本征模求解。
- 无短脉冲自由振荡谱。
- 无模式空间局域图。
- `srcZ` 能量斜率符号需要复核。

### paper 写法

可写：

> The frequency scan reveals multiple drive-response windows. The low-frequency peaks around 100-200 GHz are candidate resonant coupling channels, while the high-frequency windows around 1000-1100 GHz provide strong nonlinear driving.

不可写：

> The intrinsic Hopfion eigenfrequencies are 1000 and 1100 GHz.

## 3. B 线：点源 vs 平面源

### 可成立的结论

- 点源和平面源导致不同响应峰位，现象上表现为红移：`srcX 1000 -> 700 GHz`，`srcZ 1100 -> 800 GHz`。
- 这个红移可用源几何改变 spin-wave k-spectrum 和入射角分布来解释。
- 点源更接近纳米天线，平面源更适合本征模式研究。

### 当前失败/不足

- 没有找到 skyrmion 文献中完全对应的点源 vs 平面源标准结论。
- 当前没有实际计算点源/平面源的 `I(k,f)`。
- 点源 500 T 单格和平面源 1 T 面源不能直接做效率比较。

### paper 写法

可写：

> The point-source response is shifted to lower frequencies compared with the plane-source response. We interpret this as an effective k-spectrum effect of the localized source, consistent with the frequency-dependent magnon-skyrmion scattering picture.

不可写：

> Point sources are more efficient than plane sources.

## 4. C 线：Thiele/动力学

### 可成立的结论

- Skyrmion magnon-driven motion 文献支持“magnon flow 可通过动量转移驱动拓扑结构，并产生横向运动”。
- Hopfion 不能直接套二维 skyrmion Thiele 方程，但可以借鉴集体坐标思想。
- Hopfion 文献支持 translation、transverse motion、rotation、dilation 的耦合，因此我们的复杂漂移方向并不奇怪。

### 当前失败/不足

- 没有拟合 Hopfion 的广义 gyro/dissipation tensor。
- 没有计算自旋波动量流和散射角。
- 不能定量预测每个频率下的速度和方向。

### paper 写法

可写：

> Inspired by magnon-driven Thiele dynamics of skyrmions, the Hopfion motion can be interpreted as a generalized collective-coordinate response to magnon-induced forces, where translational and internal degrees of freedom are coupled.

不可写：

> The conventional skyrmion Thiele equation quantitatively explains the Hopfion trajectory.

## 5. 推荐 paper 结构

### Section 1: Motivation

强调 3D magnetic Hopfion 是比 2D skyrmion 更复杂的拓扑结构。现有 Hopfion 动力学研究多集中在 STT、外场共振或 AFM magnon scattering；frustrated FM Hopfion 的 spin-wave driven dynamics 仍有空间。

### Section 2: Model and simulation setup

写清楚 frustrated FM、Q_H=1、公共初态、平面源/点源定义、频率和幅度扫描设置。这里要提前说明点源和平面源的能量注入不可直接等价。

### Section 3: Frequency-selective plane-wave driving

展示 `srcX`、`srcZ` 频率响应。重点不是“哪个最大”，而是多窗口响应、方向选择、低频候选共振、高频强驱动。

### Section 4: Point-source driving and source-geometry effect

展示点源峰位红移和方向分布复杂化。理论解释为局域源的宽 `k` 谱和多角度散射。

### Section 5: Effective dynamical interpretation

用 skyrmion magnon-driven Thiele 文献和 Hopfion STT 集体坐标文献建立广义方程图像。解释为什么自旋波驱动可以产生横向/反向/非线性运动。

### Section 6: Nonlinear control and stability threshold

放 `freq_switch v3`：100 GHz 与 1100 GHz 能双向控制，但 1100 GHz 强驱动后坍塌。这个结果不要隐藏，反而可作为强非线性窗口和拓扑稳定阈值的证据。

### Section 7: Limitations and outlook

明确写出还需要 pulse FFT、mode map、k-spectrum 和 momentum-flux analysis。客观承认这篇 paper 目前的定位是“spin-wave driven Hopfion response and interpretation”，不是完整 eigenmode theory。

## 6. 后续最小补强包

如果只补最少分析，建议按这个顺序：

1. **重算能量吸收谱**  
   目标：确认 `200 GHz srcX` 和 `100 GHz srcZ` 的证据等级。

2. **做无 Hopfion 的源 k 谱**  
   目标：证明点源和平面源确实有不同 `k` 分布。

3. **对 4 个代表频率做空间模态图**  
   频率：`100, 200, 1000, 1100 GHz`。目标：区分内部形变和纯漂移。

4. **整理速度/能量/形变三变量相关性**  
   目标：把 Thiele 图像从纯文字提升为半定量解释。

## 7. 最终客观评价

当前项目已经足够形成一篇有物理主线的 paper 初稿，但理论解释还处于“合理框架 + 部分证据支持”阶段。最危险的地方是把位移响应峰直接包装成 Hopfion 固有频率。最有希望的方向是把 paper 定位为：

> Frequency-selective and source-geometry-dependent spin-wave control of a frustrated-ferromagnetic Hopfion.

这个定位允许我们诚实展示已有现象，同时通过 skyrmion/Hopfion 文献把现象组织成理论上可理解的 magnon-Hopfion coupling story。

