# FM + Bulk-DMI 环境下 Hopfion 长时演化稳定性研究报告

**日期**：2026-03-07 ~ 2026-03-08
**材料体系**：FeGe（B20 手征磁体）
**仿真工具**：Mumax3 v3.11.1，Python + discretisedfield
**状态**：✅ 已成功稳定 Bloch Hopfion

---

## 1. 研究目标

在含体积 DMI（Bulk DMI）的铁磁（FM）环境中，构造 Hopfion 初始态并运行 Mumax3 时间演化，验证其在合理参数范围内能够长时间保持拓扑结构稳定（不漂移、不解体）。

---

## 2. FeGe 材料参数

| 参数 | 数值 | 说明 |
|------|------|------|
| Msat | 384 × 10³ A/m | 饱和磁化强度（276K，skyrmion 形成温度附近） |
| Aex | 8.78 × 10⁻¹² J/m | 交换刚度 |
| Dbulk | 1.58 × 10⁻³ J/m² | Bulk DMI 常数（Bloch 型，B20 结构） |
| Ku1 | 0 | 无磁晶各向异性 |
| λ | 70 nm | 螺旋周期，λ = 4πA/D |
| B_ext | 0 | 零外场 |

---

## 3. 探索过程与失败案例

### 3.1 Bulk PBC 测试（全部失败）

在 128×128×128 @ 2nm（256nm 立方体）网格上系统测试了 2×2 组合：

| 配置 | 结果 | 失败原因 |
|------|------|----------|
| PBC + Demag，B=0 | mz → 0.008（螺旋相） | FeGe 零场基态是螺旋相，FM 背景不稳定 |
| PBC + Demag，B=0.5T | mz → 1.000（均匀 FM） | B > B_sat，Hopfion 被外场"吹散" |
| PBC + No Demag，B=0 | 同上（螺旋相） | 同上 |
| No PBC + Demag，B=0 | 同上（螺旋相） | 同上 |

**关键认知**：bulk PBC 下，无论是否有退磁场，FeGe 的热力学基态始终是螺旋相（mz≈0）或均匀 FM（B>B_sat）。Hopfion 无法在 bulk 中以局部极小值形式稳定存在。

### 3.2 Sutcliffe 大圆盘（d=210nm）无冻结层

- 配置：d=210nm, h=70nm，EnableDemag=true，无 frozenspins
- 初始态：`create_hopfion_AFM.py` 环形 ansatz（R=40nm 或 R=25nm）
- 结果：mz → ~0（螺旋态），Relax() 也收敛到螺旋态
- 原因：环形 ansatz 不在 Hopfion 吸引盆内，Relax() 直接滑向螺旋态极小值

### 3.3 Khodzhaev 小圆盘（d=128nm）

- 配置：d=128nm, h=64nm，EnableDemag=true，无 frozenspins
- 初始态：create_hopfion_AFM.py 生成（R=20nm 或 R=25nm）
- 结果：mz → ~0（螺旋态）
- 原因：同上，初始 ansatz 偏离 Hopfion 能量极小值，且无边界约束

---

## 4. 文献调研

### 4.1 Khodzhaev & Turgut (2022)

> *Hopfion dynamics in chiral magnets*, J. Phys.: Condens. Matter **34**, 225805

**关键发现**：
- 在 d=128nm（≈2λ）、h=64nm（≈λ）的 FeGe 纳米圆盘中，退磁场是 Hopfion 稳定的关键
- **无退磁场** → MAP（磁单极-反磁单极对）为基态
- **有退磁场** → Hopfion 为稳定态（B=0 即可）
- 退磁场提供形状各向异性，在小圆盘中效果更显著

### 4.2 Sutcliffe (2018)

> *Hopfions in chiral magnets*, J. Phys. A: Math. Theor. **51**, 375401

**关键发现**：
- 在 d=3λ=210nm、h=λ=70nm 的 FeGe 纳米圆柱中存在稳定 Hopfion
- **必要边界条件**：顶底面 m=e₃（即 mz=1），曲面采用手征自由边界条件
- **解析近似公式（eq. 3.3）**，在柱坐标 (ρ, θ, z) 中定义：

$$\Omega = \tan(\pi z / L), \quad \Xi = \frac{(1+(2z/L)^2)\sec(\pi\rho/2L)}{L}, \quad \Lambda = \Xi^2\rho^2 + \Omega^2/4$$

$$m_x = \frac{4\Xi\rho(\Omega\cos\theta - (\Lambda-1)\sin\theta)}{(1+\Lambda)^2}$$

$$m_y = \frac{4\Xi\rho(\Omega\sin\theta + (\Lambda-1)\cos\theta)}{(1+\Lambda)^2}$$

$$m_z = 1 - \frac{8\Xi^2\rho^2}{(1+\Lambda)^2}$$

- z=±L/2（顶底面）处，公式给出 mz→1，与边界条件一致
- 使用自定义柱坐标有限差分代码（非 Mumax3），标准 Mumax3 无法完整复现手征边界条件

---

## 5. 成功方案

### 5.1 三个必要条件

经过系统排查，同时满足以下三个条件才能在 Mumax3 中稳定 Hopfion：

| 条件 | 具体实现 | 物理意义 |
|------|----------|----------|
| **(a) Sutcliffe 解析初始态** | `gen_sutcliffe_hopfion.py`（实现 eq.3.3） | 初始态在 Hopfion 能量吸引盆内 |
| **(b) 顶底层冻结边界** | `frozenspins.setRegion(1, 1)` 施加于 Layer(0) 和 Layer(Nz-1) | 近似实现 m=e₃ 边界条件，提供侧向约束 |
| **(c) EnableDemag=true** | Mumax3 默认值（不设置 `EnableDemag = false`） | 形状各向异性增强稳定性 |

### 5.2 仿真流程

```
gen_sutcliffe_hopfion.py
       ↓ 生成 hopfion_sutcliffe_analytic.ovf
run_analytic_relax.mx3
       ↓ Relax()（α=0.5，能量最小化，找局部极小）
       ↓ saveas("hopfion_analytic_relax")
       ↓ Run(2e-9, α=0.02)（低阻尼动力学验证稳定性）
       ↓ saveas("hopfion_analytic_final")
visualize_hopfion.py
       ↓ 输出 hopfion_visualization.png（拓扑确认）
```

### 5.3 仿真参数

```
SetGridSize(105, 105, 35)
SetCellSize(2e-9, 2e-9, 2e-9)
SetGeom(Cylinder(2.1e-7, 7e-8))  // d=210nm=3λ, h=70nm=λ

Msat  = 384e3
Aex   = 8.78e-12
Dbulk = 1.58e-3
Ku1   = 0
// EnableDemag = true (默认)

frozenspins.setRegion(1, 1)  // 顶底层

alpha = 0.5
Relax()
alpha = 0.02
Run(5e-9)
```

---

## 6. 结果

### 6.1 数值结果

| 量 | 数值 |
|----|------|
| mz_mean（Relax 后） | 0.3756 |
| mz_mean（2ns Run 后） | 0.3756（完全不变） |
| mz 范围 | [-1.000, +1.000] |
| mz < 0 区域占比 | 16.19%（Hopfion 核心） |
| mz < -0.5 区域占比 | 5.84% |
| 核心环半径 R（z=0 截面） | ≈50 ± 20 nm |
| E_total | −2.92 × 10⁻¹⁷ J |
| E_demag | +4.98 × 10⁻¹⁷ J |

### 6.2 可视化确认

![Hopfion 拓扑结构](hopfion_dmi_fm_stable.png)

- **左图（z=0 截面）**：同心环形结构，中心 mz=+1（蓝），外圈 mz=-1（红），符合 Bloch Hopfion 特征
- **中图（y=0 截面）**：两侧对称负 mz 核心，顶底层强制 mz=+1，与 Sutcliffe 2018 Fig.1 一致
- **右图（面内矢量场）**：Bloch 型旋转涡旋，确认手征结构

### 6.3 稳定性判据

Relax() 收敛后，以 α=0.02 运行 2ns 动力学演化，mz 均值变化 < 0.0001，判定为**动力学稳定**的局部能量极小值。

---

## 7. 关键物理认知

1. **FeGe bulk 中无法稳定 Hopfion**：零场下螺旋相是热力学基态（mz→0），有场则超过饱和场后 Hopfion 被均匀 FM 吞噬。Hopfion 必须依赖几何约束。

2. **顶底层约束是核心**：强制 mz=1 的边界条件（对应 Sutcliffe 的强垂直各向异性帽盖）是 Hopfion 存在的必要条件，等价于为螺旋态施加高度方向的约束（h=λ，刚好容纳一个螺旋周期，且不超出）。

3. **退磁场的作用**：在小圆盘（d≈2λ）中，形状各向异性使 Hopfion 比 MAP 更低能，从而取代 MAP 成为局部稳定态（Khodzhaev & Turgut 的核心贡献）。

4. **初始 ansatz 的关键性**：Sutcliffe eq.3.3 解析公式已非常接近真实 Hopfion 解，直接放入 Relax() 的吸引盆。而通用环形 ansatz（固定 R, r 参数）通常不在该吸引盆内，Relax() 会收敛到螺旋态极小值。

---

## 8. 文件清单

```
20251219_dmi_fm/
├── PROJECT_REPORT.md                          # 本报告
├── hopfion_dmi_fm_stable.png                  # Hopfion 可视化结果图
├── Sutcliffe_Bloch_Hopfion/
│   ├── gen_sutcliffe_hopfion.py               # 生成 Sutcliffe eq.3.3 初始态
│   ├── hopfion_sutcliffe_analytic.ovf         # 解析初始态 OVF
│   ├── run_analytic_relax.mx3                 # 核心仿真脚本（成功）
│   ├── visualize_hopfion.py                   # 拓扑可视化分析
│   ├── hopfion_visualization.png              # 可视化图像
│   ├── run_analytic_relax.out/
│   │   ├── hopfion_analytic_relax.ovf         # Relax 后状态
│   │   └── hopfion_analytic_final.ovf         # 2ns 动力学验证后最终状态
│   └── [其他失败尝试脚本，保留用于对比]
└── bulk_stability_test/                       # Bulk PBC 系统性测试（全部失败）
    ├── run_pbc_demag.mx3                      # PBC + Demag，B=0
    ├── run_pbc_nodemag.mx3                    # PBC + No Demag，B=0.5T
    ├── run_nopbc_demag.mx3                    # No PBC + Demag
    ├── run_nopbc_nodemag.mx3                  # No PBC + No Demag
    └── analyze_stability.py                   # 分析脚本
```

---

## 9. 参考文献

1. Sutcliffe, P. *Hopfions in chiral magnets*. J. Phys. A: Math. Theor. **51**, 375401 (2018).
2. Khodzhaev, Z. & Turgut, E. *Hopfion dynamics in chiral magnets*. J. Phys.: Condens. Matter **34**, 225805 (2022).
3. Tai, J.-S. B. & Smalyukh, I. I. *Static Hopf solitons and knotted emergent fields in solid-state noncentrosymmetric magnetic nanostructures*. Phys. Rev. Lett. **121**, 187201 (2018).
