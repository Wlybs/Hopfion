% =========================================================================
% 诊断脚本主程序
% =========================================================================

clear; clc; close all;

%% 1. 参数设置
ovf_filename = 'stable-state-h+1+2_trans_q=2.ovf';
save_path = 'hopfion_diagnostics.png';
size_est_threshold = 0.1; 

%% 2. 执行流程
[m, cellsize, nodes] = load_ovf_ascii(ovf_filename);
[~, ~, bounds] = estimate_hopfion_size(m, cellsize, nodes, size_est_threshold);

% 调用诊断绘图函数
plot_diagnostics(m, cellsize, nodes, bounds, save_path);