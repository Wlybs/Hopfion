#!/bin/sh

# 定义数据路径
datapath=3d-motion 

# 定义Python脚本的路径和命令
PYTHON_SCRIPT_PATH="python find_center.py"

# 遍历所有以 .out 结尾的目录
for i in `ls -d $datapath/test*.out`; do

	outputfile=`echo $i | awk '{sub(/^.*\//,""); sub(/\.out/,".csv"); printf $0}'`
	outputpath="$datapath/$outputfile"

	echo "Processing folder "$i" -> $outputpath"

    # 删除旧的CSV文件，确保重新开始
    if [ -f "$outputpath" ]; then
        rm "$outputpath"
    fi

	# --- 修改部分：为每个目录初始化一个变量来存储初始位置 ---
	initial_pos=""
	
	nr=0
	# 按版本号顺序遍历ovf文件
	for j in `ls -v $i/m*.ovf`; do
		echo "  Processing file "$j"..."

		# --- 修改部分：根据 initial_pos 是否已设置来决定如何调用Python ---
		if [ -z "$initial_pos" ]; then
			# 如果 initial_pos 为空（这是第一个或之前的都失败了）
			# 正常调用Python脚本获取绝对坐标
			line=$($PYTHON_SCRIPT_PATH $j | awk '{gsub(/[\(\)\[\]]/,""); sub(/^ +/, ""); sub(/ +$/, ""); print $0}')
			
			if [ -n "$line" ] && [ "$line" != "NaN NaN NaN" ]; then
				# 第一次成功找到中心，将其存为初始位置
				initial_pos=$line
				# 对于初始位置，其位移为0
				echo "$nr,0.000000000e+00,0.000000000e+00,0.000000000e+00" >> $outputpath
			else
				# 如果第一个就失败了，则输出NaN
				echo "$nr,NaN,NaN,NaN" >> $outputpath
			fi
		else
			# 如果 initial_pos 已被设置，将其作为参数传给Python脚本以计算位移
			line=$($PYTHON_SCRIPT_PATH $j $initial_pos | awk '{gsub(/[\(\)\[\]]/,""); sub(/^ +/, ""); sub(/ +$/, ""); print $0}')
			
			if [ -n "$line" ] && [ "$line" != "NaN NaN NaN" ]; then
				# 将序号和计算出的位移写入文件
				echo "$nr,$line" | awk '{gsub(/ +/, ","); print $0}' >> $outputpath
			else
				# 如果后续文件计算失败，输出NaN
				echo "$nr,NaN,NaN,NaN" >> $outputpath
			fi
		fi
		
		nr=`expr $nr + 1`
	done
done

echo "All folders processed."