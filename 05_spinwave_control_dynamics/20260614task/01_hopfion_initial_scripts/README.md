# Hopfion 初始态生成与可视化

本目录用于保存 Hopfion 初始磁化构型的生成脚本、OVF 文件和三维可视化结果。它主要回答汇报中的两个问题：Hopfion 初始态从哪里来，以及不同拓扑荷的 Hopfion 在三维空间中是什么形态。

## 研究目标

- 根据解析模型生成 Hopfion 磁化场。
- 输出可用于后续 Mumax3 或其他微磁仿真的 OVF 初始态。
- 可视化 Hopfion 的等值面结构，检查环面形态和背景磁化方向。
- 展示 Q_H=1、Q_H=2 和 Q_H=4 三类代表性构型。

## 文件说明

| 文件 | 作用 |
|---|---|
| `create_hopfion.py` | 生成解析 Hopfion 初始态并输出 OVF 文件 |
| `draw_hopfion.py` | 读取 OVF 文件并绘制 Hopfion 三维等值面图 |
| `hopfion_Qh1_p1q1.ovf` | Q_H=1、p=1、q=1 的基本 Hopfion 构型 |
| `hopfion_Qh1_p1q1.png` | Q_H=1 构型的三维可视化图 |
| `hopfion_Qh2_p2q1_axisX.ovf` | Q_H=2、p=2、q=1 且轴向沿 x 的 Hopfion 构型 |
| `hopfion_Qh2_p2q1_axisX.png` | Q_H=2 构型的三维可视化图 |
| `hopfion_Qh4.ovf` | Q_H=4、p=2、q=2 的高拓扑荷 Hopfion 构型 |
| `hopfion_Qh4.png` | Q_H=4 构型的三维可视化图 |
| `Magnetic Hopfions as Local Rotations of the Uniform Magnetization Background.pdf` | 解析构造方法的理论参考文献 |

## 示例构型

| 拓扑荷 | 文件 | 说明 |
|---|---|---|
| Q_H=1 | `hopfion_Qh1_p1q1.ovf` | 最基础的 Hopfion 构型，用作结构展示和后续对照 |
| Q_H=2 | `hopfion_Qh2_p2q1_axisX.ovf` | 展示拓扑荷增加和轴向旋转后的构型差异 |
| Q_H=4 | `hopfion_Qh4.ovf` | 高拓扑荷示例，用于展示更复杂的缠绕结构 |

## 方法说明

`create_hopfion.py` 通过参数 `Qh`、`p`、`q`、`R`、`r` 和 `axis` 控制 Hopfion 的拓扑荷、缠绕数、环面尺寸和轴向。`draw_hopfion.py` 会读取 OVF 磁化场，并根据背景磁化方向渲染对应的等值面，因此可以处理不同轴向的 Hopfion 构型。

## 注意事项

- 本目录中的 OVF 文件是初始态示例，不等同于在具体材料参数下弛豫后的稳定态。
- 后续自旋波驱动仿真使用的是 `02_hopfion_spinwave_control_scripts/initial_hopfion.ovf`，它是经过居中和稳定性验证的 Q_H=1 初始态。
- 图片用于汇报展示和结构检查，定量分析应以 OVF 数据和后续仿真结果为准。
