# Hopfion 项目导师汇报 — 设计文档

- **日期**：2026-06-01
- **作者**：吴佳乐
- **场景**：与导师 1-on-1 casual talk，无严格时长
- **目标**：把 Hopfion 项目下所有跑过的仿真完整、诚实地呈现，不掩盖失败与半成品
- **交付物**：
  1. `presentation/talk.pptx` — 朴素 PowerPoint，文本框+插图，中文
  2. `presentation/key_code/` — 阅读型代码包，每多文件目录配 README

## 1. 设计原则

1. **完整真实**：184 个仿真目录全部纳入呈现，包括失败、被推翻、未完成的子集。**不沿用毕设论文里"叙事截断"的做法**（如 freq_switch v3 仅展示到 0.80 ns 不提坍塌）。
2. **结论分级**：
   - 有清晰结论的实验 → 现象 + 结论
   - 没有归纳结论 / 不完善的 → 只描述现象，不强行下结论
3. **无介绍页**：不放 Hopfion 概念、研究路线、未来展望等"包装"页面；只摆仿真结果。
4. **代码与 PPT 解耦**：PPT 只讲结论与现象，不引用代码路径；代码包独立提供，老师按 README 自查。
5. **图源复用**：从已有 `analysis/` 与论文 `figures/` 拷图，不重画；缺图的页面纯文字。

## 2. PPT 大纲（29 页）

### A. DMI-FM 体系（P1–P5）

| 页 | 仿真目录 | 内容性质 |
|---|---|---|
| P1 | `20251219_dmi_fm/successful_simulation/run_analytic_relax.out/` | 现象 + 结论：Sutcliffe 解析初始态 + frozenspins + 退磁 → 2ns 稳定，三条件缺一不可 |
| P2 | `failed_attempts/bulk_pbc_tests/` (2 runs) | 现象：Bulk PBC 螺旋态竞争失败，无成功条件 |
| P3 | `failed_attempts/sutcliffe_disc_wrong_ansatz/` (4 runs) | 现象：环形 ansatz 4 次失败 |
| P4 | `failed_attempts/toroidal_nanoring_approach/` (2 runs) | 现象：未完成 |
| P5 | `isolated_hopfion_10lambda/` + `neel_hopfion/` (1+9 runs) | 现象 + 结论：Neel 型也可稳定 |

### B. Frustrated FM 稳定性（P6–P9）

| 页 | 仿真目录 | 内容性质 |
|---|---|---|
| P6 | `size_sweep/` (R8r4, R12r5) | 结论：固有吸引子 R=2.60 nm |
| P7 | `centered_stability_test/` (Ku=0/10k/50k) | 结论：三组都通过 1ns 稳态判据；Ku=10k 选为后续 SW 初始态 |
| P8 | `anisotropy_study/ku_critical_sweep/` (13 Ku 点) | 结论：Ku 增大 → 收缩 → R8r4 体系 ~52–55k 区间坍塌 |
| P9 | `anisotropy_study/size_vs_ku/` + `compute_hopf_index.py` | 结论：当前体系 Q_H=1；Q_H=2/4 从未仿真 |

### C. 漂移实验（P10–P11）

| 页 | 仿真目录 | 内容性质 |
|---|---|---|
| P10 | `drift_experiments/bg_mx_axis_x_stable/` + `bg_my_axis_y_stable/` | 旧实验：bg=mz 漂移 / bg=mx,my 稳定 |
| P11 | `drift_experiments/unified_rerun/` (4 组) | 结论修正：旧结论推翻，4 组完全一致，真实机理是前 1ns 轴向格点 4.75 nm 递举钉扎 |

### D. 自旋波 — 平面源（P12–P17）

| 页 | 仿真目录 | 内容性质 |
|---|---|---|
| P12 | `spin_wave_dynamics/drive_selection/plane_wave/` (5 组) | 结论：vibX 强耦合 / vibZ 无耦合 / srcX≡srcY |
| P13 | `freq_sweep/plane_wave/srcX/` (02ns 10 + 05ns 4) | 结论：100-200/1000 GHz 强响应，400-600 GHz 死区 |
| P14 | `freq_sweep/plane_wave/srcZ/` (coarse 10 + fine 10) | 结论：1100 GHz 最强 -18.1 nm，100 GHz 异常 +z，多个死区 |
| P15 | `amplitude_sweep/plane_wave/srcX/` @440 GHz (6 点) | 现象：旧 v∝B¹·⁹⁹ 拟合已推翻；方向反转阈值 Bc∈(0.1,0.2) T |
| P16 | `amplitude_sweep/plane_wave/srcZ/` @1100 GHz (6 点 cron) | 现象：数据可能不全，仅展示已完成 B 点 |
| P17 | srcX vs srcZ 双向 z 可控性总结 | 结论：单源双向控制建立 |

### E. 自旋波 — 点源（P18–P20）

| 页 | 仿真目录 | 内容性质 |
|---|---|---|
| P18 | `freq_sweep/point_source/srcX/` (10 频率) | 结论：700 GHz 最强 5.71 nm，全频段 +z，死区消失，Hall 角 69-89° |
| P19 | `freq_sweep/point_source/srcZ/` (10 频率) | 结论：800 GHz 最强 -7.31 nm，方向分布复杂 (6+z/3-z)，Hall 角 9-40° |
| P20 | `amplitude_sweep/point_source/` @1100 GHz | 现象：B100/200/300/400 完成；B500 停在 0.433 ns；B700/B1000/B2000 未跑 |

### F. 多源控制 / freq_switch（P21–P22）

| 页 | 仿真目录 | 内容性质 |
|---|---|---|
| P21 | `multisource_control/baseline/` + `bidirectional_z/v1/` | 现象：双源仅 +z，未实现反转 |
| P22 | `bidirectional_z/v2/`, `v3/` | 现象 + 诚实呈现：v2 双向 FAILED；v3 Phase1 +17.6 nm PASS / Phase2 反转 SUCCESS 但 **t≈0.91 ns Hopfion 坍塌 core=0**；毕设展示截到 0.80 ns 未提，本次完整呈现 |

### G. STT 驱动（P23）

| 页 | 仿真目录 | 内容性质 |
|---|---|---|
| P23 | `20260310_wang2019_hopfion_STT/` (v1 91 帧 + v2 32 帧) | 结论：Wang 2019 PRL 复现，Bloch Hopfion STT 可驱动 |

### H. LIF 神经元（P24–P26）

| 页 | 仿真目录 | 内容性质 |
|---|---|---|
| P24 | `lif_neuron_hopfion/gradient_ku_verification/` (V2 gradient + uniform) | 结论：PASS，梯度恢复力确认；意外发现 Hopfion 偏好低 Ku 区，与初始假设相反 |
| P25 | `lif_cycle_demo/pulse_train_integrate/lif_pulse_train.out/` | 现象：F1 FAILED，t=1.089 ns kill；1100 GHz 推 -z 方向与梯度恢复力同向（非反向），Leak 期持续 overshoot |
| P26 | Phase 2 重设计候选方案 A/B/C/D | 现状：未开工，4 个候选未定 |

### I. 旧仿真对标（P27–P28）

| 页 | 仿真目录 | 内容性质 |
|---|---|---|
| P27 | `old_results/My_old_simulation/` (20 runs) | 现象：旧版本系数错误，与当前版差异约 2-3% 拓扑荷，列为系数符号陷阱教训 |
| P28 | `deviceB_package/` (9 runs) + `srtp/` 学生项目 | 现象：Device B 验证；部分学生工作未完成 |

### 末页（P29）

- 现状清单：跑完有结论 / 跑完没结论 / 停在半路 / 从未启动 四类逐项列

## 3. 代码包结构

```
presentation/key_code/
├── README.md                                # 顶层总索引
│
├── 00_shared_libs/                          # 共享分析库
│   ├── README.md
│   ├── hopfion_analysis.py
│   ├── compute_hopf_index.py
│   ├── paper_style.py
│   ├── post_sim_analysis.py
│   └── audit_sweep_params.py
│
├── 01_dmi_fm/
│   ├── README.md
│   ├── gen_sutcliffe_hopfion.py
│   ├── run_analytic_relax.mx3
│   ├── run_sutcliffe_with_demag.mx3
│   ├── failed_bulk_pbc.mx3
│   ├── failed_disc_ansatz.mx3
│   ├── neel_hopfion_v4.mx3
│   └── visualize_hopfion.py
│
├── 02_frustrated_fm_stability/
│   ├── README.md
│   ├── gen_hopfion_R8r4.py
│   ├── size_sweep_R8r4_Ku0.mx3
│   ├── size_sweep_R12r5_Ku0.mx3
│   ├── stability_Ku0.mx3
│   ├── stability_Ku10k.mx3                  # 后续 SW 初始态来源
│   ├── stability_Ku50k.mx3
│   ├── ku_critical_template.mx3
│   ├── size_vs_ku_template.mx3
│   └── compute_qh_timeseries.py
│
├── 03_drift/
│   ├── README.md
│   ├── bg_mx_axis_x_stable.mx3
│   ├── unified_rerun_template.mx3
│   └── analyze_drift_unified_v2.py
│
├── 04_spin_wave_plane/
│   ├── README.md
│   ├── drive_selection_template.mx3
│   ├── freq_sweep_srcX_template.mx3
│   ├── freq_sweep_srcZ_fine_template.mx3
│   ├── amplitude_sweep_srcX_440GHz.mx3
│   ├── amplitude_sweep_srcZ_1100GHz.mx3
│   ├── analyze_freq_response.py
│   └── analyze_amplitude_scaling.py
│
├── 05_spin_wave_point/
│   ├── README.md
│   ├── point_source_template.mx3
│   ├── freq_sweep_srcX_point.mx3
│   ├── freq_sweep_srcZ_point.mx3
│   └── amplitude_sweep_point_1100GHz.mx3
│
├── 06_multisource_freq_switch/
│   ├── README.md
│   ├── baseline_dual_src.mx3
│   ├── freq_switch_v1.mx3
│   ├── freq_switch_v2.mx3
│   ├── freq_switch_v3.mx3                   # 0.91 ns 坍塌案例
│   └── analyze_freq_switch.py
│
├── 07_stt_wang2019/
│   ├── README.md
│   ├── run_bloch_hopfion.mx3
│   └── run_bloch_hopfion_v2.mx3
│
├── 08_lif_neuron/
│   ├── README.md
│   ├── gradient_ku_drive_release.mx3        # Phase 1 PASS
│   ├── uniform_ku_drive_release.mx3
│   ├── lif_pulse_train.mx3                  # Phase 2 F1 FAILED
│   ├── analyze_leaky_drift.py
│   └── analyze_lif_cycle.py
│
├── 09_old_simulations/
│   ├── README.md                            # 重点说明系数符号错误
│   ├── My_old_simulation_srcX.mx3
│   ├── My_old_simulation_srcZ.mx3
│   └── deviceB_freq_sweep.mx3
│
└── figures/                                 # PPT 共用关键分析图
    ├── README.md
    ├── dmi_fm_stable.png
    ├── ku_critical_R_vs_Ku.png
    ├── drift_4groups_comparison.png
    ├── freq_response_srcX.png
    ├── freq_response_srcZ.png
    ├── amplitude_law_failed.png
    ├── point_vs_plane.png
    ├── freq_switch_v3_collapse.png
    ├── lif_phase1_pass.png
    └── lif_phase2_f1_failed.png
```

10 个子目录 + figures + 顶层 README。每个含 2 文件以上的子目录配独立 README。

**代表性原则**：每个子实验拷 1-2 个代表 `.mx3`（template + 一个典型实例），加 1 个分析脚本；不拷 184 个全部。

### README 统一模板

每个子目录 README 包含：
- 物理主题一句话
- 脚本清单：文件名 + 一行功能 + 输入/输出
- 关键参数表（如有）
- 对应原始 `.out` 目录路径
- 当前状态：完成 / 部分完成 / 失败

### 范围与排除

**纳入**：
- 代表性 `.mx3` 脚本（不是 184 个全拷）
- 关键 Python 分析脚本
- 共享库 `scripts/*.py`
- 关键分析图（PNG）

**排除**：
- 所有 `.out/` 输出目录与 `.ovf` 帧
- 毕设 `bishe/`
- 论文 `.tex`
- bd / mempalace 数据库

## 4. 工作流程

1. 建 `presentation/key_code/` 子树骨架（含空 README）
2. 拷代码 + 共享库 → 各子目录
3. 写各级 README
4. 收图到 `presentation/key_code/figures/`
5. 写 `presentation/talk_outline.md`（页对页文字 + 图引用）
6. 用 pptx skill 生成 `presentation/talk.pptx`
7. 走查：对照 P1-P29 检查每页

### 数据流

```
源仿真目录 (.out/, .mx3, .py)
        ↓ rsync 排除 .ovf/.out/.tex
presentation/key_code/<module>/
        ↓ README 标注
presentation/key_code/figures/  ←  从 *.out/analysis/ 收
        ↓ 引用
presentation/talk_outline.md → talk.pptx
```

## 5. 风险与缓解

| 风险 | 缓解 |
|---|---|
| 部分仿真无分析图（如 LIF F1 FAILED 可能仅 log） | 该页改纯文字 + table.txt 摘录，不造图 |
| `My_old_simulation/srcX/srcX/` 子目录套娃 | `find` 定位真实脚本路径 |
| `amplitude_sweep srcZ` cron 数据不全 | 注明"数据不全，仅展示已完成 B 点" |
| `failed_attempts/` 多脚本同名 | 拷贝时加前缀 `bulk_pbc_attempt_<i>.mx3` |
| LIF Phase 2 4 候选方案无代码 | 不进 key_code，P26 仅描述 |
| 共享库路径耦合 | README 注明加 PYTHONPATH |

## 6. 输出位置

- 全部产物：`/mnt/d/Research/Hopfion/presentation/`
- 不动 `bishe/` 与其它源仿真目录

## 7. 退出标准

- `presentation/key_code/` 树齐 + 所有 README 写完
- `presentation/talk.pptx` 29 页齐
- `presentation/README.md` 一段话使用说明

## 8. 后续

本 spec 经用户审过后，进入 writing-plans skill，把上述工作流拆为可执行 task 列表。
