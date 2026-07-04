import sys
from pathlib import Path

import numpy as np


REPO = Path(__file__).resolve().parents[1].parent
sys.path.insert(0, str(REPO / "scripts"))

from resonance_analysis import (  # noqa: E402
    find_fft_peaks,
    generate_sinc_ringdown_mx3,
    ringdown_fft_from_table,
)


def _write_synthetic_table(path, freq_ghz=200.0, dt_ps=0.05, duration_ps=100.0):
    t = np.arange(0.0, duration_ps * 1e-12, dt_ps * 1e-12)
    omega = 2 * np.pi * freq_ghz * 1e9
    mx = 0.01 * np.sin(omega * t)
    my = 0.005 * np.cos(omega * t)
    mz = 0.002 * np.sin(2 * omega * t)
    energy = 1e-18 * np.cos(omega * t)
    data = np.column_stack([t, mx, my, mz, energy])
    header = "# t (s)\tmx ()\tmy ()\tmz ()\tE_total (J)"
    np.savetxt(path, data, header=header, comments="")


def test_ringdown_fft_from_table_recovers_known_frequency(tmp_path):
    table = tmp_path / "table.txt"
    _write_synthetic_table(table, freq_ghz=200.0)

    spectrum = ringdown_fft_from_table(table, columns=("mx", "my", "mz", "E_total"))

    peak_mx = spectrum["freqs_ghz"][np.argmax(spectrum["psd_mx"])]
    peak_mz = spectrum["freqs_ghz"][np.argmax(spectrum["psd_mz"])]

    assert abs(peak_mx - 200.0) <= 10.0
    assert abs(peak_mz - 400.0) <= 10.0
    assert "psd_E_total" in spectrum


def test_find_fft_peaks_returns_ranked_frequency_candidates(tmp_path):
    table = tmp_path / "table.txt"
    _write_synthetic_table(table, freq_ghz=200.0)
    spectrum = ringdown_fft_from_table(table, columns=("mx",))

    peaks = find_fft_peaks(
        spectrum["freqs_ghz"],
        spectrum["psd_mx"],
        min_freq_ghz=50.0,
        max_freq_ghz=600.0,
        max_peaks=3,
        min_prominence_rel=0.05,
    )

    assert peaks
    assert abs(peaks[0]["frequency_ghz"] - 200.0) <= 10.0
    assert peaks[0]["power"] >= peaks[-1]["power"]


def test_generate_sinc_ringdown_mx3_is_table_only_and_axis_selective(tmp_path):
    mx3 = tmp_path / "ringdown_sinc_Bx.mx3"

    generate_sinc_ringdown_mx3(
        mx3,
        drive_axis="x",
        cutoff_ghz=2000.0,
        b0_t=0.005,
        t0_ps=2.37,
        run_ns=0.5,
        table_dt_ps=0.05,
    )

    text = mx3.read_text(encoding="utf-8")

    assert "B0 := 0.005" in text
    assert "fc := 2000e9" in text
    assert "t0 := 2.37e-12" in text
    assert "B_ext = Vector(pulse, 0, 0)" in text
    assert "tableautosave(0.05e-12)" in text
    assert "TableAdd(E_Total)" in text
    assert "run(0.5e-9)" in text
    assert "autosave(m" not in text
    assert "DefRegion(7" not in text
