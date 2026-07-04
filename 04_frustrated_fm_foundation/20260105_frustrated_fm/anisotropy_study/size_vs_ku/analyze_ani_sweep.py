"""
各向异性扫描结果分析脚本
用法: source /mnt/d/Research/Hopfion/hopfion/bin/activate
      cd .../anisotropy_sweep/
      python analyze_ani_sweep.py

功能:
  1. 对每个 Ku1 组, 取 7 个关键帧 (t=0~3ns, 每0.5ns)
  2. 计算 hopfion 的 R(大半径) 和 r(管半径), 判断存活/死亡
  3. 输出 results/ 目录:
     - R_r_vs_time.png   : 各 Ku1 下 R(t), r(t) 时间线
     - summary_Rr_vs_Ku1.png : 末帧 R, r 汇总图
     - survival_table.txt: 文本存活报告
"""

import os
import sys
import glob
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.optimize import least_squares
from skimage import measure
import discretisedfield as df

# ─────────────────────────────────────────────
# 参数配置
# ─────────────────────────────────────────────
SWEEP_DIR   = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(SWEEP_DIR, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

# Ku1 列表 (J/m³)，与目录名对应（6个完整3ns数据点）
KU1_LIST = [0, 2500, 5000, 7500, 10000, 12000]

# 采样帧索引 (共31帧, 0~30 对应 t=0~3ns, 步长0.1ns)
SAMPLE_INDICES = [0, 5, 10, 15, 20, 25, 30]
SAMPLE_TIMES   = [i * 0.1 for i in SAMPLE_INDICES]   # ns

# hopfion 核心阈值: mz < (mz_min + threshold) 识别为核心
CORE_THRESHOLD = 0.05

# 拟合质量判定: 平均残差 > BAD_FIT_NM nm 认为拟合失败
BAD_FIT_NM = 3.0   # nm


# ─────────────────────────────────────────────
# 工具函数
# ─────────────────────────────────────────────

def _circle_residuals(params, pts):
    xc, yc, R = params
    return np.sqrt((pts[:, 0] - xc)**2 + (pts[:, 1] - yc)**2) - R


def _pbc_unwrap_xy(xy, box_L):
    """PBC 坐标折叠: 以质心为基准, 将所有点折叠到半盒范围内"""
    centroid = np.mean(xy, axis=0)
    delta = xy - centroid
    delta -= box_L * np.round(delta / box_L)
    return centroid + delta


def compute_hopfion_Rr(field):
    """
    计算 hopfion 大半径 R 和管半径 r.
    返回 (R_nm, r_nm, status) 其中 status ∈ {'alive', 'fit_failed', 'no_core', 'no_isosurface'}
    R_nm, r_nm 为 None 表示无法计算.
    """
    mz  = field.array[..., 2]
    cell = np.array(field.mesh.cell)     # (dx, dy, dz)
    pmin = np.array(field.mesh.region.pmin)
    box_L = np.array(field.mesh.region.pmax) - pmin   # (Lx, Ly, Lz)

    mz_min = float(np.min(mz))
    core_mask = mz < (mz_min + CORE_THRESHOLD)

    if not np.any(core_mask):
        return None, None, "no_core"

    # 核心格点坐标 (真实空间, 单位 m)
    idx = np.array(np.where(core_mask)).T          # shape (N, 3)
    coords = pmin + idx * cell                     # (N, 3)
    xy = coords[:, :2]

    if len(xy) < 4:
        return None, None, "no_core"

    # PBC 折叠
    xy_unwrapped = _pbc_unwrap_xy(xy, box_L[:2])

    center_guess = np.mean(xy_unwrapped, axis=0)
    r_guess = np.mean(np.linalg.norm(xy_unwrapped - center_guess, axis=1))

    try:
        res = least_squares(
            _circle_residuals,
            [center_guess[0], center_guess[1], r_guess],
            args=(xy_unwrapped,),
            method='lm'
        )
        xc, yc, R_fit = res.x
        fit_error_nm = np.sqrt(res.cost / len(xy_unwrapped)) * 1e9
    except Exception:
        return None, None, "fit_failed"

    if fit_error_nm > BAD_FIT_NM:
        return R_fit * 1e9, None, "fit_failed"

    R_nm = abs(R_fit) * 1e9

    # 计算管半径 r: 用 mz=0 等值面到核心环的平均距离
    try:
        verts, _, _, _ = measure.marching_cubes(
            volume=mz, level=0,
            spacing=tuple(cell)
        )
        verts += pmin
    except (ValueError, RuntimeError):
        return R_nm, None, "no_isosurface"

    if len(verts) == 0:
        return R_nm, None, "no_isosurface"

    core_z_center = float(np.mean(coords[:, 2]))
    dist_xy = np.sqrt((verts[:, 0] - xc)**2 + (verts[:, 1] - yc)**2)
    dist_to_ring = np.sqrt((dist_xy - abs(R_fit))**2 + (verts[:, 2] - core_z_center)**2)
    r_nm = float(np.mean(dist_to_ring)) * 1e9

    return R_nm, r_nm, "alive"


# ─────────────────────────────────────────────
# 主流程
# ─────────────────────────────────────────────

def find_out_dir(ku1):
    pattern = os.path.join(SWEEP_DIR, f"Ku1_{ku1:.1e}_Ms_*.out")
    matches = glob.glob(pattern)
    if not matches:
        # 尝试整数格式
        pattern2 = os.path.join(SWEEP_DIR, f"Ku1_{float(ku1):.1e}_Ms_*.out")
        matches = glob.glob(pattern2)
    return matches[0] if matches else None


def analyze_ku1(ku1):
    out_dir = find_out_dir(ku1)
    if out_dir is None:
        print(f"  [警告] 找不到 Ku1={ku1} 的输出目录，跳过")
        return None

    results = []
    for idx in SAMPLE_INDICES:
        ovf_path = os.path.join(out_dir, f"m{idx:06d}.ovf")
        if not os.path.exists(ovf_path):
            print(f"    [缺失] {ovf_path}")
            results.append((idx * 0.1, None, None, "missing"))
            continue
        try:
            field = df.Field.from_file(ovf_path)
            R, r, status = compute_hopfion_Rr(field)
            del field   # 释放内存
            results.append((idx * 0.1, R, r, status))
            print(f"    t={idx*0.1:.1f}ns  R={f'{R:.2f}nm' if R else 'N/A':>8s}  "
                  f"r={f'{r:.2f}nm' if r else 'N/A':>8s}  [{status}]")
        except Exception as e:
            print(f"    [错误] {ovf_path}: {e}")
            results.append((idx * 0.1, None, None, "error"))

    return results


def plot_Rr_vs_time(all_data):
    """为每个 Ku1 画 R(t) 和 r(t) 曲线"""
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    colors = plt.cm.plasma(np.linspace(0.1, 0.9, len(KU1_LIST)))

    for (ku1, data), color in zip(all_data.items(), colors):
        if data is None:
            continue
        ts   = [d[0] for d in data]
        Rs   = [d[1] for d in data]
        rs   = [d[2] for d in data]
        label = f"Ku1={ku1:.0f} J/m³"

        # 只画有效点
        ts_R = [t for t, R in zip(ts, Rs) if R is not None]
        Rs_v = [R for R in Rs if R is not None]
        ts_r = [t for t, r in zip(ts, rs) if r is not None]
        rs_v = [r for r in rs if r is not None]

        if ts_R:
            axes[0].plot(ts_R, Rs_v, 'o-', color=color, label=label, markersize=5)
        if ts_r:
            axes[1].plot(ts_r, rs_v, 's-', color=color, label=label, markersize=5)

    for ax, ylabel, title in zip(
        axes,
        ["R (nm)", "r (nm)"],
        ["Major Radius R vs Time", "Tube Radius r vs Time"]
    ):
        ax.set_xlabel("Time (ns)")
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)

    plt.suptitle("Frustrated FM Hopfion — Anisotropy Sweep R/r vs Time", fontsize=12)
    plt.tight_layout()
    out_path = os.path.join(RESULTS_DIR, "R_r_vs_time.png")
    plt.savefig(out_path, dpi=200)
    plt.close()
    print(f"\n[图] 时间线图已保存: {out_path}")


def plot_summary(all_data):
    """末帧 R, r vs Ku1 汇总图"""
    ku1_arr, R_arr, r_arr, status_arr = [], [], [], []
    for ku1, data in all_data.items():
        if data is None:
            continue
        # 取最后一个有效帧
        last = None
        for d in reversed(data):
            if d[1] is not None:
                last = d
                break
        ku1_arr.append(ku1)
        R_arr.append(last[1] if last else None)
        r_arr.append(last[2] if last else None)
        status_arr.append(last[3] if last else "missing")

    fig, ax = plt.subplots(figsize=(8, 5))
    for ku1, R, r, st in zip(ku1_arr, R_arr, r_arr, status_arr):
        if R is not None:
            ax.scatter(ku1, R, marker='o', s=80, color='steelblue',
                       zorder=5, label='R (major)' if ku1 == ku1_arr[0] else "")
        if r is not None:
            ax.scatter(ku1, r, marker='s', s=80, color='tomato',
                       zorder=5, label='r (tube)' if ku1 == ku1_arr[0] else "")
        if st not in ('alive',):
            ax.axvline(x=ku1, color='gray', linestyle='--', alpha=0.4)
            ax.text(ku1, 1, st, fontsize=7, ha='center', color='gray')

    ku1_valid = [k for k, R in zip(ku1_arr, R_arr) if R is not None]
    R_valid   = [R for R in R_arr if R is not None]
    r_valid   = [r for r in r_arr if r is not None]
    if len(ku1_valid) > 1:
        ax.plot(ku1_valid, R_valid, '--', color='steelblue', alpha=0.5)
    if len(ku1_valid) > 1 and r_valid:
        ku1_r = [k for k, r in zip(ku1_arr, r_arr) if r is not None]
        ax.plot(ku1_r, r_valid, '--', color='tomato', alpha=0.5)

    ax.set_xlabel("Ku1 (J/m³)")
    ax.set_ylabel("Size (nm)")
    ax.set_title("Hopfion Final-Frame Size vs Anisotropy\n(Frustrated FM, t=3ns)")
    handles, labels = ax.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    ax.legend(by_label.values(), by_label.keys())
    ax.grid(True, alpha=0.3)

    out_path = os.path.join(RESULTS_DIR, "summary_Rr_vs_Ku1.png")
    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
    plt.close()
    print(f"[图] 汇总图已保存: {out_path}")


def write_survival_table(all_data):
    lines = ["Ku1 (J/m³)  |  t=0 R/r (nm)  |  t=3ns R/r (nm)  |  Final Status",
             "-" * 65]
    for ku1, data in all_data.items():
        if data is None:
            lines.append(f"{ku1:10.0f}  |  data missing")
            continue
        d0 = data[0]
        dl = None
        for d in reversed(data):
            if d[1] is not None:
                dl = d
                break
        r0 = f"{d0[1]:.1f}/{d0[2]:.1f}" if (d0[1] and d0[2]) else "N/A"
        rl = f"{dl[1]:.1f}/{dl[2]:.1f}" if (dl and dl[1] and dl[2]) else "N/A"
        st = dl[3] if dl else "missing"
        lines.append(f"{ku1:10.0f}  |  {r0:>14s}  |  {rl:>16s}  |  {st}")
    txt = "\n".join(lines)
    out_path = os.path.join(RESULTS_DIR, "survival_table.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(txt + "\n")
    print(f"[报告] 存活表已保存: {out_path}")
    print("\n" + txt)


def main():
    print("=" * 55)
    print("  各向异性扫描 Hopfion 存活分析")
    print("=" * 55)

    all_data = {}
    for ku1 in KU1_LIST:
        print(f"\n>>> Ku1 = {ku1:.0f} J/m³")
        all_data[ku1] = analyze_ku1(ku1)

    print("\n" + "=" * 55)
    print("  生成图表与报告...")
    print("=" * 55)
    plot_Rr_vs_time(all_data)
    plot_summary(all_data)
    write_survival_table(all_data)
    print("\n分析完成。")


if __name__ == "__main__":
    main()
