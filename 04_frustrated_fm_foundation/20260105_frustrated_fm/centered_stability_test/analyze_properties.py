"""
analyze_properties.py
Supplement property plots for centered_stability_test.

Existing plots (hopfion_z_drift.png etc.) only show position and core count.
This script adds:
  fig_energy_evolution.png   : Total energy E(t) for 3 Ku conditions
  fig_Rr_evolution.png       : Major radius R(t) and tube radius r(t)
  fig_magnetization.png      : <mz>(t) from table.txt

Data: stability_Ku{0,10k,50k}.out/, each 21 OVFs (50ps, 0~1ns), table 1001 rows
"""

import os
import glob
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.optimize import least_squares
from skimage import measure
import discretisedfield as df

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "stability_results")
os.makedirs(RESULTS, exist_ok=True)

RUNS = [
    {"label": "Ku=0",   "dir": "stability_Ku0.out",   "color": "#1E88E5"},
    {"label": "Ku=10k", "dir": "stability_Ku10k.out", "color": "#43A047"},
    {"label": "Ku=50k", "dir": "stability_Ku50k.out", "color": "#E53935"},
]

CORE_THRESHOLD = 0.05
DT_OVF = 5e-11   # 50ps autosave


# ── R/r computation (reused from anisotropy sweep) ───────────────

def _circle_residuals(params, pts):
    xc, yc, R = params
    return np.sqrt((pts[:, 0] - xc)**2 + (pts[:, 1] - yc)**2) - R


def _pbc_unwrap_xy(xy, box_L):
    centroid = np.mean(xy, axis=0)
    delta = xy - centroid
    delta -= box_L * np.round(delta / box_L)
    return centroid + delta


def compute_Rr(field):
    """Return (R_nm, r_nm) or (None, None)."""
    mz = field.array[..., 2]
    cell = np.array(field.mesh.cell)
    pmin = np.array(field.mesh.region.pmin)
    box_L = np.array(field.mesh.region.pmax) - pmin

    core_mask = mz < (np.min(mz) + CORE_THRESHOLD)
    if not np.any(core_mask):
        return None, None

    idx = np.array(np.where(core_mask)).T
    coords = pmin + idx * cell
    xy = coords[:, :2]
    if len(xy) < 4:
        return None, None

    xy_uw = _pbc_unwrap_xy(xy, box_L[:2])
    cg = np.mean(xy_uw, axis=0)
    rg = np.mean(np.linalg.norm(xy_uw - cg, axis=1))

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

    core_z = float(np.mean(coords[:, 2]))
    dist_xy = np.sqrt((verts[:, 0] - xc)**2 + (verts[:, 1] - yc)**2)
    dist_ring = np.sqrt((dist_xy - abs(R_fit))**2 + (verts[:, 2] - core_z)**2)
    r_nm = float(np.mean(dist_ring)) * 1e9

    return R_nm, r_nm


# ── Table loading ────────────────────────────────────────────────

def load_table(out_dir):
    """Return (t_ns, mz_avg, E_total)."""
    path = os.path.join(out_dir, "table.txt")
    ts, mzs, Es = [], [], []
    with open(path) as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            cols = line.split()
            try:
                ts.append(float(cols[0]) * 1e9)
                mzs.append(float(cols[3]))
                Es.append(float(cols[4]))
            except (ValueError, IndexError):
                continue
    return np.array(ts), np.array(mzs), np.array(Es)


def main():
    print("=" * 60)
    print("  Centered Stability: Property Analysis")
    print("=" * 60)

    all_Rr = {}
    all_table = {}

    for run in RUNS:
        label = run["label"]
        out_dir = os.path.join(HERE, run["dir"])
        print(f"\n>>> {label}")

        # Load table data
        t_tbl, mz_tbl, E_tbl = load_table(out_dir)
        all_table[label] = {"t": t_tbl, "mz": mz_tbl, "E": E_tbl, **run}
        print(f"  table: {len(t_tbl)} rows, t={t_tbl[0]:.2f}~{t_tbl[-1]:.2f} ns")

        # Compute R/r from OVFs
        ovfs = sorted(glob.glob(os.path.join(out_dir, "m*.ovf")))
        ts_ovf, Rs, rs = [], [], []
        for i, fpath in enumerate(ovfs):
            t_ns = i * DT_OVF * 1e9
            field = df.Field.from_file(fpath)
            R, r = compute_Rr(field)
            del field
            ts_ovf.append(t_ns)
            Rs.append(R)
            rs.append(r)
            if i % 5 == 0:
                R_s = f"{R:.2f}" if R else "N/A"
                r_s = f"{r:.2f}" if r else "N/A"
                print(f"  frame {i:02d} t={t_ns:.2f}ns  R={R_s}nm  r={r_s}nm")

        all_Rr[label] = {"t": np.array(ts_ovf), "R": Rs, "r": rs, **run}

    # ── Fig 1: Energy evolution ──────────────────────────────────
    fig, ax = plt.subplots(figsize=(8, 5))
    for label, d in all_table.items():
        # Normalize to initial energy for easier comparison
        E_norm = (d["E"] - d["E"][0]) / abs(d["E"][0]) * 100  # percent change
        ax.plot(d["t"], E_norm, "-", color=d["color"], linewidth=1.2,
                label=label, alpha=0.85)

    ax.set_xlabel("Time (ns)", fontsize=12)
    ax.set_ylabel("$\\Delta E / E_0$ (%)", fontsize=12)
    ax.set_title("Total Energy Evolution (Centered Hopfion, 1ns)", fontsize=13)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    out1 = os.path.join(RESULTS, "fig_energy_evolution.png")
    plt.savefig(out1, dpi=200)
    plt.close()
    print(f"\n[fig] {out1}")

    # ── Fig 2: R(t) and r(t) ────────────────────────────────────
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))

    for label, d in all_Rr.items():
        ts = d["t"]
        Rs_valid = [(t, R) for t, R in zip(ts, d["R"]) if R is not None]
        rs_valid = [(t, r) for t, r in zip(ts, d["r"]) if r is not None]

        if Rs_valid:
            t_R, R_v = zip(*Rs_valid)
            ax1.plot(t_R, R_v, "o-", color=d["color"], label=label,
                     markersize=5, linewidth=1.5)
        if rs_valid:
            t_r, r_v = zip(*rs_valid)
            ax2.plot(t_r, r_v, "s-", color=d["color"], label=label,
                     markersize=5, linewidth=1.5)

    for ax, ylabel, title in zip(
        [ax1, ax2], ["R (nm)", "r (nm)"],
        ["Major Radius R(t)", "Tube Radius r(t)"]
    ):
        ax.set_xlabel("Time (ns)", fontsize=12)
        ax.set_ylabel(ylabel, fontsize=12)
        ax.set_title(title, fontsize=13)
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3)

    fig.suptitle("Hopfion Geometry: Centered Stability Test (1ns)",
                 fontsize=14, y=1.02)
    plt.tight_layout()
    out2 = os.path.join(RESULTS, "fig_Rr_evolution.png")
    plt.savefig(out2, dpi=200, bbox_inches="tight")
    plt.close()
    print(f"[fig] {out2}")

    # ── Fig 3: Average magnetization ─────────────────────────────
    fig, ax = plt.subplots(figsize=(8, 5))
    for label, d in all_table.items():
        ax.plot(d["t"], d["mz"], "-", color=d["color"], linewidth=1.2,
                label=label, alpha=0.85)

    ax.set_xlabel("Time (ns)", fontsize=12)
    ax.set_ylabel("$\\langle m_z \\rangle$", fontsize=12)
    ax.set_title("Average Magnetization $\\langle m_z \\rangle$ (Centered Hopfion, 1ns)",
                 fontsize=13)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    out3 = os.path.join(RESULTS, "fig_magnetization.png")
    plt.savefig(out3, dpi=200)
    plt.close()
    print(f"[fig] {out3}")

    # ── Print summary ────────────────────────────────────────────
    print("\n" + "=" * 70)
    print(f"{'Ku':<8} {'R_0':>6} {'R_end':>6} {'r_0':>6} {'r_end':>6} "
          f"{'dE/E0%':>8} {'<mz>_0':>8} {'<mz>_end':>8}")
    print("-" * 70)
    for label in [r["label"] for r in RUNS]:
        Rr = all_Rr[label]
        tbl = all_table[label]
        R0 = Rr["R"][0]
        Re = Rr["R"][-1]
        r0 = Rr["r"][0]
        re = Rr["r"][-1]
        dE = (tbl["E"][-1] - tbl["E"][0]) / abs(tbl["E"][0]) * 100
        mz0 = tbl["mz"][0]
        mze = tbl["mz"][-1]
        print(f"{label:<8} {R0:>6.2f} {Re:>6.2f} {r0:>6.2f} {re:>6.2f} "
              f"{dE:>+7.3f}% {mz0:>8.5f} {mze:>8.5f}")
    print("=" * 70)


if __name__ == "__main__":
    main()
