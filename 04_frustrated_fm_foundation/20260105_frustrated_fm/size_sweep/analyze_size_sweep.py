"""
尺寸收敛性分析脚本
用法: source /mnt/d/Research/Hopfion/hopfion/bin/activate
      cd .../size_sweep/
      python analyze_size_sweep.py

功能:
  - R8r4_Ku0.out:            0→1ns   (21帧, 步长50ps)
  - R12r5_Ku0.out:           0→0.95ns (20帧)
  - R12r5_Ku0_continue.out:  0.95→4.95ns (81帧, 步长50ps)
  - 对比两组在各时间点的 R/r, 判断 R12r5 是否收敛至同一吸引子
"""

import os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.optimize import least_squares
from skimage import measure
import discretisedfield as df

BASE = os.path.dirname(os.path.abspath(__file__))

# 已知 R8r4 收敛吸引子（参考值）
REF_R = 2.60   # nm
REF_r = 2.16   # nm

CORE_THRESHOLD = 0.05
BAD_FIT_NM     = 3.0


# ── 几何计算 ───────────────────────────────────────────────────────────────

def _circle_residuals(params, pts):
    xc, yc, R = params
    return np.sqrt((pts[:, 0] - xc)**2 + (pts[:, 1] - yc)**2) - R


def _pbc_unwrap_xy(xy, box_L):
    centroid = np.mean(xy, axis=0)
    delta = xy - centroid
    delta -= box_L * np.round(delta / box_L)
    return centroid + delta


def compute_Rr(field):
    """返回 (R_nm, r_nm, status)"""
    mz   = field.array[..., 2]
    cell = np.array(field.mesh.cell)
    pmin = np.array(field.mesh.region.pmin)
    box_L = np.array(field.mesh.region.pmax) - pmin

    mz_min   = float(np.min(mz))
    core_mask = mz < (mz_min + CORE_THRESHOLD)
    if not np.any(core_mask):
        return None, None, "no_core"

    idx    = np.array(np.where(core_mask)).T
    coords = pmin + idx * cell
    xy     = coords[:, :2]
    if len(xy) < 4:
        return None, None, "no_core"

    xy_uw = _pbc_unwrap_xy(xy, box_L[:2])
    cg    = np.mean(xy_uw, axis=0)
    rg    = np.mean(np.linalg.norm(xy_uw - cg, axis=1))

    try:
        res = least_squares(_circle_residuals, [cg[0], cg[1], rg],
                            args=(xy_uw,), method='lm')
        xc, yc, R_fit = res.x
        fit_err = np.sqrt(res.cost / len(xy_uw)) * 1e9
    except Exception:
        return None, None, "fit_failed"

    if fit_err > BAD_FIT_NM:
        return abs(R_fit) * 1e9, None, "fit_failed"

    R_nm = abs(R_fit) * 1e9

    try:
        verts, _, _, _ = measure.marching_cubes(mz, level=0, spacing=tuple(cell))
        verts += pmin
    except (ValueError, RuntimeError):
        return R_nm, None, "no_isosurface"

    if len(verts) == 0:
        return R_nm, None, "no_isosurface"

    core_z   = float(np.mean(coords[:, 2]))
    dist_xy  = np.sqrt((verts[:, 0] - xc)**2 + (verts[:, 1] - yc)**2)
    dist_ring = np.sqrt((dist_xy - abs(R_fit))**2 + (verts[:, 2] - core_z)**2)
    r_nm = float(np.mean(dist_ring)) * 1e9

    return R_nm, r_nm, "alive"


# ── 采样逻辑 ───────────────────────────────────────────────────────────────

def sample_run(out_dir, t_offset=0.0, dt=5e-11, step=5, label=""):
    """
    对 out_dir 中每隔 step 帧采样一次, 返回 [(t_ns, R, r, status), ...]
    t_offset: 该段仿真的真实起始时间 (s)
    """
    ovfs = sorted(f for f in os.listdir(out_dir) if f.endswith(".ovf") and f.startswith("m"))
    results = []
    for i, fname in enumerate(ovfs):
        if i % step != 0:
            continue
        t_ns = (t_offset + i * dt) * 1e9
        path = os.path.join(out_dir, fname)
        try:
            field = df.Field.from_file(path)
            R, r, st = compute_Rr(field)
            del field
        except Exception as e:
            R, r, st = None, None, f"err:{e}"
        print(f"  {label} t={t_ns:.2f}ns  R={R:.2f}nm  r={r:.2f}nm  [{st}]"
              if R else f"  {label} t={t_ns:.2f}ns  [{st}]")
        results.append((t_ns, R, r, st))
    return results


# ── 主流程 ─────────────────────────────────────────────────────────────────

def main():
    print("=" * 55)
    print("  尺寸收敛性分析 (size_sweep)")
    print("=" * 55)

    # ── R8r4 (0→1ns) ──
    print("\n>>> R8r4_Ku0 (初始 R=8nm, r=4nm)")
    r8_data = sample_run(
        os.path.join(BASE, "R8r4_Ku0.out"),
        t_offset=0.0, dt=5e-11, step=2, label="R8r4"
    )

    # ── R12r5 第一段 (0→0.95ns) ──
    print("\n>>> R12r5_Ku0 段1 (初始 R=12nm, r=5nm, 0→0.95ns)")
    r12_seg1 = sample_run(
        os.path.join(BASE, "R12r5_Ku0.out"),
        t_offset=0.0, dt=5e-11, step=2, label="R12r5-seg1"
    )

    # ── R12r5 续跑 (0.95→4.95ns) ──
    # continue.out 第 i 帧真实时间 = 0.95ns + i×50ps
    print("\n>>> R12r5_Ku0_continue (0.95→4.95ns)")
    r12_seg2 = sample_run(
        os.path.join(BASE, "R12r5_Ku0_continue.out"),
        t_offset=0.95e-9, dt=5e-11, step=4, label="R12r5-seg2"
    )

    # 拼接 R12r5 两段
    r12_data = r12_seg1 + r12_seg2

    # ── 绘图 ──────────────────────────────────────────────────────────────
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    for data, color, label in [
        (r8_data,  "steelblue", "R8r4 (初始 R=8,r=4nm)"),
        (r12_data, "tomato",    "R12r5 (初始 R=12,r=5nm)"),
    ]:
        ts = [d[0] for d in data]
        Rs = [d[1] for d in data]
        rs = [d[2] for d in data]

        ts_R = [t for t, R in zip(ts, Rs) if R is not None]
        Rs_v = [R for R in Rs if R is not None]
        ts_r = [t for t, r in zip(ts, rs) if r is not None]
        rs_v = [r for r in rs if r is not None]

        if ts_R:
            axes[0].plot(ts_R, Rs_v, 'o-', color=color, label=label, markersize=5)
        if ts_r:
            axes[1].plot(ts_r, rs_v, 's-', color=color, label=label, markersize=5)

    # 参考吸引子水平线
    for ax, ref, ylabel, title in zip(
        axes,
        [REF_R, REF_r],
        ["R (nm)", "r (nm)"],
        ["大半径 R(t)", "管半径 r(t)"]
    ):
        ax.axhline(ref, color='k', linestyle='--', linewidth=1.2,
                   label=f"参考吸引子 {ref:.2f} nm")
        ax.set_xlabel("时间 (ns)")
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        ax.legend(fontsize=9)
        ax.grid(True, alpha=0.3)

    plt.suptitle("Frustrated FM Hopfion — 初始尺寸收敛性", fontsize=13)
    plt.tight_layout()
    out_png = os.path.join(BASE, "size_convergence_full.png")
    plt.savefig(out_png, dpi=200)
    plt.close()
    print(f"\n[图] 已保存: {out_png}")

    # ── 末帧汇总 ──────────────────────────────────────────────────────────
    def last_valid(data):
        for d in reversed(data):
            if d[1] is not None:
                return d
        return (None, None, None, None)

    r8_last  = last_valid(r8_data)
    r12_last = last_valid(r12_data)

    print("\n" + "=" * 55)
    print("  末帧汇总")
    print("=" * 55)
    print(f"  参考吸引子 :  R={REF_R:.2f} nm,  r={REF_r:.2f} nm")
    print(f"  R8r4  末帧  :  t={r8_last[0]:.2f}ns  R={r8_last[1]:.2f}nm  r={r8_last[2]:.2f}nm  [{r8_last[3]}]"
          if r8_last[1] else "  R8r4  末帧  :  无有效数据")
    print(f"  R12r5 末帧  :  t={r12_last[0]:.2f}ns  R={r12_last[1]:.2f}nm  r={r12_last[2]:.2f}nm  [{r12_last[3]}]"
          if r12_last[1] else "  R12r5 末帧  :  无有效数据")

    if r12_last[1] and r8_last[1]:
        dR = abs(r12_last[1] - REF_R)
        dr = abs(r12_last[2] - REF_r) if r12_last[2] else float('nan')
        print(f"\n  R12r5 与参考吸引子偏差:  ΔR={dR:.2f}nm  Δr={dr:.2f}nm")
        if dR < 0.5 and dr < 0.5:
            print("  ✅ 结论: R12r5 已收敛至同一吸引子")
        else:
            print("  ⚠️  结论: R12r5 尚未完全收敛，需进一步延长")


if __name__ == "__main__":
    main()
