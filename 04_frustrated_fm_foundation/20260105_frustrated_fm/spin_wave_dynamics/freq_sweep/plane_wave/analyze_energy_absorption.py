#!/usr/bin/env python3
"""
Energy Absorption Spectrum: dE/dt vs frequency
Hopfion-duo: 从已有 table.txt 提取能量吸收率，定位共振频率。

产出:
  - energy_absorption_spectrum.png (srcX + srcZ 对比)
  - energy_absorption_summary.txt (数值汇总)
"""
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import re
import matplotlib
matplotlib.rcParams['axes.unicode_minus'] = False

BASE = Path(__file__).parent

# ── 数据路径定义 ──────────────────────────────────────────────
srcX_02ns = {
    f: BASE / f"srcX/02ns/sw_f{f}GHz.out/table.txt"
    for f in range(100, 1001, 100)
}
srcX_05ns = {
    300: BASE / "srcX/05ns/sw_f300GHz.out/table.txt",
    400: BASE / "srcX/05ns/sw_f400GHz.out/table.txt",
    900: BASE / "srcX/05ns/sw_f900GHz.out/table.txt",
    1000: BASE / "srcX/05ns/sw_f1000GHz.out/table.txt",
}

srcZ_coarse = {
    f: BASE / f"srcZ/sw_srcZ_f{f}GHz.out/table.txt"
    for f in range(100, 1001, 100)
}
srcZ_fine = {}
for f in [25, 50, 75, 125, 150, 175, 1100, 1200, 1300, 1500]:
    srcZ_fine[f] = BASE / f"srcZ/sw_srcZ_fine_f{f}GHz.out/table.txt"


def load_table(path):
    """Load Mumax3 table.txt, return (t_s, E_total_J)."""
    data = np.loadtxt(path, skiprows=1)
    t = data[:, 0]          # column 0: time (s)
    E = data[:, 4]          # column 4: E_total (J)
    return t, E


def compute_absorption(t, E, t_start_frac=0.0, t_end_frac=1.0):
    """
    Compute average dE/dt via linear regression over [t_start_frac, t_end_frac]
    of the total time range.
    Returns: slope (J/s), R² value
    """
    t_min, t_max = t[0], t[-1]
    t0 = t_min + (t_max - t_min) * t_start_frac
    t1 = t_min + (t_max - t_min) * t_end_frac
    mask = (t >= t0) & (t <= t1)
    if mask.sum() < 10:
        return np.nan, np.nan
    t_sel, E_sel = t[mask], E[mask]
    # Linear regression
    coeffs = np.polyfit(t_sel, E_sel, 1)
    slope = coeffs[0]  # dE/dt in J/s
    # R² for quality check
    E_pred = np.polyval(coeffs, t_sel)
    ss_res = np.sum((E_sel - E_pred) ** 2)
    ss_tot = np.sum((E_sel - np.mean(E_sel)) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0
    return slope, r2


def analyze_set(table_paths, label, t_start_frac=0.0, t_end_frac=1.0):
    """Analyze a set of frequency points. Returns sorted arrays."""
    freqs, slopes, r2s = [], [], []
    for f in sorted(table_paths.keys()):
        path = table_paths[f]
        if not path.exists():
            print(f"  SKIP {label} f={f}GHz: {path} not found")
            continue
        t, E = load_table(path)
        slope, r2 = compute_absorption(t, E, t_start_frac, t_end_frac)
        freqs.append(f)
        slopes.append(slope)
        r2s.append(r2)
    return np.array(freqs), np.array(slopes), np.array(r2s)


# ── 分析 ──────────────────────────────────────────────────────
print("=== Energy Absorption Spectrum Analysis ===\n")

# srcX: prefer 05ns data where available, fallback to 02ns
srcX_merged = dict(srcX_02ns)  # start with all 02ns
srcX_merged.update(srcX_05ns)   # overwrite with 05ns where available

srcX_freqs, srcX_dEdt, srcX_r2 = analyze_set(srcX_merged, "srcX", 0.3, 1.0)

# srcZ: merge coarse + fine (no overlap)
srcZ_all = dict(srcZ_coarse)
srcZ_all.update(srcZ_fine)
srcZ_freqs, srcZ_dEdt, srcZ_r2 = analyze_set(srcZ_all, "srcZ", 0.3, 1.0)

# Also compute full-range for comparison
srcX_freqs_full, srcX_dEdt_full, _ = analyze_set(srcX_merged, "srcX_full", 0.0, 1.0)
srcZ_freqs_full, srcZ_dEdt_full, _ = analyze_set(srcZ_all, "srcZ_full", 0.0, 1.0)

# ── 绘图 ──────────────────────────────────────────────────────
outdir = BASE / "energy_absorption"
outdir.mkdir(exist_ok=True)

fig, axes = plt.subplots(2, 1, figsize=(12, 9), sharex=False)

# -- srcX subplot --
ax = axes[0]
ax.bar(srcX_freqs, srcX_dEdt * 1e9, width=40, color='#2196F3', alpha=0.8,
       edgecolor='#1565C0', linewidth=0.8, label='dE/dt (0.3T–end)')
ax.set_ylabel('dE/dt  (nJ/s)', fontsize=12)
ax.set_title('srcX (in-plane propagation) — Energy Absorption Spectrum', fontsize=13)
ax.axhline(0, color='gray', linewidth=0.5, linestyle='--')
ax.legend(fontsize=10)
ax.grid(axis='y', alpha=0.3)

# Mark peaks
srcX_peak_idx = np.argsort(np.abs(srcX_dEdt))[-3:]
for idx in srcX_peak_idx:
    ax.annotate(f'{srcX_freqs[idx]}GHz',
                xy=(srcX_freqs[idx], srcX_dEdt[idx] * 1e9),
                xytext=(0, 10), textcoords='offset points',
                ha='center', fontsize=9, fontweight='bold', color='red')

# -- srcZ subplot --
ax = axes[1]
ax.bar(srcZ_freqs, srcZ_dEdt * 1e9, width=30, color='#FF9800', alpha=0.8,
       edgecolor='#E65100', linewidth=0.8, label='dE/dt (0.3T–end)')
ax.set_xlabel('Frequency (GHz)', fontsize=12)
ax.set_ylabel('dE/dt  (nJ/s)', fontsize=12)
ax.set_title('srcZ (axial propagation) — Energy Absorption Spectrum', fontsize=13)
ax.axhline(0, color='gray', linewidth=0.5, linestyle='--')
ax.legend(fontsize=10)
ax.grid(axis='y', alpha=0.3)

# Mark peaks
srcZ_peak_idx = np.argsort(np.abs(srcZ_dEdt))[-3:]
for idx in srcZ_peak_idx:
    ax.annotate(f'{srcZ_freqs[idx]}GHz',
                xy=(srcZ_freqs[idx], srcZ_dEdt[idx] * 1e9),
                xytext=(0, 10), textcoords='offset points',
                ha='center', fontsize=9, fontweight='bold', color='red')

plt.tight_layout()
fig.savefig(outdir / 'energy_absorption_spectrum.png', dpi=200, bbox_inches='tight')
print(f"\nSaved: {outdir / 'energy_absorption_spectrum.png'}")

# ── 汇总表 ────────────────────────────────────────────────────
summary_path = outdir / 'energy_absorption_summary.txt'
with open(summary_path, 'w') as f:
    f.write("=" * 72 + "\n")
    f.write("Energy Absorption Spectrum Summary (dE/dt via linear fit, 0.3T–end)\n")
    f.write("=" * 72 + "\n\n")

    f.write("srcX (面内传播, 100-1000 GHz):\n")
    f.write(f"{'Freq(GHz)':>10}  {'dE/dt(J/s)':>14}  {'dE/dt(nJ/s)':>12}  {'R²':>8}\n")
    f.write("-" * 50 + "\n")
    for i, freq in enumerate(srcX_freqs):
        f.write(f"{freq:10.0f}  {srcX_dEdt[i]:14.6e}  {srcX_dEdt[i]*1e9:12.4f}  {srcX_r2[i]:8.4f}\n")
    # Peak: highest |dE/dt| with R² > 0.5
    srcX_valid = srcX_r2 > 0.5
    if srcX_valid.any():
        srcX_peak_f = srcX_freqs[srcX_valid][np.argmax(np.abs(srcX_dEdt[srcX_valid]))]
    else:
        srcX_peak_f = srcX_freqs[np.argmax(np.abs(srcX_dEdt))]
    f.write(f"\n  → srcX 最强吸收频率 (R²>0.5): {srcX_peak_f:.0f} GHz\n\n")

    f.write("srcZ (轴向传播, 25-1500 GHz):\n")
    f.write(f"{'Freq(GHz)':>10}  {'dE/dt(J/s)':>14}  {'dE/dt(nJ/s)':>12}  {'R²':>8}\n")
    f.write("-" * 50 + "\n")
    for i, freq in enumerate(srcZ_freqs):
        f.write(f"{freq:10.0f}  {srcZ_dEdt[i]:14.6e}  {srcZ_dEdt[i]*1e9:12.4f}  {srcZ_r2[i]:8.4f}\n")
    srcZ_valid = srcZ_r2 > 0.5
    if srcZ_valid.any():
        srcZ_peak_f = srcZ_freqs[srcZ_valid][np.argmax(np.abs(srcZ_dEdt[srcZ_valid]))]
    else:
        srcZ_peak_f = srcZ_freqs[np.argmax(np.abs(srcZ_dEdt))]
    f.write(f"\n  → srcZ 最强吸收频率 (R²>0.5): {srcZ_peak_f:.0f} GHz\n")

print(f"Saved: {summary_path}")
plt.close()
print("\nDone.")
