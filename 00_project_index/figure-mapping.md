# Figure Mapping — 图表-仿真-脚本对应表

> 修改任何论文图表前必须查阅此文件。图表来源如有变化，请同步更新此表。

## 第三章：Hopfion 稳定性

| 图号 | 文件名 | 来源仿真目录 | 绘图脚本 | 说明 |
|------|--------|------------|---------|------|
| Fig.3-1 | `fig3-1_fege_hopfion_stable.png` | `02_early_dmi_fm_feasibility/20251219_dmi_fm/successful_simulation/` | 手动截图/visualize | FeGe Hopfion 稳定态 |
| Fig.3-3 | `fig3-3_size_convergence.png` | `04_frustrated_fm_foundation/20260105_frustrated_fm/size_sweep/` | `size_sweep/` 内分析脚本 | 尺寸收敛性验证 |
| Fig.3-4a | `fig3-4_drift_comparison.png` | `04_frustrated_fm_foundation/20260105_frustrated_fm/drift_experiments/` | `95_shared_scripts/hopfion_analysis.py` | 漂移对比（多条件） |
| Fig.3-4b | `fig3-4_drift_trajectory_10ns.png` | `04_frustrated_fm_foundation/20260105_frustrated_fm/drift_experiments/` | `95_shared_scripts/hopfion_analysis.py` | 10ns 漂移轨迹 |
| Fig.3-5 | `fig3-5_drift_detail.png` | `04_frustrated_fm_foundation/20260105_frustrated_fm/drift_experiments/` | `95_shared_scripts/hopfion_analysis.py` | 漂移细节 |
| Fig.3-6 | `fig3-6_anisotropy_Rr_vs_time.png` | `04_frustrated_fm_foundation/20260105_frustrated_fm/anisotropy_study/` | `anisotropy_study/` 内分析脚本 | Ku 对 R/r 的影响随时间 |
| Fig.3-7 | `fig3-7_anisotropy_summary.png` | `04_frustrated_fm_foundation/20260105_frustrated_fm/anisotropy_study/` | `anisotropy_study/` 内分析脚本 | 各向异性参数汇总 |
| Fig.3-8 | `fig3-8_centered_z_drift.png` | `04_frustrated_fm_foundation/20260105_frustrated_fm/centered_stability_test/` | `centered_stability_test/` 内脚本 | 中心化后 z 漂移 |
| Fig.3-9 | `fig3-9_centered_core_count.png` | `04_frustrated_fm_foundation/20260105_frustrated_fm/centered_stability_test/` | `centered_stability_test/` 内脚本 | Core voxel 数随时间 |

## 第四章：自旋波动力学

| 图号 | 文件名 | 来源仿真目录 | 绘图脚本 | 说明 |
|------|--------|------------|---------|------|
| Fig.4-freq-1 | `displacement_all_freq.png` | `spin_wave_dynamics/freq_sweep/02ns/` | `freq_sweep/analyze_motion_modes.py` | 各频率位移轨迹 |
| Fig.4-freq-2 | `velocity_all_freq.png` | `spin_wave_dynamics/freq_sweep/02ns/` | `freq_sweep/analyze_motion_modes.py` | 各频率速度 |
| Fig.4-freq-3 | `hall_angle_vs_freq.png` | `spin_wave_dynamics/freq_sweep/` | `freq_sweep/analyze_motion_modes.py` | Hall 角 vs 频率 |
| Fig.4-freq-4 | `motion_mode_map.png` | `spin_wave_dynamics/freq_sweep/02ns/` | `freq_sweep/analyze_motion_modes.py` | 运动模式分类图 |
| Fig.4-amp-1 | `hall_angle_vs_amplitude.png` | `spin_wave_dynamics/amplitude_sweep/` | `amplitude_sweep/analyze_amplitude_sweep.py` | Hall 角 vs 振幅 |
| Fig.4-amp-2 | `trajectory_vs_B.png` | `spin_wave_dynamics/amplitude_sweep/` | `amplitude_sweep/analyze_amplitude_sweep.py` | 轨迹 vs 场强 |
| Fig.4-amp-3 | `scaling_440GHz.png` | `spin_wave_dynamics/amplitude_sweep/` | `amplitude_sweep/analyze_amplitude_scaling.py` | 440GHz 标度律 |
| Fig.4-dir-1 | `direction_coupling/results/` | `spin_wave_dynamics/direction_coupling/` | `direction_coupling/analyze_sw_4combos.py` | 方向耦合（4组合） |
| Fig.4-ms-1 | `baseline_trajectories.png` | `spin_wave_dynamics/multisource_baseline/` | `multisource_baseline/analyze_baselines.py` | 多源基线轨迹 |
| Fig.4-ms-2 | `direction_rose_plot.png` | `spin_wave_dynamics/multisource_baseline/` | `multisource_baseline/analyze_baselines.py` | 方向玫瑰图 |

## 待补充

> 第四章动力学图表（ch04-dynamics.tex）中如有新增图表，运行后在此更新。
> 运行 `grep -r "includegraphics" 09_paper_thesis_talks/bishe/thesis/chapters/` 可快速核查。

---

*最后更新：2026-04-01*
