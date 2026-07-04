# Codex 辅助 Prompts — Hopfion Thiele 研究

> 配套 `RESEARCH_PLAN.md`。每个 prompt 自包含，可直接贴给 Codex。
> 通用护栏（已内置每个 prompt）：WSL venv 激活；强制 `from hopfion_analysis import ...`（C-7）；输出写带日期结果目录，不写入 repo 源树；前因子/符号抄 Liu 2020 PRL 124,127204 不重导；J2/J4 符号抄 R8r4_Ku0.mx3；点源/面源绝不比绝对量级。
>
> **当前批次（用户细看后启动）**：C-1, C-2, C-3, C-4（Phase 0）。**C-5 暂缓；C-6 待期刊层级定**。

---

## Prompt C-1 [Phase 0] — 计算 G,D 平动块+膨胀块 + 闭环零 + 霍尔角预言

```
TASK: Compute the translation-block (and dilation-block) gyrotensor G and dissipation tensor D of a frustrated-FM Hopfion from its STATIC texture, then predict the srcX Hall deflection angle. STATIC-texture computation; run NO micromagnetic simulation. SCOPE: translation {X,Y,Z} + dilation {R,r} only; twist/helicity is OUT OF SCOPE (future work).

ENV: source /mnt/d/Research/Hopfion/hopfion/bin/activate  (discretisedfield, numpy, scipy)
SHARED LIB (MANDATORY, do not rewrite): import sys; sys.path.insert(0,'/mnt/d/Research/Hopfion/95_shared_scripts'); from hopfion_analysis import compute_Rr  (+ the OVF loader)

STEP 1 — real driven texture and its R,r:
  - Extract m000020.ovf from /mnt/d/Research/Hopfion/04_frustrated_fm_foundation/20260105_frustrated_fm/centered_stability_test/stability_Ku10k.out/ovf_archive.tar.zst into a scratch dir under /tmp (NOT into the repo tree).
  - Load with discretisedfield; run compute_Rr -> R,r. Report them.

STEP 2 — translation derivatives WITHOUT any constructor:
  - dm/dX,dm/dY,dm/dZ = rigid spatial shift of the REAL m000020 texture by +-delta (delta = 1 cell = 0.5 nm), CENTERED: (m(+d)-m(-d))/(2d). Use np.roll on (nx,ny,nz,3) (PBC consistent).
  - Cell-wise renormalize |m|=1, then TANGENT-PROJECT: dm -= (dm.m) m.
  - dilation derivatives dm/dR, dm/dr: generate_hopfion_ovf(..., afm=None) at (R+-dR), (r+-dr) using the REAL R,r as center; VERIFY each generated texture reproduces the real R,r and Q_H=1 (numerical Hopf integral) BEFORE differencing.

STEP 3 — integrate (lift OVERALL PREFACTOR AND SIGN from Liu et al. 2020 PRL 124,127204; do NOT re-derive):
  G_ab = (Ms/gamma) * sum_cells [ m . (d_a m x d_b m) ] * dV
  D_ab = (alpha*Ms/gamma) * sum_cells [ d_a m . d_b m ] * dV
  Ms=1.5e5, gamma=1.76e11, dV=(0.5e-9)**3. EXTRACT alpha from the .mx3 (do NOT assume); grep /mnt/d/Research/Hopfion/04_frustrated_fm_foundation/20260105_frustrated_fm/**/*.mx3 for 'alpha ='. Report alpha and its source file.
  EXCLUDE a 5-cell boundary shell (match exclude_boundary=5).

STEP 4 — VALIDATION GATES (report all; abort interpretation if any fail):
  (a) BEFORE the Hopfion, validate on a 2D Bloch skyrmion texture: must reproduce G=4*pi*Q*Ms/gamma per unit thickness WITH CORRECT SIGN. Print expected vs computed.
  (b) Antisymmetry |G_ab+G_ba|/max(|G|)<1e-3; Symmetry |D_ab-D_ba|/max(|D|)<1e-3.
  (c) Convergence: halve delta, report % change of every entry (<5%).
  (d) Closed-loop test: report |G_XY|,|G_XZ|,|G_YZ| RELATIVE to scale (Ms/gamma)*mean(|grad m|^2)*V_eff; state which are above a stated noise floor.

STEP 5 — Hall-angle prediction: theta_H_pred = degrees(atan( G_xz/(alpha*D_xx) )); also full M=G+alpha*D inverse-based angle. State assumption "F roughly along propagation (x)".

OUTPUT: /mnt/d/Research/Hopfion/results_thiele_GD_<YYYYMMDD>/G_D_tensors.json (R,r,alpha,source,entries,gates,theta_H_pred) + stdout log. Do NOT modify /mnt/d/Research/Hopfion/95_shared_scripts or simulation trees.
```

---

## Prompt C-2 [Phase 0] — 轨迹纵/横分解 + 实测霍尔角

```
TASK: Decompose driven-Hopfion trajectories into longitudinal/transverse components and compute the MEASURED Hall angle, for comparison against the Thiele prediction. NO simulation.

ENV: source /mnt/d/Research/Hopfion/hopfion/bin/activate
SHARED LIB (MANDATORY): import sys; sys.path.insert(0,'/mnt/d/Research/Hopfion/95_shared_scripts'); from hopfion_analysis import compute_hall_angle, extract_trajectory_phase_correlation

INPUT (on disk, no re-run):
  - /mnt/d/Research/Hopfion/06_eigenmode_frequency_mechanism/hopfion_mode_map_20260608/results/deformation_timeseries.csv (per-frame centroid_x/y/z, dx/dy/dz for srcX 200/1000, srcZ 100/1100 GHz)
  - cross-check vs .../freq_sweep/results/motion_mode_summary.txt
  - also any surviving freq_sweep table-derived trajectories.

METHOD per run:
  - propagation axis: srcX->'x', srcZ->'z'.
  - Build the trajectory dict compute_hall_angle expects (see its docstring); USE PHASE-CORRELATION trajectory, NOT raw weighted centroid (internal breathing contaminates centroid; state this).
  - compute_hall_angle(traj, sw_propagation_axis=axis, skip_fraction=0.33); keep valid==True only.
  - Report v_long, v_trans (late-time linear-fit slopes), theta_H_deg, theta_H_err_deg, valid.

OUTPUT: /mnt/d/Research/Hopfion/results_hall_measured_<YYYYMMDD>/hall_measured.json (per source,freq) + theta_H(f) plot for srcX with error bars. Do NOT write into repo source tree or .out dirs.
```

---

## Prompt C-3 [Phase 0] — R/r 跟踪 + 坍缩 + Q_H(t)（twist 仅诊断）

```
TASK: Track R(t), r(t), core volume, and the topological Hopf index Q_H(t) through the strong-drive runs, including the t~0.91 ns collapse. NO new simulation. SCOPE: poloidal/twist phase is a DIAGNOSTIC only (not a collective coordinate for G/D this paper).

ENV: source /mnt/d/Research/Hopfion/hopfion/bin/activate
SHARED LIB (MANDATORY, EXTEND don't rewrite, C-7): /mnt/d/Research/Hopfion/95_shared_scripts/hopfion_analysis.py has extract_Rr_series, extract_trajectory_phase_correlation, compute_Rr, core_count. ADD: hopf_index(field) (numerical Hopf integral — REUSE the project's existing Q_H routine formula; locate it first and cite the file, do NOT re-derive); and OPTIONAL poloidal_phase(field) on the mz=0 tube as a diagnostic. Keep all existing functions intact and follow the file's style.

INPUT: extract to /tmp scratch (NOT into repo):
  - /mnt/d/Research/Hopfion/04_frustrated_fm_foundation/20260105_frustrated_fm/spin_wave_dynamics/multisource_control/bidirectional_z/freq_switch_bidirectional_v3.out/ovf_archive.tar.zst  (220 frames @5 ps, 1.1 ns, includes collapse)
  - also v2 and z_bidirectional_control.out archives.

METHOD: dt_ns=0.005. extract_Rr_series->R(t),r(t); core_count->volume(t); phase-correlation->centroid(t); hopf_index->Q_H(t). Identify collapse frame; report whether Q_H actually changes (topological unwinding) vs structure destruction at fixed Q_H.

OUTPUT: /mnt/d/Research/Hopfion/results_collapse_track_<YYYYMMDD>/ CSV (t,R,r,core,centroid_xyz,Q_H[,twist]) + plots. Do NOT modify simulation .out dirs.
```

---

## Prompt C-4 [Phase 0] — 逆向 F_eff（保持非循环）

```
TASK: Extract the translation-projected effective force F_eff = (G+alpha*D).v_measured and study ONLY its dependence on (f,B,source). Keep NON-CIRCULAR: never present "F_eff reproduces v" as a result. NO simulation.

ENV: source /mnt/d/Research/Hopfion/hopfion/bin/activate
INPUTS: G,D from results_thiele_GD_<date>/G_D_tensors.json (C-1); v_measured from results_hall_measured_<date>/hall_measured.json (C-2).

METHOD:
  - F_eff = (G + alpha*D) @ v_measured per run.
  - Report F_eff DIRECTION (angle) and MAGNITUDE vs f, vs source. For source comparison: DIRECTION DISTRIBUTION and peak POSITION only — NEVER absolute magnitude across point vs plane (incomparable injection: 500 T cell vs 1 T sheet). State this caveat.
  - Label "translation-projected effective force", NOT "the magnon force".
  - Non-circularity note: the load-bearing test is the parameter-free theta_H (C-1 vs C-2); F_eff(B) scaling (once Phase-1 sweep exists) is the falsifiable extrapolation.

OUTPUT: /mnt/d/Research/Hopfion/results_Feff_<YYYYMMDD>/Feff.json + plots. Do NOT write into repo source tree.
```

---

## Prompt C-5 [Phase 1 — 暂缓] — 宽幅振幅扫描脚本生成（含控制）+ F_eff(B)

```
TASK: Generate (do NOT auto-run; user launches under the quiet-hours rule) a wide-range amplitude-sweep mumax3 batch to redo the OVERTURNED v∝B^1.99 scaling cleanly, plus three controls making srcX->+z causally attributable to topology. Provide the F_eff(B) analysis script.

TEMPLATE TO CLONE: /mnt/d/Research/Hopfion/05_spinwave_control_dynamics/20260614task/02_hopfion_spinwave_control_95_shared_scripts/plane_wave_drive.mx3. KEEP system: 100^3, 0.5nm, frustrated-FM J2=-0.164 J1, J4=-0.082 J1, Ms=1.5e5, Aex=5e-12, gamma=1.76e11. COPY J1/J2/J4 coefficient SIGNS VERBATIM from the existing .mx3 (pitfall J2J4-coefficient-sign). Use the SAME boundary condition as the template (absorbing layers + no PBC); RECORD it.

RUNS (plane srcX, f=200 GHz): B=0.01,0.02,0.05,0.1,0.2,0.5,1,2,5,10 T; 0.5 ns; table 1 ps; OVF 50 ps (11 frames — envelope v+R/r only, do NOT carrier-resolve).
CONTROLS (same drive): C1 NO Hopfion (background drift?); C2 B=0 baseline; C3 topologically trivial texture (transverse motion absent?).

ANALYSIS: from hopfion_analysis import extract_trajectory_phase_correlation, compute_Rr. Fit late-time v(B); test v∝B vs B^2; locate collapse threshold B*; F_eff(B) using G,D from C-1; report F_eff∝B (linear momentum) vs B^2 (radiation pressure).

OUTPUT: .mx3 + run_sweep.sh + analyze_ampsweep.py into NEW dir /mnt/d/Research/Hopfion/20260615_amp_sweep/ (deliverable dir, allowed). Do NOT launch mumax (respect 23:00-03:00 Singapore quiet window). Do NOT modify shared scripts.
```

---

## Prompt C-6 [Phase 2 — 期刊层级定后] — 空间 FFT k 谱 I(k,f)（含无-Hopfion 控制）

```
TASK: (ONLY if user approves Phase 2.) Generate carrier-resolved mumax3 runs + spatial-FFT analysis to test the point->plane redshift as a k-spectrum effect, WITH a no-Hopfion control to rule out box/source artifacts.

TEMPLATE: clone plane_wave_drive.mx3 (+ point-source variant) at /mnt/d/Research/Hopfion/05_spinwave_control_dynamics/20260614task/02_hopfion_spinwave_control_95_shared_scripts/. Same frustrated-FM params; COPY J2/J4 signs verbatim. RECORD boundary condition; if PBC, NOTE wrapped waves self-interfere (why the no-Hopfion control is mandatory).

RUNS (single matched freq, e.g. 800 GHz where redshift lands): plane srcX, point srcX, EACH with/without the Hopfion = 4 runs. CARRIER-RESOLVED OVF: every ~0.1 ps, >=10 frames/period, >=20 periods. WARN any freq where wavelength < ~6 cells (aliasing); report wavelength-in-cells.

ANALYSIS: spatial FFT far from Hopfion -> I(k,f); with/without -> transmission/reflection -> momentum-flux estimate for F. Compare plane vs point: PEAK POSITION, k-DISTRIBUTION, DIRECTION only — NEVER absolute efficiency. If no-Hopfion control already shows the plane/point difference, the redshift is partly a source/box effect — state this.

OUTPUT: /mnt/d/Research/Hopfion/20260615_kspectrum/ (scripts + I_kf.json + plots). Disk ~12 GB — confirm with user before launch. Do NOT auto-run.
```
