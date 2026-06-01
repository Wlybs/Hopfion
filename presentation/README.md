# Hopfion 项目导师汇报包 (2026-06-01)

## 内容

- `talk.pptx` — 29 页 PowerPoint 汇报
- `talk_outline.md` — 页对页文字稿（PPT 的可读源）
- `key_code/` — 阅读型代码包（10 子目录 + figures）

## 使用方式

1. 打开 `talk.pptx` 直接看
2. 想了解某页背后的代码 → 进 `key_code/<目录>/`，看 README，再读 `.mx3` / `.py`
3. 想知道原始仿真输出位置 → 各 README 的"原始数据位置"段，指向 `/mnt/d/Research/Hopfion/<原 dir>/`

## 范围

本包覆盖 Hopfion 项目所有跑过的 184 个仿真，包括：
- 成功结果（毕设论文已用）
- 失败案例（毕设未提）
- 半完成实验（如 amplitude_sweep srcZ 部分 cron）
- 被推翻的旧结论（如漂移 bg=mz 结论）

不包括未启动的方向（Q_H=2/4、LIF Phase 2 重设计、freq_switch v3 方案 A 调参）。

## 作者

吴佳乐，2026-06-01
