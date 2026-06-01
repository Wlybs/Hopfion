# Hopfion 导师汇报 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `presentation/` 下产出 (1) 29 页 PPT `talk.pptx`，(2) 阅读型代码包 `key_code/` 含 10 子目录与 README，完整呈现 Hopfion 项目所有 184 个仿真的真实结果（包括失败与半成品）。

**Architecture:** 两条独立任务线。代码包：从 4 个源目录拷代表性 `.mx3`/`.py` + 共享库 + 关键分析图，每多文件子目录配 README。PPT：朴素文本框+插图，29 页按 A-I 九块结构，纯结果叙事不掩盖失败。

**Tech Stack:** Bash (rsync, find, cp), Python (pptx 通过 superpowers:pptx skill), Markdown READMEs。

---

## File Structure

```
presentation/
├── README.md                           # 顶层使用说明（T15 创建）
├── talk.pptx                           # 最终 PPT（T17 生成）
├── talk_outline.md                     # 页对页文字稿（T16 创建）
└── key_code/
    ├── README.md                       # 总索引（T14）
    ├── 00_shared_libs/      (+README)  # T2
    ├── 01_dmi_fm/           (+README)  # T3
    ├── 02_frustrated_fm_stability/  (+README) # T4
    ├── 03_drift/            (+README)  # T5
    ├── 04_spin_wave_plane/  (+README)  # T6
    ├── 05_spin_wave_point/  (+README)  # T7
    ├── 06_multisource_freq_switch/  (+README) # T8
    ├── 07_stt_wang2019/     (+README)  # T9
    ├── 08_lif_neuron/       (+README)  # T10
    ├── 09_old_simulations/  (+README)  # T11
    └── figures/             (+README)  # T12-T13
```

## 源路径定位约定（执行者必读）

所有任务中提到"从 `XXX/` 拷"指相对 `/mnt/d/Research/Hopfion/`。如果具体 `.mx3` 文件名与本计划不符（重命名/移动），用 `find` 定位：

```bash
find /mnt/d/Research/Hopfion/<dir>/ -name "*.mx3" -not -path "*/\.out/*"
```

执行任何拷贝前先 `find` 验证源文件存在；找不到则记在该任务的"缺失文件"段，并跳到下一文件，**不阻塞整个任务**。

---

### Task 1: 建 presentation 根 + key_code 骨架

**Files:**
- Create: `/mnt/d/Research/Hopfion/presentation/`
- Create: `/mnt/d/Research/Hopfion/presentation/key_code/{00_shared_libs,01_dmi_fm,02_frustrated_fm_stability,03_drift,04_spin_wave_plane,05_spin_wave_point,06_multisource_freq_switch,07_stt_wang2019,08_lif_neuron,09_old_simulations,figures}/`

- [ ] **Step 1: 建目录**

```bash
cd /mnt/d/Research/Hopfion
mkdir -p presentation/key_code/{00_shared_libs,01_dmi_fm,02_frustrated_fm_stability,03_drift,04_spin_wave_plane,05_spin_wave_point,06_multisource_freq_switch,07_stt_wang2019,08_lif_neuron,09_old_simulations,figures}
```

- [ ] **Step 2: 验证骨架**

```bash
ls -d presentation/key_code/*/
```

Expected: 列出 11 个子目录（10 代码 + 1 figures）

- [ ] **Step 3: 加 .gitignore 排除 pptx 临时文件**

Write `/mnt/d/Research/Hopfion/presentation/.gitignore`:
```
*.pptx~
~$*.pptx
.~lock.*
```

- [ ] **Step 4: 提交骨架**

```bash
cd /mnt/d/Research/Hopfion
git add presentation/.gitignore
git commit -m "feat(presentation): scaffold key_code subdirectory tree"
```

---

### Task 2: 00_shared_libs — 拷共享分析库 + README

**Files:**
- Source: `/mnt/d/Research/Hopfion/scripts/*.py`
- Target: `presentation/key_code/00_shared_libs/`
- Create: `presentation/key_code/00_shared_libs/README.md`

- [ ] **Step 1: 定位共享库脚本**

```bash
ls /mnt/d/Research/Hopfion/scripts/*.py
```

Expected: 包括 `hopfion_analysis.py`, `compute_hopf_index.py`, `paper_style.py`, `post_sim_analysis.py`, `audit_sweep_params.py`（可能名字略有差异）

- [ ] **Step 2: 拷贝**

```bash
cd /mnt/d/Research/Hopfion
cp scripts/hopfion_analysis.py scripts/compute_hopf_index.py scripts/paper_style.py scripts/post_sim_analysis.py scripts/audit_sweep_params.py presentation/key_code/00_shared_libs/ 2>&1
```

如某文件缺失，跳过它，记在 README 的"缺失"段。

- [ ] **Step 3: 写 README**

Write `presentation/key_code/00_shared_libs/README.md`:

```markdown
# 00_shared_libs — 共享分析库

所有子目录的 Python 分析脚本依赖本目录的函数。使用前把本目录加到 PYTHONPATH：

```bash
export PYTHONPATH=/path/to/key_code/00_shared_libs:$PYTHONPATH
```

## 脚本清单

| 文件 | 功能 | 主要 API |
|---|---|---|
| `hopfion_analysis.py` | Hopfion 质心、R、r 提取，OVF 批量加载，PBC 坐标展开 | `compute_center()`, `extract_R_r()`, `load_ovf_series()` |
| `compute_hopf_index.py` | Hopf 不变量数值计算 Q_H | `compute_hopf()` |
| `paper_style.py` | 统一论文/PPT 图风格（衬线宋体+STIX+四边黑框+刻度朝内） | `apply_style()` |
| `post_sim_analysis.py` | 仿真完成后自动分析（生成轨迹/速度/能量图） | `analyze_run()` |
| `audit_sweep_params.py` | sweep 实验参数一致性审计 | `audit()` |

## 依赖

Python 3 + numpy, scipy, matplotlib, discretisedfield（不含包管理，需用户自备 hopfion venv）
```

- [ ] **Step 4: 验证 + 提交**

```bash
ls presentation/key_code/00_shared_libs/
git add presentation/key_code/00_shared_libs/
git commit -m "feat(presentation): copy shared analysis libs"
```

---

### Task 3: 01_dmi_fm — 拷脚本 + README

**Files:**
- Sources under: `20251219_dmi_fm/`
- Target: `presentation/key_code/01_dmi_fm/`

- [ ] **Step 1: 定位脚本**

```bash
find /mnt/d/Research/Hopfion/20251219_dmi_fm -maxdepth 4 -name "*.mx3" -not -path "*/\.out/*" | head -40
find /mnt/d/Research/Hopfion/20251219_dmi_fm -maxdepth 4 -name "*.py" -not -path "*/\.out/*" | head -20
```

记录实际路径。

- [ ] **Step 2: 拷代表脚本（重命名避同名冲突）**

```bash
cd /mnt/d/Research/Hopfion
SRC=20251219_dmi_fm
DST=presentation/key_code/01_dmi_fm

cp $SRC/Sutcliffe_Bloch_Hopfion/gen_sutcliffe_hopfion.py $DST/ 2>/dev/null || echo "miss: gen_sutcliffe"
cp $SRC/Sutcliffe_Bloch_Hopfion/run_analytic_relax.mx3 $DST/ 2>/dev/null || echo "miss: run_analytic_relax"
cp $SRC/Sutcliffe_Bloch_Hopfion/run_sutcliffe_with_demag.mx3 $DST/ 2>/dev/null || echo "miss: run_with_demag"
cp $SRC/Sutcliffe_Bloch_Hopfion/visualize_hopfion.py $DST/ 2>/dev/null || echo "miss: visualize"

# 失败案例代表（用 find 找一个）
find $SRC/failed_attempts/bulk_pbc_tests -name "*.mx3" | head -1 | xargs -I {} cp {} $DST/failed_bulk_pbc.mx3
find $SRC/failed_attempts/sutcliffe_disc_wrong_ansatz -name "*.mx3" | head -1 | xargs -I {} cp {} $DST/failed_disc_ansatz.mx3

# Neel 型代表
find $SRC/neel_hopfion -name "*v4*.mx3" -o -name "*.mx3" | head -1 | xargs -I {} cp {} $DST/neel_hopfion_v4.mx3

ls $DST/
```

- [ ] **Step 3: 写 README**

Write `presentation/key_code/01_dmi_fm/README.md`:

```markdown
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
| `run_sutcliffe_with_demag.mx3` | 含退磁场的 2 ns 动力学验证 |
| `failed_bulk_pbc.mx3` | 失败案例：Bulk PBC，螺旋态竞争 |
| `failed_disc_ansatz.mx3` | 失败案例：环形 ansatz |
| `neel_hopfion_v4.mx3` | Neel 型 Hopfion 稳定性扫描 |
| `visualize_hopfion.py` | 3D 渲染 |

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
```

- [ ] **Step 4: 提交**

```bash
git add presentation/key_code/01_dmi_fm/
git commit -m "feat(presentation): copy DMI-FM scripts + README"
```

---

### Task 4: 02_frustrated_fm_stability — 拷脚本 + README

**Files:**
- Sources under: `20260105_frustrated_fm/{size_sweep,centered_stability_test,anisotropy_study}/`
- Target: `presentation/key_code/02_frustrated_fm_stability/`

- [ ] **Step 1: 定位**

```bash
find /mnt/d/Research/Hopfion/20260105_frustrated_fm/size_sweep -name "*.mx3" -not -path "*/\.out/*"
find /mnt/d/Research/Hopfion/20260105_frustrated_fm/centered_stability_test -name "*.mx3" -not -path "*/\.out/*"
find /mnt/d/Research/Hopfion/20260105_frustrated_fm/anisotropy_study -name "*.mx3" -not -path "*/\.out/*" | head -20
```

- [ ] **Step 2: 拷脚本**

```bash
cd /mnt/d/Research/Hopfion
SRC=20260105_frustrated_fm
DST=presentation/key_code/02_frustrated_fm_stability

# size_sweep
find $SRC/size_sweep -name "*R8r4*Ku0*.mx3" -not -path "*/\.out/*" | head -1 | xargs -I {} cp {} $DST/size_sweep_R8r4_Ku0.mx3
find $SRC/size_sweep -name "*R12r5*Ku0*.mx3" -not -path "*/\.out/*" | head -1 | xargs -I {} cp {} $DST/size_sweep_R12r5_Ku0.mx3

# centered_stability
find $SRC/centered_stability_test -name "*Ku0*.mx3" -not -path "*/\.out/*" | head -1 | xargs -I {} cp {} $DST/stability_Ku0.mx3
find $SRC/centered_stability_test -name "*Ku10k*.mx3" -not -path "*/\.out/*" | head -1 | xargs -I {} cp {} $DST/stability_Ku10k.mx3
find $SRC/centered_stability_test -name "*Ku50k*.mx3" -not -path "*/\.out/*" | head -1 | xargs -I {} cp {} $DST/stability_Ku50k.mx3
find $SRC/centered_stability_test -name "compute_qh_timeseries.py" | head -1 | xargs -I {} cp {} $DST/

# 初始态生成
find $SRC -name "gen_hopfion*R8r4*.py" -o -name "create_hopfion*.py" | head -1 | xargs -I {} cp {} $DST/gen_hopfion_R8r4.py

# Ku critical sweep template
find $SRC/anisotropy_study/ku_critical_sweep -name "generate_sweep.py" -o -name "*template*.mx3" | head -1 | xargs -I {} cp {} $DST/ku_critical_template.mx3

# size_vs_ku template
find $SRC/anisotropy_study/size_vs_ku -name "*.mx3" -not -path "*/\.out/*" | head -1 | xargs -I {} cp {} $DST/size_vs_ku_template.mx3

ls $DST/
```

- [ ] **Step 3: 写 README**

Write `presentation/key_code/02_frustrated_fm_stability/README.md`:

```markdown
# 02_frustrated_fm_stability — 竞争交换 FM Hopfion 稳定性

体系：100³ 格点, 0.5 nm/cell, PBC(1,1,1), Ms=1.5e5, Aex=5e-12, J2=-0.164·J1, J4=-0.082·J1，无 DMI。

## 物理主题

- 固有吸引子：R8r4 / R12r5 初始 → 都收敛到 R=2.60 nm (Ku=0)
- 居中稳态：Ku=0/10k/50k 三组 1 ns 都通过稳态判据（漂移 <2 nm）
- Ku=10k 选为后续自旋波仿真的初始态（最稳，z 漂移 -0.019 nm）
- Ku 临界趋势：Ku 增大 → Hopfion 收缩 → R8r4 体系 ~52–55k 区间坍塌（13 点扫描）
- 拓扑荷：当前体系仅 Q_H=1 验证；Q_H=2/4 从未仿真

## 脚本清单

| 文件 | 功能 |
|---|---|
| `gen_hopfion_R8r4.py` | 解析 Hopfion 初始态生成（R=8nm, r=4nm） |
| `size_sweep_R8r4_Ku0.mx3` | 尺寸扫描：R8r4 初始 → 吸引子 |
| `size_sweep_R12r5_Ku0.mx3` | 尺寸扫描：R12r5 初始 → 吸引子 |
| `stability_Ku0.mx3` | 居中稳态 Ku=0（呼吸模式）|
| `stability_Ku10k.mx3` | 居中稳态 Ku=10k（最稳，SW 初始态来源）|
| `stability_Ku50k.mx3` | 居中稳态 Ku=50k |
| `ku_critical_template.mx3` | Ku 临界扫描模板（13 点 0→58k）|
| `size_vs_ku_template.mx3` | R(Ku) 依赖扫描模板 |
| `compute_qh_timeseries.py` | Hopfion 拓扑荷密度时序分析 |

## 当前状态

- size_sweep: 2 runs 完成
- centered_stability: 3 runs 完成
- ku_critical_sweep: 13 runs 完成
- size_vs_ku: 6 runs 完成
- Q_H=1 验证完成；Q_H=2/4 未启动

## 原始数据位置

`20260105_frustrated_fm/{size_sweep, centered_stability_test, anisotropy_study/{ku_critical_sweep, size_vs_ku}}/`
```

- [ ] **Step 4: 提交**

```bash
git add presentation/key_code/02_frustrated_fm_stability/
git commit -m "feat(presentation): copy frustrated FM stability scripts + README"
```

---

### Task 5: 03_drift — 拷脚本 + README

**Files:**
- Sources under: `20260105_frustrated_fm/drift_experiments/`
- Target: `presentation/key_code/03_drift/`

- [ ] **Step 1: 定位**

```bash
find /mnt/d/Research/Hopfion/20260105_frustrated_fm/drift_experiments -name "*.mx3" -not -path "*/\.out/*"
find /mnt/d/Research/Hopfion/20260105_frustrated_fm/drift_experiments -name "*.py"
```

- [ ] **Step 2: 拷脚本**

```bash
cd /mnt/d/Research/Hopfion
SRC=20260105_frustrated_fm/drift_experiments
DST=presentation/key_code/03_drift

find $SRC/bg_mx_axis_x_stable -name "*.mx3" -not -path "*/\.out/*" | head -1 | xargs -I {} cp {} $DST/bg_mx_axis_x_stable.mx3
find $SRC/unified_rerun -name "*.mx3" -not -path "*/\.out/*" | head -1 | xargs -I {} cp {} $DST/unified_rerun_template.mx3
find $SRC -name "analyze_drift_unified_v2.py" -o -name "analyze_drift*.py" | head -1 | xargs -I {} cp {} $DST/analyze_drift_unified_v2.py

ls $DST/
```

- [ ] **Step 3: 写 README**

Write `presentation/key_code/03_drift/README.md`:

```markdown
# 03_drift — Hopfion 漂移实验

## 物理主题

- 旧实验（alpha=5.0, R8r4, 不同时长）：曾得出"bg=mz 漂移、bg=mx/my 稳定"
- 控制变量重跑（unified_rerun, alpha=0.2, Ku=0, R3r2, 2 ns 统一参数）：
  4 组 (bg=mx,my,mz × axis 组合) **完全一致**
- **旧结论已推翻**：bg 方向无影响；真实机理是前 1 ns 轴向格点 4.75 nm 递举弛豫，之后钉扎

## 脚本清单

| 文件 | 功能 |
|---|---|
| `bg_mx_axis_x_stable.mx3` | 旧实验代表（10 ns, 200 帧）|
| `unified_rerun_template.mx3` | 控制变量统一模板（4 组共用） |
| `analyze_drift_unified_v2.py` | 4 组对比图生成（fig3-4）|

## 当前状态

- 完成：bg_mx_axis_x_stable, bg_my_axis_y_stable, unified_rerun 4 组
- 旧结论修正同步至 ch03 §3.2.3 与 ch06

## 原始数据位置

`20260105_frustrated_fm/drift_experiments/{bg_mx_axis_x_stable, bg_my_axis_y_stable, unified_rerun}/`
```

- [ ] **Step 4: 提交**

```bash
git add presentation/key_code/03_drift/
git commit -m "feat(presentation): copy drift experiment scripts + README"
```

---

### Task 6: 04_spin_wave_plane — 拷脚本 + README

**Files:**
- Sources under: `20260105_frustrated_fm/spin_wave_dynamics/{drive_selection,freq_sweep,amplitude_sweep}/plane_wave/`
- Target: `presentation/key_code/04_spin_wave_plane/`

- [ ] **Step 1: 定位**

```bash
SW=/mnt/d/Research/Hopfion/20260105_frustrated_fm/spin_wave_dynamics
find $SW/drive_selection/plane_wave -name "*.mx3" -not -path "*/\.out/*" | head -5
find $SW/freq_sweep/plane_wave/srcX -name "*.mx3" -not -path "*/\.out/*" | head -5
find $SW/freq_sweep/plane_wave/srcZ -name "*.mx3" -not -path "*/\.out/*" | head -5
find $SW/amplitude_sweep/plane_wave -name "*.mx3" -not -path "*/\.out/*" | head -10
```

- [ ] **Step 2: 拷脚本**

```bash
cd /mnt/d/Research/Hopfion
SW=20260105_frustrated_fm/spin_wave_dynamics
DST=presentation/key_code/04_spin_wave_plane

find $SW/drive_selection/plane_wave -name "*.mx3" -not -path "*/\.out/*" | head -1 | xargs -I {} cp {} $DST/drive_selection_template.mx3
find $SW/freq_sweep/plane_wave/srcX -name "*.mx3" -not -path "*/\.out/*" | head -1 | xargs -I {} cp {} $DST/freq_sweep_srcX_template.mx3
find $SW/freq_sweep/plane_wave/srcZ -name "*fine*.mx3" -not -path "*/\.out/*" 2>/dev/null | head -1 | xargs -I {} cp {} $DST/freq_sweep_srcZ_fine_template.mx3
find $SW/amplitude_sweep/plane_wave -name "*440*.mx3" -not -path "*/\.out/*" 2>/dev/null | head -1 | xargs -I {} cp {} $DST/amplitude_sweep_srcX_440GHz.mx3
find $SW/amplitude_sweep/plane_wave -name "*1100*.mx3" -not -path "*/\.out/*" 2>/dev/null | head -1 | xargs -I {} cp {} $DST/amplitude_sweep_srcZ_1100GHz.mx3

# 分析脚本
find $SW -name "analyze_freq_response.py" -o -name "analyze_motion_mode.py" | head -1 | xargs -I {} cp {} $DST/analyze_freq_response.py
find $SW -name "analyze_amplitude*.py" | head -1 | xargs -I {} cp {} $DST/analyze_amplitude_scaling.py

ls $DST/
```

- [ ] **Step 3: 写 README**

Write `presentation/key_code/04_spin_wave_plane/README.md`:

```markdown
# 04_spin_wave_plane — 平面源自旋波驱动

公共初始态：`02_frustrated_fm_stability/stability_Ku10k.mx3` 输出的 m000020.ovf。

## 物理主题

- 方向选择性：vibX 强耦合 / vibZ 无耦合 / srcX≡srcY（5 组实验）
- srcX 频率响应（02ns 10 频率 + 05ns 4 频率）：100-200/1000 GHz 强响应，400-600 GHz 死区
- srcZ 频率响应（coarse 10 + fine 10 = 20 频率）：1100 GHz 最强 -18.1 nm，多个死区
- 幅度扫描 srcX @440 GHz（6 点 B=0.05–2.0 T）：**旧 v∝B¹·⁹⁹ 拟合已推翻**（数据不足，Bc∈(0.1,0.2)T 方向反转阈值未精确定位）
- 幅度扫描 srcZ @1100 GHz：cron 跑，可能部分缺失
- 单源双向 z 可控：srcX→+z, srcZ→-z

## 脚本清单

| 文件 | 功能 |
|---|---|
| `drive_selection_template.mx3` | 方向选择性扫描模板 |
| `freq_sweep_srcX_template.mx3` | srcX 频率扫描模板 |
| `freq_sweep_srcZ_fine_template.mx3` | srcZ 精细频率扫描（25 GHz 间隔）|
| `amplitude_sweep_srcX_440GHz.mx3` | srcX 幅度扫描 @440 GHz |
| `amplitude_sweep_srcZ_1100GHz.mx3` | srcZ 幅度扫描 @1100 GHz |
| `analyze_freq_response.py` | 频率响应谱 / 运动模式分析 |
| `analyze_amplitude_scaling.py` | 幅度-位移标度律拟合 |

## 当前状态

- drive_selection: 5 runs 完成
- freq_sweep srcX: 14 runs 完成（02ns 10 + 05ns 4）
- freq_sweep srcZ: 20 runs 完成
- amplitude_sweep srcX @440GHz: 6 runs 完成
- amplitude_sweep srcZ @1100GHz: cron 中（可能不全）

## 原始数据位置

`20260105_frustrated_fm/spin_wave_dynamics/{drive_selection, freq_sweep, amplitude_sweep}/plane_wave/`
```

- [ ] **Step 4: 提交**

```bash
git add presentation/key_code/04_spin_wave_plane/
git commit -m "feat(presentation): copy plane wave spin wave scripts + README"
```

---

### Task 7: 05_spin_wave_point — 拷脚本 + README

**Files:**
- Sources under: `20260105_frustrated_fm/spin_wave_dynamics/{freq_sweep,amplitude_sweep}/point_source/`
- Target: `presentation/key_code/05_spin_wave_point/`

- [ ] **Step 1: 定位**

```bash
SW=/mnt/d/Research/Hopfion/20260105_frustrated_fm/spin_wave_dynamics
find $SW/freq_sweep/point_source -name "*.mx3" -not -path "*/\.out/*" | head -10
find $SW/amplitude_sweep/point_source -name "*.mx3" -not -path "*/\.out/*" | head -10
```

- [ ] **Step 2: 拷脚本**

```bash
cd /mnt/d/Research/Hopfion
SW=20260105_frustrated_fm/spin_wave_dynamics
DST=presentation/key_code/05_spin_wave_point

find $SW/freq_sweep/point_source -name "*template*.mx3" -not -path "*/\.out/*" 2>/dev/null | head -1 | xargs -I {} cp {} $DST/point_source_template.mx3
find $SW/freq_sweep/point_source/srcX -name "*.mx3" -not -path "*/\.out/*" 2>/dev/null | head -1 | xargs -I {} cp {} $DST/freq_sweep_srcX_point.mx3
find $SW/freq_sweep/point_source/srcZ -name "*.mx3" -not -path "*/\.out/*" 2>/dev/null | head -1 | xargs -I {} cp {} $DST/freq_sweep_srcZ_point.mx3
find $SW/amplitude_sweep/point_source -name "*1100*.mx3" -not -path "*/\.out/*" 2>/dev/null | head -1 | xargs -I {} cp {} $DST/amplitude_sweep_point_1100GHz.mx3

ls $DST/
```

- [ ] **Step 3: 写 README**

Write `presentation/key_code/05_spin_wave_point/README.md`:

```markdown
# 05_spin_wave_point — 点源自旋波驱动

点源：`DefRegionCell(7, 30, 50, 50)`，单格 0.5 nm³，B_amp=500 T（对比平面源 B_amp=1 T 薄片层）。

## 物理主题

- srcX 点源 freq sweep（10 频率）：700 GHz 最强 5.71 nm，全频段 +z，**死区消失**（对比平面源 400-600 GHz 死区），Hall 角 69-89°
- srcZ 点源 freq sweep（10 频率）：800 GHz 最强 -7.31 nm，方向分布复杂（6+z/3-z），Hall 角 9-40°（对比平面源 ~1°）
- amplitude sweep @1100 GHz：B100/200/300/400 完成；**B500 停在 0.433 ns 未续跑；B700/B1000/B2000 未跑**
- 核心结论：振荡方向选择性、Hall 角等本质由 Hopfion 拓扑结构决定，不依赖激励几何；点源改变共振频率分布细节

## 脚本清单

| 文件 | 功能 |
|---|---|
| `point_source_template.mx3` | 点源激发通用模板 |
| `freq_sweep_srcX_point.mx3` | srcX 点源频率扫描 |
| `freq_sweep_srcZ_point.mx3` | srcZ 点源频率扫描 |
| `amplitude_sweep_point_1100GHz.mx3` | 点源幅度扫描 |

## 当前状态

- srcX freq sweep: 10 runs 完成（B 设备数据迁回 2026-04-09）
- srcZ freq sweep: 10 runs 完成
- amplitude sweep: 4/7 完成 + 1 中断 + 3 未跑

## 原始数据位置

`20260105_frustrated_fm/spin_wave_dynamics/{freq_sweep, amplitude_sweep}/point_source/`
```

- [ ] **Step 4: 提交**

```bash
git add presentation/key_code/05_spin_wave_point/
git commit -m "feat(presentation): copy point source spin wave scripts + README"
```

---

### Task 8: 06_multisource_freq_switch — 拷脚本 + README

**Files:**
- Sources under: `20260105_frustrated_fm/spin_wave_dynamics/multisource_control/`
- Target: `presentation/key_code/06_multisource_freq_switch/`

- [ ] **Step 1: 定位**

```bash
MS=/mnt/d/Research/Hopfion/20260105_frustrated_fm/spin_wave_dynamics/multisource_control
find $MS -name "*.mx3" -not -path "*/\.out/*"
find $MS -name "*.py"
```

- [ ] **Step 2: 拷脚本**

```bash
cd /mnt/d/Research/Hopfion
MS=20260105_frustrated_fm/spin_wave_dynamics/multisource_control
DST=presentation/key_code/06_multisource_freq_switch

find $MS/baseline -name "*.mx3" -not -path "*/\.out/*" | head -1 | xargs -I {} cp {} $DST/baseline_dual_src.mx3
find $MS/bidirectional_z -name "*v1*.mx3" -not -path "*/\.out/*" | head -1 | xargs -I {} cp {} $DST/freq_switch_v1.mx3
find $MS/bidirectional_z -name "*v2*.mx3" -not -path "*/\.out/*" | head -1 | xargs -I {} cp {} $DST/freq_switch_v2.mx3
find $MS/bidirectional_z -name "*v3*.mx3" -not -path "*/\.out/*" | head -1 | xargs -I {} cp {} $DST/freq_switch_v3.mx3
find $MS -name "analyze*.py" | head -1 | xargs -I {} cp {} $DST/analyze_freq_switch.py

ls $DST/
```

- [ ] **Step 3: 写 README**

Write `presentation/key_code/06_multisource_freq_switch/README.md`:

```markdown
# 06_multisource_freq_switch — 双向 z 控制 / 多源 freq_switch

## 物理主题

- baseline (srcX + srcZ 同时)：双源仅 +z，未实现反转
- bidirectional_z v1：双源叠加，同样未逆转
- v2 (freq_switch, Phase1=0.10ns/Phase2=0.40ns)：Phase1 仅 +0.04 nm（太短）/ Phase2 -18.7 nm → **双向 FAILED**
- v3 (Phase1=0.50ns/Phase2=0.50ns)：
  - Phase1 100 GHz: 0 → +17.6 nm **PASS**
  - Phase2 1100 GHz: +17.6 → -12.9 nm 反转 **SUCCESS**
  - **t ≈ 0.91 ns Hopfion 拓扑结构坍塌 core=0**
  - 毕设展示截到 0.80 ns，未提坍塌（叙事截断）
  - 本汇报完整呈现到 1.00 ns

## 失败根因

1. 1100 GHz 推 -z 力量过强（耦合 ~74 nm/ns vs Phase1 ~35 nm/ns）
2. Phase2 持续 0.30 ns 太久，形变累积过临界

## 后续未实施候选方案 A

- Phase2 脉宽 0.30 → 0.05/0.10 ns 扫描
- Phase2 振幅 1 T → 0.5/0.3 T
- Phase2 后接 0 场维持 0.5 ns
- 验证 LIF 充放电循环

## 脚本清单

| 文件 | 功能 |
|---|---|
| `baseline_dual_src.mx3` | 双源基线（srcX + srcZ 同时）|
| `freq_switch_v1.mx3` | 双源叠加版 |
| `freq_switch_v2.mx3` | freq_switch v2（Phase1 太短） |
| `freq_switch_v3.mx3` | freq_switch v3（**0.91 ns 坍塌案例**）|
| `analyze_freq_switch.py` | 切换序列分析（trajectory + core_count）|

## 原始数据位置

`20260105_frustrated_fm/spin_wave_dynamics/multisource_control/{baseline, bidirectional_z}/`
```

- [ ] **Step 4: 提交**

```bash
git add presentation/key_code/06_multisource_freq_switch/
git commit -m "feat(presentation): copy multisource freq_switch scripts + README"
```

---

### Task 9: 07_stt_wang2019 — 拷脚本 + README

**Files:**
- Sources under: `20260310_wang2019_hopfion_STT/`
- Target: `presentation/key_code/07_stt_wang2019/`

- [ ] **Step 1: 定位 + 拷**

```bash
cd /mnt/d/Research/Hopfion
SRC=20260310_wang2019_hopfion_STT
DST=presentation/key_code/07_stt_wang2019

find $SRC -name "*.mx3" -not -path "*/\.out/*" | head -5
find $SRC -name "run_bloch_hopfion.mx3" -not -path "*/\.out/*" | head -1 | xargs -I {} cp {} $DST/run_bloch_hopfion.mx3
find $SRC -name "run_bloch_hopfion_v2.mx3" -not -path "*/\.out/*" | head -1 | xargs -I {} cp {} $DST/run_bloch_hopfion_v2.mx3

ls $DST/
```

- [ ] **Step 2: 写 README**

Write `presentation/key_code/07_stt_wang2019/README.md`:

```markdown
# 07_stt_wang2019 — Spin Transfer Torque 驱动 Bloch Hopfion

参考：Wang et al. 2019 PRL（Hopfion STT 动力学）。

## 物理主题

复现 Wang 2019 PRL：STT 电流驱动 Bloch Hopfion 沿电流方向运动。

## 脚本清单

| 文件 | 功能 |
|---|---|
| `run_bloch_hopfion.mx3` | v1（91 帧）|
| `run_bloch_hopfion_v2.mx3` | v2（32 帧，参数调整）|

## 当前状态

- v1, v2 均完成
- 结论：STT 可驱动 Bloch Hopfion；后续未深入

## 原始数据位置

`20260310_wang2019_hopfion_STT/{run_bloch_hopfion.out, run_bloch_hopfion_v2.out}/`
```

- [ ] **Step 3: 提交**

```bash
git add presentation/key_code/07_stt_wang2019/
git commit -m "feat(presentation): copy STT Wang2019 scripts + README"
```

---

### Task 10: 08_lif_neuron — 拷脚本 + README

**Files:**
- Sources under: `lif_neuron_hopfion/`
- Target: `presentation/key_code/08_lif_neuron/`

- [ ] **Step 1: 定位 + 拷**

```bash
cd /mnt/d/Research/Hopfion
SRC=lif_neuron_hopfion
DST=presentation/key_code/08_lif_neuron

find $SRC -name "*.mx3" -not -path "*/\.out/*"
find $SRC -name "*.py" -not -path "*/\.out/*"

find $SRC -name "gradient_ku_drive_release.mx3" | head -1 | xargs -I {} cp {} $DST/
find $SRC -name "uniform_ku_drive_release.mx3" | head -1 | xargs -I {} cp {} $DST/
find $SRC -name "lif_pulse_train.mx3" | head -1 | xargs -I {} cp {} $DST/
find $SRC -name "analyze_leaky_drift.py" | head -1 | xargs -I {} cp {} $DST/
find $SRC -name "analyze_lif_cycle.py" | head -1 | xargs -I {} cp {} $DST/

ls $DST/
```

- [ ] **Step 2: 写 README**

Write `presentation/key_code/08_lif_neuron/README.md`:

```markdown
# 08_lif_neuron — Hopfion 作 LIF 神经元（基于 Skyrmion 专利 CN 118284316 A 改写）

## Phase 1: 梯度 Ku 恢复力验证 (PASS, 2026-04-19)

drive-release 实验：100 GHz 驱动 0.3 ns → 关掉 2 ns 自由弛豫，对比 gradient Ku vs uniform Ku。

**结论：PASS** — 梯度 Ku 提供恢复力，gradient 在 +7.8 nm 收敛（near-critical damping），uniform 在原点附近振荡（underdamped）。

**意外发现**：Hopfion 偏好低 Ku 区（gradient 平衡在 Ku≈7500 端），与初始假设"Hopfion 趋向高 Ku 区"相反。Phase 2 设计因此反转。

## Phase 2: 完整 LIF 循环 (F1 FAILED, 2026-04-19)

`lif_pulse_train.mx3`：4 脉冲 @1100 GHz integrate（0.15 ns on / 0.25 ns gap） + 100 GHz fire + 不应期。

**FAILED**：t=1.089 ns kill。失败原因：
1. 1100 GHz 推 -z 方向与梯度 Ku 恢复力 +z 同向（不是反向），integrate 期持续 overshoot
2. Phase1 V2 在 100 GHz 下的"低 Ku 偏好"不能外推到 1100 GHz

## Phase 2 重设计候选（未开工）

- 方案 A：反转源-初态相对位置（initial 在 -z 端，100 GHz integrate +z, 梯度自然回拉）
- 方案 B：降 1100 GHz 幅度 + 延长 gap
- 方案 C：缩短 pulse 宽（0.15 → 0.05 ns）
- 方案 D：双频叠加抑制残余自旋波

## 脚本清单

| 文件 | 功能 |
|---|---|
| `gradient_ku_drive_release.mx3` | Phase 1 V2 (梯度版)，PASS |
| `uniform_ku_drive_release.mx3` | Phase 1 V2 (均匀版)，对照 |
| `lif_pulse_train.mx3` | Phase 2 F1，FAILED（保留作设计迭代样本）|
| `analyze_leaky_drift.py` | drive-release 轨迹对比 |
| `analyze_lif_cycle.py` | LIF 循环分析（--compare F1 vs F3）|

## 原始数据位置

`lif_neuron_hopfion/{gradient_ku_verification, lif_cycle_demo}/`
```

- [ ] **Step 3: 提交**

```bash
git add presentation/key_code/08_lif_neuron/
git commit -m "feat(presentation): copy LIF neuron scripts + README"
```

---

### Task 11: 09_old_simulations — 拷脚本 + README

**Files:**
- Sources under: `20260105_frustrated_fm/old_results/My_old_simulation/`, `deviceB_package/`
- Target: `presentation/key_code/09_old_simulations/`

- [ ] **Step 1: 定位**

```bash
find /mnt/d/Research/Hopfion/20260105_frustrated_fm/old_results -name "*.mx3" -not -path "*/\.out/*" | head -10
find /mnt/d/Research/Hopfion -path "*deviceB*" -name "*.mx3" -not -path "*/\.out/*" | head -5
```

- [ ] **Step 2: 拷脚本**

```bash
cd /mnt/d/Research/Hopfion
DST=presentation/key_code/09_old_simulations

find 20260105_frustrated_fm/old_results -path "*srcX*" -name "*.mx3" -not -path "*/\.out/*" | head -1 | xargs -I {} cp {} $DST/My_old_simulation_srcX.mx3
find 20260105_frustrated_fm/old_results -path "*srcZ*" -name "*.mx3" -not -path "*/\.out/*" | head -1 | xargs -I {} cp {} $DST/My_old_simulation_srcZ.mx3
find . -path "*deviceB*" -name "*.mx3" -not -path "*/\.out/*" 2>/dev/null | head -1 | xargs -I {} cp {} $DST/deviceB_freq_sweep.mx3

ls $DST/
```

- [ ] **Step 3: 写 README（重点说明系数错误）**

Write `presentation/key_code/09_old_simulations/README.md`:

```markdown
# 09_old_simulations — 旧版本对标

## 教训

旧 `My_old_simulation/` 系列（共 20 runs，srcX/srcZ point source freq sweep 100-1000 GHz）
**含 J2/J4 系数符号错误**。与当前正确版本对比，拓扑荷差异约 2-3%。

**陷阱**：J2 / J4 在 frustrated FM 模型里有正负号约定，不同文献存在差异。
**经验**：复用别人代码时必须验证符号；直接从已验证的 `R8r4_Ku0.mx3` 拷参数，不要从公式重推。

## 脚本清单

| 文件 | 功能 |
|---|---|
| `My_old_simulation_srcX.mx3` | 旧版本 srcX 点源代表（**系数错误**）|
| `My_old_simulation_srcZ.mx3` | 旧版本 srcZ 点源代表（**系数错误**）|
| `deviceB_freq_sweep.mx3` | Device B（用户次要机器）独立验证版本 |

## 原始数据位置

- `20260105_frustrated_fm/old_results/My_old_simulation/{srcX, srcZ}/srcX/`（套娃路径）
- `20260105_frustrated_fm/spin_wave_dynamics/freq_sweep/point_source/`（数据已迁回 2026-04-09）
- `deviceB_package/deviceB_package/`
```

- [ ] **Step 4: 提交**

```bash
git add presentation/key_code/09_old_simulations/
git commit -m "feat(presentation): copy old simulation references + README"
```

---

### Task 12: figures/ — 收关键图

**Files:**
- Sources：分散在各 `*.out/analysis/`、`*/results/`、`bishe/figures/`
- Target: `presentation/key_code/figures/`

- [ ] **Step 1: 定位关键图**

为 P1-P29 收 10-15 张代表图。逐条 find 定位：

```bash
cd /mnt/d/Research/Hopfion

# DMI-FM 稳定结构图
find 20251219_dmi_fm -name "*.png" -not -path "*/\.git/*" | head -10

# Ku critical R vs Ku
find 20260105_frustrated_fm/anisotropy_study -name "*.png" -not -path "*/\.out/*" | head -10

# 漂移 4 组对比
find 20260105_frustrated_fm/drift_experiments -name "*drift*.png" -o -name "fig3-4*" | head -5

# 频率响应谱
find 20260105_frustrated_fm/spin_wave_dynamics/freq_sweep -name "*.png" | head -10

# 幅度扫描旧拟合
find 20260105_frustrated_fm/spin_wave_dynamics/amplitude_sweep -name "*.png" | head -10

# 点源 vs 平面源
find 20260105_frustrated_fm/spin_wave_dynamics -name "*point*.png" -o -name "*comparison*.png" | head -10

# freq_switch v3 坍塌
find 20260105_frustrated_fm/spin_wave_dynamics/multisource_control -name "*.png" | head -10

# LIF Phase 1/2
find lif_neuron_hopfion -name "*.png" | head -10

# 论文 figures (备选)
ls bishe/figures/ 2>/dev/null | head -20
```

- [ ] **Step 2: 拷贝（按目标文件名重命名）**

执行者按上一步找到的实际路径执行 cp。目标命名按 spec：

```bash
DST=presentation/key_code/figures

# 示例命名，实际文件名按 find 输出
# cp <find_result> $DST/dmi_fm_stable.png
# cp <find_result> $DST/ku_critical_R_vs_Ku.png
# cp <find_result> $DST/drift_4groups_comparison.png
# cp <find_result> $DST/freq_response_srcX.png
# cp <find_result> $DST/freq_response_srcZ.png
# cp <find_result> $DST/amplitude_law_failed.png
# cp <find_result> $DST/point_vs_plane.png
# cp <find_result> $DST/freq_switch_v3_collapse.png
# cp <find_result> $DST/lif_phase1_pass.png
# cp <find_result> $DST/lif_phase2_f1_failed.png

ls $DST/
```

找不到的图 → 在 README 标"缺图，PPT 该页改纯文字"。

- [ ] **Step 3: 写 figures/README**

Write `presentation/key_code/figures/README.md`:

```markdown
# figures — PPT 关键分析图索引

PPT (`talk.pptx`) 引用的所有插图集中在这里。

| 文件 | 对应 PPT 页 | 来源 | 描述 |
|---|---|---|---|
| `dmi_fm_stable.png` | P1 | 20251219_dmi_fm/ | DMI-FM Hopfion 2 ns 稳定截面 |
| `ku_critical_R_vs_Ku.png` | P8 | anisotropy_study/ku_critical_sweep/ | R(Ku) 13 点曲线 + 临界区域 |
| `drift_4groups_comparison.png` | P11 | drift_experiments/unified_rerun/ | 4 组完全一致（旧结论推翻）|
| `freq_response_srcX.png` | P13 | freq_sweep/plane_wave/srcX/results/ | srcX 频响谱 |
| `freq_response_srcZ.png` | P14 | freq_sweep/plane_wave/srcZ/results/ | srcZ 频响谱（含 1100 GHz 峰）|
| `amplitude_law_failed.png` | P15 | amplitude_sweep/plane_wave/results/ | 旧 v∝B¹·⁹⁹ 拟合（已推翻）|
| `point_vs_plane.png` | P18-P19 | freq_sweep/point_source/results/ | 点源 vs 平面源对比 |
| `freq_switch_v3_collapse.png` | P22 | multisource_control/bidirectional_z/ | v3 完整轨迹到 1.00 ns（含 0.91 ns 坍塌）|
| `lif_phase1_pass.png` | P24 | lif_neuron_hopfion/gradient_ku_verification/analysis/ | gradient vs uniform Ku 对比 |
| `lif_phase2_f1_failed.png` | P25 | lif_neuron_hopfion/lif_cycle_demo/ | Phase 2 F1 失败轨迹 |

## 缺图情况

[执行 Task 12 Step 2 后填入]
```

- [ ] **Step 4: 提交**

```bash
git add presentation/key_code/figures/
git commit -m "feat(presentation): collect PPT figures + index README"
```

---

### Task 13: 顶层 key_code/README.md

**Files:**
- Create: `presentation/key_code/README.md`

- [ ] **Step 1: 写总索引**

Write `presentation/key_code/README.md`:

```markdown
# Hopfion 项目代码包

阅读型代码包，对应吴佳乐 2026-06-01 给导师的汇报 PPT。

## 项目背景

Hopfion 3D 磁性拓扑结构的微磁学仿真（mumax3）。本包含 4 个体系：
1. DMI-FM (FeGe) Hopfion 稳定性
2. Frustrated FM Hopfion（无 DMI，竞争交换）— 主体
3. Wang 2019 STT 复现
4. LIF 神经元仿真

## 目录索引

| 目录 | 主题 |
|---|---|
| `00_shared_libs/` | 共享分析库（所有子目录依赖）|
| `01_dmi_fm/` | DMI-FM Hopfion 稳定性 |
| `02_frustrated_fm_stability/` | Frustrated FM 稳定性（吸引子、Ku 临界、Q_H）|
| `03_drift/` | Hopfion 漂移（含被推翻的旧结论）|
| `04_spin_wave_plane/` | 平面源自旋波驱动 |
| `05_spin_wave_point/` | 点源自旋波驱动 |
| `06_multisource_freq_switch/` | 双向 z 控制 / freq_switch（含 v3 0.91 ns 坍塌）|
| `07_stt_wang2019/` | STT Wang 2019 PRL 复现 |
| `08_lif_neuron/` | LIF 神经元仿真（Phase 1 PASS / Phase 2 FAILED）|
| `09_old_simulations/` | 旧版本对标（系数错误教训）|
| `figures/` | PPT 用关键分析图 |

每个子目录有独立 README。

## 数据排除

本包不含：
- `*.out/` 仿真输出（含 `.ovf` 帧、`table.txt`、`log.txt`）— 体积过大
- 毕设 LaTeX 章节 `bishe/`
- bd / mempalace 数据库

如需复现：联系作者获取完整数据快照。

## 共享库使用

所有 Python 分析脚本依赖 `00_shared_libs/`：

```bash
export PYTHONPATH=$(pwd)/00_shared_libs:$PYTHONPATH
python <subdir>/<script>.py
```

需要 Python 3 + numpy/scipy/matplotlib/discretisedfield。

## 仿真总数

184 个 `*.out/` 仿真目录，分布在原始 4 个体系下。本包代表性收 ~50 个 `.mx3` 与 ~10 个分析脚本。
```

- [ ] **Step 2: 提交**

```bash
git add presentation/key_code/README.md
git commit -m "feat(presentation): top-level key_code README"
```

---

### Task 14: presentation 顶层 README

**Files:**
- Create: `presentation/README.md`

- [ ] **Step 1: 写说明**

Write `presentation/README.md`:

```markdown
# Hopfion 项目导师汇报包 (2026-06-01)

## 内容

- `talk.pptx` — 29 页 PowerPoint 汇报
- `talk_outline.md` — 页对页文字稿（PPT 的可读源）
- `key_code/` — 阅读型代码包（10 子目录 + figures）

## 使用方式

1. 打开 `talk.pptx` 直接看
2. 想了解某页背后的代码 → 进 `key_code/<目录>/`，看 README，再读 `.mx3` / `.py`
3. 想知道原始仿真输出位置 → 各 README 的"原始数据位置"段，指向 `/mnt/d/Research/Hopfion/<原 dir>/`

## 范围

本包覆盖 Hopfion 项目所有跑过的 184 个仿真，包括：
- 成功结果（毕设论文已用）
- 失败案例（毕设未提）
- 半完成实验（如 amplitude_sweep srcZ 部分 cron）
- 被推翻的旧结论（如漂移 bg=mz 结论）

不包括未启动的方向（Q_H=2/4、LIF Phase 2 重设计、freq_switch v3 方案 A 调参）。

## 作者

吴佳乐，2026-06-01
```

- [ ] **Step 2: 提交**

```bash
git add presentation/README.md
git commit -m "feat(presentation): top-level README"
```

---

### Task 15: 写 talk_outline.md（页对页文字稿）

**Files:**
- Create: `presentation/talk_outline.md`

- [ ] **Step 1: 写 29 页文字稿骨架**

Write `presentation/talk_outline.md`：每页一节，每节包含 (a) 标题, (b) 正文文本（150 字内）, (c) 插图引用 `![](key_code/figures/xxx.png)` 或 "无图". 内容直接复制 spec 第 2 节 PPT 大纲表格的"内容性质"字段，扩成 1-2 段文字。

按以下模板执行（执行者按 spec PPT 大纲 P1-P29 逐页填）：

```markdown
# Hopfion 项目研究结果汇报 — 文字稿

## P1 — DMI-FM Hopfion 成功稳定

正文：在 FeGe 体系下，用 Sutcliffe 解析初始态作为种子，结合顶底层 frozenspins
强制 mz=±1 边界，并开启退磁场后，Bloch Hopfion 在 d=210 nm (3λ)、h=70 nm (λ)
盘几何中 2 ns 演化保持稳定。三个条件缺一不可：缺 Sutcliffe → 不收敛；缺 frozenspins
→ Hopfion 被表面磁化吃掉；缺退磁场 → MAP 态比 Hopfion 能量更低，跃迁到 MAP。

![DMI-FM 2ns 稳定截面](key_code/figures/dmi_fm_stable.png)

来源仿真：`20251219_dmi_fm/successful_simulation/run_analytic_relax.out/`

---

## P2 — DMI-FM 失败：Bulk PBC 螺旋态竞争

正文：在 Bulk PBC（无 frozen 边界、无表面）几何下尝试 2 次仿真，Hopfion 初始
态弛豫过程中始终被螺旋态竞争掉，最终演化为螺旋态。说明 Bloch Hopfion 在 FeGe
中的稳定性强依赖于表面边界条件，不是 bulk 拓扑稳定相。

无图。

来源：`20251219_dmi_fm/failed_attempts/bulk_pbc_tests/` (2 runs)

---

## P3-P29 — [按 spec 第 2 节 PPT 大纲逐页填，格式同上]
```

完整 29 页详细文字按 spec § 2 PPT 大纲表 P1-P29 的内容性质字段，每页扩成 80-150 字。

- [ ] **Step 2: 验证 29 节齐**

```bash
grep -c "^## P" presentation/talk_outline.md
```

Expected: 29

- [ ] **Step 3: 提交**

```bash
git add presentation/talk_outline.md
git commit -m "feat(presentation): 29-page talk outline"
```

---

### Task 16: 生成 talk.pptx

**Files:**
- Create: `presentation/talk.pptx`

- [ ] **Step 1: 调用 pptx skill**

调 `superpowers:pptx` skill（已存在），输入 `presentation/talk_outline.md`，要求：
- 朴素布局：标题 + 文本框 + 单张图（如有）
- 不套配色模板，白底黑字
- 中文字体（系统默认或宋体）
- 每节 `## P{n}` 对应一页
- `![](path)` 行嵌入图片
- 不要加封面 / 目录 / 总结页（spec 排除）

如果 pptx skill 不能自动从 .md 生成，则用 python-pptx 手工生成：

```python
from pptx import Presentation
from pptx.util import Inches, Pt
import re

prs = Presentation()
prs.slide_width = Inches(13.33)  # 16:9
prs.slide_height = Inches(7.5)

with open('presentation/talk_outline.md', encoding='utf-8') as f:
    md = f.read()

# 按 ## P 切页
pages = re.split(r'\n## (P\d+ — [^\n]+)\n', md)[1:]
for i in range(0, len(pages), 2):
    title, body = pages[i], pages[i+1]
    slide = prs.slides.add_slide(prs.slide_layouts[5])  # blank
    # 标题文本框
    tb = slide.shapes.add_textbox(Inches(0.5), Inches(0.3), Inches(12), Inches(0.7))
    tb.text_frame.text = title
    tb.text_frame.paragraphs[0].font.size = Pt(24)
    # 正文 + 图
    fig_match = re.search(r'!\[.*?\]\((.+?)\)', body)
    text_body = re.sub(r'!\[.*?\]\(.+?\)', '', body).strip()
    txt = slide.shapes.add_textbox(Inches(0.5), Inches(1.2), Inches(7.5), Inches(5.5))
    txt.text_frame.text = text_body
    for p in txt.text_frame.paragraphs:
        p.font.size = Pt(14)
    if fig_match:
        img_path = 'presentation/' + fig_match.group(1) if not fig_match.group(1).startswith('presentation') else fig_match.group(1)
        try:
            slide.shapes.add_picture(img_path, Inches(8.3), Inches(1.5), width=Inches(4.7))
        except Exception as e:
            print(f"Missing image: {img_path}: {e}")

prs.save('presentation/talk.pptx')
```

执行：

```bash
cd /mnt/d/Research/Hopfion
source hopfion/bin/activate
python -c "<上面脚本>" 或写到临时 build_pptx.py
```

- [ ] **Step 2: 验证 29 页**

```bash
python -c "from pptx import Presentation; p=Presentation('presentation/talk.pptx'); print(len(p.slides))"
```

Expected: 29

- [ ] **Step 3: 用户人工抽查**

让用户打开 talk.pptx 抽查 5 页：P1（成功 DMI-FM）、P11（漂移修正）、P15（旧标度律推翻）、P22（freq_switch v3 坍塌）、P29（现状清单）。
确认文字与图都正确显示。

- [ ] **Step 4: 提交**

```bash
git add presentation/talk.pptx
git commit -m "feat(presentation): generate talk.pptx (29 pages)"
```

---

### Task 17: 走查与最终验证

**Files:**
- Modify (if needed): 任何 README / outline / pptx

- [ ] **Step 1: 走查清单**

```bash
cd /mnt/d/Research/Hopfion

# 1. key_code 树齐
ls -d presentation/key_code/*/
# Expected: 11 entries (10 code subdirs + figures)

# 2. 每子目录有 README
for d in presentation/key_code/*/; do test -f "$d/README.md" && echo "OK: $d" || echo "MISS: $d"; done

# 3. 顶层 README 齐
ls presentation/{README.md,talk_outline.md,talk.pptx} presentation/key_code/README.md
# Expected: 4 files present

# 4. PPT 页数
python -c "from pptx import Presentation; p=Presentation('presentation/talk.pptx'); print('Pages:', len(p.slides))"
# Expected: Pages: 29

# 5. 图引用与实际图对应
grep -oE "key_code/figures/[a-z_]+\.png" presentation/talk_outline.md | sort -u > /tmp/refs.txt
ls presentation/key_code/figures/*.png | sed 's|.*/|key_code/figures/|' | sort -u > /tmp/exist.txt
diff /tmp/refs.txt /tmp/exist.txt
# Expected: 无差异（或差异都标注在 figures/README.md 缺图段）
```

- [ ] **Step 2: 修正发现的问题**

发现的缺漏 / 文件错位 / 缺图就地 Edit 修复。

- [ ] **Step 3: 终态提交（如有改动）**

```bash
git status
git add -A
git commit -m "fix(presentation): final walkthrough corrections" || echo "no changes"
```

- [ ] **Step 4: 通知用户完工**

向用户报告：
- `presentation/talk.pptx` 29 页
- `presentation/key_code/` 树齐 + 所有 README
- 已 commit 到 master
- 等待用户最终人工 review

---

## Self-Review 结果

**1. Spec coverage**：
- A-I 9 块 → T3-T11 + T16 outline 覆盖
- 共享库 → T2
- figures → T12
- README 层级 → T2-T13
- pptx → T16
- 走查 → T17
- 全部 spec 章节均有任务对应 ✓

**2. Placeholder scan**：无 TBD/TODO；T15 step 1 用 "按 spec § 2 逐页填" 是合规引用（spec 在仓库内）；T16 给了完整 python-pptx 代码不是占位 ✓

**3. Type consistency**：目录命名、README 模板段名、图文件名在 T2-T17 一致使用 ✓

---

## Execution Handoff

Plan 已落 `docs/superpowers/plans/2026-06-01-hopfion-advisor-talk-plan.md`。两种执行方式：

1. **Subagent-Driven (推荐)**：每个 task 派一个 fresh subagent 跑完，两阶段 review，快速迭代
2. **Inline Execution**：本 session 用 executing-plans skill，分批执行 + checkpoint 给用户审

选哪个？
