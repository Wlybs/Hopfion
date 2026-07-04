# 竞争交换铁磁体系 Hopfion 研究 — 完整工作日志

> 项目目录: `/mnt/d/Research/Hopfion/04_frustrated_fm_foundation/20260105_frustrated_fm/`
> 起止时间: 2026-01-05 ~ 至今
> 状态: **进行中**（稳定性研究完成，自旋波驱动分析中）

---

## 一、项目概述

本项目研究竞争交换铁磁体系中 Hopfion 的稳定性、漂移行为、各向异性依赖和自旋波驱动动力学。该体系无 DMI、无退磁场，Hopfion 完全依赖 J1-J2-J4 竞争交换稳定。采用三维周期性边界条件（PBC）模拟无限体块。

### 材料参数

| 参数 | 符号 | 数值 |
|------|------|------|
| 饱和磁化强度 | $M_s$ | 1.5×10⁵ A/m |
| 最近邻交换 | $A_{ex}$ (J1) | 5×10⁻¹² J/m |
| 次近邻交换 | J2 | -0.164 J1（反铁磁） |
| 第四近邻交换 | J4 | -0.082 J1（反铁磁） |
| 网格 | — | 100×100×100, 0.5nm/格 |
| 边界条件 | — | PBC(1,1,1) |

### Mumax3 中 J2/J4 实现

J2、J4 通过 `AddFieldTerm(Mul(Const(Coeff), sum_shifted))` 实现：
- J4: 6 个邻居在 2a 处 → `Shifted(m, ±2, 0, 0)` 等
- J2: 12 个邻居在 √2·a 处 → `Shifted(m, ±1, ±1, 0)` 等
- 系数公式: `Coeff = A_Jn * 2.0 / (Ms * CellSize²)`

**关键 bug 记录**: 曾出现 `Coeff = -2.0/Ms * A_J4 / CellSize²` 的符号错误，导致竞争交换变为非竞争（Coeff 符号反转），Hopfion 在 50ps 内坍缩。正确公式为 `Coeff = A_Jn * 2.0 / (Ms * CellSize²)`，此时 A_Jn 本身为负值，Coeff 自然为负。

---

## 二、根目录文件

根目录仅保留工作日志和子目录，**不存放仿真脚本或分析脚本**（已于 2026-03-24 整理）。

| 目录 | 描述 |
|------|------|
| `size_sweep/` | 尺寸收敛测试（R8r4、R12r5 → 同一吸引子） |
| `anisotropy_study/` | 各向异性扫描，含 size_vs_ku 和 ku_critical_sweep |
| `drift_experiments/` | 漂移稳定性实验（unified_rerun 控制变量组） |
| `centered_stability_test/` | 居中稳态验证（Ku=0/10k/50k 三组） |
| `spin_wave_dynamics/` | 自旋波驱动动力学实验 |
| `templates/` | 复用模板：基础 .mx3 模板、sweep 生成脚本、参数一致性审计脚本 |

**`templates/` 文件清单**:

| 文件 | 描述 |
|------|------|
| `frustrated_fm_base.mx3.template` | 基础 frustrated FM 参数模板（材料参数、J2/J4 系数） |
| `generate_sweep.py` | 批量生成 Ku 扫描 .mx3 脚本 |
| `audit_sweep_params.py` | 扫描参数一致性审计（防止控制变量不一致） |

---

## 三、尺寸收敛测试 (`size_sweep/`)

**目的**: 验证不同初始尺寸的 Hopfion 是否收敛到同一平衡态（固有尺寸吸引子）。

### 文件清单

| 文件 | 描述 |
|------|------|
| `hopfion_z_R8_r4.ovf` | R=8nm, r=4nm 初始态（12MB） |
| `hopfion_z_R12_r5.ovf` | R=12nm, r=5nm 初始态（12MB） |
| `R8r4_Ku0.mx3` | R8r4 初始态，Ku1=0，1ns 弛豫 |
| `R12r5_Ku0.mx3` | R12r5 初始态，Ku1=0，0.95ns 弛豫（首段） |
| `R12r5_Ku0_continue.mx3` | R12r5 续跑脚本，0.95→4.95ns（4ns） |
| `analyze_size_sweep.py` | 分析 R(t), r(t) 收敛行为 |
| `replot_english.py` | 英文标注重绘版（含三组数据集） |

### 仿真输出

| 目录 | 帧数 | 时长 | 结果 |
|------|------|------|------|
| `R8r4_Ku0.out/` | 21 | 1ns | 收敛到 R=2.60nm, r=2.16nm |
| `R12r5_Ku0.out/` | **100** | **4.95ns**（首段+续跑合并） | 收敛到 R=2.60nm, r=2.27nm |

> R12r5 两段输出已于 2026-03-24 合并：首段 m000000~m000019（0~0.95ns）+ 续跑重映射 m000020~m000099（1.0~4.95ns），共 100 帧。原 `R12r5_Ku0_continue.out/` 目录已删除。

### 结果

**三组初始尺寸均收敛到同一固有吸引子**（与 `anisotropy_study/size_vs_ku/` Ku=0 数据共同验证）：

| 配置 | 初始 R | 收敛后 R / r | 收敛时间 |
|------|--------|-------------|---------|
| Small (R=3.1nm) | 3.1nm | 2.60 / 2.27 nm | ~1.3ns |
| R8r4 | 8.0nm | 2.63 / 2.22 nm | ~0.8ns |
| R12r5 | 12.0nm | 2.60 / 2.27 nm | ~2.5ns |

**固有尺寸吸引子**: $R_{eq} \approx 2.60$ nm, $r_{eq} \approx 2.16$ nm — 与初始尺寸无关，三者误差 <2%。

输出图: `size_convergence_english.png`（含三组初始态，2026-03-24 更新）

---

## 四、吸引子唯一性验证 (`anisotropy_study/size_vs_ku/`)

> 原目录 `anisotropy_sweep/` 已于 2026-03-24 重命名/迁移为 `anisotropy_study/size_vs_ku/`，与 `ku_critical_sweep/` 共同构成 `anisotropy_study/` 子项目。

**目的**: 验证从**小初始态**（R≈3.1nm）出发，不同 Ku 值下 Hopfion 是否收敛到与大初始态相同的吸引子。

### 文件清单

- **初始态**: `hopfion_Qh1_FM_SMALL.ovf`（R≈3.1nm，小尺寸 Hopfion）
- **6 组 .mx3 脚本**: Ku1 = 0, 2.5k, 5k, 7.5k, 10k, 12k J/m³
  - 每组加载相同初始态，3ns 弛豫，autosave 0.1ns（31 帧）
  - 原 15k/18k/20k/25k 四组因数据截断/不完整，已于 2026-03-24 删除
- **分析脚本**: `analyze_ani_sweep.py`（R/r 时间演化 + 存活表）

### 仿真输出（6 组有效数据）

| 目录 | Ku1 (J/m³) | R @ 3ns (nm) | r @ 3ns (nm) | 状态 |
|------|-----------|-------------|-------------|------|
| `Ku1_0.0e+00_Ms_*.out/` | 0 | 2.60 | 2.16 | 存活 |
| `Ku1_2.5e+03_Ms_*.out/` | 2500 | 2.35 | 1.95 | 存活 |
| `Ku1_5.0e+03_Ms_*.out/` | 5000 | 2.29 | 1.81 | 存活 |
| `Ku1_7.5e+03_Ms_*.out/` | 7500 | 2.17 | 1.74 | 存活 |
| `Ku1_1.0e+04_Ms_*.out/` | 10000 | 2.17 | 1.64 | 存活 |
| `Ku1_1.2e+04_Ms_*.out/` | 12000 | 2.00 | 1.64 | 存活 |

### 结果

与 `ku_critical_sweep/` 重叠点完全一致（误差 <3%），证明**吸引子与初始态尺寸无关**。

输出: `results/` 下 `R_r_vs_time.png`, `summary_Rr_vs_Ku1.png`, `survival_table.txt`

---

## 五、临界各向异性主体扫描 (`anisotropy_study/ku_critical_sweep/`)

> 原目录 `anisotropy_sweep_large/`（粗扫）和 `critical_ku_fine/`（细化）已于 2026-03-24 合并为 `anisotropy_study/ku_critical_sweep/`。

**目的**: 用大初始态（R=8nm）进行完整 Ku1 扫描，确定准确的临界阈值 Ku_c 并绘制平衡相图。

### 文件清单

- **10 组 .mx3 脚本**: Ku1 = 0, 5k, 10k, 20k, 30k, **40k**, 50k, 52k, 55k, 58k J/m³
  - 加载 `hopfion_z_R8_r4.ovf`（R=8nm, r=4nm），α=0.2，1ns，autosave 50ps（21 帧）
  - Ku=40k 为 2026-03-24 补充；原 Ku=75k 数据因已确认消解区间而删除
- **分析脚本**: `analyze_sweep_large.py`（含 PBC 坐标展开、圆拟合、mz=0 等值面管径计算）

### 仿真输出（完整 10 点）

| 目录 | Ku1 (J/m³) | 帧数 | R @ 1ns (nm) | r @ 1ns (nm) | 状态 |
|------|-----------|------|-------------|-------------|------|
| `R8r4_Ku0.out/` | 0 | 21 | 2.63 | 2.22 | 存活 |
| `R8r4_Ku5k.out/` | 5000 | 21 | 2.35 | 1.85 | 存活 |
| `R8r4_Ku10k.out/` | 10000 | 21 | 2.17 | 1.64 | 存活 |
| `R8r4_Ku20k.out/` | 20000 | 21 | 1.82 | 1.54 | 存活 |
| `R8r4_Ku30k.out/` | 30000 | 21 | 1.82 | 1.38 | 存活 |
| `R8r4_Ku40k.out/` | 40000 | 21 | 1.69 | 1.30 | 存活（2026-03-24 新增） |
| `R8r4_Ku50k.out/` | 50000 | 21 | 1.56 | 1.24 | 存活 |
| `R8r4_Ku52k.out/` | 52000 | 21 | 1.46 | 1.27 | 存活（接近临界） |
| `R8r4_Ku55k.out/` | 55000 | — | — | — | **消解** |
| `R8r4_Ku58k.out/` | 58000 | — | — | — | 消解 |

### 结果

**临界各向异性**: $K_{u1,c} \in (52000, 55000)$ J/m³，精度 3k J/m³

> ⚠️ 早期记录中曾误写 "Ku55k 存活，Ku58k 消解"，已于 2026-03-24 更正。正确：Ku52k 存活，Ku55k 即已消解。

物理机制: 各向异性压缩管径至格点分辨率以下 → 拓扑保护失效坍缩。

输出: `results/` 下 `R_r_vs_time.png`, `summary_Rr_vs_Ku1.png`（Ku≥55k 标为消解）, `survival_table.txt`

---

## 六、漂移实验 (`drift_experiments/`)

**目的**: 系统研究 Hopfion 在不同背景磁化方向下的漂移行为。

### ~~旧结论（已推翻）~~

> ~~漂移由背景磁化方向决定，与 Hopfion 轴向无关: bg=mz → 漂移; bg=mx/my → 稳定。~~
>
> 此结论基于控制变量不一致的旧实验（alpha=5.0 vs 0.2、R8r4 vs R3r2 初始态、不同运行时长），**已于 2026-03-24 被推翻**。

### 控制变量重跑（`unified_rerun/`，2026-03-23）

统一参数：alpha=0.2, Ku1=0, R3r2 初始态, 100³ PBC(1,1,1), 2ns

| 配置 | 背景 | Hopfion 轴 | 轴向位移 | 横向位移 | 判定 |
|------|------|------------|----------|----------|------|
| bg=mz, axis=z | mz=+1 | z | +4.750 nm (z) | 0 nm | 格点弛豫 |
| bg=mz, axis=x | mz=+1 | x | +4.750 nm (x) | 0 nm | 格点弛豫 |
| bg=my, axis=y | my=+1 | y | +4.750 nm (y) | 0 nm | 格点弛豫 |
| bg=mx, axis=x | mx=+1 | x | +4.750 nm (x) | 0 nm | 格点弛豫 |

### 关键发现（修正后）

**背景磁化方向对漂移行为无影响。** 4 组配置表现完全一致：前 ~1ns 沿 Hopfion 轴向发生 4.75nm 一次性格点弛豫（初始 ansatz 到最近格点势极小值），之后完全钉扎。横向位移始终为零。旧实验中观测到的"bg=mz 漂移"是控制变量不一致的实验假象。

### 文件清单

**初始态** (`initial_states/`):
| 文件 | 描述 |
|------|------|
| `hopfion_z_R3_r2.ovf` | 轴=z, bg=mz |
| `hopfion_x_R3_r2.ovf` | 轴=x, bg=mx |
| `hopfion_y_R3_r2.ovf` | 轴=y, bg=my |
| `hopfion_xaxis_zbg_R3_r2.ovf` | 轴=x, bg=mz (空间转置生成) |

**unified_rerun/**（控制变量重跑，主结果）:
| 文件 | 描述 |
|------|------|
| `sweep_config.json` | 统一参数配置 |
| `bg_mz_axis_z.mx3` / `.out/` | bg=mz, axis=z, 2ns |
| `bg_mz_axis_x.mx3` / `.out/` | bg=mz, axis=x, 2ns |
| `bg_my_axis_y.mx3` / `.out/` | bg=my, axis=y, 2ns (含续跑) |
| `bg_mx_axis_x.mx3` / `.out/` | bg=mx, axis=x, 2ns |
| `analyze_drift_unified_v2.py` | 控制变量重跑分析脚本 |

**其他完整实验**（仍有效）：
| 子目录 | 说明 |
|------|------|
| `bg_mx_axis_x_stable/` | bg=mx 10ns 长期稳定性验证（前 0.5ns 格点弛豫后完全钉扎） |
| `bg_my_axis_y_stable/` | bg=my 2ns 稳定验证 |

> 原 `bg_mz_axis_z_drift/` 和 `bg_mz_axis_x_drift/` 因控制变量不一致（alpha=5.0, R8r4 大初始态）已于 2026-03-24 删除。旧实验中的"bg=mz 漂移"结论系实验假象，已推翻。

**分析输出** (`analysis/`):
| 文件 | 描述 |
|------|------|
| `drift_unified_v2_summary.txt` | 控制变量重跑数值汇总 |
| `trajectory_10ns_final.png` | 10ns 质心轨迹图（论文级）|

---

## 七、居中稳态验证 (`centered_stability_test/`)

**目的**: 验证 mz 背景下 z-roll 居中后的 Hopfion 能否维持稳态，为自旋波仿真提供可靠初始态。

### 文件清单

| 文件 | 描述 |
|------|------|
| `generate_centered_ovf.py` | 从 `anisotropy_study/ku_critical_sweep/` 取末帧 OVF，用 np.roll 沿 z 轴平移使 Hopfion 居中 |
| `centered_Ku0.ovf` | Ku=0 居中初始态 |
| `centered_Ku10k.ovf` | Ku=10k 居中初始态 |
| `centered_Ku50k.ovf` | Ku=50k 居中初始态 |
| `stability_Ku0.mx3` | Ku=0, α=0.2, PBC, 1ns |
| `stability_Ku10k.mx3` | Ku=10k, α=0.2, PBC, 1ns |
| `stability_Ku50k.mx3` | Ku=50k, α=0.2, PBC, 1ns |
| `run_stability_tests.sh` | 顺序执行 3 组测试（预计 21h） |
| `analyze_centered_stability.py` | 分析 z 漂移、xyz 分量、核心细胞数 |

### 仿真输出

| 目录 | Ku1 | z₀ (nm) | z_final (nm) | Δz (nm) | 核心 | 状态 |
|------|------|------|------|------|------|------|
| `stability_Ku0.out/` | 0 | 28.44 | 29.15 | +0.70 | 1984→2128 | PASS（呼吸振荡） |
| `stability_Ku10k.out/` | 10k | 25.07 | 25.05 | -0.019 | 920→908 | **PASS（极稳定）** |
| `stability_Ku50k.out/` | 50k | 25.13 | 25.19 | +0.062 | 388→404 | PASS |

### 结果

三组全部通过（|Δz| < 2nm）。**Ku=10k 最优**，被选为自旋波仿真初始态。

输出: `stability_results/` 下 `hopfion_z_drift.png`, `hopfion_xyz_drift.png`, `hopfion_mz_core_count.png`, `stability_summary.txt`

---

## 八、自旋波动力学 (`spin_wave_dynamics/`)

**目的**: 研究自旋波对 Hopfion 的驱动效应（论文第四章核心数据）。

### 实验设计

- **几何**: 100³ 网格，OBC + 6 面吸收边界（α=100, 5 格厚）
- **体阻尼**: α=0.001（低阻尼，保留自旋波）
- **频率**: 440 GHz
- **初始态**: `stability_Ku10k.out/m000020.ovf`（1ns 弛豫后的居中 Hopfion）
- **运行时长**: 0.5ns，autosave 50ps（11 帧）

### 四组组合

| 文件 | 源位置 | 振荡方向 | 描述 |
|------|--------|----------|------|
| `run_magnon.mx3` | x=-10nm (Region 7) | B 沿 X | Combo 1: srcX_vibX |
| `sw_srcX_vibZ.mx3` | x=-10nm | B 沿 Z | Combo 2: srcX_vibZ |
| `sw_srcZ_vibX.mx3` | z=-10nm (Region 7) | B 沿 X | Combo 3: srcZ_vibX |
| `sw_srcZ_vibZ.mx3` | z=-10nm | B 沿 Z | Combo 4: srcZ_vibZ |

### 其他文件

| 文件 | 描述 |
|------|------|
| `run_all_4combos.sh` | 顺序执行 4 组（~14h 总计） |
| `analyze_sw_4combos.py` | 综合分析: 位置漂移、核心变化、能量、扰动空间分布、扰动增长 |
| `工作日志_阶段1_方案设计.md` | 方案设计笔记（中文） |

### 仿真输出（全部完成）

| 目录 | 帧数 | Δz (nm) | dm_rms | 评价 |
|------|------|---------|--------|------|
| `run_magnon.out/` (srcX_vibX) | 11 | +2.36 | 7.72e-2 | **强耦合** |
| `sw_srcX_vibZ.out/` | 11 | +0.005 | 5.22e-4 | 无耦合 |
| `sw_srcZ_vibX.out/` | 11 | **-6.71** | **1.18e-1** | **最强耦合** |
| `sw_srcZ_vibZ.out/` | 11 | -0.001 | 3.45e-4 | 无耦合 |

### 核心发现

1. **面内振荡（vibX）有效驱动 Hopfion**，轴向振荡（vibZ）几乎无效
2. **srcZ_vibX 效果最强**: 源沿 Hopfion 轴向传播 + 面内振荡，Δz=6.7nm (0.5ns)
3. **Hopfion 被推向远离源的方向**
4. 扰动幅度差异达 2 个数量级（vibX ~0.1 vs vibZ ~3e-4）

输出: `sw_results/` 下 `hopfion_position_4combos.png`, `hopfion_core_4combos.png`, `energy_4combos.png`, `sw_perturbation_profiles.png`, `sw_perturbation_growth.png`, `analysis_summary.txt`

---

## 九、项目进展时间线

| 时间 | 里程碑 |
|------|--------|
| 2026-01-05 | 项目启动，建立 pbc_noani.mx3 基础模型 |
| 2026-01 ~ 02 | 尺寸收敛测试 → 发现固有吸引子 R=2.60nm, r=2.16nm |
| 2026-02 | 细粒度各向异性扫描 (Ku=0~25k) |
| 2026-03-10 | 漂移实验启动（旧实验控制变量不一致，结论后被推翻） |
| 2026-03-11 | 大范围 Ku 扫描（Ku=0~75k），确定 Ku_c ∈ (50k, 75k) |
| 2026-03-12 | bg_mx 10ns 长时间稳定性验证完成 |
| 2026-03-18 | 自旋波仿真方案设计，4-combo 脚本编写 |
| 2026-03-20 | 发现 J2/J4 系数符号 bug，修复全部 7 个脚本 |
| 2026-03-20 | 居中稳态验证完成（3 组全 PASS） |
| 2026-03-20 | 自旋波 4-combo 启动 |
| 2026-03-21 | 4-combo 全部完成，分析完成 |
| 2026-03-22 | freq_sweep_coarse 10点启动（100-1000GHz, B=1T, 0.2ns） |
| 2026-03-23 | unified_rerun 控制变量重跑完成，推翻旧漂移结论 |
| 2026-03-24 | **大规模目录整理**：Ku=40k 补充、Ku_c 修正为 (52k,55k)、R12r5 合并、anisotropy_sweep/large 合并为 anisotropy_study/、漂移实验 README 重写、size_convergence 图更新为三组数据集 |

---

## 十、待办事项

1. **频率扫描（进行中）**: freq_sweep_coarse 10点（100-1000GHz, B=1T）已完成；延伸 1200-3000GHz 5点（Hopfion-fnt）待跑
2. **振幅扫描（部分完成）**: 440GHz @B=0.05/0.1/0.2T 已完成，440GHz 处于死区；@f_res 振幅扫描待确定频率（Hopfion-ttz）
3. **关键频率重跑**: x9s 任务 4点 0.5ns 待跑（确认共振区间）
4. **Ku_c 细化**: 53k/54k 若论文需要精确值可补充（当前已知 Ku_c ∈ (52k, 55k)）
5. **自旋波延长仿真**: srcZ_vibX 跑 2~5ns，确认长时驱动行为

---

## 十一、文件统计

| 类别 | 数量 | 大小 |
|------|------|------|
| .mx3 仿真脚本 | ~35 | — |
| Python 脚本 | 13 | — |
| Shell 脚本 | 3 | — |
| .out 输出目录 | ~30 | — |
| OVF 文件 | ~658 | ~7.4 GB |
| 文档 (.md/.txt) | 3 | — |
| 图片 (.png) | ~17 | — |

---

## 十二、图表索引与物理意义

本节为项目中所有结论性插图建立完整索引，说明每张图的**物理含义、论文对应关系和关键读图要点**。

### 12.1 尺寸收敛测试

#### `size_sweep/size_convergence_english.png`

- **内容**：左图为大半径 R(t)，右图为管半径 r(t)，**三条曲线**分别对应 Small（R≈3.1nm，绿色）、R8r4（蓝色）、R12r5（橙色）初始态，黑色虚线为吸引子参考值。（2026-03-24 更新，添加 Small 数据集）
- **物理意义**：三种差异显著的初始尺寸（3.1nm、8nm、12nm）全部收敛到相同平衡，证明竞争交换体系存在**唯一的拓扑尺寸吸引子**。Hopfion 尺寸不是自由参数，而是由 J1/J2/J4 竞争交换的特征波长 $k^*$ 唯一确定。
- **关键读图点**：
  - R12r5 收缩最慢（~2.5ns），中途有 ~2ns 呼吸振荡
  - Small 从 3.1nm 先收缩到 2.28nm 再膨胀至 2.60nm
  - 三者最终收敛值误差 <2%，证明吸引子唯一
  - 对应论文**第三章 §3.1.1**

### 12.2 各向异性扫描

#### `anisotropy_study/size_vs_ku/results/R_r_vs_time.png`

- **内容**：6 条 R(t) 和 r(t) 曲线（Ku1 = 0, 2.5k, 5k, 7.5k, 10k, 12k J/m³），从小 Hopfion（R≈3.1nm）出发。
- **物理意义**：展示**弱各向异性对吸引子尺寸的微调效应**，同时验证小初始态与大初始态收敛到同一平衡。Ku1 增大 → R 和 r 单调减小，所有 Ku1 值下 Hopfion 均存活。
- **关键读图点**：Ku1=0 时 R≈2.6nm，Ku1=10k 时 R≈2.17nm，压缩幅度约 17%。

#### `anisotropy_study/size_vs_ku/results/summary_Rr_vs_Ku1.png`

- **内容**：末帧（t=3ns）R 和 r 对 Ku1 的汇总散点图（6点，Ku=0~12k）。
- **物理意义**：定量给出 Hopfion 平衡尺寸对各向异性的依赖关系，与 ku_critical_sweep 交叉验证。

#### `anisotropy_study/ku_critical_sweep/results/R_r_vs_time.png`

- **内容**：10 条曲线（Ku1 = 0, 5k, 10k, 20k, 30k, 40k, 50k, 52k, 55k, 58k J/m³），从 R8r4 大初始态出发。
- **物理意义**：确定**临界各向异性 Ku_c 的精确范围**。Ku=0~52k 全部收敛存活；Ku≥55k 消解。
- **关键读图点**：Ku=55k/58k 曲线缺失（消解），Ku_c ∈ (52k, 55k)。对应论文**第三章 §3.2.4 临界各向异性**。

#### `anisotropy_study/ku_critical_sweep/results/summary_Rr_vs_Ku1.png`

- **内容**：t=1ns 末帧 R 和 r 对 Ku1 的汇总图（10点），红色阴影区标注临界区域（52k~55k），Ku≥55k 标消解。
- **物理意义**：**论文核心图之一**。展示三个特征区：(1) Ku=0~10k 尺寸快速下降；(2) Ku=10k~52k 缓慢压缩区（R: 2.17→1.46nm）；(3) Ku>52k 临界区消解。对应论文**第三章图 3-5**。

### 12.3 漂移实验

> **重要更正（2026-03-24）**: 旧实验控制变量不一致（alpha=5.0 vs 0.2、R8r4 vs R3r2、不同时长），
> "bg=mz 漂移"的结论已被推翻。以下图表文档以 unified_rerun 控制变量重跑结果为准。

#### `drift_experiments/analysis/fig1_drift_comparison.png`（主结果图）

- **内容**：4 组配置的总漂移距离 |dr| vs 时间。所有曲线完全重合：前 ~1ns 上升至 ~5.75nm，之后平坦钉扎。
- **物理意义**：**背景磁化方向对漂移行为无影响**。4 组（bg=mz/mx/my, axis=z/x/y）在统一控制变量下表现完全一致。观测到的位移是初始 ansatz 到格点势极小值的一次性弛豫，非持续漂移。
- **关键读图点**：所有曲线最终位移 4.75nm（= 9.5 个格点），均为 Hopfion 轴向分量。对应论文**第三章 §3.2.3**。

#### `drift_experiments/analysis/fig2_drift_components.png`

- **内容**：2×3 子图矩阵（2 组 × xyz 三轴），展示各配置的轴分解位移。
- **物理意义**：位移严格沿 Hopfion 环面轴方向（axis=z 组漂移在 dz，axis=x 组在 dx，axis=y 组在 dy），横向分量始终为零。所有组的轴向位移大小一致（4.75nm）。

#### `drift_experiments/analysis/fig3_drift_velocity.png`

- **内容**：漂移速度 vs 时间 + 最终漂移量柱状图。
- **物理意义**：速度在前 0.5ns 有峰值后迅速衰减至零，确认是瞬态弛豫而非持续驱动。

#### `drift_experiments/analysis/trajectory_bg_mx.png`（旧实验，仍有效）

- **内容**：bg=mx 配置 10ns 长时间轨迹的 xyz 三轴分解。
- **物理意义**：**10ns 长期稳定性证据**。x 方向在前 1ns 有 +4.75nm 格点弛豫后完全钉扎，y/z 全程零漂移。与 unified_rerun 结果一致。

#### `drift_experiments/analysis/core_count_bg_mx.png`（旧实验，仍有效）

- **内容**：bg=mx 下核心细胞数 vs 时间 + 平均磁化 <mx> vs 时间。
- **物理意义**：从微观角度确认 Hopfion 结构完整性。核心细胞数从 ~900 升至 ~1900 后稳定，拓扑结构未受破坏。

### 12.4 居中稳态验证

#### `centered_stability_test/stability_results/hopfion_z_drift.png`

- **内容**：3 条 Δz(t) 曲线（Ku=0, 10k, 50k），虚线标记 ±2nm 阈值。
- **物理意义**：**筛选最优自旋波仿真初始态**。Ku=0（蓝色）有明显呼吸振荡（Δz 先降 1nm 再回升），Ku=10k（绿色）和 Ku=50k（红色）几乎平坦。三者均在 ±2nm 阈值内 → 全部 PASS。
- **关键读图点**：Ku=10k 最稳定（|Δz|<0.02nm），被选为自旋波仿真的初始态条件。对应论文**第三章 §3.3 居中稳定性验证**。

#### `centered_stability_test/stability_results/hopfion_xyz_drift.png`

- **内容**：3×3 矩阵图，行=Ku 值，列=xyz 三轴，每格一条 Δ-coordinate(t) 曲线。
- **物理意义**：全维度检验。关键观察：(1) 所有 Δx 和 Δy 的绝对值量级为 1e-6~1e-7 nm，即**机器精度级零漂移**；(2) Δz 是唯一非零分量，为 Hopfion 轴向（z）的格点弛豫位移。注意：此组实验使用 bg=mz 配置，Δz 位移与背景方向无关（已由 unified_rerun 控制变量实验证实）。

#### `centered_stability_test/stability_results/hopfion_mz_core_count.png`

- **内容**：核心细胞数（mz<0 的格点数）vs 时间，3 条曲线。
- **物理意义**：从结构完整性角度补充稳定性判据。Ku=0 核心约 2000 个格点且波动较大（±100），Ku=10k 约 900 个且平坦，Ku=50k 约 400 个且极平坦。**Ku 越大核心越小但越稳定**——各向异性提供了更强的势阱约束。

### 12.5 自旋波动力学

#### `spin_wave_dynamics/sw_results/hopfion_position_4combos.png`

- **内容**：4 子图（x/y/z 漂移 + 总位移），每子图 4 条曲线对应 4 种源-振荡组合。
- **物理意义**：**论文第四章核心图**。定量证明自旋波驱动 Hopfion 运动的**方向选择性**。srcZ_vibX（橙色）产生 z 方向 -6.7nm 位移（0.5ns），srcX_vibX（蓝色）产生 x 方向 -0.12nm 和 z 方向 +2.36nm 位移。vibZ 组合（绿色/红色）几乎无效。
- **关键读图点**：总位移图（右下）中 srcZ_vibX 远超其他组合，且 Hopfion 向远离源的方向运动（源在 z=-10nm，Hopfion 向 +z 被推开），符合辐射压力驱动机制。对应论文**第四章 §4.2 四组合对比**。

#### `spin_wave_dynamics/sw_results/energy_4combos.png`

- **内容**：系统总能量 vs 时间，4 条曲线。
- **物理意义**：区分自旋波注入的能量效率。srcZ_vibX（橙色）和 srcX_vibX（蓝色）使系统能量显著升高（+50%），且呈现振荡叠加上升趋势；vibZ 组合能量几乎不变。这证明 **vibX 模式能有效向系统注入能量**，而 vibZ 模式被 Hopfion 核心的对称性选择规则所排斥。

#### `spin_wave_dynamics/sw_results/hopfion_core_4combos.png`

- **内容**：核心细胞数 vs 时间，4 条曲线。
- **物理意义**：自旋波对 Hopfion 内部结构的扰动程度。srcZ_vibX 和 srcX_vibX 的核心数波动较大（±60），vibZ 组合基本恒定（±10）。核心数波动与位移强度正相关，说明驱动效应伴随着 Hopfion 内部磁化的再分布。

#### `spin_wave_dynamics/sw_results/sw_perturbation_growth.png`

- **内容**：全局 RMS 扰动幅度 <|Δm|> vs 时间，4 条曲线。
- **物理意义**：**最直接的耦合强度度量**。vibX 组合的扰动在 0.5ns 内增长到 0.08~0.12（约 8%~12% 的磁化偏转），vibZ 组合仅 3×10⁻⁴（0.03%），差距达两个数量级。这说明 Hopfion 与面内偏振自旋波的耦合效率远高于轴向偏振。

#### `spin_wave_dynamics/sw_results/sw_perturbation_profiles.png`

- **内容**：4 子图，每组沿传播方向和横向的一维扰动剖面（t=0.5ns 快照），虚线标注源位置和 Hopfion 中心。
- **物理意义**：展示**自旋波与 Hopfion 的空间交互模式**。srcX_vibX（左上）：沿传播方向（x 轴）可见清晰的自旋波波前，在 Hopfion 位置处散射增强形成明显峰值。srcZ_vibX（左下）：沿 z 轴同样可见强散射峰。vibZ 组合（右侧两图）：扰动极弱且空间上均匀——自旋波穿过 Hopfion 而几乎不散射。
- **关键读图点**：散射峰位于 Hopfion 中心附近，说明能量传递是局域的——自旋波"撞上"Hopfion 时发生非弹性散射，将动量转移给拓扑结构。

### 12.6 bg_mx 长时间稳定性

#### `drift_experiments/analysis/trajectory_bg_mx.png` + `core_count_bg_mx.png`

已在 §12.3 中详述。这两张图共同构成 **bg=mx 配置长期可靠性的完整证据链**：质心轨迹证明无宏观漂移，核心细胞数证明微观结构完好。对应论文**第三章 §3.2.3**。

> 最后更新: 2026-03-22
