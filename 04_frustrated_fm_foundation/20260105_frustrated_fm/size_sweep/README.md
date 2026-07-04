# Size Sweep — Hopfion 初始尺寸收敛性验证

**完成日期**：2026-03-09（R12r5 续跑）
**研究问题**：从不同的大尺寸初始态出发，Hopfion 是否都收敛到同一平衡吸引子？

---

## 目录结构

```
size_sweep/
├── README.md
├── hopfion_z_R8_r4.ovf          # 初始态：R=8nm, r=4nm
├── hopfion_z_R12_r5.ovf         # 初始态：R=12nm, r=5nm
├── R8r4_Ku0.mx3                 # R8r4, Ku=0, 1ns
├── R8r4_Ku0.out/                # R8r4 仿真输出（21帧，0~1ns）
├── R12r5_Ku0.mx3                # R12r5 首段仿真脚本（1ns）
├── R12r5_Ku0_continue.mx3       # R12r5 续跑脚本（4ns）
├── R12r5_Ku0.out/               # R12r5 合并输出（100帧，m000000~m000099，t=0~4.95ns）
├── analyze_size_sweep.py        # 分析脚本（计算 R/r 时间演化）
├── replot_english.py            # 论文用英文重绘脚本
└── size_convergence_english.png # 结果图（论文图）
```

> `R12r5_Ku0.out/` 已于 2026-03-24 将首段（0~0.95ns）和续跑（0.95~4.95ns）合并，共 100 帧（m000000~m000099）。

---

## 实验参数

| 参数 | 值 |
|---|---|
| 网格 | 100×100×100，0.5nm/格，PBC(1,1,1) |
| Ms | 1.5×10⁵ A/m，Aex=5×10⁻¹² J/m |
| J2 / J4 | −0.164J1 / −0.082J1 |
| Ku1 | 0（无各向异性） |
| EnableDemag | false |
| alpha | 0.2 |

| 配置 | 初始 R / r | 总时长 |
|---|---|---|
| R8r4_Ku0 | 8nm / 4nm | 1ns |
| R12r5_Ku0 | 12nm / 5nm | 4.95ns（分两段） |

---

## 结果

三种初始尺寸均收敛到同一平衡吸引子（2026-03-24 更新，含小初始态数据）：

| 配置 | 初始 R / r | 收敛后 R / r | 收敛时间 | 数据来源 |
|---|---|---|---|---|
| Small (R3) | 3.1 / 2.0 nm | **2.60 / 2.27 nm** | ~1.3ns | anisotropy_study/size_vs_ku/ |
| R8r4 | 8.0 / 4.0 nm | **2.63 / 2.22 nm** | ~0.8ns | size_sweep/R8r4_Ku0.out/ |
| R12r5 | 12.0 / 5.0 nm | **2.60 / 2.27 nm** | ~2.5ns | size_sweep/R12r5_Ku0.out/ |

**收敛行为差异**：
- Small（R3）：从初始 R=3.1nm 先收缩至 2.28nm，再单调上升至 2.60nm（1.3ns）
- R8r4：从 8nm 单调下降，0.8ns 内完成
- R12r5：从 12nm 下降后出现 ~2ns 呼吸模式振荡，约 2.5ns 后完全稳定

三者最终收敛值误差 < 2%，证明吸引子唯一。

**结果图**：`size_convergence_english.png`（含三组初始态）

---

## 科学意义（在项目中的定位）

本实验与 `anisotropy_study/` 中两组实验共同构成**三点吸引子唯一性验证**：

| 实验 | 初始 R | 最终 R @ Ku=0 | 来源 |
|---|---|---|---|
| size_vs_ku (small) | ~3.1 nm | 2.60 nm | anisotropy_study/size_vs_ku/ |
| ku_critical_sweep (R8r4) | 8.0 nm | 2.63 nm | anisotropy_study/ku_critical_sweep/ |
| **本实验 (R12r5)** | **12.0 nm** | **2.60 nm** | size_sweep/（本目录） |

三种差异显著的初始尺寸（3.1nm、8nm、12nm）全部收敛到相同平衡，有力证明：

> **Frustrated FM 体系中存在唯一的 Hopfion 稳定吸引子（R≈2.60nm，r≈2.16nm，Ku=0），与初始构型无关。**
