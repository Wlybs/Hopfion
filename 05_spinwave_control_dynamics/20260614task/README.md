# 自旋波驱动 Hopfion 动力学与控制


## 项目目标

- 构造并可视化不同拓扑荷的 Hopfion 初始态。
- 使用 Mumax3 建立自旋波驱动 Hopfion 的基础仿真示例。
- 分析 Hopfion 在自旋波作用下的能量响应、轨迹位移和结构稳定性。
- 总结偏振、频率、振幅和源几何对 Hopfion 运动模式的影响。
- 为后续 Hopfion 轨迹控制、频率切换和器件化设想提供汇报材料。

## 核心结论

- 自旋波可以驱动 Hopfion 发生可观测位移。
- 面内激励会产生接近横向的类 Hall 漂移。
- 轴向源和频率选择可用于构造沿 z 方向的双向控制。
- 响应强度与频率、振幅和源几何有关，并非简单单调关系。
- 强驱动和频率切换末段可能引入结构畸变，稳定性仍需要后续调参。

## 目录结构

| 文件夹 | 内容 | 用途 |
|---|---|---|
| `01_hopfion_initial_scripts/` | Hopfion 初始态生成脚本、OVF 文件、三维可视化图和参考文献 | 说明初始构型来源 |
| `02_hopfion_spinwave_control_scripts/` | Mumax3 驱动脚本、分析脚本、稳定初始态和示例结果图 | 说明基础仿真与分析流程 |
| `03_hopfion_spinwave_results/` | `spinwave对hopfion的影响.pptx` | 最终汇报材料 |

## 推荐阅读顺序

1. 先看 `03_hopfion_spinwave_results/spinwave对hopfion的影响.pptx`，了解完整汇报逻辑和主要结论。
2. 再看 `02_hopfion_spinwave_control_scripts/example_result/` 中的两张示例图，理解单个仿真的能量响应和轨迹结果。
3. 最后查看 `01_hopfion_initial_scripts/`，确认 Hopfion 初始构型和可视化来源。

## 文件保留状态

本目录已按汇报用途做过清理。`03_hopfion_spinwave_results/` 中只保留最终 PPT；`02_hopfion_spinwave_control_scripts/example_result/` 中只保留结果图片，不保留原始 OVF 序列、日志和 table 过程文件。

## 注意事项

- 本目录重点服务汇报展示，不是完整原始数据归档。
- 若需要重新分析轨迹，需要重新运行仿真生成新的 OVF 和 table 输出。
- PPT 中更完整的频率扫描和控制结果来自上游 `spin_wave_dynamics/` 数据整理。
