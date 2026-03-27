# Spin Wave Dynamics — Frustrated FM Hopfion

**研究目标**：通过自旋波实现对 Frustrated FM Hopfion 的任意自由控制——建立频率→运动模式映射、振幅→速度标度律、偏振方向选择性规律，为神经形态计算等应用提供可控驱动方案。

**公共初始态**：`centered_stability_test/stability_Ku10k.out/m000020.ovf`（Q_H=1，Ku=10k 下弛豫 1ns 的稳定 Hopfion，R≈2.17nm，r≈1.64nm）

> **⚠️ Q_H 修正（2026-03-26）**：原 `hopfion_z_Qh2_p1q2.ovf`（Q_H=2 解析态）**从未被任何 mx3 脚本加载**，已删除（可用 `create_hopfion_AFM_v2.py` 重新生成）。
> 所有实验的初始态追溯链为：`hopfion_z_R8_r4.ovf`（Q_H=1）→ `ku_critical_sweep/R8r4_Ku10k.out/m000020.ovf` → `centered_Ku10k.ovf` → `stability_Ku10k.out/m000020.ovf`。
> 数值 Hopf index 验证确认实际拓扑荷为 **Q_H=1**。详见 `compute_hopf_index.py`。

---

## 目录结构

```
spin_wave_dynamics/
├── # （原 hopfion_z_Qh2_p1q2.ovf 已删除，Q_H=2 解析态从未使用）
├── direction_coupling/             # 实验1：方向耦合选择性
├── freq_sweep/                     # 实验2：频率扫描（已合并）
│   ├── 02ns/                       #   100-1000GHz, 0.2ns, 10ps autosave（21帧，10频率）
│   ├── 05ns/                       #   300/400/900/1000GHz, 0.5ns, 10ps autosave（51帧，4频率）
│   ├── analyze_motion_modes.py     #   02ns 运动模式分析（相位相关法 + 向量微分）
│   ├── analyze_motion_modes_05ns.py #  05ns 运动模式分析
│   ├── gen_02ns.py / gen_05ns.py   #   mx3 生成脚本
│   └── results/                    #   输出图表（8个文件，见实验2详述）
├── amplitude_sweep/                # 实验3：幅度扫描
├── multisource_baseline/           # 实验5：多源自旋波方向控制
│   ├── sw_srcZ_neg_f200GHz.mx3    #   srcZ(-z) 基线仿真脚本（待运行）
│   └── analyze_baselines.py       #   三源基线对比分析
├── srcZ_freq_sweep/               # srcZ(+z) 频率扫描数据（实验5 复用）
└── README.md
```

---

## 实验1：方向耦合选择性 (`direction_coupling/`)

**目的**：确定自旋波振动方向与 Hopfion 的耦合强弱。

**参数**：f=440GHz, B=1T, Ku=10k, α=0.001(bulk)/100(边界), 0.5ns，4组组合

**结论（已完成，2026-03-21）**：

| 组合 | 位移 \|dr\| | Δ能量 | 结论 |
|---|---|---|---|
| srcX_vibX | 2.36 nm | +4.15×10⁻¹⁹ J | **强耦合** |
| srcZ_vibX | 6.71 nm | +2.51×10⁻¹⁹ J | **强耦合**（反向漂移） |
| srcX_vibZ | 0.005 nm | +3.4×10⁻²¹ J | 无耦合 |
| srcZ_vibZ | 0.001 nm | +3.2×10⁻²¹ J | 无耦合 |

**核心结论**：面内振动（vibX）比轴向振动（vibZ）耦合强 ~500-6000 倍。后续实验统一使用 srcX_vibX 配置。

结果图：`direction_coupling/results/`

---

## 实验2：频率响应扫描 (`freq_sweep/`)

**目的**：扫描 Hopfion 对不同自旋波频率的运动模式响应。

**参数**：srcX_vibX, B=1T, Ku=10k，100-1000GHz（10点，步长100GHz）

**数据集**：
- `02ns/`：10个频率（100-1000GHz），0.2ns，10ps autosave（21帧）
- `05ns/`：4个频率（300/400/900/1000GHz），0.5ns，10ps autosave（51帧），关键频率延伸

**分析方法**：相位相关法（FFT）逐帧提取 Hopfion 位移 r(t)，向量微分得速度 v(t) = dr/dt 和加速度 a(t) = dv/dt。

**分析脚本**：
- `analyze_motion_modes.py`：02ns 数据集（10频率）
- `analyze_motion_modes_05ns.py`：05ns 数据集（4频率）

### 02ns 运动模式分析结果（已完成，2026-03-26）

| 频率 | \|dr\| (nm) | dz (nm) | v̄ (nm/ns) | ā (nm/ns²) | Core₀ | Core_f | 模式 |
|---|---|---|---|---|---|---|---|
| 100 GHz | 1.938 | +1.833 | 15.66 | 506 | 908 | 1038 | accelerating |
| 200 GHz | 2.508 | +2.500 | 18.53 | 321 | 908 | 974 | accelerating |
| 300 GHz | 0.902 | +0.901 | 6.39 | 448 | 908 | 938 | accelerating |
| 400 GHz | 0.084 | +0.076 | 1.53 | 111 | 908 | 978 | static |
| 500 GHz | 0.151 | +0.136 | 1.86 | 130 | 908 | 973 | accelerating |
| 600 GHz | 0.077 | +0.075 | 1.83 | 149 | 908 | 989 | static |
| 700 GHz | 0.445 | +0.444 | 4.67 | 287 | 908 | 952 | accelerating |
| 800 GHz | 0.531 | +0.527 | 4.13 | 277 | 908 | 906 | accelerating |
| 900 GHz | 0.408 | +0.406 | 3.28 | 252 | 908 | 923 | accelerating |
| 1000 GHz | 5.500 | +5.498 | 41.05 | 1180 | 908 | 1045 | accelerating |

> 注：v̄ 和 ā 为跳过前 1/3 瞬态后的时间平均值。0.2ns 时间窗内大部分频率仍处于瞬态加速阶段。

### 05ns 运动模式分析结果（已完成，2026-03-26）

| 频率 | \|dr\| (nm) | dz (nm) | v̄ (nm/ns) | ā (nm/ns²) | Core₀ | Core_f | 模式 |
|---|---|---|---|---|---|---|---|
| 300 GHz | 3.838 | +3.837 | 10.10 | 354 | 908 | 971 | accelerating |
| 400 GHz | 0.542 | +0.541 | 2.33 | 159 | 908 | 940 | accelerating |
| 900 GHz | 2.422 | +2.422 | 6.64 | 253 | 908 | 940 | accelerating |
| 1000 GHz | 14.317 | +14.300 | 59.20 | 1176 | 908 | 701 | accelerating |

### 核心发现

**1. 运动方向：拓扑 Magnus 力主导**

所有频率下 dz >> dx（位移几乎全部沿 +z 方向），而自旋波从 -x 边界注入沿 +x 传播。Hopfion 运动方向与自旋波传播方向近乎垂直，这是拓扑 Magnus 力的特征行为——类比 skyrmion 的 Magnus 偏转，但 Hopfion 的三维拓扑荷导致偏转角接近 90°。

**2. 频率响应分三档**

| 响应等级 | 频率范围 | v̄ (nm/ns) | 特征 |
|---|---|---|---|
| 强响应 | 100-200, 1000 GHz | 15-60 | 持续加速，位移显著 |
| 中等响应 | 300, 700-900 GHz | 3-10 | 缓慢加速 |
| 弱响应（死区） | 400-600 GHz | <2.5 | 几乎不动 |

**3. 1000 GHz 边界反弹**

05ns 数据清晰显示 1000 GHz 的运动轨迹：Hopfion 沿 +z 加速运动，约 0.25ns 时到达 PBC 边界附近（dz ≈ 17.5nm），随后被 absorbing boundary（α=100）区域反弹回来（vz 由正变负），0.5ns 时 dz ≈ 14.3nm。Core count 在边界附近下降（908→701）是 absorbing boundary 区域扭曲 mz 分布导致的表观变化，并非结构损伤。

**4. 02ns vs 05ns 对比一致性**

| 频率 | 02ns \|dr\| | 05ns \|dr\| | 05ns/02ns 比值 | 说明 |
|---|---|---|---|---|
| 300 GHz | 0.902 | 3.838 | 4.3x | 持续加速，位移随时间增长 |
| 400 GHz | 0.084 | 0.542 | 6.5x | 弱响应，延长后稍有积累 |
| 900 GHz | 0.408 | 2.422 | 5.9x | 中等加速 |
| 1000 GHz | 5.500 | 14.317 | 2.6x | 受边界反弹限制，实际峰值 17.5nm |

### 结果文件（`freq_sweep/results/`）

| 文件 | 内容 |
|---|---|
| `displacement_all_freq.png` | 02ns 全频率位移轨迹：\|dr(t)\|, dx(t), dz(t), core count |
| `velocity_all_freq.png` | 02ns 全频率速度：\|v(t)\|, vz(t)，含模式标注 |
| `motion_mode_map.png` | 02ns 频率-位移/速度/加速度柱状图，颜色编码运动模式 |
| `motion_mode_summary.txt` | 02ns 数值汇总表 |
| `displacement_05ns.png` | 05ns 4频率位移轨迹，可见 1000GHz 边界反弹 |
| `velocity_05ns.png` | 05ns 4频率速度，1000GHz vz 由正变负 |
| `motion_mode_map_05ns.png` | 05ns 频率-位移/速度/加速度柱状图 |
| `motion_mode_summary_05ns.txt` | 05ns 数值汇总表 |

---

## 实验3：幅度扫描 (`amplitude_sweep/`)

**目的**：在固定频率下扫描自旋波幅度，得到速度-幅度标度律 v ∝ Bⁿ。

**参数**：srcX_vibX, f=440GHz, Ku=10k, 0.5ns

**完成状态**（2026-03-25 更新，B设备数据已合并）：

| B (T) | 状态 | 帧数 |
|---|---|---|
| 0.05 | 完成 | 11 |
| 0.1 | 完成 | 11 |
| 0.2 | 完成 | 11 |
| 0.5 | 完成 | 11 |
| 1.0 | 完成 | 11 |
| 2.0 | 完成 | 11 |

> 440GHz 此前被错误标记为"死区"，该结论已于 2026-03-25 撤销。6 点数据全部有分析价值。

---

## 实验4：拓扑 Hall 角定量表征 (`freq_sweep/` + `amplitude_sweep/`)

**目的**：定量测量 Q_H=1 FM Hopfion 在自旋波驱动下的拓扑 Hall 偏转角 θ_H。

**分析脚本**：
- `freq_sweep/analyze_hall_angle.py`：θ_H(f) 频率依赖
- `amplitude_sweep/analyze_hall_angle_amplitude.py`：θ_H(B) 幅度依赖

**核心结果**（2026-03-27）：

| 维度 | 结果 | 有效范围 |
|---|---|---|
| θ_H vs f | 强响应频率 θ_H ≈ 85-90°，1000GHz 最大位移（14.3nm@0.5ns） | 100-300, 700-1000 GHz |
| θ_H vs B | 有效幅度下 θ_H ≈ 85-89°，不随幅度显著变化 | B ≥ 0.5T @440GHz |
| 死区 | 400-600 GHz 位移 < 0.1nm，θ_H 无意义 | — |

**物理结论**：FM Hopfion 的拓扑 Hall 角在有效驱动范围内稳定接近 90°，表明 Magnus 力主导运动方向，具有拓扑保护特征。速度标度 v_perp ∝ B^n（n > 1，非线性）。

**bd 任务**：Hopfion-rt4.1

---

## 实验5：多源自旋波方向控制 (`multisource_baseline/`)

**目的**：建立源面位置→Hopfion 运动方向的完整映射，验证不同传播方向的 Hall 角差异。

**分析脚本**：`multisource_baseline/analyze_baselines.py`

**Phase 1 基线结果**（2026-03-27，srcZ(-z) 待补充）：

| 配置 | θ_H (deg) | 位移 (nm) | 物理含义 |
|---|---|---|---|
| srcX (+x) @ 200GHz | 87.4 | 2.51 | 面内 SW → 近 90° Hall 偏转 |
| srcZ(+z) @ 200GHz | 1.2 | 7.39 | 轴向 SW → 几乎纯平行运动 |
| srcZ(-z) @ 200GHz | 待运行 | — | 反向轴向 SW |

**物理结论**：面内自旋波（srcX）产生 ~90° Hall 偏转，轴向自旋波（srcZ）几乎无 Hall 偏转（1.2°）。这揭示了 Hopfion 拓扑 Hall 效应的强方向选择性。

**后续阶段**：Phase 2 双源组合、Phase 3 慢相位调制圆形轨迹。

**bd 任务**：Hopfion-rt4.2

---

## 对称性分析：独立激励配置

Hopfion 环面位于 xOy 平面，具有绕 z 轴的旋转对称性（C₄ᵥ）：

- **面内等价**：±x ≡ ±y → 只需测一个面内方向（srcX）
- **轴向独立**：srcZ ≠ srcX（Hopfion 面内/轴向刚度不同，共振频率可能不同）
- **极化选择性**：direction_coupling 已证实 vibX 强耦合、vibZ 无耦合

因此**独立激励配置仅 2 组**：

| 配置 | 物理含义 |
|---|---|
| srcX_vibX | 面内自旋波 → 驱动 Hopfion 面内平移 |
| srcZ_vibX | 轴向自旋波 → 驱动 Hopfion 轴向平移 |

同一共振频率不一定同时适用于两个方向——面内平动模式和轴向平动模式的本征频率由 Hopfion 在两个方向上的有效势决定，通常不同。direction_coupling 数据（440GHz 下 srcX=2.36nm vs srcZ=6.71nm）已暗示两方向耦合效率不同。

---

## 共振频率判据

共振 = 激励频率匹配 Hopfion 本征模式，能量高效转移。三种互补方法：

### 方法1：速度响应谱 v̄(f)
- 对频率扫描各点提取时间平均速度
- 画 v̄ vs f → **峰值 = 共振频率**
- 数据来源：freq_sweep/02ns + 05ns 已有数据
- 工具：`resonance_analysis.velocity_response_spectrum()`

### 方法2：能量吸收谱 ΔĖ(f)
- 从各频率点 table.txt 读取 E_total(t)
- 计算 dE_total/dt 平均斜率 → **峰值 = 共振频率**
- 共振时 Hopfion 从自旋波高效吸收能量，dE/dt 显著偏高
- 数据来源：freq_sweep/02ns + 05ns table.txt **已有数据，无需新仿真**
- 工具：`resonance_analysis.energy_absorption_spectrum()`

### 方法3：脉冲本征模谱
- 用宽频高斯脉冲（σ~0.2ps, BW~800GHz）一次激发所有内模式
- 脉冲结束后 Hopfion 自由振荡 → FFT 得本征频率
- 分析信号：centroid(t) 各分量 → 平动模式；E_total(t) → 全模式
- 工具：`resonance_analysis.generate_pulse_mx3()` + `pulse_eigenmode_analysis()`

### 几何匹配估算

| 模式 | 匹配条件 | 估算 |
|---|---|---|
| 面内平动 | λ_SW ~ 2R | ~5.2nm → k ~ 1.2 nm⁻¹ |
| 呼吸模式 | λ_SW ~ 2r | ~4.3nm → k ~ 1.5 nm⁻¹ |

具体频率需通过色散关系 ω(k) 转换（frustrated FM 色散非平凡）。

---

## 下一步计划

### P0（已完成）：现有数据运动模式分析
- ~~对 02ns/05ns 所有频率点逐帧提取位移 r(t)、速度 v(t)、加速度 a(t)~~
- ~~分类每个频率的运动模式~~
- 产出：8 个结果文件（见实验2 results 列表）

### P1：低频窗口精扫 100-200 GHz — bd: Hopfion-fnt
- 100-200 GHz 为强响应窗口，需 25GHz 步长精扫定位峰值共振频率
- srcX_vibX, B=1T, Ku=10k, 0.5ns

### P2：关键频率重跑 0.5ns — bd: Hopfion-x9s
- 100, 200 GHz 延长到 0.5ns，确认是否持续加速或趋于稳态

### P3：幅度扫描 @ 目标频率 — bd: Hopfion-ttz
- 在共振频率处扫描 B = 0.01~2.0 T，建立 v-B 标度律

### P4：srcZ_vibX 方向扫描
- 同一频率集用轴向自旋波激励，对比面内/轴向共振频率差异

---

## 更新记录

| 日期 | 内容 |
|---|---|
| 2026-03-21 | direction_coupling 4-combo 完成，结论：vibX 强耦合，vibZ 无耦合 |
| 2026-03-22 | freq_sweep_coarse 完成，发现 1000GHz 位移突增 |
| 2026-03-24 | amplitude_sweep 3点数据回收；目录重组 |
| 2026-03-25 | **修正**：撤销"440GHz死区"结论；废弃单点位移benchmark；确立运动模式分类分析框架 |
| 2026-03-26 | 合并三个 freq_sweep 目录为 freq_sweep/（02ns + 05ns）；补充对称性分析和共振判据 |
| 2026-03-26 | **完成 P0**：02ns（10频率）+ 05ns（4频率）运动模式分析。修正速度计算为向量微分 v=dr/dt。核心发现：Magnus 力导致 dz>>dx；强响应窗口 100-200GHz 和 1000GHz；400-600GHz 为死区；1000GHz 出现边界反弹 |
| 2026-03-27 | **实验4：拓扑 Hall 角定量表征** — θ_H(f) 和 θ_H(B) 分析完成。核心结论：有效范围内 θ_H ≈ 85-90°，拓扑保护。bd: Hopfion-rt4.1 |
| 2026-03-27 | **实验5 Phase 1：多源基线** — srcX 和 srcZ(+z) 分析完成，srcZ(-z) 仿真待运行。面内vs轴向 Hall 角差异显著（87° vs 1°）。bd: Hopfion-rt4.2 |
