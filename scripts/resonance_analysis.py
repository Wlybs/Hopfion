"""
resonance_analysis.py — Hopfion 共振频率分析工具库
==================================================
三种互补方法定位自旋波-Hopfion 共振频率：

  方法1: velocity_response_spectrum   — 频率扫描 v̄(f) 响应曲线
  方法2: energy_absorption_spectrum   — 频率扫描 ΔĖ(f) 能量吸收率
  方法3: generate_pulse_mx3 + pulse_eigenmode_analysis — 脉冲本征模谱

用法:
    import sys
    sys.path.insert(0, "/mnt/d/Research/Hopfion/scripts")
    from resonance_analysis import (
        velocity_response_spectrum,
        energy_absorption_spectrum,
        generate_pulse_mx3,
        pulse_eigenmode_analysis,
    )
"""

import os
import numpy as np


# ──────────────────────────────────────────────
# 公共工具
# ──────────────────────────────────────────────

def load_mumax_table(table_path):
    """
    加载 mumax3 table.txt。

    Returns
    -------
    dict : {列名: np.ndarray}
        列名取 "name (unit)" 中 "name" 部分。
    """
    with open(table_path) as f:
        header_line = f.readline().strip()
    raw_cols = header_line.lstrip("# ").split("\t")
    col_names = [c.split(" (")[0].strip() for c in raw_cols]
    data = np.loadtxt(table_path)
    if data.ndim == 1:
        data = data.reshape(1, -1)
    return {name: data[:, i] for i, name in enumerate(col_names)}


# ──────────────────────────────────────────────
# 方法1: 速度响应谱 v̄(f)
# ──────────────────────────────────────────────

def velocity_response_spectrum(sweep_dir, freqs_ghz, dt_ns,
                                exclude_boundary=5, t_skip_frac=0.3):
    """
    从频率扫描各 .out 目录提取时间平均速度 v̄。

    Parameters
    ----------
    sweep_dir : str
        包含 sw_f{freq}GHz.out/ 子目录的父目录。
    freqs_ghz : list of int
        频率点列表（GHz）。
    dt_ns : float
        OVF autosave 间隔（ns）。
    t_skip_frac : float
        跳过初始瞬态的时间比例（默认 0.3）。

    Returns
    -------
    dict : {freq_ghz: v_mean_nm_per_ns}
    """
    from hopfion_analysis import extract_trajectory_phase_correlation

    results = {}
    for f in freqs_ghz:
        out_dir = os.path.join(sweep_dir, f"sw_f{f}GHz.out")
        if not os.path.isdir(out_dir):
            continue
        traj = extract_trajectory_phase_correlation(
            out_dir, dt_ns, exclude_boundary=exclude_boundary, verbose=False)
        if len(traj) < 3:
            results[f] = 0.0
            continue

        ts = np.array([d[0] for d in traj])
        dr = np.array([np.linalg.norm(d[1]) for d in traj])
        v = np.abs(np.gradient(dr, ts))

        n_skip = int(len(v) * t_skip_frac)
        results[f] = float(np.mean(v[n_skip:]))

    return results


# ──────────────────────────────────────────────
# 方法2: 能量吸收谱 ΔĖ(f)
# ──────────────────────────────────────────────

def energy_absorption_spectrum(sweep_dir, freqs_ghz, t_skip_frac=0.3):
    """
    从频率扫描的 table.txt 提取平均能量吸收率 dE_total/dt。

    共振频率处 Hopfion 从自旋波高效吸收能量，dE/dt 显著偏高。

    Parameters
    ----------
    sweep_dir : str
    freqs_ghz : list of int
    t_skip_frac : float

    Returns
    -------
    dict : {freq_ghz: dE_dt_mean (W)}
    """
    results = {}
    for f in freqs_ghz:
        table_path = os.path.join(sweep_dir, f"sw_f{f}GHz.out", "table.txt")
        if not os.path.isfile(table_path):
            continue

        table = load_mumax_table(table_path)
        t = table.get("t")
        E = table.get("E_total")
        if t is None or E is None:
            continue

        n_skip = int(len(t) * t_skip_frac)
        t_cut = t[n_skip:]
        E_cut = E[n_skip:]

        if len(t_cut) < 2:
            results[f] = 0.0
            continue

        # 线性拟合斜率 = 平均功率吸收率
        slope = np.polyfit(t_cut, E_cut, 1)[0]
        results[f] = float(slope)

    return results


# ──────────────────────────────────────────────
# 方法3: 脉冲本征模谱 — mx3 生成
# ──────────────────────────────────────────────

_FRUSTRATED_FM_MX3 = """\
// === Frustrated FM Hopfion — {title} ===

CellSize := 0.5e-9
SetGridSize(100, 100, 100)
SetCellSize(CellSize, CellSize, CellSize)

DefRegion(1, XRange(22.5e-9, 25e-9))
DefRegion(2, XRange(-25e-9, -22.5e-9))
DefRegion(3, YRange(22.5e-9, 25e-9))
DefRegion(4, YRange(-25e-9, -22.5e-9))
DefRegion(5, ZRange(22.5e-9, 25e-9))
DefRegion(6, ZRange(-25e-9, -22.5e-9))
DefRegion(7, {source_region})

EnableDemag = false
MaxErr = 1e-4

Ms     := 1.5e5
Msat    = Ms
A_base := 5e-12
Aex     = A_base
Dbulk   = 0
Dind    = 0
Ku1     = 1e4
anisU   = vector(0, 0, 1)

alpha = 0.001
alpha.setRegion(1, 100)
alpha.setRegion(2, 100)
alpha.setRegion(3, 100)
alpha.setRegion(4, 100)
alpha.setRegion(5, 100)
alpha.setRegion(6, 100)

A_J4     := A_base * (-0.082)
Coeff_J4 := A_J4 * 2.0 / (Ms * CellSize * CellSize)
sum_J4   := Add(Shifted(m, 2, 0, 0), Shifted(m, -2, 0, 0))
sum_J4    = Add(sum_J4, Shifted(m, 0, 2, 0))
sum_J4    = Add(sum_J4, Shifted(m, 0, -2, 0))
sum_J4    = Add(sum_J4, Shifted(m, 0, 0, 2))
sum_J4    = Add(sum_J4, Shifted(m, 0, 0, -2))
AddFieldTerm(Mul(Const(Coeff_J4), sum_J4))

A_J2     := A_base * (-0.164)
Coeff_J2 := A_J2 * 2.0 / (Ms * CellSize * CellSize)
sum_J2   := Add(Shifted(m, 1, 1, 0), Shifted(m, 1, -1, 0))
sum_J2    = Add(sum_J2, Shifted(m, -1, 1, 0))
sum_J2    = Add(sum_J2, Shifted(m, -1, -1, 0))
sum_J2    = Add(sum_J2, Shifted(m, 0, 1, 1))
sum_J2    = Add(sum_J2, Shifted(m, 0, 1, -1))
sum_J2    = Add(sum_J2, Shifted(m, 0, -1, 1))
sum_J2    = Add(sum_J2, Shifted(m, 0, -1, -1))
sum_J2    = Add(sum_J2, Shifted(m, 1, 0, 1))
sum_J2    = Add(sum_J2, Shifted(m, 1, 0, -1))
sum_J2    = Add(sum_J2, Shifted(m, -1, 0, 1))
sum_J2    = Add(sum_J2, Shifted(m, -1, 0, -1))
AddFieldTerm(Mul(Const(Coeff_J2), sum_J2))

m.LoadFile("{init_ovf}")

{excitation}

autosave(m, {dt_ovf:.1f}e-12)
tableautosave({dt_table:.2f}e-12)
TableAdd(E_Total)

run({run_ns}e-9)
"""

_SRC_REGIONS = {
    'x': 'XRange(-10e-9, -9.5e-9)',
    'z': 'ZRange(-10e-9, -9.5e-9)',
}


def generate_pulse_mx3(out_path, source_axis='x', vib_axis='x',
                        sigma_ps=0.2, B_amp=0.5, run_ns=1.0,
                        dt_save_ps=1.0, init_ovf=None):
    """
    生成宽频高斯脉冲激励的 mx3 脚本。

    脉冲带宽 ~ 1/(2piσ)，σ=0.2ps → ~800GHz 覆盖。
    脉冲中心 t0=5σ，之后为自由振荡。

    Parameters
    ----------
    source_axis : str  'x' or 'z'（源面法线方向）
    vib_axis : str     'x' or 'z'（振动极化方向）
    sigma_ps : float   高斯脉冲宽度（ps）
    B_amp : float      峰值幅度（T）
    run_ns : float     运行时间（ns），频率分辨率 Δf = 1/T
    dt_save_ps : float OVF autosave 间隔（ps），Nyquist freq = 1/(2dt)
    init_ovf : str     初始态路径
    """
    if init_ovf is None:
        init_ovf = ("/mnt/d/Research/Hopfion/20260105_frustrated_fm/"
                     "centered_stability_test/stability_Ku10k.out/m000020.ovf")

    if source_axis not in _SRC_REGIONS:
        raise ValueError(f"source_axis must be 'x' or 'z', got '{source_axis}'")
    if vib_axis not in ('x', 'z'):
        raise ValueError(f"vib_axis must be 'x' or 'z', got '{vib_axis}'")

    sigma_s = sigma_ps * 1e-12
    t0_s = 5 * sigma_s
    sigma_sq2 = 2 * sigma_s ** 2

    pulse = (f"{B_amp} * exp(-(t-{t0_s:.2e})*(t-{t0_s:.2e})"
             f"/({sigma_sq2:.2e}))")
    if vib_axis == 'x':
        bext = f"Vector({pulse}, 0, 0)"
    else:
        bext = f"Vector(0, 0, {pulse})"

    excitation = f"B_ext.setRegion(7, {bext})"
    title = (f"Pulse src{source_axis.upper()}_vib{vib_axis.upper()}, "
             f"sigma={sigma_ps}ps, B={B_amp}T")

    script = _FRUSTRATED_FM_MX3.format(
        title=title,
        source_region=_SRC_REGIONS[source_axis],
        init_ovf=init_ovf,
        excitation=excitation,
        dt_ovf=dt_save_ps,
        dt_table=dt_save_ps * 0.5,
        run_ns=run_ns,
    )

    with open(out_path, 'w') as f:
        f.write(script)


def generate_cw_mx3(out_path, freq_ghz, source_axis='x', vib_axis='x',
                      B_amp=1.0, run_ns=0.2, dt_save_ps=10.0, init_ovf=None):
    """
    生成连续波激励的 mx3 脚本。支持 srcX/srcZ + vibX/vibZ。

    Parameters
    ----------
    freq_ghz : int or float  激励频率（GHz）
    其余参数同 generate_pulse_mx3。
    """
    if init_ovf is None:
        init_ovf = ("/mnt/d/Research/Hopfion/20260105_frustrated_fm/"
                     "centered_stability_test/stability_Ku10k.out/m000020.ovf")

    if source_axis not in _SRC_REGIONS:
        raise ValueError(f"source_axis must be 'x' or 'z', got '{source_axis}'")
    if vib_axis not in ('x', 'z'):
        raise ValueError(f"vib_axis must be 'x' or 'z', got '{vib_axis}'")

    freq_expr = f"{freq_ghz}e9 * 2 * pi"
    if vib_axis == 'x':
        bext = f"Vector({B_amp}*sin({freq_expr}*t), 0, 0)"
    else:
        bext = f"Vector(0, 0, {B_amp}*sin({freq_expr}*t))"

    excitation = f"f_sw := {freq_expr}\nB_ext.setRegion(7, {bext})"
    title = (f"CW src{source_axis.upper()}_vib{vib_axis.upper()}, "
             f"f={freq_ghz}GHz, B={B_amp}T")

    script = _FRUSTRATED_FM_MX3.format(
        title=title,
        source_region=_SRC_REGIONS[source_axis],
        init_ovf=init_ovf,
        excitation=excitation,
        dt_ovf=dt_save_ps,
        dt_table=min(dt_save_ps, 1.0),
        run_ns=run_ns,
    )

    with open(out_path, 'w') as f:
        f.write(script)


_FRUSTRATED_FM_RINGDOWN_TABLE_ONLY_MX3 = """\
// === Frustrated FM Hopfion — uniform sinc ringdown ({drive_axis}-axis) ===
// Table-only run for eigenmode screening. No OVF autosave is enabled.

CellSize := 0.5e-9
SetGridSize(100, 100, 100)
SetCellSize(CellSize, CellSize, CellSize)

// Six absorbing boundary slabs, matching spin_wave_dynamics freq_sweep setup.
DefRegion(1, XRange(22.5e-9, 25e-9))
DefRegion(2, XRange(-25e-9, -22.5e-9))
DefRegion(3, YRange(22.5e-9, 25e-9))
DefRegion(4, YRange(-25e-9, -22.5e-9))
DefRegion(5, ZRange(22.5e-9, 25e-9))
DefRegion(6, ZRange(-25e-9, -22.5e-9))

EnableDemag = false
MaxErr = 1e-4

Ms     := 1.5e5
Msat    = Ms
A_base := 5e-12
Aex     = A_base
Dbulk   = 0
Dind    = 0
Ku1     = 1e4
anisU   = vector(0, 0, 1)

alpha = 0.001
alpha.setRegion(1, 100)
alpha.setRegion(2, 100)
alpha.setRegion(3, 100)
alpha.setRegion(4, 100)
alpha.setRegion(5, 100)
alpha.setRegion(6, 100)

// -- J4: fourth-nearest frustrated exchange --
A_J4     := A_base * (-0.082)
Coeff_J4 := A_J4 * 2.0 / (Ms * CellSize * CellSize)
sum_J4   := Add(Shifted(m, 2, 0, 0), Shifted(m, -2, 0, 0))
sum_J4    = Add(sum_J4, Shifted(m, 0, 2, 0))
sum_J4    = Add(sum_J4, Shifted(m, 0, -2, 0))
sum_J4    = Add(sum_J4, Shifted(m, 0, 0, 2))
sum_J4    = Add(sum_J4, Shifted(m, 0, 0, -2))
AddFieldTerm(Mul(Const(Coeff_J4), sum_J4))

// -- J2: next-nearest frustrated exchange --
A_J2     := A_base * (-0.164)
Coeff_J2 := A_J2 * 2.0 / (Ms * CellSize * CellSize)
sum_J2   := Add(Shifted(m, 1, 1, 0), Shifted(m, 1, -1, 0))
sum_J2    = Add(sum_J2, Shifted(m, -1, 1, 0))
sum_J2    = Add(sum_J2, Shifted(m, -1, -1, 0))
sum_J2    = Add(sum_J2, Shifted(m, 0, 1, 1))
sum_J2    = Add(sum_J2, Shifted(m, 0, 1, -1))
sum_J2    = Add(sum_J2, Shifted(m, 0, -1, 1))
sum_J2    = Add(sum_J2, Shifted(m, 0, -1, -1))
sum_J2    = Add(sum_J2, Shifted(m, 1, 0, 1))
sum_J2    = Add(sum_J2, Shifted(m, 1, 0, -1))
sum_J2    = Add(sum_J2, Shifted(m, -1, 0, 1))
sum_J2    = Add(sum_J2, Shifted(m, -1, 0, -1))
AddFieldTerm(Mul(Const(Coeff_J2), sum_J2))

{initialization}

B0 := {b0_t}
fc := {cutoff_ghz:g}e9
t0 := {t0_ps}e-12
pulse := B0 * sin(2*pi*fc*(t-t0))/(2*pi*fc*(t-t0) + 1e-30)
{b_ext}

{spatial_output}

tableautosave({table_dt_ps}e-12)
TableAdd(E_Total)

run({run_ns}e-9)
"""


def generate_sinc_ringdown_mx3(out_path, drive_axis='x', cutoff_ghz=2000.0,
                                b0_t=0.005, t0_ps=2.37, run_ns=0.5,
                                table_dt_ps=0.05, init_ovf=None,
                                uniform_background=False, spatial_roi=None,
                                spatial_dt_ps=None):
    """
    生成 uniform weak sinc pulse 的 table-only ringdown Mumax3 脚本。

    该脚本用于本征模初筛：全局弱场短脉冲激励后，只保存 table.txt，
    对空间平均磁化和 E_total 做 FFT。它不定义自旋波源区域，也不保存 OVF。
    """
    if init_ovf is None:
        init_ovf = ("/mnt/d/Research/Hopfion/20260105_frustrated_fm/"
                    "centered_stability_test/stability_Ku10k.out/m000020.ovf")

    if drive_axis not in ('x', 'y', 'z'):
        raise ValueError("drive_axis must be 'x', 'y', or 'z'")

    if drive_axis == 'x':
        b_ext = "B_ext = Vector(pulse, 0, 0)"
    elif drive_axis == 'y':
        b_ext = "B_ext = Vector(0, pulse, 0)"
    else:
        b_ext = "B_ext = Vector(0, 0, pulse)"

    if uniform_background:
        initialization = "m = uniform(0, 0, 1)"
    else:
        initialization = f'm.LoadFile("{init_ovf}")'

    if spatial_roi is None:
        spatial_output = ""
    else:
        if len(spatial_roi) != 6:
            raise ValueError("spatial_roi must contain six cell indices")
        if spatial_dt_ps is None or spatial_dt_ps <= 0:
            raise ValueError("spatial_dt_ps must be positive when spatial_roi is set")
        x1, x2, y1, y2, z1, z2 = spatial_roi
        spatial_output = (
            f"roi_m := Crop(m, {x1}, {x2}, {y1}, {y2}, {z1}, {z2})\n"
            f"autosave(roi_m, {spatial_dt_ps:g}e-12)"
        )

    script = _FRUSTRATED_FM_RINGDOWN_TABLE_ONLY_MX3.format(
        drive_axis=drive_axis.upper(),
        initialization=initialization,
        b0_t=b0_t,
        cutoff_ghz=cutoff_ghz,
        t0_ps=t0_ps,
        table_dt_ps=table_dt_ps,
        run_ns=run_ns,
        b_ext=b_ext,
        spatial_output=spatial_output,
    )

    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(script)


def generate_circular_burst_mx3(out_path, handedness=1,
                                 frequency_ghz=174.0, b0_t=0.002,
                                 center_ps=60.0, sigma_ps=20.0,
                                 run_ns=0.5, table_dt_ps=0.05,
                                 init_ovf=None):
    """Generate a Gaussian-envelope circular microwave burst."""
    if handedness not in (-1, 1):
        raise ValueError("handedness must be -1 or 1")
    if init_ovf is None:
        init_ovf = ("/mnt/d/Research/Hopfion/20260105_frustrated_fm/"
                    "centered_stability_test/stability_Ku10k.out/m000020.ovf")

    sign = "" if handedness == 1 else "-"
    b_ext = (
        f"carrier := {frequency_ghz:g}e9 * 2 * pi\n"
        f"center := {center_ps:g}e-12\n"
        f"sigma := {sigma_ps:g}e-12\n"
        "envelope := B0 * exp(-((t-center)*(t-center))/(2*sigma*sigma))\n"
        "B_ext = Vector(envelope*cos(carrier*t), "
        f"{sign}envelope*sin(carrier*t), 0)"
    )
    script = _FRUSTRATED_FM_RINGDOWN_TABLE_ONLY_MX3.format(
        drive_axis="CIRCULAR",
        initialization=f'm.LoadFile("{init_ovf}")',
        b0_t=b0_t,
        cutoff_ghz=2000.0,
        t0_ps=2.37,
        table_dt_ps=table_dt_ps,
        run_ns=run_ns,
        b_ext=b_ext,
        spatial_output="",
    )
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(script)


def estimate_peak_metrics(freqs_ghz, power, target_ghz,
                          search_halfwidth_ghz=30.0):
    """Estimate peak frequency, numerical FWHM, and Q near a target."""
    freqs = np.asarray(freqs_ghz, dtype=float)
    psd = np.asarray(power, dtype=float)
    if freqs.shape != psd.shape:
        raise ValueError("freqs_ghz and power must have the same shape")
    mask = (np.isfinite(freqs) & np.isfinite(psd)
            & (freqs >= target_ghz - search_halfwidth_ghz)
            & (freqs <= target_ghz + search_halfwidth_ghz))
    f = freqs[mask]
    y = psd[mask]
    if len(f) < 3 or np.max(y) <= 0:
        return {"status": "no_peak"}

    peak_index = int(np.argmax(y))
    peak_frequency = float(f[peak_index])
    peak_power = float(y[peak_index])
    half_power = peak_power / 2.0

    left_candidates = np.where(y[:peak_index] < half_power)[0]
    right_candidates = np.where(y[peak_index + 1:] < half_power)[0]
    if len(left_candidates) == 0 or len(right_candidates) == 0:
        return {
            "status": "fwhm_unresolved",
            "frequency_ghz": peak_frequency,
            "power": peak_power,
        }

    left_low = int(left_candidates[-1])
    left_high = left_low + 1
    right_high = peak_index + 1 + int(right_candidates[0])
    right_low = right_high - 1

    left_cross = float(np.interp(
        half_power,
        [y[left_low], y[left_high]],
        [f[left_low], f[left_high]],
    ))
    right_cross = float(np.interp(
        half_power,
        [y[right_high], y[right_low]],
        [f[right_high], f[right_low]],
    ))
    fwhm = right_cross - left_cross
    if fwhm <= 0:
        return {"status": "fwhm_unresolved", "frequency_ghz": peak_frequency}
    return {
        "status": "ok",
        "frequency_ghz": peak_frequency,
        "power": peak_power,
        "fwhm_ghz": float(fwhm),
        "quality_factor": float(peak_frequency / fwhm),
    }


def fit_power_law(amplitudes, responses):
    """Fit response = prefactor * amplitude**exponent in log space."""
    x = np.asarray(amplitudes, dtype=float)
    y = np.asarray(responses, dtype=float)
    if x.shape != y.shape or len(x) < 2:
        raise ValueError("amplitudes and responses need matching lengths >= 2")
    if np.any(x <= 0) or np.any(y <= 0):
        raise ValueError("amplitudes and responses must be positive")
    slope, intercept = np.polyfit(np.log(x), np.log(y), 1)
    predicted = intercept + slope * np.log(x)
    residual = np.sum((np.log(y) - predicted) ** 2)
    total = np.sum((np.log(y) - np.mean(np.log(y))) ** 2)
    r_squared = 1.0 if total == 0 else 1.0 - residual / total
    return {
        "exponent": float(slope),
        "prefactor": float(np.exp(intercept)),
        "r_squared": float(r_squared),
    }


def evaluate_mode_localization(mask_mean_power, outside_mean_power,
                               hopfion_total_power, background_total_power,
                               min_localization=2.0, min_background_contrast=3.0):
    """Apply the project-level operational gate for a localized mode."""
    if outside_mean_power <= 0 or background_total_power <= 0:
        raise ValueError("reference powers must be positive")
    localization_ratio = float(mask_mean_power / outside_mean_power)
    background_contrast = float(hopfion_total_power / background_total_power)
    return {
        "localization_ratio": localization_ratio,
        "background_contrast": background_contrast,
        "passed": bool(
            localization_ratio >= min_localization
            and background_contrast >= min_background_contrast
        ),
    }


def ringdown_fft_from_table(table_path, columns=('mx', 'my', 'mz', 'E_total'),
                             t_start_s=0.0, window='hann'):
    """
    对 Mumax3 table.txt 中的平均磁化/能量序列做去均值 FFT。

    Returns
    -------
    dict
        `freqs_ghz` plus `psd_<column>` arrays for available columns.
    """
    table = load_mumax_table(table_path)
    if 't' not in table:
        raise ValueError(f"No time column 't' in {table_path}")

    t = np.asarray(table['t'], dtype=float)
    mask = t >= t_start_s
    if np.count_nonzero(mask) < 8:
        raise ValueError("Need at least 8 samples after t_start_s for FFT")

    t_cut = t[mask]
    dt = float(np.median(np.diff(t_cut)))
    if not np.isfinite(dt) or dt <= 0:
        raise ValueError("Invalid or non-monotonic time column")

    freqs_ghz = np.fft.rfftfreq(len(t_cut), d=dt) * 1e-9
    result = {'freqs_ghz': freqs_ghz}

    if window == 'hann':
        weights = np.hanning(len(t_cut))
    elif window in (None, 'none'):
        weights = np.ones(len(t_cut))
    else:
        raise ValueError("window must be 'hann', 'none', or None")

    norm = np.sum(weights ** 2)
    if norm == 0:
        norm = 1.0

    for col in columns:
        if col not in table:
            continue
        sig = np.asarray(table[col], dtype=float)[mask]
        sig = sig - np.mean(sig)
        psd = np.abs(np.fft.rfft(sig * weights)) ** 2 / norm
        result[f'psd_{col}'] = psd

    return result


def find_fft_peaks(freqs_ghz, power, min_freq_ghz=0.0, max_freq_ghz=None,
                    max_peaks=8, min_prominence_rel=0.05):
    """
    从 FFT 功率谱中提取按功率排序的候选峰。

    `min_prominence_rel` 使用全谱最大功率的相对阈值；这是轻量筛选，
    不是替代后续空间模图的严格本征模判定。
    """
    freqs = np.asarray(freqs_ghz, dtype=float)
    psd = np.asarray(power, dtype=float)
    if freqs.shape != psd.shape:
        raise ValueError("freqs_ghz and power must have the same shape")

    mask = np.isfinite(freqs) & np.isfinite(psd) & (freqs >= min_freq_ghz)
    if max_freq_ghz is not None:
        mask &= freqs <= max_freq_ghz

    f = freqs[mask]
    y = psd[mask]
    if len(y) < 3 or np.max(y) <= 0:
        return []

    threshold = np.max(y) * float(min_prominence_rel)
    peaks = []
    for i in range(1, len(y) - 1):
        if y[i] <= threshold:
            continue
        if y[i] > y[i - 1] and y[i] >= y[i + 1]:
            local_floor = max(y[i - 1], y[i + 1])
            peaks.append({
                'frequency_ghz': float(f[i]),
                'power': float(y[i]),
                'prominence': float(y[i] - local_floor),
            })

    peaks.sort(key=lambda item: item['power'], reverse=True)
    return peaks[:max_peaks]


# ──────────────────────────────────────────────
# 方法3: 脉冲本征模谱 — 分析
# ──────────────────────────────────────────────

def pulse_eigenmode_analysis(out_dir, dt_ns, exclude_boundary=5,
                              t_pulse_end_ns=0.005):
    """
    对脉冲激发后的自由振荡做 FFT，提取 Hopfion 本征频率。

    同时分析：
    - centroid(t) 各分量 → 平动模式频率
    - E_total(t) from table.txt → 全模式频率（如可用）

    Parameters
    ----------
    out_dir : str
    dt_ns : float
        OVF autosave 间隔（ns）。
    t_pulse_end_ns : float
        脉冲结束时间（ns），FFT 从此时开始排除强驱动段。

    Returns
    -------
    dict:
        'freqs_ghz': 频率轴（GHz），基于 OVF
        'psd_dx', 'psd_dy', 'psd_dz': 各分量功率谱
        'psd_dr': 总位移功率谱
        'freqs_ghz_E', 'psd_E': E_total 频率轴和功率谱（如 table.txt 可用）
    """
    from hopfion_analysis import extract_trajectory_phase_correlation

    traj = extract_trajectory_phase_correlation(
        out_dir, dt_ns, exclude_boundary=exclude_boundary, verbose=True)

    data = [(t, s) for t, s, _ in traj if t >= t_pulse_end_ns]
    if len(data) < 8:
        return None

    ts = np.array([d[0] for d in data])
    shifts = np.array([d[1] for d in data])  # (N, 3)

    dt = ts[1] - ts[0]
    N = len(ts)
    freqs_ghz = np.fft.rfftfreq(N, d=dt * 1e-9) * 1e-9

    result = {'freqs_ghz': freqs_ghz}
    for i, label in enumerate(['dx', 'dy', 'dz']):
        sig = shifts[:, i] - np.mean(shifts[:, i])
        result[f'psd_{label}'] = np.abs(np.fft.rfft(sig)) ** 2

    dr = np.linalg.norm(shifts, axis=1)
    result['psd_dr'] = np.abs(np.fft.rfft(dr - np.mean(dr))) ** 2

    # E_total FFT from table.txt（时间分辨率更高）
    table_path = os.path.join(out_dir, "table.txt")
    if os.path.isfile(table_path):
        table = load_mumax_table(table_path)
        t_E = table.get("t")    # seconds
        E = table.get("E_total")
        if t_E is not None and E is not None:
            mask = t_E >= t_pulse_end_ns * 1e-9
            t_E_cut = t_E[mask]
            E_cut = E[mask]
            if len(E_cut) > 8:
                dt_E = t_E_cut[1] - t_E_cut[0]
                freqs_E = np.fft.rfftfreq(len(E_cut), d=dt_E) * 1e-9
                result['freqs_ghz_E'] = freqs_E
                result['psd_E'] = np.abs(
                    np.fft.rfft(E_cut - np.mean(E_cut))) ** 2

    return result
