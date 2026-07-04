#!/bin/sh

datapath=test2_size

# 只处理以 PBC_areax_z_f_sw_ 开头且 .out 结尾的文件夹
for i in $datapath/*.out; do
    # 确保是目录
    if [ ! -d "$i" ]; then
        continue
    fi
    
    expectation=0.0
    outputfile=`echo $i | awk '{sub(/^.*\//,""); sub(/\.out/,".csv"); printf $0}'`
    echo "Processing "$i"..."
    nr=0
    for j in `ls $i/m*.ovf`; do
        echo $expectation" expected."
        file1=$i/m000000.ovf
        file2=$j
        line=`/d/Python/Python310/python.exe track.py $file1 $file2 $expectation | awk '{gsub(/[\(\)\[\]]/,""); sub(/^ +/, ""); sub(/ +$/, ""); print $0}'`
        echo $line | awk '{gsub(/ +/, ", "); print "'$nr', "$0}' >> $datapath/$outputfile
        expectation=`echo $line | awk '{print $4}'`
        nr=`expr $nr + 1`
    done
done