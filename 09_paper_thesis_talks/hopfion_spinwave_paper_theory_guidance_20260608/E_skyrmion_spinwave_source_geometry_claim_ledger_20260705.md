# E. Skyrmion 自旋波源几何 claim ledger

更新时间：2026-07-05

## 当前结论

这轮核查后，结论仍然要收紧写：

> 目前没有找到一篇可以直接证明“单个 skyrmion 在点源自旋波驱动下相对面源必然红移”的理论论文。已有文献可以支撑的，是 magnon-texture interaction 对入射 `k`、频率、波前、极化、散射截面、反射/透射模式、边界和源几何敏感。因此，Hopfion 点源/面源峰位差异应先写成“源几何改变有效入射谱与 scattering/loading channel”的合理解释；在完成本项目 `TB.1/TB.2` 的 `I(k,f)` 与近场散射分析前，不能写成已证明机理。

证据等级：

- `A`：PDF 已下载，并用 MinerU 或 PDF 文本抽取核对到原文图、公式或段落。
- `B`：PDF 文本已抽取，尚未跑 MinerU，但可定位到原文段落或图注。
- `C`：publisher/arXiv 页面核对到摘要或文章页内容，PDF 未成功解析或暂缺。

BBT/Zotero 状态：本 Codex 环境没有可用 Zotero/BBT connector。本文档只核 DOI、arXiv、原文页和 PDF 内容，不声称 citekey 已通过 Zotero/BBT 核对。正式论文写作前需人工或另一个带 Zotero 权限的 session 完成 citekey 校验。

## 可写进论文的安全 claim

| ID | 论文中可写的句子 | 证据位置 | 等级 | 不能写成 |
|---|---|---|---|---|
| B-01 | Magnon-skyrmion scattering is strongly wavenumber dependent, and the scattered magnon momentum can drive skyrmion motion. | Iwasaki, Beekman & Nagaosa, PRB 89, 064412 (2014), DOI `10.1103/PhysRevB.89.064412`, arXiv `1309.2361`; abstract, Fig. 1, Fig. 2, conclusion. MinerU: `/tmp/hopfion_skyrmion_spinwave_mineru_20260705/iwasaki_2014_magnon_skyrmion_scattering/auto/iwasaki_2014_magnon_skyrmion_scattering.md`, lines 11, 21, 24, 52, 54, 64, 88, 90. | A | 点源一定红移；2D skyrmion 的偏转角公式可直接套到 Hopfion。 |
| B-02 | The effective force on a skyrmion under a magnon current can be written in a Thiele-type description and is governed by magnon scattering cross sections. | Schutte & Garst, PRB 90, 094423 (2014), DOI `10.1103/PhysRevB.90.094423`, arXiv `1405.1568`; abstract, Sec. III, Sec. IV, Fig. 8, Fig. 12, Fig. 13. MinerU lines 7, 524, 548, 622, 709, 729, 745, 753, 786, 788. | A | Hopfion 的三维力学可以直接用该二维 Thiele 方程定量预测。 |
| B-03 | A skyrmion supports magnon-skyrmion bound states, including a breathing mode and, in part of parameter space, a quadrupolar mode; these are separate from the scattering continuum. | Schutte & Garst 2014; abstract, Fig. 4, Sec. III B, summary. MinerU lines 7, 421, 427, 766, 772, 784. | A | Hopfion 的 700/800/1000/1100 GHz 峰就是这些 skyrmion bound states。 |
| B-04 | In confined nanowires, the trajectory under spin-wave drive depends on both the magnon current and boundary forces; source placement and driving direction matter. | Zhang et al., NJP 19, 065001 (2017), DOI `10.1088/1367-2630/aa6b70`, arXiv `1701.02430`; abstract, Fig. 1-Fig. 4. MinerU lines 13, 21, 23, 34, 36, 38, 42, 49, 65, 71, 74, 76, 78, 97, 127, 134. | A | 点源和平面源只差一个幅度因子；边界/源近场可以忽略。 |
| B-05 | Strong local spin-wave driving can excite internal skyrmion modes, cause velocity breakdown, and even destroy the skyrmion. | Zhang et al. 2017; Fig. 5-Fig. 6 and summary. MinerU lines 101, 103, 107, 114, 116, 123, 136. Also Zhang, Ezawa & Xiao, Nanotechnology 26, 225701 (2015), DOI `10.1088/0957-4484/26/22/225701`, arXiv `1504.00409`; PDF text lines 243-250. | A/B | 强点源下的 Hopfion 位移一定是线性响应。 |
| B-06 | The direction of skyrmion motion under magnon scattering is non-intuitive: in high-energy limits, transverse momentum transfer can dominate and longitudinal transfer can be negligible. | Schroeter & Garst, Low Temp. Phys. 41, 817 (2015), DOI `10.1063/1.4932356`, arXiv `1504.02108`; abstract and conclusion. PDF text lines 8-16, 152-166, 1114-1217, 1257-1292. | B | Hopfion 必须沿自旋波传播方向运动。 |
| B-07 | Selected waveguide modes scatter differently from a skyrmion-imprint hybrid; scattering efficiency depends on both frequency and transverse mode number. | Kotus et al., APL Mater. 10, 091101 (2022), DOI `10.1063/5.0100594`; AIP article page abstract/results, Fig. 1, Fig. 2, Fig. 3, Fig. 5. Web-open lines 216-217, 230-231, 251-252, 277-282, 285-301, 332-348, 351-353. | C | 这是自由空间点源/面源 skyrmion 对照。 |
| B-08 | A propagating spin wave can cause an extended skyrmion to emit a secondary spin wave; the emitted pattern changes from nearly circular at long wavelength to more complex when the wavelength approaches the skyrmion size. | Mansell et al., APL 121, 242402 (2022), DOI `10.1063/5.0121363`; AIP article page abstract, lines 225-227. | C | Hopfion 点源 `srcZ` 的散射图样已经由这篇论文证明。 |
| B-09 | A local magnonic torque framework can translate fast spin-wave information into effective forces/torques on magnetic textures, beyond global momentum conservation alone. | Ai & Lan, PRB 107, 054441 (2023), DOI `10.1103/PhysRevB.107.054441`, arXiv `2211.12958`; abstract, Sec. II C-D, Fig. 1, conclusion. MinerU lines 11, 17, 19, 21, 23, 71, 77, 91, 93, 101, 111, 203, 210, 212. | A | 其 domain-wall 公式可直接作为 Hopfion 运动方程。 |
| B-10 | In AFM skyrmions, spin-wave polarization is an active control parameter for motion and Hall response; it should not be treated as a harmless detail. | Jin et al., PRB 104, 054419 (2021), DOI `10.1103/PhysRevB.104.054419`, arXiv `2103.00898`; PDF text lines 29-40, 75-88, 483-495, 543-560, 1233-1260, 1383-1419, 1439-1449. Lau, Hausler & Thorwart, PRB 109, 014435 (2024), DOI `10.1103/PhysRevB.109.014435`, arXiv `2306.17678`; PDF text lines 10-19, 726-842, 874-900. | B | FM Hopfion 的 `srcX/srcZ` 差异一定等同 AFM polarization effect。 |
| B-11 | Nonlinear magnon-skyrmion scattering can generate frequency-comb-like sidebands above a threshold drive; sidebands are therefore not automatically eigenfrequencies. | Wang et al., PRL 127, 037202 (2021), DOI `10.1103/PhysRevLett.127.037202`, arXiv `2102.02571`; PDF text lines 12-18, 103-130, 249-286, 485-491, 657-658, 781-785. | B | 任何多峰谱都等于线性本征模谱。 |
| B-12 | AFM skyrmions can theoretically act as magnonic lenses, and the paper explicitly discusses point-source/plane-wave interconversion in that AFM lens setting. | Wu, Wang & Lan, PRB 113, 174431 (2026), DOI `10.1103/j5hs-wsb7`, arXiv `2511.05905`; arXiv abstract; MinerU lines 13, 19, 23, 26, 155, 161, 165, 177, 187, 198, 202-209, 243. | A/C | 这直接证明 FM Hopfion 的点源/面源频移。 |

## 建议写法

英文正文可写：

> A direct theory comparing point-source and plane-wave spin-wave driving of an isolated skyrmion is not established. Nevertheless, magnon-skyrmion studies show that the response of a magnetic texture is controlled by the incident magnon wave vector, frequency, polarization, scattering cross section, boundary condition, and mode content. We therefore interpret the different Hopfion response peaks under point and plane sources as a source-geometry-dependent loading/scattering effect rather than as a shift of an intrinsic Hopfion eigenfrequency.

中文内部解释可写：

> 点源与面源的差别不是“同一束波强弱不同”，而是入射波的角谱、`k` 谱、近场分量和空间加载方式都不同。已有 skyrmion 文献支持这些变量会改变 scattering force、re-emission profile、mode conversion 和 Hall response；但 Hopfion 的红移机制必须由本项目自己的无 Hopfion 源谱和有 Hopfion 近场散射谱来证明。

## 论文中需要避开的句子

- “Skyrmion 文献已经证明点源驱动会造成红移。”
- “点源改变了 Hopfion 的本征频率。”
- “点源比平面源效率更高/更低。”
- “500 T 点源与 1 T 平面源可以直接比较驱动力。”
- “2D skyrmion Thiele 方程可直接定量预测 Hopfion 三维轨道。”
- “Mansell/Kotus 已经给出自由 skyrmion 的点源/面源对照。”
- “Wu/Wang/Lan 2026 的 AFM magnonic lens 就是我们 FM Hopfion 的机理证明。”

## 还缺的本项目证据

| 缺口 | 需要做什么 | 对应结论 |
|---|---|---|
| `I(k,f)` 源谱 | 无 Hopfion 情况下分别跑或提取平面源、点源的空间 FFT | 证明点源是否真的有更宽或偏低的有效 `k` 谱 |
| 入射/散射分离 | 有 Hopfion 情况下分区域分析入射波、散射波和 Hopfion 近场谱 | 证明峰位差异来自 scattering/loading channel |
| 能量归一化 | 用输入能量或总能量增量归一化位移、速度和谱峰强度 | 避免把 500 T 单格源和 1 T 面源直接比较 |
| 点源位置扫描 | 少量改变 source-Hopfion 相对位置 | 判断红移是几何稳健效应还是位置偶然效应 |
| 线性/非线性判别 | amplitude sweep 下看峰位是否漂移、是否出现 sidebands/frequency-comb | 区分 eigenmode、linear scattering peak 和 nonlinear sideband |

## 全文/页面核查记录

PDF 与解析路径：

- `/tmp/hopfion_skyrmion_spinwave_pdfs_20260705/iwasaki_2014_magnon_skyrmion_scattering.pdf`
- `/tmp/hopfion_skyrmion_spinwave_pdfs_20260705/schutte_garst_2014_magnon_skyrmion_scattering.pdf`
- `/tmp/hopfion_skyrmion_spinwave_pdfs_20260705/zhang_2015_all_magnetic_control.pdf`
- `/tmp/hopfion_skyrmion_spinwave_pdfs_20260705/zhang_2017_magnonic_momentum_transfer.pdf`
- `/tmp/hopfion_skyrmion_spinwave_pdfs_20260705/schroeter_garst_2015_high_energy_magnons.pdf`
- `/tmp/hopfion_skyrmion_spinwave_pdfs_20260705/ai_lan_2023_magnonic_torques.pdf`
- `/tmp/hopfion_skyrmion_spinwave_pdfs_20260705/wu_2026_afm_skyrmion_magnonic_lens.pdf`
- `/tmp/hopfion_skyrmion_spinwave_pdfs_20260705/wang_2021_frequency_comb.pdf`
- `/tmp/hopfion_skyrmion_spinwave_pdfs_20260705/jin_2021_afm_polarization.pdf`
- `/tmp/hopfion_skyrmion_spinwave_pdfs_20260705/lau_2024_bipartite_afm.pdf`

MinerU 输出：

- `/tmp/hopfion_skyrmion_spinwave_mineru_20260705/iwasaki_2014_magnon_skyrmion_scattering/auto/iwasaki_2014_magnon_skyrmion_scattering.md`
- `/tmp/hopfion_skyrmion_spinwave_mineru_20260705/schutte_garst_2014_magnon_skyrmion_scattering/auto/schutte_garst_2014_magnon_skyrmion_scattering.md`
- `/tmp/hopfion_skyrmion_spinwave_mineru_20260705/zhang_2017_magnonic_momentum_transfer/auto/zhang_2017_magnonic_momentum_transfer.md`
- `/tmp/hopfion_skyrmion_spinwave_mineru_20260705/ai_lan_2023_magnonic_torques/auto/ai_lan_2023_magnonic_torques.md`
- `/tmp/hopfion_skyrmion_spinwave_mineru_20260705/wu_2026_afm_skyrmion_magnonic_lens/auto/wu_2026_afm_skyrmion_magnonic_lens.md`

PDF 文本输出：

- `/tmp/hopfion_skyrmion_spinwave_txt_20260705/*.txt`

AIP PDF 状态：

- Kotus 2022 与 Mansell 2022 的 AIP PDF 直链被 Cloudflare/SSL 阻断，本轮只按 AIP 文章页内容与摘要核查；不要标为 PDF 已核。
