"""
自动拆分 matplotlib 多面板拼图为独立子图。
用法: python3 split_panels.py <input.png> <rows> <cols> [--output-dir DIR]

例如: python3 split_panels.py figures/fig4-4.png 1 4
      → 生成 figures/fig4-4_a.png, _b.png, _c.png, _d.png
"""

import argparse
import numpy as np
from PIL import Image
from pathlib import Path


def find_split_positions(img_array, axis, n_splits):
    """沿指定轴找到 n_splits-1 个分割位置（面板间白色间隙的中心）。"""
    gray = np.mean(img_array[:, :, :3], axis=2)

    if axis == 1:  # 水平分割（找垂直分割线）
        profile = np.mean(gray, axis=0)  # 每列的平均亮度
    else:  # 垂直分割（找水平分割线）
        profile = np.mean(gray, axis=1)  # 每行的平均亮度

    length = len(profile)
    panel_width = length / n_splits

    positions = []
    for i in range(1, n_splits):
        # 在预期分割点附近搜索最亮（最白）的位置
        center = int(i * panel_width)
        search_range = int(panel_width * 0.15)
        start = max(0, center - search_range)
        end = min(length, center + search_range)

        local_profile = profile[start:end]
        best_local = np.argmax(local_profile)
        positions.append(start + best_local)

    return positions


def split_image(input_path, rows, cols, output_dir=None):
    """将多面板图拆分为独立子图。"""
    img = Image.open(input_path)
    arr = np.array(img)
    h, w = arr.shape[:2]

    stem = Path(input_path).stem
    suffix = Path(input_path).suffix
    out_dir = Path(output_dir) if output_dir else Path(input_path).parent

    # 找分割位置
    if cols > 1:
        x_splits = find_split_positions(arr, axis=1, n_splits=cols)
    else:
        x_splits = []

    if rows > 1:
        y_splits = find_split_positions(arr, axis=0, n_splits=rows)
    else:
        y_splits = []

    # 生成边界
    x_bounds = [0] + x_splits + [w]
    y_bounds = [0] + y_splits + [h]

    labels = 'abcdefghijklmnopqrstuvwxyz'
    idx = 0
    results = []

    for r in range(rows):
        for c in range(cols):
            y1, y2 = y_bounds[r], y_bounds[r + 1]
            x1, x2 = x_bounds[c], x_bounds[c + 1]

            panel = img.crop((x1, y1, x2, y2))
            out_name = f"{stem}_{labels[idx]}{suffix}"
            out_path = out_dir / out_name
            panel.save(out_path, dpi=(300, 300))
            results.append((out_name, panel.size))
            idx += 1

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Split multi-panel figure")
    parser.add_argument("input", help="Input image path")
    parser.add_argument("rows", type=int, help="Number of rows")
    parser.add_argument("cols", type=int, help="Number of columns")
    parser.add_argument("--output-dir", "-o", help="Output directory")
    args = parser.parse_args()

    results = split_image(args.input, args.rows, args.cols, args.output_dir)
    for name, size in results:
        print(f"  {name}: {size[0]}x{size[1]}")
