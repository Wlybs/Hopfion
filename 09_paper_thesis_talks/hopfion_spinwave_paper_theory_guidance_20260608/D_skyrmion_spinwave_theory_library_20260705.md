# D. Skyrmion 自旋波理论文献库扩展

更新时间：2026-07-05

## 使用边界

这份表是为 Hopfion 自旋波驱动论文准备的 skyrmion/spin-wave 理论资源库。当前状态是 abstract-level 与网页/DOI 初核，不等于全文 claim ledger。写进论文正文前还需要逐篇用 Zotero/BBT 核 citekey，并用 PDF/MinerU 核对具体公式、图号和段落。

当前仍未找到可以直接证明“skyrmion 点源必然相对面源红移”的标准理论论文。安全写法仍是：已有 skyrmion 和 magnetic-texture 文献支持 magnon-texture interaction 对频率、波矢、极化、模式数、散射角、反射/透射和源/波前几何敏感；Hopfion 的点源/面源峰位差异应先写成源几何改变有效入射谱和散射通道的合理假说，直到 TB.1/TB.2 给出本项目自己的 `I(k,f)` 证据。

## 一眼分组

| 组别 | 论文用途 | 论文写作中的安全位置 |
|---|---|---|
| S1 散射与动量转移 | 说明自旋波不是单纯能量泵，而是通过散射、反射、透射和动量转移给纹理有效力 | B 线 source geometry，C 线 force interpretation |
| S2 本征模与 magnon band | 说明 skyrmion/SkX 的响应可由 breathing、gyration、azimuthal、band/edge modes 组织 | A 线频率响应，但不能把 Hopfion drive windows 直接叫 eigenfrequency |
| S3 极化/材料依赖驱动 | 说明 spin-wave polarization、AFM/FIM compensation、linearly/circularly polarized modes 会改变速度和 Hall angle | K1 极化选择性与 K3 偏转角类比 |
| S4 波前、源几何与器件 | 说明 skyrmion 可重构、聚焦、散射、导引、发射或过滤 spin waves | 点源/面源差异、波前几何、k 谱宽度假说 |
| S5 前沿候选 | 2025-2026 新线索，暂不作为核心引用，适合背景或 future work | 只在全文核对后使用 |

## S1. 散射与动量转移核心

| 优先级 | 文献 | 初核来源 | abstract-level 安全 claim | 对 Hopfion 的用法 | 注意 |
|---|---|---|---|---|---|
| P0 | Iwasaki, Beekman, Nagaosa, *Theory of magnon-skyrmion scattering in chiral magnets*, PRB 89, 064412 (2014). DOI `10.1103/PhysRevB.89.064412`, arXiv `1309.2361` | arXiv / APS | single skyrmion 可散射 magnon，散射角强依赖 magnon wavenumber，动量交换可驱动 skyrmion | 支撑“响应窗口依赖 `k` 与散射通道” | 2D skyrmion，不能套给 Hopfion |
| P0 | Schutte & Garst, *Magnon-skyrmion scattering in chiral magnets*, PRB 90, 094423 (2014). DOI `10.1103/PhysRevB.90.094423`, arXiv `1405.1568` | arXiv / APS | 分析 magnon-skyrmion bound states、skew/rainbow scattering、magnon pressure force 与 Thiele force | 支撑“散射截面决定有效力” | 仍不是点/面源对照 |
| P1 | Schroeter & Garst, *Scattering of high-energy magnons off a magnetic skyrmion*, Low Temp. Phys. 41, 817 (2015). DOI `10.1063/1.4932356`, arXiv `1504.02108` | arXiv / DOI | 高能极限下 emergent magnetic field 主导散射，横向动量转移具有拓扑普适性，纵向动量转移在高能极限较小 | 支撑“运动方向不一定沿入射波直觉方向” | 高能极限，与我们 GHz/THz drive 需分开 |
| P0 | Kotus et al., *Scattering of spin waves in a multimode waveguide under the influence of confined magnetic skyrmion*, APL Materials 10, 091101 (2022). DOI `10.1063/5.0100594` | AIP full page | 选定频率与宽度量子数的 incident SW 经 skyrmion-imprint hybrid 后发生频率/模式相关的反射、透射与 mode conversion | 很适合 B 线：source/waveguide mode、frequency、mode number 共同决定 scattering efficiency | 结构是 nanodot+waveguide hybrid，不是自由 skyrmion |
| P1 | Mansell, Qin & van Dijken, *Interaction of propagating spin waves with extended skyrmions*, APL 121, 242402 (2022). DOI `10.1063/5.0121363` | AIP full page | 入射 spin wave 使 extended skyrmion 重新发射 secondary spin wave；低频近圆形，高频波长接近 skyrmion size 时图样复杂；DMI 改变 skyrmion size 可调 emission | 支撑“点源/面源波前差异会改变 re-emission/scattering profile” | micromagnetic，extended skyrmion，不是 point-vs-plane |
| P1 | Huang, Burnell & Marrows, *Transient retrograde motion of spin wave-driven skyrmions in magnetic nanotracks*, PRB 107, 224418 (2023). DOI `10.1103/PhysRevB.107.224418` | APS / White Rose | Thiele treatment 可预测 skyrmion 被拉向 spin-wave source 的 transient retrograde motion；边界、阻尼、track width 会改变短时运动方向 | 支撑“motion direction 由 scattering forces + boundary/dissipation 共同决定” | 是 nanotrack transient，不等于 Hopfion 稳态 |
| P0 | Ai & Lan, *Anatomy of spin-wave-driven magnetic texture motion via magnonic torques*, PRB 107, 054441 (2023). DOI `10.1103/PhysRevB.107.054441`, arXiv `2211.12958` | arXiv / APS | 提出 magnonic torque 框架，从快速 spin wave 中抽取 time-invariant torque 来解释 texture motion，超越单纯全局动量守恒 | 给 C 线补微观力解释，也适合 K1/K3 | 原文例子是 domain wall，不是 skyrmion/Hopfion |

## S2. 本征模、局域模式与 magnon band

| 优先级 | 文献 | 初核来源 | abstract-level 安全 claim | 对 Hopfion 的用法 | 注意 |
|---|---|---|---|---|---|
| P0 | Petrova & Tchernyshyov, *Spin waves in a skyrmion crystal*, PRB 84, 214433 (2011). DOI `10.1103/PhysRevB.84.214433`, arXiv `1109.4990` | arXiv / APS | 将 SkX 视为三组相锁 helices，推导低频 spin waves；低频模式是 skyrmion 位移 Goldstone modes | A 线背景：SkX 模式不等同 isolated skyrmion，也不等同 Hopfion | SkX crystal，非 isolated |
| P0 | Mochizuki, *Spin-Wave Modes and Their Intense Excitation Effects in Skyrmion Crystals*, PRL 108, 017601 (2012). DOI `10.1103/PhysRevLett.108.017601`, arXiv `1111.5667` | 本地已 MinerU / arXiv | 面内 AC field 激发 CW/CCW rotation，面外 field 激发 breathing；强激发可 redshift 与 melting | 频率扫描方法学核心 | 只作方法学和类比 |
| P0 | Roldan-Molina, Nunez & Fernandez-Rossier, *Topological spin waves in the atomic-scale magnetic skyrmion crystal*, NJP 18, 045015 (2016). DOI `10.1088/1367-2630/18/4/045015`, arXiv `1511.08244` | arXiv / IOP | SkX spin-wave bands 可有 Berry curvature、非零 Chern number 和 chiral edge spin waves | 支撑“skyrmion lattice 作为 magnonic/topological band medium” | 偏 band topology，不是 drive dynamics |
| P0 | Kravchuk et al., *Spin eigenmodes of magnetic skyrmions and the problem of the effective skyrmion mass*, PRB 97, 064403 (2018). DOI `10.1103/PhysRevB.97.064403`, arXiv `1711.10461` | 本地已 MinerU / DOI | isolated skyrmion eigenmodes 可按角量子数分类；正确 collective coordinate 下 skyrmion mass 问题需谨慎处理 | A/C 线：模式分类和 Thiele 坐标选择 | 不能把 2D skyrmion G 迁移给 Hopfion |
| P1 | Rozsa et al., *Localized spin waves in isolated k pi skyrmions*, PRB 98, 224426 (2018). DOI `10.1103/PhysRevB.98.224426`, arXiv `1810.06471` | arXiv / APS | isolated `k pi` skyrmion 有局域 magnon modes；breathing mode 与 burst/collapse instability 相关，阻尼可使 breathing overdamped | 支撑“强驱可触发内部模/坍塌通道” | 多阶 k pi skyrmion，与 Q_H=1 Hopfion 不同 |
| P1 | Bassotti, Silvani & Carlotti, *From the spin eigenmodes of isolated Neel skyrmions to the magnonic bands of a skyrmionic crystal*, IEEE Magn. Lett. 13, 6101505 (2022). DOI `10.1109/LMAG.2021.3136152`, arXiv `2112.04967` | arXiv / DOI | isolated skyrmion eigenmodes 可演化为 chain/crystal magnonic bands，DMI/exchange 调节 band gap 与 anticrossing | 支撑“isolated vs array/lattice 条件必须区分” | micromagnetic 参数特定 |
| P1 | Desplat & Dupe, *Eigenmodes of magnetic skyrmion lattices*, PRB 107, 144415 (2023). DOI `10.1103/PhysRevB.107.144415`, arXiv `2305.06248` | arXiv / APS | 比较不同稳定机制下 SkX eigenmodes；低频 modes 可对应 individual skyrmion internal degrees，拓扑不自动意味着有 skyrmion internal modes | 支撑“拓扑数不等于所有模式/动力学都相同” | 重点是 SkX 和稳定机制 |
| P1 | Xing, Zhou & Braun, *Magnetic Skyrmion Tubes as Nonplanar Magnonic Waveguides*, Phys. Rev. Applied 13, 034051 (2020). DOI `10.1103/PhysRevApplied.13.034051`, arXiv `1901.00253` | arXiv / APS | skyrmion tube 可作为非平面 magnonic waveguide，内部/边缘通道分离，局域驱动 breathing/rotational modes 可传输信号 | 对 3D/管状纹理很有启发，可作为 Hopfion 与 skyrmion-tube 对比 | tube 不是闭合 Hopfion |

## S3. 极化、AFM/FIM 与 Hall 角控制

| 优先级 | 文献 | 初核来源 | abstract-level 安全 claim | 对 Hopfion 的用法 | 注意 |
|---|---|---|---|---|---|
| P1 | Jin et al., *Magnon-driven skyrmion dynamics in antiferromagnets: Effect of magnon polarization*, PRB 104, 054419 (2021). DOI `10.1103/PhysRevB.104.054419`, arXiv `2103.00898` | arXiv / APS | AFM skyrmion motion 强依赖 magnon polarization；linearly polarized magnon 与 moving skyrmion 互相作用可产生复杂 Hall motion | 支撑 K1 “极化选择性不是附属变量” | AFM 体系 |
| P1 | Liu et al., *Spin-wave-driven skyrmion dynamics in ferrimagnets: Effect of net angular momentum*, PRB 106, 064424 (2022). DOI `10.1103/PhysRevB.106.064424`, arXiv `2112.13232` | arXiv / APS | FiM 中 net angular momentum 控制 ferromagnetic/antiferromagnetic force terms 比例与 Hall angle；还讨论 frequency-dependent motion | 支撑“材料参数和频率会改变 Hall response” | FiM 体系 |
| P1 | Lau, Hausler & Thorwart, *Spin wave driven skyrmions in a bipartite antiferromagnetic lattice*, PRB 109, 014435 (2024). DOI `10.1103/PhysRevB.109.014435`, arXiv `2306.17678` | arXiv / APS | AFM spin waves 可按 polarization/modes 分类；circular polarization 可产生 Hall effect，linear polarization 可沿传播方向加速 skyrmion | K1/K3 类比：极化决定有效运动方向 | AFM square lattice，不是 FM Hopfion |

## S4. 波前、源几何、聚焦和器件

| 优先级 | 文献 | 初核来源 | abstract-level 安全 claim | 对 Hopfion 的用法 | 注意 |
|---|---|---|---|---|---|
| P1 | Gruszecki et al., *Microwave excitation of spin wave beams in thin ferromagnetic films*, Sci. Rep. 6, 22367 (2016). DOI `10.1038/srep22367` | DOI/search 初核 | 局域 microwave source 可激发具有方向性的 spin-wave beams | 支撑“源几何会塑造波前/k 分布” | 不是 skyrmion paper；需全文核 |
| P1 | Wang et al., *Magnonic Frequency Comb through Nonlinear Magnon-Skyrmion Scattering*, PRL 127, 037202 (2021). DOI `10.1103/PhysRevLett.127.037202`, arXiv `2102.02571` | arXiv / APS | 高于阈值的 nonlinear magnon-skyrmion scattering 可生成等间距 frequency comb，spacing 等于 skyrmion breathing-mode frequency | A 线 TA.2 边带/frequency-comb 检查 | 强非线性，不可混为线性本征谱 |
| P1 | *Magnetic Skyrmion Generation by Reflective Spin Wave Focusing*, Frontiers in Physics 9, 729967 (2021). DOI `10.3389/fphy.2021.729967` | Frontiers full page | 反射 spin wave 可由曲边聚焦，并通过局域能量沉积产生 skyrmion | 支撑“波前/边界/聚焦改变局域响应” | 是 generation，不是 skyrmion drive |
| P0 | Wu, Wang & Lan, *Spin wave reconstruction with ray magnonics*, PRB 112, 014428 (2025). DOI `10.1103/5bqm-n4j2` | APS / Tianjin Univ page | 将传播 spin wave 分解为 magnon rays 并反演 phase；用 ray-by-ray 方式分析 magnetic skyrmion 上的 spin-wave profile topology | B 线最贴近“波前/入射角/相位如何经 skyrmion 重构” | 需全文核公式后再用 |
| P0 | Wu & Lan, *Spin-wave vortex as a topological probe of magnetic textures*, PRB 112, 064410 (2025). DOI `10.1103/bvvv-kk4j` | APS / Tianjin Univ page | spin-wave flow 中的 vortex 可探测 background magnetic texture topology | 支撑“spin-wave pattern 可作为纹理拓扑读出，而非仅受动量影响” | 更偏 probe，不是 drive |
| P1 | Zhang, Wu & Lan, *Ballistic magnon circulators with magnetic skyrmions*, Chinese Phys. B 34, 107503 (2025). DOI `10.1088/1674-1056/addaa6` | CPB / Tianjin Univ page | magnetic skyrmion 可作为 magnon circulator 中非互易路由元件，系统研究 spin-wave transport behavior | 支撑器件层面的 skyrmion-controlled spin-wave routing | 器件几何，非 Hopfion |
| P0 | Wu, Wang & Lan, *Antiferromagnetic skyrmion as a magnonic lens*, PRB 113, 174431 (2026). DOI `10.1103/j5hs-wsb7`, arXiv `2511.05905` | arXiv / APS | AFM skyrmion 可在 DMI 超过阈值后作为 magnonic lens，将 spin-wave propagation directions 有组织地转换；机制主要是 DMI deflection | 目前最接近“点源/面波互相转换”的 skyrmion 线索 | AFM skyrmion lens，不等同 FM Hopfion 点/面驱动 |

## S5. 2025-2026 前沿候选

| 优先级 | 文献 | 初核来源 | 为什么保留 | 使用限制 |
|---|---|---|---|---|
| P2 | Koyama & Kawaguchi, *Point-gap topology of damped magnon excitations in skyrmion strings*, arXiv `2605.07435` (2026) | arXiv | 用 spin-wave theory + damping 讨论 skyrmion-string lattice 中 magnon propagation direction 和 non-Hermitian topology | 前沿预印本，离 Hopfion drive 较远 |
| P2 | Zheng et al., *Spin-Hall-Like Magnon Transport in a Synthetic Antiferromagnetic Skyrmion Lattice*, arXiv `2605.27822` (2026) | arXiv | SAF SkX 中 linear spin-wave theory 给出 layer-polarized edge modes | 可作 topological magnon transport 背景，不作 B 线核心 |
| P2 | Timofeev & Aristov, *Magnon edge states of skyrmion crystal in non-uniform magnetic field*, arXiv `2510.16970` (2025) | arXiv | 非均匀 field 下 SkX 界面可出现 localized magnon states | 偏 band/edge-state，不直接解释点源红移 |
| P2 | *Magnon Superlattices around Skyrmions in Frustrated Magnets*, arXiv `2601.00363` (2026) | arXiv | frustrated magnets 中 skyrmion 与 magnon hybridization 可能形成 real-space localization patterns | 与本项目 frustrated-FM 背景相近，但需全文核实和等待同行评议 |
| P2 | *Domain wall skyrmion-based magnonic crystal*, PRB (2026). DOI `10.1103/y4nd-8d93`, arXiv `2509.19741` | APS / arXiv | 用 domain-wall skyrmion chain 控制 DW spin-wave propagation 与 bandgaps | 是 domain-wall skyrmion device，不是 isolated skyrmion drive |

## 推荐优先级

1. 论文 B 线立刻可用的核心扩展：Kotus 2022、Mansell 2022、Ai & Lan 2023、Wu/Wang/Lan 2025、Wu/Wang/Lan 2026。
2. 论文 A 线补理论厚度：Petrova 2011、Roldan-Molina 2016、Rozsa 2018、Desplat 2023、Xing 2020。
3. K1/K3 极化和偏转角类比：Jin 2021、Liu 2022、Lau 2024。
4. 只作前沿背景，不进核心论证：S5 全部候选。

## 仍需 BD 跟踪的全文核对

这些新增资源应并入 `Hopfion-6cm` 的后续 claim ledger，而不是直接写进论文正文。最低全文核对顺序建议：

1. Kotus 2022：记录 scattering efficiency matrix 的定义、频率分区和与 skyrmion/imprint resonance 的关系。
2. Mansell 2022：记录 low-frequency circular re-emission 与 high-frequency complex pattern 的图号。
3. Ai & Lan 2023：提取 magnonic torque 公式与其适用边界。
4. Wu/Wang/Lan 2025 + Wu/Wang/Lan 2026：核 point/plane/ray/lens 相关公式，避免过度类比。
5. Lau 2024 + Jin 2021 + Liu 2022：核 polarization/Hall-angle 结论。
