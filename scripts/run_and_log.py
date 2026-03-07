"""
run_and_log.py — 仿真自动运行 + 科研日志记录
功能: 运行单个 mumax3 .mx3 脚本，自动提取参数和结果，
      追加写入 Markdown 日志，并执行 Git Commit。

用法:
    source /mnt/d/Research/Hopfion/hopfion/bin/activate
    python scripts/run_and_log.py <script.mx3> [--no-git] [--axis z]
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import discretisedfield as df
import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
LOG_FILE = REPO_ROOT / "research_log" / "log.md"


# ──────────────────────────────────────────
# 1. 文件 Hash
# ──────────────────────────────────────────
def sha256_short(path: Path) -> str:
    h = hashlib.sha256(path.read_bytes()).hexdigest()
    return h[:8]


# ──────────────────────────────────────────
# 2. 参数提取 (.mx3 解析)
# ──────────────────────────────────────────
def extract_mx3_params(mx3_path: Path) -> dict:
    """从 .mx3 脚本文本中提取关键物理参数。"""
    text = mx3_path.read_text()

    def find_val(pattern, default=None):
        m = re.search(pattern, text)
        return m.group(1).strip() if m else default

    return {
        "grid":      find_val(r'SetGridSize\(([^)]+)\)', 'unknown'),
        "cell_nm":   find_val(r'cellsize\s*:=\s*([\deE.+-]+)', 'unknown'),
        "Ms":        find_val(r'Ms_val\s*:=\s*([\deE.+-]+)', 'unknown'),
        "Aex":       find_val(r'A_base\s*:=\s*([\deE.+-]+)', 'unknown'),
        "J2_ratio":  find_val(r'A_base \* \(([-\d.]+)\)\s*//.*J2', 'N/A'),
        "J4_ratio":  find_val(r'A_base \* \(([-\d.]+)\)\s*//.*J4', 'N/A'),
        "Ku1":       find_val(r'Ku1_val\s*:=\s*([\deE.+-]+)', '0'),
        "DMI":       find_val(r'Dbulk\s*=\s*([\deE.+-]+)', '0'),
        "run_time":  find_val(r'run\(([\deE.+-]+)\)', 'unknown'),
        "init_ovf":  find_val(r'm\.LoadFile\("([^"]+)"\)', 'N/A'),
        "pbc":       find_val(r'SetPBC\(([^)]+)\)', '0,0,0'),
    }


# ──────────────────────────────────────────
# 3. 运行 mumax3
# ──────────────────────────────────────────
def run_mumax3(mx3_path: Path) -> tuple[bool, str]:
    """运行 mumax3，返回 (success, log_tail)。"""
    print(f"[mumax3] Running: {mx3_path.name} ...")
    proc = subprocess.run(
        ["mumax3", str(mx3_path)],
        capture_output=True, text=True
    )
    log_tail = (proc.stdout + proc.stderr)[-800:]
    success = proc.returncode == 0
    if not success:
        print(f"[mumax3] FAILED (returncode={proc.returncode})")
    else:
        print(f"[mumax3] Done.")
    return success, log_tail


# ──────────────────────────────────────────
# 4. 结果指标提取
# ──────────────────────────────────────────
def extract_results(out_dir: Path, axis: str = 'z') -> dict:
    """从输出 OVF 序列提取末态物理量。"""
    axis_idx = {'x': 0, 'y': 1, 'z': 2}[axis]
    ovf_files = sorted(out_dir.glob("m*.ovf"))

    if not ovf_files:
        return {"n_frames": 0, "mz_final": "N/A", "mz_std": "N/A",
                "drift_nm": "N/A", "survived": False}

    first = df.Field.from_file(ovf_files[0])
    last = df.Field.from_file(ovf_files[-1])

    m_last = last.array[..., axis_idx]
    mz_final = float(np.mean(m_last))
    mz_std = float(np.std(m_last))

    # 质心漂移估算
    def centroid_coord(field, idx):
        mc = field.array[..., idx]
        mask = mc < (np.min(mc) + 0.05)
        if not np.any(mask):
            return None
        coords = np.array(np.where(mask)).T
        real = field.mesh.region.pmin + coords * field.mesh.cell
        return float(np.mean(real[:, idx]))

    c0 = centroid_coord(first, axis_idx)
    c1 = centroid_coord(last, axis_idx)
    drift_nm = round((c1 - c0) * 1e9, 2) if (c0 is not None and c1 is not None) else "N/A"

    # 存活判断: 末态 mz 标准差 > 0.05 认为存在非均匀结构
    survived = mz_std > 0.05

    return {
        "n_frames": len(ovf_files),
        "mz_final": round(mz_final, 4),
        "mz_std": round(mz_std, 4),
        "drift_nm": drift_nm,
        "survived": survived,
    }


# ──────────────────────────────────────────
# 5. 写入 Markdown 日志
# ──────────────────────────────────────────
def write_log_entry(mx3_path: Path, params: dict, results: dict,
                    success: bool, mx3_hash: str, log_tail: str):
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    status_badge = "DONE" if success else "FAILED"
    survived_str = "YES" if results.get("survived") else "NO"

    entry = f"""
---

## [{timestamp}] `{mx3_path.name}` — {status_badge}

**File hash (SHA256):** `{mx3_hash}`

### Parameters

| Key | Value |
|-----|-------|
| Grid | `{params['grid']}` |
| Cell size | `{params['cell_nm']}` m |
| Ms | `{params['Ms']}` A/m |
| Aex (J1) | `{params['Aex']}` J/m |
| J2/J1 | `{params['J2_ratio']}` |
| J4/J1 | `{params['J4_ratio']}` |
| Ku1 | `{params['Ku1']}` J/m³ |
| DMI | `{params['DMI']}` T·m |
| Run time | `{params['run_time']}` s |
| Init OVF | `{params['init_ovf']}` |
| PBC | `{params['pbc']}` |

### Results

| Metric | Value |
|--------|-------|
| Frames saved | {results.get('n_frames', 'N/A')} |
| mz (final, mean) | {results.get('mz_final', 'N/A')} |
| mz (final, std) | {results.get('mz_std', 'N/A')} |
| Drift along axis | {results.get('drift_nm', 'N/A')} nm |
| Hopfion survived? | **{survived_str}** |

### Log (tail)

```
{log_tail[-400:]}
```

"""
    with open(LOG_FILE, 'a') as f:
        f.write(entry)
    print(f"[log] Entry written to {LOG_FILE}")


# ──────────────────────────────────────────
# 6. Git Commit
# ──────────────────────────────────────────
def git_commit_log(mx3_name: str, success: bool):
    status = "done" if success else "failed"
    msg = f"log: {mx3_name} [{status}] - auto research log"
    try:
        subprocess.run(
            ["git", "-C", str(REPO_ROOT), "add", str(LOG_FILE)],
            check=True, capture_output=True
        )
        subprocess.run(
            ["git", "-C", str(REPO_ROOT), "commit", "-m", msg],
            check=True, capture_output=True
        )
        print(f"[git] Committed log: '{msg}'")
    except subprocess.CalledProcessError as e:
        print(f"[git] Commit skipped: {e.stderr.decode().strip()[:200]}")


# ──────────────────────────────────────────
# 7. 主流程
# ──────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Run mumax3 + auto research log")
    parser.add_argument("mx3", help=".mx3 script to run")
    parser.add_argument("--axis", default='z', choices=['x', 'y', 'z'],
                        help="Hopfion ring axis for drift analysis")
    parser.add_argument("--no-git", action="store_true",
                        help="Skip git commit")
    args = parser.parse_args()

    mx3_path = Path(args.mx3).resolve()
    if not mx3_path.exists():
        print(f"ERROR: {mx3_path} not found")
        sys.exit(1)

    mx3_hash = sha256_short(mx3_path)
    params = extract_mx3_params(mx3_path)
    print(f"[params] {json.dumps(params, indent=2)}")

    success, log_tail = run_mumax3(mx3_path)

    out_dir = mx3_path.with_suffix('.out')
    results = extract_results(out_dir, axis=args.axis) if out_dir.exists() else {}

    write_log_entry(mx3_path, params, results, success, mx3_hash, log_tail)

    if not args.no_git:
        git_commit_log(mx3_path.name, success)

    print(f"\n[summary] survived={results.get('survived','?')}  "
          f"drift={results.get('drift_nm','?')} nm  "
          f"mz_std={results.get('mz_std','?')}")


if __name__ == "__main__":
    main()
