# 04_spin_wave_plane — 平面源自旋波驱动

公共初始态：`02_frustrated_fm_stability/stability_Ku10k.mx3` 输出的 m000020.ovf。

## 物理主题

- **方向选择性**：vibX 强耦合 / vibZ 无耦合 / srcX≡srcY（5 组 drive_selection 实验）
- **srcX 频率响应**（02ns 10 频率 + 05ns 4 频率，共 14 runs）：100-200/1000 GHz 强响应，400-600 GHz 死区
- **srcZ 频率响应**（coarse 10 + fine 10 = 20 频率）：1100 GHz 最强 -18.1 nm，多个死区
- **幅度扫描 srcX @440 GHz**（6 点 B=0.05–2.0 T）：旧 v∝B¹·⁹⁹ 拟合**已推翻**（数据不足，Bc∈(0.1,0.2)T 方向反转阈值未精确定位）
- **幅度扫描 srcZ @1100 GHz**（6 点）：cron 跑，可能部分缺失
- **单源双向 z 可控**：srcX→+z, srcZ→-z

## 脚本清单

| 文件 | 功能 |
|---|---|
| `sw_srcX_vibX.mx3` | 方向选择：srcX 位置 × X 方向振动（强耦合代表）|
| `sw_srcX_vibZ.mx3` | 方向选择：srcX × Z 方向振动 |
| `sw_srcZ_vibX.mx3` | 方向选择：srcZ × X 方向振动 |
| `sw_srcZ_vibZ.mx3` | 方向选择：srcZ × Z 方向振动（无耦合代表）|
| `freq_sweep_srcX_1000GHz.mx3` | srcX 频率扫描代表点（1000 GHz 强响应）|
| `freq_sweep_srcZ_1000GHz.mx3` | srcZ 频率扫描代表点 |
| `amplitude_sweep_srcX_B1T.mx3` | srcX @440 GHz 幅度扫描代表点 B=1T |
| `analyze_amplitude_scaling.py` | 幅度-位移标度律拟合（含旧 v∝B² 已推翻分析）|
| `analyze_hall_angle_amplitude.py` | Hall 角 vs 幅度分析 |

## 当前状态

- drive_selection: 5 runs 完成
- freq_sweep srcX: 14 runs 完成（02ns 10 + 05ns 4）
- freq_sweep srcZ: 20 runs 完成
- amplitude_sweep srcX @440GHz: 6 runs 完成
- amplitude_sweep srcZ @1100GHz: cron 中（可能不全）

## 原始数据位置

`20260105_frustrated_fm/spin_wave_dynamics/{drive_selection, freq_sweep, amplitude_sweep}/plane_wave/`
