# check_mag2exp.py
import sys
import mag2exp

print("--- mag2exp 模块结构诊断 ---")
try:
    print(f"Python 解释器路径: {sys.executable}")
    print(f"mag2exp 库版本: {mag2exp.__version__}")
    print("\n在 mag2exp 模块中可用的属性和子模块:")
    # 打印出 mag2exp 库的所有顶级内容
    print(dir(mag2exp))
except Exception as e:
    print(f"执行诊断时发生错误: {e}")