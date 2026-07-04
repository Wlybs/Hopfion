% =========================================================================
% 主脚本：绘制三维Hopfion (兼容 R2014a)
% 请运行此文件
% =========================================================================

clear; clc; close all;

%% 1. 参数设置
ovf_filename = 'stable-state-h+1+2_trans_q=2.ovf';
save_path = 'hopfion_3d_matlab_R2014a.png';
size_est_threshold = 0.1; 

%% 2. 执行主流程
% 调用独立的函数文件
[m, cellsize, nodes] = load_ovf_ascii(ovf_filename);
[radius, height, ~] = estimate_hopfion_size(m, cellsize, nodes, size_est_threshold);
plot_3d_hopfion_isosurface(m, cellsize, nodes, radius, height, save_path);