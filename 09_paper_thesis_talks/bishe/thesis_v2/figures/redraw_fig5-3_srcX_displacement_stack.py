#!/usr/bin/env python3
"""redraw_fig5-3_srcX_displacement_stack.py

将原有 4 张独立子图 (fig4-3_srcX_displacement_{a,b,c,d}.png) 垂直拼接为
单张 4x1 堆叠图, 配合 .tex 里 width=0.75\\textwidth 使用。

输出: figures/fig4-3_srcX_displacement.png
"""
from PIL import Image
import os

BASE = os.path.dirname(os.path.abspath(__file__))
INPUTS = [os.path.join(BASE, f'fig4-3_srcX_displacement_{s}.png') for s in 'abcd']
OUT = os.path.join(BASE, 'fig4-3_srcX_displacement.png')

imgs = [Image.open(p).convert('RGB') for p in INPUTS]
W = max(im.width for im in imgs)
# 统一缩放到同宽
scaled = []
for im in imgs:
    if im.width != W:
        new_h = int(im.height * W / im.width)
        im = im.resize((W, new_h), Image.LANCZOS)
    scaled.append(im)
H = sum(im.height for im in scaled)

combined = Image.new('RGB', (W, H), 'white')
y = 0
for im in scaled:
    combined.paste(im, (0, y))
    y += im.height

combined.save(OUT, dpi=(300, 300))
print(f'[OK] saved {OUT}  ({W}x{H})')
