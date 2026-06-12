#!/usr/bin/env python3
"""Demodulate wavefield slices and compare plane/point source k spectra."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
sys.path.insert(0, str(REPO / "scripts"))

from resonance_analysis import accumulate_complex_modes, wavevector_power_spectrum  # noqa: E402
from paper_style import (  # noqa: E402
    panel_label,
    save_paper_fig,
    shared_legend_above,
    setup_paper_style,
)

setup_paper_style()


def _load_ovf(path: Path) -> np.ndarray:
    import discretisedfield as df

    return np.asarray(df.Field.from_file(str(path)).array, dtype=np.float32).copy()


def _frames(paths):
    for path in paths:
        yield _load_ovf(path)


def analyze_case(case: dict) -> tuple[dict, dict]:
    out_dir = ROOT / "mx3" / f"{case['name']}.out"
    paths = sorted(out_dir.glob("slice_m*.ovf"))
    if len(paths) < 100:
        raise FileNotFoundError(f"insufficient slice frames in {out_dir}")
    dt_s = 0.02e-12
    start = int(round(10.0 / 0.02))
    selected = paths[start:]
    times = np.arange(start, len(paths), dtype=float) * dt_s
    reference = _load_ovf(paths[0])
    frequency = float(case["frequency_ghz"])
    mode = accumulate_complex_modes(
        _frames(selected), times, [frequency], reference=reference
    )[frequency]
    plus = np.squeeze(mode[..., 0] + 1j * mode[..., 1])
    minus = np.squeeze(mode[..., 0] - 1j * mode[..., 1])
    plus_power = float(np.sum(np.abs(plus) ** 2))
    minus_power = float(np.sum(np.abs(minus) ** 2))
    transverse = plus if plus_power >= minus_power else minus
    selected_channel = "m_plus" if plus_power >= minus_power else "m_minus"
    downstream = transverse[35:90, 5:95]
    spectrum = wavevector_power_spectrum(downstream, cell_size_nm=0.5, window="hann")
    metrics = {
        "name": case["name"],
        "geometry": case["geometry"],
        "frequency_ghz": frequency,
        "frame_count": len(paths),
        "selected_circular_channel": selected_channel,
        "peak_k_rad_per_nm": spectrum["peak_k_rad_per_nm"],
        "radial_fwhm_rad_per_nm": spectrum["radial_fwhm_rad_per_nm"],
        "low_k_power_fraction": spectrum["low_k_power_fraction"],
        "spectral_entropy": spectrum["spectral_entropy"],
    }
    return metrics, {"mode": downstream, "spectrum": spectrum}


def analyze():
    manifest_path = ROOT / "results" / "stage2_simulation_manifest.csv"
    with manifest_path.open(encoding="utf-8") as handle:
        cases = [row for row in csv.DictReader(handle) if row["kind"] == "wavefield"]
    rows = []
    details = {}
    for case in cases:
        try:
            metrics, detail = analyze_case(case)
        except FileNotFoundError:
            continue
        rows.append(metrics)
        details[case["name"]] = detail
        _plot_case(metrics, detail, ROOT / "figures" / f"{case['name']}_k.png")

    if rows:
        with (ROOT / "results" / "k_spectrum_metrics.csv").open(
            "w", newline="", encoding="utf-8"
        ) as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        _plot_radial_comparison(rows, details, ROOT / "figures" / "k_spectrum_comparison.png")

    comparisons = []
    for frequency in (700.0, 1000.0):
        pair = {row["geometry"]: row for row in rows if row["frequency_ghz"] == frequency}
        if set(pair) == {"plane", "point"}:
            comparisons.append({
                "frequency_ghz": frequency,
                "point_minus_plane_peak_k_rad_per_nm": (
                    pair["point"]["peak_k_rad_per_nm"]
                    - pair["plane"]["peak_k_rad_per_nm"]
                ),
                "point_minus_plane_entropy": (
                    pair["point"]["spectral_entropy"]
                    - pair["plane"]["spectral_entropy"]
                ),
                "point_minus_plane_low_k_fraction": (
                    pair["point"]["low_k_power_fraction"]
                    - pair["plane"]["low_k_power_fraction"]
                ),
            })
    summary = {
        "completed_wavefield_runs": len(rows),
        "comparisons": comparisons,
        "interpretation_rule": (
            "same peak k with larger point-source entropy supports angular/bandwidth broadening; "
            "a lower point-source peak k is required before using the term redshift"
        ),
    }
    (ROOT / "results" / "k_spectrum_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return summary


def _plot_case(metrics, detail, path: Path):
    path.parent.mkdir(exist_ok=True)
    mode_power = np.abs(detail["mode"]) ** 2
    spectrum = detail["spectrum"]
    fig, axes = plt.subplots(1, 2, figsize=(9, 4))
    axes[0].imshow(mode_power.T, origin="lower", cmap="magma", aspect="auto")
    axes[0].set_xlabel("x cell")
    axes[0].set_ylabel("y cell")
    extent = [
        spectrum["kx_rad_per_nm"][0], spectrum["kx_rad_per_nm"][-1],
        spectrum["ky_rad_per_nm"][0], spectrum["ky_rad_per_nm"][-1],
    ]
    axes[1].imshow(
        spectrum["power"].T, origin="lower", cmap="viridis", aspect="auto", extent=extent
    )
    axes[1].set_xlabel("kx (rad/nm)")
    axes[1].set_ylabel("ky (rad/nm)")
    panel_label(fig, axes[0], "(a)")
    panel_label(fig, axes[1], "(b)")
    save_paper_fig(fig, path)
    plt.close(fig)


def _plot_radial_comparison(rows, details, path: Path):
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
    for ax, frequency in zip(axes, (700.0, 1000.0)):
        for row in rows:
            if row["frequency_ghz"] != frequency:
                continue
            spectrum = details[row["name"]]["spectrum"]
            power = spectrum["radial_power"]
            if np.max(power) > 0:
                power = power / np.max(power)
            ax.plot(spectrum["radial_k_rad_per_nm"], power, label=row["geometry"])
        ax.set_xlabel(f"|k| (rad/nm), {frequency:g} GHz")
        ax.grid(True, alpha=0.25)
    axes[0].set_ylabel("normalized radial power")
    shared_legend_above(fig, axes[0], ncol=2)
    panel_label(fig, axes[0], "(a)")
    panel_label(fig, axes[1], "(b)")
    save_paper_fig(fig, path)
    plt.close(fig)


if __name__ == "__main__":
    analyze()
