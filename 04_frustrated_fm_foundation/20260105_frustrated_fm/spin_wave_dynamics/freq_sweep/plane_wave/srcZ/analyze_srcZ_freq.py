"""
analyze_srcZ_freq.py — srcZ_vibX 完整频率响应分析

数据: coarse (100-1000GHz, step 100) + fine (25-175GHz, 1100-1500GHz)
共 20 个频率点，全部 0.5ns / 10ps autosave

输出 (results/):
  1. displacement_srcZ.png   — |dr(t)| / dz(t) 轨迹（按响应强度分组）
  2. freq_response_map.png   — 频率响应谱：|dr|, v̄, ā vs f
  3. direction_map.png       — dz 符号 vs 频率（异常 +z 区域可视化）
  4. motion_summary_srcZ.txt — 数值汇总表
"""

import os, sys, re
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

sys.path.insert(0, "/mnt/d/Research/Hopfion/95_shared_scripts")
from hopfion_analysis import extract_trajectory_phase_correlation

HERE  = os.path.dirname(os.path.abspath(__file__))
RES   = os.path.join(HERE, "results")
os.makedirs(RES, exist_ok=True)

DT_NS = 0.01   # 10 ps autosave


# ── 1. 收集所有 .out 目录并解析频率 ──────────────────────────────────────
def parse_freq(dirname):
    m = re.search(r'f(\d+)GHz', dirname)
    return int(m.group(1)) if m else None

out_dirs = sorted(
    [d for d in os.listdir(HERE) if d.endswith('.out') and 'srcZ' in d],
    key=lambda d: parse_freq(d)
)

print(f"找到 {len(out_dirs)} 个仿真目录")


# ── 2. 提取轨迹 ───────────────────────────────────────────────────────────
def classify_motion(ts, dr, vz):
    if dr[-1] < 0.15:
        return "static"
    n3 = len(ts) // 3
    v_late = vz[n3:]
    speed_late = np.abs(v_late)
    if np.mean(speed_late) < 0.5:
        return "weak"
    slope = np.polyfit(ts[n3:], speed_late, 1)[0]
    if slope > 0.5:
        return "accelerating"
    return "steady"


profiles = {}
for dname in out_dirs:
    freq = parse_freq(dname)
    path = os.path.join(HERE, dname)
    print(f"  f={freq:5d}GHz  ...", end="", flush=True)
    try:
        traj = extract_trajectory_phase_correlation(path, DT_NS, verbose=False)
        if len(traj) < 3:
            print(" skip (too few frames)")
            continue
        ts    = np.array([r[0] for r in traj])
        dx    = np.array([r[1][0] for r in traj])
        dy    = np.array([r[1][1] for r in traj])
        dz    = np.array([r[1][2] for r in traj])
        dr    = np.sqrt(dx**2 + dy**2 + dz**2)
        cores = np.array([r[2] for r in traj])

        vx = np.gradient(dx, ts)
        vy = np.gradient(dy, ts)
        vz_t = np.gradient(dz, ts)
        speed = np.sqrt(vx**2 + vy**2 + vz_t**2)
        accel = np.sqrt(np.gradient(vx,ts)**2 +
                        np.gradient(vy,ts)**2 +
                        np.gradient(vz_t,ts)**2)

        n3 = len(ts) // 3
        mode = classify_motion(ts, dr, vz_t)

        profiles[freq] = dict(
            ts=ts, dx=dx, dy=dy, dz=dz, dr=dr,
            speed=speed, accel=accel, vz=vz_t,
            cores=cores, mode=mode,
            v_mean=float(np.mean(speed[n3:])),
            a_mean=float(np.mean(accel[n3:])),
        )
        print(f" {len(traj):2d}fr  |dr|={dr[-1]:.2f}nm  dz={dz[-1]:+.2f}nm  [{mode}]")
    except Exception as e:
        print(f" ERROR: {e}")

freqs = sorted(profiles.keys())
print(f"\n成功处理 {len(freqs)} 个频率点: {freqs}")


# ── 3. 颜色方案 ───────────────────────────────────────────────────────────
MODE_COLOR = {
    "static":       "#aaaaaa",
    "weak":         "#7ec8e3",
    "steady":       "#2ca02c",
    "accelerating": "#ff7f0e",
}

def mcolor(f):
    return MODE_COLOR.get(profiles[f]["mode"], "#999999")


# ── Fig 1: dz(t) 轨迹（全频率，按响应强度分为强/中/弱三组） ──────────────
dr_finals = {f: profiles[f]["dr"][-1] for f in freqs}
strong = [f for f in freqs if dr_finals[f] >= 5.0]
medium = [f for f in freqs if 1.0 <= dr_finals[f] < 5.0]
weak   = [f for f in freqs if dr_finals[f] < 1.0]

fig, axes = plt.subplots(1, 3, figsize=(18, 6), sharey=False)
fig.suptitle("srcZ_vibX: dz(t) Trajectory by Response Level (0.5ns, B=1T)", fontsize=13)

groups = [(strong, "Strong (|dr|≥5nm)", axes[0]),
          (medium, "Medium (1≤|dr|<5nm)", axes[1]),
          (weak,   "Weak (|dr|<1nm)",    axes[2])]

cmap = plt.cm.tab20
for grp_freqs, title, ax in groups:
    colors = cmap(np.linspace(0, 1, max(len(grp_freqs), 1)))
    for i, f in enumerate(grp_freqs):
        p = profiles[f]
        ax.plot(p["ts"], p["dz"], lw=1.8, color=colors[i],
                label=f"{f}GHz ({p['mode']})")
    ax.axhline(0, color='k', lw=0.8, ls='--')
    ax.set_title(title, fontsize=11)
    ax.set_xlabel("Time (ns)")
    ax.set_ylabel("dz (nm)")
    ax.legend(fontsize=7.5, loc='best')
    ax.grid(True, alpha=0.25)

plt.tight_layout()
fig.savefig(os.path.join(RES, "displacement_srcZ.png"), dpi=200)
plt.close(fig)
print("[fig] results/displacement_srcZ.png")


# ── Fig 2: 频率响应谱 ─────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 3, figsize=(18, 5))
fig.suptitle("srcZ_vibX: Frequency Response Spectrum", fontsize=13)

bar_w = 18   # GHz，条形宽度
x = np.array(freqs)
colors_bar = [mcolor(f) for f in freqs]

# Panel A: final |dr|
axes[0].bar(x, [dr_finals[f] for f in freqs],
            width=bar_w, color=colors_bar, edgecolor='k', linewidth=0.5)
axes[0].set_xlabel("Frequency (GHz)")
axes[0].set_ylabel("|dr| @ 0.5ns (nm)")
axes[0].set_title("Final displacement")

# Panel B: mean speed
axes[1].bar(x, [profiles[f]["v_mean"] for f in freqs],
            width=bar_w, color=colors_bar, edgecolor='k', linewidth=0.5)
axes[1].set_xlabel("Frequency (GHz)")
axes[1].set_ylabel("Mean |v| (nm/ns)")
axes[1].set_title("Mean speed (skip 1/3 transient)")

# Panel C: mean accel
axes[2].bar(x, [profiles[f]["a_mean"] for f in freqs],
            width=bar_w, color=colors_bar, edgecolor='k', linewidth=0.5)
axes[2].set_xlabel("Frequency (GHz)")
axes[2].set_ylabel("Mean |a| (nm/ns²)")
axes[2].set_title("Mean acceleration")

legend_els = [Patch(facecolor=c, edgecolor='k', label=m)
              for m, c in MODE_COLOR.items()]
axes[0].legend(handles=legend_els, fontsize=8)

for ax in axes:
    ax.grid(True, alpha=0.25, axis='y')
    ax.set_xlim(0, max(freqs)+100)

plt.tight_layout()
fig.savefig(os.path.join(RES, "freq_response_map.png"), dpi=200)
plt.close(fig)
print("[fig] results/freq_response_map.png")


# ── Fig 3: dz 方向图（区分 +z 与 -z 区域） ───────────────────────────────
dz_finals = {f: profiles[f]["dz"][-1] for f in freqs}
pos_z = [f for f in freqs if dz_finals[f] > 0]
neg_z = [f for f in freqs if dz_finals[f] < 0]

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
fig.suptitle("srcZ_vibX: dz Direction Map vs Frequency", fontsize=13)

# Upper: dz值（正负颜色区分）
colors_dz = ['#e74c3c' if dz_finals[f] > 0 else '#3498db' for f in freqs]
ax1.bar(x, [dz_finals[f] for f in freqs],
        width=bar_w, color=colors_dz, edgecolor='k', linewidth=0.5)
ax1.axhline(0, color='k', lw=1.2)
ax1.set_ylabel("dz @ 0.5ns (nm)")
ax1.set_title("z-displacement: red=+z (anomalous), blue=-z (normal)")
ax1.grid(True, alpha=0.25, axis='y')

p1 = Patch(facecolor='#e74c3c', edgecolor='k', label=f'+z (anomalous): {pos_z} GHz')
p2 = Patch(facecolor='#3498db', edgecolor='k', label=f'-z (normal): {len(neg_z)} freqs')
ax1.legend(handles=[p1, p2], fontsize=9)

# Lower: |dr| vs frequency，线图更清晰
ax2.plot(freqs, [dr_finals[f] for f in freqs], 'o-',
         color='#2c3e50', lw=2.0, ms=6, zorder=3)
for f in freqs:
    c = '#e74c3c' if dz_finals[f] > 0 else '#3498db'
    ax2.plot(f, dr_finals[f], 'o', color=c, ms=8, zorder=4)
ax2.set_xlabel("Frequency (GHz)")
ax2.set_ylabel("|dr| @ 0.5ns (nm)")
ax2.set_title("|dr| spectrum with direction color coding")
ax2.grid(True, alpha=0.25)
ax2.set_xlim(0, max(freqs)+100)

plt.tight_layout()
fig.savefig(os.path.join(RES, "direction_map.png"), dpi=200)
plt.close(fig)
print("[fig] results/direction_map.png")


# ── 4. 数值汇总表 ─────────────────────────────────────────────────────────
header = (f"{'freq(GHz)':>10} {'|dr|(nm)':>9} {'dz(nm)':>9} "
          f"{'v_mean':>10} {'a_mean':>12} "
          f"{'Core_0':>7} {'Core_f':>7} {'dir':>5} {'mode'}")
sep = "-" * 90
rows = [header, sep]

for f in freqs:
    p = profiles[f]
    direction = "+z" if p["dz"][-1] > 0 else "-z"
    rows.append(
        f"{f:>10} {p['dr'][-1]:>9.3f} {p['dz'][-1]:>+9.3f} "
        f"{p['v_mean']:>10.2f} {p['a_mean']:>12.2f} "
        f"{int(p['cores'][0]):>7} {int(p['cores'][-1]):>7} "
        f"{direction:>5} {p['mode']}"
    )

txt = "\n".join(rows)
with open(os.path.join(RES, "motion_summary_srcZ.txt"), "w") as fh:
    fh.write(txt + "\n")
print(f"[txt] results/motion_summary_srcZ.txt")
print("\n" + txt)
