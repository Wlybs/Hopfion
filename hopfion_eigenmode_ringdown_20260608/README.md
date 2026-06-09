# Hopfion Eigenmode Ringdown 2026-06-08

## 目的

本结果包用 weak sinc pulse + FFT ringdown 补做 Hopfion 候选本征模谱，区分“Hopfion 自己的自由振荡峰”和连续自旋波频扫中的强驱动窗口。

## 文件结构

| 路径 | 内容 |
|---|---|
| `PARAMETER_CONFIRMATION.md` | 仿真前参数确认表 |
| `mx3/ringdown_sinc_Bx.mx3` | uniform `Bx` sinc pulse table-only run |
| `mx3/ringdown_sinc_Bz.mx3` | uniform `Bz` sinc pulse table-only run |
| `mx3/ringdown_sinc_Bx.out/table.txt` | Bx ringdown 原始 table |
| `mx3/ringdown_sinc_Bz.out/table.txt` | Bz ringdown 原始 table |
| `analysis/generate_mx3.py` | 调用共享库生成 mx3 |
| `analysis/analyze_ringdown.py` | FFT、找峰、与驱动窗口对照 |
| `tests/test_ringdown_analysis.py` | 共享库 ringdown 分析测试 |
| `results/ringdown_peak_candidates.csv` | 候选峰位表 |
| `results/drive_vs_ringdown_comparison.csv` | 驱动窗口与 ringdown 峰对照 |
| `figures/ringdown_fft_drive_overlay.png` | ringdown 频谱与驱动窗口叠图 |
| `notes/ringdown_interpretation.md` | 中文物理解读 |
| `notes/spatial_mode_map_plan.md` | 空间模图方案，待用户确认 |

## 核心结果

- `Bz` ringdown 的 `m_z/E_total` 给出最清晰主峰：`173.66 GHz`。
- 弱候选峰包括 `38.82 GHz`, `126.67 GHz`, `77.64 GHz`, `10.22 GHz`，功率明显低于 `173.66 GHz` 主峰。
- `Bx` ringdown 的 `m_x/m_y` 主通道没有检测到可命名的离散候选峰；主要是 `6-8 GHz` 低频趋势/漂移段。
- 现有连续自旋波驱动窗口 `srcX 200`, `srcX 1000`, `srcZ 100`, `srcZ 1100 GHz` 均未通过 `10 GHz` ringdown 对齐判据。

## 物理判定

严格按本结果包的判据，现有强驱动窗口不能直接命名为 Hopfion 本征频率。`srcX 200 GHz` 仍可作为连续驱动下的正能量吸收/强响应窗口讨论，但它距离最近 ringdown 峰 `173.66 GHz` 约 `26.34 GHz`，不足以称为已确认本征共振。`srcZ 100 GHz` 与最近弱峰 `77.64 GHz` 相差约 `22.36 GHz`，且此前 energy absorption audit 已显示它是 `dE/dt<0` 的最强绝对能量率响应，不是正吸收峰。

下一步若要命名 `173.66 GHz` 模式为 breathing/twisting/axial mode，需要空间分辨模图。该步骤开销约 `18 GB/run` 起，已在 `notes/spatial_mode_map_plan.md` 中列出，等待用户确认。
