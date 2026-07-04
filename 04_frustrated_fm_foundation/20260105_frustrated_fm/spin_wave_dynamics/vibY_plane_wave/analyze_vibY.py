"""
Analyze vibY plane-wave experiments.
Compares vibY vs vibX across 3 source combos, 4 frequencies, 3 amplitudes.

Output (results/):
  - vibY_displacement_matrix.png   — heatmap: |dr| for each (src, freq, amp)
  - vibY_vs_vibX_comparison.png    — bar chart comparing vibY vs vibX at 440GHz/1T
  - vibY_hall_angle.png            — Hall angle distribution
  - vibY_summary.txt               — full numerical summary
"""
import sys
import os
import glob
import re
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, "/mnt/d/Research/Hopfion/95_shared_scripts")
from hopfion_analysis import extract_trajectory_phase_correlation

RESULTS_DIR = os.path.join(HERE, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

DT_NS = 0.005  # 5ps autosave

SOURCES = ["srcX", "srcY", "srcZ"]
FREQS = [200, 440, 700, 1100]
AMPS = [0.5, 1.0, 2.0]

# vibX reference data (from drive_selection @ 440GHz, 1T, 0.5ns)
VIBX_REF = {
    "srcX_vibX": {"dr": 2.36, "dz": 2.36, "hall_deg": 87},
    "srcY_vibX": {"dr": 2.31, "dz": 2.31, "hall_deg": 87},
    "srcZ_vibX": {"dr": 6.71, "dz": -6.71, "hall_deg": 1},
}


def amp_str(a):
    return f"{a:.1f}".replace(".", "p").rstrip("0").rstrip("p") or "0"


def parse_one(src, freq, amp):
    """Extract final displacement from one simulation."""
    name = f"sw_{src}_vibY_f{freq}_B{amp_str(amp)}T"
    out_dir = os.path.join(HERE, name + ".out")
    if not os.path.isdir(out_dir):
        return None

    try:
        traj = extract_trajectory_phase_correlation(out_dir, DT_NS, verbose=False)
    except Exception as e:
        print(f"  WARN: {name}: {e}")
        return None

    if len(traj) < 2:
        return None

    t0, (dx0, dy0, dz0), c0 = traj[0]
    tf, (dxf, dyf, dzf), cf = traj[-1]

    dx = dxf - dx0
    dy = dyf - dy0
    dz = dzf - dz0
    dr = np.sqrt(dx**2 + dy**2 + dz**2)

    # Hall angle: angle between displacement and propagation direction
    # srcX propagation = -x → expected motion +z → Hall = angle from +z in xz plane
    # srcZ propagation = -z → expected motion -z
    d_perp = np.sqrt(dx**2 + dy**2)  # perpendicular to z
    hall_deg = np.degrees(np.arctan2(d_perp, abs(dz))) if abs(dz) > 0.01 else 90.0

    return {
        "name": name, "src": src, "freq": freq, "amp": amp,
        "dx": dx, "dy": dy, "dz": dz, "dr": dr,
        "hall_deg": hall_deg,
        "core_start": int(c0), "core_end": int(cf),
        "n_frames": len(traj), "t_final": tf,
    }


def main():
    print("=== vibY Plane Wave Analysis ===\n")
    results = []

    for src in SOURCES:
        for freq in FREQS:
            for amp in AMPS:
                r = parse_one(src, freq, amp)
                if r:
                    results.append(r)
                    status = "OK" if r["core_end"] > 0 else "COLLAPSED"
                    print(f"  {r['name']}: |dr|={r['dr']:.3f}nm, dz={r['dz']:+.3f}nm, "
                          f"hall={r['hall_deg']:.1f}°, core={r['core_end']} [{status}]")
                else:
                    print(f"  sw_{src}_vibY_f{freq}_B{amp_str(amp)}T: NOT FOUND")

    if not results:
        print("\nNo data found. Run simulations first.")
        return

    # --- Text summary ---
    txt_path = os.path.join(RESULTS_DIR, "vibY_summary.txt")
    with open(txt_path, "w") as f:
        f.write("=" * 80 + "\n")
        f.write("vibY Plane Wave — Full Summary\n")
        f.write("3 sources × 4 frequencies × 3 amplitudes, vibY oscillation, 1ns\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"{'Name':<35} {'|dr|':>7} {'dz':>8} {'hall':>6} {'core_f':>7} {'status':>8}\n")
        f.write("-" * 75 + "\n")
        for r in sorted(results, key=lambda x: (x["src"], x["freq"], x["amp"])):
            status = "OK" if r["core_end"] > 0 else "DEAD"
            f.write(f"{r['name']:<35} {r['dr']:7.3f} {r['dz']:+8.3f} "
                    f"{r['hall_deg']:6.1f} {r['core_end']:7d} {status:>8}\n")
    print(f"\nSaved: {txt_path}")

    # --- Displacement heatmap ---
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    for ax, src in zip(axes, SOURCES):
        data = np.full((len(FREQS), len(AMPS)), np.nan)
        for r in results:
            if r["src"] == src:
                fi = FREQS.index(r["freq"])
                ai = AMPS.index(r["amp"])
                data[fi, ai] = r["dr"]
        im = ax.imshow(data, aspect="auto", cmap="YlOrRd", origin="lower")
        ax.set_xticks(range(len(AMPS)))
        ax.set_xticklabels([f"{a}T" for a in AMPS])
        ax.set_yticks(range(len(FREQS)))
        ax.set_yticklabels([f"{f}GHz" for f in FREQS])
        ax.set_title(f"{src}_vibY |dr| (nm)")
        ax.set_xlabel("Amplitude")
        ax.set_ylabel("Frequency")
        for fi in range(len(FREQS)):
            for ai in range(len(AMPS)):
                if not np.isnan(data[fi, ai]):
                    ax.text(ai, fi, f"{data[fi, ai]:.2f}", ha="center", va="center", fontsize=8)
        plt.colorbar(im, ax=ax, shrink=0.8)
    plt.suptitle("vibY Plane Wave: Displacement Matrix", fontsize=14)
    plt.tight_layout()
    out_png = os.path.join(RESULTS_DIR, "vibY_displacement_matrix.png")
    fig.savefig(out_png, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out_png}")

    # --- vibY vs vibX comparison at 440GHz, 1T ---
    fig, ax = plt.subplots(figsize=(8, 5))
    labels = []
    vibY_vals = []
    vibX_vals = []
    for src in SOURCES:
        ref_key = f"{src}_vibX"
        vibY_r = [r for r in results if r["src"] == src and r["freq"] == 440 and r["amp"] == 1.0]
        if vibY_r and ref_key in VIBX_REF:
            labels.append(src)
            vibY_vals.append(vibY_r[0]["dr"])
            vibX_vals.append(VIBX_REF[ref_key]["dr"])

    if labels:
        x = np.arange(len(labels))
        w = 0.35
        ax.bar(x - w/2, vibX_vals, w, label="vibX (reference)", color="#1f77b4")
        ax.bar(x + w/2, vibY_vals, w, label="vibY (this work)", color="#ff7f0e")
        ax.set_xticks(x)
        ax.set_xticklabels(labels)
        ax.set_ylabel("|dr| (nm)")
        ax.set_title("vibY vs vibX @ 440GHz, B=1T, 1ns vs 0.5ns")
        ax.legend()
        ax.grid(True, alpha=0.3)
    out_png = os.path.join(RESULTS_DIR, "vibY_vs_vibX_comparison.png")
    fig.savefig(out_png, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out_png}")

    # --- Hall angle distribution ---
    fig, ax = plt.subplots(figsize=(8, 5))
    for src, color in zip(SOURCES, ["#1f77b4", "#2ca02c", "#d62728"]):
        src_r = [r for r in results if r["src"] == src and r["dr"] > 0.1]
        if src_r:
            halls = [r["hall_deg"] for r in src_r]
            freqs_label = [f"f{r['freq']}\nB{r['amp']}" for r in src_r]
            ax.scatter(range(len(halls)), halls, label=src, color=color, s=60)
    ax.axhline(90, color="gray", linestyle="--", linewidth=0.8, label="90°")
    ax.set_ylabel("Hall angle (°)")
    ax.set_title("vibY: Topological Hall Angle")
    ax.legend()
    ax.grid(True, alpha=0.3)
    out_png = os.path.join(RESULTS_DIR, "vibY_hall_angle.png")
    fig.savefig(out_png, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out_png}")


if __name__ == "__main__":
    main()
