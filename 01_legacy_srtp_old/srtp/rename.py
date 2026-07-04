import os

def rename_files_in_directory():
    """
    重命名当前目录下的文件，将文件名中的 'areaz_z' 替换为 'areaz_x'。
    """
    # 获取当前目录下的所有文件列表
    file_list = os.listdir('.')
    
    # 遍历文件列表
    for filename in file_list:
        # 检查文件是否以 .out 结尾并且文件名中包含 'areaz_z'
        if 'areaz_z' in filename:
            # 创建新的文件名，将 'areaz_z' 替换为 'areaz_x'
            new_filename = filename.replace('areaz_z', 'areaz_x')
            
            # 检查新文件名是否已存在，以防止覆盖
            if not os.path.exists(new_filename):
                # 重命名文件
                os.rename(filename, new_filename)
                print(f"已重命名: {filename} -> {new_filename}")
            else:
                print(f"已跳过: {filename}。新文件名 '{new_filename}' 已存在。")

# 运行重命名函数
if __name__ == "__main__":
    rename_files_in_directory()