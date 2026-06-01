# 03_drift — Hopfion 漂移实验

## 物理主题

- 旧实验（alpha=5.0, R8r4, 不同时长）：曾得出"bg=mz 漂移、bg=mx/my 稳定"
- 控制变量重跑 unified_rerun（alpha=0.2, Ku=0, R3r2, 2 ns 统一参数）：4 组 (bg=mx,my,mz × axis 组合) **完全一致**
- **旧结论已推翻**：bg 方向无影响；真实机理是前 1 ns 轴向格点 4.75 nm 递举弛豫，之后钉扎

## 脚本清单

| 文件 | 功能 |
|---|---|
| `bg_mx_axis_x_stable.mx3` | 旧实验代表（10 ns, 200 帧）|
| `unified_rerun_bg_mx.mx3` | 控制变量统一模板：bg=mx |
| `unified_rerun_bg_mz.mx3` | 控制变量统一模板：bg=mz |
| `generate_xaxis_zbg_R3r2.py` | R3r2 + bg=mz 初始态生成 |
| `analyze_drift_4groups.py` | 4 组对比图生成（论文 fig3-4 / fig4-2 复用）|

## 当前状态

- 完成：bg_mx_axis_x_stable (10 ns), bg_my_axis_y_stable (1 ns), unified_rerun 4 组
- 旧结论修正已同步至 ch03 §3.2.3 与 ch06

## 原始数据位置

`20260105_frustrated_fm/drift_experiments/{bg_mx_axis_x_stable, bg_my_axis_y_stable, unified_rerun}/`
