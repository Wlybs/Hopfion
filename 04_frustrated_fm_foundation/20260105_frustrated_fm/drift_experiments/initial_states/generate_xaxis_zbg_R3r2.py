"""
Generate hopfion_xaxis_zbg_R3_r2.ovf

Takes the standard axis=z, bg=mz Hopfion (hopfion_z_R3_r2.ovf) and
transposes spatial axes x<->z, keeping magnetization vectors unchanged.

Result: Hopfion ring in YZ plane (axis=x), background mz=+1.
Grid 100^3, 0.5nm cell, PBC-compatible.
"""
import os
import numpy as np
import discretisedfield as df

HERE = os.path.dirname(os.path.abspath(__file__))
src = os.path.join(HERE, "hopfion_z_R3_r2.ovf")
dst = os.path.join(HERE, "hopfion_xaxis_zbg_R3_r2.ovf")

print(f"Loading {src}")
field = df.Field.from_file(src)
m = field.array  # shape (100, 100, 100, 3)

print(f"  Original shape: {m.shape}")
print(f"  Far-field mz: {m[0,0,0,2]:.4f}")
print(f"  mz min: {m[:,:,:,2].min():.4f}")

# Swap spatial axes x <-> z (axis 0 <-> axis 2)
# Magnetization vectors (mx, my, mz) are KEPT as-is
m_new = np.transpose(m, (2, 1, 0, 3)).copy()

print(f"  After transpose shape: {m_new.shape}")
print(f"  Far-field mz: {m_new[0,0,0,2]:.4f}")

# Verify: the ring should now be in YZ plane
core_mask = m_new[:,:,:,2] < (m_new[:,:,:,2].min() + 0.05)
core_idx = np.array(np.where(core_mask)).T
print(f"  Core cells: {len(core_idx)}")
if len(core_idx) > 0:
    cx = np.mean(core_idx[:, 0]) * 0.5
    cy = np.mean(core_idx[:, 1]) * 0.5
    cz = np.mean(core_idx[:, 2]) * 0.5
    print(f"  Core centroid: x={cx:.1f}nm, y={cy:.1f}nm, z={cz:.1f}nm")
    # Check spread in each axis
    sx = (core_idx[:, 0].max() - core_idx[:, 0].min()) * 0.5
    sy = (core_idx[:, 1].max() - core_idx[:, 1].min()) * 0.5
    sz = (core_idx[:, 2].max() - core_idx[:, 2].min()) * 0.5
    print(f"  Core spread: dx={sx:.1f}nm, dy={sy:.1f}nm, dz={sz:.1f}nm")
    print(f"  (Ring should be spread in YZ, compact in X)")

field_new = df.Field(field.mesh, nvdim=3, value=m_new)
field_new.to_file(dst)
print(f"\nSaved: {dst}")
