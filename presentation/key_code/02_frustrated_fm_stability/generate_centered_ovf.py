"""
Generate centered Hopfion OVF files by rolling z-axis.

Takes equilibrated Hopfion states from anisotropy_sweep_large/
and shifts them so the Hopfion center is at z=25nm (grid center).
"""
import discretisedfield as df
import numpy as np
import os

BASE = "/mnt/d/Research/Hopfion/20260105_frustrated_fm"
OUT_DIR = os.path.join(BASE, "centered_stability_test")

# Source OVFs and their measured Hopfion z-center (nm)
sources = {
    "Ku0":  (os.path.join(BASE, "anisotropy_sweep_large/R8r4_Ku0.out/m000020.ovf"),  35.0),
    "Ku10k": (os.path.join(BASE, "anisotropy_sweep_large/R8r4_Ku10k.out/m000020.ovf"), 41.3),
    "Ku50k": (os.path.join(BASE, "anisotropy_sweep_large/R8r4_Ku50k.out/m000020.ovf"), 42.9),
}

CELL_SIZE = 0.5  # nm
TARGET_Z = 25.0  # nm (grid center for 100-cell box)

for name, (ovf_path, current_z) in sources.items():
    print(f"\n=== {name} ===")
    field = df.Field.from_file(ovf_path)
    m = field.array  # (100, 100, 100, 3)

    # Calculate roll amount (in cells)
    shift_nm = TARGET_Z - current_z
    shift_cells = int(round(shift_nm / CELL_SIZE))
    print(f"  Current z = {current_z} nm, shift = {shift_nm:.1f} nm = {shift_cells} cells")

    # Roll along z-axis (axis=2)
    m_centered = np.roll(m, shift_cells, axis=2)

    # Verify new center
    mz = m_centered[:,:,:,2]
    z_coords = np.arange(100) * CELL_SIZE
    x_coords = np.arange(100) * CELL_SIZE
    X, Y, Z = np.meshgrid(x_coords, x_coords, z_coords, indexing='ij')
    weight = np.maximum(1.0 - mz, 0)
    w_sum = weight.sum()
    new_cz = np.sum(Z * weight) / w_sum
    print(f"  New center z = {new_cz:.2f} nm")
    print(f"  mz_min = {mz.min():.4f}, mz<0 cells = {np.sum(mz < 0)}")

    # Save centered OVF
    field_new = df.Field(field.mesh, nvdim=3, value=m_centered)
    out_path = os.path.join(OUT_DIR, f"centered_{name}.ovf")
    field_new.to_file(out_path)
    print(f"  Saved: {out_path}")

print("\nDone.")
