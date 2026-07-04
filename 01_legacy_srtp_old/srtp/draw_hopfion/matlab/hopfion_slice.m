% =========================================================================
% 最终版主脚本 (兼容 R2014a) - 使用SURF渲染
% =========================================================================
clear; clc; close all;

%% 1. 参数设置
ovf_filename = 'stable-state-h+1+2_trans_q=2.ovf';
save_path = 'hopfion_slices_SURF_final.png';
size_est_threshold = 0.1; 

% --- 通过调节这两个值来控制圆环的样式 ---
ring_inner_threshold = 0.3; % 内圈阈值，调高可使中心空洞变大
ring_outer_threshold = 0.98;% 外圈阈值，调低可使圆环变细

%% 2. 执行主流程
[m, cellsize, nodes] = load_ovf_ascii(ovf_filename);
[radius, height, bounds] = estimate_hopfion_size(m, cellsize, nodes, size_est_threshold);
plot_ring_slices(m, cellsize, nodes, bounds, radius, height, ...
                  ring_inner_threshold, ring_outer_threshold, save_path);