"""
analyze_leaky_drift.py — Phase 1: Gradient Ku Restoring Force Verification
===========================================================================
Analyzes whether a gradient Ku profile creates a restoring (leaky-integrator)
force on a Hopfion after spin-wave drive is released.

Compares two experiments:
  1. Gradient Ku  : Hopfion driven to +z by spin wave, then released.
                    Expected: drifts back toward z=0 (restoring force).
  2. Uniform Ku   : Same drive sequence, then released (control).
                    Expected: stays displaced (no restoring force).

Usage
-----
# Default: compare gradient vs uniform
source /mnt/d/Research/Hopfion/hopfion/bin/activate
python analyze_leaky_drift.py

# With gradient strength sweep (--sweep flag)
python analyze_leaky_drift.py --sweep

Output files (all in analysis/ directory)
------------------------------------------
  leaky_drift_comparison.png     — full trajectory + release-phase comparison
  leaky_drift_summary.txt        — pass/fail verdict + numeric results
  gradient_sweep_scaling.png     — |drift| vs dKu (with --sweep only)
"""

import os
import sys
import argparse
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit

# ── Shared library ────────────────────────────────────────────────────────────
sys.path.insert(0, "/mnt/d/Research/Hopfion/scripts")
from hopfion_analysis import extract_trajectory, core_count
import discretisedfield as df

# ── Configuration constants ───────────────────────────────────────────────────
_BASE = "/mnt/d/Research/Hopfion/lif_neuron_hopfion"

GRADIENT_OUT = os.path.join(
    _BASE,
    "gradient_ku_verification/drive_release_test/with_gradient",
    "gradient_ku_drive_release.out",
)
UNIFORM_OUT = os.path.join(
    _BASE,
    "gradient_ku_verification/drive_release_test/uniform_control",
    "uniform_ku_drive_release.out",
)
OUTPUT_DIR = os.path.join(_BASE, "gradient_ku_verification/analysis")

DT_NS = 0.005        # 5 ps autosave interval
DRIVE_END_NS = 0.30  # Phase A (drive) ends at 0.30 ns
SURVIVAL_THRESHOLD = 100  # mz<0 cell count below this → collapsed


# ── Helper: load last OVF in a .out directory ─────────────────────────────────

def _last_ovf(out_dir):
    """Return path to the last m*.ovf frame in out_dir."""
    files = sorted(
        f for f in os.listdir(out_dir)
        if f.startswith("m") and f.endswith(".ovf")
    )
    if not files:
        raise FileNotFoundError(f"No OVF files found in: {out_dir}")
    return os.path.join(out_dir, files[-1])


# ── 1. Survival check ─────────────────────────────────────────────────────────

def check_hopfion_survival(out_dir):
    """
    Load last OVF frame from out_dir and return core_count (mz<0 cells).

    Returns
    -------
    int
        Core count. Values < SURVIVAL_THRESHOLD indicate Hopfion has collapsed.
    """
    path = _last_ovf(out_dir)
    field = df.Field.from_file(path)
    cc = core_count(field)
    del field
    return cc


# ── 2. Z-trajectory extraction ───────────────────────────────────────────────

def extract_z_trajectory(out_dir):
    """
    Extract the z-coordinate time series from a .out directory.

    Uses extract_trajectory() from hopfion_analysis, filters out frames where
    the centroid is None (collapsed), and returns parallel numpy arrays.

    Parameters
    ----------
    out_dir : str

    Returns
    -------
    times : np.ndarray, shape (N,)   — time in ns
    z_vals : np.ndarray, shape (N,)  — z centroid in nm
    """
    traj = extract_trajectory(out_dir, DT_NS, verbose=True)
    times, z_vals = [], []
    for t_ns, centroid in traj:
        if centroid is not None:
            times.append(t_ns)
            z_vals.append(centroid[2])
    return np.array(times), np.array(z_vals)


# ── 3. Release-phase analysis ─────────────────────────────────────────────────

def _exp_decay(t_rel, z0, dz, tau):
    """Exponential model: z(t) = z0 + dz * exp(-t/tau)."""
    return z0 + dz * np.exp(-t_rel / tau)


def analyze_release_phase(times, z_vals, label):
    """
    Analyze Hopfion z-displacement after spin-wave drive is released.

    Filters to t >= DRIVE_END_NS, fits z(t) = z0 + dz*exp(-t/tau),
    and reports the net drift over the release window.

    Parameters
    ----------
    times  : np.ndarray — full time array (ns)
    z_vals : np.ndarray — full z-centroid array (nm)
    label  : str        — identifier for print/plot labels

    Returns
    -------
    dict with keys:
        label         : str
        z_at_release  : float (nm)  — z value at moment of release
        z_at_end      : float (nm)  — z value at final frame
        drift_nm      : float (nm)  — z_at_end - z_at_release (negative = restoring)
        tau_leak_ns   : float (ns)  — exponential decay time constant (None if fit fails)
        t_rel         : np.ndarray  — release-phase time shifted to 0 (ns)
        z_rel         : np.ndarray  — release-phase z values (nm)
    """
    mask = times >= DRIVE_END_NS
    if not np.any(mask):
        raise ValueError(f"[{label}] No frames found at t >= {DRIVE_END_NS} ns")

    t_rel = times[mask] - DRIVE_END_NS
    z_rel = z_vals[mask]

    z_at_release = float(z_rel[0])
    z_at_end = float(z_rel[-1])
    drift_nm = z_at_end - z_at_release

    # Exponential fit: z(t) = z0 + dz * exp(-t/tau)
    tau_leak_ns = None
    try:
        dz0 = z_at_end - z_at_release
        tau0 = max(t_rel[-1] / 3.0, 0.01)
        p0 = [z_at_release, dz0, tau0]
        popt, _ = curve_fit(
            _exp_decay, t_rel, z_rel,
            p0=p0,
            bounds=([-np.inf, -np.inf, 1e-4], [np.inf, np.inf, 100.0]),
            maxfev=5000,
        )
        tau_leak_ns = float(popt[2])
    except (RuntimeError, ValueError) as exc:
        print(f"  [{label}] Exponential fit failed: {exc}")

    return {
        "label": label,
        "z_at_release": z_at_release,
        "z_at_end": z_at_end,
        "drift_nm": drift_nm,
        "tau_leak_ns": tau_leak_ns,
        "t_rel": t_rel,
        "z_rel": z_rel,
    }


# ── 4. Plot ───────────────────────────────────────────────────────────────────

def plot_comparison(grad_data, uni_data, output_path):
    """
    Two-panel figure comparing gradient and uniform Ku experiments.

    Left panel  : Full z(t) trajectory for both cases, vertical line at DRIVE_END_NS.
    Right panel : Release-phase only (t >= DRIVE_END_NS), with drift values in legend.

    Parameters
    ----------
    grad_data : dict from analyze_release_phase()
    uni_data  : dict from analyze_release_phase()
    output_path : str — path to save PNG
    """
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Reconstruct full time arrays from stored release-phase arrays
    # (we need to pull full arrays from outside; pass them in as extras)
    t_full_g = grad_data.get("t_full")
    z_full_g = grad_data.get("z_full")
    t_full_u = uni_data.get("t_full")
    z_full_u = uni_data.get("z_full")

    # ── Left: full trajectory ──
    ax = axes[0]
    if t_full_g is not None:
        ax.plot(t_full_g, z_full_g, color="tab:blue", lw=1.5,
                label="Gradient Ku")
    if t_full_u is not None:
        ax.plot(t_full_u, z_full_u, color="tab:orange", lw=1.5,
                label="Uniform Ku (control)")
    ax.axvline(DRIVE_END_NS, color="gray", ls="--", lw=1.2,
               label=f"Drive end ({DRIVE_END_NS} ns)")
    ax.set_xlabel("Time (ns)")
    ax.set_ylabel("Hopfion z-centroid (nm)")
    ax.set_title("Full trajectory")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)

    # ── Right: release phase only ──
    ax = axes[1]
    gd = grad_data
    ud = uni_data

    grad_lbl = (f"Gradient Ku  drift={gd['drift_nm']:+.2f} nm"
                + (f"  τ={gd['tau_leak_ns']:.3f} ns"
                   if gd["tau_leak_ns"] is not None else ""))
    uni_lbl = (f"Uniform Ku   drift={ud['drift_nm']:+.2f} nm"
               + (f"  τ={ud['tau_leak_ns']:.3f} ns"
                  if ud["tau_leak_ns"] is not None else ""))

    ax.plot(gd["t_rel"] + DRIVE_END_NS, gd["z_rel"],
            color="tab:blue", lw=1.5, label=grad_lbl)
    ax.plot(ud["t_rel"] + DRIVE_END_NS, ud["z_rel"],
            color="tab:orange", lw=1.5, label=uni_lbl)

    # Overlay exponential fits
    for data, color in [(gd, "tab:blue"), (ud, "tab:orange")]:
        if data["tau_leak_ns"] is not None:
            t_fit = np.linspace(data["t_rel"][0], data["t_rel"][-1], 300)
            z_fit = _exp_decay(
                t_fit,
                data["z_at_release"],
                data["z_at_end"] - data["z_at_release"],
                data["tau_leak_ns"],
            )
            ax.plot(t_fit + DRIVE_END_NS, z_fit,
                    color=color, ls="--", lw=1.0, alpha=0.7)

    ax.axvline(DRIVE_END_NS, color="gray", ls="--", lw=1.2)
    ax.set_xlabel("Time (ns)")
    ax.set_ylabel("Hopfion z-centroid (nm)")
    ax.set_title("Release phase (t ≥ DRIVE_END_NS)")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    fig.suptitle("Gradient Ku Restoring Force — Phase 1 Verification", fontsize=12)
    fig.tight_layout()
    fig.savefig(output_path, dpi=200)
    plt.close(fig)
    print(f"  Saved: {output_path}")


# ── 5. Main ───────────────────────────────────────────────────────────────────

def main():
    """
    Compare gradient-Ku vs uniform-Ku drive-release experiments.
    Prints a results table and writes summary + comparison plot.
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("=" * 60)
    print("Phase 1: Gradient Ku Restoring Force Verification")
    print("=" * 60)

    # ── Survival check ──
    print("\n[1] Checking Hopfion survival...")
    for label, out_dir in [("Gradient Ku", GRADIENT_OUT),
                            ("Uniform Ku",  UNIFORM_OUT)]:
        cc = check_hopfion_survival(out_dir)
        status = "ALIVE" if cc >= SURVIVAL_THRESHOLD else "COLLAPSED"
        print(f"  {label}: core_count={cc}  → {status}")
        if cc < SURVIVAL_THRESHOLD:
            print(f"  WARNING: Hopfion collapsed in {label} simulation. "
                  "Results may be unreliable.")

    # ── Extract trajectories ──
    print("\n[2] Extracting z-trajectories...")
    print(f"  Gradient Ku ({GRADIENT_OUT}):")
    t_g, z_g = extract_z_trajectory(GRADIENT_OUT)
    print(f"  Uniform Ku ({UNIFORM_OUT}):")
    t_u, z_u = extract_z_trajectory(UNIFORM_OUT)

    # ── Analyze release phase ──
    print("\n[3] Analyzing release phase (t >= {:.3f} ns)...".format(DRIVE_END_NS))
    grad_data = analyze_release_phase(t_g, z_g, "Gradient Ku")
    uni_data  = analyze_release_phase(t_u, z_u, "Uniform Ku")

    # Attach full arrays for plotting
    grad_data["t_full"] = t_g
    grad_data["z_full"] = z_g
    uni_data["t_full"]  = t_u
    uni_data["z_full"]  = z_u

    # ── Print results table ──
    print("\n[4] Results")
    print("-" * 58)
    header = f"  {'Metric':<30} {'Gradient Ku':>12} {'Uniform Ku':>12}"
    print(header)
    print("-" * 58)

    rows = [
        ("z at release (nm)",    "z_at_release"),
        ("z at end (nm)",        "z_at_end"),
        ("net drift (nm)",       "drift_nm"),
        ("τ_leak (ns)",          "tau_leak_ns"),
    ]
    for name, key in rows:
        gv = grad_data[key]
        uv = uni_data[key]
        g_str = f"{gv:.4f}" if gv is not None else "  fit fail"
        u_str = f"{uv:.4f}" if uv is not None else "  fit fail"
        print(f"  {name:<30} {g_str:>12} {u_str:>12}")
    print("-" * 58)

    # ── Pass/fail verdict ──
    print("\n[5] Verdict")
    g_drift = grad_data["drift_nm"]
    u_drift = uni_data["drift_nm"]
    crit_restoring = g_drift < -2.0
    crit_contrast  = abs(g_drift) - abs(u_drift) > 1.0

    print(f"  Criterion 1 — gradient drift < -2 nm        : "
          f"{'PASS' if crit_restoring else 'FAIL'}  "
          f"(gradient drift = {g_drift:+.3f} nm)")
    print(f"  Criterion 2 — |grad_drift| - |uni_drift| > 1 nm: "
          f"{'PASS' if crit_contrast else 'FAIL'}  "
          f"(diff = {abs(g_drift) - abs(u_drift):+.3f} nm)")

    verdict = "PASS" if (crit_restoring and crit_contrast) else "FAIL"
    print(f"\n  OVERALL: {verdict}")
    if verdict == "PASS":
        print("  Gradient Ku generates a measurable restoring force. "
              "Ready for Phase 2.")
    else:
        print("  Restoring force NOT confirmed. Check gradient strength "
              "or drive amplitude.")

    # ── Plot ──
    print("\n[6] Generating comparison plot...")
    plot_path = os.path.join(OUTPUT_DIR, "leaky_drift_comparison.png")
    plot_comparison(grad_data, uni_data, plot_path)

    # ── Summary text ──
    summary_path = os.path.join(OUTPUT_DIR, "leaky_drift_summary.txt")
    with open(summary_path, "w") as f:
        f.write("Gradient Ku Restoring Force — Phase 1 Summary\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"DRIVE_END_NS : {DRIVE_END_NS} ns\n")
        f.write(f"DT_NS        : {DT_NS} ns\n\n")
        for data in [grad_data, uni_data]:
            f.write(f"[{data['label']}]\n")
            f.write(f"  z_at_release : {data['z_at_release']:.4f} nm\n")
            f.write(f"  z_at_end     : {data['z_at_end']:.4f} nm\n")
            f.write(f"  drift_nm     : {data['drift_nm']:.4f} nm\n")
            tau_str = (f"{data['tau_leak_ns']:.4f} ns"
                       if data["tau_leak_ns"] is not None else "fit failed")
            f.write(f"  tau_leak_ns  : {tau_str}\n\n")
        f.write(f"Criterion 1 (gradient drift < -2 nm)           : "
                f"{'PASS' if crit_restoring else 'FAIL'}\n")
        f.write(f"Criterion 2 (|grad|-|uni| contrast > 1 nm)     : "
                f"{'PASS' if crit_contrast else 'FAIL'}\n")
        f.write(f"\nOVERALL VERDICT: {verdict}\n")
    print(f"  Saved: {summary_path}")
    print("\nDone.")


# ── 6. Gradient sweep (V3, --sweep flag) ─────────────────────────────────────

def analyze_gradient_sweep():
    """
    Loop over dKu values [200, 500, 1000] A/m and analyze drift scaling.

    Each experiment is expected at:
        .../gradient_strength_sweep/dKu_{value}/gradient_ku_dKu{value}.out

    Plots |drift| vs dKu to identify the weakest working gradient for Phase 2.
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    DKU_VALUES = [200, 500, 1000]
    sweep_base = os.path.join(
        _BASE, "gradient_ku_verification/gradient_strength_sweep"
    )

    results = []
    print("=" * 60)
    print("Gradient Strength Sweep Analysis")
    print("=" * 60)

    for dku in DKU_VALUES:
        out_dir = os.path.join(
            sweep_base,
            f"dKu_{dku}",
            f"gradient_ku_dKu{dku}.out",
        )
        print(f"\ndKu = {dku} A/m  →  {out_dir}")

        if not os.path.isdir(out_dir):
            print(f"  SKIPPED: directory not found")
            results.append({"dku": dku, "drift_nm": None,
                             "tau_ns": None, "survived": False})
            continue

        cc = check_hopfion_survival(out_dir)
        survived = cc >= SURVIVAL_THRESHOLD
        print(f"  core_count={cc}  → {'ALIVE' if survived else 'COLLAPSED'}")

        if not survived:
            results.append({"dku": dku, "drift_nm": None,
                             "tau_ns": None, "survived": False})
            continue

        t, z = extract_z_trajectory(out_dir)
        data = analyze_release_phase(t, z, f"dKu={dku}")
        print(f"  drift={data['drift_nm']:+.3f} nm  "
              f"tau={data['tau_leak_ns']}")
        results.append({
            "dku": dku,
            "drift_nm": data["drift_nm"],
            "tau_ns": data["tau_leak_ns"],
            "survived": True,
        })

    # ── Scaling plot ──
    valid = [r for r in results if r["survived"] and r["drift_nm"] is not None]
    if len(valid) < 2:
        print("\nInsufficient data for scaling plot (need >= 2 surviving sims).")
    else:
        dku_arr  = np.array([r["dku"]            for r in valid])
        drift_arr = np.abs([r["drift_nm"]         for r in valid])

        fig, ax = plt.subplots(figsize=(7, 5))
        ax.plot(dku_arr, drift_arr, "o-", color="tab:blue", lw=1.5, ms=7)
        ax.axhline(2.0, color="gray", ls="--", lw=1.0, label="2 nm threshold")
        ax.set_xlabel("dKu gradient strength (A/m)")
        ax.set_ylabel("|Drift after release| (nm)")
        ax.set_title("Gradient Ku Strength Scaling")
        ax.legend(fontsize=9)
        ax.grid(True, alpha=0.3)

        sweep_plot = os.path.join(OUTPUT_DIR, "gradient_sweep_scaling.png")
        fig.tight_layout()
        fig.savefig(sweep_plot, dpi=200)
        plt.close(fig)
        print(f"\n  Saved: {sweep_plot}")

    # ── Recommendation ──
    print("\n[Recommendation]")
    working = [r for r in results
               if r["survived"] and r["drift_nm"] is not None
               and abs(r["drift_nm"]) > 2.0]
    if working:
        weakest = min(working, key=lambda r: r["dku"])
        print(f"  Weakest working gradient: dKu = {weakest['dku']} A/m  "
              f"(|drift| = {abs(weakest['drift_nm']):.3f} nm > 2 nm)")
        print(f"  → Use dKu = {weakest['dku']} A/m for Phase 2.")
    else:
        print("  No gradient value produced drift > 2 nm.")
        print("  → Increase dKu range or check drive amplitude.")
    print("\nDone.")


# ── CLI dispatch ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Phase 1: Gradient Ku restoring-force analysis."
    )
    parser.add_argument(
        "--sweep",
        action="store_true",
        help="Run gradient strength sweep (V3) instead of single comparison.",
    )
    args = parser.parse_args()

    if args.sweep:
        analyze_gradient_sweep()
    else:
        main()
