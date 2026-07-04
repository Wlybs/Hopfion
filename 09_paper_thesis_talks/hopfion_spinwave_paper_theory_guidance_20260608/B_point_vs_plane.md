# B. 点源 vs 平面源自旋波驱动理论解释

## B1. 这条线要回答什么

当前 Hopfion 数据中，平面源和点源有明显不同：

- 平面源 `srcX` 强峰约在 `1000 GHz`，点源 `srcX` 强峰约在 `700 GHz`。
- 平面源 `srcZ` 强峰约在 `1100 GHz`，点源 `srcZ` 强峰约在 `800 GHz`。
- 点源 `srcZ` 的方向分布比平面源更复杂。

这条线的目标不是强行说“点源改变了 Hopfion 固有频率”，而是解释：**同一个 Hopfion，在不同源几何下看到不同响应峰，是因为入射自旋波的 k 空间分布、角度分布和散射矩阵元不同。**

## B2. 直接文献情况

客观记录：目前没有找到一篇可以直接照搬的“单个 skyrmion 点源 vs 平面源自旋波驱动对比”的标准理论论文。

因此这条线不能写成“已有 skyrmion 文献已经证明点源会红移”。更真实的写法应是：

> Although a direct one-to-one skyrmion point-source versus plane-source theory is not established, existing studies on spin-wave-driven skyrmion motion and magnon-skyrmion scattering show that the response is controlled by magnon propagation, reflectivity, scattering angle and momentum transfer. This supports interpreting the point/plane-source difference as a k-spectrum and source-geometry effect.

## B3. 可借鉴的 skyrmion 自旋波驱动文献

### Zhang et al. 2018

论文：*Spin-Wave-Driven Skyrmion Motion in Magnetic Nanostrip*, Journal of Nanotechnology 2018, 2602913.  
链接：https://doi.org/10.1155/2018/2602913

主要结论：

- skyrmion 速度随 spin wave 频率和幅度变化。
- spin wave 被 skyrmion 反射的程度对运动速度有很大影响。
- 这说明频率响应峰不是单纯“固有频率峰”，还包含传播和反射因素。

对我们的启发：

平面源和点源看到不同峰位，可以先解释为不同入射波导致的不同 magnon-Hopfion scattering，而不是 Hopfion 自身频率改变。

### Zhang et al. 2017

论文：*Motion of skyrmions in nanowires driven by magnonic momentum-transfer forces*, New Journal of Physics 19, 065001.  
链接：https://arxiv.org/abs/1701.02430  
DOI：https://doi.org/10.1088/1367-2630/aa6b70

主要结论：

- skyrmion 由靠近边缘的 driving layer 发出的 magnon current 驱动。
- 轨迹由 magnon current force 和边界力共同决定。
- transverse magnon current 可形成稳态运动；低 current density 下速度近似 `v ~ J/alpha`。
- 强驱动会把 skyrmion 推向源/边界，导致速度下降甚至毁灭。

对我们的启发：

点源局域驱动不只是“弱一点的平面源”。源附近强近场、衰减、边界/几何力都可能改变运动方式。我们的点源 500 T 单格与平面源 1 T 薄层不能直接比较绝对效率。

### Schuette & Garst 2014

论文：*Magnon-skyrmion scattering in chiral magnets*, Phys. Rev. B 90, 094423.  
链接：https://arxiv.org/abs/1405.1568  
DOI：https://doi.org/10.1103/PhysRevB.90.094423

主要结论：

- skyrmion 与小振幅 magnon 的相互作用可以看作 magnon 在 skyrmion 拓扑纹理产生的有效场中散射。
- 散射具有非平庸角分布，和 skyrmion 拓扑结构相关。

对我们的启发：

点源产生多角度入射波时，Hopfion 看到的是一组入射方向的叠加，方向分布自然可能比平面源复杂。

### Schroeter & Garst 2015

论文：*Scattering of high-energy magnons off a magnetic skyrmion*.  
链接：https://arxiv.org/abs/1504.02108

主要结论：

- 高能 magnon 对单 skyrmion 的散射由 emergent magnetic field 主导。
- 横向动量转移具有拓扑普适性，纵向动量转移在高能极限较小。
- 导致 magnon-driven skyrmion motion 与入射 magnon current 有非直观方向关系。

对我们的启发：

Hopfion 的运动方向不能只用“自旋波从哪来就往哪走”解释。源几何改变入射角分布后，合力方向也会改变。

## B4. 平面源和点源的物理差别

### 平面源

平面源像一排人同时拍水，形成比较整齐的波前。理想情况下：

- 入射方向较单一。
- 波矢分布较窄。
- 更适合做本征模式研究。
- 频率响应峰更容易解释为某类模式/散射通道的选择性耦合。

### 点源

点源像往水面丢一颗石子，波向四周扩散。它带来：

- 宽角度入射。
- 宽 `k` 谱和近场成分。
- 幅度随距离衰减。
- 对 Hopfion 不同部位的局域激发不均匀。

因此点源峰位红移可以有一个合理解释：点源的宽 `k` 谱中低 `k` 或不同角度成分更容易与某些 Hopfion 运动/形变通道耦合，使有效响应峰从平面源的高频峰移动到较低频率。

## B5. 对当前 Hopfion 结果的解释

| 现象 | 可支持解释 | 证据不足 |
|---|---|---|
| `srcX` 平面源 1000 GHz，点源 700 GHz | 点源宽 k 谱导致有效耦合峰红移 | 尚未做 spin-wave 空间 FFT，不能证明 k 谱 |
| `srcZ` 平面源 1100 GHz，点源 800 GHz | 同上，且轴向入射对 Hopfion 环/管结构更敏感 | 点源方向分布复杂，需分解入射角 |
| 点源 `srcZ` 方向更散 | 多角度入射与 Hopfion 拓扑散射叠加 | 目前只有最终位移图，缺少波场散射图 |
| 点源需要 500 T 级单格场 | 单格源体积极小，绝对场强不能与 1 T 平面源直接比较 | 缺少输入功率/能量归一化 |

## B6. 失败/不足记录

- 没有直接 skyrmion 文献证明“点源必然红移”。
- 当前 Hopfion 数据没有输入功率归一化，不能说点源比平面源“更高效”或“更低效”。
- 当前没有点源/平面源的 `I(k,f)` 谱，因此 k 谱解释仍是合理假说，不是已证明结论。
- 点源用 500 T，平面源用 1 T，源体积不同，不能做绝对驱动力比较。

## B7. 下一步建议

1. 无 Hopfion 对照下分别记录平面源和点源 spin wave，做空间 FFT。
2. 在有 Hopfion 情况下，分析入射波、散射波和 Hopfion 近场的频谱。
3. 用输入能量或 `E_total` 增量归一化位移/速度，而不是直接比较 B_amp。
4. 对点源位置做少量扫描，判断红移是否稳定，还是源-Hopfion 几何偶然性。

