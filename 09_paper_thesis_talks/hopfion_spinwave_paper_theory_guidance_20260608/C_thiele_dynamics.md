# C. Thiele 方程、magnon 动量转移与 Hopfion 动力学解释

## C1. 这条线要回答什么

当前 Hopfion 自旋波驱动的关键现象是：

- `srcX` 平面源让 Hopfion 主要沿 +z 漂移，接近垂直于传播方向。
- `srcZ` 平面源在多数频率下让 Hopfion 沿 -z 漂移，但 100 GHz 异常为 +z。
- 100 GHz 与 1100 GHz 可实现双向 z 控制。
- 强 1100 GHz 阶段会造成 Hopfion 坍塌。

这条线要解释的是：为什么拓扑结构的运动方向和速度不是简单由波传播方向决定，而是由 magnon 力、拓扑陀螺项、阻尼、边界/形变共同决定。

## C2. Skyrmion 中的 Thiele 图像

对二维 skyrmion，常见低维动力学可以写成类似：

```text
G x v + alpha D v = F_drive + F_edge + F_pin
```

这里：

- `G` 与 skyrmion number 有关，给出横向 Magnus/gyrotropic 响应。
- `D` 是耗散张量。
- `F_drive` 可来自电流、自旋流、自旋波或温度梯度产生的 magnon current。
- `F_edge` 是边界力。

这个方程的意义不是“skyrmion 是刚性小球”，而是把复杂自旋纹理的低频运动压缩到几个集体坐标上。

## C3. Magnon-driven skyrmion 文献结论

### Kong & Zang 2013

论文：*Dynamics of an insulating Skyrmion under a temperature gradient*, Phys. Rev. Lett. 111, 067203.  
链接：https://arxiv.org/abs/1308.2343  
DOI：https://doi.org/10.1103/PhysRevLett.111.067203

主要结论：

- 温度梯度激发 magnon flow 后，single 和 multiple skyrmions 会向高温区域运动。
- 这与普通粒子扩散方向相反。
- skyrmion 拓扑荷导致横向运动，理论与数值模拟定性、定量一致。

对我们的启发：

Magnon flow 可以有效驱动拓扑结构运动，并且运动方向包含拓扑横向分量。这支持我们用“自旋波动量/角动量转移 + 拓扑响应”解释 Hopfion 漂移。

### Zhang et al. 2017

论文：*Motion of skyrmions in nanowires driven by magnonic momentum-transfer forces*, New Journal of Physics 19, 065001.  
链接：https://arxiv.org/abs/1701.02430  
DOI：https://doi.org/10.1088/1367-2630/aa6b70

主要结论：

- 使用 micromagnetic simulation 和 effective Thiele equation 解释 magnon-driven skyrmion motion。
- 轨迹由 magnon current force 与边界力共同控制。
- 低 magnon current 下速度近似 `v ~ J/alpha`。
- 强驱动会导致速度下降，甚至破坏 skyrmion。

对我们的启发：

我们的 1100 GHz 强反向控制后坍塌，与“强 magnon driving 可造成结构破坏”的 skyrmion 图像相容。幅度扫描中也应寻找弱驱动区和强非线性区的分界。

### Schuette & Garst 2014 / Schroeter & Garst 2015

论文：

- *Magnon-skyrmion scattering in chiral magnets*, Phys. Rev. B 90, 094423. https://arxiv.org/abs/1405.1568
- *Scattering of high-energy magnons off a magnetic skyrmion*. https://arxiv.org/abs/1504.02108

主要结论：

- Magnon 与 skyrmion 的相互作用可理解为在 emergent magnetic field 中散射。
- 高能极限下横向动量转移具有拓扑普适性。
- magnon-driven skyrmion motion 可出现不直观方向。

对我们的启发：

Hopfion 的 `srcX -> +z` 这种近似横向运动不应被视为奇怪现象。拓扑纹理对 magnon 的散射本来就能产生横向动量交换。

## C4. Hopfion 不能直接套 2D Thiele

Hopfion 与 skyrmion 的关键差异：

| Skyrmion | Hopfion |
|---|---|
| 2D 拓扑荷 `Q` | 3D Hopf index `Q_H` |
| 主要集体坐标 `X,Y,R,helicity` | `X,Y,Z,R_ring,r_tube,toroidal/poloidal phase` |
| gyrovector 常写成 `G zhat` | 更可能是 gyro-tensor / Berry-phase coupling matrix |
| 平面内运动 | 三维平移 + 旋转 + dilation |

因此，paper 中不建议写“we use the skyrmion Thiele equation to explain Hopfion motion”。更稳妥写法：

> Inspired by the Thiele description of magnon-driven skyrmions, we interpret the Hopfion motion through a generalized collective-coordinate equation where magnon-induced forces act on coupled translational and internal degrees of freedom.

## C5. Hopfion 动力学文献支点

### Liu et al. 2020

论文：*Three-dimensional dynamics of a magnetic hopfion driven by spin transfer torque*, Phys. Rev. Lett. 124, 127204.  
链接：https://arxiv.org/abs/2001.00417  
DOI：https://doi.org/10.1103/PhysRevLett.124.127204

主要结论：

- 研究对象是 frustrated magnet 中 Q_H=1 Hopfion。
- Hopfion 的 spin Berry phase 和对称性导致多个集体坐标在相空间中纠缠。
- 电流驱动下出现 longitudinal motion、transverse motion、rotational motion 和 dilation。
- 动力学由非绝热 STT 参数与阻尼参数之比控制。

对我们的启发：

这篇是当前最直接的理论桥。我们的自旋波驱动不是 STT，但 Hopfion 本身的集体坐标耦合结构相同。因此可以用它支持“Hopfion 动力学天然不是单一质心平移，而是平移、旋转、膨胀耦合”。

### Raftrey & Fischer 2021

论文：*Field-driven dynamics of magnetic Hopfions*, Phys. Rev. Lett. 127, 257201.  
链接：https://arxiv.org/abs/2104.13349  
DOI：https://doi.org/10.1103/PhysRevLett.127.257201

主要结论：

- 外场驱动下 Hopfion 有可识别的 resonant spin-wave modes。
- 模式在频域有特征振幅，在实空间有唯一 localization pattern。
- Hopfion、toron、target skyrmion 的频谱差异可作为实验 fingerprint。

对我们的启发：

我们的 paper 应补空间模态图，否则频率扫描只是驱动结果，不是完整 Hopfion 模式研究。

### Zhang et al. 2023

论文：*Magnon scattering modulated by omnidirectional hopfion motion in antiferromagnets for meta-learning*, Science Advances 9, eade7439.  
链接：https://pmc.ncbi.nlm.nih.gov/articles/PMC9908019/  
DOI：https://doi.org/10.1126/sciadv.ade7439

主要结论：

- 研究 magnon 与 Hopfion 运动之间的相互调制。
- 提出 Hopfion 运动可调制 magnon scattering。
- 文中提到 spin-wave polarization 与 Hopfion driving/Hall angle 的联系，并用 frequency dependence 训练/验证速度模型。

对我们的启发：

这为“magnon-Hopfion scattering 与运动速度/方向有关”提供了直接 Hopfion 文献支撑。虽然体系是 antiferromagnetic hopfion，不能直接代入我们的 frustrated FM 参数，但思想非常接近。

## C6. 对当前 Hopfion 数据的解释

| 现象 | Thiele/动量转移解释 | 证据等级 |
|---|---|---|
| `srcX` 主要 +z 漂移 | 入射 magnon 与 Hopfion 拓扑纹理交换横向动量，广义 gyrotropic response 导致近横向运动 | 中等 |
| `srcZ` 多数频率 -z | 轴向入射下纵向散射/动量传递占主导 | 中等 |
| `srcZ 100 GHz` 反向 +z | 可能耦合不同内部模式或散射通道，导致有效力反号 | 偏弱，需要模式图 |
| `100/1100 GHz` 双向控制 | 不同频率对应不同有效 magnon force，可切换力方向 | 中强现象，理论待补 |
| 1100 GHz 坍塌 | 强 magnon force 激发内部形变，超过 Hopfion 稳定阈值 | 中强 |

## C7. 建议写入 paper 的广义方程语言

可以写成概念方程，而不是假装已经推导完整解析式：

```text
G_ab(q) qdot_b + alpha D_ab(q) qdot_b = F_a^mag(omega, k, polarization, source) + F_a^edge + F_a^int
```

其中 `q` 可以包括：

```text
q = {X, Y, Z, R_ring, r_tube, Phi_toroidal, Phi_poloidal}
```

解释：

- `F^mag` 来自自旋波动量和角动量转移。
- `G_ab` 来自 Hopfion 的 Berry-phase / topological gyrotropic coupling。
- `D_ab` 描述阻尼。
- `F^int` 描述内部形变恢复力。

这比直接套 `G x v` 更诚实，也更适合 Hopfion。

## C8. 失败/不足记录

- 当前没有从 Mumax 数据拟合出 `G_ab`、`D_ab` 或 `F^mag`。
- 当前没有自旋波散射角、反射率、透射率的定量分析。
- 当前没有把 Hopfion 内部形变与速度变化关联起来。
- 因此 Thiele 部分只能作为理论解释框架，不能宣称已定量验证。

## C9. 下一步建议

1. 从频扫数据中提取速度 `v(f)`、能量吸收 `P(f)`、core/R/r 形变指标，做相关性图。
2. 对 `100 GHz`、`1100 GHz` 做模式图，判断力反号是否与不同内部形变有关。
3. 计算入射/散射自旋波动量流，至少做半定量方向判断。
4. 若要强理论，建立简化集体坐标模型：`Z` 平移 + `R/r` 形变 + 一个相位角，先解释双向控制。

