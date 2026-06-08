# A. 频率扫描与固有/共振频率研究

## A1. 这条线要回答什么

我们现在有很多频率扫描结果，但 paper 不能只写“这个频率位移大，那个频率位移小”。这条线的目标是把这些峰分成三类：

1. **固有频率 eigenfrequency**  
   Hopfion 自己的小振幅自由振荡频率。严格说需要脉冲 FFT 或线性本征值分析确认。

2. **共振耦合频率 resonant coupling frequency**  
   外部驱动频率与某个内部模式耦合较强，有能量吸收或模式空间图支持，但还未严格完成本征模求解。

3. **驱动响应窗口 drive-response window**  
   位移或速度很大，可用于控制，但可能混合了自旋波传播、散射推力、边界、阻尼和非线性形变，不能直接叫固有频率。

## A2. 单 skyrmion 固有模式文献结论

### Lin, Batista & Saxena 2014

论文：*Internal modes of a skyrmion in the ferromagnetic state of chiral magnets*, Phys. Rev. B 89, 024415.  
链接：https://arxiv.org/abs/1309.5168  
DOI：https://doi.org/10.1103/PhysRevB.89.024415

主要结论：

- 研究对象是单个 skyrmion，而不是 skyrmion crystal。
- 弱形变可以分解成本征内部模式，这些模式局域在 skyrmion 附近。
- 在 magnon continuum 以下存在多个 internal modes，包括 translational mode 和不同类型的 breathing modes。
- 磁场降低时，内部模式数量增加；低场区若若干模式变 gapless，意味着单个 skyrmion 解趋于不稳定。
- 外加 easy-axis anisotropy 可稳定单 skyrmion。

对我们的启发：

Hopfion 频率响应也应先找“局域内部模式”。如果一个频率只是让 Hopfion 质心移动很大，但没有显示局域内部振荡，就不应直接叫固有频率。

### Zhang et al. 2017

论文：*Eigenmodes of Neel skyrmions in ultrathin magnetic films*, AIP Advances 7, 055212.  
链接：https://arxiv.org/abs/1612.06622  
DOI：https://doi.org/10.1063/1.4983806

主要结论：

- Néel skyrmion lattice 中可看到 breathing、counterclockwise、clockwise 三类低阶模式。
- 对 isolated skyrmion，主要保留 breathing 和 counterclockwise mode。
- clockwise mode 很依赖 skyrmion-skyrmion interaction，因此在单个 skyrmion 中不存在或很弱。

对我们的启发：

我们当前 Hopfion 是周期边界下的单 Hopfion 初态，但不是 skyrmion crystal。若借鉴 skyrmion 文献，应优先引用 isolated skyrmion 结果，而不是把 skyrmion lattice 的三峰结构直接套过来。

### Kravchuk et al. 2018

论文：*Spin eigenmodes of magnetic skyrmions and the problem of the effective skyrmion mass*, Phys. Rev. B 97, 064403.  
链接：https://arxiv.org/abs/1711.10461  
DOI：https://doi.org/10.1103/PhysRevB.97.064403

主要结论：

- skyrmion 局域 magnon mode 可按角量子数 `mu` 分类。
- 至少有 `mu=0` breathing mode 和 `mu=+/-1` gyrotropic family。
- 大半径极限下有尺度律：breathing mode 约随 `R_s^-2`，不同 gyrotropic branch 约随 `R_s^-1` 或 `R_s^-3`。
- 用正确 traveling-wave 集体坐标时，ferromagnetic skyrmion 的平移动力学是 massless Thiele equation。

对我们的启发：

Hopfion 频率必须和几何尺度一起讨论。我们应至少跟踪 `center(t)`、环半径 `R(t)`、管半径 `r(t)`，甚至 toroidal/poloidal phase。只看位移会把平移、呼吸、形变混在一起。

### Garanin, Jaafar & Chudnovsky 2020

论文：*Breathing Mode of a Skyrmion on a Lattice*, Phys. Rev. B 101, 014418.  
链接：https://arxiv.org/abs/1906.09212  
DOI：https://doi.org/10.1103/PhysRevB.101.014418

主要结论：

- breathing mode 可看作 skyrmion 半径和 chirality angle 的耦合振荡。
- breathing 频率随外磁场变化，在接近稳定性边界时 softening。
- 大振幅 breathing 会强阻尼，甚至导致 collapse；小振幅 breathing 可较稳定。

对我们的启发：

`freq_switch v3` 中 1100 GHz 阶段有效反向推动 Hopfion，但随后 core=0，不能只写成“1100 GHz 最好”。它也可能是强耦合导致形变累积越过稳定阈值。

## A3. 磁场驱动频率和自旋波驱动频率的区别

磁场驱动更像“全局摇晃”。例如 `H_z sin(2πft)` 接近均匀面外驱动，容易选择 breathing-like mode。面内磁场更容易选择 rotational/gyrotropic-like mode。

自旋波驱动更像“一束带波长和方向的水波打到拓扑结构上”。它不只有频率 `f`，还有：

- 波矢 `k`
- 群速度
- 衰减长度
- 极化
- 入射方向
- 反射/散射系数

因此自旋波驱动下的响应峰不一定等于固有频率。它可能是内部模式耦合、传播效率和动量传递效率共同决定的结果。

## A4. 当前 Hopfion 频率证据分级

| 频率窗口 | 现象 | 证据等级 | 推荐表述 |
|---|---|---|---|
| `srcX 200 GHz` | 位移强，能量吸收摘要中 `dE/dt` 最大且拟合质量高 | 较强 | candidate resonant coupling frequency |
| `srcZ 100 GHz` | 位移方向异常为 +z，能量吸收摘要标为强响应 | 中等 | candidate resonant coupling frequency, pending energy-slope sign check |
| `srcX 1000 GHz` | 位移强，0.5 ns 中更明显 | 中等 | strong drive-response window |
| `srcZ 1100 GHz` | 位移最强，可用于反向控制，但强驱动后坍塌 | 中等 | strong nonlinear drive-response window |
| 点源 `srcX 700 GHz` | 相对平面源红移 | 中等 | point-source response peak |
| 点源 `srcZ 800 GHz` | 相对平面源红移，方向复杂 | 中等 | point-source response peak |

## A5. 失败/不足记录

- 当前没有真正的 Hopfion eigenmode calculation。
- 当前没有 pulse-off free oscillation FFT。
- 当前没有 cell-wise FFT spatial mode map。
- 能量吸收谱摘要已存在，但 `srcZ` 表中多处 `dE/dt` 为负，必须复核符号含义和拟合窗口。
- 因此，严格 paper 中不能写“we identify the eigenfrequency at 1000 GHz/1100 GHz”。可以写“we identify frequency-selective drive-response windows, among which 200 GHz and 100 GHz are candidate resonant coupling frequencies”.

## A6. 下一步建议

1. 复核能量吸收谱，统一窗口，报告 `dE/dt`、`|dE/dt|` 和拟合 `R^2`。
2. 做短脉冲自由振荡，输出 `PSD_center`、`PSD_R`、`PSD_r`、`PSD_E`。
3. 对 `100/200/1000/1100 GHz` 做空间 FFT 模态图。
4. 写 paper 时用“eigenfrequency / resonant coupling / drive-response”三级术语。

