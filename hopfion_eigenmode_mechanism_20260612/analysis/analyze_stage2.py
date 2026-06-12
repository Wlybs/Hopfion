#!/usr/bin/env python3
"""Analyze gated continuous-wave bridge runs without claiming net absorption."""

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

from resonance_analysis import coherent_amplitude, fit_power_law, load_mumax_table  # noqa: E402


def _load_ovf(path: Path) -> np.ndarray:
    import discretisedfield as df

    return np.asarray(df.Field.from_file(str(path)).array, dtype=np.float32).copy()


def _roi_observables(paths: list[Path], dt_ps=1.0, t_start_ps=100.0) -> dict:
    if len(paths) < 2:
        return {}
    coordinates = None
    centroids = []
    core_cells = []
    for path in paths:
        array = _load_ovf(path)
        mz = np.squeeze(array[..., 2])
        if coordinates is None:
            axes = [np.arange(size, dtype=float) * 0.5 for size in mz.shape]
            coordinates = np.meshgrid(*axes, indexing="ij")
        contrast = np.maximum(1.0 - mz, 0.0) ** 2
        total = float(np.sum(contrast))
        if total <= 0:
            centroids.append(np.full(3, np.nan))
        else:
            centroids.append(np.array([
                np.sum(contrast * coordinate) / total for coordinate in coordinates
            ]))
        core_cells.append(int(np.count_nonzero(mz < 0)))
    centroids = np.asarray(centroids)
    displacement = np.linalg.norm(centroids - centroids[0], axis=1)
    times_ps = np.arange(len(paths), dtype=float) * dt_ps
    mask = times_ps >= t_start_ps
    if not np.any(mask):
        mask = np.ones(len(paths), dtype=bool)
    core = np.asarray(core_cells, dtype=float)
    return {
        "frame_count": len(paths),
        "mean_displacement_nm": float(np.nanmean(displacement[mask])),
        "max_displacement_nm": float(np.nanmax(displacement[mask])),
        "core_cells_mean": float(np.mean(core[mask])),
        "core_cells_std": float(np.std(core[mask])),
    }


def _energy_trend(table: dict, t_start_s=0.1e-9) -> float:
    t = np.asarray(table["t"])
    energy = np.asarray(table["E_total"])
    mask = t >= t_start_s
    if np.count_nonzero(mask) < 2:
        return float("nan")
    return float(np.polyfit(t[mask], energy[mask], 1)[0])


def analyze():
    manifest_path = ROOT / "results" / "stage2_simulation_manifest.csv"
    if not manifest_path.is_file():
        raise FileNotFoundError("stage2_simulation_manifest.csv is missing")
    with manifest_path.open(encoding="utf-8") as handle:
        cases = [row for row in csv.DictReader(handle) if row["kind"] == "cw"]
    stage1_gate = json.loads(
        (ROOT / "results" / "stage1_gate.json").read_text(encoding="utf-8")
    )
    target_frequency = float(stage1_gate.get("target_frequency_ghz", 174.0))

    rows = []
    for case in cases:
        out_dir = ROOT / "mx3" / f"{case['name']}.out"
        table_path = out_dir / "table.txt"
        if not table_path.is_file():
            continue
        frequency = float(case["frequency_ghz"])
        table = load_mumax_table(table_path)
        row = {
            **case,
            "response_mx": coherent_amplitude(table["t"], table["mx"], frequency, 0.1e-9),
            "response_my": coherent_amplitude(table["t"], table["my"], frequency, 0.1e-9),
            "response_mz": coherent_amplitude(table["t"], table["mz"], frequency, 0.1e-9),
            "energy_trend_w": _energy_trend(table),
        }
        row["response_vector"] = float(np.linalg.norm([
            row["response_mx"], row["response_my"], row["response_mz"]
        ]))
        roi_paths = sorted(out_dir.glob("roi_m*.ovf"))
        row.update(_roi_observables(roi_paths))
        rows.append(row)

    results_path = ROOT / "results" / "cw_bridge.csv"
    if rows:
        with results_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        _plot_frequency_bridge(
            rows, ROOT / "figures" / "cw_bridge_frequency.png", target_frequency
        )

    amplitude_rows = [
        row for row in rows
        if row["source_axis"] == "x" and row["vib_axis"] == "x"
        and abs(float(row["frequency_ghz"]) - target_frequency) < 1e-9
    ]
    fit = None
    if len(amplitude_rows) == 3 and all(row["response_vector"] > 0 for row in amplitude_rows):
        fit = fit_power_law(
            [float(row["b_amp_t"]) for row in amplitude_rows],
            [row["response_vector"] for row in amplitude_rows],
        )
    summary = {
        "completed_cw_runs": len(rows),
        "response_amplitude_power_law": fit,
        "energy_trend_warning": (
            "energy_trend_w is a post-transient total-energy slope, not a net absorption rate"
        ),
    }
    (ROOT / "results" / "cw_bridge_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return summary


def _plot_frequency_bridge(rows: list[dict], path: Path, target_frequency: float):
    selected = sorted(
        (
            row for row in rows
            if row["source_axis"] == "x" and row["vib_axis"] == "x"
            and abs(float(row["b_amp_t"]) - 0.2) < 1e-12
        ),
        key=lambda row: float(row["frequency_ghz"]),
    )
    if not selected:
        return
    path.parent.mkdir(exist_ok=True)
    frequencies = [float(row["frequency_ghz"]) for row in selected]
    responses = [row["response_vector"] for row in selected]
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.plot(frequencies, responses, "o-", color="#176b87", label="CW coherent response")
    ax.axvline(
        target_frequency,
        color="#c44e52",
        ls="--",
        lw=1.2,
        label=f"clean ringdown {target_frequency:.2f} GHz",
    )
    ax.set_xlabel("drive frequency (GHz)")
    ax.set_ylabel("coherent |m| amplitude")
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=220)
    plt.close(fig)


if __name__ == "__main__":
    analyze()
