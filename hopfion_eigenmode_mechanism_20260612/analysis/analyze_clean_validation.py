#!/usr/bin/env python3
"""Analyze clean linewidth, spatial mode, and circular-polarization controls."""

from __future__ import annotations

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
    load_mumax_table,
    ringdown_fft_difference,
    topology_mask_from_reference,
)


def evaluate_spatial_mode_power(hopfion_power, uniform_power, topology_mask):
    """Evaluate topology localization and uniform-background contrast."""
    hopfion_power = np.asarray(hopfion_power, dtype=float)
    uniform_power = np.asarray(uniform_power, dtype=float)
    mask = np.asarray(topology_mask, dtype=bool)
    if hopfion_power.shape != uniform_power.shape or mask.shape != hopfion_power.shape:
        raise ValueError("power arrays and topology_mask must share one shape")
    if not np.any(mask) or np.all(mask):
        raise ValueError("topology_mask must contain inner and outer cells")
    metrics = evaluate_mode_localization(
        float(np.mean(hopfion_power[mask])),
        float(np.mean(hopfion_power[~mask])),
        float(np.mean(hopfion_power)),
        float(np.mean(uniform_power)),
    )
    return {
        "mask_mean_power": float(np.mean(hopfion_power[mask])),
        "outside_mean_power": float(np.mean(hopfion_power[~mask])),
        "hopfion_total_power": float(np.mean(hopfion_power)),
        "uniform_total_power": float(np.mean(uniform_power)),
        **metrics,
    }


def _load_ovf(path: Path) -> np.ndarray:
    import discretisedfield as df

    return np.asarray(df.Field.from_file(str(path)).array, dtype=np.float32).copy()


def _frames(paths):
    for path in paths:
        yield _load_ovf(path)


def _mode(paths, frequency_ghz, reference):
    times = np.arange(len(paths), dtype=float) * 0.2e-12
    return accumulate_complex_modes(
        _frames(paths), times, [frequency_ghz], reference=reference
    )[frequency_ghz]


def analyze_linewidth(candidate_ghz):
    driven = ROOT / "mx3" / "clean_Bz_1mT_10ns.out" / "table.txt"
    control = ROOT / "mx3" / "clean_Bz_0mT_10ns.out" / "table.txt"
    spectrum = ringdown_fft_difference(
        driven, control, columns=("mz", "E_total"), t_start_s=5e-12
    )
    result = {}
    for signal in ("mz", "E_total"):
        result[signal] = estimate_peak_metrics(
            spectrum["freqs_ghz"], spectrum[f"psd_{signal}"],
            candidate_ghz, search_halfwidth_ghz=20.0,
        )
    return result


def analyze_spatial(candidate_ghz):
    names = {
        "driven": "clean_spatial_Bz_5mT",
        "control": "clean_spatial_Bz_0mT",
        "uniform": "clean_spatial_uniform_Bz_5mT",
    }
    paths = {
        key: sorted((ROOT / "mx3" / f"{name}.out").glob("roi_m*.ovf"))
        for key, name in names.items()
    }
    counts = {len(items) for items in paths.values()}
    if len(counts) != 1 or min(counts) < 8:
        raise FileNotFoundError("clean spatial frame counts are missing or inconsistent")
    references = {key: _load_ovf(items[0]) for key, items in paths.items()}
    modes = {
        key: _mode(items, candidate_ghz, references[key])
        for key, items in paths.items()
    }
    pulse_mode = modes["driven"] - modes["control"]
    hopfion_power = np.sum(np.abs(pulse_mode) ** 2, axis=-1)
    uniform_power = np.sum(np.abs(modes["uniform"]) ** 2, axis=-1)
    topology_mask = topology_mask_from_reference(references["control"])
    metrics = evaluate_spatial_mode_power(hopfion_power, uniform_power, topology_mask)
    _plot_spatial(
        hopfion_power,
        uniform_power,
        ROOT / "figures" / "clean_spatial_mode.png",
        candidate_ghz,
    )
    return metrics


def analyze_circular(candidate_ghz):
    plus_path = ROOT / "mx3" / "clean_circular_plus_2mT.out" / "table.txt"
    minus_path = ROOT / "mx3" / "clean_circular_minus_2mT.out" / "table.txt"
    plus = _complex_circular_lockin(plus_path, candidate_ghz)
    minus = _complex_circular_lockin(minus_path, candidate_ghz)
    matched_plus = plus["m_plus"]
    matched_minus = minus["m_minus"]
    denominator = matched_plus + matched_minus
    return {
        "carrier_ghz": candidate_ghz,
        "candidate_offset_ghz": 0.0,
        "plus_drive": plus,
        "minus_drive": minus,
        "matched_channel_asymmetry": (
            float((matched_plus - matched_minus) / denominator)
            if denominator > 0 else None
        ),
        "interpretation_allowed": True,
    }


def _complex_circular_lockin(path: Path, carrier_ghz: float, t_start_s=120e-12):
    table = load_mumax_table(path)
    t = np.asarray(table["t"], dtype=float)
    mask = t >= t_start_s
    t = t[mask]
    weights = np.hanning(len(t))
    phase = np.exp(-2j * np.pi * carrier_ghz * 1e9 * t)
    result = {}
    for name, signal in (
        ("m_plus", np.asarray(table["mx"])[mask] + 1j * np.asarray(table["my"])[mask]),
        ("m_minus", np.asarray(table["mx"])[mask] - 1j * np.asarray(table["my"])[mask]),
    ):
        signal = signal - np.average(signal, weights=weights)
        result[name] = float(2 * np.abs(np.sum(signal * weights * phase)) / np.sum(weights))
    return result


def _plot_spatial(hopfion_power, uniform_power, path: Path, frequency_ghz: float):
    path.parent.mkdir(exist_ok=True)
    fig, axes = plt.subplots(2, 3, figsize=(11, 7))
    labels = ["xy (sum z)", "xz (sum y)", "yz (sum x)"]
    for row, (data, title) in enumerate((
        (hopfion_power, "Hopfion driven-control"),
        (uniform_power, "uniform driven"),
    )):
        for column, projection in enumerate((
            np.sum(data, axis=2), np.sum(data, axis=1), np.sum(data, axis=0)
        )):
            image = axes[row, column].imshow(projection.T, origin="lower", cmap="magma")
            axes[row, column].set_title(f"{title}: {labels[column]}")
            fig.colorbar(image, ax=axes[row, column], fraction=0.046)
    fig.suptitle(f"clean complex-mode power at {frequency_ghz:.2f} GHz")
    fig.tight_layout()
    fig.savefig(path, dpi=220)
    plt.close(fig)


def analyze():
    clean_gate = json.loads(
        (ROOT / "results" / "clean_linearity_gate.json").read_text(encoding="utf-8")
    )
    if clean_gate.get("passed") is not True:
        raise ValueError("clean linearity gate did not pass")
    candidate = float(clean_gate["candidate_frequency_ghz"])
    summary = {
        "candidate_frequency_ghz": candidate,
        "linewidth": analyze_linewidth(candidate),
        "spatial_gate": analyze_spatial(candidate),
        "circular": analyze_circular(candidate),
    }
    stage1_gate = {
        "target_frequency_ghz": candidate,
        "passed": summary["spatial_gate"]["passed"],
        "localization_ratio": summary["spatial_gate"]["localization_ratio"],
        "background_contrast": summary["spatial_gate"]["background_contrast"],
        "source": "clean driven-minus-zero-field complex mode",
    }
    _write_json(ROOT / "results" / "clean_validation_summary.json", summary)
    _write_json(ROOT / "results" / "stage1_gate.json", stage1_gate)
    return summary


def _json_safe(value):
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, float) and not np.isfinite(value):
        return "inf" if value > 0 else "nan"
    return value


def _write_json(path: Path, payload):
    path.write_text(
        json.dumps(_json_safe(payload), ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    analyze()
