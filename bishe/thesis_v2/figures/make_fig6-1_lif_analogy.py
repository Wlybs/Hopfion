#!/usr/bin/env python3
# Fig 6-2: 霍普夫子双向控制与 LIF 神经元充放电的类比示意
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as _fm

for _fp in ('/mnt/c/Windows/Fonts/simhei.ttf', '/mnt/c/Windows/Fonts/msyh.ttc'):
    try:
        _fm.fontManager.addfont(_fp)
    except Exception:
        pass
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Noto Sans CJK SC', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['mathtext.fontset'] = 'stix'

fig, axes = plt.subplots(2, 1, figsize=(7.5, 7.8))
ax1, ax2 = axes

# ---- 左图：霍普夫子 z 方向位移（双 phase 类比充放电） ----
t1 = np.linspace(0, 0.5, 220)
z1 = 18.6 * (1 - np.exp(-t1 / 0.15))          # Phase 1: 指数型积累
t2 = np.linspace(0.5, 1.0, 220)
z2 = 18.6 * np.exp(-(t2 - 0.5) / 0.12) - 2    # Phase 2: 快速回落并反向
t_full = np.concatenate([t1, t2])
z_full = np.concatenate([z1, z2])

ax1.plot(t_full, z_full, color='#1756a8', linewidth=2.3, label=r'霍普夫子 $z$ 向位移')
ax1.axvspan(0, 0.5, alpha=0.18, color='#4caf50', label='Phase 1 srcZ@100 GHz 积累')
ax1.axvspan(0.5, 1.0, alpha=0.18, color='#ff9800', label='Phase 2 srcZ@1100 GHz 反转')
ax1.axhline(0, color='gray', linewidth=0.8, alpha=0.5)
ax1.annotate('', xy=(0.5, 14), xytext=(0.25, 14),
             arrowprops=dict(arrowstyle='->', color='#4caf50', lw=1.5))
ax1.text(0.28, 15.2, '充电', fontsize=12, color='#2e7d32')
ax1.annotate('', xy=(0.85, 0), xytext=(0.6, 12),
             arrowprops=dict(arrowstyle='->', color='#ff9800', lw=1.5))
ax1.text(0.64, 8, '放电', fontsize=12, color='#ef6c00')

ax1.set_xlabel('时间 (ns)', fontsize=15)
ax1.set_ylabel(r'$\Delta z$ (nm)', fontsize=15)
ax1.tick_params(axis='both', which='major', labelsize=13)
ax1.legend(loc='upper right', fontsize=13)
ax1.grid(alpha=0.3)
ax1.set_xlim(0, 1)
ax1.set_ylim(-5, 22)

# ---- 右图：LIF 神经元膜电位 ----
V_rest = -70
V_thr = -55
V_peak = 30
V_reset = -80

tL = np.linspace(0, 1.0, 500)
VL = np.zeros_like(tL)
charge_mask = tL < 0.5
VL[charge_mask] = V_rest + (V_thr - V_rest) * (1 - np.exp(-tL[charge_mask] / 0.15))
reset_fall = (tL >= 0.5) & (tL < 0.55)
VL[reset_fall] = V_thr + (V_reset - V_thr) * ((tL[reset_fall] - 0.5) / 0.05)
recover = tL >= 0.55
VL[recover] = V_reset + (V_rest - V_reset) * (1 - np.exp(-(tL[recover] - 0.55) / 0.18))

ax2.plot(tL, VL, color='#6a1b9a', linewidth=2.3, label=r'膜电位 $V_m$')
ax2.axhline(V_rest, color='gray', linewidth=0.6, alpha=0.5)
ax2.text(0.85, V_rest + 2, r'静息 $V_{\mathrm{rest}}$', fontsize=11, color='gray')
ax2.axvspan(0, 0.5, alpha=0.18, color='#4caf50', label='整合（突触输入累积）')
ax2.axvspan(0.5, 1.0, alpha=0.18, color='#ff9800', label='复位与恢复')

ax2.set_xlabel('时间 (相对单位)', fontsize=15)
ax2.set_ylabel(r'膜电位 $V_m$ (mV)', fontsize=15)
ax2.tick_params(axis='both', which='major', labelsize=13)
ax2.legend(loc='upper right', fontsize=13)
ax2.grid(alpha=0.3)
ax2.set_xlim(0, 1)
ax2.set_ylim(-95, -45)

plt.tight_layout()
out = '/mnt/d/Research/Hopfion/bishe/thesis_v2/figures/fig6-1_lif_analogy.png'
plt.savefig(out, dpi=180, bbox_inches='tight')
print(f'saved: {out}')
