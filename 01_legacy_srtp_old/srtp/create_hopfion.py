import numpy as np

# --- 用户配置区 (请确保与您的Mumax3脚本一致) ---
sizeX, sizeY, sizeZ = 75e-9, 75e-9, 375e-9
gridX, gridY, gridZ = 64, 64, 256
output_filename = "hopfion_initial.ovf"
m_vorticity, n_vorticity, p_polarity, a_radius = 1, 1, 1, 20e-9
# --- 配置区结束 ---

def write_ovf_definitive(filename, m_field):
    """
    一个专门的函数，通过二进制写入来精确控制每一个字节，
    确保生成与您成功案例完全兼容的OVF 1.0文本文件。
    """
    nx, ny, nz, _ = m_field.shape
    cellX, cellY, cellZ = sizeX / nx, sizeY / ny, sizeZ / nz
    
    # 使用二进制写入模式 'wb'
    with open(filename, 'wb') as f:
        # 定义Windows换行符
        win_newline = b'\r\n'
        
        # --- 写入与您成功加载文件完全兼容的OVF 1.0文件头 ---
        f.write(b"# OOMMF: rectangular mesh v1.0" + win_newline)
        f.write(b"# Segment count: 1" + win_newline)
        f.write(b"# Begin: Segment" + win_newline)
        f.write(b"# Begin: Header" + win_newline)
        f.write(f"# Title: {filename}".encode('utf-8') + win_newline)
        f.write(b"# meshtype: rectangular" + win_newline)
        f.write(b"# meshunit: m" + win_newline)
        f.write(f"# xbase: {cellX/2}".encode('utf-8') + win_newline)
        f.write(f"# ybase: {cellY/2}".encode('utf-8') + win_newline)
        f.write(f"# zbase: {cellZ/2}".encode('utf-8') + win_newline)
        f.write(f"# xstepsize: {cellX}".encode('utf-8') + win_newline)
        f.write(f"# ystepsize: {cellY}".encode('utf-8') + win_newline)
        f.write(f"# zstepsize: {cellZ}".encode('utf-8') + win_newline)
        f.write(f"# xnodes: {nx}".encode('utf-8') + win_newline)
        f.write(f"# ynodes: {ny}".encode('utf-8') + win_newline)
        f.write(f"# znodes: {nz}".encode('utf-8') + win_newline)
        f.write(b"# valueunit: 1" + win_newline)
        f.write(b"# valuemultiplier: 1" + win_newline) # 修正为整数1
        f.write(b"# ValueRangeMinMag: 1" + win_newline) # 修正为整数1
        f.write(b"# ValueRangeMaxMag: 1" + win_newline) # 修正为整数1
        f.write(b"# End: Header" + win_newline)
        f.write(b"# Begin: Data Text" + win_newline)
        
        # --- 写数据 ---
        for k in range(nz):
            for j in range(ny):
                for i in range(nx):
                    mx, my, mz = m_field[i, j, k]
                    line = f" {mx: .10e} {my: .10e} {mz: .10e}"
                    f.write(line.encode('utf-8') + win_newline)
        
        f.write(b"# End: Data Text" + win_newline)
        f.write(b"# End: Segment" + win_newline)
    print(f"成功生成最终兼容格式的Hopfion初始态文件: {filename}")

# ... (脚本的其余计算部分保持不变) ...
x_coords = np.linspace(0, sizeX, gridX, endpoint=False) + (sizeX / gridX / 2)
y_coords = np.linspace(0, sizeY, gridY, endpoint=False) + (sizeY / gridY / 2)
z_coords = np.linspace(0, sizeZ, gridZ, endpoint=False) + (sizeZ / gridZ / 2)
m_field = np.zeros((gridX, gridY, gridZ, 3))

for i, x in enumerate(x_coords):
    for j, y in enumerate(y_coords):
        for k, z in enumerate(z_coords):
            xc, yc, zc = x - sizeX/2, y - sizeY/2, z - sizeZ/2
            rho, phi = np.sqrt(xc**2 + yc**2), np.arctan2(yc, xc)
            r_sq = rho**2 + zc**2
            eta_arg = (2 * a_radius * rho) / (r_sq + a_radius**2)
            if eta_arg >= 1.0: eta_arg = 0.999999999
            eta = np.arctanh(eta_arg)
            beta = np.arctan2(2 * a_radius * zc, r_sq - a_radius**2)
            cosh_eta_2m = np.cosh(eta)**(2 * m_vorticity)
            tanh_eta_2n = np.tanh(eta)**(2 * n_vorticity)
            cos2zeta = p_polarity * (1 - cosh_eta_2m * tanh_eta_2n) / (1 + cosh_eta_2m * tanh_eta_2n)
            zeta = 0.5 * np.arccos(cos2zeta)
            Theta, Phi = 2 * zeta, n_vorticity * phi + m_vorticity * beta
            mx, my, mz = np.sin(Theta) * np.cos(Phi), np.sin(Theta) * np.sin(Phi), np.cos(Theta)
            m_field[i, j, k] = [mx, my, mz]

write_ovf_definitive(output_filename, m_field)