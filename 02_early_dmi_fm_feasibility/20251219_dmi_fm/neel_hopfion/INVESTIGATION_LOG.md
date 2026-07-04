# Néel Hopfion 复现尝试日志

**论文**: Khodzhaev & Turgut 2022, J. Phys.: Condens. Matter 34, 225805, Section 3
**状态**: ❌ 未成功复现（2026-03-10）

---

## 参数（论文 Section 3，已验证正确）

| 参数 | 值 |
|------|-----|
| Msat | 3×10⁵ A/m |
| Aex | 1.1×10⁻¹² J/m |
| Dind | 1.15×10⁻³ J/m² |
| Ku1 | 1×10⁶ J/m³ |
| 几何 | 圆柱盘 d=64nm, h=8nm, cell=0.5nm |
| B_ext | -0.12T（论文稳定范围 -30~-440mT） |

---

## 尝试的方案

| 方案 | 初始态 | 弛豫方法 | 结果 |
|------|--------|---------|------|
| v1 | torus R=12nm, r=4nm | Relax() α=0.5 | 湮灭 mz=0.995 |
| v2 | torus R=12nm, r=3nm | α=5.0 Run(0.5ns) | 0.22ns 内湮灭 |
| v3 | torus R=12nm, r=3nm | α=5.0 Run(0.5ns), B=-0.3T | 湮灭 |
| v4 | torus R=12nm, r=3nm | 阶梯 α: 0.001→0.01→0.1→0.5 | 背景翻转到 mz=-1 FM |
| Sutcliffe | Sutcliffe eq.3.3 L=8nm, 旋转90° | Relax() α=0.5 | 湮灭 mz=0.995 |
| 负 Dind | Sutcliffe, Dind=-1.15e-3 | Relax() | 螺旋态（非 Hopfion）|
| B=0 动力学 | Sutcliffe L=8nm | α=0.1 Run(0.05ns) | 短暂结构存活（mz_min=-1, 16%负mz）|
| B=0 Relax | Sutcliffe L=8nm | Relax() α=0.5 | meron 态（mz_min=0）|
| 保守极限 | torus r=3nm | α=0.001 Run(0.05ns) | 拓扑保存但全局进动 |

---

## 根本原因分析

### 1. 论文参考文献 [43] 不存在
论文文本引用 "known hopfion ansatz [43]" 但参考列表只有 42 篇。
这很可能是作者自己之前仿真的一个预计算 OVF 文件（不是公开文档），导致无法复现。

### 2. 物理上是浅势阱亚稳态
- κ = Dind / √(4·Aex·Ku1) = 1.15e-3 / 2.10e-3 = **0.548 < 1**
- 低于斯格明子自发成核阈值 → DMI 不足以自发稳定 Hopfion
- Hopfion 是浅势阱亚稳态：初始态必须**非常接近**平衡态才能收敛

### 3. PMA 软边界 vs frozenspins 硬边界
- Bloch Hopfion（FeGe，成功）：顶底层 frozenspins → 硬边界，Hopfion 拓扑锁定
- Néel Hopfion（Ir/Co/Pt）：PMA 软边界 → Hopfion 可沿 z 方向逃逸，无拓扑保护
- 任何通用 ansatz → 初始态不在正确能量盆 → 0.1ns 内湮灭

---

## 关键实验发现

- α=0.001（保守极限）：拓扑存活（mz_min=-1），但系统全局进动，不收敛
- B_ext=0 + α=0.1 Run(0.05ns)：mz_min=-1，16% 负 mz，结构短暂存活
- 所有 Relax() 或 α≥0.1 的弛豫：0.1ns 内湮灭到 FM 态（mz≈0.995）

---

## 若要继续复现

1. **联系论文作者**索取初始态 OVF（最直接）
2. 用 FeGe Bloch Hopfion OVF 做 90° 旋转 + 尺度插值，适配 64nm×8nm 几何
3. 尝试从 B_ext=0 开始场冷却（B_ext: 0 → -0.12T），观察是否在某个临界场成核

---

## 文件清单

| 文件 | 说明 |
|------|------|
| `gen_neel_hopfion_init.py` | torus ansatz R=12nm, r=4nm |
| `neel_hopfion_init.ovf` | 上述初始态 |
| `neel_hopfion_init_r3.ovf` | torus R=12nm, r=3nm（管壁与圆盘面 1nm 间距）|
| `neel_hopfion_sutcliffe.ovf` | Sutcliffe L=8nm 旋转 90°（核心 R≈5nm）|
| `run_neel_hopfion.mx3` | v1 脚本（Relax()）|
| `run_neel_hopfion_v2.mx3` | v2 脚本（α=5.0 Run）|
| `run_neel_hopfion_v3.mx3` | v3 脚本（r=3nm, B=-0.3T）|
| `run_neel_hopfion_v4.mx3` | v4 脚本（阶梯 α）|
| `run_neel_sutcliffe.mx3` | Sutcliffe 初始态版本 |
| `run_neel_hopfion.out/` | v1 仿真输出（已完成 2ns，Hopfion 湮灭）|
