"""快速测试 paper_style 在 WSL+Windows 字体下能否渲染中文。
跑完检查 ./_test_paper_style.png。
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from paper_style import (setup_paper_style, COLORS, save_paper_fig,
                          add_ref_line, panel_label, shared_legend_above)

setup_paper_style()

t = np.linspace(0, 1, 100)
r8 = 2.6 + 0.3 * np.exp(-t * 3) * np.cos(2 * np.pi * 5 * t)
r12 = 2.6 + 0.6 * np.exp(-t * 2) - 0.05 * t

fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))

# 两个 panel 的数据线一致，legend 只标一次（figure 顶部）。参考线只画灰虚线，
# 数值在论文 caption 写，图内不放文字。
axes[0].plot(t, r8,  "o-", color=COLORS["primary"],   label=r"初始 $R=8,\,r=4$ nm")
axes[0].plot(t, r12, "s-", color=COLORS["secondary"], label=r"初始 $R=12,\,r=5$ nm")
add_ref_line(axes[0], 2.6)
axes[0].set_xlabel(r"时间 $t$ (ns)")
axes[0].set_ylabel(r"大半径 $R$ (nm)")

axes[1].plot(t, r8 * 0.8,  "o-", color=COLORS["primary"],   label=r"初始 $R=8,\,r=4$ nm")
axes[1].plot(t, r12 * 0.85, "s-", color=COLORS["secondary"], label=r"初始 $R=12,\,r=5$ nm")
add_ref_line(axes[1], 2.16)
axes[1].set_xlabel(r"时间 $t$ (ns)")
axes[1].set_ylabel(r"管半径 $r$ (nm)")

# figure 顶部共享 legend（左右两个 axes 数据线相同，只标一次）
shared_legend_above(fig, axes[0], ncol=2, y=1.02)

# panel 编号在每个 axes 框正上方左侧
panel_label(fig, axes[0], "(a)")
panel_label(fig, axes[1], "(b)")

save_paper_fig(fig, os.path.join(os.path.dirname(os.path.abspath(__file__)), "_test_paper_style.png"))
print("OK -> _test_paper_style.png")
