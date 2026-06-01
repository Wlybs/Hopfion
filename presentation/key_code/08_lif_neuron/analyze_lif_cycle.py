"""
analyze_lif_cycle.py — Phase 2: LIF Neuron Cycle Analysis
=========================================================
Plots Hopfion z-displacement as the LIF membrane potential and overlays
the pulse train envelope to visualize integrate → leak → fire+reset →
refractory dynamics.

Inputs
------
F1 (supra-threshold, B=1T) : lif_cycle_demo/pulse_train_integrate/lif_pulse_train.out
F3 (sub-threshold, B=0.1T) : lif_cycle_demo/threshold_comparison/subthreshold_B0p1T.out

Usage
-----
source /mnt/d/Research/Hopfion/hopfion/bin/activate
python analyze_lif_cycle.py              # F1 only
python analyze_lif_cycle.py --compare    # F1 vs F3 threshold comparison

Outputs (lif_cycle_demo/analysis/)
-----------------------------------
lif_cycle_f1.png             — membrane potential + pulse timeline
lif_cycle_threshold.png      — F1 vs F3 supra/sub threshold (with --compare)
lif_cycle_report.txt         — per-phase statistics + verdict
"""

import os
import sys
import argparse
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, "/mnt/d/Research/Hopfion/scripts")
from hopfion_analysis import extract_trajectory, core_count
import discretisedfield as df

# ── Paths ────────────────────────────────────────────────────────────────────
_BASE = "/mnt/d/Research/Hopfion/lif_neuron_hopfion/lif_cycle_demo"

F1_OUT = os.path.join(_BASE, "pulse_train_integrate", "lif_pulse_train.out")
F3_OUT = os.path.join(_BASE, "threshold_comparison",  "subthreshold_B0p1T.out")
OUTPUT_DIR = os.path.join(_BASE, "analysis")

DT_NS = 0.005  # autosave(m, 5e-12)
SURVIVAL_THRESHOLD = 100

# ── LIF phase timeline (mx3 protocol) ────────────────────────────────────────
# (label, t_start_ns, t_end_ns, kind)   kind ∈ {integrate, leak, fire, refractory}
PHASES = [
    ("Pulse 1",    0.00, 0.15, "integrate"),
    ("Leak 1",     0.15, 0.40, "leak"),
    ("Pulse 2",    0.40, 0.55, "integrate"),
    ("Leak 2",     0.55, 0.80, "leak"),
    ("Pulse 3",    0.80, 0.95, "integrate"),
    ("Leak 3",     0.95, 1.20, "leak"),
    ("Pulse 4",    1.20, 1.35, "integrate"),
    ("Fire+Reset", 1.35, 1.85, "fire"),
    ("Refractory", 1.85, 2.15, "refractory"),
]

PHASE_COLORS = {
    "integrate":  "#ffe0b3",  # light orange — drive toward -z (integrate)
    "leak":       "#f0f0f0",  # light gray — passive leak
    "fire":       "#b3d9ff",  # light blue — drive toward +z (fire/reset)
    "refractory": "#e0e0e0",  # darker gray — OFF
}


# ── Loaders ──────────────────────────────────────────────────────────────────

def _last_ovf(out_dir):
    files = sorted(f for f in os.listdir(out_dir)
                   if f.startswith("m") and f.endswith(".ovf"))
    if not files:
        raise FileNotFoundError(f"No OVF files in {out_dir}")
    return os.path.join(out_dir, files[-1])


def check_survival(out_dir):
    path = _last_ovf(out_dir)
    field = df.Field.from_file(path)
    cc = core_count(field)
    del field
    return cc


def load_z_trajectory(out_dir):
    """Return (times_ns, z_nm) from extract_trajectory, filtering None frames."""
    traj = extract_trajectory(out_dir, DT_NS, verbose=False)
    ts, zs = [], []
    for t_ns, centroid in traj:
        if centroid is not None:
            ts.append(t_ns)
            zs.append(centroid[2])
    return np.array(ts), np.array(zs)


# ── Phase statistics ─────────────────────────────────────────────────────────

def phase_stats(t, z, phases=PHASES):
    """For each phase, compute dz (z_end - z_start)."""
    rows = []
    for label, t0, t1, kind in phases:
        mask = (t >= t0) & (t <= t1)
        if not np.any(mask):
            rows.append((label, t0, t1, kind, None, None, None))
            continue
        z_seg = z[mask]
        z_start = float(z_seg[0])
        z_end = float(z_seg[-1])
        dz = z_end - z_start
        rows.append((label, t0, t1, kind, z_start, z_end, dz))
    return rows


# ── Plotting ─────────────────────────────────────────────────────────────────

def _shade_phases(ax, phases=PHASES, ylim=None):
    if ylim is None:
        ylim = ax.get_ylim()
    for label, t0, t1, kind in phases:
        ax.axvspan(t0, t1, color=PHASE_COLORS[kind], alpha=0.55, zorder=0)
        ax.text((t0 + t1) / 2, ylim[1] - 0.05 * (ylim[1] - ylim[0]),
                label, ha="center", va="top", fontsize=7, color="#333")


def plot_lif_cycle(t, z, title, output_path, phases=PHASES):
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(t, z, color="tab:blue", lw=1.6, label="Hopfion z-centroid (membrane V)")
    ax.axhline(0, color="gray", ls=":", lw=0.8, alpha=0.6)
    ymin, ymax = float(z.min()) - 1.5, float(z.max()) + 2.0
    ax.set_ylim(ymin, ymax)
    _shade_phases(ax, phases, ylim=(ymin, ymax))
    ax.set_xlabel("Time (ns)")
    ax.set_ylabel("Hopfion z-centroid (nm)")
    ax.set_title(title)
    ax.grid(True, alpha=0.3, zorder=1)
    ax.legend(loc="lower right", fontsize=9)
    fig.tight_layout()
    fig.savefig(output_path, dpi=200)
    plt.close(fig)
    print(f"  Saved: {output_path}")


def plot_threshold_comparison(t_supra, z_supra, t_sub, z_sub,
                              output_path, phases=PHASES):
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(t_supra, z_supra, color="tab:red",  lw=1.8,
            label="Supra-threshold (B=1.0T)")
    ax.plot(t_sub,   z_sub,   color="tab:gray", lw=1.4, ls="--",
            label="Sub-threshold (B=0.1T)")
    ax.axhline(0, color="gray", ls=":", lw=0.8, alpha=0.6)
    all_z = np.concatenate([z_supra, z_sub])
    ymin, ymax = float(all_z.min()) - 1.5, float(all_z.max()) + 2.0
    ax.set_ylim(ymin, ymax)
    _shade_phases(ax, phases, ylim=(ymin, ymax))
    ax.set_xlabel("Time (ns)")
    ax.set_ylabel("Hopfion z-centroid (nm)")
    ax.set_title("LIF Threshold Comparison — Supra vs Sub")
    ax.grid(True, alpha=0.3, zorder=1)
    ax.legend(loc="lower right", fontsize=9)
    fig.tight_layout()
    fig.savefig(output_path, dpi=200)
    plt.close(fig)
    print(f"  Saved: {output_path}")


# ── Report writer ────────────────────────────────────────────────────────────

def write_report(rows_f1, rows_f3, z_f1, z_f3, output_path):
    with open(output_path, "w") as f:
        f.write("LIF Neuron Cycle — Phase 2 Report\n")
        f.write("=" * 60 + "\n\n")

        def _block(name, rows, z_arr):
            if rows is None:
                f.write(f"[{name}]  NOT AVAILABLE\n\n")
                return
            f.write(f"[{name}]\n")
            f.write(f"  z range : {float(z_arr.min()):+.3f} .. "
                    f"{float(z_arr.max()):+.3f} nm   "
                    f"(peak excursion {float(z_arr.max() - z_arr.min()):.3f} nm)\n")
            f.write(f"  {'Phase':<11} {'t0-t1 (ns)':<14} "
                    f"{'kind':<10} {'z_start':>9} {'z_end':>9} {'dz':>9}\n")
            for label, t0, t1, kind, zs, ze, dz in rows:
                if zs is None:
                    f.write(f"  {label:<11} {t0:.2f}-{t1:.2f}       "
                            f"{kind:<10} {'--':>9} {'--':>9} {'--':>9}\n")
                else:
                    f.write(f"  {label:<11} {t0:.2f}-{t1:.2f}       "
                            f"{kind:<10} {zs:+9.3f} {ze:+9.3f} {dz:+9.3f}\n")
            f.write("\n")

        _block("F1 supra-threshold (B=1.0T)", rows_f1, z_f1)
        _block("F3 sub-threshold (B=0.1T)",   rows_f3, z_f3)

        # Verdict
        if rows_f1 is not None:
            integrate_dz = sum(r[6] for r in rows_f1
                               if r[3] == "integrate" and r[6] is not None)
            fire_dz = next((r[6] for r in rows_f1 if r[3] == "fire"), None)
            f.write("Verdict (F1):\n")
            f.write(f"  Total integrate dz (sum of 4 pulses) : {integrate_dz:+.3f} nm\n")
            f.write(f"  Fire+Reset dz                        : "
                    f"{fire_dz:+.3f} nm\n" if fire_dz is not None else
                    f"  Fire+Reset dz                        : N/A\n")
            crit_integrate = integrate_dz < -2.0
            crit_fire = fire_dz is not None and fire_dz > 2.0
            f.write(f"  Criterion: sum integrate dz < -2 nm : "
                    f"{'PASS' if crit_integrate else 'FAIL'}\n")
            f.write(f"  Criterion: fire/reset dz > +2 nm     : "
                    f"{'PASS' if crit_fire else 'FAIL'}\n")
            verdict = "PASS" if crit_integrate and crit_fire else "FAIL"
            f.write(f"  OVERALL: {verdict}\n")
    print(f"  Saved: {output_path}")


# ── Main ─────────────────────────────────────────────────────────────────────

def analyze_run(out_dir, label):
    print(f"\n[{label}] {out_dir}")
    if not os.path.isdir(out_dir):
        print("  NOT AVAILABLE (directory missing)")
        return None, None, None
    cc = check_survival(out_dir)
    print(f"  survival core_count = {cc}  "
          f"→ {'ALIVE' if cc >= SURVIVAL_THRESHOLD else 'COLLAPSED'}")
    t, z = load_z_trajectory(out_dir)
    if len(t) == 0:
        print("  no valid frames")
        return None, None, None
    rows = phase_stats(t, z)
    print(f"  frames = {len(t)}  "
          f"t range = {t[0]:.3f} .. {t[-1]:.3f} ns  "
          f"z range = {z.min():+.3f} .. {z.max():+.3f} nm")
    return t, z, rows


def main():
    ap = argparse.ArgumentParser(description="Phase 2 LIF cycle analysis.")
    ap.add_argument("--compare", action="store_true",
                    help="Also analyze F3 sub-threshold run and plot comparison.")
    args = ap.parse_args()

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print("=" * 60)
    print("Phase 2: LIF Neuron Cycle Analysis")
    print("=" * 60)

    # F1
    t_f1, z_f1, rows_f1 = analyze_run(F1_OUT, "F1 supra B=1.0T")
    if t_f1 is None:
        print("\nF1 not available — aborting.")
        sys.exit(1)

    plot_lif_cycle(t_f1, z_f1,
                   "LIF Cycle (F1, B=1.0T) — Hopfion Membrane Potential",
                   os.path.join(OUTPUT_DIR, "lif_cycle_f1.png"))

    # F3
    t_f3, z_f3, rows_f3 = (None, None, None)
    if args.compare:
        t_f3, z_f3, rows_f3 = analyze_run(F3_OUT, "F3 sub  B=0.1T")
        if t_f3 is not None:
            plot_threshold_comparison(
                t_f1, z_f1, t_f3, z_f3,
                os.path.join(OUTPUT_DIR, "lif_cycle_threshold.png"))

    write_report(rows_f1, rows_f3,
                 z_f1 if z_f1 is not None else np.array([]),
                 z_f3 if z_f3 is not None else np.array([]),
                 os.path.join(OUTPUT_DIR, "lif_cycle_report.txt"))
    print("\nDone.")


if __name__ == "__main__":
    main()
