import os
import subprocess

# 指定目标目录
target_dir = os.getcwd()

# 遍历目标目录下的所有文件夹
for folder in os.listdir(target_dir):
    folder_path = os.path.join(target_dir, folder)

    # 检查是否为文件夹
    if os.path.isdir(folder_path):
        # 查找文件夹中是否有 .out 文件
        has_out_file = 1  #any(filename.endswith('.out') for filename in os.listdir(folder_path))
        #这上面一句代码后面的我注释掉了，改成下面代码直接执行。

        # 如果包含 .out 文件，执行命令
        if has_out_file:
            print(f"Processing folder: {folder_path}")
            
            # 构建要执行的命令
            commands = [
                "mumax3-convert -omf text *.ovf",
                "ls | grep ovf | xargs rm -rf",
                "mumax3-convert -ovf text *.omf",
                "ls | grep omf | xargs rm -rf"
            ]
            
            for command in commands:
                print(f"Executing: {command} in {folder_path}")
                subprocess.run(command, cwd=folder_path, shell=True)

# 提示用户所有命令已执行
print("All commands executed in applicable folders.")