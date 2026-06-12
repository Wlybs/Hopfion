# Hopfion 本征模与自旋波耦合机制

本结果包执行 2026-06-12 确认的方案 B。研究对象为 frustrated-FM 条件下的 Q_H=1 Hopfion，目标是把 `173.66 GHz` table-average ringdown 候选峰推进到可检验的空间本征模与传播自旋波耦合证据链。

## 当前批次

原第一阶段包含七组仿真。首个 `1 mT` 运行中的临时审计暴露出可能的边界淬火污染，因此队列在该算例完成后暂停，转入零场控制、目标开放边界平衡和差分 ringdown。修正参数及停止条件见 `PARAMETER_CONFIRMATION.md`，修正矩阵见 `results/control_simulation_manifest.csv`。

运行命令：

```bash
bash hopfion_eigenmode_mechanism_20260612/run_stage1.sh
```

脚本串行使用单 GPU，日志写入 `logs/`，状态写入 `results/stage1_run_status.tsv`。每个成功输出目录包含 `.complete` 标记；重复执行时会跳过已完成项目。

修正批次使用 `run_recovery_pipeline.sh`。它按 C0-C3 阶段门执行，任何关键控制失败都会停止后续高开销仿真。

## 防捏造规则

- `173.66 GHz` 在空间阶段门通过前只称候选峰。
- 局域性阈值是本项目操作性标准，不声称是普适常数。
- 均匀背景出现同等级峰时，记录为背景/有限几何候选模式。
- 连续波强位移窗口不自动等于本征共振。

当前证据的权威入口见 `notes/evidence_status_20260612.md`。该文件明确覆盖早期文档在 ringdown 完成前对 `srcX 200 GHz` 的候选命名。带结果占位符的论文讨论框架见 `notes/paper_draft_cn.md`；占位符只能由本批次机器输出回填。
