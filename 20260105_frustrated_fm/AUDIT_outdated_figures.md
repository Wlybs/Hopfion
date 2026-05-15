# 审计：20260105_frustrated_fm/* 与毕设 figures/ 的不一致清单

> 生成时间：2026-05-14
> 范围：`20260105_frustrated_fm/` 全部子目录共 49 张 PNG
> 对照源：`bishe/thesis_v2/figures/`（毕设最终图，~80 张）+ `figure-mapping.md`（最后更新 2026-04-01）
> 用户决定：**只列清单不动手**
> 关键发现：毕设已用 Hopf 指数 $Q_H$ 替代 core-voxel 计数作为稳定性判据，但源仿真目录里仍残留 core-voxel 老图。`bishe/thesis_v2/figures/fig3-9_centered_core_count.png` 文件名仍为 core_count，caption 已改为 "$Q_H$ 随时间演化"（filename 没同步改）。

---

## A 类：核心矛盾 — 仍按 core-voxel 路线生成的老图（毕设已弃用此判据） ✓ 已处理 2026-05-14

毕设 ch04-stability.tex 已用 $Q_H$ 时间序列作为稳定性判据。以下源目录图仍是老的 core-voxel 计数路线，**与论文结论不符**：

| # | 文件路径（相对 20260105_frustrated_fm/） | size | 论文引用 | 处理 |
|---|---|---|---|---|
| A1 | `centered_stability_test/stability_results/hopfion_mz_core_count.png` | 69KB | 无 | ✓ 已 `rm` 2026-05-14 |
| A2 | `spin_wave_dynamics/drive_selection/plane_wave/results/hopfion_core_4combos.png` | 127KB | 无 | ✓ 已 `rm` 2026-05-14 |
| A3 | `spin_wave_dynamics/drive_selection/plane_wave/results/hopfion_core_5combos.png` | 151KB | 无 | ✓ 已 `rm` 2026-05-14 |
| A4 | `spin_wave_dynamics/amplitude_sweep/point_source/results/core_comparison.png` | 138KB | 无 | ✓ 已 `rm` 2026-05-14 |

> 同目录 analyzer 脚本均保留（`analyze_centered_stability.py`、`analyze_sw_4combos.py`、`analyze_full_B_sweep.py` 等），如有需要可重跑生成新版（论文不再使用 core voxel 判据，不建议重跑老图）。

---

## B 类：格式未统一 — 内容仍有效但命名/标签风格不符合论文规范 ✓ 已处理 2026-05-14

**结果**：
- 5 张保留图（B01/B06/B07/B11/B12）已用 `scripts/paper_style.py` 统一论文风格重画，输出到对应 `results/` 子目录
- 8 张废图（B02/B03/B04/B05/B08/B09/B10/B13）已 rm
- 各源目录新增 `replot_paper_style.py` 脚本（复用原 analyzer 数据加载，重画图）
- B 类总计 13 张已全部清理。详见各 replot 脚本

**保留 5 张新版位置**:
| BN | 新版路径 |
|---|---|
| B01 | `centered_stability_test/stability_results/fig_Rr_evolution.png` |
| B06 | `size_sweep/results/size_convergence.png`（旧 `size_convergence_english.png` 已删） |
| B07 | `anisotropy_study/ku_critical_sweep/results/R_r_vs_time.png` |
| B11 | `anisotropy_study/size_vs_ku/results/R_r_vs_time.png` |
| B12 | `anisotropy_study/size_vs_ku/results/summary_Rr_vs_Ku1.png` |

**遗留 TODO**：
- B07 中高 Ku（≥55 kJ/m³）数据点拟合失败（hopfion 坍塌后），新图把这些 R≈19 nm 异常值也画出来了。物理上正确但视觉误导，建议在 analyze_sweep_large.py 的 plot 数据过滤层加 `status=='alive'` 判定。本次未改。

---



源目录用 `fig_*.png` 或英文标签的旧风格，论文用 `fig3-*` / `fig4-*` 中文标签 + (a)(b) panel 拆分：

| # | 源目录文件 | 论文对应 | 不一致点 | 建议 |
|---|---|---|---|---|
| B1 | `centered_stability_test/stability_results/fig_Rr_evolution.png` | （非论文直接来源） | `fig_*` 旧命名 | 归档 |
| B2 | `centered_stability_test/stability_results/fig_energy_evolution.png` | 未入论文 | 旧命名 | 归档 |
| B3 | `centered_stability_test/stability_results/fig_magnetization.png` | 未入论文 | 旧命名 | 归档 |
| B4 | `centered_stability_test/stability_results/hopfion_z_drift.png` | Fig.3-8（`fig3-8_centered_z_drift.png`） | 内容近似但缺统一字体/panel 标签 | 用论文 figures/ 反向覆盖，或重跑脚本统一格式 |
| B5 | `centered_stability_test/stability_results/hopfion_xyz_drift.png` | Fig.3-8 系列 | 同 B4 | 同 B4 |
| B6 | `size_sweep/size_convergence_english.png` | Fig.3-3（`fig3-3_size_convergence.png` + `_a/_b`） | 英文标签，论文要中文+(a)(b) 拆分 | **重跑脚本** 输出 zh 版本 |
| B7 | `anisotropy_study/ku_critical_sweep/results/R_r_vs_time.png` | Fig.3-6（`fig3-6_anisotropy_Rr_vs_time.png` + `_a/_b`） | 命名旧、未拆 panel | 用论文 figures/ 反向覆盖 |
| B8 | `anisotropy_study/ku_critical_sweep/results/summary_Rr_vs_Ku1.png` | Fig.3-7（`fig3-7_anisotropy_summary.png`） | 命名旧 | 反向覆盖或重跑 |
| B9 | `anisotropy_study/ku_critical_sweep/results/centroid_xyz_vs_time.png` | 未入论文 | — | 归档 |
| B10 | `anisotropy_study/ku_critical_sweep/results/centroid_z_vs_time.png` | 未入论文 | — | 归档 |
| B11 | `anisotropy_study/size_vs_ku/results/R_r_vs_time.png` | 同 B7（重复目录） | 重复 | 归档 |
| B12 | `anisotropy_study/size_vs_ku/results/summary_Rr_vs_Ku1.png` | 同 B8 | 重复 | 归档 |
| B13 | `drift_experiments/analysis/trajectory_10ns_final.png` | Fig.3-4（`fig3-4_drift_trajectory_10ns.png` + `_a/_b/_c`） | 未拆 panel | 反向覆盖 |

---

## C 类：版本迭代历史 — 同一指标多版本并存 ✓ 已处理 2026-05-14

**结果**：5 组并存版本均删旧留新。
- C1 删 `B_sweep_scaling.png` (v1) 留 `B_sweep_scaling_v2.png`
- C2 删 `displacement_05ns.png` 留 `displacement_all_freq.png`（Fig.4-freq-1 来源）
- C3 删 `velocity_05ns.png` 留 `velocity_all_freq.png`（Fig.4-freq-2 来源）
- C4 删 `motion_mode_map_05ns.png` 留 `motion_mode_map.png`（Fig.4-freq-4 来源）
- C5 删 `freq_switch_z_control.png` (v1) 留 `freq_switch_v3_z_control.png`（v3 是最新迭代，论文 fig4-11 另外重做）



源目录里 `_v2` / `_05ns` / `_all_freq` 并存，论文只引用其中一个（一般是最新）：

| # | 路径 | 共存版本 | 论文实际用 | 建议 |
|---|---|---|---|---|
| C1 | `spin_wave_dynamics/amplitude_sweep/point_source/results/B_sweep_scaling.png` 与 `..._v2.png` | v1 + v2 | 待核对论文实际版本 | 留 v2，归档 v1 |
| C2 | `spin_wave_dynamics/freq_sweep/plane_wave/srcX/results/displacement_05ns.png` 与 `displacement_all_freq.png` | 05ns + all_freq | `all_freq` → Fig.4-freq-1 | 留 all_freq，归档 05ns |
| C3 | `spin_wave_dynamics/freq_sweep/plane_wave/srcX/results/velocity_05ns.png` 与 `velocity_all_freq.png` | 05ns + all_freq | `all_freq` → Fig.4-freq-2 | 同 C2 |
| C4 | `spin_wave_dynamics/freq_sweep/plane_wave/srcX/results/motion_mode_map.png` 与 `motion_mode_map_05ns.png` | 主图 + 05ns | 主图 → Fig.4-freq-4 | 归档 05ns |
| C5 | `spin_wave_dynamics/multisource_control/bidirectional_z/results/freq_switch_z_control.png` 与 `freq_switch_v3_z_control.png` | v1 + v3 | 论文使用 `fig4-11_freq_switch_z_control.png`（需核对哪版） | 待核对 |

---

## D 类：未入论文的中间产物 — 仅作 SI/答辩备用 ✓ 已处理 2026-05-14

**结果**：22 张孤儿图中，D01（`ku_critical_sweep/results/hopfion_gallery_vs_Ku.png`）删除，D02–D22（21 张）保留作 SI/答辩备用。



可能仍有价值（答辩 Q&A 或补充材料），但论文正文未引用：

| # | 路径 |
|---|---|
| D1 | `anisotropy_study/ku_critical_sweep/results/hopfion_gallery_vs_Ku.png` |
| D2 | `spin_wave_dynamics/amplitude_sweep/point_source/results/B_sweep_8pts_final.png` |
| D3 | `spin_wave_dynamics/amplitude_sweep/point_source/results/dr_vs_B_curve.png` |
| D4 | `spin_wave_dynamics/amplitude_sweep/point_source/results/energy_comparison.png` |
| D5 | `spin_wave_dynamics/amplitude_sweep/point_source/results/perturbation_comparison.png` |
| D6 | `spin_wave_dynamics/amplitude_sweep/point_source/results/perturbation_profiles.png` |
| D7 | `spin_wave_dynamics/amplitude_sweep/point_source/results/position_comparison.png` |
| D8 | `spin_wave_dynamics/amplitude_sweep/point_source/results/ps_B_sweep_full.png` |
| D9 | `spin_wave_dynamics/drive_selection/plane_wave/results/energy_4combos.png` |
| D10 | `spin_wave_dynamics/drive_selection/plane_wave/results/energy_5combos.png` |
| D11 | `spin_wave_dynamics/drive_selection/plane_wave/results/hopfion_position_4combos.png` |
| D12 | `spin_wave_dynamics/drive_selection/plane_wave/results/hopfion_position_5combos.png` |
| D13 | `spin_wave_dynamics/drive_selection/plane_wave/results/sw_perturbation_growth.png` |
| D14 | `spin_wave_dynamics/drive_selection/plane_wave/results/sw_perturbation_profiles.png` |
| D15 | `spin_wave_dynamics/freq_sweep/plane_wave/srcX/results/hall_angle_time_resolved.png` |
| D16 | `spin_wave_dynamics/freq_sweep/plane_wave/srcZ/results/direction_map.png` |
| D17 | `spin_wave_dynamics/freq_sweep/plane_wave/srcZ/results/displacement_srcZ.png` |
| D18 | `spin_wave_dynamics/freq_sweep/plane_wave/srcZ/results/freq_response_map.png` |
| D19 | `spin_wave_dynamics/freq_sweep/point_source/results/point_source_comparison.png` |
| D20 | `spin_wave_dynamics/freq_sweep/point_source/results/point_source_freq_response.png` |
| D21 | `spin_wave_dynamics/freq_sweep/point_source/results/point_source_hall_angle.png` |
| D22 | `spin_wave_dynamics/multisource_control/bidirectional_z/results/z_control_demo.png` |

---

## F 类：毕设 `bishe/thesis_v2/figures/` 内部的文件名 ↔ caption / 编号不一致 ✓ 已处理 2026-05-14

**F1** ✓ `fig3-9_centered_core_count.png` → `fig3-9_centered_Qh_evolution.png`
- 图本身已是 $Q_H$ 曲线（验证后确认），只是文件名 misleading
- 同步改：`ch04-stability.tex` includegraphics + L89 `\cref` 引用 + label → `fig:centered-Qh-evolution`
- 同步改：generator `make_fig3-9_centered_core_count.py` 重命名 + 内部 OUT 路径

**F2** ✓ `fig6-2_lif_analogy.png` → `fig6-1_lif_analogy.png`
- ch06 叙事顺序：§6.1 先讲 LIF 类比 → §6.2 后讲器件
- 改：includegraphics + generator 脚本名 + 内部路径
- `fig6-2_device_concept.png` 保持不变

**F3** ✓ 原 audit 描述有误：
- `fig4-5_srcZ_freq_response.png` 实际不存在（在 `fig4-4_*` 下面）
- 真正孤儿只有 `fig4-5_srcZ_direction_map.png` + _a + _b，已 mv 到 `figures/_unused/`
- ch05 唯一引用 `fig4-5_srcZ_trajectory.png` 保留



来源：扫描 `bishe/thesis_v2/chapters/ch0*.tex` 所有 `\includegraphics` + `\caption` 配对得到。

| # | 文件 | 引用处 | 不一致点 | 建议 |
|---|---|---|---|---|
| F1 | `fig3-9_centered_core_count.png` | ch04-stability.tex L102-103 | filename = `core_count`（core voxel 数，已弃用判据），caption = "居中 霍普夫子 的 Hopf 指数 $Q_H$ 随时间演化" | **重命名** `fig3-9_centered_Qh_evolution.png`，同步改 .tex 的 includegraphics 路径；并核对图像本身是否真为 $Q_H$ 曲线（若仍是 core_count 老图，需重新绘图） |
| F2 | `fig6-2_lif_analogy.png` 与 `fig6-2_device_concept.png` 都叫 `fig6-2_*` | ch06-neuromorphic.tex L14（lif_analogy 先出现）、L25（device_concept 后出现） | 同章节两张图共享 fig6-2 编号；章内**没有 fig6-1** | 按出现顺序重编：`fig6-2_lif_analogy.png` → `fig6-1_lif_analogy.png`；或反向（看叙事逻辑：通常先讲器件 device_concept = fig6-1，再讲 LIF 类比 = fig6-2，则需调整 tex 中两图前后顺序） |
| F3 | `fig4-5_srcZ_trajectory.png`、`fig4-5_srcZ_freq_response.png`、`fig4-5_srcZ_direction_map.png` 共用 fig4-5 编号 | ch05-dynamics.tex L103 只引用 `fig4-5_srcZ_trajectory.png` | 同编号下 3 个不同后缀；后两个未在正文 includegraphics 中出现（疑似孤儿或历史遗留） | 核对正文实际用图，孤儿图重命名或归档；若都进 SI，按 `fig4-5a/b/c` 或 `figS4-5_*` 区分 |

> 备注：以上仅是文件名层面的不一致。**还需要图像内容核对**——例如 F1 的图是否真的已替换为 $Q_H$ 曲线，还是 caption 改了但图没换。建议下次动手时先 visual diff（用 imagemagick `compare` 或人眼）。

## 跨章节编号一致性观察（附记）

毕设 `figure-mapping.md` 用 "第三章：Hopfion 稳定性" 标题，但当前 `ch04-stability.tex` 才是稳定性章。文件名仍用 `fig3-*`，这是从早期"第三章=稳定性"沿袭下来的命名。

| 现象 | 备注 |
|---|---|
| Chapter 4 (ch04-stability.tex) 内的图都叫 `fig3-*` | 历史遗留；不影响编译，但 cross-ref 容易混淆 |
| Chapter 5 (ch05-dynamics.tex) 内的图都叫 `fig4-*` | 同上 |
| `figure-mapping.md` 章节号未跟新章节顺序更新 | 建议把 mapping 里的"第三章/第四章"改成"稳定性章/动力学章"以解耦 |

> 这条不算 bug 但属于"将来维护陷阱"，决定要不要修要看你毕设是否还会改。

---

## E 类：与论文图基本对应、形式相近的源图 — 重画为论文风格 (进行中)

> **2026-05-15 校正**：之前 E 类标"保留即可"是判断失误——"形式相近"≠"风格统一"。
> 源目录这些 E 类图实际是旧 analyzer 跑的英文风格，需要按 paper_style 重画。
> D 类同步处理（user 决定全部 results/ 走论文风格）。

### 进度跟踪 (E + D 类批量重画)

✓ **1/9 已完成**: `spin_wave_dynamics/amplitude_sweep/plane_wave/` (4 张 E)
   - trajectory_vs_B.png / velocity_vs_B.png / scaling_440GHz.png / hall_angle_vs_amplitude.png
   - 改 analyze_amplitude_sweep.py / analyze_amplitude_scaling.py / analyze_hall_angle_amplitude.py
   - commit 5f718a0

### 剩余 (next session 接手)

⏳ **8/9 待做** (约 23 张):

1. `spin_wave_dynamics/amplitude_sweep/point_source/` (7 D)
   - analyzer: analyze_full_B_sweep.py / analyze_ps_baseline.py
   - 图: B_sweep_8pts_final, dr_vs_B_curve, energy_comparison, perturbation_comparison, perturbation_profiles, position_comparison, ps_B_sweep_full

2. `spin_wave_dynamics/drive_selection/plane_wave/` (6 D)
   - analyzer: analyze_sw_4combos.py
   - 图: energy_4combos, energy_5combos, hopfion_position_4combos, hopfion_position_5combos, sw_perturbation_growth, sw_perturbation_profiles

3. `spin_wave_dynamics/freq_sweep/plane_wave/srcX/` 余下 (1 E + 3 D ≈ 4)
   - 图: hall_angle_vs_freq (E5, fig4-freq-3 论文用), motion_mode_map (E6, fig4-freq-4 论文用) — 这俩可能已论文风格需 verify
   - 图: hall_angle_time_resolved (D15) 等

4. `spin_wave_dynamics/freq_sweep/plane_wave/srcZ/` (3 D)
   - 图: direction_map / displacement_srcZ / freq_response_map

5. `spin_wave_dynamics/freq_sweep/plane_wave/energy_absorption/` (1 E)
   - 图: energy_absorption_spectrum

6. `spin_wave_dynamics/freq_sweep/point_source/` (3 D)
   - 图: point_source_comparison / point_source_freq_response / point_source_hall_angle

7. `spin_wave_dynamics/multisource_control/baseline/` (2 E)
   - analyzer: analyze_baselines.py
   - 图: baseline_trajectories (E7, fig4-ms-1 论文用) / direction_rose_plot (E8, fig4-ms-2)

8. `spin_wave_dynamics/multisource_control/bidirectional_z/` (1 D)
   - 图: z_control_demo

### 已知 paper_style 边界 case

🐛 `panel_label` 默认 `top_center_outside` 与单 axes 上的 `legend_above` (位置 (0.5, 1.02)) 重叠
   - 表现: hall_angle_vs_amplitude.png 的 (b) 标号被 legend 压住
   - 修复方案: 当 axes 使用 legend_above 时, panel_label 自动 fallback 到 `top_left_outside`，或加 `top_right_outside`
   - 位置: `/mnt/d/Research/Hopfion/scripts/paper_style.py`

### 复用模板 (来自 amp_sweep/plane_wave/)

每个 analyzer 改造步骤一致:
```python
# 1. 顶部 imports 增加
sys.path.insert(0, "/mnt/d/Research/Hopfion/scripts")
from paper_style import (setup_paper_style, COLORS, save_paper_fig,
                          panel_label, shared_legend_above, legend_above,
                          sweep_colors)
setup_paper_style()

# 2. plot 部分关键替换
# 英文 label → 中文斜体: r"时间 $t$ (ns)" / r"$|\Delta r|$ (nm)"
# colors = plt.cm.<cmap>(np.linspace(...)) → sweep_colors(N, cmap=)
# ax.set_title / plt.suptitle → 删除 (留 caption)
# ax.legend(fontsize=...) → legend_above(ax, ncol=) 或 shared_legend_above(fig, axes[0], ncol=)
# panel 标号 → panel_label(fig, ax, "(a)")
# plt.savefig + plt.tight_layout → save_paper_fig(fig, out_png)
```



| # | 路径 | 对应论文图 |
|---|---|---|
| E1 | `spin_wave_dynamics/amplitude_sweep/plane_wave/results/hall_angle_vs_amplitude.png` | Fig.4-amp-1 |
| E2 | `spin_wave_dynamics/amplitude_sweep/plane_wave/results/trajectory_vs_B.png` | Fig.4-amp-2 |
| E3 | `spin_wave_dynamics/amplitude_sweep/plane_wave/results/scaling_440GHz.png` | Fig.4-amp-3 |
| E4 | `spin_wave_dynamics/amplitude_sweep/plane_wave/results/velocity_vs_B.png` | Fig.4-amp 系列 |
| E5 | `spin_wave_dynamics/freq_sweep/plane_wave/srcX/results/hall_angle_vs_freq.png` | Fig.4-freq-3 |
| E6 | `spin_wave_dynamics/freq_sweep/plane_wave/srcX/results/motion_mode_map.png` | Fig.4-freq-4 |
| E7 | `spin_wave_dynamics/multisource_control/baseline/results/baseline_trajectories.png` | Fig.4-ms-1 |
| E8 | `spin_wave_dynamics/multisource_control/baseline/results/direction_rose_plot.png` | Fig.4-ms-2 |
| E9 | `spin_wave_dynamics/freq_sweep/plane_wave/energy_absorption/energy_absorption_spectrum.png` | Fig.4-6 系列 |

---

## 工作量摘要

| 类 | 数量 | 处理路径 |
|---|---|---|
| A（源目录 core-voxel 老图） | 4 | 必删/归档 |
| B（源目录格式未统一） | 13 | 重跑脚本或反向覆盖 |
| C（源目录版本并存） | 5 | 留新版、归档旧版 |
| D（源目录孤儿图） | 22 | 看你是否要进 SI |
| E（源目录基本一致） | 9 | 保留 |
| F（**毕设 figures/ 内部不一致**） | 3 | 重命名 + tex 同步改 |
| 合计 | **56**（部分文件被多分类计数） | — |

> 注：`templates/` 目录无 PNG，未列入。

## 下一步可选动作

> 当前用户决定：只列清单不动手。以下为可选后续动作（待批准）：

1. **最低清扫**：只清 A 类 4 张（违背毕设结论的 core-voxel 图）
2. **中度清扫**：A + B + C，统一格式 + 删冗余版本（共 22 张需动）
3. **重跑脚本统一**：对 B 类 13 张运行各 subdir 内 analysis 脚本，输出符合论文格式版本（耗时多但最干净）
4. **不动手只更新 figure-mapping.md**：把现状记入 mapping，标注"源目录已废弃，论文图为权威"
5. **优先修毕设 F 类**：先把 F1（fig3-9 重命名）+ F2（fig6-1/fig6-2 编号）+ F3（fig4-5 重号）改掉，这 3 项**会进答辩 / 终稿 PDF**，影响最大；源目录清扫可放后

## 参考

- 毕设 figures: `/mnt/d/Research/Hopfion/bishe/thesis_v2/figures/`
- 章节 tex: `/mnt/d/Research/Hopfion/bishe/thesis_v2/chapters/ch04-stability.tex` (含 fig3-* 引用)
- 图表-脚本映射: `/mnt/d/Research/Hopfion/figure-mapping.md`
