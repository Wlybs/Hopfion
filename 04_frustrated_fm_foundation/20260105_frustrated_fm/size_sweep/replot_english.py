"""Replot size convergence with English labels for thesis.
Reuses compute_Rr from the original analyze_size_sweep.py."""
import os, sys, numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.optimize import least_squares
from skimage import measure
import discretisedfield as df

BASE = os.path.dirname(os.path.abspath(__file__))
REF_R, REF_r = 2.60, 2.16
CORE_THRESHOLD = 0.05
BAD_FIT_NM = 3.0

def _circle_residuals(params, pts):
    xc, yc, R = params
    return np.sqrt((pts[:, 0] - xc)**2 + (pts[:, 1] - yc)**2) - R

def _pbc_unwrap_xy(xy, box_L):
    centroid = np.mean(xy, axis=0)
    delta = xy - centroid
    delta -= box_L * np.round(delta / box_L)
    return centroid + delta

def compute_Rr(field):
    mz   = field.array[..., 2]
    cell = np.array(field.mesh.cell)
    pmin = np.array(field.mesh.region.pmin)
    box_L = np.array(field.mesh.region.pmax) - pmin
    mz_min = float(np.min(mz))
    core_mask = mz < (mz_min + CORE_THRESHOLD)
    if not np.any(core_mask):
        return None, None
    idx    = np.array(np.where(core_mask)).T
    coords = pmin + idx * cell
    xy     = coords[:, :2]
    if len(xy) < 4:
        return None, None
    xy_uw = _pbc_unwrap_xy(xy, box_L[:2])
    cg    = np.mean(xy_uw, axis=0)
    rg    = np.mean(np.linalg.norm(xy_uw - cg, axis=1))
    try:
        res = least_squares(_circle_residuals, [cg[0], cg[1], rg],
                            args=(xy_uw,), method='lm')
        xc, yc, R_fit = res.x
    except Exception:
        return None, None
    R_nm = abs(R_fit) * 1e9
    try:
        verts, _, _, _ = measure.marching_cubes(mz, level=0, spacing=tuple(cell))
        verts += pmin
    except (ValueError, RuntimeError):
        return R_nm, None
    if len(verts) == 0:
        return R_nm, None
    xy_v  = verts[:, :2]
    xy_v_uw = _pbc_unwrap_xy(xy_v, box_L[:2])
    rho   = np.sqrt((xy_v_uw[:,0]-xc)**2 + (xy_v_uw[:,1]-yc)**2)
    z_v   = verts[:, 2]
    dist  = np.sqrt((rho - abs(R_fit))**2 + (z_v - np.mean(coords[:,2]))**2)
    r_nm  = float(np.median(dist)) * 1e9
    return R_nm, r_nm

def extract_series(out_dir, dt=0.05):
    """dt: autosave interval in ns (0.05 for 50ps, 0.1 for 100ps)."""
    ovf_files = sorted([f for f in os.listdir(out_dir) if f.endswith('.ovf') and f.startswith('m')])
    results = []
    for ovf in ovf_files:
        idx = int(ovf.replace('m','').replace('.ovf',''))
        t_ns = idx * dt
        path = os.path.join(out_dir, ovf)
        field = df.Field.from_file(path)
        R, r = compute_Rr(field)
        results.append((t_ns, R, r))
        r_str = f"{r:.2f}" if r else "N/A"
        R_str = f"{R:.2f}" if R else "N/A"
        sys.stdout.write(f"\r  {ovf}: R={R_str}, r={r_str}    ")
    print()
    return results

# Paths
SMALL_DIR = "/mnt/d/Research/Hopfion/04_frustrated_fm_foundation/20260105_frustrated_fm/anisotropy_study/size_vs_ku/Ku1_0.0e+00_Ms_1.5000e+05.out"

# Extract data
print("Processing R3 (small, Ku=0, 3ns)...")
r3_data  = extract_series(SMALL_DIR, dt=0.1)   # autosave=100ps

print("Processing R8r4 (Ku=0, 1ns)...")
r8_data  = extract_series(os.path.join(BASE, "R8r4_Ku0.out"), dt=0.05)

print("Processing R12r5 (Ku=0, merged 4.95ns)...")
r12_data = extract_series(os.path.join(BASE, "R12r5_Ku0.out"), dt=0.05)

# Plot with English labels
fig, axes = plt.subplots(1, 2, figsize=(13, 5))
datasets = [
    (r3_data,  "Small (init R≈3.1 nm)",    "#2ca02c"),
    (r8_data,  "R8r4  (init R=8 nm)",      "#1f77b4"),
    (r12_data, "R12r5 (init R=12 nm)",     "#ff7f0e"),
]

for data, label, color in datasets:
    ts = [d[0] for d in data]
    Rs = [d[1] for d in data]
    rs = [d[2] for d in data]
    ts_R = [t for t, R in zip(ts, Rs) if R is not None]
    Rs_v = [R for R in Rs if R is not None]
    ts_r = [t for t, r in zip(ts, rs) if r is not None]
    rs_v = [r for r in rs if r is not None]
    if ts_R:
        axes[0].plot(ts_R, Rs_v, 'o-', color=color, label=label, markersize=5)
    if ts_r:
        axes[1].plot(ts_r, rs_v, 's-', color=color, label=label, markersize=5)

for ax, ref, ylabel, title in zip(
    axes, [REF_R, REF_r], ["R (nm)", "r (nm)"],
    ["Major radius R(t)", "Tube radius r(t)"]
):
    ax.axhline(ref, color='k', linestyle='--', linewidth=1.2,
               label=f"Attractor {ref:.2f} nm")
    ax.set_xlabel("Time (ns)")
    ax.set_ylabel(ylabel)
    ax.set_title(title, fontsize=13)
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)

plt.suptitle("Frustrated FM Hopfion — Size Convergence", fontsize=14)
plt.tight_layout()
out_png = os.path.join(BASE, "size_convergence_english.png")
plt.savefig(out_png, dpi=200)
plt.close()
print(f"Saved: {out_png}")
