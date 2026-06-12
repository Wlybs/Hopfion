#!/usr/bin/env python3
"""Analyze stage-1 linear, linewidth, circular, and ROI mode evidence."""

from __future__ import annotations

import argparse
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

from resonance_analysis import (  # noqa: E402
    accumulate_complex_modes,
    estimate_peak_metrics,
    evaluate_mode_localization,
    fit_power_law,
    load_mumax_table,
    ringdown_fft_from_table,
    topology_mask_from_reference,
)


TARGET_GHZ = 173.66
SPATIAL_FREQUENCIES_GHZ = [173.66, 126.67, 77.64, 38.82]
EXISTING_5MT_TABLE = (
    REPO
    / "hopfion_eigenmode_ringdown_20260608"
    / "mx3"
    / "ringdown_sinc_Bz.out"
    / "table.txt"
)


def _table_path(name: str) -> Path:
    return ROOT / "mx3" / f"{name}.out" / "table.txt"


def _write_csv(path: Path, rows: list[dict]):
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _json_safe(value):
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, float) and not np.isfinite(value):
        return "inf" if value > 0 else "-inf"
    return value


def _write_json(path: Path, payload):
    path.write_text(
        json.dumps(_json_safe(payload), ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def analyze_ringdown_tables(results_dir: Path, figures_dir: Path) -> dict:
    runs = [
        ("linear_Bz_1mT_05ns", 0.001, _table_path("linear_Bz_1mT_05ns")),
        ("linear_Bz_2mT_05ns", 0.002, _table_path("linear_Bz_2mT_05ns")),
        ("existing_Bz_5mT_05ns", 0.005, EXISTING_5MT_TABLE),
    ]
    rows = []
    spectra = {}
    amplitudes = []
    powers = []
    for name, amplitude, table_path in runs:
        if not table_path.is_file():
            continue
        spectrum = ringdown_fft_from_table(
            table_path,
            columns=("mz", "E_total"),
            t_start_s=5e-12,
        )
        spectra[name] = spectrum
        for signal in ("mz", "E_total"):
            key = f"psd_{signal}"
            metrics = estimate_peak_metrics(
                spectrum["freqs_ghz"],
                spectrum[key],
                target_ghz=TARGET_GHZ,
            )
            row = {
                "run": name,
                "b0_t": amplitude,
                "signal": signal,
                **metrics,
            }
            rows.append(row)
            if signal == "mz" and metrics.get("power", 0) > 0:
                amplitudes.append(amplitude)
                powers.append(metrics["power"])

    _write_csv(results_dir / "stage1_ringdown_metrics.csv", rows)
    summary = {"available_linear_runs": len(amplitudes)}
    if len(amplitudes) == 3:
        fit = fit_power_law(amplitudes, powers)
        summary["linear_power_law"] = fit
        _write_json(results_dir / "stage1_linear_fit.json", fit)
        _plot_linearity(amplitudes, powers, fit, figures_dir / "stage1_linearity.png")

    linewidth_table = _table_path("linewidth_Bz_1mT_10ns")
    if linewidth_table.is_file():
        spectrum = ringdown_fft_from_table(
            linewidth_table,
            columns=("mz", "E_total"),
            t_start_s=5e-12,
        )
        linewidth = {}
        for signal in ("mz", "E_total"):
            linewidth[signal] = estimate_peak_metrics(
                spectrum["freqs_ghz"],
                spectrum[f"psd_{signal}"],
                target_ghz=TARGET_GHZ,
            )
        summary["linewidth_1ns"] = linewidth
        _write_json(results_dir / "stage1_linewidth.json", linewidth)
        _plot_linewidth(spectrum, figures_dir / "stage1_linewidth.png")

    return summary


def _plot_linearity(amplitudes, powers, fit, path: Path):
    x = np.asarray(amplitudes)
    y = np.asarray(powers)
    order = np.argsort(x)
    x = x[order]
    y = y[order]
    fit_y = fit["prefactor"] * x ** fit["exponent"]
    fig, ax = plt.subplots(figsize=(6, 4.2))
    ax.loglog(x * 1e3, y, "o", color="#176b87", label="ringdown peak")
    ax.loglog(x * 1e3, fit_y, "-", color="#c44e52", label=f"n={fit['exponent']:.2f}")
    ax.set_xlabel("pulse amplitude (mT)")
    ax.set_ylabel("m_z peak power (arb. units)")
    ax.grid(True, which="both", alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=220)
    plt.close(fig)


def _plot_linewidth(spectrum, path: Path):
    fig, ax = plt.subplots(figsize=(7, 4.2))
    freqs = spectrum["freqs_ghz"]
    power = spectrum["psd_mz"]
    mask = (freqs >= 130) & (freqs <= 220)
    ax.plot(freqs[mask], power[mask] / np.max(power[mask]), color="#202020")
    ax.axvline(TARGET_GHZ, color="#c44e52", ls="--", lw=1)
    ax.set_xlabel("frequency (GHz)")
    ax.set_ylabel("normalized m_z power")
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=220)
    plt.close(fig)


def _complex_inplane_power(table_path: Path, t_start_s=120e-12) -> dict:
    table = load_mumax_table(table_path)
    t = np.asarray(table["t"])
    mask = t >= t_start_s
    t = t[mask]
    dt = float(np.median(np.diff(t)))
    window = np.hanning(len(t))
    mx = np.asarray(table["mx"])[mask]
    my = np.asarray(table["my"])[mask]
    freqs = np.fft.fftfreq(len(t), d=dt) * 1e-9
    result = {}
    for label, signal in (("m_plus", mx + 1j * my), ("m_minus", mx - 1j * my)):
        signal = signal - np.mean(signal)
        power = np.abs(np.fft.fft(signal * window)) ** 2 / np.sum(window**2)
        positive = freqs >= 0
        metrics = estimate_peak_metrics(
            freqs[positive], power[positive], target_ghz=174.0, search_halfwidth_ghz=20.0
        )
        result[label] = metrics
    return result


def analyze_circular(results_dir: Path) -> dict | None:
    paths = {
        "plus_drive": _table_path("circular_plus_2mT"),
        "minus_drive": _table_path("circular_minus_2mT"),
    }
    if not all(path.is_file() for path in paths.values()):
        return None
    result = {name: _complex_inplane_power(path) for name, path in paths.items()}
    plus_power = result["plus_drive"]["m_plus"].get("power", 0.0)
    minus_power = result["minus_drive"]["m_minus"].get("power", 0.0)
    denominator = plus_power + minus_power
    result["matched_channel_asymmetry"] = (
        float((plus_power - minus_power) / denominator) if denominator > 0 else None
    )
    _write_json(results_dir / "stage1_circular_selectivity.json", result)
    return result


def _load_ovf(path: Path) -> np.ndarray:
    import discretisedfield as df

    return np.asarray(df.Field.from_file(str(path)).array, dtype=np.float32).copy()


def _ovf_paths(name: str) -> list[Path]:
    return sorted((ROOT / "mx3" / f"{name}.out").glob("*.ovf"))


def _frame_stream(paths: list[Path]):
    for path in paths:
        yield _load_ovf(path)


def analyze_spatial(results_dir: Path, figures_dir: Path) -> dict | None:
    hopfion_paths = _ovf_paths("spatial_hopfion_Bz")
    background_paths = _ovf_paths("spatial_uniform_Bz")
    if len(hopfion_paths) < 8 or len(background_paths) < 8:
        return None
    if len(hopfion_paths) != len(background_paths):
        raise ValueError("Hopfion and background ROI frame counts differ")

    times = np.arange(len(hopfion_paths), dtype=float) * 0.2e-12
    hopfion_reference = _load_ovf(hopfion_paths[0])
    background_reference = _load_ovf(background_paths[0])
    hopfion_modes = accumulate_complex_modes(
        _frame_stream(hopfion_paths),
        times,
        SPATIAL_FREQUENCIES_GHZ,
        reference=hopfion_reference,
    )
    background_modes = accumulate_complex_modes(
        _frame_stream(background_paths),
        times,
        SPATIAL_FREQUENCIES_GHZ,
        reference=background_reference,
    )
    topology_mask = topology_mask_from_reference(hopfion_reference)

    rows = []
    gate = None
    for frequency in SPATIAL_FREQUENCIES_GHZ:
        hopfion_power = np.sum(np.abs(hopfion_modes[frequency]) ** 2, axis=-1)
        background_power = np.sum(np.abs(background_modes[frequency]) ** 2, axis=-1)
        inner = float(np.mean(hopfion_power[topology_mask]))
        outer = float(np.mean(hopfion_power[~topology_mask]))
        hopfion_total = float(np.mean(hopfion_power))
        background_total = float(np.mean(background_power))
        metrics = evaluate_mode_localization(
            inner,
            outer,
            hopfion_total,
            background_total,
        )
        rows.append({
            "frequency_ghz": frequency,
            "mask_mean_power": inner,
            "outside_mean_power": outer,
            "hopfion_total_power": hopfion_total,
            "background_total_power": background_total,
            **metrics,
        })
        if frequency == SPATIAL_FREQUENCIES_GHZ[0]:
            gate = metrics
            _plot_mode_projections(
                hopfion_power,
                background_power,
                topology_mask,
                figures_dir / "stage1_mode_173p66GHz.png",
            )

    _write_csv(results_dir / "stage1_spatial_metrics.csv", rows)
    gate_payload = {
        "target_frequency_ghz": TARGET_GHZ,
        "criteria": {
            "min_localization_ratio": 2.0,
            "min_background_contrast": 3.0,
        },
        **gate,
    }
    _write_json(results_dir / "stage1_gate.json", gate_payload)
    return gate_payload


def _plot_mode_projections(hopfion_power, background_power, mask, path: Path):
    fig, axes = plt.subplots(2, 3, figsize=(11, 7))
    datasets = [hopfion_power, background_power]
    titles = ["Hopfion", "uniform background"]
    for row, (data, title) in enumerate(zip(datasets, titles)):
        projections = [np.sum(data, axis=2), np.sum(data, axis=1), np.sum(data, axis=0)]
        for col, projection in enumerate(projections):
            image = axes[row, col].imshow(projection.T, origin="lower", cmap="magma")
            axes[row, col].set_title(f"{title}: {'xyz'[col]} projection")
            fig.colorbar(image, ax=axes[row, col], fraction=0.046)
    fig.suptitle("173.66 GHz complex-mode power")
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def write_interpretation(summary: dict, path: Path):
    lines = [
        "# 第一阶段分析记录",
        "",
        "本文件由现有输出自动生成。缺失批次保持为空，不补写预测结果。",
        "",
        "## 当前机器可读摘要",
        "",
        "```json",
        json.dumps(summary, ensure_ascii=False, indent=2),
        "```",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()

    results_dir = ROOT / "results"
    figures_dir = ROOT / "figures"
    notes_dir = ROOT / "notes"
    results_dir.mkdir(exist_ok=True)
    figures_dir.mkdir(exist_ok=True)
    notes_dir.mkdir(exist_ok=True)

    summary = {
        "ringdown": analyze_ringdown_tables(results_dir, figures_dir),
        "circular": analyze_circular(results_dir),
        "spatial_gate": analyze_spatial(results_dir, figures_dir),
    }
    if args.require_complete and any(value is None for value in summary.values()):
        raise FileNotFoundError("Stage-1 outputs are incomplete")
    _write_json(results_dir / "stage1_summary.json", summary)
    write_interpretation(summary, notes_dir / "stage1_interpretation.md")


if __name__ == "__main__":
    main()
