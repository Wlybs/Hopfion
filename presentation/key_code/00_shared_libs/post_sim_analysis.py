"""
post_sim_analysis.py — 仿真完成后自动分析脚本
==============================================
扫描所有 .out 目录，检测收敛状态，提取关键指标，生成汇总报告。

用法：
    python scripts/post_sim_analysis.py [--hours 24] [--dir PATH] [--output report.md]

默认扫描过去 24 小时内修改的 .out 目录。
"""

import os
import sys
import time
import argparse
import re
from datetime import datetime, timedelta
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent


def find_out_dirs(root: Path, hours: float = 24) -> list[Path]:
    """找出过去 N 小时内修改的 .out 目录。"""
    cutoff = time.time() - hours * 3600
    results = []
    for dirpath in root.rglob("*.out"):
        if dirpath.is_dir():
            mtime = dirpath.stat().st_mtime
            if mtime >= cutoff:
                results.append(dirpath)
    return sorted(results, key=lambda p: p.stat().st_mtime, reverse=True)


def parse_log(log_path: Path) -> dict:
    """解析 mumax3 log.txt，提取关键信息。"""
    info = {
        "status": "unknown",
        "last_line": "",
        "error": None,
        "steps": 0,
        "final_time_ns": None,
    }
    if not log_path.exists():
        info["status"] = "no_log"
        return info

    lines = log_path.read_text(errors="ignore").splitlines()
    if not lines:
        info["status"] = "empty_log"
        return info

    info["last_line"] = lines[-1]

    # 检测错误
    for line in lines:
        if "panic" in line.lower() or "error" in line.lower():
            info["status"] = "error"
            info["error"] = line.strip()
            break

    # 检测正常完成：mumax3 结束时会输出引用信息块
    completed_markers = [
        "please cite the following",
        "vansteenkiste et al.",
        "total time",
        "//end",
    ]
    last_block = "\n".join(lines[-10:]).lower()
    if any(m in last_block for m in completed_markers):
        info["status"] = "completed"
    elif info["status"] == "unknown":
        info["status"] = "running_or_incomplete"

    # 计步数（mumax3 table.txt 行数）
    table = log_path.parent / "table.txt"
    if table.exists():
        try:
            with table.open() as f:
                step_lines = [l for l in f if not l.startswith("#") and l.strip()]
            info["steps"] = len(step_lines)
            if step_lines:
                cols = step_lines[-1].split()
                if cols:
                    try:
                        info["final_time_ns"] = float(cols[0]) * 1e9  # s → ns
                    except ValueError:
                        pass
        except Exception:
            pass

    return info


def parse_ovf_count(out_dir: Path) -> int:
    """统计输出的 .ovf 帧数。"""
    return len(list(out_dir.glob("m*.ovf")))


def extract_drift_summary(out_dir: Path) -> str:
    """
    尝试从分析结果读取漂移数据（如果已有 results/ 子目录）。
    返回简短摘要字符串，失败则返回 '—'。
    """
    # 查找相邻 results 目录
    results_dir = out_dir.parent / "results"
    if not results_dir.exists():
        return "—"

    summary_files = list(results_dir.glob("*summary*.txt")) + list(results_dir.glob("*table*.txt"))
    if not summary_files:
        return "—"

    try:
        content = summary_files[0].read_text(errors="ignore")
        # 取前 3 行非空内容
        lines = [l.strip() for l in content.splitlines() if l.strip()][:3]
        return " | ".join(lines) if lines else "—"
    except Exception:
        return "—"


def analyze_out_dirs(out_dirs: list[Path]) -> list[dict]:
    """对每个 .out 目录执行分析，返回结果列表。"""
    results = []
    for out_dir in out_dirs:
        log_info = parse_log(out_dir / "log.txt")
        ovf_count = parse_ovf_count(out_dir)
        drift = extract_drift_summary(out_dir)
        rel_path = out_dir.relative_to(PROJECT_ROOT)
        mtime = datetime.fromtimestamp(out_dir.stat().st_mtime)

        results.append({
            "path": str(rel_path),
            "status": log_info["status"],
            "steps": log_info["steps"],
            "final_time_ns": log_info["final_time_ns"],
            "ovf_frames": ovf_count,
            "drift_summary": drift,
            "error": log_info["error"],
            "modified": mtime.strftime("%m-%d %H:%M"),
            "last_line": log_info["last_line"][:80] if log_info["last_line"] else "",
        })
    return results


def generate_report(results: list[dict], hours: float) -> str:
    """生成 Markdown 格式报告。"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        f"# 仿真状态报告",
        f"",
        f"生成时间：{now}  |  扫描范围：过去 {hours:.0f} 小时  |  发现目录：{len(results)} 个",
        f"",
    ]

    # 状态分组
    completed = [r for r in results if r["status"] == "completed"]
    running = [r for r in results if r["status"] == "running_or_incomplete"]
    errors = [r for r in results if r["status"] == "error"]
    others = [r for r in results if r["status"] not in ("completed", "running_or_incomplete", "error")]

    # 汇总表
    lines += [
        "## 汇总",
        "",
        f"- ✅ 完成：{len(completed)}",
        f"- 🔄 运行中/未完成：{len(running)}",
        f"- ❌ 错误：{len(errors)}",
        f"- ❓ 其他：{len(others)}",
        "",
    ]

    # 详细表格
    lines += [
        "## 详细状态",
        "",
        "| 状态 | 目录 | 修改时间 | 步数 | 时长(ns) | OVF帧 | 漂移摘要 |",
        "|------|------|---------|------|---------|------|--------|",
    ]

    status_icon = {
        "completed": "✅",
        "running_or_incomplete": "🔄",
        "error": "❌",
        "no_log": "📭",
        "empty_log": "📭",
        "unknown": "❓",
    }

    for r in results:
        icon = status_icon.get(r["status"], "❓")
        t = f"{r['final_time_ns']:.2f}" if r["final_time_ns"] else "—"
        lines.append(
            f"| {icon} | `{r['path']}` | {r['modified']} | {r['steps']} | {t} | {r['ovf_frames']} | {r['drift_summary']} |"
        )

    # 错误详情
    if errors:
        lines += ["", "## 错误详情", ""]
        for r in errors:
            lines.append(f"### `{r['path']}`")
            lines.append(f"```\n{r['error']}\n```")
            lines.append("")

    # 待处理建议
    lines += ["", "## 建议操作", ""]
    if errors:
        lines.append(f"- ❌ {len(errors)} 个仿真报错，需检查参数后重启")
    if running:
        lines.append(f"- 🔄 {len(running)} 个可能仍在运行或已中断，确认进程状态")
    if completed:
        lines.append(f"- ✅ {len(completed)} 个已完成，可运行对应分析脚本生成图表")
    if not results:
        lines.append("- 过去 {hours:.0f} 小时内无新的仿真输出，无需操作")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="扫描仿真 .out 目录并生成状态报告")
    parser.add_argument("--hours", type=float, default=24, help="扫描过去 N 小时（默认 24）")
    parser.add_argument("--dir", type=str, default=str(PROJECT_ROOT), help="扫描根目录")
    parser.add_argument("--output", type=str, default="", help="输出报告文件路径（默认打印到 stdout）")
    args = parser.parse_args()

    scan_root = Path(args.dir)
    print(f"扫描目录：{scan_root}，时间范围：过去 {args.hours:.0f} 小时...", file=sys.stderr)

    out_dirs = find_out_dirs(scan_root, args.hours)
    if not out_dirs:
        print("未发现最近修改的 .out 目录。", file=sys.stderr)
        report = f"# 仿真状态报告\n\n{datetime.now().strftime('%Y-%m-%d %H:%M')} — 过去 {args.hours:.0f} 小时内无新仿真输出。\n"
    else:
        results = analyze_out_dirs(out_dirs)
        report = generate_report(results, args.hours)

    if args.output:
        Path(args.output).write_text(report, encoding="utf-8")
        print(f"报告已保存到：{args.output}", file=sys.stderr)
    else:
        print(report)


if __name__ == "__main__":
    main()
