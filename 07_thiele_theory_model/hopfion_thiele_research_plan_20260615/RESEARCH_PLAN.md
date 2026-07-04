# Hopfion 自旋波驱动论文 — Thiele 理论收口研究框架

> ⚠️ **SUPERSEDED（2026-07-03）**：本文件只操作化了 C（Thiele）线。已被覆盖三线（A 频率 / B 源几何 / C Thiele）的项目总指导取代：
> **`00_project_index/hopfion_spinwave_paper_master_plan_20260703.md`**。
> 本文件的 Thiele 数值细节（§2 概念方程、Tier 0 收敛闸、§2.3 闭环零判定、§4 证据等级/must-not-say）仍被新规划引用，保留作参考；执行以新规划为准。
>
> 生成：2026-06-15（superpower planning workflow，4 视角 + 综合 LEAD，5 agents）
> 状态：**已存档，执行未开始，等待用户细看**
> 关联：`hopfion_spinwave_paper_theory_guidance_20260608.md`（A/B/C 理论调研）、vault `Hopfion-Physics/progress.md`（物理进度，canonical）、bd `Hopfion-rt4` 等

## 决策记录（2026-06-15，用户拍板）

- **执行起点**：先存档全套方案，用户细看后再执行（本次不启动任何分析 / 仿真）。
- **首篇 Thiele 范围**：平动块 `{X,Y,Z}` + 膨胀块 `{R,r}`；**twist/helicity (Φ) 列为 future work**。
  - 影响：§2.1 选项 (a)「给生成器加全局相位旋钮」**推迟**；Tier 3 的 twist 耦合 `G_{Z,Φ}` 首篇**不做**；Prompt C-3 中 `poloidal_phase` 仅作**坍缩诊断量**（不作为集体坐标进入 G/D）。
- **Phase 1 振幅扫描 (S1)**：**暂缓**，等 Phase 0 看完再决定。
- **目标期刊层级**：暂不定，先做出 Phase 0/1 结果再定（决定是否需要 Phase 2 昂贵仿真）。

> 已核实的工具现实（agents 实地读仓库纠正）：`create_hopfion.py` 不存在，实为 `create_hopfion_AFM_v2.py`（`afm=None` 即纯 FM 纹理，无连续 twist 旋钮）；`compute_hall_angle` 共享库已有；`m000020.ovf` 与 freq_switch OVF 均封装在 `ovf_archive.tar.zst` 内需解包；大部分驱动仿真只剩 `table.txt`，仅 freq_switch v3/v2/z_bidir 留全场 OVF，mode_map 留 `deformation_timeseries.csv`；边界条件分叉（示例脚本吸收层无 PBC vs 标称 PBC(1,1,1)）。

---

## 1. 一句话主线 + 三旋钮×三为什么骨架

### 主线（送审用，一句话）
> 自旋波驱动一个三维阻挫铁磁 Hopfion 的运动，可通过**频率、源几何、激励极化**三个旋钮选择性调控；其运动——尤其是横向的类霍尔偏转——由一个广义集体坐标（Thiele）力平衡组织，而该力平衡的回旋/耗散结构张量可**直接从静态纹理计算**，给出一个**与力大小 |F| 无关、无自由参数的偏转角预言**作为可证伪检验。

冲突解决（叙事 vs 原始骨架）：采纳叙事视角的修正——把原「驱动方向」旋钮拆开。原骨架把「输入极化选择性」与「输出运动方向」混为一谈，掩盖了论文最强结果（横向运动）。三旋钮重命名为**输入可控量**，三个「为什么」统一锚定到**同一个** Thiele 力平衡（而非三个并列的手挥解释）。

### 三旋钮 × 三为什么（统一骨架）

| 旋钮（输入，可控） | 观测（输出） | 唯一的「为什么」（同一框架的三个探针） |
|---|---|---|
| **K1 激励极化**（vibX 耦合 / vibZ 不耦合；srcX≡srcY） | 耦合 开/关 | 磁振子力在 Hopfion 集体坐标上的**投影对称性**：vibZ 不与任何被驱动坐标交叠 → 力为零 |
| **K2 频率**（驱动-响应窗口；点源→面源红移） | 哪些窗口驱动、强度 | 频率设定磁振子 k 谱 → 决定 F(ω,k) 加载哪个散射/耦合通道；源几何重塑同一 I(k,f) |
| **K3 传播轴**（srcX 面内 / srcZ 轴向） | 横向 +z vs 纵向 −z；频率切换双向 | Thiele 力平衡 (G+αD)·v=F：**偏转角仅由 G/(αD) 决定，与 |F| 无关** —— 唯一定量可测的理论预言 |

**备用主线**（若霍尔角检验不匹配，预先准备）：横向偏转**不能**单由平动回旋耦合复现 → 内部（呼吸/膨胀）模式或各向异性磁振子力是 Hopfion 自旋波输运的本质 —— 这本身是区分 Hopfion 与 2D skyrmion 的结构性结果。两种结局都可发表，这正是框架的强度。

---

## 2. 理论框架（Thiele / 集体坐标骨架）

### 2.0 概念方程（论文里照此写，是概念方程不是已解析求解的模型）
```
(G_ab + α D_ab) q̇_b = F_a^mag(ω,k,pol,source) + F_a^edge + F_a^int
q = {X, Y, Z, R_ring, r_tube, Φ_tor, Φ_pol}
G_ab = (Ms/γ) ∫ m·(∂_a m × ∂_b m) dV     (反对称, 回旋)
D_ab = (α Ms/γ) ∫ (∂_a m · ∂_b m) dV       (对称, 耗散)
```
**核心可解性洞见**：G_ab、D_ab 是**静态纹理的纯几何性质**，不需要任何动力学仿真，今天即可算。只有 F 难。整个前向预言价值来自——**偏转角只依赖 G 与 D**（廉价、可算的部分）。

### 2.1 计算什么、按什么顺序、每个结果意味着什么

**Tier 0 — 静态纹理族 + 导数算子（一切前置）**

- **G/D 必须在真实驱动 Hopfion 的 R,r 上算**，不是生成器默认（默认 R=12 r=6；驱动平衡态 R≈8 r≈4）。先对 `m000020.ovf`（需从 `ovf_archive.tar.zst` 解包）跑 `compute_Rr` 取真实 R,r，再喂进纹理族。
- **平动块 {X,Y,Z} 无需任何解析构造器**：∂m/∂q 就是真实纹理的刚性空间平移（对真实 OVF 做 np.roll 移格，PBC 一致）。这绕开了「生成器构造是否正确」的地雷，是最稳的路径。
- **仅内部坐标 {R,r}（twist 已推迟）需要生成器**：`generate_hopfion_ovf(..., afm=None)` 给纯 FM 纹理。但**必须**验证生成的纹理复现真实 R,r 与 Q_H=1（数值 Hopf 积分），否则 G/D 建在错误静态态上。
- ~~twist 旋钮~~：**首篇推迟（决策记录）**。生成器无连续 Φ 旋钮；twist 耦合列 future work。

有限差分 + 切向投影（必须）：中心差分 `∂_a m ≈ (m(q+δ)−m(q−δ))/(2δ)`；逐胞归一 |m|=1；**切向投影** `∂_a m −= (∂_a m·m)m`（否则 D 对角线混入伪径向贡献）。δ_X=0.5–1.0 nm，δ_R/δ_r=0.5–1 nm。

**Tier 0 收敛/正确性闸（必过，否则整个霍尔角预言静默崩坏）**：
1. **独立标定**：先在 2D skyrmion 纹理上验证积分器复现教科书值 `G=4πQ·Ms/γ`（含符号）。这是最重要的验证步。
2. 对称性自洽闸：数值上 G_ab=−G_ba（反对称）、D_ab=D_ba（对称）必须成立。
3. δ 减半 → G,D 变化 <5%。
4. `alpha` **从 `.mx3` 提取并报告**，不假设。
5. 排除 5 胞吸收边界壳层（与分析库 `exclude_boundary=5` 一致）。

**Tier 1 — 平动 3×3 块 G_trans, D_trans（最先做；最高价值最低风险）**
- D 对角 D_XX≈D_YY≠D_ZZ（环在平面内）设各轴拖曳；G 反对称 3 独立项 G_XY,G_XZ,G_YZ 是能产生横向运动的分量。
- **物理判定**：G_XZ≠0 → srcX 沿 x 的力产生沿 z 速度 = 观测 srcX→+z 横向运动的候选来源（无需各向异性力）。G_XZ≈0 → 横向运动**不能**来自平动回旋耦合，必须来自 F 本身或内部模式（=闭环开放问题，§2.3）。

**Tier 2 — 平动↔膨胀交叉块（第二）**
- G_{Z,R}, G_{Z,r}, D_{Z,R}, D_{Z,r} 及 X/Y 类比。非零 → srcZ 轴向驱动如何同时驱动平动与形变 → 直接关联 1100 GHz 坍缩（形变失控）与 srcZ-100GHz 反转。连接 Thiele 与呼吸模式叙事。

**Tier 3 — 膨胀 2×2 块（第三；twist 耦合已推迟）**
- D_{R,R}, D_{r,r}, D_{R,r}, G_{R,r}。**不得**由此声称呼吸本征频率（诚信地雷——无确认本征频率）；至多报耗散膨胀拖曳。
- ~~twist 耦合 G_{Z,Φ}, G_{R,Φ}~~：首篇 future work。

**作用域外但点名：F^int 与能量 Hessian** —— F^int=−∂E/∂q 是**微磁能量**量（非几何积分）。需在阻挫-FM 能量上算 E(R),E(r) 有限差分。**J2/J4 系数符号必须逐字抄自 `R8r4_Ku0.mx3`，绝不重导**（项目坑 `J2J4-coefficient-sign`）。解析纹理非离散哈密顿量能量极小，故只作**定性刚度符号**，标 [保持定性]。

### 2.2 前向霍尔角预言（与 |F| 无关 —— 全计划最高价值前向检验）

稳态漂移下 `(G+αD)v=F`。在 **F 大致沿传播轴**（caveat）假设下，`v=M⁻¹F`，预测偏转角
```
θ_H^pred = atan2( |(M⁻¹)_⊥,∥| , |(M⁻¹)_∥,∥| )    —— |F| 在比值中消去
srcX 二坐标约化（drive∥x, 横向∥z, 小α）: θ_H^pred ≈ atan( G_xz / (α D_xx) )
```
即偏转仅由无量纲比 **G_xz/(α·D_xx)** 决定。

**对比对象（已存在的实测）**：`freq_sweep/analyze_hall_angle.py` 调 `compute_hall_angle(traj, sw_propagation_axis='x')`，对 02ns/05ns 数据出每频点 `theta_H_deg`，validity 闸 `d_total>0.1 nm`。用 `valid==True`、晚时（`skip_fraction=0.33`）、**相位关联轨迹**的角，比对强耦合窗口（100–200, 1000 GHz）的**平台值**。

**匹配/不匹配判定树（每个结局都是结果）**：
- **匹配**：强支持横向 srcX→+z 是**刚体拓扑回旋耦合**，F 基本沿传播，内部模式是旁观者 → 论文核心定量主张。
- **不匹配但实测角仍频率无关**：刚体 M 结构对但 F 不沿传播（各向异性磁振子力有横向分量）→ 亦可发表，激励 F 散射路线。
- **不匹配且实测角强频率依赖**（srcZ-100GHz 变号）：刚体 Thiele 不足，**内部模式参与** → 路由 Tier 2/3 交叉块 + A 线模式图。双向控制 = 模式选择性，亦是结果。

**必声明 caveat**：预言假设 F∥传播。srcX 是干净检验；srcZ 是故意的压力测试（θ≈0/180，可观测是 ±z 符号；100 GHz 反转是内部模式参与的诊断）。

### 2.3 闭环回旋耦合开放问题（论文智力核心）

Hopfion 是闭合环，平动回旋矢量 G 可能因环两侧对称抵消而趋零（不同于 2D skyrmion 的稳健 `G=4πQẑ`）。**必须计算，不得假设**（C4 明令禁止套用 skyrmion `Gẑ` 形式）。

测试是否为零：(1) Tier 1 算全 3×3 G_trans；(2) 相对自然尺度 `(Ms/γ)·⟨|∂m|²⟩·V` 报量级——「零」=低于 D 尺度几个 % 的噪声地板；(3) 鲁棒闸：变 δ、变积分域、在平衡吸引域内变 R,r —— 真对称零守在地板，近抵消的有限值会漂移。

**判定树**：
- **G_XZ,G_YZ 有限**：纯 Thiele 刚体耦合可解释 srcX→+z → 进 §2.2 前向霍尔角作为头条定量结果。
- **G_XZ≈0**：横向运动非刚体回旋。两存活解释：(a) F 本征各向异性；(b) 内部模式经 Tier 2 交叉块中介。用 A 线模式图区分。
- **整个 G_trans≈0**：平动非回旋/过阻尼，方向选择全来自 F 各向异性，偏转由 D 各向异性比 D_⊥/D_∥ 设定 —— 仍是干净可算故事，且与 skyrmion 物理迥异（卖点）。

### 2.4 逆向 F_eff 提取（如何保持非循环）

`F_eff ≡ (G+αD)·v_measured`。**如直接用 F_eff「解释」同一个 v 是循环**。三条独立逃逸（用 ≥2）：
1. **在未用于提取的轴上预言**：在 (f₀,B₀) 提 F_eff，在不同 (f,B,source) 独立预言并对**未使用的** v 检验。若 F_eff∝B² 在固定 f 成立，是对未用速度的可证伪预言。
2. **霍尔角检验是干净非循环内核**：θ_H 仅依赖 G,D（从静态纹理算，从不碰轨迹）→预言→比实测轨迹角，两套不相交数据源。
3. **变结构而非只变驱动**：比两个不同 R/r 的 Hopfion，G/(αD) 以可算方式变 → 预言不同 θ_H。

**禁区**：不得把 F_eff 简称「磁振子力」，称「平动投影有效力」。点源/面源 F_eff **量级绝不互比**。

---

## 3. 分阶段执行计划

> **数据现实**：几乎所有驱动仿真**未保留 OVF 时序**（只剩 `table.txt`）。幸存全场 OVF 仅 freq_switch v3/v2/z_bidir 的 `ovf_archive.tar.zst`（含坍缩）。模式图 OVF 已删但 `deformation_timeseries.csv` 保留了 srcX 200/1000、srcZ 100/1100 的逐帧质心+形变 RMS。
> **边界条件分叉**：示例/控制脚本用吸收层+无 PBC（alpha=100，6 面）；标称系统 PBC(1,1,1)。G/D 结构积分在周期静态纹理上算，驱动动力学在吸收边界盒里。论文中保持分离。

### Phase 0 — 现有数据零仿真（无 mumax；先做）

| 任务 | 输入 | 输出 | 谁做 | 依赖 |
|---|---|---|---|---|
| **P0-A 轨迹纵/横分解** | `06_eigenmode_frequency_mechanism/hopfion_mode_map_20260608/results/deformation_timeseries.csv` + `motion_mode_summary.txt` | (v_long, v_trans, θ) per (source,freq)，用 `compute_hall_angle` | Codex | — |
| **P0-C G/D 静态结构积分（最高 payoff）** | 解包 `m000020.ovf`→`compute_Rr` 取真 R,r；平动块=刚性移格真实纹理；内部块=`generate_hopfion_ovf(afm=None)` | 数值 G_ab,D_ab + θ_H^pred + 闭环零判定 | Codex（理论 Claude 审） | 需先解包 |
| **P0-D 逆向 F_eff** | P0-C 张量 + P0-A 速度 | F_eff(f,B,source) | Codex | P0-A,P0-C |
| **P0-E 能量/磁化标量诊断** | 各 `table.txt` + `resonance_analysis` | 后瞬态 dE/dt、磁化响应 per (f,source) | Codex | — |
| **P0-B R/r + 坍缩轨迹** | 解包 freq_switch_v3/v2/z_bidir 的 OVF 档→`extract_Rr_series`、相位关联质心、Q_H(t) | R/r/core vs t，含 t≈0.91 ns 坍缩 + Q_H(t) | Codex（需给库加 hopf_index(t)；poloidal_phase 仅诊断） | 需解包 + 加库函数 |

**解包须知**：解包到 `/tmp` scratch（只读派生），**绝不写入 repo 树**。
**Phase 0 交付**：核心理论图（G/(αD)→预测偏转角 vs 实测角）+ 坍缩形变轨迹 + Q_H(t)。零 GPU。

### Phase 1 — 廉价定向仿真（**已决策暂缓，待 Phase 0 后定**）

| 任务 | 设计 | 成本 | payoff |
|---|---|---|---|
| **S1 宽幅振幅扫描** | plane srcX，单频 **200 GHz**，B=0.01…10 T（3 量级 10 点），0.5 ns，table 1 ps，OVF 仅 50 ps（11 帧） | ~1.3 GB | 干净 v∝B? 律、坍缩阈 B*、F_eff(B)，关闭 progress 主线项 5 |
| **S1 控制** | 1× 无 Hopfion + 1× B=0 基线 + 1× 拓扑平庸纹理同驱动 | 含上 | 唯有此 srcX→+z 才能归因 Q_H |

约束：尊重 Singapore 时间 **23:00–03:00 静默窗**。

### Phase 2 — 昂贵仿真（需用户决策；**期刊层级未定前不启动**）

| 任务 | 设计 | 成本 | 何时才做 |
|---|---|---|---|
| **S2 k 谱 I(k,f)，面 vs 点** | 同频两 run 载波分辨 OVF + 无-Hopfion 控制 | ~12 GB | 仅当 Phase0 霍尔角不足解释实测角 |
| **S3 高时间分辨空间模式图** | srcX 200/1000、srcZ 100/1100 | ~18 GB/run（~70 GB） | 仅当审稿要求模式图、且 srcZ-100GHz 机制必须由模式图关闭 |

### Phase 3 — 理论收口 + 写作
- 核心图组 F7（G/D 块+闭环零）、F8（霍尔角预言 vs 实测）、F9（F_eff(f,B,source)）。
- §S6 理论 + §S8 局限（把否定闸**写进论文作护盾**）。
- 系数来源/单位/约定**审计表**；全部 DOI **Zotero 核验**后方可引用。

---

## 4. 证据等级总表

| # | 主张 | 等级 | 必需措辞/依赖 |
|---|---|---|---|
| 1 | G_trans,D_trans 3×3 块数值 | **已确认（算出后）** | Tier1；真实驱动 R,r；前因子/符号抄 Liu 2020；先过 skyrmion 标定闸 |
| 2 | 平动 G_XZ/G_YZ 是否≈0（闭环抵消） | **已确认（算出后）** | §2.3 纯几何；对噪声地板报，非字面 0 |
| 3 | 预测 srcX 霍尔角 θ=atan(G_xz/(αD_xx)) | **强支持（前向、无自由参数）** | §2.2；|F| 无关 |
| 4 | 实测 srcX θ_H(f) 强窗平台 | **已确认** | 已由 `analyze_hall_angle.py` 算 |
| 5 | (3)vs(4) 裁决 | **强支持（裁决本身即结果）** | 判定树 §2.2/2.3 |
| 6 | 极化选择性 vibX/vibZ；srcX≡srcY | **已确认** | 直陈 |
| 7 | 多窗口频率选择性+死区 | **已确认** | 「驱动-响应窗口」 |
| 8 | srcX 200 GHz 共振耦合通道 | **候选** | 「候选共振耦合通道」；距 ringdown 173.66 ~26 GHz；**绝不**本征频率 |
| 9 | srcZ 100 GHz 反常 +z | **强支持（现象）/机制候选** | 「反常非平衡响应窗口」；dE/dt<0 |
| 10 | F_eff(B) 标度（替换 v∝B^1.99） | **候选→需新仿真** | 需 Phase1 宽幅扫描 |
| 11 | F_eff 方向 vs 频率/源（点-面红移） | **强支持（峰位/方向）** | 点-面**仅峰位与方向，绝不量级** |
| 12 | 平动↔膨胀交叉块 | **已确认（算出后）** | Tier2 纯几何 |
| 13 | 膨胀块⇒呼吸刚度 | **必须 hedge（定性）** | 需 E(R),E(r) Hessian，J2/J4 抄 R8r4_Ku0.mx3 |
| 14 | 强驱坍缩 t≈0.91 ns | **强支持** | 含 Q_H(t),R/r(t)；不赋普适阈 |

### 绝不可说清单（must-not-say → 安全替换）

| 绝不说 | 安全替换 |
|---|---|
| 「200/1000/1100 GHz 是 Hopfion 本征频率/共振模式」 | 「驱动-响应/传输窗口」 |
| 「173.66 GHz 共振模」 | 「开边界系统候选自由模，未隔离为线性耦合本征模（quench_dominated=true）」 |
| 「79.14 GHz 本征模」 | 「未通过 field²幂律+SNR 闸的差分候选峰（passed=false）」 |
| 「srcZ 100 GHz 净能量吸收峰」 | 「最强绝对非平衡能量率响应；拟合后瞬态斜率为负」 |
| 「点源比面源更高效/耦合更强」 | 「点源响应峰相对面源红移」（能量注入不可比：500T 单胞 vs 1T 面） |
| 「Thiele 方程定量解释/复现轨迹」 | 「广义集体坐标框架解读运动；一个无参数预言（偏转角）对仿真检验」 |
| 「我们测得/确定了磁振子力 F」 | 「从实测速度提取有效力 F_eff，并独立检验一个无参数偏转角预言」 |
| 「拓扑回旋耦合驱动横向运动」（算 G 之前） | 「横向运动与拓扑回旋耦合一致；我们计算平动回旋张量以检验其是否足够」 |
| 「1100 GHz 超过 Hopfion 稳定阈」 | 「强 1100 GHz 驱动在此协议下 t≈0.91 ns 摧毁结构；报 Q_H(t) 与 R/r(t)」 |
| 「Hopfion 平动 G=4πQ_H ẑ」 | C4 禁止套用；必须计算 |
| 「v∝B^1.99」 | 完全省略，直到重做宽幅振幅扫描存在 |

---

## 5. Codex 辅助 prompts

见同目录 `codex_prompts.md`（C-1…C-6，即贴即用、自包含）。

通用规则（每个 prompt 内已含）：WSL venv 激活；**强制** `from hopfion_analysis import ...`（C-7，绝不重写共享库）；输出写到带日期结果目录，**不写入 repo 源树**；**前因子/符号抄 Liu 2020 PRL 124,127204，绝不重导**；点源/面源绝不比绝对量级。

按当前决策：C-1（G/D 平动+膨胀块）+ C-2（实测霍尔角）+ C-3（坍缩追踪，twist 降为诊断）+ C-4（逆向 F_eff）属 Phase 0，可在用户细看后启动；C-5（振幅扫描）暂缓；C-6（k 谱）期刊层级定后再说。

---

## 6. 需要用户拍板的开放决策（含已决项）

1. ✅ **Thiele 范围**：已定 = 平动块+膨胀块，twist future work。
2. ⏸ **是否投资 Phase 2 昂贵仿真**：待 Phase 0 霍尔角检验结果 + 期刊层级后定（条件触发）。
3. ⏸ **目标期刊层级**：待 Phase 0/1 结果后定。
4. ⏸ **振幅扫描 S1**：暂缓，待 Phase 0 后定。
5. **twist/poloidal-phase + Q_H(t) 库函数**：确认接受**扩展** `hopfion_analysis.py`（非另起文件）；需提供项目里现有 Q_H 数值积分实现路径供 Codex 复用公式（避免重导）。
6. **边界条件呈现**：是否接受「结构张量(周期) + 驱动响应(吸收边界)」分离表述，并把 ringdown 否定闸显式写进 Limitations 作护盾。

### 实现关键文件
- `95_shared_scripts/hopfion_analysis.py`（compute_hall_angle / extract_Rr_series / extract_trajectory_phase_correlation / compute_Rr / core_count；C-3 需扩展 hopf_index + poloidal_phase）
- `04_frustrated_fm_foundation/20260105_frustrated_fm/centered_stability_test/stability_Ku10k.out/ovf_archive.tar.zst`（封装 m000020.ovf 真实驱动平衡态）
- `95_shared_scripts/create_hopfion_AFM_v2.py`（generate_hopfion_ovf，afm=None 即纯 FM；缺连续 twist 旋钮——仅内部 R/r 块需要它，须先验证复现真实 R,r 与 Q_H=1）
- `04_frustrated_fm_foundation/20260105_frustrated_fm/spin_wave_dynamics/multisource_control/bidirectional_z/freq_switch_bidirectional_v3.out/ovf_archive.tar.zst`（唯一幸存驱动全场 OVF，含 t≈0.91 ns 坍缩；C-3 输入）
- `06_eigenmode_frequency_mechanism/hopfion_mode_map_20260608/results/deformation_timeseries.csv`（Phase-0 轨迹纵/横分解输入；C-2 输入）
