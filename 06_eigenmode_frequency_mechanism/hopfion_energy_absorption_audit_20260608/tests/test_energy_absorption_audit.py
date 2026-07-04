from pathlib import Path
import sys

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis"))

from energy_absorption_audit import (  # noqa: E402
    FrequencyRecord,
    classify_slope_sign,
    fit_energy_rate,
    rank_peak_records,
    summarize_window_stability,
)


def test_fit_energy_rate_recovers_linear_slope_and_r2():
    t = np.linspace(0.0, 1.0e-9, 101)
    expected_slope = 3.2e-9
    energy = 1.0e-18 + expected_slope * t

    fit = fit_energy_rate(t, energy, 0.2, 0.8)

    assert abs(fit.slope_j_per_s - expected_slope) < 1.0e-20
    assert fit.r2 > 0.999999
    assert fit.n_points == 61


def test_summarize_window_stability_marks_mixed_signs_as_unstable():
    fits = {
        "full": fit_energy_rate(np.array([0.0, 1.0, 2.0]), np.array([0.0, 1.0, 2.0]), 0.0, 1.0),
        "late": fit_energy_rate(np.array([0.0, 1.0, 2.0]), np.array([0.0, -1.0, -2.0]), 0.0, 1.0),
    }

    stability = summarize_window_stability(fits)

    assert stability.sign_label == "mixed"
    assert stability.sign_consistency < 1.0


def test_rank_peak_records_keeps_positive_absorption_and_magnitude_separate():
    records = [
        FrequencyRecord(
            source="srcZ",
            freq_ghz=100.0,
            duration_ns=0.5,
            reference_slope_nj_per_s=-5.0,
            corrected_slope_nj_per_s=-4.0,
            abs_corrected_slope_nj_per_s=4.0,
            r2=0.9,
            sign_label="stable_negative",
            sign_consistency=1.0,
            data_path=Path("negative/table.txt"),
        ),
        FrequencyRecord(
            source="srcZ",
            freq_ghz=200.0,
            duration_ns=0.5,
            reference_slope_nj_per_s=3.0,
            corrected_slope_nj_per_s=2.0,
            abs_corrected_slope_nj_per_s=2.0,
            r2=0.8,
            sign_label="stable_positive",
            sign_consistency=1.0,
            data_path=Path("positive/table.txt"),
        ),
    ]

    peaks = rank_peak_records(records, min_r2=0.5)

    assert peaks["positive_absorption"].freq_ghz == 200.0
    assert peaks["energy_rate_magnitude"].freq_ghz == 100.0


def test_classify_slope_sign_uses_tolerance():
    assert classify_slope_sign(1.0e-4, tolerance=1.0e-3) == "near_zero"
    assert classify_slope_sign(2.0e-3, tolerance=1.0e-3) == "positive"
    assert classify_slope_sign(-2.0e-3, tolerance=1.0e-3) == "negative"
