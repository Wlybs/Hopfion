"""
param_sweep.py — Hopfion 参数自动扫描脚本
功能: 生成 J2/J1 × J4/J1 的 3×3 参数网格，并发运行 mumax3，
      自动提取稳定性指标并排序输出。

用法:
    source /mnt/d/Research/Hopfion/hopfion/bin/activate
    python scripts/param_sweep.py --template <base.mx3> --init <init.ovf> \
                                  --outdir sweep_results --workers 3
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from itertools import product
from pathlib import Path

import discretisedfield as df
import numpy as np

# ──────────────────────────────────────────
# 1. 参数网格定义
# ──────────────────────────────────────────
J2_RATIOS = [-0.123, -0.164, -0.205]   # ±25% around reference
J4_RATIOS = [-0.062, -0.082, -0.102]   # ±25% around reference
PARAM_GRID = list(product(J2_RATIOS, J4_RATIOS))  # 9 combinations


# ──────────────────────────────────────────
# 2. .mx3 文件生成
# ──────────────────────────────────────────
def generate_mx3(template_path: Path, init_ovf: Path,
                 j2_ratio: float, j4_ratio: float,
                 outdir: Path) -> Path:
    """根据模板替换 J2/J4 比例，生成新的 .mx3 文件。"""
    template = template_path.read_text()

    # 替换 J2 和 J4 系数行
    template = re.sub(
        r'A_base \* \(-?[\d.]+\)\s*//.*J2',
        f'A_base * ({j2_ratio})    // J2 ratio={j2_ratio}',
        template
    )
    template = re.sub(
        r'A_base \* \(-?[\d.]+\)\s*//.*J4',
        f'A_base * ({j4_ratio})    // J4 ratio={j4_ratio}',
        template
    )

    # 替换初始 OVF 路径
    template = re.sub(
        r'm\.LoadFile\(".*?"\)',
        f'm.LoadFile("{init_ovf.resolve()}")',
        template
    )

    tag = f"J2_{j2_ratio:.3f}_J4_{j4_ratio:.3f}".replace('-', 'n').replace('.', 'p')
    mx3_path = outdir / f"sweep_{tag}.mx3"
    mx3_path.write_text(template)
    return mx3_path


# ──────────────────────────────────────────
# 3. 单次仿真运行
# ──────────────────────────────────────────
def run_simulation(mx3_path: Path, timeout: int = 600) -> dict:
    """运行单个 mumax3 仿真，返回结果字典。"""
    start = time.time()
    out_dir = mx3_path.with_suffix('.out')

    result = {
        "mx3": mx3_path.name,
        "j2_ratio": None,
        "j4_ratio": None,
        "status": "unknown",
        "elapsed_s": 0,
        "stability_score": 0.0,
        "mz_final": None,
        "mz_std": None,
        "drift_nm": None,
        "error": None,
    }

    # 从文件名解析参数
    m = re.search(r'J2_(n?[\dp]+)_J4_(n?[\dp]+)', mx3_path.stem)
    if m:
        result["j2_ratio"] = float(m.group(1).replace('n', '-').replace('p', '.'))
        result["j4_ratio"] = float(m.group(2).replace('n', '-').replace('p', '.'))

    try:
        proc = subprocess.run(
            ["mumax3", str(mx3_path)],
            capture_output=True, text=True, timeout=timeout
        )
        if proc.returncode != 0:
            result["status"] = "failed"
            result["error"] = proc.stderr[-500:]
            return result
    except subprocess.TimeoutExpired:
        result["status"] = "timeout"
        return result

    result["elapsed_s"] = round(time.time() - start, 1)

    # 提取最终状态指标
    ovf_files = sorted(out_dir.glob("m*.ovf"))
    if ovf_files:
        metrics = extract_stability_metrics(ovf_files)
        result.update(metrics)
        result["status"] = "done"
    else:
        result["status"] = "no_output"

    return result


# ──────────────────────────────────────────
# 4. 稳定性指标提取
# ──────────────────────────────────────────
def extract_stability_metrics(ovf_files: list) -> dict:
    """
    从 OVF 文件序列提取 Hopfion 稳定性指标。
    指标: 末态 mz 均值、标准差（非均匀 = 可能存在 Hopfion）、质心漂移量。
    """
    first = df.Field.from_file(ovf_files[0])
    last = df.Field.from_file(ovf_files[-1])

    mz_first = first.array[..., 2]
    mz_last = last.array[..., 2]

    mz_final = float(np.mean(mz_last))
    mz_std = float(np.std(mz_last))

    # 质心漂移 (沿 z 轴)
    drift_nm = _centroid_drift_nm(first, last, axis_idx=2)

    # 稳定性评分: 高方差（结构存活）+ 低漂移 = 好
    stability_score = mz_std * 10 - abs(drift_nm) * 0.1

    return {
        "mz_final": round(mz_final, 4),
        "mz_std": round(mz_std, 4),
        "drift_nm": round(drift_nm, 2),
        "stability_score": round(stability_score, 3),
    }


def _centroid_drift_nm(field_start: df.Field, field_end: df.Field,
                       axis_idx: int = 2) -> float:
    """计算 Hopfion 核心质心沿指定轴的漂移量 (nm)。"""
    def centroid(field, idx):
        m_comp = field.array[..., idx]
        m_min = np.min(m_comp)
        mask = m_comp < (m_min + 0.05)
        if not np.any(mask):
            return 0.0
        coords = np.array(np.where(mask)).T
        coords_real = field.mesh.region.pmin + coords * field.mesh.cell
        return float(np.mean(coords_real[:, idx]))

    c_start = centroid(field_start, axis_idx)
    c_end = centroid(field_end, axis_idx)
    return (c_end - c_start) * 1e9


# ──────────────────────────────────────────
# 5. 结果排序与输出
# ──────────────────────────────────────────
def print_ranking(results: list):
    ranked = sorted(results, key=lambda r: r.get("stability_score", -999), reverse=True)

    print("\n" + "=" * 75)
    print(f"{'Rank':<5} {'File':<35} {'J2/J1':>7} {'J4/J1':>7} "
          f"{'mz_std':>7} {'Drift(nm)':>10} {'Score':>7}")
    print("-" * 75)
    for i, r in enumerate(ranked, 1):
        status = r.get("status", "?")
        if status != "done":
            print(f"{i:<5} {r['mx3']:<35} {'ERR':>7} {'ERR':>7} "
                  f"{'ERR':>7} {'ERR':>10} {status:>7}")
            continue
        print(f"{i:<5} {r['mx3']:<35} {r['j2_ratio']:>7.3f} {r['j4_ratio']:>7.3f} "
              f"{r['mz_std']:>7.4f} {r['drift_nm']:>10.2f} {r['stability_score']:>7.3f}")
    print("=" * 75)
    print(f"Best config: {ranked[0]['mx3']}  (score={ranked[0].get('stability_score','?')})\n")
    return ranked


def save_results_json(results: list, outdir: Path):
    out = outdir / "sweep_results.json"
    out.write_text(json.dumps(results, indent=2))
    print(f"Results saved to {out}")


# ──────────────────────────────────────────
# 6. 主流程
# ──────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Hopfion J2×J4 Parameter Sweep")
    parser.add_argument("--template", required=True, help="Base .mx3 template file")
    parser.add_argument("--init", required=True, help="Initial OVF file for m.LoadFile()")
    parser.add_argument("--outdir", default="sweep_results", help="Output directory")
    parser.add_argument("--workers", type=int, default=3, help="Parallel mumax3 processes")
    parser.add_argument("--timeout", type=int, default=600, help="Per-job timeout (s)")
    args = parser.parse_args()

    template_path = Path(args.template).resolve()
    init_ovf = Path(args.init).resolve()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    print(f"Generating {len(PARAM_GRID)} .mx3 files...")
    mx3_files = [
        generate_mx3(template_path, init_ovf, j2, j4, outdir)
        for j2, j4 in PARAM_GRID
    ]

    print(f"Running {len(mx3_files)} simulations with {args.workers} parallel workers...\n")
    results = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(run_simulation, f, args.timeout): f for f in mx3_files}
        for future in as_completed(futures):
            r = future.result()
            results.append(r)
            print(f"  [{r['status'].upper()}] {r['mx3']}  score={r.get('stability_score','?')}")

    ranked = print_ranking(results)
    save_results_json(ranked, outdir)


if __name__ == "__main__":
    main()
