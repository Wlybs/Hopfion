import sys
import os
from create_hopfion_AFM_v2 import generate_hopfion_ovf

configs = [
    {"Qh": 1, "p": 1, "q": 1, "out": "hopfion_Qh1_p1q1.ovf"},
    {"Qh": 2, "p": 2, "q": 1, "out": "hopfion_Qh2_p2q1.ovf"},
    {"Qh": 2, "p": 1, "q": 2, "out": "hopfion_Qh2_p1q2.ovf"},
]

for cfg in configs:
    generate_hopfion_ovf(
        Qh=cfg["Qh"], p=cfg["p"], q=cfg["q"],
        R=12e-9, r=6e-9,
        xnodes=100, ynodes=100, znodes=100,
        xstepsize=5e-10, ystepsize=5e-10, zstepsize=5e-10,
        output_filename=cfg["out"],
        axis='z'
    )
