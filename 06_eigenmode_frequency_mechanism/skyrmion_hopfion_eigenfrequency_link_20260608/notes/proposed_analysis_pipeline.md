# 建议的 Hopfion 固有频率确认流程

## 目标

把现在的“驱动频率响应峰”升级为可写论文的“Hopfion 内禀模式频率”。

## Step 1：脉冲自由振荡谱

仿照 Mochizuki 2012：

- 对 `centered_stability_test/stability_Ku10k.out/m000020.ovf` 初态施加短脉冲。
- 脉冲方向至少包含 `x/y/z` 三个方向，必要时加圆偏振或相位差组合。
- 脉冲后关场自由演化，保存 `m(t)`、`E_total(t)`、Hopfion center、`R(t)`、`r(t)`、core count。
- 对这些时间序列做 FFT，找无持续驱动下的固有峰。

输出建议：

- `PSD_center_x/y/z(f)`
- `PSD_R(f), PSD_r(f)`
- `PSD_E(f)`
- 频峰汇总表

## Step 2：空间模态识别

对候选峰做 cell-wise Fourier amplitude / phase map：

- breathing-like：`R/r` 振荡强，空间振幅围绕 shell/core 近似同相。
- translation-like：质心强，Hopfion 形状变化较小。
- twist-like：质心和尺寸不一定最大，但 toroidal/poloidal phase 有明显旋转。
- scattering-dominated：能量/位移响应强，但局域模态图不集中在 Hopfion 内部，可能主要来自传播波和边界。

## Step 3：能量吸收谱重算

已有 `energy_absorption_summary.txt` 很有价值，但建议做一次更严格版本：

- 统一拟合窗口，例如去除前 `0.05-0.10 ns` 瞬态。
- 同时报告 `dE/dt` 和 `|dE/dt|`，避免符号约定混淆。
- 对 `srcX/srcZ` 平面源和点源分别画谱。
- 与位移谱同图标注，区分“吸收峰”和“位移峰”。

## Step 4：源几何与 k 谱

为了解释点源红移：

- 在无 Hopfion 对照场中记录 spin wave，做空间 FFT 得到 `I(k,f)`。
- 平面源应表现为较窄 `k` 分布。
- 点源应表现为宽角度/宽 `k` 分布。
- 把 `I(k,f)` 与 Hopfion 尺度估计 `k ~ 1/R`、`1/r` 对比。

## Step 5：写作建议

在论文或汇报中建议分三类术语：

- **eigenfrequency**：只给脉冲 FFT / 线性本征值 / 空间模态三者确认的峰。
- **resonant coupling frequency**：能量吸收峰或模式选择清楚，但空间模态尚未完全确认。
- **drive-response window**：位移大、可用于控制，但可能混合散射、传播、阻尼和非线性效应。

按这个标准，当前 `srcX 200 GHz` 可作为 resonant coupling 候选；`srcZ 100 GHz` 应先作为特殊非平衡响应窗口汇报；`700/800/1000/1100 GHz` 更适合作为 drive-response window 先行汇报。
