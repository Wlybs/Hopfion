#!/usr/bin/env python3
"""md_to_pdf.py — markdown → HTML (Python stdlib) → PDF (Edge headless).

Usage:
    python3 md_to_pdf.py <input.md> [input2.md ...]

Each input.md becomes input.pdf in the same directory. No external pip deps.
"""

from __future__ import annotations

import html
import os
import re
import subprocess
import sys
from pathlib import Path

EDGE_EXE = "/mnt/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"

HTML_HEADER = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<style>
@page {{ size: A4; margin: 1.5cm 1.8cm; }}
body {{
  font-family: "Microsoft YaHei", "Segoe UI", "PingFang SC", sans-serif;
  font-size: 10.5pt;
  line-height: 1.6;
  color: #1a1a1a;
  max-width: 100%;
}}
h1 {{ font-size: 20pt; border-bottom: 2px solid #333; padding-bottom: 0.25em; margin: 0.3em 0 0.6em; }}
h2 {{ font-size: 15pt; border-bottom: 1px solid #999; padding-bottom: 0.15em; margin: 1.4em 0 0.5em; }}
h3 {{ font-size: 12.5pt; margin: 1.1em 0 0.4em; color: #222; }}
h4 {{ font-size: 11pt; margin: 0.9em 0 0.3em; color: #333; }}
code {{
  font-family: "Consolas", "Cascadia Mono", "DejaVu Sans Mono", monospace;
  background: #f0f0f0;
  padding: 1px 5px;
  border-radius: 3px;
  font-size: 0.92em;
}}
pre {{
  background: #f7f7f7;
  border-left: 3px solid #888;
  padding: 0.55em 0.9em;
  overflow-x: auto;
  font-family: "Consolas", "Cascadia Mono", "DejaVu Sans Mono", monospace;
  font-size: 9pt;
  line-height: 1.35;
  white-space: pre;
  page-break-inside: avoid;
}}
pre code {{ background: none; padding: 0; font-size: inherit; }}
blockquote {{
  border-left: 4px solid #bbb;
  margin: 0.8em 0;
  padding: 0.2em 1em;
  color: #555;
  background: #fafafa;
}}
table {{
  border-collapse: collapse;
  margin: 0.8em 0;
  width: 100%;
  page-break-inside: avoid;
}}
th, td {{
  border: 1px solid #ccc;
  padding: 4px 9px;
  text-align: left;
  font-size: 10pt;
  vertical-align: top;
}}
th {{ background: #ececec; font-weight: 600; }}
hr {{ border: 0; border-top: 1px solid #ccc; margin: 1.4em 0; }}
ul, ol {{ padding-left: 1.5em; margin: 0.4em 0; }}
li {{ margin: 0.18em 0; }}
strong {{ color: #000; }}
a {{ color: #1565c0; text-decoration: none; }}
p {{ margin: 0.45em 0; }}
</style>
</head>
<body>
"""

HTML_FOOTER = "</body></html>"


def esc(s: str) -> str:
    return html.escape(s, quote=False)


def render_inline(text: str) -> str:
    """Process inline markdown. Order matters."""
    # Protect inline code
    codes: list[str] = []
    def repl_code(m: re.Match) -> str:
        codes.append(m.group(1))
        return f"\x01C{len(codes) - 1}\x01"
    text = re.sub(r"`([^`]+)`", repl_code, text)

    # Protect math ($$...$$ and $...$)
    maths: list[str] = []
    def repl_math(m: re.Match) -> str:
        maths.append(m.group(0))
        return f"\x01M{len(maths) - 1}\x01"
    text = re.sub(r"\$\$.+?\$\$", repl_math, text, flags=re.DOTALL)
    text = re.sub(r"\$[^\$\n]+\$", repl_math, text)

    # HTML escape the rest
    text = esc(text)

    # Links [text](url)
    text = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        lambda m: f'<a href="{m.group(2)}">{m.group(1)}</a>',
        text,
    )

    # Bold **...**
    text = re.sub(r"\*\*([^\*]+)\*\*", r"<strong>\1</strong>", text)

    # Restore code
    def restore_code(m: re.Match) -> str:
        return "<code>" + esc(codes[int(m.group(1))]) + "</code>"
    text = re.sub(r"\x01C(\d+)\x01", restore_code, text)

    # Restore math (rendered as monospace verbatim — no MathJax)
    def restore_math(m: re.Match) -> str:
        s = maths[int(m.group(1))]
        return '<code class="math">' + esc(s) + "</code>"
    text = re.sub(r"\x01M(\d+)\x01", restore_math, text)

    return text


def is_table_row(line: str) -> bool:
    s = line.strip()
    return s.startswith("|") and s.endswith("|")


def parse_table(lines: list[str], i: int) -> tuple[str, int]:
    header = [c.strip() for c in lines[i].strip().strip("|").split("|")]
    n = len(header)
    out = ["<table><thead><tr>"]
    for c in header:
        out.append("<th>" + render_inline(c) + "</th>")
    out.append("</tr></thead><tbody>")
    j = i + 2
    while j < len(lines) and is_table_row(lines[j]):
        cells = [c.strip() for c in lines[j].strip().strip("|").split("|")]
        while len(cells) < n:
            cells.append("")
        out.append("<tr>")
        for c in cells[:n]:
            out.append("<td>" + render_inline(c) + "</td>")
        out.append("</tr>")
        j += 1
    out.append("</tbody></table>")
    return "".join(out), j


def md_to_html(md_text: str, title: str) -> str:
    lines = md_text.split("\n")
    out: list[str] = []
    i = 0
    in_code = False
    code_buf: list[str] = []
    in_list: str | None = None

    def close_list() -> None:
        nonlocal in_list
        if in_list:
            out.append(f"</{in_list}>")
            in_list = None

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith("```"):
            if not in_code:
                close_list()
                in_code = True
                code_buf = []
            else:
                in_code = False
                out.append("<pre><code>" + esc("\n".join(code_buf)) + "</code></pre>")
            i += 1
            continue
        if in_code:
            code_buf.append(line)
            i += 1
            continue

        m = re.match(r"^(#{1,6})\s+(.+)$", line)
        if m:
            close_list()
            lvl = len(m.group(1))
            out.append(f"<h{lvl}>{render_inline(m.group(2))}</h{lvl}>")
            i += 1
            continue

        if re.match(r"^---+\s*$", line):
            close_list()
            out.append("<hr>")
            i += 1
            continue

        if (
            is_table_row(line)
            and i + 1 < len(lines)
            and re.match(r"^\s*\|[\s\|:\-]+\|\s*$", lines[i + 1])
        ):
            close_list()
            t, end = parse_table(lines, i)
            out.append(t)
            i = end
            continue

        if stripped.startswith(">"):
            close_list()
            qs: list[str] = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                qs.append(lines[i].strip().lstrip(">").strip())
                i += 1
            out.append("<blockquote>" + render_inline(" ".join(qs)) + "</blockquote>")
            continue

        if re.match(r"^[\-\*]\s+", line):
            if in_list != "ul":
                close_list()
                out.append("<ul>")
                in_list = "ul"
            content = re.sub(r"^[\-\*]\s+", "", line)
            out.append("<li>" + render_inline(content) + "</li>")
            i += 1
            continue

        if re.match(r"^\d+\.\s+", line):
            if in_list != "ol":
                close_list()
                out.append("<ol>")
                in_list = "ol"
            content = re.sub(r"^\d+\.\s+", "", line)
            out.append("<li>" + render_inline(content) + "</li>")
            i += 1
            continue

        if stripped == "":
            close_list()
            i += 1
            continue

        close_list()
        out.append("<p>" + render_inline(line) + "</p>")
        i += 1

    close_list()
    return HTML_HEADER.format(title=esc(title)) + "\n".join(out) + HTML_FOOTER


def wsl_to_win_url(p: Path) -> str:
    win = subprocess.check_output(["wslpath", "-w", str(p)]).decode().strip()
    return "file:///" + win.replace("\\", "/")


def wsl_to_win(p: Path) -> str:
    return subprocess.check_output(["wslpath", "-w", str(p)]).decode().strip()


def convert_one(md_path: Path) -> bool:
    md_text = md_path.read_text(encoding="utf-8")
    title_match = re.search(r"^#\s+(.+)$", md_text, re.MULTILINE)
    title = (
        re.sub(r"[\*`]", "", title_match.group(1)) if title_match else md_path.stem
    )

    html_str = md_to_html(md_text, title)
    html_path = md_path.with_suffix(".html")
    html_path.write_text(html_str, encoding="utf-8")

    pdf_path = md_path.with_suffix(".pdf")

    cmd = [
        EDGE_EXE,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--no-pdf-header-footer",
        f"--print-to-pdf={wsl_to_win(pdf_path)}",
        wsl_to_win_url(html_path),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    ok = pdf_path.exists() and pdf_path.stat().st_size > 1000

    if ok:
        html_path.unlink()
        print(f"OK    {pdf_path.name}  ({pdf_path.stat().st_size // 1024} KB)")
    else:
        print(f"FAIL  {md_path.name}", file=sys.stderr)
        print(res.stderr[-500:], file=sys.stderr)
    return ok


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    fails = 0
    for arg in sys.argv[1:]:
        p = Path(arg).resolve()
        if not p.exists():
            print(f"MISSING {p}", file=sys.stderr)
            fails += 1
            continue
        if not convert_one(p):
            fails += 1
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
