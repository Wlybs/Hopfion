# Hopfion 自旋波驱动论文 — 项目总指导（Master Plan）

> 生成：2026-07-03（Claude Opus 多智能体规划 workflow：4 数据审计 + 3 文献核实 + 3 竞争方案 + 2 评审 + 1 诚信守门，共 13 agents）
> 状态：**主导文件（active）**。取代 `07_thiele_theory_model/hopfion_thiele_research_plan_20260615/RESEARCH_PLAN.md`（旧版只操作化了 C 线，本版把 A/B/C 三线统一成一篇论文并给出分工）。
> 单一信源分工：物理进度 → vault `Hopfion-Physics/progress.md`（canonical）；任务状态 → bd；本文件 = 论文级研究规划与执行路线。

---

## 0. 定位与"为什么重做"

用户目标：把现有 frustrated-FM Hopfion 自旋波驱动数据（点源/平面源 × 频率扫描 × 幅度扫描）**从"现象堆砌"抬成一篇有理论的好论文**。三条借鉴线：
- **A 频率**：借 skyrmion 本征模/共振研究，给频率扫描一个自洽理论解释。
- **B 源几何**：借 skyrmion 点源 vs 平面源 / magnon 散射结论，解释两种源的现象差异。
- **C Thiele**：借 skyrmion Thiele 方程结论，解释自旋波驱动下的动力学。

旧 Codex 规划的三处不足（评审共识）：① 只把 C 线操作化，A/B 线停在文字建议；② 没有统一图表规划与分工；③ G/D 张量首算后收敛门失败（`delta=1 vs 2`：G_XY 变化 ~80%，D 对角 ~19%），旧 Codex prompt 已过时。本版全部修复。

**评审裁决**：3 个竞争方案（理论优先 / 叙事优先 / 审稿人优先）经 2 位评审打分，**审稿人优先方案胜出（18 vs 16/16）**。最终主线 = 采其机理骨架，嫁接叙事方案的"三旋钮"标题框架 + 期刊层级决策规则，嫁接理论方案的数值收敛阶梯。

---

## 1. 一句话主线 + 三旋钮框架（摘要/标题层）

> **主线（送审一句话）**：一个三维阻挫铁磁 Hopfion 的自旋波驱动运动，可由**驱动频率、源几何、激励极化**三个旋钮选择性调控；其驱动响应窗口（A）源于**与纹理的 k 依赖 magnon 散射**（B），而净力在纹理上的投影由**可从静态纹理直接计算的广义集体坐标（Thiele）G/D 张量**组织（C）——由此给出一个**无自由参数、可证伪的漂移/偏转角预言**，并（若收敛门通过）定量区分闭合环 Hopfion 与 2D skyrmion。**全程不声称任何已解析的线性本征频率。**

**三旋钮 × 机理链（论文正文骨架，"必要链"而非三个并列解释）**：

| 旋钮（输入，可控） | 观测（输出） | 机理链中的位置 |
|---|---|---|
| **K1 极化**（vibX 耦合 / vibZ 不耦合；srcX≡srcY） | 耦合开/关 | magnon 力在被驱动集体坐标上的**投影对称性** |
| **K2 频率 + 源几何**（驱动-响应窗口；点源→平面源红移） | 哪些窗口驱动、峰位 | 频率+源几何设定注入 magnon 的 **k 谱** → 决定 F(ω,k) 加载哪个散射通道（**window → scattering**） |
| **K3 传播轴 + 净漂移**（srcX→+z 横向；srcZ→−z 纵向；频率切换双向） | 漂移方向与偏转角 | Thiele 力平衡 (G+αD)·v = F：偏转由 **G/(αD)** 组织（**scattering → force**） |

摘要/标题用叙事方案的 **"three-knob control map"** 措辞（对宽口径编辑更易读）；正文用胜出方案的 **window→scattering→force 必要链** 作论证主体。

---

## 2. 三条线的证据现状（来自 4 份数据审计，全部可溯源）

### A 线（频率/本征模）— 详见 `06_eigenmode_frequency_mechanism/`
- **无任何已确认 Hopfion 线性本征频率（截至 2026-06-14）。** 这是硬红线。
- `173.66 GHz`：Bz ringdown table-average 主峰，但零场控制振幅与 1/5 mT 几乎相同（control/1mT = 1.0046，1→5 mT 指数 −0.0048）→ `quench_dominated=true`。**只能称"开放边界体系的边界淬火候选自由模"**。
- `79.14 GHz`：平衡态差分候选峰，峰位一致性好（离散 0.282 GHz）但**未通过**场强平方律（指数 −0.0635，R²=0.5323）和 SNR 门（2.64<3）→ `passed=false`。**只能称"未通过线性门的差分候选峰"**。
- 连续驱动窗口（srcX 200/1000、srcZ 100/1100 GHz）均未通过与 ringdown 峰的 10 GHz 对齐判据 → **一律称"驱动-响应窗口"**。
- 能量率审计：srcX 200 GHz 是最强正的背景校正能量率（39.812 nJ/s，R²=0.986）；srcZ 无稳健正吸收峰，100 GHz 最强绝对响应但斜率为负 → **srcZ 100 GHz = "最强绝对非平衡能量率响应，后瞬态斜率为负"，绝不写"净吸收峰"**。
- ⚠️ **决定性负结果证据（quench/linearity/topology 三个门的产物）目前只在未合并分支 `codex/hopfion-eigenmode-mechanism-20260612` 上**，master 树里没有。写任何负结果句之前必须先合并（见 WS-0）。

### B 线（源几何）— 详见 `04_frustrated_fm_foundation/.../spin_wave_dynamics/freq_sweep/`
- 峰位红移：srcX 1000→700 GHz，srcZ 1100→800 GHz（平面→点源）。**只比峰位与方向，绝不比幅度**（点源 500 T 单胞 vs 平面 1 T 面，能量注入不可比）。
- srcZ 点源方向分布复杂（raw **7 个 +z / 3 个 −z**；vault 旧记 6+z/3−z，需订正）；平面源仅 100 GHz 异常。
- 从未计算过 I(k,f)；数据现实：freq_sweep 存活 54 个 table.txt，plane_wave 零 OVF，point_source 仅 2 OVF + srcZ.7z；4 个峰值 run 的全场 OVF 封在 `ovf_archive.tar.zst`（可解包做 k 谱）。

### C 线（Thiele）— 详见 `07_thiele_theory_model/`
- 平动 G/D 张量已首算（`results_thiele_GD_translation_20260615/G_D_translation.json`）。反对称门 PASS，闭环平动回旋三分量全部低于 3% 噪声底（**与零一致**，支持"闭合环对称抵消"猜想）。
- **但 `delta=1 vs delta=2` 有限差分收敛门 FAIL**（G_XY ~80%，D 对角 ~19%）→ 零 G 结果**尚不可发布**，无霍尔角预言。根因很可能是纹理太小（R≈2.17nm、r≈1.64nm，0.5nm 网格 → 管子只有 ~6–7 胞宽），单胞 `np.roll` 差分过粗。修数值是全论文定量核心的前置门。
- 工具现实：生成器 `95_shared_scripts/create_hopfion_AFM_v2.py`（`afm=None`=纯 FM，无连续 twist 旋钮）；`hopfion_analysis.py` 已有 compute_hall_angle / extract_Rr_series / compute_Rr；`compute_hopf_index.py` 在 `04_frustrated_fm_foundation/20260105_frustrated_fm/`（复用，勿重导）。

---

## 3. 验证过的文献基础（引用前仍须 Zotero/BBT 核对，标注见下）

**方法学（A 线）**：Mochizuki 2012 PRL 108,017601（弱脉冲吸收谱）· McMichael & Stiles 2005 JAP 97,10J901（本征模/吸收法）· Baker et al. 2017 JMMM 421,428（micromagnetic 自旋波方法）· Kravchuk et al. 2018 PRB 97,064403（skyrmion 本征模/有效质量）· Garanin et al. 2020 PRB 102,064406（breathing 软化→坍塌）· Sobucki et al. 2022 APL Mater. 10,091116（Bloch hopfion magnon 谱）· Raftrey & Fischer 2021 PRL 127,257201（hopfion 场驱共振 + 空间局域判据）· Wang et al. 2021 PRL 127,037202（非线性边带/frequency comb）。

**散射/源几何（B 线）**：Iwasaki, Beekman & Nagaosa 2014 PRB 89,064412（magnon-skyrmion 散射）· Schütte & Garst 2014 PRB 90,094423（magnon-skyrmion 束缚态）· Zhang, Ezawa, Xiao et al. 2015 Nanotechnology 26,225701（自旋波驱动 skyrmion，峰≠本征频率）· Gruszecki et al. 2016 Sci. Rep. 6,22367（局域自旋波激发/波前）。

**Thiele/集体坐标（C 线）**：Thiele 1973 PRL 30,230（原始）· Wang, Qaiumzadeh & Brataas 2019 PRL 123,147203（电流驱动 hopfion）· Liu, Hou, Han & Zang 2020 PRL 124,127204（Erratum PRL 125,159901；hopfion 动力学，G/D 前因子来源）· Popadiuk, Kravchuk et al. 2023 pss(RRL) 17,2300131· Guslienko 2024 Magnetism 4,383（集体坐标综述）。

**Hopfion 实验/背景**：Zheng et al. 2023 Nature 623,718 · Khodzhaev & Turgut 2022 JPCM 34,225805 · Arora, Kumar & Das 2025 APL Mater. 13,041109 · Tejo & Otxoa 2025 arXiv（hopfion breathing，追踪 R/r/Q_H）。

> **[待核实 PDF] 硬约束**：Hopfion 平动回旋矢量"消失(Wang 2019) vs 非零(Liu 2020/Popadiuk 2023)"的**具体归属**必须先读 `wang2019.pdf`（仓库根，untracked）+ Liu 2020 全文核对作者/公式/符号后才能写；**在核对前只能说"本项目内这是开放问题"，不得写成已成定论的文献之争**（防 Zheng-2023-误标-Liu-2018 型错误重演）。所有上表 DOI 已由文献 agent 核到，但引用进正文句子前仍须 Zotero 逐条确认。

---

## 4. 工作流：四个工作块 + 决策门

> **成本分层**：零仿真（本周即可做，主力）→ 廉价仿真 <2 GB（A/B 设备，新加坡 23:00–03:00 静默窗，仅在门触发时跑）→ 18 GB 全场 mode map（**门控关闭**，除非 A 线出现通过线性门的模式）。D: 盘将满，重仿真一律放 WSL home。

### WS-0 诚信与可溯源（PRIORITY 0，阻塞一切论文写作，零仿真）
- **T0.1 合并负结果分支**：把 `codex/hopfion-eigenmode-mechanism-20260612` cherry-pick/merge 进 master，使以下**真实文件名**在 master 可解析（❗旧提案误引 `open_boundary_topology_audit.json`，实际不存在）：
  - `hopfion_eigenmode_mechanism_20260612/results/clean_linearity_gate.json`（79.14 GHz，passed=false）
  - `.../results/control_quench_audit.json`（173.66 GHz，quench 比 1.0046）
  - `.../results/equilibrated_topology_check.json`（Hopf 相对变化 2.51e-9）
  - `.../notes/evidence_status_20260612.md`、`.../notes/boundary_quench_audit.md`
  - **GATE G0**：四组产物在 master 可读且数值与 progress.md 一致（2.51e-9 / 1.0046 / passed=false）。**FAIL → 在解析前不得写任何负结果句。** 冲突则逐文件 cherry-pick，勿改写历史。Owner: Claude。
- **T0.2 订正陈旧负债**：srcZ 方向计数 raw 7+z/3−z vs vault 6+z/3−z（改 vault `decisions/point-vs-plane-source.md` 为 raw）；标注 `amplitude_sweep/point_source/README.md` 里过时的"440 GHz 已知共振频率"；标注已推翻的 v∝B^1.99。Owner: Claude。
- **T0.3 claim ledger**：把现有 14 行 Thiele 证据表扩到 A/B/C 每一句意图句 → 数据文件 → 证据等级。Owner: Claude。Dep: T0.1。

### WS-A 频率响应 = 散射而非本征模（PRIORITY 1，零仿真优先）
- **TA.1（零仿真）高灵敏重分析**：对 ringdown + C2 表做 multitaper/Welch PSD、m_x–m_y 交叉谱（手性）、以及从 `deformation_timeseries.csv` 提取集体坐标（质心、RMS 宽度）做 FFT，替代原始 table-average m_z。扩展 `analyze_ringdown.py`。Owner: Codex 写 / Claude 审。
  - **GATE GA1**：79.14 GHz 是否在重分析后 **同时** SNR≥3 且幂律指数 ∈[1.5,2.5]？**PASS → 才可称"candidate internal mode"（仍非 eigenfrequency）**，喂给 C 线；**FAIL → 保持强制措辞 "failed the field²+SNR gate (passed=false)"**，A 线写成有门纪律的负结果 + 散射框架。
- **TA.2（零仿真）非线性边带/frequency-comb 检查**（Wang 2021）：对现有连续驱动 table.txt FFT，看驱动线附近等间距边带。
  - **GATE GA2**：等间距边带存在？PASS → 间距=非线性区间接内部模频率（标注非线性）；FAIL → 强化纯驱动-响应框架（仍可发）。
- **TA.3（廉价仿真 <2 GB，条件触发）Mochizuki-2012 差分吸收谱**：平衡态开放边界上单宽带 sinc @ 1/5/10 mT + 零场控制，table-only，复用 20260612 分支 `clean_Bz_*mT_05ns.mx3`。仅当 TA.1 留下 SNR 2–3 的模糊地带才跑。
  - **GATE GA3**：差分峰现在过 B²+SNR≥3？PASS → 确认候选模；FAIL → 定论负结果 "0–1200 GHz 无线性吸收模"，作 Limitations 护盾。

### WS-B 源几何 = k 谱（PRIORITY 1，零仿真优先）
- **TB.1（零仿真）现有 OVF 的 k 谱**：解包 4 个峰值 run 的 `ovf_archive.tar.zst`（plane srcX 1000 / point srcX 700 / plane srcZ 1100 / point srcZ 800），做空间 FFT |m_k| 快照，比较 k 谱**形状**（各自归一，绝不比幅度）。
  - **GATE GB1**：点源 k 谱是否在匹配 f 下明显更宽？PASS → 红移机理在现有数据上成立；FAIL → 红移写成"源几何相关的窗口移动，机理[未确认]"，升级 TB.2。
- **TB.2（廉价仿真 <2 GB，条件触发）纯源 I(k,f) 控制**：2 个无 Hopfion 均匀背景 run（plane 1 T 面 / point 500 T 胞），同 100³，0.5 ns，记录一个平面上的 m，2D+时间 FFT → 各自归一的注入 I(k)。
  - **GATE GB2**：注入点源 k 明显宽于平面？PASS → 单实验机理证明；FAIL → 红移归于源-Hopfion 几何，仍作现象报告。
- **TB.3（零仿真）能量归一响应**：用现有表按注入 dE(t) 归一 |dr|（**替代被禁的 500T-vs-1T 幅度比较**）。图注必须写"仅位置与方向；跨源幅度不可比"。

### WS-C Thiele G/D — 验证或转向（PRIORITY 1，审稿人 O3）
- **TC.1（零仿真）收敛阶梯**（嫁接自理论方案）：Richardson δ 阶梯（δ=1,2,3,4）+ 4 阶差分 stencil + 谱(FFT)导数 + 2×/4× 超采样。所有小 G 变化相对自然尺度 S 表达，要求零判定在每个 δ 都成立。
  - **GATE GC1（全论文枢纽）**：{4 阶 FD, Richardson, 谱导数, 2×超采样} 是否互相 5% 内一致？**PASS → 释放收敛后的 G/D**；FAIL → TC.2。
- **TC.2（廉价仿真 <2 GB，条件触发）细网格重弛豫**：仅当 GC1 FAIL。200³ @ 0.25 nm，初态=插值 m000020，J2/J4 **逐字抄** `R8r4_Ku0.mx3`（项目坑）；**先重审细网格离散哈密顿量**[未核实]。
  - **GATE GC2**：细网格张量收敛？PASS → 释放；FAIL → 带 TC.3 离散误差棒作**有界估计**上报，不声称精确值。
- **TC.3（零仿真）匹配分辨率 skyrmion 再标定**：skyrmion 核 ~3 胞（匹配 Hopfion 管 ~3.4 胞半径），扫分辨率，产出 computed-vs-analytic G 误差 vs cells-per-core 曲线 = 可迁移的**离散偏置误差棒**。⚠️ 现有 0.17% 标定用 401×401 过分辨 skyrmion，**不能**用来 bound Hopfion 张量精度；且此曲线只作积分器标定，**绝不把 skyrmion G=4πQ·Ms/γ 迁移给 Hopfion**（C4 硬禁）。
- **TC.4（零仿真）实测偏转角**：从 `deformation_timeseries.csv` + 轨迹提取（先修 codex prompt C-2 里的陈旧路径）。**这是 C 线预言必须面对的数字。**
- **TC.5（零仿真）膨胀块 {R,r} G/D + 坍塌 Q_H(t)**：扩展 `hopfion_analysis.py` 加 hopf_index（复用 `compute_hopf_index.py`），解包 freq_switch v3 档追踪 R/r/Q_H 过 t≈0.91 ns 坍塌。
- **GATE GC-FINAL（GC1/GC2 通过后 + TC.4）**：收敛后的平动 G 是否与零一致？
  - **PASS-零 → 头条 = "Hopfion 平动无刚体回旋耦合：近零霍尔漂移，异于 2D skyrmion"**（预言 θ_H≈0，对比 TC.4 实测角）。⚠️ **此头条严格门控在 GC1/GC2 PASS 之后**；在收敛一致（5%）证明前，G 只能写"consistent with zero at the noise floor, convergence [unconfirmed]"，**不得**下头条（防 R2 造假风险）。
  - **PASS-非零 → 头条 = θ_H = atan(G/(αD)) 预言 vs 实测**。
  - 两分支都能发表。

---

## 5. 图表规划（主文 6–8 图，每图标数据源）

- **F1 概念图**：Hopfion 纹理 + 点/平面源几何 + window→scattering→force 逻辑链。源：`m000020.ovf` 渲染 + 手绘。
- **F2 频率响应窗口≠本征模**：驱动-响应峰位（srcX 200/1000、srcZ 100/1100）叠 ringdown 谱，标注 10 GHz 不对齐；插图=quench 控制（173.66 GHz 比 1.0046）。源：ringdown results + `control_quench_audit.json`。
- **F3 负线性门诚信面板**：79.14 GHz 峰位一致(0.282 GHz) PASS vs 幂律 R²=0.53/SNR 2.64 FAIL。源：`clean_linearity_gate.json` + TA.1。**诚信中心图**。
- **F4 峰位红移**：srcX 1000→700、srcZ 1100→800（仅位置/方向，幅度归一）。源：motion summaries + TB.3。图注写"跨源幅度不可比"。
- **F5 k 谱机理**：点 vs 平面归一 |m_k|（TB.1）和/或纯源 I(k)（TB.2）。
- **F6 Thiele G/D 收敛**：Richardson δ 阶梯 + 4 阶/谱一致 + skyrmion 偏置曲线(TC.3)作误差模型。源：TC.1+TC.3+`G_D_translation.json`。
- **F7 预言 vs 实测漂移/霍尔角**：θ_H（近零或 atan(G/αD)）vs 实测轨迹角。源：TC.4 + GC-FINAL。**可证伪的收官图**。
- **F8（条件）坍塌与拓扑**：Q_H(t)、R/r(t) 过 freq_switch v3 ~0.91 ns 坍塌，框成超阈非线性 breathing（Garanin 2020）。仅高层级期刊收入。

**最小可发版（零仿真地板）**：F1+F3+F4+F6+F7 即构成一篇纯零仿真论文。

---

## 6. 分工

- **Claude Code（分析/编排/诚信）**：独占 WS-0（git 合并 T0.1、订正 T0.2、claim ledger T0.3）；审所有 Codex 数值——尤其 TC.1 收敛数学（论文枢纽）与每个门判定；跑决策门路由；按 ledger 起草论文各节。
- **Codex（批处理脚本）**：写/扩分析码——TA.1 multitaper+交叉谱、TA.2 边带 FFT、TB.1 OVF k-FFT、TB.3 能量归一、TC.1 收敛阶梯+4阶+谱导数、TC.3 skyrmion 再标定、TC.4 霍尔角/轨迹、TC.5 膨胀 G/D + hopf_index 扩库；备好所有廉价仿真的 mx3 + 配套分析。**每个 Codex prompt 内嵌 must-not-say 清单，且路径用编号前缀新目录（04_/06_/07_）。**
- **用户（A/B 设备手动仿真 + 决策）**：跑三个条件廉价仿真（TA.3 差分吸收、TB.2 纯源 I(k,f)、TC.2 细网格重弛豫）于新加坡 23:00–03:00 静默窗、WSL home / B 设备；在 GC-FINAL + TC.4 落地后定期刊层级；对最终 G-零/非零头条分支做物理签字。

---

## 7. 决策规则 / 分支路由（每个分支都可发表）

**期刊层级规则（打破"层级待定"循环）**：**层级在 GC-FINAL + TC.4 落地后立即决定**，并**门控所有 Phase-1 廉价仿真花费**。高层级（PRL/PRB-Rapid）仅当 GC1 PASS 且拿到干净的 skyrmion-对比或有限霍尔角头条；否则中层级（PRB/JMMM/AIP Advances）记录"三旋钮控制图"。

**Fallback（无分支能杀死论文，只定层级）**：① A 全负 → "预注册门搜 0–1200 GHz 无线性本征模，驱动窗口即散射窗口"（负结果+门纪律本身是贡献+护盾）；② B 机理双失 → 红移作稳健源几何现象，机理标[未确认]；③ C 收敛永不过 → 带离散误差棒的**有界** G/D，作"首个带量化数值不确定度的 frustrated-FM Hopfion 静态 Thiele 张量"，推迟精确霍尔角；④ 最佳（GC-FINAL PASS-零）→ 近零霍尔作 skyrmion 对比头条。**论文的单元是 reconciled mechanism story（window→scattering→force），任一线负也成立。**

---

## 8. 诚信红线 + must-not-say（受全局 ACADEMIC INTEGRITY 硬约束）

| 绝不说 | 安全替换 |
|---|---|
| "200/1000/1100 GHz 是本征频率/共振模式" | "驱动-响应/传输窗口" |
| "173.66 GHz 是本征模" | "开放边界候选自由模，quench_dominated=true" |
| "79.14 GHz 是本征模" | "未过场²幂律+SNR 门的差分候选峰，passed=false"（除非 TA.1 出现真 PASS 才升"candidate internal mode"，仍非 eigenfrequency） |
| "srcZ 100 GHz 净吸收峰" | "最强绝对非平衡能量率响应，后瞬态斜率为负" |
| "点源比平面源更高效/耦合更强" | 只比峰位与方向；幅度经 TB.3 按注入能量归一后才可对比 |
| "Thiele 方程定量复现轨迹" | "广义集体坐标框架解读运动；一个无参数偏转角预言对仿真检验" |
| "Hopfion 平动 G=4πQ_H ẑ" | C4 禁；必须计算 |
| "v∝B^1.99" | 完全省略，直到宽幅扫描重做 |
| 零 G / 近零霍尔头条（收敛门未过时） | "consistent with zero at noise floor, convergence [unconfirmed]" |
| Wang2019 消失 vs Liu2020/Popadiuk2023 非零（读 PDF 前） | "本项目内开放问题，待原文核实" |

**诚信守门 punch-list（写作时逐条执行，均来自 workflow 守门 agent）**：
1. T0.1/G0 与所有图/ledger 引用改用**真实文件名**（`equilibrated_topology_check.json` 而非虚构的 `open_boundary_topology_audit.json`）。
2. 零 G / 近零霍尔头条严格门控在 GC1 或 GC2 PASS 之后。
3. Wang 2019 / Liu 2020 / Popadiuk 2023 的回旋矢量归属标 [待核实 PDF]，读 `wang2019.pdf` + Liu 全文后方可写。
4. 79.14 GHz 的 "candidate internal mode" 标签严格条件于 TA.1 出现文档化 PASS。
5. skyrmion G=4πQ 只作积分器标定，明确 0.17% 不 bound Hopfion 精度；Hopfion G 必须计算。
6. 每次重述保留限定词（quench_dominated / passed=false / 斜率为负 / 驱动-响应窗口）。
7. TB.3 是唯一"幅度相邻"比较，且只经每注入能量归一；F4/F5 图注明确跨源幅度不可比。
8. Iwasaki 2014 / Schütte 2014 / Gruszecki 2016 等在写进句子前逐条 Zotero/BBT 核对 DOI（DOI 已初核，见 §3）。

---

## 9. 证据等级总表

| # | 主张 | 等级 | 措辞/依赖 |
|---|---|---|---|
| 1 | 平动 G/D 3×3 块数值 | 已确认（收敛门通过后） | TC.1；先过 skyrmion 匹配分辨率标定 |
| 2 | 平动 G 是否≈0（闭环抵消） | 已确认（收敛门通过后） | TC.1；相对噪声底报，非字面 0 |
| 3 | srcX 霍尔角 θ=atan(G/αD) 或 ≈0 预言 | 强支持（前向、无自由参数） | GC-FINAL；\|F\| 无关 |
| 4 | 实测 srcX 漂移/偏转角 | 已确认 | TC.4 |
| 5 | (3)vs(4) 裁决 | 强支持（裁决即结果） | GC-FINAL 双分支 |
| 6 | 极化选择性 vibX/vibZ；srcX≡srcY | 已确认 | 直陈 |
| 7 | 多窗口频率选择性 + 死区 | 已确认 | "驱动-响应窗口" |
| 8 | 173.66 GHz | 候选自由模 | quench_dominated=true |
| 9 | 79.14 GHz | 负结果（除非 TA.1 PASS） | passed=false |
| 10 | 频率窗口=散射（非本征模） | 强支持 | TA.1/TA.2 + Iwasaki/Zhang 散射框架 |
| 11 | 点/平面峰位红移 | 强支持（峰位/方向） | 仅峰位与方向 |
| 12 | 红移=点源宽 k 谱 | 候选→强支持 | GB1/GB2 |
| 13 | 膨胀块 G/D + 坍塌 Q_H(t) | 已确认（算出后）/强支持 | TC.5；Garanin 2020 框架 |
| 14 | 强驱坍塌 t≈0.91 ns | 强支持 | 含 Q_H(t)、R/r(t)；不赋普适阈 |

---

## 10. 本周可立即启动的零仿真核心（无仿真、无额度风险）

按依赖顺序，全部零仿真、可交 Codex：
1. **T0.1** 合并 20260612 分支（Claude，git）→ 解锁一切负结果引用。
2. **TC.1** G/D 收敛阶梯（论文枢纽）→ 决定 C 线成败。
3. **TC.4** 实测偏转角 → C 线预言的靶子。
4. **TB.1** 4 个峰值 OVF 的 k 谱 → B 线机理（现有档案即可，168 个 `ovf_archive.tar.zst` 已确认存在）。
5. **TA.1** ringdown/C2 高灵敏重分析 + **TA.2** 边带检查 → A 线散射定性。
6. **TB.3** 能量归一响应 + **TC.3** skyrmion 再标定误差棒。

其余廉价仿真（TA.3/TB.2/TC.2）全部推到各自门后，18 GB 全场 map 保持门控关闭。

---

## 附：相关文件
- 旧规划（本版取代，Thiele 细节仍可参考）：`07_thiele_theory_model/hopfion_thiele_research_plan_20260615/RESEARCH_PLAN.md`
- A/B/C 早期理论调研：`09_paper_thesis_talks/hopfion_spinwave_paper_theory_guidance_20260608/`
- 物理进度 canonical：vault `Hopfion-Physics/progress.md`
- 规划 workflow 全量产物（本文件的证据来源）：`99_scratch_outputs/master_plan_workflow_distilled.md`
- 共享脚本：`95_shared_scripts/hopfion_analysis.py`、`create_hopfion_AFM_v2.py`
