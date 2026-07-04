from pathlib import Path
import sys

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis"))

from mode_map_analysis import (  # noqa: E402
    deformation_amplitude,
    projection_maps,
    sampling_report,
    summarize_deformation,
)


def test_deformation_amplitude_is_cellwise_vector_norm():
    initial = np.zeros((2, 3, 4, 3), dtype=float)
    current = np.zeros_like(initial)
    current[0, 0, 0] = [3.0, 4.0, 0.0]
    current[1, 2, 3] = [0.0, 0.0, -2.0]

    amp = deformation_amplitude(initial, current)

    assert amp.shape == (2, 3, 4)
    assert amp[0, 0, 0] == 5.0
    assert amp[1, 2, 3] == 2.0


def test_projection_maps_return_mean_and_max_projections():
    amp = np.arange(2 * 3 * 4, dtype=float).reshape(2, 3, 4)

    maps = projection_maps(amp)

    assert maps["xy_mean"].shape == (2, 3)
    assert maps["xz_mean"].shape == (2, 4)
    assert maps["yz_mean"].shape == (3, 4)
    assert maps["xy_mean"][1, 2] == np.mean(amp[1, 2, :])
    assert maps["xz_max"][0, 3] == np.max(amp[0, :, 3])
    assert maps["yz_mean"][2, 1] == np.mean(amp[:, 2, 1])


def test_summarize_deformation_reports_core_localization():
    amp = np.array(
        [
            [[1.0, 2.0], [3.0, 4.0]],
            [[5.0, 6.0], [7.0, 8.0]],
        ]
    )
    core_mask = amp >= 5.0

    summary = summarize_deformation(amp, core_mask)

    assert np.isclose(summary["global_rms"], np.sqrt(np.mean(amp**2)))
    assert np.isclose(summary["core_rms"], np.sqrt(np.mean(np.array([5, 6, 7, 8]) ** 2)))
    assert np.isclose(summary["background_rms"], np.sqrt(np.mean(np.array([1, 2, 3, 4]) ** 2)))
    assert summary["core_energy_fraction"] > 0.7
    assert summary["core_to_background_rms"] > 2.0


def test_sampling_report_flags_existing_runs_as_not_fft_resolvable():
    report = sampling_report(freq_ghz=200.0, dt_ps=10.0)

    assert report["drive_period_ps"] == 5.0
    assert report["samples_per_period"] == 0.5
    assert report["nyquist_ok"] is False
    assert report["mode_fft_reliable"] is False
    assert "stroboscopic" in report["recommended_interpretation"]
