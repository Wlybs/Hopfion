"""
TC.1 static-texture translation Thiele tensor convergence ladder.

No micromagnetic simulation is run. Re-analyzes the SAME relaxed texture used by
the 2026-06-15 first-pass calculation (m000020.ovf from stability_Ku10k.out),
replacing the single delta=1-vs-delta=2 finite-difference comparison with four
independent differentiation methods, cross-validated against each other:

  1. Richardson (Neville) extrapolation over centered finite differences at
     delta = 1, 2, 3, 4 cells (expansion in even powers of h).
  2. A single 4th-order (5-point) centered stencil at delta = 1 cell.
  3. Exact spectral (FFT) derivative on the native 100^3 grid (valid because
     the texture is defined on a fully periodic mesh, SetPBC(1,1,1)).
  4. Fourier (trigonometric) supersampling of the texture to 2x and 4x
     resolution, followed by spectral differentiation on the finer grid.

Convergence gate (GC1): all pairwise disagreements between the five method
estimates (Richardson-FD, 4th-order-FD, spectral-native, supersample-2x,
supersample-4x), for every tensor component, must be <=5% of the natural
scale S. This directly follows master-plan wording: "all small G changes are
expressed relative to the natural scale S; the zero-verdict must hold at
every delta" (00_project_index/hopfion_spinwave_paper_master_plan_20260703.md
Section 4, WS-C, TC.1 / GATE GC1).

If GC1 fails, this script explicitly withholds the "G is zero" headline and
the Hall-angle prediction, per Section 8 must-not-say rules.

The 2026-06-15 skyrmion calibration (0.17% relative error at 401x401
over-resolution) is NOT reused here to bound Hopfion tensor precision -- the
master plan (TC.3, Section 4 / Section 8 item 5) explicitly forbids that.
A fresh, same-method (spectral) calibration check is run at matched
resolution purely as an implementation correctness sanity check (sign and
literature prefactor), not as an error bar for the Hopfion result.
"""

import itertools
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

import numpy as np
from scipy.signal import resample

# ----------------------------------------------------------------------
# Paths and physical constants (verbatim from the 2026-06-15 first pass,
# results_thiele_GD_translation_20260615/G_D_translation.json).
# ----------------------------------------------------------------------

ARCHIVE_SOURCE = (
    r"D:\Research\Hopfion\04_frustrated_fm_foundation\20260105_frustrated_fm"
    r"\centered_stability_test\stability_Ku10k.out\ovf_archive.tar.zst"
)
MEMBER = "m000020.ovf"
OUT_DIR = r"D:\Research\Hopfion\07_thiele_theory_model\results_thiele_GD_convergence_20260703"
TAR_EXE = r"C:\Windows\System32\tar.exe"  # bsdtar with libzstd; ships with Windows 10 1803+


def extract_member(archive_path, member, tar_exe=TAR_EXE):
    """Extract a single member from a .tar.zst archive into a fresh temp dir
    using the system bsdtar (libzstd-enabled). Returns (extracted_path, tmpdir)."""
    tmpdir = tempfile.mkdtemp(prefix="thiele_GD_convergence_")
    subprocess.run(
        [tar_exe, "--zstd", "-xf", archive_path, "-C", tmpdir, member],
        check=True, capture_output=True,
    )
    extracted = os.path.join(tmpdir, member)
    if not os.path.isfile(extracted):
        raise FileNotFoundError(f"expected {extracted} after tar extraction")
    return extracted, tmpdir

Ms = 150000.0          # A/m
GAMMA = 1.76e11         # rad s^-1 T^-1
ALPHA = 0.001           # material alpha, verbatim from sw_*.mx3 (plane_wave amplitude_sweep set)
ALPHA_SOURCE = (
    r"04_frustrated_fm_foundation\20260105_frustrated_fm\spin_wave_dynamics"
    r"\amplitude_sweep\plane_wave\sw_B1p0T.mx3"
)

LITERATURE = {
    "source": "Y. Liu et al., Phys. Rev. Lett. 124, 127204 (2020)",
    "doi": "https://doi.org/10.1103/PhysRevLett.124.127204",
    "arxiv": "https://arxiv.org/abs/2001.00417",
    "G_convention": "G_ab = +(Ms/gamma) * integral m . (d_a m x d_b m) dV",
    "D_convention": "D_ab = +(alpha*Ms/gamma) * integral (d_a m . d_b m) dV",
}

GATE_THRESHOLD_PERCENT_OF_S = 5.0
NOISE_FLOOR_FRACTION_OF_S = 0.03


def log(msg):
    print(msg)
    LOGLINES.append(msg)


LOGLINES = []


# ----------------------------------------------------------------------
# OVF2 binary4 reader (no discretisedfield dependency; hand-parsed per the
# OOMMF OVF 2.0 spec, matching the format Mumax3 writes).
# ----------------------------------------------------------------------

def read_ovf2_binary4(path):
    with open(path, "rb") as f:
        raw = f.read()
    marker = b"# Begin: Data Binary 4\n"
    idx = raw.find(marker)
    if idx == -1:
        raise ValueError("OVF2 binary4 data marker not found: " + path)
    header_text = raw[:idx].decode("utf-8", errors="strict")
    data_start = idx + len(marker)

    hdr = {}
    for line in header_text.splitlines():
        line = line.strip()
        if not line.startswith("#"):
            continue
        line = line[1:].strip()
        if ":" in line:
            k, v = line.split(":", 1)
            hdr[k.strip()] = v.strip()

    nx = int(hdr["xnodes"])
    ny = int(hdr["ynodes"])
    nz = int(hdr["znodes"])
    valuedim = int(hdr.get("valuedim", "3"))
    hx = float(hdr["xstepsize"])
    hy = float(hdr["ystepsize"])
    hz = float(hdr["zstepsize"])

    control = np.frombuffer(raw, dtype="<f4", count=1, offset=data_start)[0]
    if abs(float(control) - 1234567.0) > 1.0:
        raise ValueError(f"OVF control value mismatch: {control} (expected 1234567.0)")

    n_values = nx * ny * nz * valuedim
    body = np.frombuffer(raw, dtype="<f4", count=n_values, offset=data_start + 4)
    body = body.reshape(nz, ny, nx, valuedim)                  # OVF order: z slowest, x fastest
    arr = np.ascontiguousarray(np.transpose(body, (2, 1, 0, 3)).astype(np.float64))

    end_marker = raw.find(b"# End: Data Binary 4", data_start)
    if end_marker == -1:
        log("WARNING: '# End: Data Binary 4' footer not found; file may be truncated.")

    return arr, dict(nx=nx, ny=ny, nz=nz, hx=hx, hy=hy, hz=hz, header=hdr)


# ----------------------------------------------------------------------
# Differentiation methods
# ----------------------------------------------------------------------

def periodic_central_diff(field, axis, delta, spacing):
    fwd = np.roll(field, -delta, axis=axis)
    bwd = np.roll(field, delta, axis=axis)
    return (fwd - bwd) / (2.0 * delta * spacing)


def periodic_4th_order_diff(field, axis, spacing):
    fm2 = np.roll(field, 2, axis=axis)
    fm1 = np.roll(field, 1, axis=axis)
    fp1 = np.roll(field, -1, axis=axis)
    fp2 = np.roll(field, -2, axis=axis)
    return (-fp2 + 8.0 * fp1 - 8.0 * fm1 + fm2) / (12.0 * spacing)


def spectral_diff(field, axis, spacing, n):
    k = 2.0 * np.pi * np.fft.fftfreq(n, d=spacing)
    shape = [1] * field.ndim
    shape[axis] = n
    ik = (1j * k).reshape(shape)
    F = np.fft.fft(field, axis=axis)
    d = np.fft.ifft(F * ik, axis=axis)
    return d.real


def richardson_extrapolate(values_by_delta):
    """Neville extrapolation to h -> 0 assuming an expansion in even powers of h.
    values_by_delta: dict {delta_int: ndarray}, delta in units of the base cell."""
    deltas = sorted(values_by_delta.keys())
    xs = [float(d) ** 2 for d in deltas]           # expand in h^2
    T = [values_by_delta[d].copy() for d in deltas]
    n = len(xs)
    for k in range(1, n):
        newT = []
        for i in range(n - k):
            xi, xik = xs[i], xs[i + k]
            num = (0.0 - xik) * T[i] - (0.0 - xi) * T[i + 1]
            newT.append(num / (xi - xik))
        T = newT
    return T[0]


def compute_GD(dm, m, dV):
    """dm: dict{0,1,2 -> partial derivative array (...,3)}; m: (...,3). Returns raw (unscaled) G, D sums."""
    G = np.zeros((3, 3))
    D = np.zeros((3, 3))
    for a in range(3):
        for b in range(3):
            cross_ab = np.cross(dm[a], dm[b])
            G[a, b] = np.sum(np.einsum("...i,...i->...", m, cross_ab)) * dV
            D[a, b] = np.sum(np.einsum("...i,...i->...", dm[a], dm[b])) * dV
    G_scaled = G * (Ms / GAMMA)
    D_scaled = D * (ALPHA * Ms / GAMMA)
    return G_scaled, D_scaled


def fourier_supersample(field, factor):
    """Trigonometric (band-limited) interpolation to factor*n along each of the
    first 3 axes, via scipy.signal.resample (handles even-length Nyquist split
    correctly). Casts to float32 to bound memory for factor=4."""
    big = field.astype(np.float32)
    for axis, n0 in enumerate(field.shape[:3]):
        big = resample(big, n0 * factor, axis=axis).astype(np.float32)
    return big


# ----------------------------------------------------------------------
# Skyrmion sanity check (implementation correctness only; NOT an error bar
# for the Hopfion result -- see module docstring and master-plan Section 8).
# ----------------------------------------------------------------------

def skyrmion_sanity_check(n=100, box_L_nm=50.0):
    """2D Bloch skyrmion, core -z, background +z, vorticity +1, on the SAME
    100x100 in-plane resolution / box size as the Hopfion mesh (0.5 nm cells),
    periodic in x,y. Checks sign and literature prefactor of the G_xy formula
    via the same spectral-derivative code path used on the real texture."""
    h = box_L_nm / n * 1e-9
    x = (np.arange(n) + 0.5) * h - box_L_nm * 1e-9 / 2.0
    X, Y = np.meshgrid(x, x, indexing="ij")
    R = np.sqrt(X ** 2 + Y ** 2)
    R0 = 8.0e-9
    profile_width = 4.0e-9
    mz = -np.tanh((R0 - R) / profile_width)
    rho = np.sqrt(np.clip(1.0 - mz ** 2, 0.0, 1.0))
    phi = np.arctan2(Y, X)
    mx = -rho * np.sin(phi)   # Bloch (chirality +1), vorticity +1
    my = rho * np.cos(phi)
    m = np.stack([mx, my, mz], axis=-1)
    m = m / np.linalg.norm(m, axis=-1, keepdims=True)

    dmx = spectral_diff(m, 0, h, n)
    dmy = spectral_diff(m, 1, h, n)
    dm = {0: dmx, 1: dmy}
    cross_xy = np.cross(dm[0], dm[1])
    G_xy_raw = float(np.sum(np.einsum("...i,...i->...", m, cross_xy))) * h * h
    # computed_Q is DERIVED from the same integral as G_xy_raw (Q = G_xy_raw/4pi by
    # construction) -- it is reported only as a transparency check that the
    # synthetic profile was built with the intended winding, NOT as the reference
    # the G_xy formula is validated against (that would be a tautology).
    computed_Q = G_xy_raw / (4.0 * np.pi)

    analytic_Q_target = -1  # by construction: core -z, background +z, vorticity +1, Bloch
    G_xy_per_thickness = G_xy_raw * (Ms / GAMMA)
    # independent reference value: G_xy = (Ms/gamma) * 4*pi * Q, evaluated at the
    # FIXED topological target, not at computed_Q.
    expected_G_xy_per_thickness = 4.0 * np.pi * analytic_Q_target * Ms / GAMMA

    rel_err = abs(G_xy_per_thickness - expected_G_xy_per_thickness) / abs(expected_G_xy_per_thickness)
    q_rel_err = abs(computed_Q - analytic_Q_target) / abs(analytic_Q_target)
    return dict(
        note="sanity check only -- NOT used to bound Hopfion tensor precision (master plan TC.3/Section 8 item 5)",
        grid=[n, n],
        spacing_m=h,
        analytic_Q_target=analytic_Q_target,
        computed_Q=computed_Q,
        computed_Q_relative_error_percent=q_rel_err * 100.0,
        computed_G_xy_SI_per_m=G_xy_per_thickness,
        expected_G_xy_SI_per_m=expected_G_xy_per_thickness,
        relative_error=rel_err,
        relative_error_percent=rel_err * 100.0,
        pass_=bool(rel_err < 0.05),
    )


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------

def main():
    t0 = time.time()
    log("STATIC-TEXTURE TRANSLATION-BLOCK THIELE ANALYSIS -- CONVERGENCE LADDER (TC.1)")
    log("No micromagnetic simulation is run.")
    log(f"Archive: {ARCHIVE_SOURCE}")
    log(f"Texture member: {MEMBER}")
    log(f"G convention: {LITERATURE['G_convention']}")
    log(f"D convention: {LITERATURE['D_convention']}")
    log(f"Literature: {LITERATURE['source']}, DOI {LITERATURE['doi']}")
    log("")

    ovf_path, tmpdir = extract_member(ARCHIVE_SOURCE, MEMBER)
    log(f"Extracted {MEMBER} to scratch: {ovf_path}")
    try:
        arr, meta = read_ovf2_binary4(ovf_path)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
        log(f"Scratch cleaned: {tmpdir}")
    nx, ny, nz = meta["nx"], meta["ny"], meta["nz"]
    hx, hy, hz = meta["hx"], meta["hy"], meta["hz"]
    assert hx == hy == hz, "non-cubic cells not supported by this script"
    h = hx
    dV = hx * hy * hz

    norm = np.linalg.norm(arr, axis=-1, keepdims=True)
    max_norm_err = float(np.max(np.abs(norm - 1.0)))
    arr = arr / norm

    log(f"REAL RELAXED TEXTURE: shape=({nx},{ny},{nz}), cell={h*1e9:.4f} nm, "
        f"max|m|-1 error before renorm = {max_norm_err:.3e}")
    log("")

    # ---- Method 1: Richardson (Neville) extrapolation over delta=1..4 ----
    deltas = [1, 2, 3, 4]
    G_by_delta = {}
    D_by_delta = {}
    for d_ in deltas:
        dm = {a: periodic_central_diff(arr, a, d_, h) for a in range(3)}
        G_by_delta[d_], D_by_delta[d_] = compute_GD(dm, arr, dV)

    log("RAW DELTA LADDER (for continuity with the 2026-06-15 first pass):")
    for d_ in deltas:
        log(f"  delta={d_}: G_XY={G_by_delta[d_][0,1]:.6e}  D_XX={D_by_delta[d_][0,0]:.6e}  "
            f"D_YY={D_by_delta[d_][1,1]:.6e}  D_ZZ={D_by_delta[d_][2,2]:.6e}")
    log("")

    G_richardson = richardson_extrapolate(G_by_delta)
    D_richardson = richardson_extrapolate(D_by_delta)

    # ---- Method 2: 4th-order 5-point stencil at delta=1 ----
    dm4 = {a: periodic_4th_order_diff(arr, a, h) for a in range(3)}
    G_4th, D_4th = compute_GD(dm4, arr, dV)

    # ---- Method 3: spectral derivative, native 100^3 grid ----
    dm_spec = {0: spectral_diff(arr, 0, h, nx),
               1: spectral_diff(arr, 1, h, ny),
               2: spectral_diff(arr, 2, h, nz)}
    G_spec, D_spec = compute_GD(dm_spec, arr, dV)

    # natural scale S, defined identically to the 2026-06-15 first pass,
    # using the spectral derivative (most accurate available) on the native grid.
    grad_sq = sum(np.sum(dm_spec[a] ** 2, axis=-1) for a in range(3))
    mean_grad_sq = float(np.mean(grad_sq))
    V_eff = nx * ny * nz * dV
    S = (Ms / GAMMA) * mean_grad_sq * V_eff
    log(f"Natural scale S = {S:.6e} (SI)")
    log("  NOTE: this uses the FULL 100^3 box (PBC wrap is exact, no boundary exclusion).")
    log("  The 2026-06-15 first pass reported S=3.7607e-13 using only the inner box with a")
    log("  5-cell margin excluded on each face (V_eff/V_full=0.729); that exclusion is not")
    log("  needed here because all derivatives below are computed with genuine periodic")
    log("  wrap, not a truncated stencil near the array edge.")
    log("")

    # ---- Method 4: Fourier supersampling 2x, 4x + spectral derivative ----
    supersample_results = {}
    for factor in (2, 4):
        t_s = time.time()
        big = fourier_supersample(arr, factor)
        norm_big = np.linalg.norm(big, axis=-1, keepdims=True)
        norm_big = np.where(norm_big == 0, 1.0, norm_big).astype(np.float32)
        big = (big / norm_big).astype(np.float32)
        h_fine = h / factor
        dV_fine = h_fine ** 3
        n_fine = nx * factor
        dm_big = {0: spectral_diff(big, 0, h_fine, n_fine),
                  1: spectral_diff(big, 1, h_fine, n_fine),
                  2: spectral_diff(big, 2, h_fine, n_fine)}
        G_b, D_b = compute_GD(dm_big, big, dV_fine)
        supersample_results[factor] = (G_b, D_b)
        log(f"supersample {factor}x done in {time.time()-t_s:.1f}s "
            f"(grid {n_fine}^3): G_XY={G_b[0,1]:.6e}  D_XX={D_b[0,0]:.6e}")
        del big, dm_big
    log("")

    methods = {
        "richardson_fd_delta1to4": (G_richardson, D_richardson),
        "fourth_order_fd_delta1": (G_4th, D_4th),
        "spectral_native_100cube": (G_spec, D_spec),
        "supersample_2x_spectral": supersample_results[2],
        "supersample_4x_spectral": supersample_results[4],
    }

    log("METHOD COMPARISON (G components, SI):")
    for name, (G, D) in methods.items():
        log(f"  {name:28s}  G_XY={G[0,1]: .6e}  G_XZ={G[0,2]: .6e}  G_YZ={G[1,2]: .6e}")
    log("")
    log("METHOD COMPARISON (D diagonal, SI):")
    for name, (G, D) in methods.items():
        log(f"  {name:28s}  D_XX={D[0,0]: .6e}  D_YY={D[1,1]: .6e}  D_ZZ={D[2,2]: .6e}")
    log("")

    # ---- GATE GC1: pairwise disagreement across ALL FIVE methods, relative to S ----
    method_names = list(methods.keys())
    max_rel_diff_G = np.zeros((3, 3))
    max_rel_diff_D = np.zeros((3, 3))
    worst_pair_G = np.empty((3, 3), dtype=object)
    worst_pair_D = np.empty((3, 3), dtype=object)
    for n1, n2 in itertools.combinations(method_names, 2):
        G1, D1 = methods[n1]
        G2, D2 = methods[n2]
        diff_G = np.abs(G1 - G2) / S
        diff_D = np.abs(D1 - D2) / S
        upd_G = diff_G > max_rel_diff_G
        upd_D = diff_D > max_rel_diff_D
        max_rel_diff_G = np.where(upd_G, diff_G, max_rel_diff_G)
        max_rel_diff_D = np.where(upd_D, diff_D, max_rel_diff_D)
        for i in range(3):
            for j in range(3):
                if upd_G[i, j]:
                    worst_pair_G[i, j] = f"{n1} vs {n2}"
                if upd_D[i, j]:
                    worst_pair_D[i, j] = f"{n1} vs {n2}"

    gate_threshold = GATE_THRESHOLD_PERCENT_OF_S / 100.0
    gc1_G_pass = bool(np.all(max_rel_diff_G <= gate_threshold))
    gc1_D_pass = bool(np.all(max_rel_diff_D <= gate_threshold))
    gc1_pass = gc1_G_pass and gc1_D_pass

    log("GATE GC1: CROSS-METHOD CONVERGENCE (5 methods, pairwise, relative to S)")
    log(f"  threshold: {GATE_THRESHOLD_PERCENT_OF_S:.1f}% of S = {S*gate_threshold:.3e} (SI)")
    log("  max pairwise |Delta G_ab| / S (percent):")
    for i in range(3):
        row = "    " + "  ".join(f"{max_rel_diff_G[i,j]*100:8.4f}%" for j in range(3))
        log(row)
    log("  max pairwise |Delta D_ab| / S (percent):")
    for i in range(3):
        row = "    " + "  ".join(f"{max_rel_diff_D[i,j]*100:8.4f}%" for j in range(3))
        log(row)
    log(f"  G sub-gate PASS: {gc1_G_pass}")
    log(f"  D sub-gate PASS: {gc1_D_pass}")
    log(f"  GATE GC1 PASS: {gc1_pass}")
    log("")

    # ---- symmetry gate (should be automatic; verified numerically) ----
    G_best, D_best = methods["supersample_4x_spectral"]
    antisym_err = float(np.max(np.abs(G_best + G_best.T)) / max(np.max(np.abs(G_best)), 1e-300))
    sym_err = float(np.max(np.abs(D_best - D_best.T)) / max(np.max(np.abs(D_best)), 1e-300))
    log("GATE: TENSOR ALGEBRA (finest method, supersample_4x_spectral)")
    log(f"  max|G+G^T|/max|G|: {antisym_err:.3e}")
    log(f"  max|D-D^T|/max|D|: {sym_err:.3e}")
    tensor_gate_pass = bool(antisym_err < 1e-3 and sym_err < 1e-3)
    log(f"  PASS: {tensor_gate_pass}")
    log("")

    # ---- closed-loop zero check, using the finest converged method ----
    log("CLOSED-LOOP TRANSLATIONAL GYROCOUPLING (finest method = supersample_4x_spectral)")
    closed_loop = {}
    for label, (i, j) in {"XY": (0, 1), "XZ": (0, 2), "YZ": (1, 2)}.items():
        val = float(G_best[i, j])
        rel = abs(val) / S
        below_floor = bool(rel < NOISE_FLOOR_FRACTION_OF_S)
        closed_loop[label] = dict(
            absolute_G_SI=val,
            relative_to_S=rel,
            relative_percent_of_S=rel * 100.0,
            noise_floor_fraction_of_S=NOISE_FLOOR_FRACTION_OF_S,
            verdict=("below 3% noise floor; consistent with zero" if below_floor
                     else "ABOVE 3% noise floor; NOT consistent with zero"),
        )
        log(f"  |G_{label}|={abs(val):.6e}; |G_{label}|/S={rel*100:.6f}%; "
            f"{'below' if below_floor else 'ABOVE'} 3% noise floor")
    all_zero = bool(all(v["absolute_G_SI"] == 0 or abs(v["absolute_G_SI"]) / S < NOISE_FLOOR_FRACTION_OF_S
                         for v in closed_loop.values()))
    log(f"  all three consistent with zero: {all_zero}")
    log("")

    # ---- implementation sanity check (NOT an Hopfion error bar) ----
    sky = skyrmion_sanity_check(n=nx)
    log("IMPLEMENTATION SANITY CHECK (2D Bloch skyrmion, matched 100x100 in-plane grid):")
    log(f"  {sky['note']}")
    log(f"  computed Q={sky['computed_Q']:.6f} (target {sky['analytic_Q_target']})")
    log(f"  computed G_xy={sky['computed_G_xy_SI_per_m']:.6e}  expected={sky['expected_G_xy_SI_per_m']:.6e}")
    log(f"  relative error: {sky['relative_error_percent']:.4f}%  PASS: {sky['pass_']}")
    log("")

    # ---- final integrity gate ----
    all_gates_pass = bool(gc1_pass and tensor_gate_pass)
    log("=" * 70)
    if all_gates_pass:
        log("GATE GC1 PASS: all four differentiation methods (plus Richardson) agree")
        log("within 5% of the natural scale S. Convergence gate CLEARED.")
        if all_zero:
            log("Closed-loop translational G is consistent with zero at the noise floor,")
            log("with convergence CONFIRMED (not merely unconfirmed as in the 2026-06-15 pass).")
        else:
            log("Closed-loop translational G is ABOVE the noise floor with convergence")
            log("CONFIRMED -- a nonzero-G interpretation may proceed to GC-FINAL (requires TC.4).")
        log("No Hall-angle number is computed here; that requires TC.4 measured deflection")
        log("and is gated at GC-FINAL per the master plan.")
    else:
        log("GATE GC1 FAIL: at least one pairwise method disagreement exceeds 5% of S.")
        log("STOP: no zero-G / near-zero-Hall headline may be reported.")
        log("Per master-plan Section 4 (WS-C) this routes to TC.2: conditional fine-grid")
        log("re-relaxation (200^3 @ 0.25 nm) with J2/J4 copied verbatim from R8r4_Ku0.mx3,")
        log("or TC.3 bounded-uncertainty reporting if TC.2 also fails to converge.")
    log("=" * 70)

    elapsed = time.time() - t0
    log(f"\nTotal wall time: {elapsed:.1f} s")

    # ---- JSON payload ----
    def mat(a):
        return [[float(a[i, j]) for j in range(3)] for i in range(3)]

    payload = {
        "analysis": "static texture, translation coordinates X/Y/Z, convergence ladder (TC.1)",
        "status": "gate_cleared" if all_gates_pass else "stopped_after_failed_convergence_gate",
        "integrity": {
            "no_micromagnetic_simulation_run": True,
            "no_eigenfrequency_claim": True,
            "hall_angle_computed": False,
            "hall_angle_withheld_reason": "requires TC.4 measured deflection; gated at GC-FINAL",
            "skyrmion_calibration_used_to_bound_hopfion_precision": False,
        },
        "literature_convention": LITERATURE,
        "constants": {
            "Ms_A_per_m": Ms,
            "gamma_SI": GAMMA,
            "alpha": ALPHA,
            "alpha_source_file": ALPHA_SOURCE,
            "cell_spacing_m": h,
            "cell_volume_m3": dV,
        },
        "texture": {
            "archive": ARCHIVE_SOURCE,
            "member": MEMBER,
            "mesh_shape": [nx, ny, nz],
            "mesh_cell_m": [hx, hy, hz],
            "max_unit_norm_error_before_renormalization": max_norm_err,
        },
        "natural_scale_S_SI": S,
        "natural_scale_S_note": (
            "Full 100^3 box, exact periodic wrap; no boundary-cell exclusion. The "
            "2026-06-15 first pass used S=3.7607e-13 with a 5-cell margin excluded on "
            "each face (V_eff/V_full=0.729); not needed here since all derivatives use "
            "genuine periodic wrap rather than a truncated stencil near the array edge."
        ),
        "raw_delta_ladder": {
            str(d_): {"G_SI": mat(G_by_delta[d_]), "D_SI": mat(D_by_delta[d_])}
            for d_ in deltas
        },
        "methods": {
            name: {"G_SI": mat(G), "D_SI": mat(D)} for name, (G, D) in methods.items()
        },
        "gates": {
            "GC1_cross_method_convergence": {
                "threshold_percent_of_S": GATE_THRESHOLD_PERCENT_OF_S,
                "max_pairwise_G_percent_of_S": mat(max_rel_diff_G * 100.0),
                "max_pairwise_D_percent_of_S": mat(max_rel_diff_D * 100.0),
                "worst_pair_G": [[worst_pair_G[i, j] for j in range(3)] for i in range(3)],
                "worst_pair_D": [[worst_pair_D[i, j] for j in range(3)] for i in range(3)],
                "G_subgate_pass": gc1_G_pass,
                "D_subgate_pass": gc1_D_pass,
                "pass": gc1_pass,
            },
            "tensor_algebra": {
                "antisymmetry_relative_error": antisym_err,
                "D_symmetry_relative_error": sym_err,
                "threshold": 1.0e-3,
                "pass": tensor_gate_pass,
            },
            "closed_loop_translational_gyrocoupling": {
                "method": "supersample_4x_spectral",
                "components": closed_loop,
                "all_three_consistent_with_zero": all_zero,
            },
            "skyrmion_implementation_sanity_check": sky,
        },
        "all_numeric_validation_gates_pass": all_gates_pass,
        "hall_prediction": None,
        "hall_prediction_withheld_reason": (
            None if not all_gates_pass else
            "GC1 cleared, but Hall-angle prediction additionally requires TC.4 measured "
            "deflection and is gated at GC-FINAL; not computed in this script."
        ) if all_gates_pass else "GC1 (cross-method convergence) failed; stopped before interpretation.",
        "wall_time_seconds": elapsed,
    }

    json_path = os.path.join(OUT_DIR, "G_D_translation_convergence.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    log(f"\nJSON written: {json_path}")

    log_path = os.path.join(OUT_DIR, "G_D_translation_convergence_stdout.log")
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("\n".join(LOGLINES) + "\n")
    print(f"Log written: {log_path}")


if __name__ == "__main__":
    main()
