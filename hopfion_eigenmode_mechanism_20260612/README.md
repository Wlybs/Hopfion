# Hopfion 本征模与自旋波耦合机制

本结果包执行 2026-06-12 确认的方案 B。研究对象为 frustrated-FM 条件下的 Q_H=1 Hopfion，目标是把 `173.66 GHz` table-average ringdown 候选峰推进到可检验的空间本征模与传播自旋波耦合证据链。

## 当前批次

第一阶段包含七组仿真：弱场线性标度三组、Hopfion/均匀背景 ROI 空间模态两组、左右圆偏微波两组。参数见 `PARAMETER_CONFIRMATION.md`，机器可读列表见 `results/simulation_manifest.csv`。

运行命令：

```bash
bash hopfion_eigenmode_mechanism_20260612/run_stage1.sh
```

脚本串行使用单 GPU，日志写入 `logs/`，状态写入 `results/stage1_run_status.tsv`。每个成功输出目录包含 `.complete` 标记；重复执行时会跳过已完成项目。

## 防捏造规则

- `173.66 GHz` 在空间阶段门通过前只称候选峰。
- 局域性阈值是本项目操作性标准，不声称是普适常数。
- 均匀背景出现同等级峰时，记录为背景/有限几何候选模式。
- 连续波强位移窗口不自动等于本征共振。
