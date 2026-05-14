"""B06 论文风格重画 — 复用 analyze_size_sweep.py 的 sample_run，只改绘图。

输出：size_convergence.png（论文风格，取代 size_convergence_english.png 旧版）
"""
import os, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# 引入统一论文风格 helper
sys.path.insert(0, "/mnt/d/Research/Hopfion/scripts")
from paper_style import (setup_paper_style, COLORS, save_paper_fig,
                          add_ref_line, panel_label, shared_legend_above)

# 复用现有 analyzer 的数据加载/几何拟合
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, THIS_DIR)
from analyze_size_sweep import sample_run, REF_R, REF_r

setup_paper_style()

# R8r4: 21 帧 0→1ns，步长 50ps
r8_data = sample_run(
    os.path.join(THIS_DIR, "R8r4_Ku0.out"),
    t_offset=0.0, dt=5e-11, step=1, label="R8r4",
)
# R12r5: 100 帧 0→4.95ns（continue 段已合并到同一目录），步长 50ps
r12_data = sample_run(
    os.path.join(THIS_DIR, "R12r5_Ku0.out"),
    t_offset=0.0, dt=5e-11, step=2, label="R12r5",
)

fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))

for data, color, marker, label in [
    (r8_data,  COLORS["primary"],   "o", r"初始 $R=8,\,r=4$ nm"),
    (r12_data, COLORS["secondary"], "s", r"初始 $R=12,\,r=5$ nm"),
]:
    ts_R = [d[0] for d in data if d[1] is not None]
    Rs_v = [d[1] for d in data if d[1] is not None]
    ts_r = [d[0] for d in data if d[2] is not None]
    rs_v = [d[2] for d in data if d[2] is not None]
    if ts_R:
        axes[0].plot(ts_R, Rs_v, marker + "-", color=color, label=label)
    if ts_r:
        axes[1].plot(ts_r, rs_v, marker + "-", color=color, label=label)

# 参考线只画灰虚线，数值留 caption
add_ref_line(axes[0], REF_R)
add_ref_line(axes[1], REF_r)

axes[0].set_xlabel(r"时间 $t$ (ns)")
axes[0].set_ylabel(r"大半径 $R$ (nm)")

axes[1].set_xlabel(r"时间 $t$ (ns)")
axes[1].set_ylabel(r"管半径 $r$ (nm)")

# 共享 legend 顶部外
shared_legend_above(fig, axes[0], ncol=2, y=1.02)

# panel 编号居中放轴外
panel_label(fig, axes[0], "(a)")
panel_label(fig, axes[1], "(b)")

out_dir = os.path.join(THIS_DIR, "results")
os.makedirs(out_dir, exist_ok=True)
out_png = os.path.join(out_dir, "size_convergence.png")
save_paper_fig(fig, out_png)
print(f"[OK] {out_png}")
