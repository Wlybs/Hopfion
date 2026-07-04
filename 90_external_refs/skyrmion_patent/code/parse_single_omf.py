import matplotlib.pyplot as plt
import numpy as np
# 文件路径
file_path = "D:\\HuaweiMoveData\\Users\\27189\\Desktop\\oommf\\app\\oxs\\examples\\skym\\state1.omf"
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
    one_dimensional_list = []

    # 处理每一行数据
    for line in lines:
        # 在这里你可以进一步处理每一行的数据
        one_dimensional_list.append([i for i in line.split()])

    # # 将列表转换为字符串，并去掉单引号
    # data_string = repr(data_list).replace("'", "")

    # 打印结果
    # print(len(data_list))
    rows = 250
    cols = 25
    two_dimensional_list = [one_dimensional_list[i:i + cols] for i in range(0, len(one_dimensional_list), cols)]
    print(two_dimensional_list[0][0][0])
    # posxSumMin=0
    # posx=0
    # for i in range(lyMax-1):
    #     posxSum = 0
    #     for j in range(lxMax-1):
    #         posxSum=posxSum+float((data_list)[i*250+j][2])
    #         if abs(posxSum) > posxSumMin:
    #             posxSumMax=posxSum
    #             posx=i
    # print(posx)
else:
    print("Markers not found.")
