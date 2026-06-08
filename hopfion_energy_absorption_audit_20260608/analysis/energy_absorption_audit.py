#!/usr/bin/env python3
"""Audit Hopfion spin-wave energy-rate spectra from Mumax3 table files."""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


DEFAULT_PROJECT_ROOT = Path("/mnt/d/Research/Hopfion")
DEFAULT_FREQ_ROOT = (
    DEFAULT_PROJECT_ROOT
    / "20260105_frustrated_fm/spin_wave_dynamics/freq_sweep/plane_wave"
)
DEFAULT_BACKGROUND_TABLE = (
    DEFAULT_PROJECT_ROOT
    / "20260105_frustrated_fm/centered_stability_test/stability_Ku10k.out/table.txt"
)
DEFAULT_OUTDIR = DEFAULT_PROJECT_ROOT / "hopfion_energy_absorption_audit_20260608"

WINDOWS = (
    ("00_100", 0.0, 1.0),
    ("10_100", 0.1, 1.0),
    ("20_100", 0.2, 1.0),
    ("30_100", 0.3, 1.0),
    ("40_100", 0.4, 1.0),
    ("50_100", 0.5, 1.0),
)
REFERENCE_WINDOW = "30_100"


@dataclass(frozen=True)
class FitResult:
    label: str
    start_frac: float
    end_frac: float
    slope_j_per_s: float
    intercept_j: float
    r2: float
    n_points: int
    t_start_ns: float
    t_end_ns: float
    delta_e_j: float


@dataclass(frozen=True)
class WindowStability:
    sign_label: str
    sign_consistency: float
    median_slope_nj_per_s: float
    n_windows: int


@dataclass(frozen=True)
class FrequencyRecord:
    source: str
    freq_ghz: float
    duration_ns: float
    reference_slope_nj_per_s: float
    corrected_slope_nj_per_s: float
    abs_corrected_slope_nj_per_s: float
    r2: float
    sign_label: str
    sign_consistency: float
    data_path: Path
    dataset: str = ""
    preferred: bool = True
    background_slope_nj_per_s: float = 0.0
    n_points: int = 0
    delta_e_aj: float = 0.0


def load_mumax_table(path: Path) -> tuple[np.ndarray, np.ndarray]:
    """Return time and E_total arrays from a Mumax3 table.txt file."""
    data = np.loadtxt(path, skiprows=1)
    if data.ndim != 2 or data.shape[1] < 5:
        raise ValueError(f"Expected at least 5 columns in {path}")
    return data[:, 0], data[:, 4]


def fit_energy_rate(
    t_s: np.ndarray,
    energy_j: np.ndarray,
    start_frac: float,
    end_frac: float,
    label: str = "fit",
) -> FitResult:
    """Fit dE/dt over a fractional time window."""
    if not 0.0 <= start_frac < end_frac <= 1.0:
        raise ValueError("fit window fractions must satisfy 0 <= start < end <= 1")
    if t_s.size != energy_j.size:
        raise ValueError("time and energy arrays must have the same length")
    t_min = float(t_s[0])
    t_max = float(t_s[-1])
    t0 = t_min + (t_max - t_min) * start_frac
    t1 = t_min + (t_max - t_min) * end_frac
    mask = (t_s >= t0) & (t_s <= t1)
    if int(mask.sum()) < 3:
        raise ValueError(f"Need at least 3 points for window {label}")

    t_sel = t_s[mask]
    e_sel = energy_j[mask]
    slope, intercept = np.polyfit(t_sel, e_sel, 1)
    e_pred = slope * t_sel + intercept
    ss_res = float(np.sum((e_sel - e_pred) ** 2))
    ss_tot = float(np.sum((e_sel - np.mean(e_sel)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0
    return FitResult(
        label=label,
        start_frac=start_frac,
        end_frac=end_frac,
        slope_j_per_s=float(slope),
        intercept_j=float(intercept),
        r2=float(r2),
        n_points=int(mask.sum()),
        t_start_ns=float(t_sel[0] * 1e9),
        t_end_ns=float(t_sel[-1] * 1e9),
        delta_e_j=float(e_sel[-1] - e_sel[0]),
    )


def fit_energy_rate_absolute(
    t_s: np.ndarray,
    energy_j: np.ndarray,
    t_start_s: float,
    t_end_s: float,
    label: str = "fit",
) -> FitResult:
    """Fit dE/dt over an absolute time window."""
    if t_start_s >= t_end_s:
        raise ValueError("absolute fit window must satisfy start < end")
    mask = (t_s >= t_start_s) & (t_s <= t_end_s)
    if int(mask.sum()) < 3:
        raise ValueError(f"Need at least 3 points for absolute window {label}")
    t_sel = t_s[mask]
    e_sel = energy_j[mask]
    slope, intercept = np.polyfit(t_sel, e_sel, 1)
    e_pred = slope * t_sel + intercept
    ss_res = float(np.sum((e_sel - e_pred) ** 2))
    ss_tot = float(np.sum((e_sel - np.mean(e_sel)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0
    return FitResult(
        label=label,
        start_frac=0.0,
        end_frac=1.0,
        slope_j_per_s=float(slope),
        intercept_j=float(intercept),
        r2=float(r2),
        n_points=int(mask.sum()),
        t_start_ns=float(t_sel[0] * 1e9),
        t_end_ns=float(t_sel[-1] * 1e9),
        delta_e_j=float(e_sel[-1] - e_sel[0]),
    )


def classify_slope_sign(slope_nj_per_s: float, tolerance: float = 0.05) -> str:
    """Classify an energy-rate slope in nJ/s."""
    if abs(slope_nj_per_s) < tolerance:
        return "near_zero"
    return "positive" if slope_nj_per_s > 0 else "negative"


def summarize_window_stability(
    fits: dict[str, FitResult], tolerance_nj_per_s: float = 0.05
) -> WindowStability:
    """Summarize whether signs remain stable across fit windows."""
    labels = [
        classify_slope_sign(fit.slope_j_per_s * 1e9, tolerance=tolerance_nj_per_s)
        for fit in fits.values()
    ]
    counts = {label: labels.count(label) for label in set(labels)}
    if "positive" in counts and "negative" in counts:
        sign_label = "mixed"
    elif "positive" in counts:
        sign_label = "stable_positive"
    elif "negative" in counts:
        sign_label = "stable_negative"
    else:
        sign_label = "near_zero"
    consistency = max(counts.values()) / len(labels) if labels else 0.0
    return WindowStability(
        sign_label=sign_label,
        sign_consistency=float(consistency),
        median_slope_nj_per_s=float(
            np.median([fit.slope_j_per_s * 1e9 for fit in fits.values()])
        ),
        n_windows=len(labels),
    )


def rank_peak_records(
    records: Iterable[FrequencyRecord], min_r2: float = 0.5
) -> dict[str, FrequencyRecord | None]:
    """Return separate signed-positive and absolute-magnitude peak records."""
    qualified = [record for record in records if record.r2 >= min_r2]
    positive = [record for record in qualified if record.corrected_slope_nj_per_s > 0]
    magnitude = [record for record in qualified if record.abs_corrected_slope_nj_per_s > 0]
    return {
        "positive_absorption": max(
            positive, key=lambda record: record.corrected_slope_nj_per_s, default=None
        ),
        "energy_rate_magnitude": max(
            magnitude,
            key=lambda record: record.abs_corrected_slope_nj_per_s,
            default=None,
        ),
    }


def discover_table_paths(freq_root: Path) -> list[dict[str, object]]:
    """Discover plane-wave frequency-sweep table files."""
    entries: list[dict[str, object]] = []
    srcx_paths: dict[float, list[Path]] = {}
    for path in sorted((freq_root / "srcX").glob("*/*GHz.out/table.txt")):
        freq = float(path.parent.name.split("f")[-1].split("GHz")[0])
        srcx_paths.setdefault(freq, []).append(path)
    for freq, paths in srcx_paths.items():
        preferred = max(paths, key=lambda p: 1 if "/05ns/" in p.as_posix() else 0)
        for path in paths:
            entries.append(
                {
                    "source": "srcX",
                    "freq_ghz": freq,
                    "dataset": "srcX_05ns" if "/05ns/" in path.as_posix() else "srcX_02ns",
                    "path": path,
                    "preferred": path == preferred,
                }
            )

    for path in sorted((freq_root / "srcZ").glob("*GHz.out/table.txt")):
        name = path.parent.name
        freq = float(name.split("_f")[-1].split("GHz")[0])
        entries.append(
            {
                "source": "srcZ",
                "freq_ghz": freq,
                "dataset": "srcZ",
                "path": path,
                "preferred": True,
            }
        )
    return sorted(entries, key=lambda e: (str(e["source"]), float(e["freq_ghz"]), str(e["dataset"])))


def fit_background_for_run(
    background_t_s: np.ndarray | None,
    background_e_j: np.ndarray | None,
    duration_s: float,
    start_frac: float,
    end_frac: float,
) -> FitResult | None:
    """Fit background over the same absolute time span as a driven run."""
    if background_t_s is None or background_e_j is None:
        return None
    t0 = duration_s * start_frac
    t1 = duration_s * end_frac
    if t1 > float(background_t_s[-1]):
        t1 = float(background_t_s[-1])
    if t0 >= t1:
        return None
    return fit_energy_rate_absolute(background_t_s, background_e_j, t0, t1, "background")


def analyze_one_entry(
    entry: dict[str, object],
    background_t_s: np.ndarray | None,
    background_e_j: np.ndarray | None,
) -> tuple[FrequencyRecord, list[dict[str, object]]]:
    """Analyze all fit windows for one frequency entry."""
    path = Path(entry["path"])
    t_s, energy_j = load_mumax_table(path)
    duration_s = float(t_s[-1] - t_s[0])
    fits = {
        label: fit_energy_rate(t_s, energy_j, start, end, label=label)
        for label, start, end in WINDOWS
    }
    stability = summarize_window_stability(fits)
    reference = fits[REFERENCE_WINDOW]
    background = fit_background_for_run(
        background_t_s,
        background_e_j,
        duration_s,
        reference.start_frac,
        reference.end_frac,
    )
    background_slope_nj = background.slope_j_per_s * 1e9 if background else 0.0
    reference_slope_nj = reference.slope_j_per_s * 1e9
    corrected_slope_nj = reference_slope_nj - background_slope_nj
    record = FrequencyRecord(
        source=str(entry["source"]),
        freq_ghz=float(entry["freq_ghz"]),
        duration_ns=duration_s * 1e9,
        reference_slope_nj_per_s=reference_slope_nj,
        corrected_slope_nj_per_s=corrected_slope_nj,
        abs_corrected_slope_nj_per_s=abs(corrected_slope_nj),
        r2=reference.r2,
        sign_label=stability.sign_label,
        sign_consistency=stability.sign_consistency,
        data_path=path,
        dataset=str(entry["dataset"]),
        preferred=bool(entry["preferred"]),
        background_slope_nj_per_s=background_slope_nj,
        n_points=reference.n_points,
        delta_e_aj=reference.delta_e_j * 1e18,
    )

    rows = []
    for label, fit in fits.items():
        background_fit = fit_background_for_run(
            background_t_s, background_e_j, duration_s, fit.start_frac, fit.end_frac
        )
        background_fit_slope = (
            background_fit.slope_j_per_s * 1e9 if background_fit else 0.0
        )
        rows.append(
            {
                "source": record.source,
                "freq_ghz": record.freq_ghz,
                "dataset": record.dataset,
                "preferred": record.preferred,
                "window": label,
                "start_frac": fit.start_frac,
                "end_frac": fit.end_frac,
                "duration_ns": record.duration_ns,
                "slope_nj_per_s": fit.slope_j_per_s * 1e9,
                "background_slope_nj_per_s": background_fit_slope,
                "corrected_slope_nj_per_s": fit.slope_j_per_s * 1e9 - background_fit_slope,
                "r2": fit.r2,
                "n_points": fit.n_points,
                "delta_e_aj": fit.delta_e_j * 1e18,
                "data_path": path.as_posix(),
            }
        )
    return record, rows


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def record_to_row(record: FrequencyRecord) -> dict[str, object]:
    row = asdict(record)
    row["data_path"] = record.data_path.as_posix()
    return row


def plot_spectrum(records: list[FrequencyRecord], outpath: Path) -> None:
    preferred = [record for record in records if record.preferred]
    fig, axes = plt.subplots(2, 1, figsize=(11, 8), constrained_layout=True)
    for ax, source, color_pos, color_neg in [
        (axes[0], "srcX", "#2f78b7", "#b64b4b"),
        (axes[1], "srcZ", "#d88921", "#7b5ab6"),
    ]:
        subset = sorted(
            [record for record in preferred if record.source == source],
            key=lambda record: record.freq_ghz,
        )
        x = [record.freq_ghz for record in subset]
        y = [record.corrected_slope_nj_per_s for record in subset]
        colors = [color_pos if value >= 0 else color_neg for value in y]
        widths = 40 if source == "srcX" else 28
        ax.bar(x, y, width=widths, color=colors, alpha=0.82, edgecolor="black", linewidth=0.4)
        ax.axhline(0.0, color="black", linewidth=0.8)
        ax.set_title(f"{source}: background-corrected dE/dt")
        ax.set_ylabel("dE/dt (nJ/s)")
        ax.grid(axis="y", alpha=0.25)
        peaks = rank_peak_records(subset)
        for key, marker in [
            ("positive_absorption", "o"),
            ("energy_rate_magnitude", "s"),
        ]:
            peak = peaks[key]
            if peak is None:
                continue
            ax.scatter(
                [peak.freq_ghz],
                [peak.corrected_slope_nj_per_s],
                marker=marker,
                s=64,
                color="white",
                edgecolor="black",
                linewidth=1.0,
                zorder=5,
            )
        peak_lines = []
        positive = peaks["positive_absorption"]
        magnitude = peaks["energy_rate_magnitude"]
        if positive is None:
            peak_lines.append("positive peak: none")
        else:
            peak_lines.append(f"positive peak: {positive.freq_ghz:.0f} GHz")
        if magnitude is None:
            peak_lines.append("magnitude peak: none")
        elif positive is not None and magnitude.freq_ghz == positive.freq_ghz:
            peak_lines[-1] += " (also magnitude)"
        else:
            peak_lines.append(f"magnitude peak: {magnitude.freq_ghz:.0f} GHz")
        ax.text(
            0.72,
            0.92,
            "\n".join(peak_lines),
            transform=ax.transAxes,
            fontsize=8,
            va="top",
            ha="left",
            bbox={"facecolor": "white", "edgecolor": "0.7", "alpha": 0.82, "pad": 4},
        )
    axes[1].set_xlabel("Frequency (GHz)")
    outpath.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(outpath, dpi=220)
    plt.close(fig)


def plot_trace_examples(records: list[FrequencyRecord], outpath: Path) -> None:
    selected = {
        ("srcX", 100.0),
        ("srcX", 200.0),
        ("srcX", 1000.0),
        ("srcZ", 100.0),
        ("srcZ", 1100.0),
        ("srcZ", 1500.0),
    }
    subset = [
        record
        for record in records
        if record.preferred and (record.source, record.freq_ghz) in selected
    ]
    fig, axes = plt.subplots(2, 3, figsize=(12, 6), constrained_layout=True)
    for ax, record in zip(axes.ravel(), subset):
        t_s, energy_j = load_mumax_table(record.data_path)
        fit = fit_energy_rate(t_s, energy_j, 0.3, 1.0, label="30_100")
        rel_energy_aj = (energy_j - energy_j[0]) * 1e18
        fit_line_aj = ((fit.slope_j_per_s * t_s + fit.intercept_j) - energy_j[0]) * 1e18
        ax.plot(t_s * 1e9, rel_energy_aj, color="#2b2b2b", linewidth=1.1)
        ax.plot(t_s * 1e9, fit_line_aj, color="#c43c39", linewidth=1.0)
        ax.axvspan(fit.t_start_ns, fit.t_end_ns, color="#c43c39", alpha=0.08)
        ax.set_title(f"{record.source} {record.freq_ghz:.0f} GHz")
        ax.set_xlabel("t (ns)")
        ax.set_ylabel("Delta E (aJ)")
        ax.grid(alpha=0.2)
    for ax in axes.ravel()[len(subset) :]:
        ax.axis("off")
    outpath.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(outpath, dpi=220)
    plt.close(fig)


def write_summary(
    records: list[FrequencyRecord],
    outpath: Path,
    background_path: Path | None,
) -> None:
    preferred = [record for record in records if record.preferred]
    lines = [
        "# Hopfion plane-wave energy-rate audit",
        "",
        "Date: 2026-06-08",
        "",
        "## Method",
        "",
        "- Quantity: linear-fit energy rate `dE_total/dt` from Mumax3 `table.txt`.",
        "- Reference fit window: 30%-100% of each simulation time span.",
        "- Robustness check: six windows from full range to 50%-100%.",
        "- Background correction: subtract same-window rate from the no-drive centered Ku10k stability run.",
        "- Interpretation rule: positive corrected slope is treated as signed energy absorption; negative slope is reported as energy-rate response, not automatically called absorption.",
        "",
        "## Data coverage",
        "",
        f"- Total table entries analyzed: {len(records)}",
        f"- Preferred spectrum entries: {len(preferred)}",
        f"- Background table: `{background_path}`" if background_path else "- Background table: not used",
        "",
        "## Peak summary",
        "",
    ]
    for source in ["srcX", "srcZ"]:
        subset = [record for record in preferred if record.source == source]
        peaks = rank_peak_records(subset)
        lines.append(f"### {source}")
        positive = peaks["positive_absorption"]
        magnitude = peaks["energy_rate_magnitude"]
        if positive:
            lines.append(
                f"- Strongest positive corrected energy absorption: {positive.freq_ghz:.0f} GHz "
                f"({positive.corrected_slope_nj_per_s:.3f} nJ/s, R2={positive.r2:.3f}, "
                f"{positive.sign_label})."
            )
        else:
            lines.append("- No robust positive corrected energy-absorption peak with R2 >= 0.5.")
        if magnitude:
            lines.append(
                f"- Strongest absolute energy-rate response: {magnitude.freq_ghz:.0f} GHz "
                f"({magnitude.corrected_slope_nj_per_s:.3f} nJ/s signed, "
                f"|rate|={magnitude.abs_corrected_slope_nj_per_s:.3f} nJ/s, "
                f"R2={magnitude.r2:.3f}, {magnitude.sign_label})."
            )
        else:
            lines.append("- No robust absolute energy-rate response with R2 >= 0.5.")
        lines.append("")

    lines.extend(
        [
            "## Paper-facing interpretation",
            "",
            "- `srcX` can support a low-frequency positive absorption channel if its signed positive peak remains aligned with displacement response.",
            "- `srcZ` negative fitted rates should be described cautiously as driven energy-rate response or relaxation-assisted motion unless a proper drive-minus-no-drive power balance proves net positive absorption.",
            "- Displacement peaks at high frequency should not be renamed eigenfrequencies from this analysis alone.",
            "",
            "## Output files",
            "",
            "- `results/energy_absorption_audit_records.csv`: one row per frequency table.",
            "- `results/energy_absorption_window_sensitivity.csv`: one row per frequency and fit window.",
            "- `figures/energy_absorption_audit_spectrum.png`: signed corrected spectrum.",
            "- `figures/energy_trace_fit_examples.png`: representative energy traces and fit windows.",
        ]
    )
    outpath.parent.mkdir(parents=True, exist_ok=True)
    outpath.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_audit(freq_root: Path, background_table: Path | None, outdir: Path) -> list[FrequencyRecord]:
    background_t_s = None
    background_e_j = None
    if background_table and background_table.exists():
        background_t_s, background_e_j = load_mumax_table(background_table)
    entries = discover_table_paths(freq_root)
    records: list[FrequencyRecord] = []
    window_rows: list[dict[str, object]] = []
    for entry in entries:
        record, rows = analyze_one_entry(entry, background_t_s, background_e_j)
        records.append(record)
        window_rows.extend(rows)

    result_dir = outdir / "results"
    figure_dir = outdir / "figures"
    write_csv(
        result_dir / "energy_absorption_audit_records.csv",
        [record_to_row(record) for record in records],
    )
    write_csv(result_dir / "energy_absorption_window_sensitivity.csv", window_rows)
    plot_spectrum(records, figure_dir / "energy_absorption_audit_spectrum.png")
    plot_trace_examples(records, figure_dir / "energy_trace_fit_examples.png")
    write_summary(records, outdir / "README.md", background_table)
    return records


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freq-root", type=Path, default=DEFAULT_FREQ_ROOT)
    parser.add_argument("--background-table", type=Path, default=DEFAULT_BACKGROUND_TABLE)
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    records = run_audit(args.freq_root, args.background_table, args.outdir)
    preferred = [record for record in records if record.preferred]
    print(f"Analyzed {len(records)} table entries ({len(preferred)} preferred spectrum points).")
    for source in ["srcX", "srcZ"]:
        peaks = rank_peak_records([record for record in preferred if record.source == source])
        positive = peaks["positive_absorption"]
        magnitude = peaks["energy_rate_magnitude"]
        pos_text = "none" if positive is None else f"{positive.freq_ghz:.0f} GHz"
        mag_text = "none" if magnitude is None else f"{magnitude.freq_ghz:.0f} GHz"
        print(f"{source}: positive_absorption={pos_text}; magnitude={mag_text}")


if __name__ == "__main__":
    main()
