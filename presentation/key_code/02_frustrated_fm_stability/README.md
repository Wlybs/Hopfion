# 02_frustrated_fm_stability — 竞争交换 FM Hopfion 稳定性

体系：100³ 格点, 0.5 nm/cell, PBC(1,1,1), Ms=1.5e5, Aex=5e-12, J2=-0.164·J1, J4=-0.082·J1，无 DMI。

## 物理主题

- 固有吸引子：R8r4 / R12r5 初始 → 都收敛到 R=2.60 nm (Ku=0)
- 居中稳态：Ku=0/10k/50k 三组 1 ns 都通过稳态判据（漂移 <2 nm）
- Ku=10k 选为后续自旋波仿真的初始态（最稳，z 漂移 -0.019 nm）
- Ku 临界趋势：Ku 增大 → Hopfion 收缩 → R8r4 体系 ~52–55k 区间坍塌（13 点扫描）
- 拓扑荷：当前体系仅 Q_H=1 验证；Q_H=2/4 从未仿真

## 脚本清单

| 文件 | 功能 |
|---|---|
| `generate_centered_ovf.py` | 居中 Hopfion 初始态 OVF 生成 |
| `size_sweep_R8r4_Ku0.mx3` | 尺寸扫描 R8r4 初始 → 吸引子 |
| `size_sweep_R12r5_Ku0.mx3` | 尺寸扫描 R12r5 初始 → 吸引子 |
| `stability_Ku0.mx3` | 居中稳态 Ku=0（呼吸模式）|
| `stability_Ku10k.mx3` | 居中稳态 Ku=10k（最稳，SW 初始态来源）|
| `stability_Ku50k.mx3` | 居中稳态 Ku=50k |
| `compute_qh_timeseries.mx3` | Hopf 拓扑荷密度时序计算 |
| `ku_critical_R8r4_Ku50k.mx3` | Ku 临界扫描代表点（完整 13 点见原始目录）|
| `size_vs_ku_Ku0.mx3` | R(Ku) 依赖扫描代表点（完整 6 点见原始目录）|
| `analyze_sweep_large.py` | Ku 扫描后处理分析 |

## 当前状态

- size_sweep: 2 runs 完成
- centered_stability: 3 runs 完成（Ku=0/10k/50k）
- ku_critical_sweep: 13 runs 完成（Ku=0/5k/10k/20k/30k/40k/50k/52k/55k/56k/57k/58k）
- size_vs_ku: 6 runs 完成
- Q_H=1 验证完成；Q_H=2/4 未启动

## 原始数据位置

- `20260105_frustrated_fm/size_sweep/`
- `20260105_frustrated_fm/centered_stability_test/`
- `20260105_frustrated_fm/anisotropy_study/ku_critical_sweep/`
- `20260105_frustrated_fm/anisotropy_study/size_vs_ku/`
