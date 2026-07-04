# Hopfion 四个代表频率空间响应审计

本文件夹基于现有 OVF 保存帧分析四个代表性的平面自旋波驱动结果。
由于保存帧间隔约为 10 ps，这里的结果应理解为 stroboscopic deformation/localization map，而不是严格的驱动频率 FFT 本征模图。

## 分析对象

- `srcX_200GHz`：能量吸收审计给出的候选 resonant coupling 频率。
- `srcX_1000GHz`：高频强位移/控制窗口，但不是稳健正吸收峰。
- `srcZ_100GHz`：轴向异常响应，拟合能量斜率为负。
- `srcZ_1100GHz`：高频轴向强控制窗口，但不是稳健正吸收峰。

## 输出文件

- `results/mode_map_summary.csv`：逐频率的采样、形变、局域化、质心位移指标。
- `results/deformation_timeseries.csv`：逐帧形变和质心轨迹。
- `figures/mode_map_rms_xz_overview.png`
- `figures/deformation_timeseries_overview.png`
- `figures/srcX_200GHz_deformation_maps.png`
- `figures/srcX_1000GHz_deformation_maps.png`
- `figures/srcZ_100GHz_deformation_maps.png`
- `figures/srcZ_1100GHz_deformation_maps.png`

## 主要数值读法

- `srcX_200GHz`：核心振幅显著高于背景，但总响应并非完全局域。终态质心位移为 1.014 nm，主导分量为 dz；RMS 核心/背景振幅比为 10.037，核心差分能量占比为 0.084。
- `srcX_1000GHz`：核心振幅显著高于背景，但总响应并非完全局域。终态质心位移为 10.075 nm，主导分量为 dz；RMS 核心/背景振幅比为 14.031，核心差分能量占比为 0.152。
- `srcZ_100GHz`：核心振幅显著高于背景，但总响应并非完全局域。终态质心位移为 8.470 nm，主导分量为 dz；RMS 核心/背景振幅比为 10.802，核心差分能量占比为 0.096。
- `srcZ_1100GHz`：核心振幅显著高于背景，但总响应并非完全局域。终态质心位移为 13.905 nm，主导分量为 dz；RMS 核心/背景振幅比为 14.292，核心差分能量占比为 0.157。

## 关键限制

这四个代表频率全部低于可靠驱动频率 FFT mode map 所需的采样条件。
若要得到严格的本征模或频域模式图，需要补跑高时间分辨率 OVF 保存，最好每个驱动周期保存 8 到 16 帧。
