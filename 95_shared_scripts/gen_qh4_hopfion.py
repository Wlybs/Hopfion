import sys
from create_hopfion_AFM_v2 import generate_hopfion_ovf

generate_hopfion_ovf(
    Qh=4, p=2, q=2,
    R=12e-9, r=6e-9,
    xnodes=100, ynodes=100, znodes=100,
    xstepsize=5e-10, ystepsize=5e-10, zstepsize=5e-10,
    output_filename="hopfion_Qh4_p2q2.ovf",
    axis='z'
)
