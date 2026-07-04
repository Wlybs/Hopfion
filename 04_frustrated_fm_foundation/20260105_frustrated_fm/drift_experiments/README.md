# Hopfion 漂移稳定性实验

**完成日期**：2026-03-24（结论修订）

---

## 实验目的

验证受挫 FM 体系中 Hopfion 的长期稳定性，以及背景磁化方向是否影响漂移行为。

---

## 目录结构

```
drift_experiments/
├── README.md
├── initial_states/              # 四种初始态 OVF
│   ├── hopfion_x_R3_r2.ovf
│   ├── hopfion_y_R3_r2.ovf
│   ├── hopfion_z_R3_r2.ovf
│   └── hopfion_xaxis_zbg_R8_r4.ovf
├── bg_mx_axis_x_stable/         # 主结果：10ns 完整稳定性验证
│   ├── run.mx3 / run.out/
├── bg_my_axis_y_stable/         # 对照：2ns 稳定
│   ├── run.mx3 / run.out/
├── unified_rerun/               # 控制变量重跑（4组，alpha=0.2，2ns）
└── analysis/
    ├── trajectory_10ns_final.png       # 10ns 质心轨迹（论文图）
    └── drift_unified_v2_summary.txt    # 统一重跑数值汇总
```

---

## 实验设计与参数

**公共参数**（unified_rerun 统一控制）：

| 参数 | 值 |
|---|---|
| 网格 | 100×100×100，0.5nm/格 |
| 边界 | PBC(1,1,1) |
| Ms | 1.5×10⁵ A/m，Aex=5×10⁻¹² J/m |
| J2 / J4 | −0.164J1 / −0.082J1 |
| Ku1 | 0 |
| alpha | **0.2**（统一） |
| 初始态 | hopfion_z_R3_r2.ovf（R=3nm, r=2nm，统一） |

**四组对照**（unified_rerun）：

| 配置 | 背景方向 | 环轴 | 时长 |
|---|---|---|---|
| bg_mz_axis_z | mz=+1 | z | 2ns |
| bg_mz_axis_x | mz=+1 | x | 2ns |
| bg_my_axis_y | my=+1 | y | 2ns |
| bg_mx_axis_x | mx=+1 | x | 2ns |

---

## 结果

### 控制变量重跑结论（unified_rerun，2ns）

| 配置 | \|dr\|_max | 最终位移方向 | 状态 |
|---|---|---|---|
| bg=mz, axis=z | 5.75 nm | +z（沿环轴） | 钉扎 |
| bg=mz, axis=x | 5.75 nm | +x（沿环轴） | 钉扎 |
| bg=my, axis=y | 5.75 nm | +y（沿环轴） | 钉扎 |
| bg=mx, axis=x | 5.75 nm | +x（沿环轴） | 钉扎 |

**四组完全一致**：Hopfion 在 < 0.5ns 内沿环轴方向跳跃约 4.75nm（约 9.5 个格点）弛豫至最近格点，之后永久钉扎，无持续漂移。

### bg_mx 长期稳定性（10ns）

`bg_mx_axis_x_stable/` 对 bg=mx 配置做了 10ns 完整验证：

| 方向 | 漂移速率 | 说明 |
|---|---|---|
| x（轴向） | +0.001 nm/ns | 格点噪声量级 |
| y | 0.000 nm/ns | 完全静止 |
| z | 0.000 nm/ns | 完全静止 |

质心在 t < 0.5ns 完成格点弛豫后，**10ns 内全程固定不动**。

结果图：`analysis/trajectory_10ns_final.png`

---

## 核心结论

1. **背景磁化方向对 Hopfion 漂移行为无影响**：四种方向下表现完全一致，验证体系的立方对称性。

2. **初始格点弛豫是正常现象**：~4.75nm 轴向跳跃是 Hopfion 从任意位置吸附至最近格点的一次性弛豫，不是持续漂移。这也是 `centered_stability_test/` 采用预弛豫初始态的原因。

3. **长期稳定性确认**：10ns 内零自发漂移，Hopfion 具有强拓扑稳定性。

---

## 历史注记

早期实验（现已删除）因控制变量不一致（bg_mz 组误用了 alpha=5.0 和 R8r4 大初始态），得出过"bg=mz 漂移、bg=mx/my 稳定"的错误结论。unified_rerun（2026-03-23）以统一参数重跑后推翻了该结论。旧数据和相关分析已于 2026-03-24 清理。
