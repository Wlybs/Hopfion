"""
生成 FeGe bulk Hopfion 初始态 OVF
网格: 128×128×128, 2nm/格 → 256nm 立方体
Hopfion: R=40nm, r=20nm (λ_FeGe ≈ 103nm，R≈0.39λ)
"""
import sys
import os

sys.path.insert(0, '/mnt/d/Research/Hopfion/scripts')
from create_hopfion_AFM import generate_hopfion_ovf

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

generate_hopfion_ovf(
    Qh=1, p=1, q=1,
    R=40e-9,          # 环形环中心半径 (m)
    r=20e-9,          # 管道截面半径 (m)
    xnodes=128, ynodes=128, znodes=128,
    xstepsize=2e-9, ystepsize=2e-9, zstepsize=2e-9,
    output_filename=os.path.join(OUTPUT_DIR, 'bulk_hopfion_init.ovf'),
    afm=None,
)

print(f"OVF saved to: {OUTPUT_DIR}/bulk_hopfion_init.ovf")
print("Grid: 128x128x128 @ 2nm = 256nm box")
print("Hopfion: R=40nm, r=20nm")
