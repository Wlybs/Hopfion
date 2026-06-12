import sys
import json
from pathlib import Path

import numpy as np


REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO / "hopfion_eigenmode_mechanism_20260612" / "analysis"))

from resonance_analysis import (  # noqa: E402
    accumulate_complex_modes,
    coherent_amplitude,
    estimate_peak_metrics,
    evaluate_mode_localization,
    fit_power_law,
    generate_circular_burst_mx3,
    generate_cw_mx3,
    generate_equilibrated_state_mx3,
    generate_sinc_ringdown_mx3,
    generate_wavefield_mx3,
    ringdown_fft_difference,
    wavevector_power_spectrum,
    topology_mask_from_reference,
)
from generate_simulations import generate_stage1_files  # noqa: E402
from generate_controls import generate_control_files  # noqa: E402
from generate_stage2 import generate_stage2_files  # noqa: E402
from analyze_controls import evaluate_clean_linearity, evaluate_quench_control  # noqa: E402
from analyze_clean_validation import evaluate_spatial_mode_power  # noqa: E402


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


def test_evaluate_mode_localization_accepts_zero_background_power():
    result = evaluate_mode_localization(
        mask_mean_power=2.5,
        outside_mean_power=1.0,
        hopfion_total_power=1.0,
        background_total_power=0.0,
    )

    assert result["passed"] is True
    assert np.isinf(result["background_contrast"])


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


def test_generate_equilibrated_state_uses_target_open_boundaries(tmp_path):
    mx3 = tmp_path / "equilibrate_open.mx3"

    generate_equilibrated_state_mx3(mx3)

    text = mx3.read_text(encoding="utf-8")
    assert "SetPBC" not in text
    assert "alpha = 0.2" in text
    assert "alpha.setRegion(1, 100)" in text
    assert "Relax()" in text
    assert 'saveas(m, "equilibrated_open_boundary")' in text


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


def test_accumulate_complex_modes_localizes_synthetic_oscillation():
    times = np.arange(0.0, 20e-12, 0.05e-12)
    reference = np.zeros((2, 2, 2, 3), dtype=np.float32)
    frames = []
    for time_s in times:
        frame = reference.copy()
        frame[1, 0, 1, 2] = np.cos(2 * np.pi * 100e9 * time_s)
        frames.append(frame)

    modes = accumulate_complex_modes(frames, times, [100.0], reference=reference)
    power = np.sum(np.abs(modes[100.0]) ** 2, axis=-1)

    assert np.unravel_index(np.argmax(power), power.shape) == (1, 0, 1)
    assert power[1, 0, 1] > 100 * np.max(np.delete(power.ravel(), 5))


def test_topology_mask_from_reference_marks_nonuniform_region():
    reference = np.zeros((3, 3, 3, 3), dtype=np.float32)
    reference[..., 2] = 1.0
    reference[1, 1, 1, 2] = -1.0

    mask = topology_mask_from_reference(reference, relative_threshold=0.1)

    assert mask.sum() == 1
    assert mask[1, 1, 1]


def test_generate_cw_mx3_can_be_table_only(tmp_path):
    mx3 = tmp_path / "cw_174GHz.mx3"

    generate_cw_mx3(
        mx3,
        freq_ghz=174.0,
        source_axis="x",
        vib_axis="x",
        B_amp=0.2,
        run_ns=0.3,
        table_dt_ps=0.1,
        save_m=False,
    )

    text = mx3.read_text(encoding="utf-8")
    assert "0.2*sin(174" in text
    assert "tableautosave(0.1e-12)" in text
    assert "autosave(m" not in text


def test_generate_cw_mx3_can_save_center_roi(tmp_path):
    mx3 = tmp_path / "cw_174GHz_roi.mx3"

    generate_cw_mx3(
        mx3,
        freq_ghz=174.0,
        source_axis="x",
        vib_axis="x",
        B_amp=0.2,
        run_ns=0.3,
        table_dt_ps=0.1,
        save_m=False,
        spatial_roi=(26, 74, 26, 74, 26, 74),
        spatial_dt_ps=1.0,
    )

    text = mx3.read_text(encoding="utf-8")
    assert "roi_m := Crop(m, 26, 74, 26, 74, 26, 74)" in text
    assert "autosave(roi_m, 1e-12)" in text
    assert "autosave(m" not in text


def test_generate_wavefield_mx3_controls_source_norm_and_slice(tmp_path):
    plane = tmp_path / "plane.mx3"
    point = tmp_path / "point.mx3"

    generate_wavefield_mx3(plane, geometry="plane", frequency_ghz=700.0)
    generate_wavefield_mx3(point, geometry="point", frequency_ghz=700.0)

    plane_text = plane.read_text(encoding="utf-8")
    point_text = point.read_text(encoding="utf-8")
    assert "DefRegion(7, XRange(-10e-9, -9.5e-9))" in plane_text
    assert "B_amp := 0.1" in plane_text
    assert "DefRegionCell(7, 30, 50, 50)" in point_text
    assert "B_amp := 10" in point_text
    assert "slice_m := CropZ(m, 50, 51)" in plane_text
    assert "autosave(slice_m, 0.02e-12)" in plane_text
    assert "run(30e-12)" in plane_text


def test_wavevector_power_spectrum_recovers_plane_wave_k():
    n = 64
    cell_nm = 0.5
    mode_index = 4
    x = np.arange(n)[:, None]
    field = np.exp(2j * np.pi * mode_index * x / n) * np.ones((1, n))

    spectrum = wavevector_power_spectrum(field, cell_size_nm=cell_nm)

    expected = 2 * np.pi * mode_index / (n * cell_nm)
    assert abs(spectrum["peak_k_rad_per_nm"] - expected) < 0.06
    assert spectrum["spectral_entropy"] < 0.1


def test_coherent_amplitude_recovers_sinusoid_amplitude():
    times = np.arange(0.0, 0.3e-9, 0.05e-12)
    signal = 0.37 * np.sin(2 * np.pi * 174e9 * times + 0.4) + 2.0

    amplitude = coherent_amplitude(
        times,
        signal,
        frequency_ghz=174.0,
        t_start_s=0.1e-9,
    )

    assert abs(amplitude - 0.37) < 1e-3


def test_ringdown_fft_difference_removes_common_quench_mode(tmp_path):
    times = np.arange(0.0, 0.2e-9, 0.05e-12)
    common = 2e-5 * np.sin(2 * np.pi * 174e9 * times)
    driven_only = 4e-6 * np.sin(2 * np.pi * 120e9 * times + 0.3)
    control = tmp_path / "control.txt"
    driven = tmp_path / "driven.txt"

    def write_table(path, mz):
        with path.open("w", encoding="utf-8") as handle:
            handle.write("# t (s)\tmx ()\tmy ()\tmz ()\tE_total (J)\n")
            for time_s, value in zip(times, mz):
                handle.write(f"{time_s}\t0\t0\t{value}\t0\n")

    write_table(control, common)
    write_table(driven, common + driven_only)
    spectrum = ringdown_fft_difference(
        driven,
        control,
        columns=("mz",),
        t_start_s=5e-12,
    )
    metrics = estimate_peak_metrics(
        spectrum["freqs_ghz"], spectrum["psd_mz"], 120.0, 10.0
    )

    frequency_step = spectrum["freqs_ghz"][1] - spectrum["freqs_ghz"][0]
    common_index = np.argmin(np.abs(spectrum["freqs_ghz"] - 174.0))
    assert abs(metrics["frequency_ghz"] - 120.0) <= frequency_step / 2
    assert metrics["power"] > 1000 * spectrum["psd_mz"][common_index]


def test_generate_stage2_is_gated_and_writes_fifteen_runs(tmp_path):
    gate_path = tmp_path / "results" / "stage1_gate.json"
    gate_path.parent.mkdir(parents=True)
    gate_path.write_text(json.dumps({"passed": False}), encoding="utf-8")

    assert generate_stage2_files(tmp_path, gate_path=gate_path) == []
    assert not list((tmp_path / "mx3").glob("cw_*.mx3"))

    gate_path.write_text(json.dumps({"passed": True}), encoding="utf-8")
    manifest = generate_stage2_files(tmp_path, gate_path=gate_path)

    assert len(manifest) == 15
    assert sum(row["kind"] == "cw" for row in manifest) == 11
    assert sum(row["kind"] == "wavefield" for row in manifest) == 4
    assert len(list((tmp_path / "mx3").glob("cw_*.mx3"))) == 11
    assert len(list((tmp_path / "mx3").glob("wavefield_*.mx3"))) == 4
    assert (tmp_path / "results" / "stage2_simulation_manifest.csv").is_file()

    gate_path.write_text(
        json.dumps({"passed": True, "target_frequency_ghz": 120.0}),
        encoding="utf-8",
    )
    shifted = generate_stage2_files(tmp_path, gate_path=gate_path)
    shifted_cw = [row for row in shifted if row["kind"] == "cw"]
    assert any(float(row["frequency_ghz"]) == 120.0 for row in shifted_cw)
    assert not any(float(row["frequency_ghz"]) == 174.0 for row in shifted_cw)


def test_generate_control_files_writes_quench_and_clean_matrix(tmp_path):
    manifest = generate_control_files(tmp_path)

    assert len(manifest) == 13
    assert {row["stage"] for row in manifest} == {
        "quench_control",
        "equilibration",
        "clean_linearity",
        "clean_validation",
    }
    clean_1mt = tmp_path / "mx3" / "clean_Bz_1mT_05ns.mx3"
    text = clean_1mt.read_text(encoding="utf-8")
    assert "equilibrate_open_boundary.out/equilibrated_open_boundary.ovf" in text
    assert (tmp_path / "results" / "control_simulation_manifest.csv").is_file()
    uniform = tmp_path / "mx3" / "clean_spatial_uniform_Bz_5mT.mx3"
    assert "m = uniform(0, 0, 1)" in uniform.read_text(encoding="utf-8")


def test_evaluate_quench_control_detects_drive_independent_mode():
    result = evaluate_quench_control(
        control_amplitude=0.9,
        one_mt_amplitude=1.0,
        five_mt_amplitude=1.02,
    )

    assert result["quench_dominated"] is True
    assert result["control_to_1mt_ratio"] == 0.9


def test_evaluate_clean_linearity_requires_scaling_snr_and_peak_agreement():
    passed = evaluate_clean_linearity(
        exponent=2.05,
        r_squared=0.99,
        snr_5mt=8.0,
        peak_spread_ghz=2.0,
        frequency_step_ghz=2.1,
    )
    failed = evaluate_clean_linearity(
        exponent=0.1,
        r_squared=0.99,
        snr_5mt=8.0,
        peak_spread_ghz=2.0,
        frequency_step_ghz=2.1,
    )

    assert passed["passed"] is True
    assert failed["passed"] is False


def test_evaluate_spatial_mode_power_uses_topology_and_uniform_control():
    mask = np.zeros((3, 3, 3), dtype=bool)
    mask[1, 1, 1] = True
    hopfion_power = np.ones((3, 3, 3))
    hopfion_power[mask] = 4.0
    uniform_power = np.full((3, 3, 3), 0.2)

    result = evaluate_spatial_mode_power(hopfion_power, uniform_power, mask)

    assert result["passed"] is True
    assert result["localization_ratio"] == 4.0
