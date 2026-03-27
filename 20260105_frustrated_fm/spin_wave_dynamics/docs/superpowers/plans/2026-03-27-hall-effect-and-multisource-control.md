# Hall Effect & Multi-Source Spin Wave Control — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Quantify the topological Hall angle of a Q_H=1 FM Hopfion driven by spin waves, and establish multi-source trajectory control.

**Architecture:** Two parallel studies. Study 1 (Hall angle) starts with zero-cost analysis of existing data, then optional new sims. Study 2 (multi-source) requires 1 new simulation for srcZ(-z) baseline, then dual-source combinations. All analysis uses the shared library at `/mnt/d/Research/Hopfion/scripts/`.

**Tech Stack:** Mumax3 (simulation), Python 3.12 + discretisedfield + numpy + matplotlib (analysis), PowerShell (B-device batch), bash (A-device local)

**Key paths:**
- Shared library: `/mnt/d/Research/Hopfion/scripts/hopfion_analysis.py`
- Spin wave project: `/mnt/d/Research/Hopfion/20260105_frustrated_fm/spin_wave_dynamics/`
- Initial state: `/mnt/d/Research/Hopfion/20260105_frustrated_fm/centered_stability_test/stability_Ku10k.out/m000020.ovf`
- Python venv: `source /mnt/d/Research/Hopfion/hopfion/bin/activate`

---

## Task 1: Add `compute_hall_angle` to shared library

**Files:**
- Modify: `/mnt/d/Research/Hopfion/scripts/hopfion_analysis.py` (append new function)
- Modify: `/mnt/d/Research/Hopfion/scripts/README.md` (update index)

- [ ] **Step 1: Add `compute_hall_angle` function**

Append to `/mnt/d/Research/Hopfion/scripts/hopfion_analysis.py`:

```python
# ──────────────────────────────────────────────
# 3. Hall 角计算
# ──────────────────────────────────────────────

def compute_hall_angle(trajectory_data, sw_propagation_axis="x",
                       skip_fraction=0.33):
    """
    从位移轨迹计算拓扑 Hall 角 theta_H。

    Parameters
    ----------
    trajectory_data : list of (t_ns, shift_nm, core_cnt)
        extract_trajectory_phase_correlation() 的输出。
    sw_propagation_axis : str
        自旋波传播方向：'x', 'y', 或 'z'。
        v_parallel 沿此轴，v_perp 为其余分量。
    skip_fraction : float
        跳过前 N% 帧以避免瞬态。

    Returns
    -------
    dict with keys:
        'theta_H_deg': float — Hall 角（度），0=沿SW方向，90=完全垂直
        'theta_H_err_deg': float — 基于位移不确定度的估计误差
        'v_parallel': float — 平行速度 (nm/ns)
        'v_perp': float — 垂直速度 (nm/ns)
        'displacement_total_nm': float — 总位移
        'valid': bool — 位移是否足够大以给出可靠 Hall 角
    """
    ts = np.array([d[0] for d in trajectory_data])
    shifts = np.array([d[1] for d in trajectory_data])  # (N, 3) in nm

    # Skip initial transient
    n_skip = max(1, int(len(ts) * skip_fraction))
    ts_late = ts[n_skip:]
    shifts_late = shifts[n_skip:]

    # Map axis to index
    axis_map = {'x': 0, 'y': 1, 'z': 2}
    par_idx = axis_map[sw_propagation_axis]
    perp_indices = [i for i in range(3) if i != par_idx]

    # Displacement components (late-time)
    d_par = shifts_late[-1, par_idx] - shifts_late[0, par_idx]
    d_perp_vec = shifts_late[-1, perp_indices] - shifts_late[0, perp_indices]
    d_perp = np.linalg.norm(d_perp_vec)
    d_total = np.linalg.norm(shifts[-1] - shifts[0])

    # Time span
    dt = ts_late[-1] - ts_late[0]
    v_par = d_par / dt if dt > 0 else 0.0
    v_perp = d_perp / dt if dt > 0 else 0.0

    # Hall angle
    theta_H = np.degrees(np.arctan2(d_perp, abs(d_par)))

    # Validity check: displacement must exceed grid resolution (~0.05nm)
    valid = d_total > 0.1  # nm

    # Error estimate from grid resolution (0.5nm cell -> ~0.05nm subpixel)
    dx_err = 0.05  # nm
    if valid and abs(d_par) > dx_err:
        theta_H_err = np.degrees(dx_err / max(abs(d_par), dx_err))
    else:
        theta_H_err = 90.0  # meaningless

    return {
        'theta_H_deg': theta_H,
        'theta_H_err_deg': theta_H_err,
        'v_parallel': v_par,
        'v_perp': v_perp,
        'displacement_total_nm': d_total,
        'valid': valid,
    }
```

- [ ] **Step 2: Verify function loads without error**

```bash
source /mnt/d/Research/Hopfion/hopfion/bin/activate
python -c "from hopfion_analysis import compute_hall_angle; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Quick smoke test with freq_sweep 200GHz data**

```bash
python -c "
import sys; sys.path.insert(0, '/mnt/d/Research/Hopfion/scripts')
from hopfion_analysis import extract_trajectory_phase_correlation, compute_hall_angle
traj = extract_trajectory_phase_correlation(
    '/mnt/d/Research/Hopfion/20260105_frustrated_fm/spin_wave_dynamics/freq_sweep/02ns/sw_f200GHz.out',
    dt_ns=0.01, verbose=False)
result = compute_hall_angle(traj, sw_propagation_axis='x')
print(f'theta_H = {result[\"theta_H_deg\"]:.1f} +/- {result[\"theta_H_err_deg\"]:.1f} deg, valid={result[\"valid\"]}')
"
```

Expected: theta_H near 85-90 deg, valid=True (since 200GHz |dr|=2.5nm > 0.1nm threshold)

- [ ] **Step 4: Update scripts/README.md — add entry to function table**

Add row to the function table in `hopfion_analysis.py` section:

```markdown
| `compute_hall_angle(traj, axis, skip)` | Hall 角 theta_H（度）+ 误差 + 有效性判定 | `dict` |
```

- [ ] **Step 5: Commit**

```bash
cd /mnt/d/Research/Hopfion
git add scripts/hopfion_analysis.py scripts/README.md
git commit -m "feat: add compute_hall_angle to shared analysis library"
```

---

## Task 2: Study 1 Phase 1 — Hall angle vs frequency analysis

**Files:**
- Create: `/mnt/d/Research/Hopfion/20260105_frustrated_fm/spin_wave_dynamics/freq_sweep/analyze_hall_angle.py`
- Output: `freq_sweep/results/hall_angle_vs_freq.png`
- Output: `freq_sweep/results/hall_angle_time_resolved.png`
- Output: `freq_sweep/results/hall_angle_summary.txt`

- [ ] **Step 1: Write analysis script**

Create `freq_sweep/analyze_hall_angle.py`:

```python
"""
Hall Angle Analysis — freq_sweep data
Extract theta_H(f) from existing 02ns (10 freq) + 05ns (4 freq) datasets.

Data: freq_sweep/02ns/ + freq_sweep/05ns/
Output: freq_sweep/results/
"""

import os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, "/mnt/d/Research/Hopfion/scripts")
from hopfion_analysis import (extract_trajectory_phase_correlation,
                               compute_hall_angle)

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(HERE, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

# ── Data sources ──
DATASETS = {
    "02ns": {
        "dir": os.path.join(HERE, "02ns"),
        "freqs_ghz": list(range(100, 1100, 100)),
        "dt_ns": 0.01,
        "pattern": "sw_f{freq}GHz.out",
    },
    "05ns": {
        "dir": os.path.join(HERE, "05ns"),
        "freqs_ghz": [300, 400, 900, 1000],
        "dt_ns": 0.01,
        "pattern": "sw_f{freq}GHz.out",
    },
}


def analyze_one(out_dir, dt_ns, freq_ghz):
    """Extract trajectory and compute Hall angle for one frequency."""
    traj = extract_trajectory_phase_correlation(out_dir, dt_ns, verbose=False)
    if len(traj) < 3:
        return None
    ha = compute_hall_angle(traj, sw_propagation_axis='x')
    ha['freq_ghz'] = freq_ghz
    ha['traj'] = traj  # keep for time-resolved plot
    return ha


def compute_theta_h_time_series(traj, sw_axis='x'):
    """Compute theta_H(t) from cumulative displacement at each frame."""
    axis_map = {'x': 0, 'y': 1, 'z': 2}
    par_idx = axis_map[sw_axis]
    perp_indices = [i for i in range(3) if i != par_idx]

    ts, thetas = [], []
    for t_ns, shift, _ in traj:
        if t_ns == 0:
            continue
        d_par = shift[par_idx]
        d_perp = np.linalg.norm(shift[perp_indices])
        theta = np.degrees(np.arctan2(d_perp, abs(d_par)))
        ts.append(t_ns)
        thetas.append(theta)
    return np.array(ts), np.array(thetas)


# ── Main ──
all_results = {}

for ds_name, ds in DATASETS.items():
    for freq in ds["freqs_ghz"]:
        out_dir = os.path.join(ds["dir"], ds["pattern"].format(freq=freq))
        if not os.path.isdir(out_dir):
            print(f"SKIP {ds_name}/{freq}GHz: no output dir")
            continue
        print(f"Processing {ds_name}/{freq}GHz ...")
        result = analyze_one(out_dir, ds["dt_ns"], freq)
        if result:
            key = (ds_name, freq)
            all_results[key] = result

# ── Plot 1: theta_H vs frequency ──
fig, ax = plt.subplots(figsize=(10, 6))

for ds_name, marker, color in [("02ns", "o", "C0"), ("05ns", "s", "C1")]:
    freqs, angles, errs, valids = [], [], [], []
    for (dn, f), r in sorted(all_results.items()):
        if dn != ds_name:
            continue
        freqs.append(f)
        angles.append(r['theta_H_deg'])
        errs.append(r['theta_H_err_deg'])
        valids.append(r['valid'])

    freqs, angles, errs, valids = map(np.array, [freqs, angles, errs, valids])
    # Plot valid points with error bars
    mask = valids.astype(bool)
    if mask.any():
        ax.errorbar(freqs[mask], angles[mask], yerr=errs[mask],
                     fmt=marker, color=color, capsize=3,
                     label=f"{ds_name} (valid)", markersize=8)
    if (~mask).any():
        ax.scatter(freqs[~mask], angles[~mask],
                   marker='x', color='gray', s=60, zorder=5,
                   label=f"{ds_name} (|dr|<0.1nm)")

ax.set_xlabel("Frequency (GHz)", fontsize=13)
ax.set_ylabel("Hall angle θ_H (deg)", fontsize=13)
ax.set_title("Topological Hall Angle vs Spin Wave Frequency\n"
             "srcX_vibX, B=1T, Q_H=1 Frustrated FM Hopfion", fontsize=13)
ax.set_ylim(0, 95)
ax.axhline(90, ls='--', color='gray', alpha=0.5, label='θ_H = 90°')
ax.legend(fontsize=10)
ax.grid(True, alpha=0.3)
fig.tight_layout()
fig.savefig(os.path.join(RESULTS_DIR, "hall_angle_vs_freq.png"), dpi=150)
plt.close(fig)
print(f"Saved: hall_angle_vs_freq.png")

# ── Plot 2: theta_H(t) time-resolved ──
fig, axes = plt.subplots(2, 1, figsize=(12, 10), sharex=False)

for ax_i, ds_name in enumerate(["02ns", "05ns"]):
    ax = axes[ax_i]
    for (dn, f), r in sorted(all_results.items()):
        if dn != ds_name or not r['valid']:
            continue
        ts, thetas = compute_theta_h_time_series(r['traj'])
        ax.plot(ts, thetas, label=f"{f} GHz", linewidth=1.5)
    ax.set_ylabel("θ_H(t) (deg)", fontsize=12)
    ax.set_title(f"{ds_name} dataset", fontsize=12)
    ax.set_ylim(0, 100)
    ax.axhline(90, ls='--', color='gray', alpha=0.5)
    ax.legend(fontsize=9, ncol=2)
    ax.grid(True, alpha=0.3)

axes[-1].set_xlabel("Time (ns)", fontsize=12)
fig.suptitle("Time-Resolved Hall Angle θ_H(t)", fontsize=14, y=1.01)
fig.tight_layout()
fig.savefig(os.path.join(RESULTS_DIR, "hall_angle_time_resolved.png"), dpi=150)
plt.close(fig)
print(f"Saved: hall_angle_time_resolved.png")

# ── Summary table ──
with open(os.path.join(RESULTS_DIR, "hall_angle_summary.txt"), "w") as f:
    f.write(f"{'Dataset':>6s} {'Freq':>6s} {'θ_H':>8s} {'±err':>8s} "
            f"{'v_par':>8s} {'v_perp':>8s} {'|dr|':>8s} {'valid':>6s}\n")
    f.write("-" * 62 + "\n")
    for (ds, freq), r in sorted(all_results.items()):
        f.write(f"{ds:>6s} {freq:>5d}  {r['theta_H_deg']:>7.1f}  "
                f"{r['theta_H_err_deg']:>7.1f}  {r['v_parallel']:>7.2f}  "
                f"{r['v_perp']:>7.2f}  {r['displacement_total_nm']:>7.3f}  "
                f"{'Y' if r['valid'] else 'N':>5s}\n")
    print(f"Saved: hall_angle_summary.txt")
```

- [ ] **Step 2: Run the analysis**

```bash
source /mnt/d/Research/Hopfion/hopfion/bin/activate
cd /mnt/d/Research/Hopfion/20260105_frustrated_fm/spin_wave_dynamics/freq_sweep
python analyze_hall_angle.py
```

Expected: 3 output files in `results/`, theta_H values near 85-90 deg for strong-response frequencies.

- [ ] **Step 3: Inspect outputs, verify physically reasonable**

Check `results/hall_angle_summary.txt` — dead-zone frequencies (400-600 GHz) should show valid=N. Strong-response frequencies should show theta_H > 80 deg.

- [ ] **Step 4: Commit**

```bash
cd /mnt/d/Research/Hopfion
git add 20260105_frustrated_fm/spin_wave_dynamics/freq_sweep/analyze_hall_angle.py
git commit -m "feat: Hall angle vs frequency analysis (Study 1 Phase 1)"
```

---

## Task 3: Study 2 Phase 1 — Generate srcZ(-z) simulation script

**Files:**
- Create: `/mnt/d/Research/Hopfion/20260105_frustrated_fm/spin_wave_dynamics/multisource_baseline/sw_srcZ_neg_f200GHz.mx3`

- [ ] **Step 1: Create directory and mx3 script**

```bash
mkdir -p /mnt/d/Research/Hopfion/20260105_frustrated_fm/spin_wave_dynamics/multisource_baseline
```

Create `multisource_baseline/sw_srcZ_neg_f200GHz.mx3`:

```
// === srcZ(-z)_vibX: f = 200 GHz, B=1T, 0.5ns ===
// Source: +Z boundary (9.5nm ~ 10nm), SW propagates toward -z
// Vibration: X direction (face-in-plane polarization)

CellSize := 0.5e-9
SetGridSize(100, 100, 100)
SetCellSize(CellSize, CellSize, CellSize)

// Absorbing boundary regions (5-cell thick, alpha=100)
DefRegion(1, XRange(22.5e-9, 25e-9))
DefRegion(2, XRange(-25e-9, -22.5e-9))
DefRegion(3, YRange(22.5e-9, 25e-9))
DefRegion(4, YRange(-25e-9, -22.5e-9))
DefRegion(5, ZRange(22.5e-9, 25e-9))
DefRegion(6, ZRange(-25e-9, -22.5e-9))

// SW source at z = +10nm (inside absorbing boundary gap)
DefRegion(7, ZRange(9.5e-9, 10e-9))

EnableDemag = false
MaxErr = 1e-4

// -- Frustrated FM parameters --
Ms     := 1.5e5
Msat    = Ms
A_base := 5e-12
Aex     = A_base
Dbulk   = 0
Dind    = 0
Ku1     = 1e4
anisU   = vector(0, 0, 1)

// Damping: low in bulk, absorbing at boundaries
alpha = 0.001
alpha.setRegion(1, 100)
alpha.setRegion(2, 100)
alpha.setRegion(3, 100)
alpha.setRegion(4, 100)
alpha.setRegion(5, 100)
alpha.setRegion(6, 100)

// -- J4: 4th nearest-neighbor (6 neighbors at 2a) --
A_J4     := A_base * (-0.082)
Coeff_J4 := A_J4 * 2.0 / (Ms * CellSize * CellSize)
sum_J4   := Add(Shifted(m, 2, 0, 0), Shifted(m, -2, 0, 0))
sum_J4    = Add(sum_J4, Shifted(m, 0, 2, 0))
sum_J4    = Add(sum_J4, Shifted(m, 0, -2, 0))
sum_J4    = Add(sum_J4, Shifted(m, 0, 0, 2))
sum_J4    = Add(sum_J4, Shifted(m, 0, 0, -2))
AddFieldTerm(Mul(Const(Coeff_J4), sum_J4))

// -- J2: Next-nearest-neighbor (12 neighbors at sqrt(2)*a) --
A_J2     := A_base * (-0.164)
Coeff_J2 := A_J2 * 2.0 / (Ms * CellSize * CellSize)
sum_J2   := Add(Shifted(m, 1, 1, 0), Shifted(m, 1, -1, 0))
sum_J2    = Add(sum_J2, Shifted(m, -1, 1, 0))
sum_J2    = Add(sum_J2, Shifted(m, -1, -1, 0))
sum_J2    = Add(sum_J2, Shifted(m, 0, 1, 1))
sum_J2    = Add(sum_J2, Shifted(m, 0, 1, -1))
sum_J2    = Add(sum_J2, Shifted(m, 0, -1, 1))
sum_J2    = Add(sum_J2, Shifted(m, 0, -1, -1))
sum_J2    = Add(sum_J2, Shifted(m, 1, 0, 1))
sum_J2    = Add(sum_J2, Shifted(m, 1, 0, -1))
sum_J2    = Add(sum_J2, Shifted(m, -1, 0, 1))
sum_J2    = Add(sum_J2, Shifted(m, -1, 0, -1))
AddFieldTerm(Mul(Const(Coeff_J2), sum_J2))

// -- Load centered equilibrated Hopfion (Ku10k, 1ns relaxed) --
m.LoadFile("/mnt/d/Research/Hopfion/20260105_frustrated_fm/centered_stability_test/stability_Ku10k.out/m000020.ovf")

// -- Spin wave: x-polarized, 200 GHz, from +z face --
f_sw := 200e9 * 2 * pi
B_ext.setRegion(7, Vector(sin(f_sw*t), 0, 0))

// -- Output --
autosave(m, 1e-11)    // 10ps -> 51 frames over 0.5ns
tableautosave(1e-12)
TableAdd(E_Total)

run(0.5e-9)
```

- [ ] **Step 2: Verify script syntax**

Visual check: compare Region 7 definition with `sw_srcZ_f200GHz.mx3` (srcZ(+z) uses `ZRange(-10e-9, -9.5e-9)`, this one uses `ZRange(9.5e-9, 10e-9)` — opposite face). All other parameters identical.

- [ ] **Step 3: Run simulation on B device**

Copy to B device and run:

```powershell
# On B device (Windows PowerShell)
mumax3 sw_srcZ_neg_f200GHz.mx3
```

Wait for completion (~10min for 0.5ns).

- [ ] **Step 4: Commit script**

```bash
cd /mnt/d/Research/Hopfion
git add 20260105_frustrated_fm/spin_wave_dynamics/multisource_baseline/sw_srcZ_neg_f200GHz.mx3
git commit -m "feat: srcZ(-z) baseline sim script for multi-source study"
```

---

## Task 4: Study 2 Phase 1 — Analyze three single-source baselines

**Files:**
- Create: `/mnt/d/Research/Hopfion/20260105_frustrated_fm/spin_wave_dynamics/multisource_baseline/analyze_baselines.py`
- Output: `multisource_baseline/results/direction_rose_plot.png`
- Output: `multisource_baseline/results/baseline_trajectories.png`
- Output: `multisource_baseline/results/baseline_summary.txt`

- [ ] **Step 1: Write baseline analysis script**

Create `multisource_baseline/analyze_baselines.py`:

```python
"""
Multi-Source Baseline Analysis
Compare 3 independent single-source configurations:
  1. srcX_vibX @ 200GHz (from freq_sweep/02ns/)
  2. srcZ(+z)_vibX @ 200GHz (from srcZ_freq_sweep/)
  3. srcZ(-z)_vibX @ 200GHz (from multisource_baseline/)

Output: direction rose plot + trajectory comparison + Hall angle table
"""

import os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, "/mnt/d/Research/Hopfion/scripts")
from hopfion_analysis import (extract_trajectory_phase_correlation,
                               compute_hall_angle)

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = "/mnt/d/Research/Hopfion/20260105_frustrated_fm/spin_wave_dynamics"
RESULTS_DIR = os.path.join(HERE, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

CONFIGS = {
    "srcX (+x)": {
        "out_dir": os.path.join(BASE, "freq_sweep/02ns/sw_f200GHz.out"),
        "dt_ns": 0.01,
        "sw_axis": "x",
        "color": "C0",
    },
    "srcZ(+z)": {
        "out_dir": os.path.join(BASE, "srcZ_freq_sweep/sw_srcZ_f200GHz.out"),
        "dt_ns": 0.01,
        "sw_axis": "z",
        "color": "C1",
    },
    "srcZ(-z)": {
        "out_dir": os.path.join(HERE, "sw_srcZ_neg_f200GHz.out"),
        "dt_ns": 0.01,
        "sw_axis": "z",  # propagation along -z, but axis is still z
        "color": "C2",
    },
}

results = {}
for name, cfg in CONFIGS.items():
    if not os.path.isdir(cfg["out_dir"]):
        print(f"SKIP {name}: {cfg['out_dir']} not found")
        continue
    print(f"Processing {name} ...")
    traj = extract_trajectory_phase_correlation(
        cfg["out_dir"], cfg["dt_ns"], verbose=False)
    ha = compute_hall_angle(traj, sw_propagation_axis=cfg["sw_axis"])
    results[name] = {"traj": traj, "hall": ha, "cfg": cfg}

# ── Plot 1: 3D trajectory comparison ──
fig, axes = plt.subplots(1, 3, figsize=(15, 5))
comp_labels = ["dx (nm)", "dy (nm)", "dz (nm)"]

for name, r in results.items():
    traj = r["traj"]
    ts = [d[0] for d in traj]
    shifts = np.array([d[1] for d in traj])
    color = r["cfg"]["color"]
    for i, ax in enumerate(axes):
        ax.plot(ts, shifts[:, i], label=name, color=color, linewidth=1.5)

for i, ax in enumerate(axes):
    ax.set_xlabel("Time (ns)", fontsize=11)
    ax.set_ylabel(comp_labels[i], fontsize=11)
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)

fig.suptitle("Single-Source Baseline: Hopfion Displacement Components\n"
             "f=200GHz, B=1T, vibX", fontsize=13)
fig.tight_layout()
fig.savefig(os.path.join(RESULTS_DIR, "baseline_trajectories.png"), dpi=150)
plt.close(fig)
print("Saved: baseline_trajectories.png")

# ── Plot 2: Direction rose plot (polar) ──
fig, ax = plt.subplots(subplot_kw=dict(projection='polar'), figsize=(8, 8))

for name, r in results.items():
    traj = r["traj"]
    shifts = np.array([d[1] for d in traj])
    # Final displacement vector in xz plane (primary motion plane)
    dx_final = shifts[-1, 0]
    dz_final = shifts[-1, 2]
    angle = np.arctan2(dz_final, dx_final)
    magnitude = np.sqrt(dx_final**2 + dz_final**2)
    color = r["cfg"]["color"]
    ax.annotate("", xy=(angle, magnitude), xytext=(0, 0),
                arrowprops=dict(arrowstyle="->", color=color, lw=2.5))
    ax.scatter([angle], [magnitude], color=color, s=80, zorder=5)
    # Label at arrow tip
    ax.annotate(f"{name}\n({magnitude:.2f}nm)",
                xy=(angle, magnitude), fontsize=9,
                ha='center', va='bottom')

ax.set_title("Motion Direction Rose Plot (xz plane)\n"
             "Arrow = final displacement vector", fontsize=12, pad=20)
fig.tight_layout()
fig.savefig(os.path.join(RESULTS_DIR, "direction_rose_plot.png"), dpi=150)
plt.close(fig)
print("Saved: direction_rose_plot.png")

# ── Summary table ──
with open(os.path.join(RESULTS_DIR, "baseline_summary.txt"), "w") as f:
    f.write(f"{'Config':>12s} {'θ_H(deg)':>9s} {'±err':>7s} "
            f"{'v_par':>8s} {'v_perp':>8s} {'|dr|':>8s} {'valid':>6s}\n")
    f.write("-" * 62 + "\n")
    for name, r in results.items():
        h = r['hall']
        f.write(f"{name:>12s} {h['theta_H_deg']:>8.1f} "
                f"{h['theta_H_err_deg']:>7.1f} {h['v_parallel']:>8.2f} "
                f"{h['v_perp']:>8.2f} {h['displacement_total_nm']:>8.3f} "
                f"{'Y' if h['valid'] else 'N':>5s}\n")
print("Saved: baseline_summary.txt")
```

- [ ] **Step 2: Run analysis (after Task 3 simulation completes)**

```bash
source /mnt/d/Research/Hopfion/hopfion/bin/activate
cd /mnt/d/Research/Hopfion/20260105_frustrated_fm/spin_wave_dynamics/multisource_baseline
python analyze_baselines.py
```

Note: If srcZ(-z) sim is not yet complete, the script will skip it and analyze the other two. Rerun after sim completes.

- [ ] **Step 3: Review outputs**

Check `results/baseline_summary.txt` for:
- srcX: theta_H should match Task 2 result at 200 GHz
- srcZ(+z) vs srcZ(-z): compare magnitude and direction — asymmetry expected due to Ku along z

- [ ] **Step 4: Commit**

```bash
cd /mnt/d/Research/Hopfion
git add 20260105_frustrated_fm/spin_wave_dynamics/multisource_baseline/analyze_baselines.py
git commit -m "feat: multi-source baseline analysis with direction rose plot"
```

---

## Task 5: Create bd issues for both studies

- [ ] **Step 1: Create Study 1 bd issue**

```bash
cd /mnt/d/Research/Hopfion
bd create --title "Study 1: FM Hopfion 拓扑 Hall 角定量表征" \
  --priority P2 --parent Hopfion-rt4 \
  --body "Phase 1: theta_H(f) from existing freq_sweep (zero cost)
Phase 2: theta_H(B) from amplitude_sweep + optional new sims
Phase 3: trajectory demonstration
See: spin_wave_dynamics/docs/superpowers/specs/2026-03-27-hall-effect-and-multisource-control-design.md"
```

- [ ] **Step 2: Create Study 2 bd issue**

```bash
bd create --title "Study 2: 多源自旋波轨迹控制" \
  --priority P2 --parent Hopfion-rt4 \
  --body "Phase 1: 3 single-source baselines (1 new sim: srcZ(-z))
Phase 2: dual-source combinations (2-4 sims)
Phase 3: slow phase modulation circular trajectory
See: spin_wave_dynamics/docs/superpowers/specs/2026-03-27-hall-effect-and-multisource-control-design.md"
```

---

## Task 6: Study 1 Phase 2 — Hall angle vs amplitude analysis

**Depends on:** Task 2 results (to decide if 440 GHz amplitude_sweep data is in the dead zone)

**Files:**
- Create: `/mnt/d/Research/Hopfion/20260105_frustrated_fm/spin_wave_dynamics/amplitude_sweep/analyze_hall_angle_amplitude.py`
- Output: `amplitude_sweep/results/hall_angle_vs_amplitude.png`

- [ ] **Step 1: Write amplitude Hall angle analysis**

Create `amplitude_sweep/analyze_hall_angle_amplitude.py`:

```python
"""
Hall Angle vs Amplitude — amplitude_sweep data
Extract theta_H(B) from existing 440GHz amplitude sweep (6 points).

Data: amplitude_sweep/sw_B*.out/
Output: amplitude_sweep/results/
"""

import os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, "/mnt/d/Research/Hopfion/scripts")
from hopfion_analysis import (extract_trajectory_phase_correlation,
                               compute_hall_angle)

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(HERE, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

# B values and corresponding output directories
B_VALUES = [0.05, 0.1, 0.2, 0.5, 1.0, 2.0]
B_LABELS = ["0p05T", "0p1T", "0p2T", "0p5T", "1p0T", "2p0T"]
DT_NS = 0.01  # 10ps for 11-frame / 0.5ns data; check actual autosave

results = []
for B, label in zip(B_VALUES, B_LABELS):
    out_dir = os.path.join(HERE, f"sw_B{label}.out")
    if not os.path.isdir(out_dir):
        # Try deviceB naming convention
        out_dir = os.path.join(HERE, f"deviceB_200GHz/sw_B{label}.out")
    if not os.path.isdir(out_dir):
        print(f"SKIP B={B}T: not found")
        continue

    n_ovf = len([f for f in os.listdir(out_dir)
                 if f.startswith("m") and f.endswith(".ovf")])
    # Determine dt from frame count and 0.5ns total
    dt = 0.5 / max(n_ovf - 1, 1) if n_ovf > 1 else 0.01

    print(f"Processing B={B}T ({n_ovf} frames, dt={dt:.4f}ns) ...")
    traj = extract_trajectory_phase_correlation(out_dir, dt, verbose=False)
    ha = compute_hall_angle(traj, sw_propagation_axis='x')
    ha['B'] = B
    results.append(ha)

# ── Plot ──
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

Bs = [r['B'] for r in results]
thetas = [r['theta_H_deg'] for r in results]
errs = [r['theta_H_err_deg'] for r in results]
valids = [r['valid'] for r in results]
v_perps = [r['v_perp'] for r in results]

mask = np.array(valids, dtype=bool)
Bs, thetas, errs, v_perps = map(np.array, [Bs, thetas, errs, v_perps])

# Panel 1: theta_H vs B
if mask.any():
    ax1.errorbar(Bs[mask], thetas[mask], yerr=errs[mask],
                 fmt='o-', capsize=4, markersize=8, color='C0')
if (~mask).any():
    ax1.scatter(Bs[~mask], thetas[~mask], marker='x', color='gray', s=80)
ax1.set_xlabel("Spin Wave Amplitude B (T)", fontsize=12)
ax1.set_ylabel("Hall Angle θ_H (deg)", fontsize=12)
ax1.set_xscale('log')
ax1.set_ylim(0, 95)
ax1.axhline(90, ls='--', color='gray', alpha=0.5)
ax1.set_title("θ_H vs Amplitude (440 GHz)", fontsize=12)
ax1.grid(True, alpha=0.3)

# Panel 2: v_perp vs B (speed scaling)
if mask.any():
    ax2.plot(Bs[mask], np.abs(v_perps[mask]), 'o-', markersize=8, color='C1')
    # Fit power law v = a * B^n
    log_B = np.log(Bs[mask])
    log_v = np.log(np.abs(v_perps[mask]) + 1e-10)
    if len(log_B) > 2:
        coeffs = np.polyfit(log_B, log_v, 1)
        n_exp = coeffs[0]
        B_fit = np.logspace(np.log10(Bs[mask].min()), np.log10(Bs[mask].max()), 50)
        v_fit = np.exp(coeffs[1]) * B_fit**n_exp
        ax2.plot(B_fit, v_fit, '--', color='C1', alpha=0.7,
                 label=f"fit: v ∝ B^{n_exp:.2f}")
        ax2.legend(fontsize=11)

ax2.set_xlabel("Spin Wave Amplitude B (T)", fontsize=12)
ax2.set_ylabel("|v_perp| (nm/ns)", fontsize=12)
ax2.set_xscale('log')
ax2.set_yscale('log')
ax2.set_title("Perpendicular Speed vs Amplitude", fontsize=12)
ax2.grid(True, alpha=0.3)

fig.suptitle("Hall Angle & Speed Scaling — Amplitude Sweep", fontsize=14)
fig.tight_layout()
fig.savefig(os.path.join(RESULTS_DIR, "hall_angle_vs_amplitude.png"), dpi=150)
plt.close(fig)
print("Saved: hall_angle_vs_amplitude.png")
```

- [ ] **Step 2: Run analysis**

```bash
source /mnt/d/Research/Hopfion/hopfion/bin/activate
cd /mnt/d/Research/Hopfion/20260105_frustrated_fm/spin_wave_dynamics/amplitude_sweep
python analyze_hall_angle_amplitude.py
```

- [ ] **Step 3: Evaluate results — decide if new sims needed**

If 440 GHz gives theta_H with large error (displacement < 0.5nm at low B), consider running 200 GHz amplitude sweep (new Task, not in this plan — create bd sub-issue if needed).

- [ ] **Step 4: Commit**

```bash
cd /mnt/d/Research/Hopfion
git add 20260105_frustrated_fm/spin_wave_dynamics/amplitude_sweep/analyze_hall_angle_amplitude.py
git commit -m "feat: Hall angle vs amplitude analysis (Study 1 Phase 2)"
```

---

## Task 7: Update spin_wave_dynamics/README.md with results

**Depends on:** Tasks 2, 4, 6 completion

**Files:**
- Modify: `/mnt/d/Research/Hopfion/20260105_frustrated_fm/spin_wave_dynamics/README.md`

- [ ] **Step 1: Add Hall angle results section**

Append to README.md after existing experiment sections:

```markdown
## 实验4：拓扑 Hall 角定量表征 (`freq_sweep/` + `amplitude_sweep/`)

**目的**：定量测量 Q_H=1 FM Hopfion 在自旋波驱动下的 Hall 偏转角。

**分析脚本**：
- `freq_sweep/analyze_hall_angle.py`：θ_H(f) 频率依赖
- `amplitude_sweep/analyze_hall_angle_amplitude.py`：θ_H(B) 幅度依赖

**结果**：[填入实际数值]

---

## 实验5：多源自旋波方向控制 (`multisource_baseline/`)

**目的**：建立源面位置→运动方向完整映射。

**分析脚本**：`multisource_baseline/analyze_baselines.py`

**结果**：[填入实际数值]
```

- [ ] **Step 2: Commit**

```bash
cd /mnt/d/Research/Hopfion
git add 20260105_frustrated_fm/spin_wave_dynamics/README.md
git commit -m "docs: add Hall angle and multi-source experiment sections to README"
```

---

## Execution Order & Parallelism

```
Task 1 (shared lib)  ──→  Task 2 (Hall angle analysis)  ──→  Task 6 (amplitude)
                      ──→  Task 3 (srcZ(-z) sim, B device)  ──→  Task 4 (baseline analysis)
Task 5 (bd issues) — independent, do anytime

Task 7 (README update) — after Tasks 2, 4, 6
```

**Immediate parallel start:**
- Task 1 + Task 3 can run simultaneously (library code + sim generation)
- Task 2 + Task 5 can run after Task 1 completes
- Task 3 (simulation) runs on B device while Tasks 1-2 run locally

**Total estimated new simulations:** 1 (srcZ(-z) @ 200GHz, 0.5ns)
