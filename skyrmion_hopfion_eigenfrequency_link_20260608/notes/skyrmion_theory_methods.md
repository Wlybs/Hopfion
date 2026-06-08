# Skyrmion 固有频率理论方法摘记

## 1. 微波吸收谱方法

Mochizuki 2012 是最直接可迁移的范式。做法是先给 skyrmion crystal 一个很短的磁场脉冲，然后对总磁化 `m(t)` 做傅里叶变换，得到动态磁化率或吸收谱。峰位再通过谐波驱动和空间快照确认模式类型。

关键方法点：

- 面内 ac field 激发两支旋转模式，通常对应 CW / CCW gyrotropic-like modes。
- 面外 ac field 激发 breathing mode。
- 圆偏振选择性很强，说明“激励方向/偏振”本身就是模式选择规则。
- 强激发会造成非线性 redshift，甚至导致 skyrmion lattice melting。

迁移到 Hopfion：我们不能只看某个频率下位移最大。更稳妥的判据是对 `m(t)`、Hopfion 质心、`R(t)`、`r(t)`、`E_total(t)` 做 FFT/吸收谱，再查看该频率下空间振幅是否局域在 Hopfion core、shell 或 vortex-line 附近。

## 2. 线性本征值问题与模式量子数

Kravchuk et al. 2018 把 skyrmion 的小振幅扰动写成角向量子数 `mu` 的本征模。核心结论是，skyrmion 至少有 `mu=0` breathing mode 和 `mu=+/-1` gyrotropic family；大半径极限下有清晰尺度律：

- breathing mode: `omega_0 ~ R_s^-2`
- one gyrotropic branch: `omega_-|mu| ~ R_s^-1`
- opposite branch: `omega_|mu| ~ R_s^-3`

它还指出，用真正对应平移的集体坐标时，ferromagnetic skyrmion 的平移动力学服从 massless Thiele equation。所谓有效质量往往来自对“中心”的定义混合了高频 gyrotropic mode。

迁移到 Hopfion：Hopfion 的模式不应只用“质心运动”分类。它至少需要三个坐标层级：整体平移、环半径/管半径呼吸、环面/极向扭转相位。报告中建议用 Hopfion 的 toroidal/poloidal 几何来类比 `mu` 分类。

## 3. 集体坐标 breathing 理论

Garanin et al. 2020 把 skyrmion breathing mode 视为尺寸和 chirality angle 的耦合振荡。其重要启发不是某个具体频率值，而是两点：

- 频率会随外场变化，在接近稳定性阈值时 softening。
- 大振幅 breathing 可能被 spin-wave reservoir 强烈阻尼并以 collapse 结束，小振幅则可以保持稳定振荡。

迁移到 Hopfion：我们 `freq_switch v3` 中 1100 GHz phase 造成 t≈0.91 ns core=0，很像强共振/强耦合下的非线性失稳。这个现象可以放进“强激发超过拓扑结构形变阈值”的理论叙事，而不是简单归因于数值事故。

## 4. Spin-wave-driven motion 的频率依赖

Zhang et al. 2018 的 spin-wave-driven skyrmion nanostrip 工作提醒我们：自旋波驱动速度峰不等于本征频率峰。速度受至少三项共同控制：

- 入射自旋波在该频率能否传播，以及到达 skyrmion 时的幅度。
- skyrmion 对该频率自旋波的反射/散射系数。
- skyrmion 内部本征模与入射波的耦合矩阵元。

迁移到 Hopfion：点源和平面源的频率峰红移不能只用“固有频率变了”解释。更自然的解释是：点源激发的是宽 `k` 谱/球面波，平面源激发的是较纯的传播方向和波矢，因此二者在相同 Hopfion 上看到不同的有效响应峰。

## 5. Hopfion 文献的直接参照

Raftrey & Fischer 2021 已经把 magnetic Hopfion 的场驱动共振模式当作“3D 拓扑结构指纹”来做，强调频谱峰和空间局域图必须一起看。Sobucki et al. 2022 进一步从本征值问题角度给出 Bloch hopfion 的丰富 spin-wave spectrum。2025 年 Tejo & Otxoa 的预印本则给了 Hopfion breathing mode 的集体坐标图像：core diameter 与 shell width 协同呼吸，拓扑荷保持不变。

因此，Hopfion 的固有频率研究应直接采用 skyrmion 的谱学范式，但模式分类要升级为三维：core/shell/vortex-line localization、toroidal/poloidal phase、translation/dilation/twist 的耦合。
