# LIF Neuron Hopfion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Verify that gradient Ku creates a restoring force on Hopfion (Leaky mechanism), then demonstrate a complete LIF neuron cycle using spin wave pulses.

**Architecture:** Two-phase approach — Phase 1 validates the gradient Ku restoring force via drive-release experiments; Phase 2 (gated on Phase 1 pass) builds a full Leaky-Integrate-Fire cycle with pulsed spin waves. All simulations share the frustrated FM Hopfion system (100^3, 0.5nm/cell, Q_H=1).

**Tech Stack:** Mumax3 (.mx3), Python 3 + discretisedfield + matplotlib + scipy, Bash

**Spec:** `docs/superpowers/specs/2026-04-18-lif-neuron-hopfion-design.md`

---

## Task 1: Create Directory Structure

**Files:**
- Create: all directories under `/mnt/d/Research/Hopfion/08_lif_neuron_device_application/lif_neuron_hopfion/`

- [ ] **Step 1: Create all directories**

```bash
cd /mnt/d/Research/Hopfion/08_lif_neuron_device_application/lif_neuron_hopfion
mkdir -p gradient_ku_verification/drive_release_test/with_gradient
mkdir -p gradient_ku_verification/drive_release_test/uniform_control
mkdir -p gradient_ku_verification/gradient_strength_sweep/dKu_200
mkdir -p gradient_ku_verification/gradient_strength_sweep/dKu_500
mkdir -p gradient_ku_verification/gradient_strength_sweep/dKu_1000
mkdir -p gradient_ku_verification/analysis
mkdir -p lif_cycle_demo/pulse_train_integrate
mkdir -p lif_cycle_demo/threshold_comparison
mkdir -p lif_cycle_demo/analysis
mkdir -p scripts
```

- [ ] **Step 2: Verify structure**

```bash
find /mnt/d/Research/Hopfion/08_lif_neuron_device_application/lif_neuron_hopfion -type d | sort
```

Expected: 13 directories listed.

---

## Task 2: Write V2 Gradient Ku Drive-Release Experiment

**Files:**
- Create: `gradient_ku_verification/drive_release_test/with_gradient/gradient_ku_drive_release.mx3`

- [ ] **Step 1: Write the mx3 script**

```mx3
// === Gradient Ku Drive-Release Test ===
// Phase 1 verification: does gradient Ku create a restoring force?
// Phase A (0.00-0.30ns): srcZ @ 100GHz, B=1T → push Hopfion to +z
// Phase B (0.30-2.30ns): OFF → observe spontaneous drift-back (Leaky)
//
// Ku gradient: 10 regions along z, 10000→5500 J/m³ (dKu=500/region)
// Hopfion should drift back toward high-Ku end (-z) during Phase B

CellSize := 0.5e-9
SetGridSize(100, 100, 100)
SetCellSize(CellSize, CellSize, CellSize)

// --- Gradient Ku regions (DEFINED FIRST) ---
// z interior: cells 5-94, 90 cells, 45nm
// 10 regions of 9 cells (4.5nm) each
DefRegion(10, ZRange(-22.5e-9, -18.0e-9))  // Ku = 10000 (start, highest)
DefRegion(11, ZRange(-18.0e-9, -13.5e-9))  // Ku =  9500
DefRegion(12, ZRange(-13.5e-9,  -9.0e-9))  // Ku =  9000
DefRegion(13, ZRange( -9.0e-9,  -4.5e-9))  // Ku =  8500
DefRegion(14, ZRange( -4.5e-9,   0.0))     // Ku =  8000
DefRegion(15, ZRange(  0.0,      4.5e-9))   // Ku =  7500
DefRegion(16, ZRange(  4.5e-9,   9.0e-9))   // Ku =  7000
DefRegion(17, ZRange(  9.0e-9,  13.5e-9))   // Ku =  6500
DefRegion(18, ZRange( 13.5e-9,  18.0e-9))   // Ku =  6000
DefRegion(19, ZRange( 18.0e-9,  22.5e-9))   // Ku =  5500 (end, lowest)

// --- Absorbing boundary regions (DEFINED SECOND, override gradient at edges) ---
DefRegion(1, XRange(22.5e-9, 25e-9))
DefRegion(2, XRange(-25e-9, -22.5e-9))
DefRegion(3, YRange(22.5e-9, 25e-9))
DefRegion(4, YRange(-25e-9, -22.5e-9))
DefRegion(5, ZRange(22.5e-9, 25e-9))
DefRegion(6, ZRange(-25e-9, -22.5e-9))

// --- Source region (DEFINED LAST) ---
DefRegion(7, ZRange(-10e-9, -9.5e-9))

// --- Physics ---
EnableDemag = false
MaxErr = 1e-4

Ms     := 1.5e5
Msat    = Ms
A_base := 5e-12
Aex     = A_base
Dbulk   = 0
Dind    = 0
anisU   = vector(0, 0, 1)

// --- Gradient Ku per region ---
Ku1 = 1e4  // global default (absorbing regions + source get this)
Ku1.setRegion(10, 10000)
Ku1.setRegion(11,  9500)
Ku1.setRegion(12,  9000)
Ku1.setRegion(13,  8500)
Ku1.setRegion(14,  8000)
Ku1.setRegion(15,  7500)
Ku1.setRegion(16,  7000)
Ku1.setRegion(17,  6500)
Ku1.setRegion(18,  6000)
Ku1.setRegion(19,  5500)

// --- Damping ---
alpha = 0.001
alpha.setRegion(1, 100)
alpha.setRegion(2, 100)
alpha.setRegion(3, 100)
alpha.setRegion(4, 100)
alpha.setRegion(5, 100)
alpha.setRegion(6, 100)

// --- J4 (4th neighbor exchange) ---
A_J4     := A_base * (-0.082)
Coeff_J4 := A_J4 * 2.0 / (Ms * CellSize * CellSize)
sum_J4   := Add(Shifted(m, 2, 0, 0), Shifted(m, -2, 0, 0))
sum_J4    = Add(sum_J4, Shifted(m, 0, 2, 0))
sum_J4    = Add(sum_J4, Shifted(m, 0, -2, 0))
sum_J4    = Add(sum_J4, Shifted(m, 0, 0, 2))
sum_J4    = Add(sum_J4, Shifted(m, 0, 0, -2))
AddFieldTerm(Mul(Const(Coeff_J4), sum_J4))

// --- J2 (2nd neighbor exchange) ---
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

// --- Load initial state ---
m.LoadFile("/mnt/d/Research/Hopfion/04_frustrated_fm_foundation/20260105_frustrated_fm/centered_stability_test/stability_Ku10k.out/m000020.ovf")

// --- Data collection ---
autosave(m, 5e-12)
tableautosave(1e-12)
TableAdd(E_Total)

// === Phase A: Drive — srcZ @ 100 GHz (0.00 - 0.30 ns) ===
f1 := 100e9 * 2 * pi
B_ext.setRegion(7, Vector(sin(f1*t), 0, 0))
run(0.30e-9)

// === Phase B: Release — OFF (0.30 - 2.30 ns) ===
B_ext.setRegion(7, Vector(0, 0, 0))
run(2.00e-9)
```

- [ ] **Step 2: Verify script syntax**

Visually check: 100 grid, 10 gradient regions, 6 absorbing, 1 source, J2+J4 terms, 2 phases.

---

## Task 3: Write V2 Uniform Control Experiment

**Files:**
- Create: `gradient_ku_verification/drive_release_test/uniform_control/uniform_ku_drive_release.mx3`

- [ ] **Step 1: Write the mx3 script**

Identical to Task 2 except: no gradient Ku regions (10-19), uniform Ku1=10000 everywhere.

```mx3
// === Uniform Ku Drive-Release Control ===
// Control experiment: identical drive protocol, NO Ku gradient
// Expected: minimal drift-back during Release phase

CellSize := 0.5e-9
SetGridSize(100, 100, 100)
SetCellSize(CellSize, CellSize, CellSize)

// --- Absorbing boundary regions ---
DefRegion(1, XRange(22.5e-9, 25e-9))
DefRegion(2, XRange(-25e-9, -22.5e-9))
DefRegion(3, YRange(22.5e-9, 25e-9))
DefRegion(4, YRange(-25e-9, -22.5e-9))
DefRegion(5, ZRange(22.5e-9, 25e-9))
DefRegion(6, ZRange(-25e-9, -22.5e-9))

// --- Source region ---
DefRegion(7, ZRange(-10e-9, -9.5e-9))

// --- Physics ---
EnableDemag = false
MaxErr = 1e-4

Ms     := 1.5e5
Msat    = Ms
A_base := 5e-12
Aex     = A_base
Dbulk   = 0
Dind    = 0
Ku1     = 1e4
anisU   = vector(0, 0, 1)

// --- Damping ---
alpha = 0.001
alpha.setRegion(1, 100)
alpha.setRegion(2, 100)
alpha.setRegion(3, 100)
alpha.setRegion(4, 100)
alpha.setRegion(5, 100)
alpha.setRegion(6, 100)

// --- J4 (4th neighbor exchange) ---
A_J4     := A_base * (-0.082)
Coeff_J4 := A_J4 * 2.0 / (Ms * CellSize * CellSize)
sum_J4   := Add(Shifted(m, 2, 0, 0), Shifted(m, -2, 0, 0))
sum_J4    = Add(sum_J4, Shifted(m, 0, 2, 0))
sum_J4    = Add(sum_J4, Shifted(m, 0, -2, 0))
sum_J4    = Add(sum_J4, Shifted(m, 0, 0, 2))
sum_J4    = Add(sum_J4, Shifted(m, 0, 0, -2))
AddFieldTerm(Mul(Const(Coeff_J4), sum_J4))

// --- J2 (2nd neighbor exchange) ---
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

// --- Load initial state ---
m.LoadFile("/mnt/d/Research/Hopfion/04_frustrated_fm_foundation/20260105_frustrated_fm/centered_stability_test/stability_Ku10k.out/m000020.ovf")

// --- Data collection ---
autosave(m, 5e-12)
tableautosave(1e-12)
TableAdd(E_Total)

// === Phase A: Drive — srcZ @ 100 GHz (0.00 - 0.30 ns) ===
f1 := 100e9 * 2 * pi
B_ext.setRegion(7, Vector(sin(f1*t), 0, 0))
run(0.30e-9)

// === Phase B: Release — OFF (0.30 - 2.30 ns) ===
B_ext.setRegion(7, Vector(0, 0, 0))
run(2.00e-9)
```

---

## Task 4: Write Run Script and Launch V2 Simulations

**Files:**
- Create: `gradient_ku_verification/drive_release_test/run_v2_test.sh`

- [ ] **Step 1: Write run script**

```bash
#!/bin/bash
# Run V2 drive-release test: gradient vs uniform control
# Expected runtime: ~15-30 min each on GPU

BASEDIR="/mnt/d/Research/Hopfion/08_lif_neuron_device_application/lif_neuron_hopfion/gradient_ku_verification/drive_release_test"
LOG="$BASEDIR/run_v2_$(date +%Y%m%d_%H%M).log"

echo "=== V2 Drive-Release Test ===" | tee "$LOG"
echo "Start: $(date)" | tee -a "$LOG"

echo "[1/2] Running gradient Ku experiment..." | tee -a "$LOG"
mumax3 "$BASEDIR/with_gradient/gradient_ku_drive_release.mx3" 2>&1 | tee -a "$LOG"
echo "Gradient done: $(date)" | tee -a "$LOG"

echo "[2/2] Running uniform control..." | tee -a "$LOG"
mumax3 "$BASEDIR/uniform_control/uniform_ku_drive_release.mx3" 2>&1 | tee -a "$LOG"
echo "Uniform done: $(date)" | tee -a "$LOG"

echo "=== All V2 simulations complete ===" | tee -a "$LOG"
```

- [ ] **Step 2: Make executable and launch**

```bash
chmod +x "$BASEDIR/run_v2_test.sh"
nohup "$BASEDIR/run_v2_test.sh" > /dev/null 2>&1 &
```

- [ ] **Step 3: Verify simulations started**

```bash
ps aux | grep mumax3 | grep -v grep
```

Expected: one mumax3 process running.

---

## Task 5: Write Phase 1 Analysis Script

**Files:**
- Create: `gradient_ku_verification/analysis/analyze_leaky_drift.py`

- [ ] **Step 1: Write analysis script**

```python
"""
analyze_leaky_drift.py — Phase 1: Gradient Ku restoring force verification
===========================================================================
Compares Hopfion z-drift during Release phase:
  - Gradient Ku: should show drift-back toward high-Ku end (-z)
  - Uniform Ku: should show minimal drift (control)

Usage:
    source /mnt/d/Research/Hopfion/hopfion/bin/activate
    python3 analyze_leaky_drift.py

Output:
    analysis/leaky_drift_comparison.png
    analysis/leaky_drift_summary.txt
"""

import sys
import os
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit

sys.path.insert(0, "/mnt/d/Research/Hopfion/95_shared_scripts")
from hopfion_analysis import extract_trajectory, core_count
import discretisedfield as df

# --- Configuration ---
BASE = "/mnt/d/Research/Hopfion/08_lif_neuron_device_application/lif_neuron_hopfion/gradient_ku_verification"
GRADIENT_OUT = os.path.join(BASE, "drive_release_test/with_gradient/gradient_ku_drive_release.out")
UNIFORM_OUT = os.path.join(BASE, "drive_release_test/uniform_control/uniform_ku_drive_release.out")
OUTPUT_DIR = os.path.join(BASE, "analysis")
DT_NS = 0.005  # 5 ps autosave interval
DRIVE_END_NS = 0.30  # Phase A ends at 0.30 ns

os.makedirs(OUTPUT_DIR, exist_ok=True)


def extract_z_trajectory(out_dir):
    """Extract time and z-centroid arrays from simulation output."""
    traj = extract_trajectory(out_dir, DT_NS)
    times = np.array([t for t, c in traj if c is not None])
    z_vals = np.array([c[2] for t, c in traj if c is not None])
    return times, z_vals


def exp_decay(t, z0, dz, tau):
    """Exponential decay: z(t) = z0 + dz * exp(-t/tau)"""
    return z0 + dz * np.exp(-t / tau)


def analyze_release_phase(times, z_vals, label):
    """Analyze the Release phase (t > DRIVE_END_NS)."""
    mask = times >= DRIVE_END_NS
    t_rel = times[mask] - DRIVE_END_NS  # relative time from release start
    z_rel = z_vals[mask]

    z_at_release = z_rel[0]
    z_at_end = z_rel[-1]
    drift = z_at_end - z_at_release

    # Try exponential fit for leak time constant
    tau_leak = None
    try:
        p0 = [z_rel[-1], z_at_release - z_rel[-1], 0.5]
        popt, _ = curve_fit(exp_decay, t_rel, z_rel, p0=p0, maxfev=5000)
        tau_leak = abs(popt[2])
    except (RuntimeError, ValueError):
        pass

    return {
        "label": label,
        "z_at_release": z_at_release,
        "z_at_end": z_at_end,
        "drift_nm": drift,
        "tau_leak_ns": tau_leak,
        "t_rel": t_rel,
        "z_rel": z_rel,
    }


def check_hopfion_survival(out_dir):
    """Check if Hopfion survives by examining core_count of last frame."""
    ovf_files = sorted([f for f in os.listdir(out_dir) if f.endswith(".ovf")])
    if not ovf_files:
        return 0
    last_ovf = os.path.join(out_dir, ovf_files[-1])
    field = df.Field.from_file(last_ovf)
    return core_count(field)


def plot_comparison(grad_data, uni_data, output_path):
    """Plot gradient vs uniform z(t) comparison."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Left: full trajectory
    ax = axes[0]
    for out_dir, label, color in [
        (GRADIENT_OUT, "Gradient Ku", "C0"),
        (UNIFORM_OUT, "Uniform Ku", "C1"),
    ]:
        times, z_vals = extract_z_trajectory(out_dir)
        ax.plot(times, z_vals, color=color, label=label, linewidth=1.5)
    ax.axvline(DRIVE_END_NS, color="gray", linestyle="--", alpha=0.5, label="Drive OFF")
    ax.set_xlabel("Time (ns)")
    ax.set_ylabel("z centroid (nm)")
    ax.set_title("Full Trajectory")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Right: release phase only
    ax = axes[1]
    for data, color in [(grad_data, "C0"), (uni_data, "C1")]:
        ax.plot(data["t_rel"], data["z_rel"], color=color,
                label=f'{data["label"]} (drift={data["drift_nm"]:.2f} nm)', linewidth=1.5)
    ax.set_xlabel("Time since release (ns)")
    ax.set_ylabel("z centroid (nm)")
    ax.set_title("Release Phase — Leaky Drift")
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close()
    print(f"Saved: {output_path}")


def main():
    print("=== Phase 1: Gradient Ku Leaky Drift Analysis ===\n")

    # Check Hopfion survival
    for out_dir, label in [(GRADIENT_OUT, "Gradient"), (UNIFORM_OUT, "Uniform")]:
        cc = check_hopfion_survival(out_dir)
        status = "ALIVE" if cc > 100 else "COLLAPSED"
        print(f"  {label}: core_count={cc} [{status}]")
        if cc < 100:
            print(f"  ERROR: Hopfion collapsed in {label} experiment!")
            return

    # Extract trajectories
    print("\nExtracting trajectories...")
    grad_times, grad_z = extract_z_trajectory(GRADIENT_OUT)
    uni_times, uni_z = extract_z_trajectory(UNIFORM_OUT)

    # Analyze release phase
    grad_data = analyze_release_phase(grad_times, grad_z, "Gradient Ku")
    uni_data = analyze_release_phase(uni_times, uni_z, "Uniform Ku")

    # Print results
    print("\n--- Release Phase Analysis ---")
    for d in [grad_data, uni_data]:
        tau_str = f"{d['tau_leak_ns']:.3f} ns" if d["tau_leak_ns"] else "N/A"
        print(f"  {d['label']}:")
        print(f"    z at release: {d['z_at_release']:.2f} nm")
        print(f"    z at end:     {d['z_at_end']:.2f} nm")
        print(f"    drift:        {d['drift_nm']:.2f} nm")
        print(f"    tau_leak:     {tau_str}")

    # Pass/fail verdict
    drift_diff = abs(grad_data["drift_nm"]) - abs(uni_data["drift_nm"])
    passed = grad_data["drift_nm"] < -2.0 and drift_diff > 1.0
    verdict = "PASS" if passed else "FAIL"
    print(f"\n=== VERDICT: {verdict} ===")
    print(f"  Gradient drift: {grad_data['drift_nm']:.2f} nm")
    print(f"  Uniform drift:  {uni_data['drift_nm']:.2f} nm")
    print(f"  Difference:     {drift_diff:.2f} nm")
    if passed:
        print("  -> Gradient Ku creates measurable restoring force. Proceed to V3.")
    else:
        print("  -> Restoring force insufficient. Consider stronger gradient or alternative mechanism.")

    # Plot
    plot_path = os.path.join(OUTPUT_DIR, "leaky_drift_comparison.png")
    plot_comparison(grad_data, uni_data, plot_path)

    # Save summary
    summary_path = os.path.join(OUTPUT_DIR, "leaky_drift_summary.txt")
    with open(summary_path, "w") as f:
        f.write("Phase 1 V2: Gradient Ku Leaky Drift Verification\n")
        f.write(f"Verdict: {verdict}\n\n")
        for d in [grad_data, uni_data]:
            tau_str = f"{d['tau_leak_ns']:.3f} ns" if d["tau_leak_ns"] else "N/A"
            f.write(f"{d['label']}:\n")
            f.write(f"  z_release = {d['z_at_release']:.2f} nm\n")
            f.write(f"  z_end     = {d['z_at_end']:.2f} nm\n")
            f.write(f"  drift     = {d['drift_nm']:.2f} nm\n")
            f.write(f"  tau_leak  = {tau_str}\n\n")
    print(f"Saved: {summary_path}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify imports work**

```bash
source /mnt/d/Research/Hopfion/hopfion/bin/activate
python3 -c "import discretisedfield; print('OK')"
python3 -c "
import sys; sys.path.insert(0, '/mnt/d/Research/Hopfion/95_shared_scripts')
from hopfion_analysis import hopfion_centroid, extract_trajectory, core_count
print('Shared library OK')
"
```

Expected: both print OK.

---

## Task 6: Run V2 Analysis — GATE POINT

**Files:**
- Read: V2 simulation output directories

- [ ] **Step 1: Wait for V2 simulations to complete**

Check output directories exist and have OVF files:
```bash
ls /mnt/d/Research/Hopfion/08_lif_neuron_device_application/lif_neuron_hopfion/gradient_ku_verification/drive_release_test/with_gradient/gradient_ku_drive_release.out/*.ovf | wc -l
ls /mnt/d/Research/Hopfion/08_lif_neuron_device_application/lif_neuron_hopfion/gradient_ku_verification/drive_release_test/uniform_control/uniform_ku_drive_release.out/*.ovf | wc -l
```

Expected: ~460 OVF files each (2.3ns / 5ps).

- [ ] **Step 2: Run analysis**

```bash
source /mnt/d/Research/Hopfion/hopfion/bin/activate
cd /mnt/d/Research/Hopfion/08_lif_neuron_device_application/lif_neuron_hopfion/gradient_ku_verification/analysis
python3 analyze_leaky_drift.py
```

- [ ] **Step 3: Evaluate verdict**

Read `analysis/leaky_drift_summary.txt`. Check:
- **PASS**: gradient drift < -2nm AND clearly exceeds uniform → proceed to Task 7
- **FAIL**: gradient drift ~ 0 or same as uniform → STOP, reassess mechanism
- **COLLAPSED**: Hopfion destroyed by gradient → reduce dKu, rerun

> **GATE: Do NOT proceed to Task 7+ if FAIL or COLLAPSED.**

---

## Task 7: Write V3 Gradient Strength Sweep (after V2 PASS)

**Files:**
- Create: `gradient_ku_verification/gradient_strength_sweep/dKu_200/gradient_ku_dKu200.mx3`
- Create: `gradient_ku_verification/gradient_strength_sweep/dKu_500/gradient_ku_dKu500.mx3`
- Create: `gradient_ku_verification/gradient_strength_sweep/dKu_1000/gradient_ku_dKu1000.mx3`
- Create: `gradient_ku_verification/gradient_strength_sweep/run_v3_sweep.sh`

- [ ] **Step 1: Write dKu=200 script**

Same as Task 2 script but with Ku gradient regions changed to:

```mx3
// Ku gradient: dKu = 200 J/m³/region, range 10000 → 8200
Ku1 = 1e4
Ku1.setRegion(10, 10000)
Ku1.setRegion(11,  9800)
Ku1.setRegion(12,  9600)
Ku1.setRegion(13,  9400)
Ku1.setRegion(14,  9200)
Ku1.setRegion(15,  9000)
Ku1.setRegion(16,  8800)
Ku1.setRegion(17,  8600)
Ku1.setRegion(18,  8400)
Ku1.setRegion(19,  8200)
```

All other code (grid, regions, exchange, drive protocol) identical to Task 2.

- [ ] **Step 2: Write dKu=500 script**

Copy Task 2 script as-is (dKu=500 is the same gradient).

- [ ] **Step 3: Write dKu=1000 script**

Same structure, gradient regions changed to:

```mx3
// Ku gradient: dKu = 1000 J/m³/region, range 10000 → 1000
Ku1 = 1e4
Ku1.setRegion(10, 10000)
Ku1.setRegion(11,  9000)
Ku1.setRegion(12,  8000)
Ku1.setRegion(13,  7000)
Ku1.setRegion(14,  6000)
Ku1.setRegion(15,  5000)
Ku1.setRegion(16,  4000)
Ku1.setRegion(17,  3000)
Ku1.setRegion(18,  2000)
Ku1.setRegion(19,  1000)
```

- [ ] **Step 4: Write run script**

```bash
#!/bin/bash
BASEDIR="/mnt/d/Research/Hopfion/08_lif_neuron_device_application/lif_neuron_hopfion/gradient_ku_verification/gradient_strength_sweep"
LOG="$BASEDIR/run_v3_$(date +%Y%m%d_%H%M).log"

echo "=== V3 Gradient Strength Sweep ===" | tee "$LOG"
for dku in 200 500 1000; do
    echo "[dKu=$dku] Start: $(date)" | tee -a "$LOG"
    mumax3 "$BASEDIR/dKu_${dku}/gradient_ku_dKu${dku}.mx3" 2>&1 | tee -a "$LOG"
    echo "[dKu=$dku] Done: $(date)" | tee -a "$LOG"
done
echo "=== V3 sweep complete ===" | tee -a "$LOG"
```

- [ ] **Step 5: Launch sweep**

```bash
chmod +x "$BASEDIR/run_v3_sweep.sh"
nohup "$BASEDIR/run_v3_sweep.sh" > /dev/null 2>&1 &
```

---

## Task 8: Analyze V3 Results — Determine Optimal Gradient

**Files:**
- Modify: `gradient_ku_verification/analysis/analyze_leaky_drift.py` (add sweep mode)

- [ ] **Step 1: Add sweep analysis function to analyze_leaky_drift.py**

Append to the script:

```python
def analyze_gradient_sweep():
    """Analyze V3 gradient strength sweep results."""
    SWEEP_BASE = os.path.join(BASE, "gradient_strength_sweep")
    dku_values = [200, 500, 1000]
    results = []

    print("\n=== V3: Gradient Strength Sweep ===\n")

    for dku in dku_values:
        out_dir = os.path.join(SWEEP_BASE, f"dKu_{dku}", f"gradient_ku_dKu{dku}.out")
        if not os.path.exists(out_dir):
            print(f"  dKu={dku}: output not found, skipping")
            continue

        cc = check_hopfion_survival(out_dir)
        if cc < 100:
            print(f"  dKu={dku}: COLLAPSED (core_count={cc})")
            results.append({"dku": dku, "collapsed": True})
            continue

        times, z_vals = extract_z_trajectory(out_dir)
        data = analyze_release_phase(times, z_vals, f"dKu={dku}")
        data["dku"] = dku
        data["collapsed"] = False
        results.append(data)

        tau_str = f"{data['tau_leak_ns']:.3f}" if data["tau_leak_ns"] else "N/A"
        print(f"  dKu={dku}: drift={data['drift_nm']:.2f} nm, tau={tau_str} ns")

    # Plot scaling
    valid = [r for r in results if not r.get("collapsed", True)]
    if len(valid) >= 2:
        fig, ax = plt.subplots(figsize=(7, 5))
        dkus = [r["dku"] for r in valid]
        drifts = [abs(r["drift_nm"]) for r in valid]
        taus = [r["tau_leak_ns"] for r in valid if r["tau_leak_ns"]]

        ax.plot(dkus, drifts, "o-", color="C0", markersize=8, label="|drift| (nm)")
        ax.set_xlabel("dKu per region (J/m³)")
        ax.set_ylabel("|drift| during Release (nm)")
        ax.set_title("V3: Leaky Drift vs Gradient Strength")
        ax.legend()
        ax.grid(True, alpha=0.3)

        sweep_plot = os.path.join(OUTPUT_DIR, "gradient_sweep_scaling.png")
        plt.savefig(sweep_plot, dpi=200, bbox_inches="tight")
        plt.close()
        print(f"\nSaved: {sweep_plot}")

    # Recommend optimal
    working = [r for r in valid if abs(r["drift_nm"]) > 2.0]
    if working:
        best = min(working, key=lambda r: r["dku"])
        print(f"\nRecommended for Phase 2: dKu={best['dku']} (weakest gradient with sufficient leak)")
    else:
        print("\nNo gradient produced sufficient leak. Consider mechanism alternatives.")
```

- [ ] **Step 2: Add CLI dispatch**

Replace the `if __name__` block with:

```python
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--sweep", action="store_true", help="Run V3 sweep analysis")
    args = parser.parse_args()

    if args.sweep:
        analyze_gradient_sweep()
    else:
        main()
```

- [ ] **Step 3: Run sweep analysis**

```bash
source /mnt/d/Research/Hopfion/hopfion/bin/activate
python3 analyze_leaky_drift.py --sweep
```

- [ ] **Step 4: Record optimal dKu for Phase 2**

Note the recommended dKu value. This value feeds into Phase 2 scripts.

---

## Task 9: Write Phase 2 F1 Pulse Train Script

**Files:**
- Create: `lif_cycle_demo/pulse_train_integrate/lif_pulse_train.mx3`

> NOTE: Uses optimal dKu from Task 8. Script below uses dKu=500 as placeholder — replace Ku values with Task 8 recommendation.

- [ ] **Step 1: Write the mx3 script**

```mx3
// === LIF Neuron: Pulse Train Integrate-Fire Demo ===
// Emulates patent Fig.3: pulsed spin wave integration with leaky gaps
//
// Pulse 1-4: srcZ @ 100GHz, 0.2ns each (Integrate)
// Gap 1-3: OFF, 0.3ns each (Leak)
// Fire: srcZ @ 1100GHz, 0.5ns (reverse reset)
// Refractory: OFF, 0.3ns
//
// Gradient Ku: dKu=500 (adjust per V3 results)

CellSize := 0.5e-9
SetGridSize(100, 100, 100)
SetCellSize(CellSize, CellSize, CellSize)

// --- Gradient Ku regions ---
DefRegion(10, ZRange(-22.5e-9, -18.0e-9))
DefRegion(11, ZRange(-18.0e-9, -13.5e-9))
DefRegion(12, ZRange(-13.5e-9,  -9.0e-9))
DefRegion(13, ZRange( -9.0e-9,  -4.5e-9))
DefRegion(14, ZRange( -4.5e-9,   0.0))
DefRegion(15, ZRange(  0.0,      4.5e-9))
DefRegion(16, ZRange(  4.5e-9,   9.0e-9))
DefRegion(17, ZRange(  9.0e-9,  13.5e-9))
DefRegion(18, ZRange( 13.5e-9,  18.0e-9))
DefRegion(19, ZRange( 18.0e-9,  22.5e-9))

// --- Absorbing boundaries ---
DefRegion(1, XRange(22.5e-9, 25e-9))
DefRegion(2, XRange(-25e-9, -22.5e-9))
DefRegion(3, YRange(22.5e-9, 25e-9))
DefRegion(4, YRange(-25e-9, -22.5e-9))
DefRegion(5, ZRange(22.5e-9, 25e-9))
DefRegion(6, ZRange(-25e-9, -22.5e-9))

// --- Source ---
DefRegion(7, ZRange(-10e-9, -9.5e-9))

// --- Physics ---
EnableDemag = false
MaxErr = 1e-4

Ms     := 1.5e5
Msat    = Ms
A_base := 5e-12
Aex     = A_base
Dbulk   = 0
Dind    = 0
anisU   = vector(0, 0, 1)

// --- Gradient Ku (dKu=500, adjust per V3 results) ---
Ku1 = 1e4
Ku1.setRegion(10, 10000)
Ku1.setRegion(11,  9500)
Ku1.setRegion(12,  9000)
Ku1.setRegion(13,  8500)
Ku1.setRegion(14,  8000)
Ku1.setRegion(15,  7500)
Ku1.setRegion(16,  7000)
Ku1.setRegion(17,  6500)
Ku1.setRegion(18,  6000)
Ku1.setRegion(19,  5500)

alpha = 0.001
alpha.setRegion(1, 100)
alpha.setRegion(2, 100)
alpha.setRegion(3, 100)
alpha.setRegion(4, 100)
alpha.setRegion(5, 100)
alpha.setRegion(6, 100)

// --- J4 ---
A_J4     := A_base * (-0.082)
Coeff_J4 := A_J4 * 2.0 / (Ms * CellSize * CellSize)
sum_J4   := Add(Shifted(m, 2, 0, 0), Shifted(m, -2, 0, 0))
sum_J4    = Add(sum_J4, Shifted(m, 0, 2, 0))
sum_J4    = Add(sum_J4, Shifted(m, 0, -2, 0))
sum_J4    = Add(sum_J4, Shifted(m, 0, 0, 2))
sum_J4    = Add(sum_J4, Shifted(m, 0, 0, -2))
AddFieldTerm(Mul(Const(Coeff_J4), sum_J4))

// --- J2 ---
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

// --- Load initial state ---
m.LoadFile("/mnt/d/Research/Hopfion/04_frustrated_fm_foundation/20260105_frustrated_fm/centered_stability_test/stability_Ku10k.out/m000020.ovf")

autosave(m, 5e-12)
tableautosave(1e-12)
TableAdd(E_Total)

// --- LIF Protocol ---
f_integrate := 100e9 * 2 * pi    // 100 GHz → +z (anomalous mode)
f_fire      := 1100e9 * 2 * pi   // 1100 GHz → -z (normal mode, reset)

// Pulse 1: Integrate (0.00 - 0.20 ns)
B_ext.setRegion(7, Vector(sin(f_integrate*t), 0, 0))
run(0.20e-9)

// Gap 1: Leak (0.20 - 0.50 ns)
B_ext.setRegion(7, Vector(0, 0, 0))
run(0.30e-9)

// Pulse 2: Integrate (0.50 - 0.70 ns)
B_ext.setRegion(7, Vector(sin(f_integrate*t), 0, 0))
run(0.20e-9)

// Gap 2: Leak (0.70 - 1.00 ns)
B_ext.setRegion(7, Vector(0, 0, 0))
run(0.30e-9)

// Pulse 3: Integrate (1.00 - 1.20 ns)
B_ext.setRegion(7, Vector(sin(f_integrate*t), 0, 0))
run(0.20e-9)

// Gap 3: Leak (1.20 - 1.50 ns)
B_ext.setRegion(7, Vector(0, 0, 0))
run(0.30e-9)

// Pulse 4: Integrate — threshold reached (1.50 - 1.70 ns)
B_ext.setRegion(7, Vector(sin(f_integrate*t), 0, 0))
run(0.20e-9)

// Fire + Reset: 1100 GHz reverse (1.70 - 2.20 ns)
B_ext.setRegion(7, Vector(sin(f_fire*t), 0, 0))
run(0.50e-9)

// Refractory: OFF (2.20 - 2.50 ns)
B_ext.setRegion(7, Vector(0, 0, 0))
run(0.30e-9)
```

---

## Task 10: Write Phase 2 F3 Threshold Comparison Scripts

**Files:**
- Create: `lif_cycle_demo/threshold_comparison/subthreshold_B0.1T.mx3`
- Create: `lif_cycle_demo/threshold_comparison/suprathreshold_B1.0T.mx3`

- [ ] **Step 1: Write sub-threshold script (B=0.1T)**

Same as Task 9 but with `B_ext` amplitude scaled by 0.1:

Replace all drive lines with:
```mx3
// Pulse N: Integrate (sub-threshold, B=0.1T)
B_ext.setRegion(7, Vector(0.1*sin(f_integrate*t), 0, 0))
```

And fire/reset with:
```mx3
// Fire + Reset: 1100 GHz (B=0.1T)
B_ext.setRegion(7, Vector(0.1*sin(f_fire*t), 0, 0))
```

All other code identical to Task 9.

- [ ] **Step 2: Write supra-threshold script (B=1.0T)**

Copy Task 9 script as-is (already uses B=1T via `sin(f*t)` which has amplitude 1T by default in Mumax3 B_ext).

---

## Task 11: Write Phase 2 Analysis Script

**Files:**
- Create: `lif_cycle_demo/analysis/analyze_lif_cycle.py`

- [ ] **Step 1: Write analysis script**

```python
"""
analyze_lif_cycle.py — Phase 2: LIF neuron cycle visualization
================================================================
Generates membrane potential (z-displacement) vs time plot with
L-I-F phase annotations, mirroring patent Fig.3.

Usage:
    source /mnt/d/Research/Hopfion/hopfion/bin/activate
    python3 analyze_lif_cycle.py [--threshold]

Output:
    analysis/lif_membrane_potential.png
    analysis/threshold_comparison.png (with --threshold flag)
"""

import sys
import os
import numpy as np
import matplotlib.pyplot as plt

sys.path.insert(0, "/mnt/d/Research/Hopfion/95_shared_scripts")
from hopfion_analysis import extract_trajectory, core_count

BASE = "/mnt/d/Research/Hopfion/08_lif_neuron_device_application/lif_neuron_hopfion/lif_cycle_demo"
DT_NS = 0.005
OUTPUT_DIR = os.path.join(BASE, "analysis")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# LIF protocol phases (from spec)
PHASES = [
    (0.00, 0.20, "Integrate", "Pulse 1"),
    (0.20, 0.50, "Leak", "Gap 1"),
    (0.50, 0.70, "Integrate", "Pulse 2"),
    (0.70, 1.00, "Leak", "Gap 2"),
    (1.00, 1.20, "Integrate", "Pulse 3"),
    (1.20, 1.50, "Leak", "Gap 3"),
    (1.50, 1.70, "Integrate", "Pulse 4"),
    (1.70, 2.20, "Fire", "Reset"),
    (2.20, 2.50, "Refractory", "OFF"),
]

PHASE_COLORS = {
    "Integrate": "#2196F3",   # blue
    "Leak": "#FFC107",        # amber
    "Fire": "#F44336",        # red
    "Refractory": "#9E9E9E",  # gray
}


def extract_z(out_dir):
    traj = extract_trajectory(out_dir, DT_NS)
    times = np.array([t for t, c in traj if c is not None])
    z_vals = np.array([c[2] for t, c in traj if c is not None])
    # Subtract initial z to get displacement
    z_disp = z_vals - z_vals[0]
    return times, z_disp


def plot_lif_cycle(times, z_disp, output_path):
    """Plot membrane potential curve with phase annotations."""
    fig, ax = plt.subplots(figsize=(12, 5))

    # Phase background shading
    for t_start, t_end, phase_type, label in PHASES:
        color = PHASE_COLORS[phase_type]
        ax.axvspan(t_start, t_end, alpha=0.15, color=color)
        ax.text((t_start + t_end) / 2, ax.get_ylim()[1] if ax.get_ylim()[1] != 1.0 else max(z_disp) * 1.1,
                label, ha="center", va="bottom", fontsize=7, rotation=45)

    # Main curve
    ax.plot(times, z_disp, "k-", linewidth=1.5, label="Hopfion z-displacement")

    ax.set_xlabel("Time (ns)", fontsize=12)
    ax.set_ylabel("z displacement (nm) ~ Membrane Potential", fontsize=12)
    ax.set_title("Hopfion LIF Neuron: Membrane Potential Curve", fontsize=14)

    # Legend for phase types
    from matplotlib.patches import Patch
    legend_patches = [Patch(facecolor=c, alpha=0.3, label=k) for k, c in PHASE_COLORS.items()]
    ax.legend(handles=legend_patches, loc="upper left")
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close()
    print(f"Saved: {output_path}")


def plot_threshold_comparison(output_path):
    """Plot sub-threshold vs supra-threshold overlay."""
    sub_out = os.path.join(BASE, "threshold_comparison/subthreshold_B0.1T.out")
    sup_out = os.path.join(BASE, "threshold_comparison/suprathreshold_B1.0T.out")

    fig, ax = plt.subplots(figsize=(12, 5))

    for out_dir, label, color, ls in [
        (sup_out, "Supra-threshold (B=1.0T)", "C0", "-"),
        (sub_out, "Sub-threshold (B=0.1T)", "C1", "--"),
    ]:
        if not os.path.exists(out_dir):
            print(f"  {label}: output not found, skipping")
            continue
        times, z_disp = extract_z(out_dir)
        ax.plot(times, z_disp, color=color, linestyle=ls, linewidth=1.5, label=label)

    # Phase shading (same protocol)
    for t_start, t_end, phase_type, _ in PHASES:
        ax.axvspan(t_start, t_end, alpha=0.08, color=PHASE_COLORS[phase_type])

    ax.set_xlabel("Time (ns)", fontsize=12)
    ax.set_ylabel("z displacement (nm) ~ Membrane Potential", fontsize=12)
    ax.set_title("Threshold Effect: All-or-Nothing Firing", fontsize=14)
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close()
    print(f"Saved: {output_path}")


def main():
    print("=== Phase 2: LIF Cycle Analysis ===\n")

    pulse_out = os.path.join(BASE, "pulse_train_integrate/lif_pulse_train.out")
    if not os.path.exists(pulse_out):
        print("ERROR: pulse train output not found")
        return

    times, z_disp = extract_z(pulse_out)
    print(f"Frames: {len(times)}, Duration: {times[-1]:.2f} ns")
    print(f"Max displacement: {max(z_disp):.2f} nm")
    print(f"Final displacement: {z_disp[-1]:.2f} nm")

    plot_path = os.path.join(OUTPUT_DIR, "lif_membrane_potential.png")
    plot_lif_cycle(times, z_disp, plot_path)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--threshold", action="store_true",
                        help="Generate threshold comparison plot")
    args = parser.parse_args()

    main()
    if args.threshold:
        thresh_path = os.path.join(OUTPUT_DIR, "threshold_comparison.png")
        plot_threshold_comparison(thresh_path)
```

---

## Task 12: Run Phase 2 Simulations and Analyze

**Files:**
- Create: `lif_cycle_demo/run_phase2.sh`

- [ ] **Step 1: Write run script**

```bash
#!/bin/bash
BASEDIR="/mnt/d/Research/Hopfion/08_lif_neuron_device_application/lif_neuron_hopfion/lif_cycle_demo"
LOG="$BASEDIR/run_phase2_$(date +%Y%m%d_%H%M).log"

echo "=== Phase 2: LIF Cycle Simulations ===" | tee "$LOG"

echo "[1/3] Pulse train (F1)..." | tee -a "$LOG"
mumax3 "$BASEDIR/pulse_train_integrate/lif_pulse_train.mx3" 2>&1 | tee -a "$LOG"

echo "[2/3] Sub-threshold (F3)..." | tee -a "$LOG"
mumax3 "$BASEDIR/threshold_comparison/subthreshold_B0.1T.mx3" 2>&1 | tee -a "$LOG"

echo "[3/3] Supra-threshold (F3)..." | tee -a "$LOG"
mumax3 "$BASEDIR/threshold_comparison/suprathreshold_B1.0T.mx3" 2>&1 | tee -a "$LOG"

echo "=== Phase 2 complete ===" | tee -a "$LOG"
```

- [ ] **Step 2: Launch and wait for completion**

```bash
chmod +x "$BASEDIR/run_phase2.sh"
nohup "$BASEDIR/run_phase2.sh" > /dev/null 2>&1 &
```

- [ ] **Step 3: Run analysis after completion**

```bash
source /mnt/d/Research/Hopfion/hopfion/bin/activate
cd /mnt/d/Research/Hopfion/08_lif_neuron_device_application/lif_neuron_hopfion/lif_cycle_demo/analysis
python3 analyze_lif_cycle.py --threshold
```

- [ ] **Step 4: Verify output plots**

```bash
ls /mnt/d/Research/Hopfion/08_lif_neuron_device_application/lif_neuron_hopfion/lif_cycle_demo/analysis/*.png
```

Expected: `lif_membrane_potential.png` and `threshold_comparison.png`.

---

## Task 13: Write README and Commit

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write README**

```markdown
# LIF Neuron Hopfion

Demonstrates that a 3D Hopfion in a frustrated ferromagnet emulates the
Leaky-Integrate-Fire (LIF) neuron model using spin wave pulses.

Extends the Skyrmion LIF patent (CN 118284316 A, HDU 2024) from 2D to 3D
topology, replacing SOT current with spin wave driving.

## Physical System

- Frustrated FM: 100x100x100, 0.5nm/cell, Ms=1.5e5, Aex=5e-12
- Competing exchange: J2=-0.164*J1, J4=-0.082*J1
- Initial state: Q_H=1 Hopfion (stability_Ku10k.out/m000020.ovf)

## LIF Mapping

| LIF Function | Physical Mechanism |
|---|---|
| Leaky | Gradient Ku restoring force |
| Integrate | Spin wave pulses (100 GHz, +z) |
| Fire | Threshold displacement + 1100 GHz reset |

## Directory Structure

- `gradient_ku_verification/` — Phase 1: Verify gradient Ku leaky mechanism
- `lif_cycle_demo/` — Phase 2: Complete LIF cycle demonstration
- `docs/superpowers/` — Design spec and implementation plan

## Key Results

- Phase 1: [pending V2/V3 verification]
- Phase 2: [pending, gated on Phase 1]
```

- [ ] **Step 2: Commit all files**

```bash
cd /mnt/d/Research/Hopfion
git add 08_lif_neuron_device_application/lif_neuron_hopfion/
git commit -m "feat: add LIF neuron Hopfion simulation project (Phase 1 + 2 scripts)"
```
