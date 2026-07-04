import os
import glob
import subprocess
import sys

# --- 在这里配置你的路径 ---

# 1. 指定要使用的绘图脚本的完整路径
# 这是你之前确认的，使用“拓扑原像法”的那个版本
PLOT_SCRIPT_PATH = r"C:\Users\22445\Desktop\srtp\draw_hopfion\AFM\draw_afm_new.py"

# 2. Python解释器的路径 (如果 'python' 已经在系统环境变量中，保持默认即可)
PYTHON_EXEC = "python"

# --- 脚本主逻辑 ---

def find_latest_ovf(directory):
    """在一个文件夹中找到序号最大的 .ovf 文件"""
    ovf_files = glob.glob(os.path.join(directory, '*.ovf'))
    if not ovf_files:
        return None
    
    # 默认的字符串排序对于 "m000000.ovf", "m000001.ovf" ... 是有效的
    ovf_files.sort()
    return ovf_files[-1]

def run_plotting_for_directory(out_dir):
    """处理单个 .out 文件夹"""
    print(f"\n--- 正在处理文件夹: {out_dir} ---")

    # 步骤 1: 找到最新的 .ovf 文件
    latest_ovf = find_latest_ovf(out_dir)
    
    if latest_ovf is None:
        print(f"  [警告] 在 {out_dir} 中没有找到任何 .ovf 文件，已跳过。")
        return

    print(f"  找到最新的文件: {os.path.basename(latest_ovf)}")

    # 步骤 2: 构建并执行绘图命令
    # 注意：这里我们假设 AFM\draw_afm_new.py 脚本可以自动处理AFM解调
    # 如果需要为它传递特定参数，可以在 command 列表中添加
    command = [
        PYTHON_EXEC,
        PLOT_SCRIPT_PATH,
        latest_ovf
    ]
    
    print(f"  执行命令: {' '.join(command)}")
    
    try:
        # 使用 subprocess.run 来执行命令并等待其完成
        # capture_output=True 会捕获标准输出和错误
        # text=True 会将输出解码为文本
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False, # 设置为False，这样即使脚本返回非零退出码也不会抛出异常
            encoding='utf-8' # 明确指定编码
        )
        
        # 打印绘图脚本的输出，方便调试
        if result.stdout:
            print("  [绘图脚本输出]:")
            print(result.stdout)
        if result.stderr:
            print("  [绘图脚本错误输出]:")
            print(result.stderr)
            
        if result.returncode == 0:
            print(f"  [成功] 已为 {os.path.basename(latest_ovf)} 生成图像。")
        else:
            print(f"  [错误] 绘图脚本在处理 {os.path.basename(latest_ovf)} 时返回了错误码 {result.returncode}。")

    except FileNotFoundError:
        print(f"  *** 严重错误: 找不到 '{PYTHON_EXEC}' 或 '{PLOT_SCRIPT_PATH}'。请检查路径配置。")
    except Exception as e:
        print(f"  *** 严重错误: 执行绘图命令时发生未知异常: {e}")


def main():
    """主函数，查找所有 .out 文件夹并处理它们"""
    print("=======================================================")
    print("=== 批量绘图脚本: 自动处理所有 .out 文件夹中的最新OVF ===")
    print("=======================================================")
    
    # 检查绘图脚本是否存在
    if not os.path.exists(PLOT_SCRIPT_PATH):
        print(f"*** 错误: 找不到指定的绘图脚本: {PLOT_SCRIPT_PATH}")
        print("*** 请在脚本顶部更新 PLOT_SCRIPT_PATH 变量。")
        sys.exit(1)

    # 在当前目录下查找所有 .out 文件夹
    out_directories = glob.glob('*.out')
    
    if not out_directories:
        print("在当前目录下没有找到任何 .out 文件夹。")
        print("请确保你是在 parameter_sweep.py 所在的目录运行此脚本。")
        return
        
    print(f"找到了 {len(out_directories)} 个 .out 文件夹，即将开始处理...")
    
    for out_dir in sorted(out_directories):
        run_plotting_for_directory(out_dir)
        
    print("\n=======================================================")
    print("=== 所有文件夹处理完毕。 ===")
    print("=======================================================")


if __name__ == "__main__":
    main()
