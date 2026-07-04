"""
点源幅度全扫描分析（8点: B=100,200,300,400,500,700,1000,2000 @1100GHz）
提取质心位移、速度、标度律。

输出（results/）：
  - ps_B_sweep_full.png   : 位移+速度+标度律三合一
  - ps_B_sweep_full.txt   : 数值汇总
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import discretisedfield as df

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results")
os.makedirs(RESULTS, exist_ok=True)

B_VALUES = [100, 200, 300, 400, 500, 700, 1000, 2000]
DT_PS = 10  # autosave interval in ps


def hopfion_center(field):
    mz = field.array[:, :, :, 2]
    weight = np.maximum(1 - mz, 0)
    w_sum = np.sum(weight)
    centers = []
    for i in range(3):
        coords = np.linspace(
            field.mesh.region.pmin[i] + field.mesh.cell[i] / 2,
            field.mesh.region.pmax[i] - field.mesh.cell[i] / 2,
            mz.shape[i],
        )
        shape = [1, 1, 1]
        shape[i] = mz.shape[i]
        centers.append(np.sum(coords.reshape(shape) * weight) / w_sum * 1e9)
    return centers


def count_core(field):
    return int(np.sum(field.array[:, :, :, 2] < 0))


results = []
for B in B_VALUES:
    outdir = os.path.join(HERE, f"ps_srcX_vibX_1100GHz_B{B}.out")
    ovfs = sorted([f for f in os.listdir(outdir) if f.endswith(".ovf")])

    if len(ovfs) < 2:
        print(f"B={B}: skip, only {len(ovfs)} frames")
        continue

    f0 = df.Field.from_file(os.path.join(outdir, ovfs[0]))
    ff = df.Field.from_file(os.path.join(outdir, ovfs[-1]))

    c0 = hopfion_center(f0)
    cf = hopfion_center(ff)

    dx = cf[0] - c0[0]
    dy = cf[1] - c0[1]
    dz = cf[2] - c0[2]
    dr = np.sqrt(dx**2 + dy**2 + dz**2)

    n_frames = len(ovfs) - 1
    t_total_ns = n_frames * DT_PS / 1000.0
    v_mean = dr / t_total_ns if t_total_ns > 0 else 0

    core0 = count_core(f0)
    coref = count_core(ff)

    results.append({
        "B": B, "dx": dx, "dy": dy, "dz": dz, "dr": dr,
        "v": v_mean, "core0": core0, "coref": coref,
        "t_ns": t_total_ns, "n_frames": len(ovfs),
    })
    print(f"B={B:5d}  |dr|={dr:.4f}nm  dz={dz:+.4f}nm  v={v_mean:.3f}nm/ns  core={core0}->{coref}")

# ── 数值汇总 ─────────────────────────────────────────────────
with open(os.path.join(RESULTS, "ps_B_sweep_full.txt"), "w") as f:
    f.write("=" * 80 + "\n")
    f.write("Point Source Amplitude Sweep: B=100-2000T @ 1100GHz, srcX_vibX\n")
    f.write("=" * 80 + "\n\n")
    f.write(f"{'B(T)':>6}  {'dx(nm)':>9}  {'dy(nm)':>9}  {'dz(nm)':>9}  {'|dr|(nm)':>9}  {'v(nm/ns)':>9}  {'core0':>6}  {'coref':>6}\n")
    f.write("-" * 75 + "\n")
    for r in results:
        f.write(f"{r['B']:6d}  {r['dx']:+9.4f}  {r['dy']:+9.4f}  {r['dz']:+9.4f}  {r['dr']:9.4f}  {r['v']:9.3f}  {r['core0']:6d}  {r['coref']:6d}\n")

    # Power law fit for points with |dr| > 0.1 nm
    B_arr = np.array([r["B"] for r in results])
    v_arr = np.array([r["v"] for r in results])
    dr_arr = np.array([r["dr"] for r in results])
    mask = dr_arr > 0.1
    if mask.sum() >= 3:
        logB = np.log10(B_arr[mask])
        logv = np.log10(v_arr[mask])
        coeffs = np.polyfit(logB, logv, 1)
        n_exp = coeffs[0]
        A_coeff = 10 ** coeffs[1]
        v_pred = A_coeff * B_arr[mask] ** n_exp
        ss_res = np.sum((v_arr[mask] - v_pred) ** 2)
        ss_tot = np.sum((v_arr[mask] - np.mean(v_arr[mask])) ** 2)
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0
        f.write(f"\nPower-law fit (|dr|>0.1nm, {mask.sum()} points):\n")
        f.write(f"  v = {A_coeff:.6f} * B^{n_exp:.4f}\n")
        f.write(f"  R² = {r2:.4f}\n")
    f.write("\n")

print(f"\nSaved: {RESULTS}/ps_B_sweep_full.txt")

# ── 绘图 ─────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 3, figsize=(15, 5))

# (a) |dr| vs B
ax = axes[0]
ax.bar(range(len(results)), [r["dr"] for r in results], color="#FF9800", alpha=0.8)
ax.set_xticks(range(len(results)))
ax.set_xticklabels([str(r["B"]) for r in results], rotation=45)
ax.set_xlabel("B (T)")
ax.set_ylabel("|dr| (nm)")
ax.set_title("(a) Displacement vs B")

# (b) velocity vs B (log-log)
ax = axes[1]
ax.loglog(B_arr, v_arr, "o-", color="#2196F3", markersize=8)
if mask.sum() >= 3:
    B_fit = np.logspace(np.log10(B_arr[mask].min()), np.log10(B_arr[mask].max()), 50)
    ax.loglog(B_fit, A_coeff * B_fit ** n_exp, "--", color="red",
              label=f"v = {A_coeff:.2f} B^{{{n_exp:.2f}}}  R²={r2:.3f}")
    ax.legend()
ax.set_xlabel("B (T)")
ax.set_ylabel("v (nm/ns)")
ax.set_title("(b) Velocity scaling (log-log)")

# (c) core count
ax = axes[2]
ax.plot(B_arr, [r["coref"] for r in results], "s-", color="#4CAF50", markersize=8)
ax.axhline(results[0]["core0"], color="gray", linestyle="--", alpha=0.5, label=f"initial={results[0]['core0']}")
ax.set_xlabel("B (T)")
ax.set_ylabel("Core voxels (mz<0)")
ax.set_title("(c) Hopfion integrity")
ax.legend()

plt.tight_layout()
fig.savefig(os.path.join(RESULTS, "ps_B_sweep_full.png"), dpi=200, bbox_inches="tight")
print(f"Saved: {RESULTS}/ps_B_sweep_full.png")
plt.close()
