"""
Compute the Hopf index Q_H of magnetization fields from OVF files.

Method: Fourier-space computation of the Chern-Simons integral.
  1. Compute emergent magnetic field Ω_i = m · (∂_j m × ∂_k m) for cyclic (i,j,k)
  2. Solve ∇ × A = Ω in Fourier space (Coulomb gauge)
  3. Q_H = (normalization) × ∫ A · Ω d³r

Normalization is calibrated against known analytic initial states.
"""

import sys
sys.path.insert(0, "/mnt/d/Research/Hopfion/scripts")

import numpy as np
import discretisedfield as df


def compute_hopf_index(field_or_path, pbc=True, verbose=True):
    """Compute the Hopf index from an OVF file or discretisedfield.Field."""
    if isinstance(field_or_path, str):
        field = df.Field.from_file(field_or_path)
        if verbose:
            print(f"Loaded: {field_or_path}")
    else:
        field = field_or_path

    m = field.array.copy()  # (Nx, Ny, Nz, 3)
    # Normalize each spin to unit length
    norm = np.linalg.norm(m, axis=-1, keepdims=True)
    norm[norm < 1e-10] = 1.0
    m = m / norm

    Nx, Ny, Nz, _ = m.shape
    if verbose:
        print(f"Grid: {Nx}×{Ny}×{Nz}")

    # Cell size (assume uniform cubic)
    mesh = field.mesh
    dx = (mesh.region.pmax[0] - mesh.region.pmin[0]) / Nx

    # --- Step 1: Spatial derivatives with PBC or zero-padding ---
    def deriv(arr, axis):
        """Central difference along axis, PBC or forward/backward at boundaries."""
        if pbc:
            return (np.roll(arr, -1, axis=axis) - np.roll(arr, 1, axis=axis)) / (2 * dx)
        else:
            d = np.zeros_like(arr)
            slc_p = [slice(None)] * arr.ndim
            slc_m = [slice(None)] * arr.ndim
            slc_c = [slice(None)] * arr.ndim

            # Central difference for interior
            slc_p[axis] = slice(2, None)
            slc_m[axis] = slice(None, -2)
            slc_c[axis] = slice(1, -1)
            d[tuple(slc_c)] = (arr[tuple(slc_p)] - arr[tuple(slc_m)]) / (2 * dx)

            # Forward/backward at boundaries
            slc_0 = [slice(None)] * arr.ndim
            slc_1 = [slice(None)] * arr.ndim
            slc_n = [slice(None)] * arr.ndim
            slc_n1 = [slice(None)] * arr.ndim
            slc_0[axis] = 0
            slc_1[axis] = 1
            slc_n[axis] = -1
            slc_n1[axis] = -2
            d[tuple(slc_0)] = (arr[tuple(slc_1)] - arr[tuple(slc_0)]) / dx
            d[tuple(slc_n)] = (arr[tuple(slc_n)] - arr[tuple(slc_n1)]) / dx
            return d

    dm_dx = deriv(m, 0)  # (Nx, Ny, Nz, 3)
    dm_dy = deriv(m, 1)
    dm_dz = deriv(m, 2)

    # --- Step 2: Emergent magnetic field Ω_i = m · (∂_j m × ∂_k m) ---
    # Ω_x = m · (∂_y m × ∂_z m)
    # Ω_y = m · (∂_z m × ∂_x m)
    # Ω_z = m · (∂_x m × ∂_y m)
    Omega_x = np.sum(m * np.cross(dm_dy, dm_dz), axis=-1)
    Omega_y = np.sum(m * np.cross(dm_dz, dm_dx), axis=-1)
    Omega_z = np.sum(m * np.cross(dm_dx, dm_dy), axis=-1)

    if verbose:
        print(f"Ω range: x=[{Omega_x.min():.4f}, {Omega_x.max():.4f}], "
              f"y=[{Omega_y.min():.4f}, {Omega_y.max():.4f}], "
              f"z=[{Omega_z.min():.4f}, {Omega_z.max():.4f}]")
        # Check divergence-free: ∇·Ω should be ~0
        div = deriv(Omega_x[..., None], 0)[..., 0] + \
              deriv(Omega_y[..., None], 1)[..., 0] + \
              deriv(Omega_z[..., None], 2)[..., 0]
        print(f"∇·Ω (should be ~0): max|div| = {np.abs(div).max():.6f}, mean|div| = {np.abs(div).mean():.6f}")

    # --- Step 3: Solve ∇ × A = Ω in Fourier space ---
    # Fourier transform
    Omega_x_k = np.fft.fftn(Omega_x)
    Omega_y_k = np.fft.fftn(Omega_y)
    Omega_z_k = np.fft.fftn(Omega_z)

    # k-vectors
    kx = np.fft.fftfreq(Nx, d=dx) * 2 * np.pi
    ky = np.fft.fftfreq(Ny, d=dx) * 2 * np.pi
    kz = np.fft.fftfreq(Nz, d=dx) * 2 * np.pi
    KX, KY, KZ = np.meshgrid(kx, ky, kz, indexing='ij')
    K2 = KX**2 + KY**2 + KZ**2
    K2[0, 0, 0] = 1.0  # avoid division by zero

    # Coulomb gauge: A(k) = i k × Ω(k) / |k|²
    Ax_k = 1j * (KY * Omega_z_k - KZ * Omega_y_k) / K2
    Ay_k = 1j * (KZ * Omega_x_k - KX * Omega_z_k) / K2
    Az_k = 1j * (KX * Omega_y_k - KY * Omega_x_k) / K2

    # Zero mode
    Ax_k[0, 0, 0] = 0
    Ay_k[0, 0, 0] = 0
    Az_k[0, 0, 0] = 0

    # Inverse FFT
    Ax = np.real(np.fft.ifftn(Ax_k))
    Ay = np.real(np.fft.ifftn(Ay_k))
    Az = np.real(np.fft.ifftn(Az_k))

    # --- Step 4: Q_H = C × ∫ A · Ω d³r ---
    dV = dx**3
    integrand = Ax * Omega_x + Ay * Omega_y + Az * Omega_z
    raw_integral = np.sum(integrand) * dV

    # The Hopf index: Q_H = -1/(16π²) × ∫ A · Ω d³r
    # (with our convention Ω_i = m·(∂_j m × ∂_k m), no 1/(4π) prefactor)
    Q_H = -raw_integral / (16 * np.pi**2)

    if verbose:
        print(f"Raw integral = {raw_integral:.6e}")
        print(f"Q_H = {Q_H:.4f} (rounded: {round(Q_H)})")

    return Q_H


if __name__ == "__main__":
    BASE = "/mnt/d/Research/Hopfion/20260105_frustrated_fm"

    files = {
        "Initial Qh1 small (analytic)":
            f"{BASE}/anisotropy_study/size_vs_ku/hopfion_Qh1_FM_SMALL.ovf",
        "Initial R8r4 (analytic)":
            f"{BASE}/anisotropy_study/ku_critical_sweep/hopfion_z_R8_r4.ovf",
        "Initial Qh2 p1q2 (analytic)":
            f"{BASE}/spin_wave_dynamics/UNUSED_analytic_Qh2_p1q2.ovf",
        "Relaxed Ku0 (from R8r4, 1ns)":
            f"{BASE}/anisotropy_study/ku_critical_sweep/R8r4_Ku0.out/m000020.ovf",
        "Relaxed Ku10k (from R8r4, 1ns)":
            f"{BASE}/anisotropy_study/ku_critical_sweep/R8r4_Ku10k.out/m000020.ovf",
        "Centered Ku10k (roll-shifted)":
            f"{BASE}/centered_stability_test/centered_Ku10k.ovf",
        "Stability Ku10k (1ns PBC relax)":
            f"{BASE}/centered_stability_test/stability_Ku10k.out/m000020.ovf",
        "Relaxed Ku0 (from Qh1 small, 3ns)":
            f"{BASE}/anisotropy_study/size_vs_ku/Ku1_0.0e+00_Ms_1.5000e+05.out/m000030.ovf",
        "Relaxed Ku10k (from Qh1 small, 3ns)":
            f"{BASE}/anisotropy_study/size_vs_ku/Ku1_1.0e+04_Ms_1.5000e+05.out/m000030.ovf",
    }

    print("=" * 70)
    print("HOPF INDEX VERIFICATION")
    print("=" * 70)

    results = {}
    for label, path in files.items():
        print(f"\n--- {label} ---")
        try:
            # Use PBC for most cases; centered_stability_test uses PBC
            # ku_critical_sweep mx3 scripts may use PBC or OBC - need to check
            qh = compute_hopf_index(path, pbc=True, verbose=True)
            results[label] = qh
        except Exception as e:
            print(f"ERROR: {e}")
            results[label] = None

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    for label, qh in results.items():
        if qh is not None:
            print(f"  {label:45s} → Q_H = {qh:+.4f} (≈ {round(qh)})")
        else:
            print(f"  {label:45s} → FAILED")
