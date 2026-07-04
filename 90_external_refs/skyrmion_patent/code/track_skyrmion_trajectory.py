import matplotlib.pyplot as plt
import numpy as np
import os

def process_file(file_path):
    # 打开文件并读取内容
    with open(file_path, "r") as file:
        content = file.read()

    # 提取 # Begin: Data Text 和 # End: Data Text 之间的数据
    start_marker = "# Begin: Data Text"
    end_marker = "# End: Data Text"

    start_index = content.find(start_marker)
    end_index = content.find(end_marker, start_index)

    if start_index != -1 and end_index != -1:
        data_text = content[start_index + len(start_marker):end_index].strip()

        # 将数据文本分割为行
        lines = data_text.split("\n")

        # 创建一个空列表来存储每一行的数据
        rows = 75
        cols = 250
        one_dimensional_list = []
        zComponent = [[None] * (cols - 1) for _ in range(rows - 1)]

        # 处理每一行数据
        for line in lines:
            # 在这里你可以进一步处理每一行的数据
            one_dimensional_list.append([i for i in line.split()])

        two_dimensional_list = [one_dimensional_list[i:i + cols] for i in range(0, len(one_dimensional_list), cols)]
        for i in range(rows - 1):
            for j in range(cols - 1):
                zComponent[i][j] = float((two_dimensional_list[i][j][2]))

        data = np.array(zComponent)

        # 绘制热度图
        plt.imshow(data, cmap='viridis', interpolation='nearest')

        # 添加颜色条
        plt.colorbar()

        # 显示图形
        plt.show()
        ysum = 0.0
        ymax = -300000000
        ypos = 0
        for i in range(5, rows - 1 -5):
            ysum = 0.0
            for j in range(5, cols - 1 - 5):
                ysum += zComponent[i][j]
            if ysum > ymax and i != 0 and i != 24:
                ymax = ysum
                ypos = i

        xsum = 0.0
        xmax = -300000000
        xpos = 0
        for j in range(5, cols - 1 - 5):
            xsum = 0.0
            for i in range(5, rows - 1 -5):
                xsum += zComponent[i][j]
            if xsum > xmax and j != 0 and j != 249:
                xmax = xsum
                xpos = j
        print([xpos, ypos])
        return([xpos, ypos])

    else:
        print("Markers not found.")



# 文件夹路径
folder_path = "D:\\HuaweiMoveData\\Users\\27189\\Desktop\\oommf\\app\\oxs\\examples\\skym\\source"

# 获取文件夹下的所有文件
file_names = os.listdir(folder_path)

# 过滤出文件，排除文件夹
file_paths = [os.path.join(folder_path, file_name) for file_name in file_names if
              os.path.isfile(os.path.join(folder_path, file_name))]

# 输出文件列表
print("Files in the folder:")
print(file_names)

posList=[]
# 遍历每个文件
for file_path in file_paths:
    # print(f"Processing file: {file_path}")
    posList.append(process_file(file_path))
print(posList)
