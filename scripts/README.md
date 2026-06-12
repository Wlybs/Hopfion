# Hopfion 共享分析脚本库

**路径**：`/mnt/d/Research/Hopfion/scripts/`

所有子项目的**可复用分析功能**集中在此目录。编写新分析脚本前，必须先查阅本 README，确认所需功能是否已有实现。

---

## 使用方式

```python
import sys
sys.path.insert(0, "/mnt/d/Research/Hopfion/scripts")
from hopfion_analysis import hopfion_centroid, compute_Rr, extract_trajectory
```

---

## 脚本索引

### `hopfion_analysis.py` — Hopfion 核心物理量提取

**功能**：从 Mumax3 输出的 OVF 文件中提取 Hopfion 的位置、尺寸和时间序列。

#### 函数一览

| 函数 | 功能 | 返回 |
|---|---|---|
| `hopfion_centroid(field, method)` | 单帧质心坐标 | `np.array([cx, cy, cz])` (nm) |
| `core_count(field)` | 核心体积（mz<0 格点数） | `int` |
| `compute_Rr(field)` | 单帧大半径 R 和管半径 r | `(R_nm, r_nm)` |
| `extract_trajectory(out_dir, dt_ns)` | 整个序列的质心轨迹 | `list of (t_ns, centroid)` |
| `extract_Rr_series(out_dir, dt_ns)` | 整个序列的 R/r 时间演化 | `list of (t_ns, R, r)` |
| `load_ovf_series(out_dir, dt_ns, func)` | 通用 OVF 批量加载框架 | `list of (t_ns, result)` |
| `hopfion_phase_correlation(field1, field2)` | 两帧间相位相关位移（FFT法，抗自旋波噪声） | `np.array([dx, dy, dz])` (nm) |
| `extract_trajectory_phase_correlation(out_dir, dt_ns)` | 序列位移轨迹（相位相关，每帧vs第0帧） | `list of (t_ns, shift_nm, core_cnt)` |
| `compute_hall_angle(traj, axis, skip)` | Hall 角 theta_H（度）+ 误差 + 有效性判定 | `dict` |

---

#### 原理详解

**`hopfion_centroid` — 质心计算**

两种方法：

- `method="weighted"`（**推荐**）：对全场每个格点赋权重 `w = max(1 - mz, 0)`，mz=-1 处权重最大（=2），mz=+1 处权重=0。用加权平均计算质心，亚格点精度，对小位移敏感。

- `method="threshold"`：取 `mz < min(mz) + 0.05` 的格点做几何中心，精度受格点离散化限制（最小分辨率 = 格点间距），适合快速估算。

**`compute_Rr` — 大半径 R 和管半径 r**

分两步：

1. **大半径 R**：取核心格点（`mz < min(mz) + 0.05`）的 xy 坐标，经 PBC 展开后做最小二乘圆拟合，圆半径即 R。
2. **管半径 r**：用 marching cubes 提取 `mz=0` 等值面（Hopfion 管的外壳），计算每个表面顶点到环中轴（以 R 为半径的圆）的欧氏距离，取中位数为 r。

**PBC 展开**（内部函数 `_pbc_unwrap_xy`）：将周期边界体系中可能跨边界分裂的点云折叠到质心附近，确保圆拟合不受 box 边界影响。

---

#### 已知使用场景

| 子项目 | 使用的函数 | 用途 |
|---|---|---|
| `size_sweep/replot_english.py` | `compute_Rr` | R/r 收敛曲线 |
| `anisotropy_study/ku_critical_sweep/analyze_sweep_large.py` | `compute_Rr` | Ku 扫描平衡尺寸 |
| `spin_wave_dynamics/direction_coupling/analyze_sw_4combos.py` | `hopfion_centroid` | Hopfion 位移轨迹 |
| `spin_wave_dynamics/amplitude_sweep/` | `hopfion_centroid`, `core_count` | B 幅度响应分析 |
| `spin_wave_dynamics/freq_sweep_dense/analyze_motion_modes.py` | `extract_trajectory_phase_correlation` | 频率扫描运动模式分析 |

---

### `resonance_analysis.py` — 共振频率分析工具

**功能**：三种互补方法定位自旋波-Hopfion 共振频率。

| 函数 | 方法 | 输入 | 返回 |
|---|---|---|---|
| `velocity_response_spectrum(sweep_dir, freqs, dt)` | v̄(f) 速度响应谱 | 频率扫描 .out 目录 | `{freq: v̄}` |
| `energy_absorption_spectrum(sweep_dir, freqs)` | 后瞬态总能量趋势，旧名兼容，不能单独称净吸收 | 频率扫描 table.txt | `{freq: dE/dt}` |
| `generate_pulse_mx3(path, src, vib, sigma, B)` | 脉冲 mx3 生成 | 参数 | .mx3 文件 |
| `generate_cw_mx3(path, freq, src, vib, B)` | 连续波 mx3 生成 | 参数 | .mx3 文件 |
| `pulse_eigenmode_analysis(out_dir, dt)` | 脉冲后 FFT 本征模谱 | 脉冲仿真 .out | `{freqs, psd_dx/dy/dz, psd_E}` |
| `load_mumax_table(path)` | 加载 table.txt | table.txt 路径 | `{列名: ndarray}` |
| `generate_sinc_ringdown_mx3(path, axis, cutoff_ghz, b0_t)` | uniform sinc 弱脉冲 table-only mx3 | 参数 | .mx3 文件 |
| `ringdown_fft_from_table(table_path, columns)` | 对 table 平均磁化/能量做 FFT | table.txt | `{freqs_ghz, psd_*}` |
| `find_fft_peaks(freqs, power)` | 从功率谱提取候选峰 | FFT 频率轴和功率 | `list[dict]` |
| `estimate_peak_metrics(freqs, power, target)` | 目标峰位、数值 FWHM 与 Q | 频率轴、功率谱 | `dict` |
| `fit_power_law(amplitudes, responses)` | 弱场响应幂律拟合 | 正幅度与响应数组 | `dict` |
| `evaluate_mode_localization(...)` | Hopfion 局域模式阶段门 | 掩膜/背景功率 | `dict` |
| `generate_circular_burst_mx3(...)` | 高斯包络圆偏微波 mx3 | 旋向、载频、场强 | `.mx3` 文件 |
| `generate_wavefield_mx3(...)` | 均匀背景点源/平面源二维切片仿真 | 几何、频率、范数匹配场强 | `.mx3` 文件 |
| `coherent_amplitude(t, signal, frequency)` | 锁相提取指定驱动频率的相干幅值 | 时间序列 | `float` |
| `wavevector_power_spectrum(mode, cell_size_nm)` | 复模态二维 FFT、径向 k 谱与熵指标 | 二维复振幅 | `dict` |

#### `ringdown_fft_from_table` 使用场景

`hopfion_eigenmode_ringdown_20260608` 使用该函数分析 weak sinc pulse 后的 table-only 自由振荡谱。它只处理 `table.txt` 中的 `mx/my/mz/E_total`，不读取 OVF，因此适合快速区分“候选固有频率”和连续自旋波频扫中的“强驱动窗口”。

---

### 其他脚本（原有）

| 脚本 | 功能 |
|---|---|
| `create_hopfion_AFM_v2.py` | 生成 Hopfion 初始态 OVF，支持任意轴向（axis=x/y/z）、中心偏移、AFM 背景模式 |
| `draw_afm_new.py` | AFM 磁化结构可视化 |
| `param_sweep.py` | 参数扫描任务生成 |
| `run_and_log.py` | 仿真运行与日志记录 |

---

## 新增脚本规范

向本目录添加新脚本时：
1. 文件名描述功能，不用参数缩写（`hopfion_analysis.py` ✅，`Rr_calc.py` ❌）
2. 模块顶部写清楚**用途、用法示例、依赖**
3. 同步更新本 README 的脚本索引表
4. 同步更新 CLAUDE.md 中的 C-7 条款（如有新增类别）
