# FM + Bulk-DMI 环境下 Hopfion 稳定性实验

**材料体系**：FeGe（B20 手征磁体，Bulk DMI）
**状态**：✅ 已完成，Bloch Hopfion 成功稳定
**详细报告**：[PROJECT_REPORT.md](PROJECT_REPORT.md)

---

## 目录结构

```
02_early_dmi_fm_feasibility/20251219_dmi_fm/
├── README.md                          本文件
├── PROJECT_REPORT.md                  完整研究报告（含推导过程、失败案例、物理分析）
├── hopfion_dmi_fm_stable.png          最终结果图（截面可视化，确认拓扑结构）
│
├── isolated_hopfion_10lambda/         🔬 成功方案的尺寸放大测试（Bloch, FeGe）
│                                      圆柱盘 3λ→5λ(350nm)，Hopfion 离边界更远更孤立
│                                      Hopfion 本体不变（λ=70nm 决定），新增区域纯 FM 背景
│                                      gen_hopfion_10lambda_disc.py + run_10lambda_disc.mx3
│
├── neel_hopfion/                      ❌ Néel Hopfion 复现尝试（不同体系，未成功）
│                                      论文：Khodzhaev & Turgut 2022（Ir/Co/Pt，PMA 软边界）
│                                      与本项目 Bloch/FeGe 体系不同；试 9 种方案全部湮灭
│                                      失败根因见 neel_hopfion/INVESTIGATION_LOG.md
│
├── successful_simulation/             ✅ 成功方案（唯一需要关注的文件夹）
│   ├── gen_sutcliffe_hopfion.py       步骤1：生成 Sutcliffe 解析初始态 OVF
│   ├── hopfion_sutcliffe_analytic.ovf 步骤1输出：解析初始态（已生成，可直接用）
│   ├── run_analytic_relax.mx3         步骤2：Mumax3 仿真脚本（Relax + 2ns 动力学）
│   ├── run_analytic_relax.out/        步骤2输出：仿真结果
│   │   ├── hopfion_analytic_relax.ovf     Relax() 收敛后的状态
│   │   └── hopfion_analytic_final.ovf     2ns 动力学验证后的最终状态
│   ├── visualize_hopfion.py           步骤3：拓扑结构可视化分析
│   └── hopfion_visualization.png      步骤3输出：截面图（z=0, y=0 平面）
│
└── failed_attempts/                   ❌ 失败尝试存档（仅供参考，无需运行）
    ├── bulk_pbc_tests/                路线1：Bulk PBC — 全部失败
    │                                  原因：FeGe 零场基态是螺旋相，Hopfion 无法在 bulk 稳定
    ├── sutcliffe_disc_wrong_ansatz/   路线2：正确圆柱盘几何 + 错误初始态 — 全部失败
    │                                  原因：环形 ansatz 不在 Hopfion 能量吸引盆内，Relax() 收敛到螺旋态
    └── toroidal_nanoring_approach/    路线3：环形纳米环几何（Corona et al. 2023）— 未完成
                                       背景：不同文献路线，仿真未跑完，结论未知
```

---

## 成功方案三步骤

```bash
# 1. 激活虚拟环境
source /mnt/d/Research/Hopfion/hopfion/bin/activate

# 2. 生成初始态（已有 OVF 可跳过）
cd successful_simulation/
python gen_sutcliffe_hopfion.py

# 3. 运行仿真
mumax3 run_analytic_relax.mx3

# 4. 可视化结果
python visualize_hopfion.py
```

---

## 三个必要条件

缺少任意一个，Hopfion 都无法稳定：

| 条件 | 实现方式 | 为什么必要 |
|---|---|---|
| Sutcliffe 解析初始态 | `gen_sutcliffe_hopfion.py` 实现 eq.3.3 | 通用 ansatz 不在吸引盆内 |
| 顶底层冻结（frozenspins） | `frozenspins.setRegion(1,1)` | 强制 mz=1 边界，防止螺旋态侵入 |
| 退磁场开启 | `EnableDemag = true`（默认） | 形状各向异性使 Hopfion 比 MAP 更低能 |

---

## 仿真参数

| 参数 | 值 |
|---|---|
| 几何 | 圆柱盘 d=210nm (=3λ), h=70nm (=λ) |
| 网格 | 105×105×35，格点 2nm |
| Ms | 384×10³ A/m |
| Aex | 8.78×10⁻¹² J/m |
| Dbulk | 1.58×10⁻³ J/m² |
| 螺旋周期 λ | 70nm |

## 主要结果

- mz_mean（Relax 后）= 0.3756，2ns Run 后变化 < 0.0001 → 动力学稳定
- 核心环半径 R ≈ 50±20nm（z=0 截面）
- 拓扑结构：Bloch 型旋转涡旋，与 Sutcliffe 2018 Fig.1 一致
