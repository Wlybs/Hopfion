# FM Hopfion Hall Effect & Multi-Source Spin Wave Control — Design Spec

**Date**: 2026-03-27
**System**: Frustrated FM Hopfion, Q_H=1, Ku=10k, 100^3 grid, 0.5nm cell
**Initial state**: `centered_stability_test/stability_Ku10k.out/m000020.ovf`

---

## Study 1: Topological Hall Effect Quantification

### Goal

Quantitatively measure the Hall deflection angle theta_H of a Q_H=1 FM Hopfion driven by spin waves, establish its dependence on frequency and amplitude, then demonstrate predictable non-linear trajectories.

### Phase 1: Extract theta_H(f) from existing data (zero cost)

**Data sources**:
- `freq_sweep/02ns/`: 10 frequencies (100-1000 GHz, step 100), srcX_vibX, B=1T, 0.2ns, 10ps autosave
- `freq_sweep/05ns/`: 4 frequencies (300/400/900/1000 GHz), 0.5ns

**Method**:
- Extract dx(t) and dz(t) from existing phase-correlation displacement data
- SW propagates along +x, so v_parallel = v_x, v_perp = v_z
- theta_H = arctan(v_z / v_x), computed from late-time displacement ratio (skip first 1/3 transient)
- Also compute time-resolved theta_H(t) to check if it stabilizes

**Handling edge cases**:
- Dead-zone frequencies (400-600 GHz, |dr| < 0.1nm): mark theta_H as N/A
- dx very small (near 90 deg): use atan2, report with error band from displacement uncertainty (~0.05nm grid resolution)

**Expected result**: theta_H ~ 85-90 deg based on known dz >> dx in freq_sweep data.

**Outputs**:
- `results/hall_angle_vs_freq.png`
- `results/hall_angle_time_resolved.png`
- Numerical summary table

### Phase 2: theta_H(B) amplitude dependence (minimal new sims)

**Data source 1**: existing `amplitude_sweep/` 6 points (440 GHz, B=0.05-2.0T, 0.5ns)

**Data source 2 (if needed)**: new sims at 200 GHz, B = 0.1/0.2/0.5/1.0/2.0T, 0.5ns on A device

**Key question**: Is theta_H independent of amplitude (topologically protected) or does it vary?

**Output**: `results/hall_angle_vs_amplitude.png`

### Phase 3: Trajectory demonstration (1-2 sims)

Design a time-switched excitation sequence that produces a predictable trajectory based on measured theta_H:
- Phase-based switching between srcX and srcZ sources
- Compare actual trajectory to theta_H-predicted trajectory
- Demonstrate that FM Hopfion motion is quantitatively predictable

**Simulation budget**: 1-2 verification runs on A device, 0.5-1ns each.

---

## Study 2: Multi-Source Configuration & Trajectory Control

### Goal

Establish the complete mapping from source-face position to Hopfion motion direction, verify vector superposition with dual sources, and achieve programmable circular trajectories.

### Phase 1: Three independent single-source baselines

**Symmetry reduction**: Hopfion has continuous rotational symmetry around z-axis, so:
- srcX = srcY = src(-X) = src(-Y) -> only 1 in-plane config needed
- srcZ(+z) != srcZ(-z) due to broken z-symmetry (mz=+1 background + Ku along z) -> 2 axial configs

**Independent configurations**:

| Config | Source definition | Polarization | Existing data | New sim needed |
|--------|-----------------|-------------|---------------|----------------|
| srcX_vibX | XRange(-10e-9, -9.5e-9) | vibX (x-dir) | freq_sweep/02ns @ 200GHz (0.2ns, 21 frames); direction_coupling @ 440GHz (0.5ns) | Optional: 200GHz 0.5ns extension |
| srcZ(+z)_vibX | ZRange(-10e-9, -9.5e-9) | vibX (x-dir) | srcZ_freq_sweep @ 200GHz (0.5ns, 51 frames); direction_coupling @ 440GHz (0.5ns) | No |
| srcZ(-z)_vibX | ZRange(9.5e-9, 10e-9) | vibX (x-dir) | None | Yes: 200GHz, 0.5ns |

**New simulations needed**: 1 (srcZ from -z face)

**Parameters for new sim**: f=200GHz, B=1T, Ku=10k, alpha=0.001(bulk)/100(boundary), 0.5ns, 10ps autosave, tableautosave 1ps with E_Total.

**Outputs per config**:
- Displacement trajectory (dx, dy, dz) vs t
- Time-averaged velocity and Hall angle
- Direction rose diagram combining all 3 configs

### Phase 2: Dual-source combinations (A device, 2-4 sims)

Select 2-3 combinations based on Phase 1 results:

| Config | Combination | Physics question |
|--------|------------|-----------------|
| D1 | srcX + srcZ(+z), simultaneous | 3D vector addition of forces |
| D2 | srcX + src(-X), in-phase | Standing wave / interference pattern |
| D3 | srcX + src(-X), anti-phase | Traveling wave enhancement |
| D4 | srcX + srcZ(+z), phase-shifted | Phase-controlled direction rotation |

Exact selection depends on Phase 1 results. Each 0.5ns, same parameters.

### Phase 3: Slow phase modulation for circular trajectory (1-2 sims)

Adapt the AFM script technique to FM:

```
B_ext.setRegion(src1, Vector(B*sin(w*t), B*sin(w*t + Omega*t + phi0), 0))
B_ext.setRegion(src2, Vector(B*sin(w*t), B*sin(w*t + Omega*t - phi0), 0))
```

- w = 200 GHz * 2pi (carrier, fast)
- Omega = 2pi / T_curve (trajectory rotation, slow, T_curve ~ 5-10ns)
- phi0 from Phase 2 optimization

**Key FM vs AFM difference**: FM Magnus force adds an intrinsic Hall deflection on top of the programmed force rotation. The actual trajectory will be a circle with shifted center and modified radius compared to the AFM case.

**Simulation**: 10-25ns to cover at least one full T_curve period. Run on A device.

---

## Simulation Budget Summary

| Study | Phase | New sims | Device | Time per sim |
|-------|-------|----------|--------|-------------|
| 1 | Phase 1 | 0 | — | — |
| 1 | Phase 2 | 0-5 | A | 0.5ns |
| 1 | Phase 3 | 1-2 | A | 0.5-1ns |
| 2 | Phase 1 | 1 | B (PSL) | 0.5ns |
| 2 | Phase 2 | 2-4 | A | 0.5ns |
| 2 | Phase 3 | 1-2 | A | 10-25ns |
| **Total** | | **5-14** | | |

---

## Analysis Tools

All analysis scripts will use the shared library (`/mnt/d/Research/Hopfion/scripts/`):
- `hopfion_analysis.py`: centroid extraction, phase-correlation displacement, R/r measurement
- `resonance_analysis.py`: energy absorption spectrum, velocity response spectrum

New analysis functions to add to the shared library:
- `compute_hall_angle(dx, dz, skip_fraction=0.33)` -> theta_H with uncertainty
- `direction_rose_plot(configs_dict)` -> polar plot of motion directions

---

## Dependencies Between Studies

Study 1 Phase 1 (theta_H extraction) can start immediately with existing data.
Study 2 Phase 1 (srcZ(-z) new sim) can start immediately.
Both are independent and can run in parallel on different devices.

Study 2 Phase 2/3 benefits from Study 1 Phase 1 results (knowing theta_H helps predict dual-source outcomes), but is not strictly blocked.

---

## bd Task Mapping

- Study 1 -> new bd issue (to be created)
- Study 2 -> new bd issue (to be created)
- Both under parent task Hopfion-rt4 (spin wave dynamics)
