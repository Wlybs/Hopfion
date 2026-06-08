# 与当前 Hopfion 自旋波驱动结论的联系判断

## 当前结论的证据等级

### A. 可以较稳地称为“候选本征耦合”的频率

`srcX` 平面源的 `200 GHz` 值得优先关注。原因是它同时出现在位移响应的强响应区，并且能量吸收谱摘要中 `dE/dt` 拟合质量较高、数值最大。按 skyrmion 文献语言，这更接近“被驱动场有效泵入某个内禀模式”的证据。

`srcZ` 平面源的 `100 GHz` 也值得关注。它在位移图中表现为方向异常的 +z 强响应，且能量斜率摘要把它标为最强能量响应。不过这里需要重新确认 `E_total` 的符号约定和拟合窗口，因为表中不少 `dE/dt` 为负，不能简单把所有绝对值峰称为吸收峰。

### B. 更应称为“强驱动位移窗口”的频率

`srcX 1000 GHz` 和 `srcZ 1100 GHz` 是目前最显眼的位移峰，已经能用于双向 z 控制。但它们是否是 Hopfion 本征频率还不能直接判定。可能成分包括：

- 与高 `k` 自旋波匹配的内部模式。
- 自旋波散射/反射导致的线性动量传递峰。
- 长时间加速和边界/阻尼窗口叠加出来的有效位移峰。
- 强耦合造成 Hopfion 形变，在 `freq_switch v3` 中最终越过稳定阈值。

### C. 点源红移的联系

点源峰位 `srcX 700 GHz`、`srcZ 800 GHz` 相对平面源的 `1000/1100 GHz` 红移，与 skyrmion spin-wave-driven motion 的反射/传播解释相容。点源不是“同一频率下更弱的平面源”，而是宽角度、宽 `k` 的局域激发。它改变了入射波的有效波矢分布和散射矩阵元，因此响应峰移动是合理的。

## 能直接借用的 skyrmion 理论语言

1. **选择定则**  
   Skyrmion 中面内/面外 ac field 分别选择旋转/breathing 模。我们这里 `vibX` 强耦合、`vibZ` 几乎无耦合，说明 Hopfion 也存在明显的激励方向选择定则。

2. **本征模不等于位移峰**  
   Skyrmion 文献通过吸收谱、空间模态、反射系数区分“内部模式”和“被自旋波推着走”。我们也应把 `v(f)`、`|dr(f)|`、`dE/dt(f)` 和空间 FFT 分开报告。

3. **强激发红移与坍塌**  
   Mochizuki 2012 和 Garanin 2020 都指出强激发下频率可以红移，结构可进入 melting/collapse。`freq_switch v3` 的 1100 GHz 反向阶段在 0.91 ns 左右坍塌，可以放进这一理论框架。

4. **集体坐标扩展**  
   Skyrmion 的 `R_s`、helicity/chirality、`X/Y` 坐标足以描述低阶动力学；Hopfion 至少要增加环半径、管半径、扭转相位和 3D 质心。Liu et al. 的 frustrated-magnet Hopfion STT 文献也强调了 translation、rotation、dilation 的耦合。

## 不能直接照搬的部分

- Skyrmion 是二维拓扑荷 `Q`，Hopfion 是三维 Hopf index `Q_H`，拓扑项和 gyrovector 结构不同。
- Skyrmion 典型频率常在 GHz 量级；我们系统的特征尺寸只有几 nm，frustrated exchange 强，自旋波驱动频率达到数百 GHz 到 THz 边缘并不矛盾。
- Skyrmion 的面内/面外选择规则在 Hopfion 中要改写为“驱动方向、波矢方向、极化方向、Hopfion 轴向”的四维耦合矩阵。
- 平面源和点源不只是实验几何差异，也是 `k` 谱差异；因此不能用同一个一维本征频率列表解释全部响应。

## 本次判断

当前数据可以支持如下表述：

> Hopfion 自旋波驱动存在与 skyrmion 本征模谱学相似的频率选择性。能量吸收谱提示 `srcX 200 GHz` 与 `srcZ 100 GHz` 可能对应较低阶的内禀耦合模式，而 `srcX 1000 GHz`、`srcZ 1100 GHz` 更像强动量传递/强耦合控制窗口。点源红移和 1100 GHz 强驱动坍塌可分别用 skyrmion 文献中的 spin-wave reflectivity 机制与强非线性 redshift/collapse 图像解释。

严格表述时，建议把“Hopfion 固有频率”写成“候选固有/共振耦合频率”，直到补齐脉冲自由振荡 FFT 和空间模态图。
