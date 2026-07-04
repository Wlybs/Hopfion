import numpy as np
import os
import re
import discretisedfield as df

# 我们直接从您的 draw.py 和 generate_hopfion.py 文件中导入需要的函数
# 确保这三个脚本在同一个文件夹下
from draw import calculate_hopfion_radii_topological
from generate_hopfion import generate_hopfion_ovf


def parse_ovf_manually(filename):
    """
    一个强大的手动OVF解析器，可以兼容不同版本的OVF文件格式。
    它会直接读取文件内容，提取所需信息，并手动构建一个 discretisedfield.Field 对象。
    """
    print(f"检测到可能不兼容的OVF格式，正在启动手动解析模式...")
    header = {}
    data_lines = []
    
    with open(filename, 'r', errors='ignore') as f:
        in_header = False
        in_data = False
        for line in f:
            if line.startswith("# Begin: Header"):
                in_header = True
                continue
            if line.startswith("# End: Header"):
                in_header = False
                continue
            if line.startswith("# Begin: Data Text"):
                in_data = True
                continue
            if line.startswith("# End: Data Text"):
                in_data = False
                continue

            if in_header:
                parts = line.strip('# ').strip().split(':', 1)
                if len(parts) == 2:
                    header[parts[0].strip().lower()] = parts[1].strip()
            
            if in_data:
                # 忽略数据段中的注释行
                if not line.strip().startswith('#'):
                    data_lines.append(line)

    # 从header中提取必要的元数据
    try:
        xnodes = int(header['xnodes'])
        ynodes = int(header['ynodes'])
        znodes = int(header['znodes'])
        xstepsize = float(header['xstepsize'])
        ystepsize = float(header['ystepsize'])
        zstepsize = float(header['zstepsize'])
        meshunit = header.get('meshunit', 'm')
    except KeyError as e:
        raise RuntimeError(f"手动解析失败：OVF文件头部缺少关键信息 {e}")

    # 处理单位
    if meshunit == 'nm':
        xstepsize *= 1e-9
        ystepsize *= 1e-9
        zstepsize *= 1e-9

    # 定义网格区域
    # OVF文件可能只定义了xmin/max，或者只定义了nodes/stepsize。我们需要兼容。
    xmin = float(header.get('xmin', 0))
    ymin = float(header.get('ymin', 0))
    zmin = float(header.get('zmin', 0))
    
    # 如果没有xmax，则根据节点和步长计算
    xmax = float(header.get('xmax', xmin + xnodes * xstepsize))
    ymax = float(header.get('ymax', ymin + ynodes * ystepsize))
    zmax = float(header.get('zmax', zmin + znodes * zstepsize))
    
    p1 = (xmin, ymin, zmin)
    p2 = (xmax, ymax, zmax)
    cell = (xstepsize, ystepsize, zstepsize)

    # 解析磁矩数据
    data = np.loadtxt(data_lines)
    # OVF数据通常是(x, y, z)顺序扫描，我们需要将其重塑为(x, y, z, 3)的网格
    value = data.reshape(znodes, ynodes, xnodes, 3)
    value = np.transpose(value, (2, 1, 0, 3))

    # 手动创建 discretisedfield.Field 对象
    mesh = df.Mesh(p1=p1, p2=p2, cell=cell)
    field = df.Field(mesh, dim=3, value=value)
    
    print("手动解析并成功构建Field对象！")
    return field


def create_Qh1_analog(reference_ovf_file):
    """
    分析一个参考的Hopfion OVF文件，然后生成一个具有相同几何尺寸
    但拓扑荷为 Qh=1 的新Hopfion。
    """
    print(f"--- 步骤 1: 分析参考文件 '{reference_ovf_file}' 的几何尺寸 ---")
    
    if not os.path.exists(reference_ovf_file):
        print(f"错误：找不到参考文件 '{reference_ovf_file}'。")
        return

    try:
        # 优先尝试标准方法加载
        ref_field = df.Field.from_file(reference_ovf_file)
    except Exception as e:
        print(f"标准方法加载失败 (错误: {e})。")
        # 如果标准方法失败，则启动我们的手动解析器
        try:
            ref_field = parse_ovf_manually(reference_ovf_file)
        except Exception as manual_e:
            print(f"手动解析也失败了: {manual_e}")
            return

    # 使用您 draw.py 中的函数来精确计算 R 和 r
    try:
        R_measured, r_measured = calculate_hopfion_radii_topological(ref_field)
        if R_measured is None or r_measured is None:
            print("无法从参考文件中精确计算出 R 和 r，操作已中止。")
            return
    except Exception as e:
        print(f"计算半径时出错: {e}")
        return

    print(f"\n--- 步骤 2: 生成新的 Qh=1 Hopfion ---")
    print(f"将使用测量出的尺寸: R={R_measured*1e9:.2f} nm, r={r_measured*1e9:.2f} nm")

    output_filename = f"hopfion_Qh=1_analog_R{R_measured*1e9:.1f}_r{r_measured*1e9:.1f}.ovf"

    # 使用测量出的 R, r 和 Qh=1, p=1, q=1 来调用生成函数
    generate_hopfion_ovf(
        Qh=1, p=1, q=1,
        R=R_measured,
        r=r_measured,
        xnodes=100,
        ynodes=100,
        znodes=100,
        xstepsize=(R_measured + r_measured)*2 / 100, # 动态调整步长以适应尺寸
        ystepsize=(R_measured + r_measured)*2 / 100,
        zstepsize=(R_measured + r_measured)*2 / 100,
        output_filename=output_filename
    )

if __name__ == "__main__":
    reference_file = "stable-state-h+1+2_trans_q=2.ovf"
    create_Qh1_analog(reference_file)