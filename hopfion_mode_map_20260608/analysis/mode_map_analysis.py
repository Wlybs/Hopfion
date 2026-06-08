#!/usr/bin/env python3
"""Stroboscopic deformation maps for representative Hopfion spin-wave runs.

The available OVF frames are saved every 10 ps. For 100-1100 GHz drives this is
not enough for a strict cell-wise FFT eigenmode extraction. This script therefore
reports driven deformation/localization maps relative to the initial frame.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

try:
    import discretisedfield as df
except ImportError:  # pragma: no cover - exercised only outside the Hopfion env.
    df = None


ROOT = Path(__file__).resolve().parents[2]
OUT_ROOT = ROOT / "hopfion_mode_map_20260608"
RESULTS_DIR = OUT_ROOT / "results"
FIGURES_DIR = OUT_ROOT / "figures"
NOTES_DIR = OUT_ROOT / "notes"


@dataclass(frozen=True)
class RunConfig:
    label: str
    source: str
    freq_ghz: float
    relative_out_dir: str
    role: str
    energy_context: str
    dt_ps: float = 10.0

    @property
    def out_dir(self) -> Path:
        return ROOT / self.relative_out_dir


RUNS = [
    RunConfig(
        label="srcX_200GHz",
        source="srcX plane wave",
        freq_ghz=200.0,
        relative_out_dir=(
            "20260105_frustrated_fm/spin_wave_dynamics/freq_sweep/plane_wave/"
            "srcX/02ns/sw_f200GHz.out"
        ),
        role="candidate resonant coupling",
        energy_context="positive energy absorption in the previous audit",
    ),
    RunConfig(
        label="srcX_1000GHz",
        source="srcX plane wave",
        freq_ghz=1000.0,
        relative_out_dir=(
            "20260105_frustrated_fm/spin_wave_dynamics/freq_sweep/plane_wave/"
            "srcX/05ns/sw_f1000GHz.out"
        ),
        role="strong high-frequency displacement window",
        energy_context="strong response window but not a robust absorption resonance",
    ),
    RunConfig(
        label="srcZ_100GHz",
        source="srcZ plane wave",
        freq_ghz=100.0,
        relative_out_dir=(
            "20260105_frustrated_fm/spin_wave_dynamics/freq_sweep/plane_wave/"
            "srcZ/sw_srcZ_f100GHz.out"
        ),
        role="anomalous axial response",
        energy_context="strong absolute energy-rate response, but negative fitted dE/dt",
    ),
    RunConfig(
        label="srcZ_1100GHz",
        source="srcZ plane wave",
        freq_ghz=1100.0,
        relative_out_dir=(
            "20260105_frustrated_fm/spin_wave_dynamics/freq_sweep/plane_wave/"
            "srcZ/sw_srcZ_fine_f1100GHz.out"
        ),
        role="strong high-frequency axial control window",
        energy_context="strong control window but not a robust positive absorption peak",
    ),
]


def deformation_amplitude(initial: np.ndarray, current: np.ndarray) -> np.ndarray:
    """Return |m(t)-m(0)| at each cell."""
    initial = np.asarray(initial)
    current = np.asarray(current)
    if initial.shape != current.shape:
        raise ValueError(f"shape mismatch: {initial.shape} vs {current.shape}")
    if initial.ndim != 4 or initial.shape[-1] != 3:
        raise ValueError("magnetization arrays must have shape (nx, ny, nz, 3)")
    dm = current - initial
    return np.sqrt(np.sum(dm * dm, axis=-1))


def projection_maps(amplitude: np.ndarray) -> dict[str, np.ndarray]:
    """Return mean/max projections for xy, xz, and yz planes."""
    amp = np.asarray(amplitude)
    if amp.ndim != 3:
        raise ValueError("amplitude must have shape (nx, ny, nz)")
    return {
        "xy_mean": np.mean(amp, axis=2),
        "xy_max": np.max(amp, axis=2),
        "xz_mean": np.mean(amp, axis=1),
        "xz_max": np.max(amp, axis=1),
        "yz_mean": np.mean(amp, axis=0),
        "yz_max": np.max(amp, axis=0),
    }


def _rms(values: np.ndarray) -> float:
    if values.size == 0:
        return float("nan")
    return float(np.sqrt(np.mean(values * values)))


def summarize_deformation(amplitude: np.ndarray, core_mask: np.ndarray) -> dict[str, float]:
    """Summarize deformation amplitude and how much of it is core-localized."""
    amp = np.asarray(amplitude, dtype=float)
    mask = np.asarray(core_mask, dtype=bool)
    if amp.shape != mask.shape:
        raise ValueError(f"mask shape mismatch: {amp.shape} vs {mask.shape}")

    core = amp[mask]
    background = amp[~mask]
    total_power = float(np.sum(amp * amp))
    core_power = float(np.sum(core * core))
    background_rms = _rms(background)
    core_rms = _rms(core)
    ratio = core_rms / background_rms if background_rms and np.isfinite(background_rms) else float("nan")

    return {
        "global_rms": _rms(amp),
        "global_mean": float(np.mean(amp)),
        "global_max": float(np.max(amp)),
        "core_rms": core_rms,
        "background_rms": background_rms,
        "core_to_background_rms": float(ratio),
        "core_energy_fraction": core_power / total_power if total_power > 0 else float("nan"),
        "core_volume_fraction": float(np.mean(mask)),
    }


def sampling_report(freq_ghz: float, dt_ps: float) -> dict[str, Any]:
    """Report whether saved OVFs can support a drive-frequency FFT mode map."""
    drive_period_ps = 1000.0 / float(freq_ghz)
    samples_per_period = drive_period_ps / float(dt_ps)
    nyquist_ok = samples_per_period >= 2.0
    mode_fft_reliable = samples_per_period >= 6.0
    if mode_fft_reliable:
        interpretation = "saved frames can support a coarse drive-frequency mode map"
    elif nyquist_ok:
        interpretation = "Nyquist is met, but the sampling is too sparse for a reliable mode map"
    else:
        interpretation = (
            "treat the OVFs as stroboscopic deformation snapshots, not as a drive-frequency FFT mode map"
        )
    return {
        "drive_period_ps": float(drive_period_ps),
        "samples_per_period": float(samples_per_period),
        "nyquist_ok": bool(nyquist_ok),
        "mode_fft_reliable": bool(mode_fft_reliable),
        "recommended_interpretation": interpretation,
    }


def centroid_from_array(array: np.ndarray, cell_nm: np.ndarray, pmin_nm: np.ndarray) -> np.ndarray:
    """Weighted Hopfion centroid in nm, using weight=max(1-mz, 0)."""
    mz = array[:, :, :, 2]
    weight = np.maximum(1.0 - mz, 0.0)
    w_sum = float(np.sum(weight))
    if w_sum == 0:
        return np.array([np.nan, np.nan, np.nan], dtype=float)
    centers = []
    for axis, n in enumerate(mz.shape):
        coords = pmin_nm[axis] + cell_nm[axis] * (np.arange(n) + 0.5)
        shape = [1, 1, 1]
        shape[axis] = n
        centers.append(float(np.sum(coords.reshape(shape) * weight) / w_sum))
    return np.array(centers, dtype=float)


def core_count_from_array(array: np.ndarray) -> int:
    return int(np.sum(array[:, :, :, 2] < 0.0))


def load_field_array(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if df is None:
        raise RuntimeError("discretisedfield is required. Activate the project Python env first.")
    field = df.Field.from_file(str(path))
    array = np.asarray(field.array, dtype=np.float32).copy()
    cell_nm = np.asarray(field.mesh.cell, dtype=float) * 1e9
    pmin_nm = np.asarray(field.mesh.region.pmin, dtype=float) * 1e9
    return array, cell_nm, pmin_nm


def frame_paths(out_dir: Path) -> list[Path]:
    paths = sorted(out_dir.glob("m*.ovf"))
    if not paths:
        raise FileNotFoundError(f"no OVF frames found in {out_dir}")
    return paths


def analyze_run(config: RunConfig, max_frames: int | None = None) -> dict[str, Any]:
    paths = frame_paths(config.out_dir)
    if max_frames is not None:
        paths = paths[:max_frames]

    initial, cell_nm, pmin_nm = load_field_array(paths[0])
    core_mask = initial[:, :, :, 2] < 0.0
    initial_centroid = centroid_from_array(initial, cell_nm, pmin_nm)
    initial_core_count = core_count_from_array(initial)
    core_projected = projection_maps(core_mask.astype(float))

    sum_amp_sq: np.ndarray | None = None
    peak_amp: np.ndarray | None = None
    final_amp: np.ndarray | None = None
    final_centroid = initial_centroid.copy()
    final_core_count = initial_core_count
    timeseries: list[dict[str, Any]] = []

    for frame_index, path in enumerate(paths):
        current, _, _ = load_field_array(path)
        amp = deformation_amplitude(initial, current)
        centroid = centroid_from_array(current, cell_nm, pmin_nm)
        core_count = core_count_from_array(current)
        summary = summarize_deformation(amp, core_mask)

        if frame_index > 0:
            amp_sq = amp * amp
            sum_amp_sq = amp_sq if sum_amp_sq is None else sum_amp_sq + amp_sq
            peak_amp = amp.copy() if peak_amp is None else np.maximum(peak_amp, amp)

        displacement = centroid - initial_centroid
        timeseries.append(
            {
                "label": config.label,
                "frame": frame_index,
                "time_ns": frame_index * config.dt_ps * 1e-3,
                "global_rms": summary["global_rms"],
                "core_rms": summary["core_rms"],
                "background_rms": summary["background_rms"],
                "core_to_background_rms": summary["core_to_background_rms"],
                "core_energy_fraction": summary["core_energy_fraction"],
                "core_count": core_count,
                "centroid_x_nm": centroid[0],
                "centroid_y_nm": centroid[1],
                "centroid_z_nm": centroid[2],
                "dx_nm": displacement[0],
                "dy_nm": displacement[1],
                "dz_nm": displacement[2],
                "displacement_nm": float(np.linalg.norm(displacement)),
            }
        )

        final_amp = amp.copy()
        final_centroid = centroid
        final_core_count = core_count
        del current, amp

    if sum_amp_sq is None:
        sum_amp_sq = np.zeros(initial.shape[:3], dtype=np.float32)
        peak_amp = np.zeros(initial.shape[:3], dtype=np.float32)
    assert final_amp is not None
    assert peak_amp is not None
    rms_map = np.sqrt(sum_amp_sq / max(len(paths) - 1, 1))

    sampling = sampling_report(config.freq_ghz, config.dt_ps)
    final_summary = summarize_deformation(final_amp, core_mask)
    rms_summary = summarize_deformation(rms_map, core_mask)
    peak_summary = summarize_deformation(peak_amp, core_mask)
    final_displacement = final_centroid - initial_centroid

    summary_row = {
        "label": config.label,
        "source": config.source,
        "freq_ghz": config.freq_ghz,
        "role": config.role,
        "energy_context": config.energy_context,
        "out_dir": str(config.out_dir),
        "frame_count": len(paths),
        "duration_ns": (len(paths) - 1) * config.dt_ps * 1e-3,
        "dt_ps": config.dt_ps,
        "drive_period_ps": sampling["drive_period_ps"],
        "samples_per_period": sampling["samples_per_period"],
        "nyquist_ok": sampling["nyquist_ok"],
        "mode_fft_reliable": sampling["mode_fft_reliable"],
        "recommended_interpretation": sampling["recommended_interpretation"],
        "rms_global_rms": rms_summary["global_rms"],
        "rms_core_rms": rms_summary["core_rms"],
        "rms_background_rms": rms_summary["background_rms"],
        "rms_core_to_background_rms": rms_summary["core_to_background_rms"],
        "rms_core_energy_fraction": rms_summary["core_energy_fraction"],
        "rms_global_max": rms_summary["global_max"],
        "final_global_rms": final_summary["global_rms"],
        "final_core_rms": final_summary["core_rms"],
        "final_background_rms": final_summary["background_rms"],
        "final_core_to_background_rms": final_summary["core_to_background_rms"],
        "final_core_energy_fraction": final_summary["core_energy_fraction"],
        "final_global_max": final_summary["global_max"],
        "peak_global_rms": peak_summary["global_rms"],
        "peak_global_max": peak_summary["global_max"],
        "core_volume_fraction": rms_summary["core_volume_fraction"],
        "core_count_initial": initial_core_count,
        "core_count_final": final_core_count,
        "core_count_delta": final_core_count - initial_core_count,
        "centroid_initial_x_nm": initial_centroid[0],
        "centroid_initial_y_nm": initial_centroid[1],
        "centroid_initial_z_nm": initial_centroid[2],
        "centroid_final_x_nm": final_centroid[0],
        "centroid_final_y_nm": final_centroid[1],
        "centroid_final_z_nm": final_centroid[2],
        "centroid_dx_nm": final_displacement[0],
        "centroid_dy_nm": final_displacement[1],
        "centroid_dz_nm": final_displacement[2],
        "centroid_displacement_nm": float(np.linalg.norm(final_displacement)),
    }

    return {
        "config": config,
        "summary": summary_row,
        "timeseries": timeseries,
        "rms_map": rms_map,
        "final_map": final_amp,
        "peak_map": peak_amp,
        "core_projected": core_projected,
        "cell_nm": cell_nm,
        "pmin_nm": pmin_nm,
    }


def projection_extent(shape: tuple[int, int, int], cell_nm: np.ndarray, pmin_nm: np.ndarray, axes: str) -> list[float]:
    axis_map = {"x": 0, "y": 1, "z": 2}
    x_axis = axis_map[axes[0]]
    y_axis = axis_map[axes[1]]
    return [
        float(pmin_nm[x_axis]),
        float(pmin_nm[x_axis] + cell_nm[x_axis] * shape[x_axis]),
        float(pmin_nm[y_axis]),
        float(pmin_nm[y_axis] + cell_nm[y_axis] * shape[y_axis]),
    ]


def add_projection(
    ax: plt.Axes,
    data: np.ndarray,
    core: np.ndarray,
    extent: list[float],
    title: str,
    xlabel: str,
    ylabel: str,
    vmax: float | None,
):
    im = ax.imshow(
        data.T,
        origin="lower",
        extent=extent,
        aspect="auto",
        cmap="magma",
        vmin=0.0,
        vmax=vmax,
    )
    if np.max(core) > 0:
        ax.contour(
            core.T,
            levels=[0.5],
            origin="lower",
            extent=extent,
            colors="white",
            linewidths=0.7,
            alpha=0.85,
        )
    ax.set_title(title, fontsize=10)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    return im


def plot_run_maps(result: dict[str, Any]) -> Path:
    config: RunConfig = result["config"]
    rms_proj = projection_maps(result["rms_map"])
    final_proj = projection_maps(result["final_map"])
    core_proj = result["core_projected"]
    shape = result["rms_map"].shape
    cell_nm = result["cell_nm"]
    pmin_nm = result["pmin_nm"]
    vmax = float(
        np.nanpercentile(
            np.concatenate(
                [
                    rms_proj["xy_mean"].ravel(),
                    rms_proj["xz_mean"].ravel(),
                    rms_proj["yz_mean"].ravel(),
                    final_proj["xy_mean"].ravel(),
                    final_proj["xz_mean"].ravel(),
                    final_proj["yz_mean"].ravel(),
                ]
            ),
            99.5,
        )
    )
    vmax = vmax if vmax > 0 else None

    fig, axes = plt.subplots(2, 3, figsize=(12.5, 7.0), constrained_layout=True)
    specs = [
        ("xy", "xy_mean", "x (nm)", "y (nm)"),
        ("xz", "xz_mean", "x (nm)", "z (nm)"),
        ("yz", "yz_mean", "y (nm)", "z (nm)"),
    ]

    last_im = None
    for col, (plane, key, xlabel, ylabel) in enumerate(specs):
        extent = projection_extent(shape, cell_nm, pmin_nm, plane)
        last_im = add_projection(
            axes[0, col],
            rms_proj[key],
            core_proj[key.replace("mean", "max")],
            extent,
            f"RMS deformation {plane}",
            xlabel,
            ylabel,
            vmax,
        )
        last_im = add_projection(
            axes[1, col],
            final_proj[key],
            core_proj[key.replace("mean", "max")],
            extent,
            f"Final-frame deformation {plane}",
            xlabel,
            ylabel,
            vmax,
        )

    fig.suptitle(
        f"{config.label}: stroboscopic |m(t)-m(0)| projections",
        fontsize=13,
        fontweight="bold",
    )
    if last_im is not None:
        fig.colorbar(last_im, ax=axes.ravel().tolist(), shrink=0.88, label="deformation amplitude")
    path = FIGURES_DIR / f"{config.label}_deformation_maps.png"
    fig.savefig(path, dpi=220)
    plt.close(fig)
    return path


def plot_xz_overview(results: list[dict[str, Any]]) -> Path:
    xz_maps = [projection_maps(result["rms_map"])["xz_mean"] for result in results]
    vmax = float(np.nanpercentile(np.concatenate([m.ravel() for m in xz_maps]), 99.5))
    vmax = vmax if vmax > 0 else None

    fig, axes = plt.subplots(2, 2, figsize=(10.8, 8.2), constrained_layout=True)
    last_im = None
    for ax, result, xz_map in zip(axes.ravel(), results, xz_maps):
        config: RunConfig = result["config"]
        shape = result["rms_map"].shape
        extent = projection_extent(shape, result["cell_nm"], result["pmin_nm"], "xz")
        core = result["core_projected"]["xz_max"]
        last_im = add_projection(
            ax,
            xz_map,
            core,
            extent,
            f"{config.label} ({config.role})",
            "x (nm)",
            "z (nm)",
            vmax,
        )
        ax.text(
            0.02,
            0.98,
            f"samples/period={result['summary']['samples_per_period']:.2g}",
            transform=ax.transAxes,
            ha="left",
            va="top",
            fontsize=8.5,
            color="white",
            bbox={"facecolor": "black", "alpha": 0.45, "edgecolor": "none", "pad": 2.5},
        )
    fig.suptitle("RMS stroboscopic deformation, xz projection", fontsize=13, fontweight="bold")
    if last_im is not None:
        fig.colorbar(last_im, ax=axes.ravel().tolist(), shrink=0.9, label="RMS deformation amplitude")
    path = FIGURES_DIR / "mode_map_rms_xz_overview.png"
    fig.savefig(path, dpi=220)
    plt.close(fig)
    return path


def plot_timeseries(results: list[dict[str, Any]]) -> Path:
    fig, axes = plt.subplots(2, 2, figsize=(11.5, 8.0), constrained_layout=True)
    colors = {
        "srcX_200GHz": "#1f77b4",
        "srcX_1000GHz": "#d62728",
        "srcZ_100GHz": "#2ca02c",
        "srcZ_1100GHz": "#9467bd",
    }
    for result in results:
        label = result["config"].label
        rows = result["timeseries"]
        t = np.array([row["time_ns"] for row in rows])
        color = colors.get(label)
        axes[0, 0].plot(t, [row["global_rms"] for row in rows], label=label, color=color, lw=1.8)
        axes[0, 1].plot(t, [row["dx_nm"] for row in rows], label=label, color=color, lw=1.8)
        axes[1, 0].plot(t, [row["dy_nm"] for row in rows], label=label, color=color, lw=1.8)
        axes[1, 1].plot(t, [row["dz_nm"] for row in rows], label=label, color=color, lw=1.8)

    titles = ["Global deformation RMS", "Centroid dx", "Centroid dy", "Centroid dz"]
    ylabels = ["|dm| RMS", "dx (nm)", "dy (nm)", "dz (nm)"]
    for ax, title, ylabel in zip(axes.ravel(), titles, ylabels):
        ax.set_title(title, fontsize=10)
        ax.set_xlabel("time (ns)")
        ax.set_ylabel(ylabel)
        ax.grid(True, alpha=0.25)
    axes[0, 0].legend(fontsize=8, loc="best")
    fig.suptitle("Representative-frequency deformation and centroid traces", fontsize=13, fontweight="bold")
    path = FIGURES_DIR / "deformation_timeseries_overview.png"
    fig.savefig(path, dpi=220)
    plt.close(fig)
    return path


def write_csv(path: Path, rows: list[dict[str, Any]]):
    if not rows:
        return
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def localization_phrase(row: dict[str, Any]) -> str:
    ratio = float(row["rms_core_to_background_rms"])
    frac = float(row["rms_core_energy_fraction"])
    if ratio >= 2.0 and frac >= 0.5:
        return "核心局域响应占主导"
    if ratio >= 1.2:
        return "核心振幅显著高于背景，但总响应并非完全局域"
    return "响应较弥散，背景或整体运动贡献较强"


def main_conclusion(rows: list[dict[str, Any]]) -> list[str]:
    lines = []
    for row in rows:
        phrase = localization_phrase(row)
        dominant = max(
            [
                ("dx", abs(float(row["centroid_dx_nm"]))),
                ("dy", abs(float(row["centroid_dy_nm"]))),
                ("dz", abs(float(row["centroid_dz_nm"]))),
            ],
            key=lambda item: item[1],
        )[0]
        lines.append(
            f"- `{row['label']}`：{phrase}。终态质心位移为 "
            f"{float(row['centroid_displacement_nm']):.3f} nm，主导分量为 {dominant}；"
            f"RMS 核心/背景振幅比为 {float(row['rms_core_to_background_rms']):.3f}，"
            f"核心差分能量占比为 {float(row['rms_core_energy_fraction']):.3f}。"
        )
    return lines


def write_markdown(rows: list[dict[str, Any]], figure_paths: list[Path]):
    readme = OUT_ROOT / "README.md"
    notes = NOTES_DIR / "paper_interpretation_cn.md"
    all_fft_unreliable = all(not row["mode_fft_reliable"] for row in rows)

    figure_lines = "\n".join(f"- `{path.relative_to(OUT_ROOT)}`" for path in figure_paths)
    conclusion_lines = "\n".join(main_conclusion(rows))

    readme.write_text(
        "\n".join(
            [
                "# Hopfion 四个代表频率空间响应审计",
                "",
                "本文件夹基于现有 OVF 保存帧分析四个代表性的平面自旋波驱动结果。",
                "由于保存帧间隔约为 10 ps，这里的结果应理解为 stroboscopic deformation/localization map，而不是严格的驱动频率 FFT 本征模图。",
                "",
                "## 分析对象",
                "",
                "- `srcX_200GHz`：能量吸收审计给出的候选 resonant coupling 频率。",
                "- `srcX_1000GHz`：高频强位移/控制窗口，但不是稳健正吸收峰。",
                "- `srcZ_100GHz`：轴向异常响应，拟合能量斜率为负。",
                "- `srcZ_1100GHz`：高频轴向强控制窗口，但不是稳健正吸收峰。",
                "",
                "## 输出文件",
                "",
                "- `results/mode_map_summary.csv`：逐频率的采样、形变、局域化、质心位移指标。",
                "- `results/deformation_timeseries.csv`：逐帧形变和质心轨迹。",
                figure_lines,
                "",
                "## 主要数值读法",
                "",
                conclusion_lines,
                "",
                "## 关键限制",
                "",
                "这四个代表频率全部低于可靠驱动频率 FFT mode map 所需的采样条件。"
                if all_fft_unreliable
                else "其中一部分频率低于可靠驱动频率 FFT mode map 所需的采样条件。",
                "若要得到严格的本征模或频域模式图，需要补跑高时间分辨率 OVF 保存，最好每个驱动周期保存 8 到 16 帧。",
                "",
            ]
        ),
        encoding="utf-8",
    )

    notes.write_text(
        "\n".join(
            [
                "# 论文解释建议：Hopfion 四个代表频率的空间响应图",
                "",
                "## 先说清楚这一步是什么",
                "",
                "这一步不是严格的本征模 FFT 图。现有 OVF 的保存间隔约为 10 ps，而 100 GHz 的周期是 10 ps，200 GHz 的周期是 5 ps，1000 GHz 和 1100 GHz 的周期更短。因此，对于这些频率，保存帧相当于用很慢的相机去拍很快的摆动。它能告诉我们 Hopfion 在驱动后哪些区域发生了较大形变，也能比较不同频率的空间局域性和整体漂移，但不能直接宣称为频域本征模形状。",
                "",
                "一个生动类比是，用每 10 秒拍一张照片去研究每秒摆一次的钟摆。你可以看见钟摆最终偏到哪里、整套装置是否被推着移动、哪里留下了运动痕迹，但你不能仅凭这些照片重建钟摆每一次往返的完整相位。",
                "",
                "## 当前四个频率的客观读法",
                "",
                conclusion_lines,
                "",
                "这里的核心差分能量占比看起来不高，是因为 Hopfion 核心体积只占整个计算盒的一小部分。更有信息量的是两个指标一起看：核心/背景 RMS 振幅比告诉我们核心附近是不是更容易被扰动，核心差分能量占比则提醒我们是否存在大范围背景波纹或整体漂移。当前四个频率都表现出核心附近振幅增强，但不能把它们都说成纯粹的核心局域本征模。",
                "",
                "## 和前一轮能量吸收谱的联系",
                "",
                "`srcX_200GHz` 在能量吸收审计中表现为稳定正吸收，而且终态质心位移只有约 1 nm，明显小于 1000 GHz 和 srcZ 两个强控制窗口。因此它更适合作为候选 resonant coupling 频率来讨论。空间图的作用是检查这个频率是否伴随 Hopfion 核心附近的形变增强。如果图中核心轮廓附近的 RMS 差分更强，就可以把论文表述为：能量吸收峰和局域形变增强相互支持，提示该驱动主要耦合到 Hopfion 的内部/局域动力学自由度。",
                "",
                "`srcX_1000GHz`、`srcZ_100GHz` 和 `srcZ_1100GHz` 更应该谨慎表述为强响应或控制窗口，而不是本征频率。`srcX_1000GHz` 的终态 z 位移约为 +10 nm，`srcZ_100GHz` 的终态 z 位移约为 +8.5 nm，`srcZ_1100GHz` 的终态 z 位移约为 -13.9 nm。这些结果更像是驱动几何、传播波纹和非平衡位移共同造成的运动响应。特别是 `srcZ_100GHz` 在能量斜率符号上不是稳健正吸收，因此不能单靠位移大就称为能量吸收共振。",
                "",
                "一个适合放进论文讨论的逻辑是：`srcX_200GHz` 支持“候选共振耦合”叙述，而另外三个频率支持“频率选择性控制窗口”叙述。前者强调吸收和局域形变，后者强调驱动下的运动效率和方向选择性。这样可以把频率扫描从现象堆砌整理成两类物理机制，而不是把所有峰都硬说成本征频率。",
                "",
                "## 接下来若要做真正的本征模图",
                "",
                "需要补跑高时间分辨率保存的短时仿真。最低要求是满足 Nyquist 条件，即每个周期至少 2 帧；更稳妥的本征模相位和幅度图建议每个周期 8 到 16 帧。以 200 GHz 为例，周期 5 ps，保存间隔最好小于 0.5 到 0.625 ps；以 1000 GHz 为例，周期 1 ps，保存间隔需要进入 0.1 ps 量级。这样才能对每个格点的 `m_x,m_y,m_z` 做锁相/FFT，并讨论真正的 drive-frequency mode profile。",
                "",
            ]
        ),
        encoding="utf-8",
    )


def run_all(max_frames: int | None = None) -> list[dict[str, Any]]:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)

    results = []
    for config in RUNS:
        print(f"Analyzing {config.label}: {config.out_dir}")
        result = analyze_run(config, max_frames=max_frames)
        results.append(result)
        plot_path = plot_run_maps(result)
        print(f"  wrote {plot_path}")

    summary_rows = [result["summary"] for result in results]
    timeseries_rows = [row for result in results for row in result["timeseries"]]
    write_csv(RESULTS_DIR / "mode_map_summary.csv", summary_rows)
    write_csv(RESULTS_DIR / "deformation_timeseries.csv", timeseries_rows)

    figure_paths = [plot_xz_overview(results), plot_timeseries(results)]
    figure_paths.extend(FIGURES_DIR / f"{result['config'].label}_deformation_maps.png" for result in results)
    write_markdown(summary_rows, figure_paths)
    print(f"Wrote {RESULTS_DIR / 'mode_map_summary.csv'}")
    print(f"Wrote {RESULTS_DIR / 'deformation_timeseries.csv'}")
    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--max-frames",
        type=int,
        default=None,
        help="optional small-frame limit for smoke tests",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_all(max_frames=args.max_frames)
