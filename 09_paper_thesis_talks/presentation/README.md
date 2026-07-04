# Hopfion 项目导师汇报包 (2026-06-02)

## 内容

- `talk.pptx` — 23 页 PowerPoint 汇报
- `talk_outline.md` — 页对页文字稿（PPT 的可读源）
- `key_code/` — 阅读型代码包（8 子目录 + figures）

## 使用方式

1. 打开 `talk.pptx` 直接看
2. 想了解某页背后的代码 → 进 `key_code/<目录>/`，看 README，再读 `.mx3` / `.py`
3. 想知道原始仿真输出位置 → 各 README 的"原始数据位置"段，指向 `/mnt/d/Research/Hopfion/<原 dir>/`

## 范围

本包聚焦 **Frustrated FM 体系**（无 DMI，竞争交换），覆盖：
- Frustrated FM Hopfion 稳态尺寸 / Ku 临界 / Q_H 验证
- 漂移机理（含被推翻的旧 bg=mz 结论）
- 自旋波驱动动力学（平面源 / 点源 / 多源 freq_switch）
- LIF 神经元 Phase 1 PASS + Phase 2 F1 FAILED
- 旧版本对标（系数符号陷阱）

不包括：
- DMI-FM (FeGe) Bloch Hopfion 稳定性（已从本次汇报移除）
- Wang 2019 STT 复现（已从本次汇报移除）
- 未启动方向（Q_H=2/4、LIF Phase 2 重设计、freq_switch v3 方案 A 调参）

## 作者

吴佳乐，2026-06-02
