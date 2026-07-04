# CLAUDE.md — Hopfion Research Project

> 通用 Mumax3 约束在 `~/.claude/MUMAX3.md`（自动加载），本文件仅 Hopfion 特定内容。

## 项目背景

Hopfion 3D 磁性拓扑结构的微磁学仿真与动力学研究。毕业论文阶段已结束（2026-05），项目持续深入。

**主要模块：**
- `01_legacy_srtp_old/` — SRTP 与旧仿真结果，保留作历史来源和反例
- `02_early_dmi_fm_feasibility/20251219_dmi_fm/` — DMI FM Hopfion 稳定性研究（FeGe，已完成）
- `03_wang2019_stt_reproduction/20260310_wang2019_hopfion_STT/` — Wang 2019 PRL 复现（待续）
- `04_frustrated_fm_foundation/20260105_frustrated_fm/` — Frustrated FM Hopfion 主体系基础
  - `spin_wave_dynamics/` — 频率扫描、幅度扫描、方向耦合、多源控制
  - `centered_stability_test/` — 稳定性验证
  - `drift_experiments/` — 漂移实验
- `05_spinwave_control_dynamics/` — 自旋波控制任务包与汇总结果
- `06_eigenmode_frequency_mechanism/` — 本征频率、ringdown、mode map、能量吸收证据链
- `07_thiele_theory_model/` — Thiele 理论、G/D 平移、低维动力学模型
- `08_lif_neuron_device_application/lif_neuron_hopfion/` — LIF 神经元仿真（Phase 1 PASS，Phase 2 待重设计）
- `09_paper_thesis_talks/` — 毕设、论文、组会与答辩材料
- `90_external_refs/` — 外部资料、专利与设备包
- `95_shared_scripts/` — 共享分析库（强制：见 C-7）

**关键初始态文件：**
`04_frustrated_fm_foundation/20260105_frustrated_fm/centered_stability_test/stability_Ku10k.out/m000020.ovf`（Q_H=1，Ku=10k）

**Frustrated FM 参数：** 100³, 0.5nm/cell, PBC(1,1,1), Ms=1.5e5, Aex=5e-12, J2=-0.164J1, J4=-0.082J1

**技术栈：** Python（numpy/scipy/discretisedfield/matplotlib）、mumax3、LaTeX/xelatex

---

## C-1: Python 执行环境强制前置检查（Hopfion 专用）

- 运行任何 Python 分析脚本之前，**必须**先激活 Hopfion 专用 venv：
  ```bash
  source /mnt/d/Research/Hopfion/hopfion/bin/activate
  ```
- 激活后必须验证 `python -c "import discretisedfield"`；失败则停止并报告，不得继续执行分析脚本。

## C-7: 共享分析库强制使用

- **共享脚本库路径**：`/mnt/d/Research/Hopfion/95_shared_scripts/`
- 以下功能**禁止在子项目脚本中重写**，必须从共享库 import：
  - Hopfion 质心/位移计算
  - Hopfion 大半径 R、管半径 r 提取
  - OVF 批量加载与时间序列提取
  - PBC 坐标展开
  - 任何在 2 个以上子项目中重复出现的函数
- **新增可复用功能时**：先写入 `95_shared_scripts/` 对应模块，同步更新 `95_shared_scripts/README.md`，再在子项目中 import。
- **编写新分析脚本前**：必须先检查 `95_shared_scripts/README.md`，确认所需功能是否已有实现，避免重复造轮子。

---

## 通用规则

- **默认使用中文回复**，除非用户明确用英文提问
- 解释要简洁具体，用类比，不堆砌术语；默认听众是熟悉物理但不一定了解细节的研究者
- **安装系统工具（字体、解压器、包）时，优先给出手动操作步骤**，不要尝试慢速 CLI 下载
- 不确定文件是否冗余时，**先列出受影响文件，等用户确认后再删除**

---

## 仿真工作流

**执行任何 mumax3 仿真前，必须先列出参数确认表：**

| 参数 | 值 |
|------|----|
| 频率 | ? GHz |
| 振幅/场强 | ? T |
| 初始态文件 | ? |
| 仿真时长 | ? ns |
| 输出间隔 | ? ps |
| 边界条件 | PBC / 无 |
| 几何尺寸 | ? nm |

等用户确认后再生成脚本或运行。

**参数一致性检查：** 涉及频率参数时，交叉验证 mx3 脚本内变量（特别是 200GHz / 440GHz 不要混淆）。

---

## bd 任务系统

本项目用 **bd（beads）** 追踪所有任务，不用 markdown TODO 列表。

```bash
bd ready --json          # 查看可做的任务
bd create "标题" --description="详情" -p 1 --json
bd update <id> --claim --json
bd close <id> --reason "完成" --json
bd sync                  # 同步到 git
```

**每次 session 结束前必须：**
1. `bd sync` 保存任务状态
2. `git pull --rebase && git push`（确认 up to date with origin）

---

## 图表-任务对应关系

**修改任何论文图表前，必须先查阅 `00_project_index/figure-mapping.md`**，确认图表来源仿真目录和绘图脚本，不得靠猜测。

---

## Session 开场白模板

每次新 session 建议以如下格式说明工作范围：

> 今天工作范围：仅限 `[具体目录]`。任务：1) xxx 2) xxx。不修改范围外文件。

---

## 安全规则

- 批量删除/移动文件前，列出所有受影响路径，等确认
- 不要在没有读取文件内容的情况下修改文件
- 论文章节修改前，先确认对应的 `.tex` 文件和图表路径

---

## 参考文件

- `AGENTS.md` — bd 系统快速参考
- `00_project_index/figure-mapping.md` — 图表-仿真-脚本对应表
- `95_shared_scripts/hopfion_analysis.py` — 共享分析库（直接 import，不复制）
- `95_shared_scripts/post_sim_analysis.py` — 仿真完成后自动分析脚本
- `95_shared_scripts/morning_report.sh` — 晨间报告（headless Claude）
