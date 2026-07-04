#!/bin/sh

datapath=3d-motion

# 遍历所有 .out 文件
for i in $datapath/*.out; do
    expectation=0.0
    outputfile=$(basename "$i" .out).csv
    echo "Processing $i..."

    nr=0

    # 遍历 .out 文件夹中的所有 m*.ovf 文件
    for j in $i/m*.ovf; do
        echo "$expectation expected."

        file1="$i/m000000.ovf"
        file2="$j"

        # 调用 track.py 并格式化输出
        line=$(python track.py "$file1" "$file2" "$expectation" | awk '{gsub(/[\(\)\[\]]/,""); sub(/^ +/, ""); sub(/ +$/, ""); print $0}')

        # 将结果写入 CSV 文件
        echo "$line" | awk -v nr="$nr" '{gsub(/ +/, ", "); print nr", "$0}' >> "$datapath/$outputfile"

        # 更新 expectation 和 nr
        expectation=$(echo "$line" | awk '{print $4}')
        nr=$((nr + 1))
    done
done
