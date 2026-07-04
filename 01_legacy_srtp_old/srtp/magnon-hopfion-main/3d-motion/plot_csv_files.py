import os
import pandas as pd
import matplotlib.pyplot as plt

def calculate_velocity(data):
    """
    计算速度，速度为相邻点位移的差分值。
    假设时间步长为1个单位（即每个序号间隔）。
    """
    velocity = data.diff().fillna(0)  # 使用差分计算速度，并用0填充初始的NaN值
    return velocity

def plot_csv_files_in_folder(folder_path):
    """
    遍历文件夹中的所有CSV文件，为每个文件生成一张包含6个子图的PNG图像。
    子图包括x, y, z的位移和速度随时间的变化。
    """
    csv_files = [file for file in os.listdir(folder_path) if file.endswith('.csv')]

    if not csv_files:
        print("当前文件夹内没有找到CSV文件！")
        return

    for csv_file in csv_files:
        file_path = os.path.join(folder_path, csv_file)

        try:
            # 读取CSV文件，这里假设文件没有标题行
            data = pd.read_csv(file_path, header=None, names=['index', 'x', 'y', 'z', 'extra'])

            if data.shape[1] < 4:
                print(f"文件 {csv_file} 的列数少于4，格式不符合要求，已跳过。")
                continue

            # --- 关键修改：强制将 x, y, z 列转换为数值类型 ---
            # 遍历 'x', 'y', 'z' 列
            for col in ['x', 'y', 'z']:
                # pd.to_numeric 尝试将该列数据转为数字
                # errors='coerce' 会将所有无法转换的值（如文本）设为 NaN (Not a Number)
                data[col] = pd.to_numeric(data[col], errors='coerce')

            # 检查是否有整列都转换失败的情况 (可选但建议)
            if data[['x', 'y', 'z']].isnull().all().any():
                print(f"警告：文件 {csv_file} 中 x, y, z 的某一列或多列完全无法转换为数值，已跳过。")
                continue

            # 用0填充转换过程中产生的 NaN 值，以免影响后续计算
            data[['x', 'y', 'z']] = data[['x', 'y', 'z']].fillna(0)
            # -------------------- 修改结束 --------------------


            fig, axs = plt.subplots(2, 3, figsize=(24, 12))
            fig.suptitle(f'Analysis of postion and velocity - {csv_file}', fontsize=20)

            # 定义坐标轴和颜色
            coords = ['x', 'y', 'z']
            colors = ['blue', 'green', 'red']
            
            # ------------------- 绘制位移图 (第一行) -------------------
            for i, col in enumerate(coords):
                ax = axs[0, i]  # 选择第一行的第 i 个子图
                ax.plot(data['index'], data[col], label=f'{col} postion', marker='o', linestyle='-', color=colors[i])
                ax.set_title(f'position on {col}-axis & time')
                ax.set_xlabel('time (1e10)')
                ax.set_ylabel(f'position on {col} -axis')
                ax.legend()
                ax.grid(True)

            # ------------------- 计算并绘制速度图 (第二行) -------------------
            for i, col in enumerate(coords):
                ax = axs[1, i]  # 选择第二行的第 i 个子图
                velocity = calculate_velocity(data[col])
                ax.plot(data['index'], velocity, label=f'{col} velocity', marker='x', linestyle='--', color=colors[i])
                ax.set_title(f'velocity on {col}-axis & time ')
                ax.set_xlabel('time (1e10)')
                ax.set_ylabel(f'velocity on {col}-axis ')
                ax.legend()
                ax.grid(True)

            plt.tight_layout(rect=[0, 0.03, 1, 0.95])
            
            base_filename = os.path.splitext(csv_file)[0]
            output_filename = f"{base_filename}_analysis.png"
            plt.savefig(output_filename)
            plt.close(fig)

            print(f"文件 {csv_file} 的组合分析图已保存为: {output_filename}")

        except Exception as e:
            # 打印更详细的错误信息，包括文件名
            print(f"处理文件 {csv_file} 时出错: {e}")

if __name__ == "__main__":
    plt.rcParams['font.sans-serif'] = ['SimHei']
    plt.rcParams['axes.unicode_minus'] = False

    current_folder = os.getcwd()
    print(f"开始处理文件夹: {current_folder}")
    plot_csv_files_in_folder(current_folder)
    print("所有CSV文件已处理完成！")