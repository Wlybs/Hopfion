#!/usr/bin/env bash
# morning_report.sh — 晨间仿真状态报告（headless Claude）
# ============================================================
# 用法：
#   bash 95_shared_scripts/morning_report.sh            # 检查过去 24h，结果打印到终端
#   bash 95_shared_scripts/morning_report.sh --hours 48 # 检查过去 48h
#   bash 95_shared_scripts/morning_report.sh --save     # 同时保存到 daily_report.md
#
# 依赖：
#   - claude CLI 已安装并完成登录（claude --version 可用）
#   - Python 3.x（用于 post_sim_analysis.py 预扫描）

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
HOURS=24
SAVE_REPORT=false
REPORT_FILE="$PROJECT_ROOT/daily_report.md"

# 解析参数
while [[ $# -gt 0 ]]; do
    case "$1" in
        --hours) HOURS="$2"; shift 2 ;;
        --save)  SAVE_REPORT=true; shift ;;
        *) echo "未知参数：$1"; exit 1 ;;
    esac
done

echo "===== Hopfion 晨间报告 ====="
echo "时间：$(date '+%Y-%m-%d %H:%M')"
echo "扫描范围：过去 ${HOURS} 小时"
echo ""

# Step 1：Python 预扫描，生成结构化数据供 Claude 分析
PRECHECK_FILE="$(mktemp /tmp/sim_precheck_XXXXXX.md)"
python3 "$SCRIPT_DIR/post_sim_analysis.py" --hours "$HOURS" --dir "$PROJECT_ROOT" --output "$PRECHECK_FILE" 2>/dev/null || {
    echo "[警告] post_sim_analysis.py 扫描失败，将仅依赖 Claude 分析"
    echo "扫描失败，请检查 Python 环境" > "$PRECHECK_FILE"
}

PRECHECK_CONTENT="$(cat "$PRECHECK_FILE")"
rm -f "$PRECHECK_FILE"

# Step 2：构造 Claude headless prompt
PROMPT="你是我的 Hopfion 仿真研究助手。以下是过去 ${HOURS} 小时内的仿真预扫描报告：

---
${PRECHECK_CONTENT}
---

请完成以下任务（用中文，简洁清晰）：

1. **仿真状态总结**：列出已完成、进行中、报错的仿真，各用一句话说明
2. **关键发现**：如有收敛数据，简要点评结果是否符合预期
3. **今日优先建议**：
   - 需要立即处理的报错（如有）
   - 建议下一步运行的分析脚本
   - 建议启动的下一组仿真（如有明显缺口）
4. **bd 任务建议**：列出 1-3 条应该添加到 bd 系统的任务标题

输出格式：Markdown，不超过 40 行。"

echo "正在调用 Claude 分析..."
echo ""

# Step 3：headless Claude 调用
if command -v claude &> /dev/null; then
    CLAUDE_OUTPUT="$(claude -p "$PROMPT" --allowedTools "" 2>/dev/null)"
    echo "$CLAUDE_OUTPUT"

    if [ "$SAVE_REPORT" = true ]; then
        {
            echo "# 晨间仿真报告 — $(date '+%Y-%m-%d')"
            echo ""
            echo "$CLAUDE_OUTPUT"
            echo ""
            echo "---"
            echo ""
            echo "## 原始扫描数据"
            echo ""
            echo "$PRECHECK_CONTENT"
        } > "$REPORT_FILE"
        echo ""
        echo "报告已保存到：$REPORT_FILE"
    fi
else
    echo "[错误] 未找到 claude CLI，请先安装：npm install -g @anthropic-ai/claude-code"
    echo ""
    echo "以下是 Python 预扫描结果（无 Claude 分析）："
    echo ""
    echo "$PRECHECK_CONTENT"

    if [ "$SAVE_REPORT" = true ]; then
        {
            echo "# 仿真扫描报告 — $(date '+%Y-%m-%d')"
            echo ""
            echo "> Claude CLI 不可用，仅显示原始扫描数据"
            echo ""
            echo "$PRECHECK_CONTENT"
        } > "$REPORT_FILE"
        echo "原始报告已保存到：$REPORT_FILE"
    fi
fi

echo ""
echo "===== 报告结束 ====="
