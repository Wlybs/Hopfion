# 01_dmi_fm — DMI-FM (FeGe) Hopfion 稳定性

体系：B20 手征磁体 FeGe（Msat=384e3, Aex=8.78e-12, Dbulk=1.58e-3, λ=70 nm），含 DMI。

## 物理主题

证明 FeGe 中 Bloch Hopfion 稳定需三个条件缺一不可：
1. Sutcliffe 解析初始态
2. 顶底层 frozenspins (mz=±1 边界)
3. 退磁场开启 (EnableDemag=true)

几何 d=210 nm=3λ, h=70 nm=λ；2 ns 演化稳定。

## 脚本清单

| 文件 | 功能 |
|---|---|
| `gen_sutcliffe_hopfion.py` | 按 Sutcliffe eq.3.3 生成解析初始态 OVF |
| `run_analytic_relax.mx3` | 成功方案：Sutcliffe + frozen + demag + relax |
| `failed_bulk_pbc.mx3` | 失败案例：Bulk PBC，螺旋态竞争 |
| `failed_disc_ansatz.mx3` | 失败案例：环形 ansatz（错误 ansatz）|
| `neel_hopfion_v4.mx3` | Neel 型 Hopfion 稳定性扫描 v4 |
| `visualize_hopfion.py` | 3D 渲染 |

## 缺失

- `run_sutcliffe_with_demag.mx3` — 原计划文件，但 `successful_simulation/` 目录无此名脚本；`run_analytic_relax.mx3` 已涵盖含退磁场的成功方案

## 当前状态

- 成功方案：完成（2 ns 稳定）
- 失败尝试：已存档，作为对照
- Neel 型：9 runs 已跑（最大 125 帧）

## 原始数据位置

`/mnt/d/Research/Hopfion/20251219_dmi_fm/`
- successful_simulation/run_analytic_relax.out/
- failed_attempts/{bulk_pbc_tests, sutcliffe_disc_wrong_ansatz, toroidal_nanoring_approach}/
- isolated_hopfion_10lambda/
- neel_hopfion/
