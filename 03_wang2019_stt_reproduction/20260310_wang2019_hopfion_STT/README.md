# Wang 2019 PRL — Hopfion STT 动力学复现

**论文**: Wang XS, Qaiumzadeh A, Brataas A, *PRL* 123, 147203 (2019)
**标题**: Current-Driven Dynamics of Magnetic Hopfions
**状态**: 初始态已生成，仿真待运行

---

## 目标

复现论文 Fig. 3: STT 驱动下 Hopfion 沿 x 方向平移（无霍尔偏转，G=0）

---

## 材料参数（MnSi-like, 论文 Table I）

| 参数 | Bloch | Néel |
|------|-------|------|
| Aex  | 0.16 pJ/m | 0.16 pJ/m |
| Ms   | 1.51×10⁵ A/m | 1.51×10⁵ A/m |
| Kb   | 41 kJ/m³ | 20 kJ/m³ |
| D    | 0.115 mJ/m² (bulk) | 0.115 mJ/m² (interface) |
| Ks   | 0.5 mJ/m² (顶底面) | 0.5 mJ/m² (顶底面) |
| d    | 16 nm | 16 nm |

---

## Wang Ansatz（Eq. 4，H=+1 Néel Hopfion）

```
r' = (e^(R/wR) - 1) / (e^(ρ/wR) - 1)
z' = sign(z) × (e^(|z|/wh) - 1) / (e^(h/wh) - 1)

mx = 4r'[2z'sinφ + cosφ(r'²+z'²-1)] / (1+r'²+z'²)²
my = 4r'[-2z'cosφ + sinφ(r'²+z'²-1)] / (1+r'²+z'²)²
mz = 1 - 8r'² / (1+r'²+z'²)²
```

拟合参数: R=8.3nm, wR=5.6nm, h=6.3nm, hw=1.6nm
Bloch Hopfion: φ → φ + π/2（即 mx→-my, my→mx）

---

## 几何

- 纳米带: 128nm × 128nm × 16nm
- 格点: 256 × 256 × 32，cell=0.5nm
- PBC: x 方向（模拟无限长纳米带）

---

## STT 参数

- J = 10¹¹ A/m²（沿 x 方向）
- 自旋极化率 p = 0.12
- α = 0.05，β(ξ) = 0.1（β/α = 2）
- 仿真时间 15 ns

---

## 工作流

```bash
# Step 1: 生成初始态
source /mnt/d/Research/Hopfion/hopfion/bin/activate
cd init_states && python gen_wang_hopfion.py

# Step 2: 稳定化（在 Mumax3 中运行）
cd scripts
mumax3 run_bloch_hopfion.mx3   # 生成 bloch_hopfion_stable.ovf
mumax3 run_neel_hopfion.mx3    # 生成 neel_hopfion_stable.ovf

# Step 3: STT 动力学（约 2-4 小时）
mumax3 run_STT_dynamics.mx3

# Step 4: 分析
cd analysis && python analyze_hopfion_dynamics.py ../95_shared_scripts/run_STT_dynamics.out/
```

---

## 文件清单

| 文件 | 说明 |
|------|------|
| `init_states/gen_wang_hopfion.py` | Wang ansatz 生成器（Eq. 4） |
| `init_states/wang_neel_hopfion_init.ovf` | Néel Hopfion 初始态 |
| `init_states/wang_bloch_hopfion_init.ovf` | Bloch Hopfion 初始态 |
| `95_shared_scripts/run_bloch_hopfion.mx3` | Bloch 稳定化仿真 |
| `95_shared_scripts/run_neel_hopfion.mx3` | Néel 稳定化仿真 |
| `95_shared_scripts/run_STT_dynamics.mx3` | STT 动力学（Fig. 3） |
| `analysis/analyze_hopfion_dynamics.py` | 质心追踪 + 轨迹图 |
| `results/wang_ansatz_check.png` | 初始态 mz 切片验证图 |
