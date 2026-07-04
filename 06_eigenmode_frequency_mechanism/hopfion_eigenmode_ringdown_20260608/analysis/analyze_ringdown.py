#!/usr/bin/env python3
"""Analyze Hopfion weak-pulse ringdown tables and compare with drive windows."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
sys.path.insert(0, str(REPO / "scripts"))

from resonance_analysis import find_fft_peaks, ringdown_fft_from_table  # noqa: E402


RUNS = {
    "Bx": {
        "table": ROOT / "mx3" / "ringdown_sinc_Bx.out" / "table.txt",
        "primary_signals": ("mx", "my"),
        "description": "uniform Bx sinc pulse, in-plane/twist/translation channel",
    },
    "Bz": {
        "table": ROOT / "mx3" / "ringdown_sinc_Bz.out" / "table.txt",
        "primary_signals": ("mz", "E_total"),
        "description": "uniform Bz sinc pulse, axial/breathing channel",
    },
}

DRIVE_WINDOWS = [
    {
        "source": "plane srcX",
        "frequency_ghz": 200.0,
        "status": "candidate resonant coupling from positive energy absorption",
    },
    {
        "source": "plane srcX",
        "frequency_ghz": 1000.0,
        "status": "strong high-frequency drive window",
    },
    {
        "source": "plane srcZ",
        "frequency_ghz": 100.0,
        "status": "strongest absolute energy-rate response, dE/dt<0, not positive absorption",
    },
    {
        "source": "plane srcZ",
        "frequency_ghz": 1100.0,
        "status": "strong high-frequency displacement/control window",
    },
]


def _write_drive_reference(path: Path):
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["source", "frequency_ghz", "status"])
        writer.writeheader()
        writer.writerows(DRIVE_WINDOWS)


def _nearest_peak(peaks, frequency_ghz):
    if not peaks:
        return None
    return min(peaks, key=lambda peak: abs(peak["frequency_ghz"] - frequency_ghz))


def _key_for_signal(signal):
    return f"psd_{signal}"


def analyze(match_tolerance_ghz=10.0):
    results_dir = ROOT / "results"
    figures_dir = ROOT / "figures"
    notes_dir = ROOT / "notes"
    results_dir.mkdir(exist_ok=True)
    figures_dir.mkdir(exist_ok=True)
    notes_dir.mkdir(exist_ok=True)

    _write_drive_reference(results_dir / "drive_response_reference_windows.csv")

    missing = [name for name, cfg in RUNS.items() if not cfg["table"].is_file()]
    if missing:
        note = notes_dir / "ringdown_interpretation.md"
        expected = "\n".join(f"- {RUNS[name]['table']}" for name in missing)
        note.write_text(
            "# Ringdown 本征模谱解读\n\n"
            "## 当前状态\n\n"
            "未完成 FFT 分析，因为以下 Mumax3 table 尚不存在：\n\n"
            f"{expected}\n\n"
            "这表示仿真未运行、运行失败，或输出路径与分析脚本预期不一致。"
            "本结果包不使用任何伪造峰位。\n",
            encoding="utf-8",
        )
        raise FileNotFoundError(f"Missing ringdown tables: {', '.join(missing)}")

    spectra_rows = []
    peak_rows = []
    peak_index = {}
    spectra = {}

    for run_name, cfg in RUNS.items():
        spectrum = ringdown_fft_from_table(
            cfg["table"],
            columns=("mx", "my", "mz", "E_total"),
            t_start_s=5e-12,
        )
        spectra[run_name] = spectrum
        freqs = spectrum["freqs_ghz"]
        for signal in ("mx", "my", "mz", "E_total"):
            key = _key_for_signal(signal)
            if key not in spectrum:
                continue
            for freq, power in zip(freqs, spectrum[key]):
                spectra_rows.append({
                    "run": run_name,
                    "signal": signal,
                    "frequency_ghz": float(freq),
                    "power": float(power),
                })
            peaks = find_fft_peaks(
                freqs,
                spectrum[key],
                min_freq_ghz=5.0,
                max_freq_ghz=1500.0,
                max_peaks=12,
                min_prominence_rel=0.005,
            )
            peak_index[(run_name, signal)] = peaks
            for rank, peak in enumerate(peaks, start=1):
                peak_rows.append({
                    "run": run_name,
                    "signal": signal,
                    "rank": rank,
                    "frequency_ghz": peak["frequency_ghz"],
                    "power": peak["power"],
                    "prominence": peak["prominence"],
                })

    with (results_dir / "ringdown_power_spectra.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["run", "signal", "frequency_ghz", "power"])
        writer.writeheader()
        writer.writerows(spectra_rows)

    with (results_dir / "ringdown_peak_candidates.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["run", "signal", "rank", "frequency_ghz", "power", "prominence"],
        )
        writer.writeheader()
        writer.writerows(peak_rows)

    comparison_rows = []
    for win in DRIVE_WINDOWS:
        run_name = "Bx" if "srcX" in win["source"] else "Bz"
        primary_signals = RUNS[run_name]["primary_signals"]
        signals = ("mx", "my", "mz", "E_total")
        best = None
        best_signal = None
        for signal in signals:
            candidate = _nearest_peak(peak_index.get((run_name, signal), []), win["frequency_ghz"])
            if candidate is None:
                continue
            delta = abs(candidate["frequency_ghz"] - win["frequency_ghz"])
            if best is None or delta < abs(best["frequency_ghz"] - win["frequency_ghz"]):
                best = candidate
                best_signal = signal
        if best is None:
            comparison_rows.append({
                "drive_source": win["source"],
                "drive_frequency_ghz": win["frequency_ghz"],
                "drive_status": win["status"],
                "ringdown_run": run_name,
                "ringdown_signal": "",
                "primary_channel": False,
                "nearest_peak_ghz": "",
                "delta_ghz": "",
                "match_within_10ghz": False,
                "interpretation": "table 平均谱中未检测到候选峰",
            })
            continue
        delta = abs(best["frequency_ghz"] - win["frequency_ghz"])
        matched = delta <= match_tolerance_ghz
        primary = best_signal in primary_signals
        if matched and primary:
            interpretation = "与 ringdown 主通道峰对齐，可作为候选共振耦合"
        elif matched:
            interpretation = "只在次级通道对齐，需要空间模图确认"
        else:
            interpretation = "未通过 10 GHz 对齐判据，暂按强驱动/传播/散射窗口处理"
        comparison_rows.append({
            "drive_source": win["source"],
            "drive_frequency_ghz": win["frequency_ghz"],
            "drive_status": win["status"],
            "ringdown_run": run_name,
            "ringdown_signal": best_signal,
            "primary_channel": primary,
            "nearest_peak_ghz": best["frequency_ghz"],
            "delta_ghz": delta,
            "match_within_10ghz": matched,
            "interpretation": interpretation,
        })

    with (results_dir / "drive_vs_ringdown_comparison.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(comparison_rows[0].keys()))
        writer.writeheader()
        writer.writerows(comparison_rows)

    _plot_spectra(spectra, figures_dir / "ringdown_fft_drive_overlay.png")
    _write_interpretation(peak_index, comparison_rows, notes_dir / "ringdown_interpretation.md")


def _plot_spectra(spectra, out_path):
    fig, axes = plt.subplots(2, 2, figsize=(12, 7), sharex=True)
    panels = [
        ("Bx", "mx", axes[0, 0]),
        ("Bx", "my", axes[0, 1]),
        ("Bz", "mz", axes[1, 0]),
        ("Bz", "E_total", axes[1, 1]),
    ]
    colors = {
        "plane srcX": "#2266aa",
        "plane srcZ": "#aa4422",
    }
    for run_name, signal, ax in panels:
        spectrum = spectra[run_name]
        freqs = spectrum["freqs_ghz"]
        power = spectrum[_key_for_signal(signal)]
        if np.max(power) > 0:
            power = power / np.max(power)
        ax.plot(freqs, power, color="#202020", lw=1.2)
        for win in DRIVE_WINDOWS:
            color = colors[win["source"]]
            ax.axvline(win["frequency_ghz"], color=color, lw=0.9, ls="--", alpha=0.8)
        ax.set_xlim(0, 1500)
        ax.set_ylim(0, 1.05)
        ax.set_title(f"{run_name} pulse: {signal}")
        ax.set_ylabel("normalized FFT power")
        ax.grid(True, alpha=0.25)
    axes[1, 0].set_xlabel("frequency (GHz)")
    axes[1, 1].set_xlabel("frequency (GHz)")
    fig.suptitle("Weak sinc ringdown spectra vs existing spin-wave drive windows")
    fig.tight_layout()
    fig.savefig(out_path, dpi=220)
    plt.close(fig)


def _format_peak_list(peaks, n=5):
    if not peaks:
        return "- 未检测到候选峰"
    return "\n".join(
        f"- {idx}. `{peak['frequency_ghz']:.2f} GHz`, power={peak['power']:.3e}"
        for idx, peak in enumerate(peaks[:n], start=1)
    )


def _write_interpretation(peak_index, comparison_rows, out_path):
    lines = [
        "# Ringdown 本征模谱解读",
        "",
        "## 方法边界",
        "",
        "本分析使用 uniform weak sinc pulse 后的 table-only 自由振荡谱。"
        "峰位是候选固有频率，仍需空间分辨模图来命名为 translation/twist/breathing 等具体模式。",
        "",
        "## 主通道候选峰",
        "",
        "### Bx pulse: `m_x/m_y`",
        "",
        _format_peak_list(peak_index.get(("Bx", "mx"), [])),
        "",
        _format_peak_list(peak_index.get(("Bx", "my"), [])),
        "",
        "注：Bx 的 `m_x/m_y` 最高功率集中在 `6-8 GHz` 的低频趋势/漂移段，"
        "没有形成可用于本征频率命名的离散峰；同一 Bx run 的 `m_z/E_total` 中出现 "
        "`173.66 GHz` 主峰，但它不是 Bx 面内主通道峰。",
        "",
        "### Bz pulse: `m_z/E_total`",
        "",
        _format_peak_list(peak_index.get(("Bz", "mz"), [])),
        "",
        _format_peak_list(peak_index.get(("Bz", "E_total"), [])),
        "",
        "## 与现有自旋波驱动窗口的对照",
        "",
    ]
    for row in comparison_rows:
        nearest = row["nearest_peak_ghz"]
        if nearest == "":
            nearest_text = "无候选峰"
        else:
            nearest_text = f"{float(nearest):.2f} GHz, delta={float(row['delta_ghz']):.2f} GHz"
        lines.append(
            f"- `{row['drive_source']} {float(row['drive_frequency_ghz']):.0f} GHz`: "
            f"{nearest_text}; 判定：{row['interpretation']}。"
        )
    lines.extend([
        "",
        "## 论文措辞建议",
        "",
        "若某个驱动峰与 ringdown 峰在 `10 GHz` 内对齐，可写为候选共振耦合频率；"
        "若没有对齐，应写为强驱动、传播或散射窗口。"
        "`srcZ 100 GHz` 即使在位移或能量率上显著，也不能在没有正吸收和 ringdown 对齐前称为本征频率。",
    ])
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--match-tolerance-ghz", type=float, default=10.0)
    args = parser.parse_args()
    analyze(match_tolerance_ghz=args.match_tolerance_ghz)


if __name__ == "__main__":
    main()
