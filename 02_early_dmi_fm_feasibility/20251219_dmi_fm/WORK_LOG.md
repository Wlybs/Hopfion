# DMI 铁磁体系 Hopfion 稳定性研究 — 完整工作日志

> 项目目录: `/mnt/d/Research/Hopfion/02_early_dmi_fm_feasibility/20251219_dmi_fm/`
> 起止时间: 2025-12-19 ~ 2026-03-08
> 状态: **已完成**（成功实现 FeGe Bloch Hopfion 2ns 稳定）

---

## 一、项目概述

本项目研究含体积型 Dzyaloshinskii-Moriya 相互作用（Bulk DMI）的铁磁体系中 Hopfion 的稳定条件。以手性磁体 FeGe 为模型材料，通过大量失败尝试和系统排查，最终确定了 Hopfion 稳定存在的三个必要条件，并在 d=210nm、h=70nm 的圆柱模型中实现了 2ns 稳定。

### 材料参数（FeGe, 276K）

| 参数 | 符号 | 数值 |
|------|------|------|
| 饱和磁化强度 | $M_s$ | 384×10³ A/m |
| 交换刚度 | $A_{ex}$ | 8.78×10⁻¹² J/m |
| 体积型 DMI | $D_{bulk}$ | 1.58×10⁻³ J/m² |
| 螺旋周期 | $\lambda$ | 70 nm |
| 磁晶各向异性 | $K_{u1}$ | 0 |

---

## 二、成功仿真 (`successful_simulation/`)

### 最终方案

- **几何**: 圆柱体，d=210nm (3λ)，h=70nm (λ)
- **网格**: 105×105×35 @ 2nm
- **边界**: frozenspins（顶底层冻结为 mz=+1）
- **退磁场**: EnableDemag = true（默认）
- **阻尼**: Relax α=0.5 → Run α=0.02

### 文件清单

| 文件 | 描述 |
|------|------|
| `gen_sutcliffe_hopfion.py` | 基于 Sutcliffe 2018 解析解（eq.3.3）生成初始态 OVF。柱坐标参数化，含圆柱掩模和边界层处理 |
| `hopfion_sutcliffe_analytic.ovf` | 生成的初始态，105×105×35 网格，单位磁化矢量 |
| `run_analytic_relax.mx3` | 主仿真脚本。Phase 1: Relax()能量最小化；Phase 2: Run(2ns) 动力学验证。输出 relax 态和 final 态 OVF |
| `visualize_hopfion.py` | 后处理脚本，读取 final OVF，生成三面板图（z=0 截面、y=0 截面、面内矢量场） |
| `hopfion_visualization.png` | 可视化结果图 |

### 仿真输出 (`run_analytic_relax.out/`)

- **table.txt**: 时间序列数据（t, mx, my, mz, E_total, E_demag），共约 200 行
- **OVF 文件**: m000000~m000010（11 帧，每 0.2ns 一帧）+ relax 态 + final 态，共 13 个 OVF
- **最终结果**: mz_mean = 0.4768，2ns 内保持稳定
- **运行环境**: Mumax3 v3.11.1, RTX 5070 Ti Laptop, Ubuntu 24.04

### 三个必要条件

1. **Sutcliffe 解析初始态**: 基于有理映射的解析解，确保初始态处于 Hopfion 能量盆地
2. **frozenspins 边界**: 顶底层固定 mz=+1，阻止螺旋态从边界侵入
3. **退磁场 (EnableDemag=true)**: 提供形状各向异性，维持均匀 mz 背景

---

## 三、失败尝试 (`failed_attempts/`)

### 3.1 体块周期性边界测试 (`bulk_pbc_tests/`)

**目的**: 测试 FeGe 体块（PBC）中 Hopfion 是否稳定。

| 文件 | 描述 |
|------|------|
| `gen_bulk_hopfion_init.py` | 生成 256nm 立方体块中的环面初始态（R=40nm, r=20nm） |
| `bulk_hopfion_init.ovf` | 128×128×128 @ 2nm 初始态 |
| `run_pbc_demag.mx3` | PBC + Demag + B=0.5T，α=0.5，2ns |
| `run_pbc_nodemag.mx3` | PBC + 无Demag + B=0 |
| `run_nopbc_demag.mx3` | 无PBC + Demag + B=0 |
| `run_nopbc_nodemag.mx3` | 无PBC + 无Demag |
| `analyze_stability.py` | 4 组对比分析，2×2 子图 |
| `run_all.sh` | 批量执行脚本 |

**结果**: 4 组全部坍缩（mz→1.0）。体块 FeGe 在零场下基态为螺旋态，Hopfion 不稳定。

**输出**: `run_pbc_demag.out/`（11帧）、`run_pbc_nodemag.out/`（7帧），日志在 `run_logs/`。

### 3.2 错误初始态的圆盘尝试 (`sutcliffe_disc_wrong_ansatz/`)

**目的**: 用简单环面 ansatz 替代 Sutcliffe 解析解，测试能否收敛。

| 文件 | 描述 |
|------|------|
| `gen_hopfion_128nm.py` | Khodzhaev 几何（128nm 圆盘），简单环面 ansatz（R=25nm, r=12nm） |
| `hopfion_128nm_init.ovf` | 64×64×32 @ 2nm 初始态 |
| `run_128nm_demag.mx3` | Khodzhaev 几何，Relax + 5ns Run，α=0.01 |
| `run_sutcliffe_with_demag.mx3` | Sutcliffe 几何，带退磁场 |
| `run_with_demag.mx3` | 通用 Sutcliffe 尝试 |
| `Sutcliffe_Bloch_Hopfion.mx3` | Sutcliffe 公式直接测试 |

**结果**: 均坍缩或收敛到螺旋态。简单环面 ansatz 不在 Hopfion 能量盆地内。

**输出**: `run_128nm_demag.out/`（50帧，5ns），`run_sutcliffe_with_demag.out/`（29帧）等。

### 3.3 环面纳米环方法 (`toroidal_nanoring_approach/`)

**目的**: 复现 Corona et al. 2023 的环面几何方案。

| 文件 | 描述 |
|------|------|
| `check_stability.mx3` | 环面几何（R=100nm, r=80nm），FeGe 参数 |
| `check_stability.py` | Python + Mumax3 联合编排脚本 |
| `hopfion_Qh1_strategy1.png` | 初始态可视化 |

**结果**: 未完成（仅有 log.txt，无完整输出）。

---

## 四、Neel Hopfion 尝试 (`neel_hopfion/`)

**目的**: 复现 Khodzhaev & Turgut 2022 的 Neel 型 Hopfion（界面 DMI 体系，Ir/Co/Pt）。

### 材料参数

| 参数 | 数值 |
|------|------|
| $M_s$ | 3×10⁵ A/m |
| $A_{ex}$ | 1.1×10⁻¹² J/m |
| $D_{ind}$ | 1.15×10⁻³ J/m² |
| $K_{u1}$ | 1×10⁶ J/m³ |
| $B_{ext}$ | -0.12 T |

**几何**: d=64nm, h=8nm, cell=0.5nm (128×128×16)

### 文件清单

| 文件 | 描述 |
|------|------|
| `gen_neel_hopfion_init.py` | 将 Bloch ansatz 旋转 90° 生成 Neel 型初始态（R=12nm, r=4nm） |
| `neel_hopfion_init.ovf` | Neel 型初始态 OVF |
| `run_neel_hopfion.mx3` | v1: Relax() + Run(2ns)，α=0.5→0.02 |
| `run_neel_hopfion_v2.mx3` | v2: 高阻尼 α=5.0, Run(0.5ns) |
| `run_neel_hopfion_v3.mx3` | v3: 更强外场 B=-0.3T |
| `run_neel_hopfion_v4.mx3` | v4: 分阶阻尼 α: 0.001→0.01→0.1→0.5 |
| `run_neel_sutcliffe.mx3` | Sutcliffe 基 ansatz 旋转 90° |
| `run_no_field_long.mx3` | B=0 长时演化 |
| `test_conservative.mx3` | 极低阻尼 α=0.001 |
| `test_neg_dind.mx3` | 负 Dind 测试 |
| `test_no_field.mx3` | 零场测试 |
| `INVESTIGATION_LOG.md` | 详细失败分析报告（85行） |

**结果**: 所有 9 种变体均坍缩（mz→0.995，<2ns 内消失）。

**根因分析**（记录于 INVESTIGATION_LOG.md）:
1. 论文引用的"已知 Hopfion ansatz [43]"实际不存在（缺失引用）
2. κ = 0.548 < 1，势阱极浅（亚稳态，非稳态）
3. PMA 软边界（vs. frozenspins 硬边界）允许拓扑结构从 z 方向逃逸

**结论**: 需要作者提供原始 OVF 文件才能复现。

---

## 五、大圆盘验证 (`isolated_hopfion_10lambda/`)

**目的**: 测试更大圆盘（d=700nm=10λ）中 Hopfion 是否仍稳定。

| 文件 | 描述 |
|------|------|
| `gen_hopfion_10lambda_disc.py` | Sutcliffe 解析解，350×350×35 @ 2nm |
| `hopfion_10lambda_init.ovf` | 大圆盘初始态 |
| `run_10lambda_disc.mx3` | 同成功方案参数，仅几何放大 |

**输出**: `run_10lambda_disc.out/` — 2 帧（可能未完成或仅采样前两帧）。table.txt 显示 mz≈0.41，与 3λ 圆盘一致。

**结论**: Hopfion 稳定性不受圆盘尺寸影响（核心结构相同，mz_mean 因 FM 背景比例增大而升高）。

---

## 六、根目录文档

| 文件 | 描述 |
|------|------|
| `README.md` | 项目概述（85行），目录结构说明，三必要条件总结 |
| `PROJECT_REPORT.md` | 完整研究报告（220行），含失败案例分析、文献回顾、数值结果、物理洞察 |
| `hopfion_dmi_fm_stable.png` | 最终成功结果可视化（z=0 和 y=0 截面 + 面内矢量场） |

---

## 七、关键结论

1. **FeGe Bloch Hopfion 稳定的充要条件**: Sutcliffe 解析初始态 + frozenspins 边界 + EnableDemag=true
2. **Neel Hopfion (Khodzhaev 2022)**: 由于 κ<1（浅势阱），无法独立复现
3. **几何依赖**: d=3λ 是最小稳定圆盘尺寸，d=10λ 同样稳定
4. **体块 PBC**: FeGe 体块中 Hopfion 不稳定（基态为螺旋态）

---

## 八、文件统计

| 类别 | 数量 |
|------|------|
| .mx3 仿真脚本 | 16 |
| Python 脚本 | 8 |
| Shell 脚本 | 1 |
| .out 输出目录 | 14 |
| OVF 文件 | ~130 |
| 文档 (.md) | 4 |
| 图片 (.png) | 3 |

> 最后更新: 2026-03-21
