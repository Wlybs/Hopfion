"""
为论文几何（d=128nm, h=64nm）生成 FeGe Bloch Hopfion 初始态
参考: Khodzhaev & Turgut, J. Phys.: Condens. Matter 34, 225805 (2022)

网格: 64×64×32 @ 2nm = 128nm × 128nm × 64nm
圆柱: d=128nm (~2lambda), h=64nm (~lambda)
FeGe: lambda = 70nm
Hopfion: R=25nm (~lambda/3), r=12nm (~lambda/6)
"""
import sys, os
sys.path.insert(0, '/mnt/d/Research/Hopfion/95_shared_scripts')
from create_hopfion_AFM import generate_hopfion_ovf

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

generate_hopfion_ovf(
    Qh=1, p=1, q=1,
    R=25e-9,    # 环半径: ~lambda/3
    r=12e-9,    # 管半径: ~lambda/6
    xnodes=64, ynodes=64, znodes=32,
    xstepsize=2e-9, ystepsize=2e-9, zstepsize=2e-9,
    output_filename=os.path.join(OUTPUT_DIR, 'hopfion_128nm_init.ovf'),
    afm=None,
)

print("Grid: 64x64x32 @ 2nm = 128nm x 128nm x 64nm")
print("Hopfion: R=25nm, r=12nm  (lambda_FeGe=70nm)")
