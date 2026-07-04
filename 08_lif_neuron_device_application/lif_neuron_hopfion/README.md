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
