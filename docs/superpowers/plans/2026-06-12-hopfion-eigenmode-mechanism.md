# Hopfion Eigenmode Mechanism Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立 `173.66 GHz` 候选本征模的线性、空间局域、对称性和传播自旋波耦合证据链。

**Architecture:** 共享库负责生成 mx3、读取 table、流式傅里叶投影、峰宽和 k 谱指标；结果包负责声明仿真矩阵、排队运行、调用共享函数并生成论文级结果。阶段门根据机器可读判据决定是否生成和运行后续连续波批次。

**Tech Stack:** Mumax3 3.11.1、Python 3.12、numpy、scipy、discretisedfield、matplotlib、pytest。

---

### Task 1: 共享频谱与脚本生成接口

**Files:**
- Modify: `scripts/resonance_analysis.py`
- Modify: `scripts/README.md`
- Create: `hopfion_eigenmode_mechanism_20260612/tests/test_eigenmode_mechanism.py`

- [ ] 写失败测试，覆盖幅度矩阵、FWHM、ROI mx3、圆偏 mx3 和阶段门。
- [ ] 运行测试确认失败。
- [ ] 实现最小共享函数并补充 README。
- [ ] 运行测试确认通过。

### Task 2: 仿真 manifest 与 mx3 生成

**Files:**
- Create: `hopfion_eigenmode_mechanism_20260612/analysis/generate_simulations.py`
- Create: `hopfion_eigenmode_mechanism_20260612/results/simulation_manifest.csv`
- Create: `hopfion_eigenmode_mechanism_20260612/mx3/*.mx3`

- [ ] 从参数表生成批次 1 至 3 脚本。
- [ ] 检查每个脚本只有目标变量变化。
- [ ] 对全部脚本执行 `mumax3 -vet`。
- [ ] 提交设计、测试和脚本生成代码。

### Task 3: 第一阶段批量仿真

**Files:**
- Create: `hopfion_eigenmode_mechanism_20260612/run_stage1.sh`
- Create: `hopfion_eigenmode_mechanism_20260612/logs/*.log`
- Create: `hopfion_eigenmode_mechanism_20260612/mx3/*.out/`

- [ ] 串行运行 1/2 mT、1 ns、空间 Hopfion/背景和圆偏两组。
- [ ] 每组结束校验 table 最后时间、OVF 帧数和退出码。
- [ ] 不使用 `tee`，日志直接重定向。

### Task 4: 线性、局域性与圆偏分析

**Files:**
- Create: `hopfion_eigenmode_mechanism_20260612/analysis/analyze_stage1.py`
- Create: `hopfion_eigenmode_mechanism_20260612/results/stage1_*.csv`
- Create: `hopfion_eigenmode_mechanism_20260612/figures/stage1_*.png`
- Create: `hopfion_eigenmode_mechanism_20260612/notes/stage1_interpretation.md`

- [ ] 计算 1/2/5 mT 峰位和归一化功率。
- [ ] 从 1 ns 数据计算 FWHM 与 Q，并保留失败状态。
- [ ] 流式计算 Hopfion/背景 ROI 的复模态。
- [ ] 计算局域化比和圆偏选择性。
- [ ] 输出阶段门 `results/stage1_gate.json`。

### Task 5: 连续波桥接

**Files:**
- Create: `hopfion_eigenmode_mechanism_20260612/analysis/generate_stage2.py`
- Create: `hopfion_eigenmode_mechanism_20260612/run_stage2.sh`
- Create: `hopfion_eigenmode_mechanism_20260612/results/cw_bridge.csv`

- [ ] 仅在阶段门通过时生成 11 组连续波脚本。
- [ ] `mumax3 -vet` 后串行运行。
- [ ] 计算锁相相干响应、位移和形变指标；总能量斜率只作趋势量。
- [ ] 与 ringdown 峰叠图并给出严格对齐判定。

### Task 6: 点源与平面源 k 谱

**Files:**
- Create: `hopfion_eigenmode_mechanism_20260612/analysis/generate_k_spectrum.py`
- Create: `hopfion_eigenmode_mechanism_20260612/analysis/analyze_k_spectrum.py`
- Create: `hopfion_eigenmode_mechanism_20260612/results/k_spectrum_metrics.csv`

- [ ] 生成并 vet 四组短时切片仿真。
- [ ] 运行并校验切片帧数。
- [ ] 计算归一化 k 谱、FWHM 和低 k 权重。
- [ ] 判断点源红移假说是否获得支持。

### Task 7: 研究包、记录与交付

**Files:**
- Create: `hopfion_eigenmode_mechanism_20260612/README.md`
- Create: `hopfion_eigenmode_mechanism_20260612/notes/paper_draft_cn.md`
- Modify: `.beads/issues.jsonl`
- Modify outside repository: Hopfion project memory and Obsidian progress/daily notes

- [ ] 运行全部新测试和相关回归测试。
- [ ] 写明通过、失败和未核实结论。
- [ ] 更新 bd、project memory、vault。
- [ ] 分阶段提交，pull --rebase，push，并验证 HEAD 与 origin 对齐。
