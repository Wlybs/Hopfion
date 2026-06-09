# Skyrmion / Hopfion 固有频率理论方法摘记

## 0. 先把“固有频率”和“驱动响应峰”分开

固有频率是体系在小扰动后自己会振荡的频率，像轻轻敲一下杯子，杯子自己响出的音高。连续单频驱动的响应峰则像拿一个外部喇叭去扫频，哪个频率下杯子晃得最大，除了杯子的本征音高，还会受喇叭方向、波传播、散射窗口、阻尼和非线性影响。

所以本文后续建议采用两层判据。第一层是 pulse + FFT ringdown，即用弱宽带脉冲轻敲 Hopfion，然后从 `m_x(t), m_y(t), m_z(t), E_total(t)` 的自由振荡谱里找候选固有频率。第二层才是和单频自旋波驱动峰对照，能对上的频率可以称为“候选共振耦合频率”，对不上的频率应更保守地称为“强驱动窗口”或“传播/散射增强窗口”。

## 1. Mochizuki 2012：SkX 的三类微波模式和偏振选择性

Mochizuki 2012 是 skyrmion 共振谱最清楚的范式之一。它研究的是 skyrmion crystal，不是单个 skyrmion，但对“如何从驱动谱识别模式”很有参考价值。

可核验原文事实如下：

- 面内 ac field 下有两支约 `1 GHz` 的旋转模式，面外 ac field 下有一支 breathing mode。原文摘要直接写到面内场出现两个共振峰、面外场出现 breathing-type mode；总结部分又将低频支称为 CCW，高频支称为 CW。来源：Mochizuki, PRL 108, 017601 (2012), p.1 abstract; p.5 summary。
- 外加静态 `H_z` 增大时，面内两支旋转模式频率上升，而面外 breathing mode 频率下降。来源：Mochizuki 2012, p.2, Fig.2(a,b) 及 inset 描述。
- 模式识别不是只看峰位，而是用谐波场在峰频处重放动力学。面内低能/高能模式分别用 `omega_R = 6.12e-3` 和 `1.135e-2` 追踪；面外 breathing 用 `omega_R = 7.76e-3` 追踪。来源：Mochizuki 2012, p.2-p.4, Fig.3(a-c)。
- 圆偏选择性很强。左旋圆偏 LHP 显著增强低频旋转模式，右旋 RHP 对该模式不能有效激发。来源：Mochizuki 2012, p.3, Fig.4。
- 谱图计算的阻尼为 `alpha_G = 0.04`，其他动力学图使用 `alpha_G = 0.004`。来源：Mochizuki 2012, p.2 方法段。用户关心的 `alpha=0.001` 与 `alpha=0.1` 对比不属于 Mochizuki 2012，而属于 Raftrey-Fischer Hopfion 论文，见第 4 节。

生动理解：面内场像横向拨动一个小陀螺，陀螺可以顺时针或逆时针绕芯转；面外场像从上往下按压一个软泡泡，skyrmion 面积一会儿胀大一会儿缩小。圆偏振的意义是，手的旋转方向如果和陀螺自己的方向对上，就特别容易拨响；方向反了，就算频率接近也不容易耦合。

迁移到我们的 Hopfion：`srcX` 更像面内/twist/translation 族的选择器，`srcZ` 更像 axial/breathing 族的选择器。但我们的自旋波驱动是传播波，不是均匀微波场，因此还必须把传播和散射窗口剥离出来。

## 2. Kravchuk 2018：单个 skyrmion 的线性本征模谱

Kravchuk et al. 2018 更贴近“单个 skyrmion 固有频率”的理论问题。它不是从某个驱动频率现象出发，而是把小振幅扰动写成带角向量子数 `mu` 的本征值问题。

可核验原文事实如下：

- 大半径极限下，局域模频率有三类尺度律：breathing `omega_0 ~ R_s^-2`，负角向量子数分支 `omega_-|mu| ~ R_s^-1`，正角向量子数分支 `omega_|mu| ~ R_s^-3`。来源：Kravchuk et al., PRB 97, 064403 (2018), p.1 abstract; p.4, Eq.(13) 与 Fig.2。
- 扰动写成 `cos(omega tau + mu chi + eta)` / `sin(omega tau + mu chi + eta)` 的形式，`mu` 决定绕 skyrmion 中心一圈时的节点数。来源：Kravchuk 2018, p.3, eigenvalue problem 段。
- 对任意 skyrmion 半径，至少有三支局域模：`mu=0` breathing mode，以及 `mu=+1` 和 `mu=-1` 两支 gyrotropic mode。`mu=+1` 是零频 translational mode；`mu=-1` 是 high-frequency gyrotropic mode。来源：Kravchuk 2018, p.4, Fig.2 和 Fig.3。
- 半径更大时会出现 `|mu| >= 2` 的更高角向模；每个给定 `mu` 至多有一支局域模。来源：Kravchuk 2018, p.4, Fig.3。
- 用 topological-charge density 的一阶矩作为集体坐标时，skyrmion 平移动力学是 massless Thiele equation；所谓有效质量问题与不恰当的中心定义和高频模混合有关。来源：Kravchuk 2018, p.6, Eq.(21) 附近和结论段。

生动理解：`mu` 可以想成 skyrmion 边界上波纹的花瓣数。`mu=0` 是整个圆一起胖瘦变化；`mu=1` 像整个圆心平移；更高 `mu` 则像边缘出现两个、三个或更多瓣的形变。Hopfion 不能直接套二维花瓣数，但可以保留这个思想：先定义几何坐标，再按对称性和局域位置给模式命名。

迁移到我们的 Hopfion：不要把所有运动都叫“质心漂移”。Hopfion 至少要分成整体平移、环半径/管半径 breathing、环面相位 twisting、vortex-line 或 core/shell 局域响应。ringdown 谱的任务正是先把这些候选模的频率找出来，再决定哪些频率和自旋波驱动真正耦合。

## 3. Garanin 2020：breathing 的集体坐标启发

Garanin et al. 2020 把 skyrmion breathing mode 视为尺寸和 chirality angle 的耦合振荡。当前文件尚未重新解析该 PDF，因此以下两点保持为二级文献摘记，不作为新核验事实使用：

- 频率会随外场变化，在接近稳定性阈值时 softening。[未核实页码]
- 大振幅 breathing 可能被 spin-wave reservoir 强烈阻尼并以 collapse 结束，小振幅则可以保持稳定振荡。[未核实页码]

迁移到 Hopfion：我们 `freq_switch v3` 中 1100 GHz phase 造成 t≈0.91 ns core=0，可以谨慎写成“强激发超过拓扑结构形变阈值的候选证据”。在没有 ringdown 本征峰和空间模图之前，不应直接称为“breathing 本征模导致 collapse”。

## 4. Raftrey-Fischer 2021：Hopfion 的场驱动本征谱范式

Raftrey & Fischer 2021 是和我们最直接相邻的 Hopfion 频谱论文。它研究的是 DMI 手性磁体中外场驱动的 Hopfion 模式，而我们研究的是 frustrated ferromagnet 中自旋波驱动的纳米级 Hopfion；两者材料和长度尺度不同，因此 GHz 与百 GHz/THz 量级差异不是矛盾。

可核验原文事实如下：

- 体系参数为 `A = 2.19 pJ/m`, `D = 0.395 mJ/m^2`, `m_s = 384 kA/m`；圆柱高度 `h = 90 nm`、直径 `d = 200 nm`，顶部和底部 `2 nm` 固定为 `(0,0,1)`，手性周期 `L = 4*pi*A/D = 70 nm`，网格 `2 nm`，并排除非局域退磁能。来源：Raftrey & Fischer, PRL 127, 257201 (2021), p.5 方法段。注意：若把 `70 nm` 写成样品高度是不对的；解析文本中 `70 nm` 是 chiral period `L`。
- 低阻尼谱使用 `alpha=0.001`，高阻尼对比使用 `alpha=0.1`。低阻尼下用 `+z` 方向 sinc 脉冲，截止 `15 GHz`、幅度 `5 mT`、峰值偏移到 `0.67 ns`，总时长 `20 ns`、采样 `17 ps`。来源：Raftrey-Fischer 2021, p.6 方法段。
- 该文用空间平均的 `delta m_z(t)` 做 Fourier transform 来得到共振频率；再逐胞对 `delta m_z(r,t)` 做 FFT 来画空间模图。来源：Raftrey-Fischer 2021, p.6-p.7, Fig.2(b,c) 与 Fig.3。
- Fig.2 中 Hopfion 谱峰标为 `h.1` 到 `h.5`；静态 `+z` 场从 `0` 到 `50 mT` 扫描时，Hopfion 频谱随场增大整体红移。`32 mT` 附近 Hopfion 变为 toron，并伴随谱的不连续；`h.2-h.5` 与 `t.2-t.5` 跨转变不连续，只有 `h.1` 连续。来源：Raftrey-Fischer 2021, p.7, Fig.2(a)。
- Hopfion 对脉冲场的响应包含 out-of-plane `M_z` breathing 和 in-plane `M_x/M_y` twisting。MinerU 文本中一句把 `M_z` OCR 成 `M_2`，但同页 Fig.3 caption 明确区分绿色 `M_z` 与蓝/红 `M_x/M_y`，因此此处按图注校正为 `M_z`。来源：Raftrey-Fischer 2021, p.7, Fig.3。
- 模式空间分布是环面附近的同心环局域。`h.2` 振幅最大，位于 Hopfion 中央 torus，并在上下 vortex ring 有对称分量；`h.3` 只在 vortex lines 处活跃；`h.1` 频率最低、空间范围最大并耦合到 disk 边界；`h.4/h.5` 主要集中于 vortex lines 或中心附近若干 torus。来源：Raftrey-Fischer 2021, p.8, Fig.3(b)。
- `h.3` 和 toron 的 `t.3` 均有约 `5 GHz` 共振，并分别局域在 Hopfion vortex lines 与 toron Bloch points。来源：Raftrey-Fischer 2021, p.8, Fig.3(b,d) 相关描述。
- 阻尼对谱的可见性影响很大。`alpha=0.001` 时有九个强度不同的峰；`alpha=0.1` 时峰展宽并合并为一个约 `4 GHz` 的宽带。来源：Raftrey-Fischer 2021, p.9, Fig.4。

生动理解：Raftrey-Fischer 的 Hopfion 不是一个只会整体平移的小球，而像一个带有上下涡线和中央环面的三维乐器。`h.2` 像中央环和上下涡线一起被敲响，`h.3` 更像只敲到涡线；阻尼变大后，本来能分辨的许多音符会糊成一个宽峰。

和我们的关键对照：Raftrey-Fischer 是 DMI 手性磁体，样品尺度由 `L=70 nm` 的手性周期控制，谱在 `~5 GHz` 和 `15 GHz` 以下；我们是 frustrated FM，Hopfion 尺度约 `R~2 nm`，现有响应窗口在 `100-1100 GHz`。小得多的长度尺度会把频率推高，材料能标也不同，因此“他们 GHz、我们百 GHz/THz”不能作为矛盾，而应作为材料体系差异的一部分来解释。

## 5. 自旋波驱动频率依赖：为什么还要做 ringdown

Zhang et al. 2018 的 spin-wave-driven skyrmion nanostrip 工作提醒我们：自旋波驱动速度峰不等于本征频率峰。当前文件未重新解析该文 PDF，因此只保留方法层面的提醒，不列为新核验事实：

- 入射自旋波在该频率能否传播，以及到达 skyrmion 时的幅度，会改变响应峰。[未核实页码]
- skyrmion 对该频率自旋波的反射/散射系数会改变速度或位移峰。[未核实页码]
- 内部本征模与入射波的耦合矩阵元会决定某个本征模是否真的被该源激发。[未核实页码]

迁移到 Hopfion：点源和平面源的频率峰红移不能只用“固有频率变了”解释。更自然的解释是：点源激发宽 `k` 谱/球面波，平面源激发较纯传播方向和波矢，因此二者在同一个 Hopfion 上看到不同有效响应峰。下一步 ringdown 谱正是为了把“Hopfion 自己的音高”和“自旋波传过来时最容易推它的窗口”分开。

## 6. 本项目的写作结论边界

目前可以稳妥写：

- 文献上，skyrmion/Hopfion 的固有频率通常通过弱脉冲激励后的自由振荡 FFT、动态磁化率、以及空间分辨模图共同确认。
- 文献上，驱动方向有选择规则。面内场偏向 rotational/gyrotropic/twisting，面外场偏向 breathing/axial 响应。
- 对 Hopfion 而言，仅有频率扫描的运动幅度或能量斜率还不足以宣称本征频率；必须补 pulse ringdown 谱。

暂时不能写：

- 不能把 `srcZ 100 GHz` 直接叫 Hopfion 本征频率。现有 energy absorption audit 已将它降级为 `dE/dt<0` 的最强绝对能量率响应窗口，而非正吸收峰。
- 不能把 `srcZ 1100 GHz` 直接叫 breathing 本征频率，除非 ringdown 谱中 `m_z` 或 `E_total` 出现对应自由振荡峰，并最好有空间模图确认。
- 不能把 Raftrey-Fischer 的 `~5 GHz` Hopfion 模式拿来和我们的 `100-1100 GHz` 直接数值比较；只能比较方法、模式分类和尺度差异逻辑。
