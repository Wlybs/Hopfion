# LIF Neuron Hopfion Simulation Design

**Date**: 2026-04-18
**Status**: Approved
**Reference**: Skyrmion LIF Patent CN 118284316 A (HDU, 2024)

---

## 1. Objective

Demonstrate that a 3D Hopfion in a frustrated ferromagnet can physically emulate the Leaky-Integrate-Fire (LIF) neuron model, using spin wave pulses as synaptic input and Hopfion z-displacement as membrane potential. This extends the prior Skyrmion-based LIF patent (CN 118284316 A) from 2D to 3D topology, replacing SOT current drive with spin wave drive.

## 2. Two-Phase Approach

- **Phase 1 (Proof of Concept)**: Verify that gradient Ku along z-axis creates a restoring force (Leaky mechanism)
- **Phase 2 (Full Demo)**: Complete LIF cycle with pulsed spin wave protocol (only if Phase 1 passes)

## 3. Physical System

All simulations inherit the validated frustrated FM Hopfion system:

| Parameter | Value | Source |
|---|---|---|
| Grid | 100 x 100 x 100 | Validated |
| CellSize | 0.5 nm | Validated |
| Ms | 1.5e5 A/m | Frustrated FM |
| Aex | 5e-12 J/m | Frustrated FM |
| J2 | -0.164 x Aex | Frustrated FM |
| J4 | -0.082 x Aex | Frustrated FM |
| alpha (bulk) | 0.001 | Validated |
| alpha (absorbing) | 100 | 6-face boundary |
| EnableDemag | false | Frustrated FM |
| Initial state | stability_Ku10k.out/m000020.ovf | Q_H=1, centered |
| anisU | (0, 0, 1) | Uniaxial |

### Absorbing Boundary Regions (unchanged)

- Region 1: x in [+22.5, +25] nm
- Region 2: x in [-25, -22.5] nm
- Region 3: y in [+22.5, +25] nm
- Region 4: y in [-25, -22.5] nm
- Region 5: z in [+22.5, +25] nm
- Region 6: z in [-25, -22.5] nm

### Spin Wave Source

- Region 7: z in [-10.0, -9.5] nm (1 cell, srcZ)
- Excitation: B_ext.setRegion(7, Vector(sin(f*t), 0, 0))

### Competing Exchange Terms (J2 + J4)

Implemented via AddFieldTerm with Shifted(m, ...) — identical to freq_switch_bidirectional_v3.mx3.

## 4. Phase 1: Gradient Ku Verification

### 4.1 Gradient Ku Design

Divide z-axis interior (cells 5-94, 90 cells, 45 nm) into 10 regions. Ku decreases from -z (start) to +z (end).

```
Region 10: z in [-22.5, -18.0] nm  ->  Ku = Ku_base
Region 11: z in [-18.0, -13.5] nm  ->  Ku = Ku_base - 1*dKu
Region 12: z in [-13.5,  -9.0] nm  ->  Ku = Ku_base - 2*dKu
Region 13: z in [ -9.0,  -4.5] nm  ->  Ku = Ku_base - 3*dKu
Region 14: z in [ -4.5,   0.0] nm  ->  Ku = Ku_base - 4*dKu
Region 15: z in [  0.0,  +4.5] nm  ->  Ku = Ku_base - 5*dKu
Region 16: z in [ +4.5,  +9.0] nm  ->  Ku = Ku_base - 6*dKu
Region 17: z in [ +9.0, +13.5] nm  ->  Ku = Ku_base - 7*dKu
Region 18: z in [+13.5, +18.0] nm  ->  Ku = Ku_base - 8*dKu
Region 19: z in [+18.0, +22.5] nm  ->  Ku = Ku_base - 9*dKu
```

With Ku_base = 10000 J/m3 and dKu = 500 J/m3 (V2 default):
- Range: 10000 -> 5500 J/m3
- Gradient: ~100 J/m3/nm

**Region priority**: Define gradient regions 10-19 first, then absorbing regions 1-6, then source region 7 last. Later DefRegion calls override earlier ones for overlapping cells.

### 4.2 V2: Drive-Release Test

**Experiment group (with_gradient/):**

| Phase | Time (ns) | Action | Purpose |
|---|---|---|---|
| A: Drive | 0.00 - 0.30 | srcZ @ 100 GHz, B=1T | Push Hopfion to +z (low Ku end) |
| B: Release | 0.30 - 2.30 | OFF (no driving) | Observe spontaneous drift-back |

**Control group (uniform_control/):**
- Identical drive protocol, uniform Ku=10000 everywhere (no gradient)
- Expected: minimal drift in Release phase

**Data collection:**
- autosave(m, 5e-12) — 5 ps/frame, 460 frames total
- tableautosave(1e-12) — 1 ps table precision

### 4.3 V3: Gradient Strength Sweep (after V2 passes)

| Group | dKu (J/m3) | Ku range | Gradient (J/m3/nm) |
|---|---|---|---|
| dKu_200 | 200 | 10000 -> 8200 | 44 |
| dKu_500 | 500 | 10000 -> 5500 | 111 |
| dKu_1000 | 1000 | 10000 -> 1000 | 222 |

**Output**: Leak velocity v_leak vs dKu scaling law, leak time constant tau_leak.

### 4.4 Pass/Fail Criteria

| Result | Verdict | Next Step |
|---|---|---|
| Release dz < -2 nm (drift back to high Ku) and clearly faster than control | **PASS** | Proceed to V3 then Phase 2 |
| Release dz ~ 0 or same as control | **FAIL** | Try L2/L3 or increase gradient |
| Hopfion collapses | Gradient too strong | Reduce dKu and retry |

## 5. Phase 2: Full LIF Cycle (after Phase 1 passes)

Uses the optimal gradient Ku determined from V3.

### 5.1 F1: Pulse Train Integration (mirrors patent Fig.3)

| Phase | Time (ns) | Action | LIF Function |
|---|---|---|---|
| Pulse 1 | 0.00 - 0.20 | srcZ @ 100 GHz, B=1T | Integrate |
| Gap 1 | 0.20 - 0.50 | OFF | Leak |
| Pulse 2 | 0.50 - 0.70 | srcZ @ 100 GHz, B=1T | Integrate |
| Gap 2 | 0.70 - 1.00 | OFF | Leak |
| Pulse 3 | 1.00 - 1.20 | srcZ @ 100 GHz, B=1T | Integrate |
| Gap 3 | 1.20 - 1.50 | OFF | Leak |
| Pulse 4 | 1.50 - 1.70 | srcZ @ 100 GHz, B=1T | Integrate (threshold) |
| Fire+Reset | 1.70 - 2.20 | srcZ @ 1100 GHz, B=1T | Fire + reverse reset |
| Refractory | 2.20 - 2.50 | OFF | Refractory period |

> Pulse width/gap may be adjusted based on tau_leak from V3.

**Expected output**: Staircase z-displacement vs time curve with leakage between pulses, directly comparable to patent Fig.3.

### 5.2 F3: Threshold Comparison

| Group | B0 | Expected Behavior |
|---|---|---|
| Sub-threshold | 0.1 T | Weak integration fully cancelled by leak; never fires |
| Supra-threshold | 1.0 T | Integration > leak; staircase accumulation to fire |

**Output**: Two curves on the same plot showing all-or-nothing threshold effect.

## 6. Analysis Pipeline

### 6.1 Scripts

| Script | Function | Location |
|---|---|---|
| analyze_leaky_drift.py | Phase 1: z-centroid trajectory, tau_leak fitting, control comparison | gradient_ku_verification/analysis/ |
| analyze_lif_cycle.py | Phase 2: membrane potential curve, L-I-F annotation, patent Fig.3 comparison | lif_cycle_demo/analysis/ |

Both scripts import centroid calculation from `/mnt/d/Research/Hopfion/95_shared_scripts/hopfion_analysis.py` (per C-7 shared library rule).

### 6.2 Key Plots

**Phase 1:**
- `leaky_drift_comparison.png` — gradient vs uniform: z(t) during Release phase
- `gradient_sweep_scaling.png` — v_leak and tau_leak vs dKu

**Phase 2:**
- `lif_membrane_potential.png` — z(t) with L-I-F phase annotations (main result)
- `threshold_comparison.png` — sub-threshold vs supra-threshold overlay

## 7. Directory Structure

```
/mnt/d/Research/Hopfion/08_lif_neuron_device_application/lif_neuron_hopfion/
├── gradient_ku_verification/           # Phase 1
│   ├── drive_release_test/             # V2
│   │   ├── with_gradient/
│   │   │   └── gradient_ku_drive_release.mx3
│   │   └── uniform_control/
│   │       └── uniform_ku_drive_release.mx3
│   ├── gradient_strength_sweep/        # V3
│   │   ├── dKu_200/
│   │   │   └── gradient_ku_dKu200.mx3
│   │   ├── dKu_500/
│   │   │   └── gradient_ku_dKu500.mx3
│   │   └── dKu_1000/
│   │       └── gradient_ku_dKu1000.mx3
│   └── analysis/
│       └── analyze_leaky_drift.py
├── lif_cycle_demo/                     # Phase 2
│   ├── pulse_train_integrate/          # F1
│   │   └── lif_pulse_train.mx3
│   ├── threshold_comparison/           # F3
│   │   ├── subthreshold_B0.1T.mx3
│   │   └── suprathreshold_B1.0T.mx3
│   └── analysis/
│       └── analyze_lif_cycle.py
├── 95_shared_scripts/                            # Project-local utilities
├── docs/superpowers/specs/
│   └── 2026-04-18-lif-neuron-hopfion-design.md
└── README.md
```

## 8. Mapping: Patent vs Hopfion LIF

| Patent (Skyrmion) | Hopfion LIF | Advantage |
|---|---|---|
| 2D Neel Skyrmion | 3D Hopfion (Q_H=1) | Higher information density, 3D topology |
| SOT current drive | Spin wave drive | No Joule heating, lower power |
| Gradient DMI (restoring force) | Gradient Ku (restoring force) | Same principle, adapted to 3D |
| x-position = membrane potential | z-displacement = membrane potential | Axial symmetry preserved |
| Forward/reverse current | 100 GHz / 1100 GHz frequency switch | Frequency-encoded bidirectional control |
| 200x40x2 nm thin film | 50x50x50 nm 3D bulk | Topological protection in 3D |
