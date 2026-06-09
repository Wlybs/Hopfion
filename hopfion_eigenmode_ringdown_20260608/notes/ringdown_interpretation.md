# Ringdown 本征模谱解读

## 方法边界

本分析使用 uniform weak sinc pulse 后的 table-only 自由振荡谱。峰位是候选固有频率，仍需空间分辨模图来命名为 translation/twist/breathing 等具体模式。

## 主通道候选峰

### Bx pulse: `m_x/m_y`

- 未检测到候选峰

- 未检测到候选峰

注：Bx 的 `m_x/m_y` 最高功率集中在 `6-8 GHz` 的低频趋势/漂移段，没有形成可用于本征频率命名的离散峰；同一 Bx run 的 `m_z/E_total` 中出现 `173.66 GHz` 主峰，但它不是 Bx 面内主通道峰。

### Bz pulse: `m_z/E_total`

- 1. `173.66 GHz`, power=1.884e-10
- 2. `38.82 GHz`, power=2.839e-12
- 3. `126.67 GHz`, power=1.769e-12
- 4. `10.22 GHz`, power=1.417e-12
- 5. `77.64 GHz`, power=1.290e-12

- 1. `173.66 GHz`, power=6.238e-37
- 2. `38.82 GHz`, power=7.392e-39
- 3. `126.67 GHz`, power=5.004e-39
- 4. `77.64 GHz`, power=4.148e-39
- 5. `10.22 GHz`, power=3.509e-39

## 与现有自旋波驱动窗口的对照

- `plane srcX 200 GHz`: 173.66 GHz, delta=26.34 GHz; 判定：未通过 10 GHz 对齐判据，暂按强驱动/传播/散射窗口处理。
- `plane srcX 1000 GHz`: 173.66 GHz, delta=826.34 GHz; 判定：未通过 10 GHz 对齐判据，暂按强驱动/传播/散射窗口处理。
- `plane srcZ 100 GHz`: 77.64 GHz, delta=22.36 GHz; 判定：未通过 10 GHz 对齐判据，暂按强驱动/传播/散射窗口处理。
- `plane srcZ 1100 GHz`: 173.66 GHz, delta=926.34 GHz; 判定：未通过 10 GHz 对齐判据，暂按强驱动/传播/散射窗口处理。

## 论文措辞建议

若某个驱动峰与 ringdown 峰在 `10 GHz` 内对齐，可写为候选共振耦合频率；若没有对齐，应写为强驱动、传播或散射窗口。`srcZ 100 GHz` 即使在位移或能量率上显著，也不能在没有正吸收和 ringdown 对齐前称为本征频率。
