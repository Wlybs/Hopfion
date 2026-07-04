# Centered Hopfion Stability Test

**完成日期**：2026-03-20
**bd 任务**：Hopfion-5vg（已关闭）

---

## 实验目的

自旋波驱动实验需要一个 **位于盒子中心、无自发漂移** 的 Hopfion 初始态。

背景问题：frustrated FM 体系弛豫后 Hopfion 会偏离中心（z 方向 ~4.75nm 格点弛豫），若直接用于自旋波仿真，Hopfion 会被 absorbing boundary 吸收。需验证将 Hopfion 平移居中后，在不同 Ku 值下能否在 1ns 内保持稳态（判定标准：z 漂移 < 2nm）。

同时，本实验确定了哪个 Ku 值的自发漂移最小，从而选出自旋波实验的最优初始态。

---

## 文件结构

```
centered_stability_test/
├── README.md
│
├── # 输入初始态（手动平移居中后的 OVF）
├── centered_Ku0.ovf           Ku=0 居中初始态
├── centered_Ku10k.ovf         Ku=10k 居中初始态
├── centered_Ku50k.ovf         Ku=50k 居中初始态
├── generate_centered_ovf.py   生成上述居中 OVF 的脚本
│
├── # 仿真脚本与输出
├── stability_Ku0.mx3          Ku=0 仿真脚本
├── stability_Ku10k.mx3        Ku=10k 仿真脚本
├── stability_Ku50k.mx3        Ku=50k 仿真脚本
├── stability_Ku0.out/         Ku=0 原始输出（21 OVF + table.txt）
├── stability_Ku10k.out/       Ku=10k 原始输出（21 OVF + table.txt）
├── stability_Ku50k.out/       Ku=50k 原始输出（21 OVF + table.txt）
│
├── # 分析脚本
├── analyze_centered_stability.py   漂移轨迹 + core 体素数分析
├── analyze_properties.py           几何参数(R, r) + 能量演化分析
├── run_stability_tests.sh          批量运行三组仿真
├── run_log.txt                     运行日志
│
└── stability_results/             分析结果图 + 数值摘要
    ├── stability_summary.txt      数值汇总表
    ├── hopfion_xyz_drift.png      xyz 三方向漂移轨迹（核心结果图）
    ├── hopfion_z_drift.png        z 方向漂移（论文图候选）
    ├── hopfion_mz_core_count.png  核心体素数演化（结构完整性指标）
    ├── fig_Rr_evolution.png       Hopfion 几何参数 R(t), r(t)
    ├── fig_energy_evolution.png   总能量演化 ΔE/E₀ (%)
    └── fig_magnetization.png      平均磁化分量演化
```

---

## 仿真参数

| 参数 | 值 |
|---|---|
| 网格 | 100×100×100，0.5nm/格 |
| 边界 | **PBC(1,1,1)**（与自旋波实验不同） |
| Ms | 1.5×10⁵ A/m |
| Aex | 5×10⁻¹² J/m |
| J2 系数 | −0.164 × Aex |
| J4 系数 | −0.082 × Aex |
| EnableDemag | false |
| alpha | 0.2 |
| 运行时长 | 1 ns |
| autosave | 每 50ps（共 21 帧） |
| 变量 | Ku1 = 0 / 10k / 50k J/m³ |

---

## 结果

### 漂移与结构稳定性

| 配置 | z₀ (nm) | z_final (nm) | **Δz (nm/ns)** | Core₀ | Core_final | 判定 |
|---|---|---|---|---|---|---|
| Ku=0 | 28.44 | 29.15 | **+0.704** | 1984 | 2128 | PASS（呼吸模式） |
| **Ku=10k** | 25.07 | 25.05 | **−0.019** | 920 | 908 | **PASS（极稳定）** |
| Ku=50k | 25.13 | 25.19 | **+0.062** | 388 | 404 | PASS |

x、y 方向三组均无漂移（slope ≈ 0）。

### Hopfion 几何参数（1ns 内稳定）

| 配置 | 大环半径 R (nm) | 管半径 r (nm) |
|---|---|---|
| Ku=0 | ≈ 2.60 | ≈ 2.20 |
| Ku=10k | ≈ 2.20 | ≈ 1.64 |
| Ku=50k | ≈ 1.60 | ≈ 1.24 |

Ku 越大，各向异性能越强，Hopfion 被轴向压缩，体积（core 体素数）显著减小。

### 能量演化

- **Ku=0**：ΔE/E₀ 振荡幅度达 ±4%（对应呼吸模式），结构未稳定
- **Ku=10k**：ΔE/E₀ ≈ 0%，能量完全平稳
- **Ku=50k**：ΔE/E₀ ≈ 0%，能量平稳

---

## 结论与选择依据

**选择 Ku=10k 作为自旋波实验标准初始态**，理由：

1. **自发漂移极小**：Δz = −0.019 nm/ns，比 Ku=0 小 37 倍，确保测到的 Hopfion 运动来自自旋波而非自发漂移
2. **结构稳定**：core 体素数 920→908，几乎不变；R、r 全程平稳
3. **距 Ku_c 足够远**：Ku_c ≈ 57k（来自 anisotropy_sweep_fine），Ku=10k 仅为 Ku_c 的 17%，不存在消解风险
4. **Hopfion 尺寸适中**：R=2.20nm、r=1.64nm，结构清晰，便于质心追踪分析

Ku=50k 虽然也稳定，但尺寸过小（core 仅 388 体素），且接近 Ku_c，风险较高。

---

## 下游使用

```
stability_Ku10k.out/m000020.ovf   →   spin_wave_dynamics/amplitude_sweep/m000020.ovf
                                        （自旋波 4-combo + 幅度扫描的初始态）
```

t=1ns 末帧即为充分弛豫后的稳定居中 Hopfion，直接用于自旋波驱动实验加载。
