import sys
from pathlib import Path

import numpy as np


REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO / "hopfion_eigenmode_mechanism_20260612" / "analysis"))

from resonance_analysis import (  # noqa: E402
    estimate_peak_metrics,
    evaluate_mode_localization,
    fit_power_law,
    generate_circular_burst_mx3,
    generate_sinc_ringdown_mx3,
)
from generate_simulations import generate_stage1_files  # noqa: E402


def test_estimate_peak_metrics_recovers_lorentzian_fwhm_and_q():
    freqs = np.linspace(130.0, 220.0, 9001)
    center = 174.0
    fwhm = 10.0
    power = 1.0 / (1.0 + 4.0 * ((freqs - center) / fwhm) ** 2)

    metrics = estimate_peak_metrics(freqs, power, target_ghz=174.0)

    assert metrics["status"] == "ok"
    assert abs(metrics["frequency_ghz"] - center) < 0.02
    assert abs(metrics["fwhm_ghz"] - fwhm) < 0.05
    assert abs(metrics["quality_factor"] - center / fwhm) < 0.1


def test_fit_power_law_recovers_quadratic_response():
    amplitudes = np.array([0.001, 0.002, 0.005])
    powers = 7.5 * amplitudes**2

    fit = fit_power_law(amplitudes, powers)

    assert abs(fit["exponent"] - 2.0) < 1e-10
    assert fit["r_squared"] > 0.999999


def test_evaluate_mode_localization_requires_both_thresholds():
    passed = evaluate_mode_localization(
        mask_mean_power=2.1,
        outside_mean_power=1.0,
        hopfion_total_power=3.1,
        background_total_power=1.0,
    )
    failed = evaluate_mode_localization(
        mask_mean_power=4.0,
        outside_mean_power=1.0,
        hopfion_total_power=2.9,
        background_total_power=1.0,
    )

    assert passed["passed"] is True
    assert passed["localization_ratio"] == 2.1
    assert passed["background_contrast"] == 3.1
    assert failed["passed"] is False


def test_generate_spatial_ringdown_saves_only_center_roi(tmp_path):
    mx3 = tmp_path / "spatial_hopfion_Bz.mx3"

    generate_sinc_ringdown_mx3(
        mx3,
        drive_axis="z",
        b0_t=0.005,
        run_ns=0.3,
        table_dt_ps=0.05,
        spatial_roi=(26, 74, 26, 74, 26, 74),
        spatial_dt_ps=0.2,
    )

    text = mx3.read_text(encoding="utf-8")
    assert "roi_m := Crop(m, 26, 74, 26, 74, 26, 74)" in text
    assert "autosave(roi_m, 0.2e-12)" in text
    assert "autosave(m," not in text
    assert "run(0.3e-9)" in text


def test_generate_uniform_background_ringdown_does_not_load_hopfion(tmp_path):
    mx3 = tmp_path / "spatial_uniform_Bz.mx3"

    generate_sinc_ringdown_mx3(
        mx3,
        drive_axis="z",
        uniform_background=True,
        spatial_roi=(26, 74, 26, 74, 26, 74),
        spatial_dt_ps=0.2,
    )

    text = mx3.read_text(encoding="utf-8")
    assert "m = uniform(0, 0, 1)" in text
    assert "m.LoadFile(" not in text


def test_generate_circular_burst_uses_quadrature_components(tmp_path):
    plus = tmp_path / "circular_plus.mx3"
    minus = tmp_path / "circular_minus.mx3"

    generate_circular_burst_mx3(plus, handedness=1)
    generate_circular_burst_mx3(minus, handedness=-1)

    plus_text = plus.read_text(encoding="utf-8")
    minus_text = minus.read_text(encoding="utf-8")
    assert "carrier := 174e9 * 2 * pi" in plus_text
    assert "Vector(envelope*cos(carrier*t), envelope*sin(carrier*t), 0)" in plus_text
    assert "Vector(envelope*cos(carrier*t), -envelope*sin(carrier*t), 0)" in minus_text
    assert "run(0.5e-9)" in plus_text


def test_generate_stage1_files_writes_seven_controlled_runs(tmp_path):
    manifest = generate_stage1_files(tmp_path)

    assert len(manifest) == 7
    assert {row["name"] for row in manifest} == {
        "linear_Bz_1mT_05ns",
        "linear_Bz_2mT_05ns",
        "linewidth_Bz_1mT_10ns",
        "spatial_hopfion_Bz",
        "spatial_uniform_Bz",
        "circular_plus_2mT",
        "circular_minus_2mT",
    }
    assert (tmp_path / "results" / "simulation_manifest.csv").is_file()
    assert len(list((tmp_path / "mx3").glob("*.mx3"))) == 7
