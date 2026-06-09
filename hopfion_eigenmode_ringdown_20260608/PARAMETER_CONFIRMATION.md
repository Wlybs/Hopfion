# Hopfion Ringdown 本征模谱参数确认表

本结果包用于补足连续单频自旋波频扫之外的 weak-pulse 自由振荡谱。目标不是再做一个驱动响应峰，而是用 table-only sinc pulse + FFT 给出候选固有频率，再与已有 `srcX/srcZ` 自旋波频率扫描窗口对照。

| 项目 | Bx ringdown | Bz ringdown | 说明 |
|---|---:|---:|---|
| 激励类型 | uniform weak sinc pulse | uniform weak sinc pulse | 全局场脉冲，不定义点源/面源；用于本征模初筛 |
| 极化方向 | `B_ext = (B(t),0,0)` | `B_ext = (0,0,B(t))` | x 方向偏向 translation/twist 族；z 方向偏向 breathing/axial 族 |
| 脉冲形式 | `B0*sin(2*pi*fc*(t-t0))/(2*pi*fc*(t-t0))` | 同左 | 代码中分母加 `1e-30` 避免 `t=t0` 奇点 |
| 截止频率 `fc` | `2000 GHz` | `2000 GHz` | 覆盖到 `1500 GHz` 以上 |
| 峰值场强 `B0` | `5 mT` | `5 mT` | 采用 Raftrey-Fischer Hopfion pulse 量级；远弱于现有连续波 `1 T` 驱动 |
| 脉冲中心 `t0` | `2.37 ps` | `2.37 ps` | 避免恰落在 `0.05 ps` 采样网格上 |
| 初始态 | `/mnt/d/Research/Hopfion/20260105_frustrated_fm/centered_stability_test/stability_Ku10k.out/m000020.ovf` | 同左 | Q_H=1，Ku=10k，与现有频扫同源 |
| 几何尺寸 | `100^3` cells, `0.5 nm/cell`, `50 nm` cube | 同左 | frustrated FM 现有体系 |
| 材料参数 | `Ms=1.5e5 A/m`, `Aex=5e-12 J/m`, `Ku1=1e4 J/m^3`, `J2=-0.164J1`, `J4=-0.082J1` | 同左 | 复用现有 mx3 |
| 阻尼 | bulk `alpha=0.001`; 六面吸收层 `alpha=100` | 同左 | 与 spin_wave_dynamics 频扫边界阻尼一致 |
| 边界条件 | 无 `SetPBC`; 六面 `2.5 nm` 吸收层 | 同左 | 现有自旋波频扫脚本采用吸收边界；本次保持一致以利对照 |
| 仿真时长 | `0.5 ns` | `0.5 ns` | 频率分辨率约 `2 GHz` |
| table 采样 | `0.05 ps` | `0.05 ps` | Nyquist `10 THz`，足够覆盖 `1100 GHz` |
| table 内容 | 默认 `t,mx,my,mz` + `E_Total` | 同左 | 分析 `m_x/m_y/m_z/E_total` FFT |
| OVF 输出 | 不保存 | 不保存 | table-only，低开销；空间模图另需用户确认 |
| Mumax3 文件 | `mx3/ringdown_sinc_Bx.mx3` | `mx3/ringdown_sinc_Bz.mx3` | 由共享库 `scripts/resonance_analysis.py` 生成 |

参数选择结论：默认协议可直接执行。若后续需要严格线性响应验证，可追加 `B0=1 mT` 对照；本包先不扩大仿真矩阵。
