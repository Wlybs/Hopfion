#!/usr/bin/env python3
"""Audit boundary-quench contamination and clean pulse linearity gates."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
sys.path.insert(0, str(REPO / "scripts"))

from resonance_analysis import (  # noqa: E402
    coherent_amplitude,
    estimate_peak_metrics,
    find_fft_peaks,
    fit_power_law,
    load_mumax_table,
    ringdown_fft_difference,
    ringdown_fft_from_table,
)


EXISTING_5MT = (
    REPO
    / "hopfion_eigenmode_ringdown_20260608"
    / "mx3"
    / "ringdown_sinc_Bz.out"
    / "table.txt"
)


def evaluate_quench_control(control_amplitude, one_mt_amplitude, five_mt_amplitude):
    """Flag a mode that is comparable without drive or insensitive to amplitude."""
    if min(control_amplitude, one_mt_amplitude, five_mt_amplitude) < 0:
        raise ValueError("amplitudes must be non-negative")
    control_ratio = (
        float(control_amplitude / one_mt_amplitude)
        if one_mt_amplitude > 0 else float("inf")
    )
    scaling_exponent = (
        float(np.log(five_mt_amplitude / one_mt_amplitude) / np.log(5.0))
        if one_mt_amplitude > 0 and five_mt_amplitude > 0 else float("nan")
    )
    dominated = bool(control_ratio >= 0.5 or scaling_exponent < 0.5)
    return {
        "control_to_1mt_ratio": control_ratio,
        "raw_amplitude_exponent_1_to_5mt": scaling_exponent,
        "quench_dominated": dominated,
        "criteria": {
            "control_to_1mt_ratio": ">= 0.5",
            "raw_amplitude_exponent_1_to_5mt": "< 0.5",
            "combination": "either",
        },
    }


def evaluate_clean_linearity(exponent, r_squared, snr_5mt,
                             peak_spread_ghz, frequency_step_ghz):
    """Apply the clean-ringdown gate before expensive spatial validation."""
    passed = bool(
        1.5 <= exponent <= 2.5
        and r_squared >= 0.9
        and snr_5mt >= 3.0
        and peak_spread_ghz <= 1.5 * frequency_step_ghz
    )
    return {
        "passed": passed,
        "criteria": {
            "power_exponent": "1.5 <= n <= 2.5",
            "r_squared": ">= 0.9",
            "snr_5mt": ">= 3",
            "peak_spread": "<= 1.5 frequency bins",
        },
    }


def _common_window_amplitude(path: Path, target_ghz: float, t_end_s: float) -> float:
    table = load_mumax_table(path)
    mask = np.asarray(table["t"]) <= t_end_s
    return coherent_amplitude(
        np.asarray(table["t"])[mask],
        np.asarray(table["mz"])[mask],
        target_ghz,
        t_start_s=5e-12,
    )


def analyze_quench(target_ghz=173.66):
    paths = {
        "control_0mT": ROOT / "mx3" / "control_quench_Bz_0mT_05ns.out" / "table.txt",
        "one_mT": ROOT / "mx3" / "linear_Bz_1mT_05ns.out" / "table.txt",
        "five_mT": EXISTING_5MT,
    }
    if not all(path.is_file() for path in paths.values()):
        missing = [str(path) for path in paths.values() if not path.is_file()]
        raise FileNotFoundError(f"missing quench-control tables: {missing}")
    t_end = min(float(load_mumax_table(path)["t"][-1]) for path in paths.values())
    amplitudes = {
        name: _common_window_amplitude(path, target_ghz, t_end)
        for name, path in paths.items()
    }
    result = {
        "target_frequency_ghz": target_ghz,
        "common_t_end_s": t_end,
        "raw_mz_lockin_amplitudes": amplitudes,
        **evaluate_quench_control(
            amplitudes["control_0mT"],
            amplitudes["one_mT"],
            amplitudes["five_mT"],
        ),
    }
    _write_json(ROOT / "results" / "control_quench_audit.json", result)
    return result


def analyze_clean():
    control = ROOT / "mx3" / "clean_Bz_0mT_05ns.out" / "table.txt"
    driven = {
        0.001: ROOT / "mx3" / "clean_Bz_1mT_05ns.out" / "table.txt",
        0.002: ROOT / "mx3" / "clean_Bz_2mT_05ns.out" / "table.txt",
        0.005: ROOT / "mx3" / "clean_Bz_5mT_05ns.out" / "table.txt",
    }
    if not control.is_file() or not all(path.is_file() for path in driven.values()):
        raise FileNotFoundError("clean linearity tables are incomplete")

    spectra = {
        amplitude: ringdown_fft_difference(path, control, columns=("mz", "E_total"), t_start_s=5e-12)
        for amplitude, path in driven.items()
    }
    five = spectra[0.005]
    peaks = find_fft_peaks(
        five["freqs_ghz"], five["psd_mz"],
        min_freq_ghz=20.0, max_freq_ghz=1500.0,
        max_peaks=8, min_prominence_rel=0.02,
    )
    if not peaks:
        result = {"passed": False, "reason": "no_clean_mz_peak"}
        _write_json(ROOT / "results" / "clean_linearity_gate.json", result)
        return result
    target = float(peaks[0]["frequency_ghz"])
    frequency_step = float(five["freqs_ghz"][1] - five["freqs_ghz"][0])
    metrics = {}
    for amplitude, spectrum in spectra.items():
        metrics[amplitude] = estimate_peak_metrics(
            spectrum["freqs_ghz"], spectrum["psd_mz"],
            target, search_halfwidth_ghz=max(10.0, 2.0 * frequency_step),
        )
    if not all("power" in item and "frequency_ghz" in item for item in metrics.values()):
        result = {"passed": False, "reason": "peak_unresolved_across_amplitudes"}
        _write_json(ROOT / "results" / "clean_linearity_gate.json", result)
        return result

    fit = fit_power_law(
        list(metrics),
        [metrics[amplitude]["power"] for amplitude in metrics],
    )
    control_spectrum = ringdown_fft_from_table(control, columns=("mz",), t_start_s=5e-12)
    control_index = int(np.argmin(np.abs(control_spectrum["freqs_ghz"] - target)))
    control_power = float(control_spectrum["psd_mz"][control_index])
    signal_power = float(metrics[0.005]["power"])
    snr = signal_power / control_power if control_power > 0 else float("inf")
    peak_frequencies = [item["frequency_ghz"] for item in metrics.values()]
    spread = float(max(peak_frequencies) - min(peak_frequencies))
    gate = evaluate_clean_linearity(
        fit["exponent"], fit["r_squared"], snr, spread, frequency_step
    )
    result = {
        "candidate_frequency_ghz": target,
        "frequency_step_ghz": frequency_step,
        "amplitude_metrics": {f"{amplitude:g}": item for amplitude, item in metrics.items()},
        "power_law": fit,
        "control_power_at_candidate": control_power,
        "snr_5mt": snr,
        "peak_spread_ghz": spread,
        **gate,
    }
    _write_json(ROOT / "results" / "clean_linearity_gate.json", result)
    return result


def _json_safe(value):
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, float) and not np.isfinite(value):
        return "inf" if value > 0 else "nan"
    return value


def _write_json(path: Path, payload):
    path.parent.mkdir(exist_ok=True)
    path.write_text(
        json.dumps(_json_safe(payload), ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("quench", "clean"))
    args = parser.parse_args()
    result = analyze_quench() if args.phase == "quench" else analyze_clean()
    print(json.dumps(_json_safe(result), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
