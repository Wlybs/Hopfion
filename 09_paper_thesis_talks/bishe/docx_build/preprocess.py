#!/usr/bin/env python3
"""
预处理 thesis_v2/main.tex → preprocessed.tex
- 清掉 hduthesis 专有命令
- 展开 siunitx (\SI, \num, \si, \SIrange, \ang)
- 内联 \input{chapters/...}
- \abstract[cn/en] / \keywords / \printbibliography 转为标准 LaTeX
"""
import re
import os
from pathlib import Path

SRC_DIR = Path('/mnt/d/Research/Hopfion/09_paper_thesis_talks/bishe/thesis_v2')
OUT = Path('/mnt/d/Research/Hopfion/09_paper_thesis_talks/bishe/docx_build/preprocessed.tex')


def expand_siunitx(s: str) -> str:
    s = re.sub(r'\\SI\{([^}]*)\}\{([^}]*)\}',
               lambda m: f'{m.group(1)}\\,\\mathrm{{{m.group(2).strip()}}}', s)
    s = re.sub(r'\\SIrange\{([^}]*)\}\{([^}]*)\}\{([^}]*)\}',
               lambda m: f'{m.group(1)}\\text{{--}}{m.group(2)}\\,\\mathrm{{{m.group(3).strip()}}}', s)
    s = re.sub(r'\\num\{([^}]*)\}', lambda m: num_str(m.group(1)), s)
    s = re.sub(r'\\si\{([^}]*)\}', lambda m: f'\\mathrm{{{m.group(1).strip()}}}', s)
    s = re.sub(r'\\ang\{([^}]*)\}', lambda m: f'{m.group(1)}^{{\\circ}}', s)
    return s


def num_str(n: str) -> str:
    n = n.strip()
    if re.match(r'^-?\d+\.?\d*[eE]-?\d+$', n):
        base, exp = re.split(r'[eE]', n)
        exp = int(exp)
        if float(base) == 1.0:
            return f'10^{{{exp}}}'
        return f'{base}\\times10^{{{exp}}}'
    return n


def inline_inputs(tex: str, base_dir: Path) -> str:
    """Recursively replace \\input{path} with file contents."""
    def repl(m):
        path = m.group(1).strip()
        if not path.endswith('.tex'):
            path += '.tex'
        full = base_dir / path
        if not full.exists():
            return f'% MISSING: {path}\n'
        content = full.read_text(encoding='utf-8')
        return inline_inputs(content, base_dir)
    return re.sub(r'\\input\{([^}]+)\}', repl, tex)


def strip_hduthesis(s: str) -> str:
    # Strip document class and hduset block (multiline)
    s = re.sub(r'\\documentclass\s*(?:\[[^\]]*\])?\s*\{[^}]*\}', '', s, flags=re.DOTALL)
    # \hduset{ ... } — balanced braces, simple greedy until matching close
    s = strip_balanced(s, r'\\hduset')
    # Strip class-specific single commands
    for cmd in [r'\\maketitle', r'\\commitment', r'\\tableofcontents',
                r'\\usepackage\{siunitx\}', r'\\printbibliography']:
        s = re.sub(cmd, '', s)
    # \usepackage{xxx} — keep harmless ones, drop hdu-specific
    s = re.sub(r'\\usepackage\{siunitx\}\s*', '', s)
    return s


def strip_balanced(s: str, cmd_pattern: str) -> str:
    """Remove \\cmd{ ... } with balanced braces."""
    out = []
    i = 0
    while i < len(s):
        m = re.match(cmd_pattern, s[i:])
        if m:
            # skip past cmd and opening brace
            j = i + m.end()
            while j < len(s) and s[j] in ' \t\n':
                j += 1
            if j < len(s) and s[j] == '{':
                depth = 1
                j += 1
                while j < len(s) and depth > 0:
                    if s[j] == '{':
                        depth += 1
                    elif s[j] == '}':
                        depth -= 1
                    j += 1
                i = j
                continue
        out.append(s[i])
        i += 1
    return ''.join(out)


def transform_custom_envs(s: str) -> str:
    # \begin{abstract}[cn] ... \end{abstract}
    s = re.sub(
        r'\\begin\{abstract\}\s*\[cn\](.*?)\\end\{abstract\}',
        lambda m: '\\section*{摘\\quad 要}\n' + m.group(1),
        s, flags=re.DOTALL,
    )
    s = re.sub(
        r'\\begin\{abstract\}\s*\[en\](.*?)\\end\{abstract\}',
        lambda m: '\\section*{ABSTRACT}\n' + m.group(1),
        s, flags=re.DOTALL,
    )
    # \keywords{x, y, z}  →  \textbf{关键词：} x, y, z  (after 中文摘要)
    # \keywords{x, y, z}  →  \textbf{Key words:} x, y, z (after 英文 — heuristic: second occurrence)
    occurrences = [0]
    def kw_repl(m):
        occurrences[0] += 1
        label = '\\textbf{关键词：}' if occurrences[0] == 1 else '\\textbf{Key words: }'
        return f'\n\n{label} {m.group(1)}'
    s = re.sub(r'\\keywords\{([^}]+)\}', kw_repl, s)
    return s


def cref_to_ref(s: str) -> str:
    # \cref{x} → Ref. \ref{x}; pandoc 可识别 \ref
    s = re.sub(r'\\cref\{([^}]+)\}', r'\\ref{\1}', s)
    s = re.sub(r'\\Cref\{([^}]+)\}', r'\\ref{\1}', s)
    return s


def main():
    main_tex = (SRC_DIR / 'main.tex').read_text(encoding='utf-8')
    # Inline all \input{chapters/...}
    full = inline_inputs(main_tex, SRC_DIR)
    # Strip hduthesis preamble
    full = strip_hduthesis(full)
    # Transform custom environments
    full = transform_custom_envs(full)
    # Expand siunitx
    full = expand_siunitx(full)
    # cref → ref
    full = cref_to_ref(full)
    # Add minimal preamble for pandoc
    preamble = r"""\documentclass{article}
\usepackage{graphicx}
\usepackage{amsmath,amssymb}
\usepackage{hyperref}
\graphicspath{{figures/}{./figures/}{/mnt/d/Research/Hopfion/09_paper_thesis_talks/bishe/thesis_v2/figures/}}
"""
    # Replace everything before \begin{document} with minimal preamble
    m = re.search(r'\\begin\{document\}', full)
    if m:
        body = full[m.start():]
    else:
        body = '\\begin{document}\n' + full + '\n\\end{document}'
    full = preamble + body

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(full, encoding='utf-8')
    print(f'Wrote {OUT} ({len(full)} chars)')

    # Quick sanity check
    remaining = re.findall(r'\\(SI|num|si|SIrange|hduset|commitment|keywords|printbibliography)\b', full)
    if remaining:
        print(f'WARNING: unexpanded commands remain: {set(remaining)}')
    else:
        print('OK: all target commands expanded.')


if __name__ == '__main__':
    main()
