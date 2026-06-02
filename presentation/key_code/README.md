# Hopfion 项目代码包

阅读型代码包，对应吴佳乐 2026-06-02 给导师的汇报 PPT。

## 项目背景

Hopfion 3D 磁性拓扑结构的微磁学仿真（mumax3），聚焦 **Frustrated FM 体系**（无 DMI，竞争交换）：

1. Frustrated FM Hopfion 稳定性（稳态尺寸 / Ku 临界 / Q_H 验证 / 漂移）
2. 自旋波驱动 Hopfion 动力学（平面源 / 点源 / 多源切换）
3. LIF 神经元仿真

## 目录索引

| 目录 | 主题 |
|---|---|
| `00_shared_libs/` | 共享分析库（所有子目录依赖）|
| `02_frustrated_fm_stability/` | Frustrated FM 稳定性（稳态尺寸、Ku 临界、Q_H）|
| `03_drift/` | Hopfion 漂移（含被推翻的旧结论）|
| `04_spin_wave_plane/` | 平面源自旋波驱动 |
| `05_spin_wave_point/` | 点源自旋波驱动 |
| `06_multisource_freq_switch/` | 双向 z 控制 / freq_switch（含 v3 0.91 ns 坍塌）|
| `08_lif_neuron/` | LIF 神经元仿真（Phase 1 PASS / Phase 2 FAILED）|
| `09_old_simulations/` | 旧版本对标（系数错误教训）|
| `figures/` | PPT 用关键分析图 |

每个子目录有独立 README。

## 数据排除

本包不含：
- `*.out/` 仿真输出（含 `.ovf` 帧、`table.txt`、`log.txt`）— 体积过大
- 毕设 LaTeX 章节 `bishe/`
- bd / mempalace 数据库
- DMI-FM (FeGe) 研究 — 本次汇报范围外
- Wang 2019 STT 复现 — 本次汇报范围外

如需复现：联系作者获取完整数据快照。

## 共享库使用

所有 Python 分析脚本依赖 `00_shared_libs/`：

```bash
export PYTHONPATH=$(pwd)/00_shared_libs:$PYTHONPATH
python <subdir>/<script>.py
```

需要 Python 3 + numpy/scipy/matplotlib/discretisedfield。
项目专用 venv：`/mnt/d/Research/Hopfion/hopfion/bin/activate`。

## 仿真总数

Frustrated FM 体系下约 163 个 `*.out/` 仿真目录（去掉 DMI-FM 与 STT 后）。本包代表性收 ~40 个 `.mx3` 与 ~10 个分析脚本。完整数据见 `/mnt/d/Research/Hopfion/`。
