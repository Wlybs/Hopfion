# 05_spin_wave_point — 点源自旋波驱动

点源：`DefRegionCell(7, 30, 50, 50)`，单格 0.5 nm³，B_amp=500 T（对比平面源 B_amp=1 T 薄片层）。

## 物理主题

- **srcX 点源 freq sweep**（10 频率）：700 GHz 最强 5.71 nm，全频段 +z，**死区消失**（对比平面源 400-600 GHz 死区），Hall 角 69-89°
- **srcZ 点源 freq sweep**（10 频率）：800 GHz 最强 -7.31 nm，方向分布复杂（6+z/3-z），Hall 角 9-40°（对比平面源 ~1°）
- **amplitude sweep @1100 GHz**：B100/200/300/400 完成；**B500 停在 0.433 ns 未续跑；B700/B1000/B2000 未跑**
- **核心结论**：振荡方向选择性、Hall 角等本质由 Hopfion 拓扑结构决定，不依赖激励几何；点源改变共振频率分布细节

## 脚本清单

| 文件 | 功能 |
|---|---|
| `freq_sweep_srcX_point_1000GHz.mx3` | srcX 点源频率扫描代表点 |
| `freq_sweep_srcZ_point_1000GHz.mx3` | srcZ 点源频率扫描代表点 |
| `amplitude_sweep_point_1100GHz_B500.mx3` | 点源幅度扫描 B=500，**停在 0.433 ns** |
| `amplitude_sweep_point_1100GHz_B500_continue.mx3` | B500 续跑尝试 |
| `analyze_point_source_freq.py` | 点源频率响应分析 |

## 当前状态

- srcX freq sweep: 10 runs 完成（B 设备数据迁回 2026-04-09）
- srcZ freq sweep: 10 runs 完成
- amplitude sweep: 4/7 完成 + 1 中断 + 3 未跑（B700/1000/2000）

## 原始数据位置

`20260105_frustrated_fm/spin_wave_dynamics/{freq_sweep, amplitude_sweep}/point_source/`
