import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks

# --- 用户配置区 ---
# 1. 设置table.txt文件的正确路径
file_path = 'your_script_name.out/table.txt' # !!!请确保这是您的真实路径!!!

# 2. 指定要分析的列名 (最终修正版)
#    根据MuMax3的输出，时间列的真实名称包含'#'和前导空格
#    我们将其原样复制过来，作为要查找的列名
time_col = '# t (s)'

#    数据列的名称也可能包含前导空格，请务必从table.txt文件中核对并复制
#    我们假设它在文件中的名字是 ' mz_avg (A/m)' (注意' '和'(A/m)'之间的空格)
data_col = ' mz_avg (A/m)'

# 3. 设置寻找共振峰的阈值
peak_threshold = 0.001 
# --- 配置区结束 ---

# 下面的代码部分保持不变...

print(f"开始分析文件: {file_path}")
print(f"分析的磁化分量: {data_col}")

# 1. 使用pandas读取数据
try:
    # 脚本现在会寻找正确的列名
    df = pd.read_csv(file_path, sep='\t')
    
    # 提取时间和磁化数据
    t = df[time_col].to_numpy()
    m = df[data_col].to_numpy()
    
except FileNotFoundError:
    print(f"错误: 文件 '{file_path}' 未找到。请检查路径是否正确。")
    exit()
except KeyError as e:
    print(f"错误: 在文件中找不到列 {e}。")
    print("请用文本编辑器打开table.txt文件，检查并确保脚本中的'time_col'和'data_col'与文件第一行中的列名(包括所有空格和特殊字符)完全一致。")
    exit()

# 2. 准备FFT计算
N = len(t)
if N == 0:
    print("错误: 文件中没有数据。")
    exit()
    
dt = np.mean(np.diff(t))

print(f"总数据点: {N}")
print(f"平均时间步长 (dt): {dt:.2e} s")

# 3. 执行FFT
m_fft = np.fft.fft(m)
freq = np.fft.fftfreq(N, dt)

# 4. 处理FFT结果
positive_freq_mask = freq > 0
freqs = freq[positive_freq_mask]
m_fft_magnitude = np.abs(m_fft[positive_freq_mask])

# 5. 自动寻找共振峰
peaks_indices, _ = find_peaks(m_fft_magnitude, height=peak_threshold)
peak_freqs = freqs[peaks_indices]
peak_magnitudes = m_fft_magnitude[peaks_indices]

# 6. 报告结果
print("\n--- 共振峰分析结果 ---")
if len(peak_freqs) > 0:
    for f, mag in zip(peak_freqs, peak_magnitudes):
        print(f"检测到共振峰: {f / 1e9:.4f} GHz (振幅: {mag:.4f})")
else:
    print(f"在阈值 > {peak_threshold} 的条件下未找到显著的共振峰。")
    print("建议：尝试降低 'peak_threshold' 的值，或者检查Sinc脉冲的振幅是否足够大。")
    
# 7. 绘制频谱图
plt.figure(figsize=(12, 6))
plt.plot(freqs / 1e9, m_fft_magnitude, label='FFT Spectrum')
plt.plot(peak_freqs / 1e9, peak_magnitudes, 'x', color='red', markersize=10, label='Detected Peaks')

plt.title('Frequency Spectrum Analysis')
plt.xlabel('Frequency (GHz)')
plt.ylabel('FFT Amplitude (a.u.)')
plt.grid(True, which='both', linestyle='--', linewidth=0.5)
plt.legend()
plt.show()