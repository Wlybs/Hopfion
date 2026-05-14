"""统一论文图风格 helper（毕设 thesis_v2 规范）。

用法：
    import sys; sys.path.insert(0, "/mnt/d/Research/Hopfion/scripts")
    from paper_style import setup_paper_style, COLORS, save_paper_fig
    setup_paper_style()
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.set_xlabel("时间 (ns)")
    ax.set_ylabel("R (nm)")
    save_paper_fig(fig, "out.png")

规范来源：bishe/thesis_v2/figures/fig3-* 系列的视觉风格 +
分析脚本 analyze_size_sweep.py 已有的中文标签风格。

字体策略：WSL 走 Windows 字体（msyh.ttc / simhei.ttf），无需 apt 装包。

**约定（论文图规范）**：
- 不调 `ax.set_title()` 和 `plt.suptitle()`——标题留给论文 caption
- 不写 panel "(a) xxx" 文字——论文用 subcaption 自动编号
- marker 小（默认 3），论文版主结论图要清晰不要喧宾夺主
"""
from __future__ import annotations
import matplotlib as mpl
import matplotlib.font_manager as fm
import numpy as np
from pathlib import Path

WIN_FONTS_DIR = Path("/mnt/c/Windows/Fonts")
THESIS_FONTS_DIR = Path("/mnt/d/Research/Hopfion/bishe/thesis_v2/fonts")

# 论文 main.tex 用 FandolSong + STIX Two Math。matplotlib 端用同款思源宋体
# (fonts/SourceHanSerifSC-Regular.otf)，等价衬线效果。fallback 到 Windows SimSun。
SERIF_FONT_FILES = [
    THESIS_FONTS_DIR / "SourceHanSerifSC-Regular.otf",
    THESIS_FONTS_DIR / "SourceHanSerifSC-Medium.otf",
    THESIS_FONTS_DIR / "SourceHanSerifSC-Bold.otf",
]
SERIF_FONT_FALLBACK = [
    WIN_FONTS_DIR / "simsun.ttc",
    WIN_FONTS_DIR / "simfang.ttf",
]

COLORS = {
    "primary":    "steelblue",
    "secondary":  "tomato",
    "tertiary":   "forestgreen",
    "quaternary": "darkorange",
    "quinary":    "purple",
    "ref":        "k",
    "sweep_cmap": "viridis",
}

_INITIALIZED = False


def setup_paper_style() -> None:
    """全局 matplotlib 配置（幂等）。"""
    global _INITIALIZED
    if _INITIALIZED:
        return

    for fp in SERIF_FONT_FILES + SERIF_FONT_FALLBACK:
        if fp.exists():
            try:
                fm.fontManager.addfont(str(fp))
            except Exception:
                pass

    mpl.rcParams.update({
        # 论文用 FandolSong/SourceHanSerifSC 衬线宋体 + STIX Two Math
        "font.family":     "serif",
        "font.serif":      ["Source Han Serif SC", "SimSun", "STIX Two Text", "DejaVu Serif"],
        "mathtext.fontset": "stix",
        "axes.unicode_minus": False,
        "font.size":       11,
        "axes.titlesize":  12,
        "axes.labelsize":  11,
        "legend.fontsize": 9,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "axes.grid":       True,
        "grid.alpha":      0.25,
        "grid.linestyle":  "--",
        "grid.linewidth":  0.4,
        "figure.dpi":      100,
        "savefig.dpi":     300,
        "savefig.bbox":    "tight",
        "lines.markersize": 3,
        "lines.linewidth":  1.3,
        "axes.spines.top":    True,   # 四边实线黑框（论文规范）
        "axes.spines.right":  True,
        "axes.linewidth":     1.0,
        "axes.edgecolor":     "black",
        "xtick.direction":    "in",   # 刻度朝内（论文规范）
        "ytick.direction":    "in",
        "xtick.top":          True,
        "ytick.right":        True,
        "xtick.major.size":   4,
        "ytick.major.size":   4,
    })
    _INITIALIZED = True


def save_paper_fig(fig, path, dpi: int = 300) -> None:
    """统一保存接口（tight_layout + 300 dpi + bbox=tight）。"""
    import matplotlib.pyplot as plt
    plt.tight_layout()
    fig.savefig(str(path), dpi=dpi, bbox_inches="tight")


def add_ref_line(ax, value: float, label: str | None = None,
                 color: str = "gray", **kwargs) -> None:
    """水平参考线（默认灰虚线，比黑色低调，不抢主线）。"""
    kwargs.setdefault("linestyle", "--")
    kwargs.setdefault("linewidth", 1.0)
    ax.axhline(value, color=color, label=label, **kwargs)


def legend_above(ax, ncol: int | None = None, **kwargs) -> None:
    """把 legend 放到 axes 黑框正上方（论文规范，无边框横排）。

    ncol 不传则按 legend 项数自动 ≤4。
    """
    handles, labels = ax.get_legend_handles_labels()
    if ncol is None:
        ncol = min(len(labels), 4) if labels else 1
    kwargs.setdefault("frameon", False)
    kwargs.setdefault("loc", "lower center")
    kwargs.setdefault("bbox_to_anchor", (0.5, 1.02))
    kwargs.setdefault("borderaxespad", 0.0)
    kwargs.setdefault("handlelength", 1.8)
    kwargs.setdefault("columnspacing", 1.2)
    ax.legend(handles, labels, ncol=ncol, **kwargs)


def panel_label(fig, ax, label: str, loc: str = "top_center_outside",
                fontsize: int = 12) -> None:
    """添加论文风格 panel 标号 (a)/(b)。

    loc:
      - "top_left_outside":   axes 框正上方左侧（默认，论文最常见）
      - "top_center_outside": axes 框正上方居中
      - "right_outside":      axes 右侧 figure 边缘外
      - "top_left":           axes 内部左上角
    """
    if loc == "top_left_outside":
        ax.annotate(label, xy=(0.0, 1.02), xycoords="axes fraction",
                    ha="left", va="bottom", fontsize=fontsize)
    elif loc == "top_center_outside":
        ax.annotate(label, xy=(0.5, 1.02), xycoords="axes fraction",
                    ha="center", va="bottom", fontsize=fontsize)
    elif loc == "right_outside":
        ax.annotate(label, xy=(1.02, 0.5), xycoords="axes fraction",
                    ha="left", va="center", fontsize=fontsize)
    elif loc == "top_left":
        ax.annotate(label, xy=(0.03, 0.95), xycoords="axes fraction",
                    ha="left", va="top", fontsize=fontsize,
                    fontweight="bold")


def shared_legend_above(fig, source_ax, ncol: int | None = None,
                        y: float = 1.0, **kwargs) -> None:
    """整 figure 顶部一个共享 legend（多 panel legend 内容一致时用）。

    source_ax: 从哪个 ax 取 handles/labels（一般传第一个 axes）
    y: legend 在 figure 中的纵坐标（1.0 = 顶部）
    """
    handles, labels = source_ax.get_legend_handles_labels()
    if ncol is None:
        ncol = min(len(labels), 5) if labels else 1
    kwargs.setdefault("frameon", False)
    kwargs.setdefault("loc", "lower center")
    kwargs.setdefault("bbox_to_anchor", (0.5, y))
    kwargs.setdefault("borderaxespad", 0.0)
    kwargs.setdefault("handlelength", 1.8)
    kwargs.setdefault("columnspacing", 1.6)
    fig.legend(handles, labels, ncol=ncol, **kwargs)


def sweep_colors(n: int, cmap: str = "viridis"):
    """生成 n 色的渐变 color list。用于 sweep 实验（如 Ku1 sweep）。"""
    import matplotlib.pyplot as plt
    return plt.cm.get_cmap(cmap)(np.linspace(0.1, 0.9, n))
