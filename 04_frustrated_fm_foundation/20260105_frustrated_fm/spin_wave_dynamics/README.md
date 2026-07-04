# Spin Wave Dynamics — Frustrated FM Hopfion

**研究目标**：通过自旋波实现对 Frustrated FM Hopfion 的任意自由控制——建立频率→运动模式映射、振幅→速度标度律、偏振方向选择性规律，为神经形态计算等应用提供可控驱动方案。

**公共初始态**：`centered_stability_test/stability_Ku10k.out/m000020.ovf`（Q_H=1，Ku=10k 下弛豫 1ns 的稳定 Hopfion，R≈2.17nm，r≈1.64nm）

> **⚠️ Q_H 修正（2026-03-26）**：所有实验的初始态追溯链为：`hopfion_z_R8_r4.ovf`（Q_H=1）→ `ku_critical_sweep/R8r4_Ku10k.out/m000020.ovf` → `centered_Ku10k.ovf` → `stability_Ku10k.out/m000020.ovf`。数值 Hopf index 验证确认实际拓扑荷为 **Q_H=1**。

---

## 目录结构（2026-04-02 整理）

```
spin_wave_dynamics/
├── freq_sweep/                     # 频率响应扫描
│   ├── plane_wave/
│   │   ├── srcX/                   #   02ns（10频率）、05ns（4频率）、分析脚本、results/
│   │   └── srcZ/                   #   coarse(100-1000GHz,10点) + fine(25-175,1100-1500GHz,10点)，共20点，已分析
│   └── point_source/
│       ├── srcX/                   #   （待填入）
│       └── srcZ/                   #   （待填入）
│
├── amplitude_sweep/                # 幅度扫描
│   ├── plane_wave/
│   │   ├── srcX/                   #   sw_B*.out × 6，@440GHz，分析脚本，results/
│   │   └── srcZ/                   #   （待填入）
│   └── point_source/
│       ├── srcX/                   #   （待填入）
│       └── srcZ/                   #   （待填入）
│
├── drive_selection/                # 不同驱动方向/激励几何的选择性
│   ├── plane_wave/                 #   薄膜源：5组源-振动组合，方向选择性（全部完成）
│   └── point_source/               #   点源：vs 平面波对比（部分待运行）
│
├── multisource_control/            # 多源轨迹控制
│   └── baseline/                   #   三源基线：srcX/srcZ(+z)/srcZ(-z)@200GHz
│
└── docs/
    └── superpowers/specs/          #   Hall角+多源控制设计文档（Phase 2/3 参考）
```

---

## 实验1：方向选择性 (`drive_selection/plane_wave/`)

**目的**：确定自旋波振动方向与 Hopfion 的耦合强弱。

**参数**：f=440GHz, B=1T, Ku=10k, α=0.001(bulk)/100(边界), 0.5ns

**结论（已完成，2026-03-21）**：

| 组合 | \|dr\| (nm) | Δ能量 | 结论 |
|---|---|---|---|
| srcX_vibX | 2.36 | +4.15×10⁻¹⁹ J | **强耦合** |
| srcX_vibZ | 0.005 | +3.4×10⁻²¹ J | 无耦合 |
| srcY_vibX | 2.31 | +4.20×10⁻¹⁹ J | **强耦合**（面内等价） |
| srcZ_vibX | 6.71 | +2.51×10⁻¹⁹ J | **强耦合**（轴向驱动） |
| srcZ_vibZ | 0.001 | +3.2×10⁻²¹ J | 无耦合 |

**核心结论**：面内振动（vibX）耦合强，轴向振动（vibZ）无耦合。面内源等价（srcX ≡ srcY）。

结果：`drive_selection/plane_wave/results/`

---

## 实验2：频率响应扫描 (`freq_sweep/`)

**srcX 方向（数据完整，已分析）**

| 数据集 | 频率范围 | 时长 | 帧数 |
|---|---|---|---|
| `02ns/` | 100-1000 GHz（10点，步长100GHz） | 0.2ns | 21帧/频率 |
| `05ns/` | 300/400/900/1000 GHz | 0.5ns | 51帧/频率 |

**频率响应分三档**：

| 响应等级 | 频率范围 | v̄ (nm/ns) |
|---|---|---|
| 强响应 | 100-200 GHz、1000 GHz | 15-60 |
| 中等响应 | 300、700-900 GHz | 3-10 |
| 弱响应死区 | 400-600 GHz | < 2.5 |

**srcZ 方向（`freq_sweep/plane_wave/srcZ/`，数据完整，已分析，2026-04-03）**

数据：coarse 100-1000 GHz（10点，步长100GHz）+ fine 25/50/75/125/150/175/1100/1200/1300/1500 GHz（10点），共 **20个频率点**，均为 0.5ns / 10ps autosave / B=1T。

分析脚本：`freq_sweep/plane_wave/srcZ/analyze_srcZ_freq.py`，结果：`freq_sweep/plane_wave/srcZ/results/`

**完整频率响应（srcZ_vibX）**：

| 频率 (GHz) | \|dr\| (nm) | dz (nm) | v̄ (nm/ns) | 方向 | 模式 |
|---|---|---|---|---|---|
| **25** | 11.48 | -11.38 | 61.7 | -z | accelerating |
| 50 | 2.58 | -2.57 | 10.8 | -z | accelerating |
| **75** | 0.05 | -0.03 | — | — | **static（死区）** |
| **100** | 17.60 | **+17.59** | 60.8 | **+z（异常）** | steady |
| **125** | 8.29 | -8.29 | 24.8 | -z | accelerating |
| **150** | 0.63 | -0.63 | — | -z | **weak（死区）** |
| **175** | 15.41 | -15.41 | 45.9 | -z | accelerating |
| 200 | 7.39 | -7.39 | 21.7 | -z | accelerating |
| 300 | 6.95 | -6.95 | 18.6 | -z | accelerating |
| 400 | 5.05 | -5.05 | 14.0 | -z | accelerating |
| 500 | 4.99 | -4.99 | 13.6 | -z | accelerating |
| 600 | 1.44 | -1.44 | 4.9 | -z | **accelerating（局部谷）** |
| 700 | 3.09 | -3.09 | 8.6 | -z | accelerating |
| 800 | 2.81 | -2.81 | 7.9 | -z | accelerating |
| 900 | 4.57 | -4.57 | 12.7 | -z | accelerating |
| 1000 | 15.39 | -15.39 | 55.9 | -z | steady |
| **1100** | **18.15** | **-18.15** | **56.3** | -z | **steady（全频段最强）** |
| 1200 | 2.96 | -2.96 | 8.1 | -z | accelerating |
| 1300 | 0.86 | -0.85 | 2.5 | -z | **weak（死区）** |
| 1500 | 9.02 | -9.02 | 25.3 | -z | accelerating |

**核心结论**：

1. **主驱动方向**：srcZ_vibX 几乎全部沿 z 轴运动（dx ≈ 0），与 srcX_vibX（+z）相比，srcZ 驱动为 **-z 方向**，实现双向 z 轴控制。

2. **100 GHz 异常**：唯一呈 +z 方向的频率点（17.6nm），与其他频率 -z 运动相反，可能对应不同本征模式（有待进一步分析）。

3. **强响应峰（≥10nm）**：25 GHz、100 GHz(+z)、125 GHz、175 GHz、1000 GHz、**1100 GHz（最强，18.1nm）**。

4. **死区**：75 GHz（静止）、150 GHz（极弱）、600 GHz（局部谷）、1300 GHz（骤降后）。

5. **幅度扫描最优频率**：**1100 GHz**（全频段最大位移 18.1nm，稳定 -z 运动）。

**所有运动方向：dz >> dx（θ_H ≈ 1°），与 srcX 的 90° Hall 偏转截然不同——Magnus 力在轴向激励下几乎不产生横向偏转。**

结果文件（`freq_sweep/plane_wave/srcX/results/` 和 `freq_sweep/plane_wave/srcZ/results/`）：

| 文件 | 内容 |
|---|---|
| `displacement_srcZ.png` | 强/中/弱三组 dz(t) 轨迹 |
| `freq_response_map.png` | 频率响应谱（\|dr\|、速度、加速度柱状图） |
| `direction_map.png` | dz 方向图（红=+z 异常，蓝=-z 正常）+ \|dr\| 折线谱 |
| `motion_summary_srcZ.txt` | 20点完整数值汇总表 |

---

## 实验3：幅度扫描 (`amplitude_sweep/`)

**参数**：srcX_vibX, f=440GHz, Ku=10k, 0.5ns，B=0.05/0.1/0.2/0.5/1.0/2.0 T（全部完成）

**标度律**：v_perp ∝ B^n（n > 1，非线性）。

分析：`amplitude_sweep/plane_wave/srcX/analyze_amplitude_scaling.py`，结果：`amplitude_sweep/plane_wave/srcX/results/`

---

## 实验4：拓扑 Hall 角定量表征

**分析脚本**：
- `freq_sweep/plane_wave/srcX/analyze_hall_angle.py`：θ_H(f)
- `amplitude_sweep/plane_wave/srcX/analyze_hall_angle_amplitude.py`：θ_H(B)

**核心结论（2026-03-27）**：有效驱动范围内 θ_H ≈ 85-90°，拓扑保护，不随频率或幅度显著变化。

bd 任务：Hopfion-rt4.1

---

## 实验5：多源轨迹控制 (`multisource_control/`)

**Phase 1 基线（`baseline/`，部分完成）**：

| 配置 | θ_H | 位移 | 状态 |
|---|---|---|---|
| srcX @ 200GHz | 87.4° | 2.51 nm | 完成 |
| srcZ(+z) @ 200GHz | 1.2° | 7.39 nm | 完成 |
| srcZ(-z) @ 200GHz | — | — | 脚本就绪，待运行 |

分析：`multisource_control/baseline/analyze_baselines.py`

**Phase 2/3**：双源组合 + 慢相位调制圆形轨迹（规划中）。

参考设计文档：`docs/superpowers/specs/2026-03-27-hall-effect-and-multisource-control-design.md`

bd 任务：Hopfion-rt4.2

---

## 对称性分析：独立激励配置

Hopfion 环面位于 xOy 平面，绕 z 轴旋转对称（C₄ᵥ）：

| 配置 | 物理含义 |
|---|---|
| srcX_vibX（≡ srcY_vibX） | 面内自旋波 → 驱动面内平移，θ_H ≈ 87-90° |
| srcZ_vibX | 轴向自旋波 → 驱动轴向平移，θ_H ≈ 1° |

---

## 待做事项

| 优先级 | 任务 | bd |
|---|---|---|
| ~~P1~~ | ~~srcZ 全频段系统分析~~ | ~~Hopfion-r35~~ **已完成（2026-04-03）** |
| P1 | 能量吸收谱 dE/dt vs f（数据已有） | Hopfion-duo |
| P1 | 100/200/500GHz 延长到 0.5ns | Hopfion-x9s |
| P2 | 频率延伸 1200-3000GHz | Hopfion-fnt |
| P2 | B 阈值精确定位 | Hopfion-czs |
| P2 | 幅度扫描 @ 共振频率 | Hopfion-ttz |
| P3 | rt4.2 Phase 2/3：双源组合 + 圆形轨迹 | Hopfion-rt4.2 |

---

## 更新记录

| 日期 | 内容 |
|---|---|
| 2026-03-21 | direction_coupling 5-combo 完成，vibX 强耦合，vibZ 无耦合 |
| 2026-03-25 | amplitude_sweep 6点完成；撤销"440GHz死区"结论 |
| 2026-03-26 | freq_sweep 运动模式分析完成（02ns+05ns）；确立 Magnus 力主导结论 |
| 2026-03-27 | θ_H(f) 和 θ_H(B) 分析完成；srcZ 频率扫描完成；多源基线 Phase 1 |
| 2026-04-02 | **目录重组**：整合为4主文件夹（freq_sweep/amplitude_sweep/drive_selection/multisource_control/）；各主文件夹统一采用 plane_wave/ + point_source/ 子目录命名；删除 deviceB_200GHz 脚本包（未运行）和过程文档 |
| 2026-04-03 | **srcZ 完整频率分析**：coarse+fine 共20点（25-1500GHz），分析脚本 `analyze_srcZ_freq.py`，3张图+汇总表。核心结论：1100GHz 全频段最强（18.1nm，-z）；100GHz 唯一 +z 异常；死区 75/150/600/1300GHz；幅度扫描推荐频率 1100GHz |
