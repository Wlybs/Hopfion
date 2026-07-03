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

## C2 最终结果

从同一个开放边界平衡态出发的 `0/1/2/5 mT` 四组 `Bz` 脉冲均已完整运行至 `0.5 ns`。对有场轨迹减去零场轨迹后，分析程序在约 `79.14 GHz` 找到共同差分峰，但该峰未通过线性门：`1/2/5 mT` 差分功率分别约为 `1.345e-9`、`1.180e-9` 和 `1.205e-9`，功率标度指数为 `-0.0635`，拟合 `R^2=0.5323`，`5 mT` 相对零场控制的 SNR 为 `2.64`。峰位离散仅 `0.282 GHz`，但幅度平方律和 SNR 均失败，因此机器判定 `passed=false`。

该阴性结果不支持把 `79.14 GHz` 或原始 `173.66 GHz` 峰称为已确认的 Hopfion 线性本征模。流水线已按门控停止，没有启动 1 ns 线宽、空间逐胞 FFT、圆偏选择或 stage2 CW/k 批次。机器可读结果见 `results/clean_linearity_gate.json`。

## 防捏造规则

- `173.66 GHz` 在空间阶段门通过前只称候选峰。
- 局域性阈值是本项目操作性标准，不声称是普适常数。
- 均匀背景出现同等级峰时，记录为背景/有限几何候选模式。
- 连续波强位移窗口不自动等于本征共振。
- 差分谱中出现峰位一致但场强平方律或 SNR 不通过时，只记录候选差分响应，不命名为本征频率。

当前证据的权威入口见 `notes/evidence_status_20260612.md`。该文件明确覆盖早期文档在 ringdown 完成前对 `srcX 200 GHz` 的候选命名。带结果占位符的论文讨论框架见 `notes/paper_draft_cn.md`；占位符只能由本批次机器输出回填。
