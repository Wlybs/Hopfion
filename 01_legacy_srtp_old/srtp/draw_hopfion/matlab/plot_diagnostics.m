function plot_diagnostics(m, cellsize, nodes, bounds, save_path)
    if isempty(fieldnames(bounds))
        return;
    end
    
    fprintf('正在生成诊断图像...\n');
    
    % 准备数据
    mx = m(:,:,:,1);
    my = m(:,:,:,2);
    mz = m(:,:,:,3);
    
    % 中心切片索引
    xc_index = round((bounds.xmin + bounds.xmax) / 2);
    zc_index = round((bounds.zmin + bounds.zmax) / 2);

    % 提取XOY切片
    mx_xoy = squeeze(mx(zc_index,:,:));
    my_xoy = squeeze(my(zc_index,:,:));
    mz_xoy = squeeze(mz(zc_index,:,:));

    % 提取YOZ切片
    mx_yoz = squeeze(mx(:,:,xc_index));
    my_yoz = squeeze(my(:,:,xc_index));
    mz_yoz = squeeze(mz(:,:,xc_index));
    
    % 创建 2x3 的子图窗口
    figure('Position', [50, 50, 1200, 600], 'Color', 'white');
    
    x_axis = (1:nodes.x) * cellsize.dx * 1e9;
    y_axis = (1:nodes.y) * cellsize.dy * 1e9;
    z_axis = (1:nodes.z) * cellsize.dz * 1e9;

    % --- 第一行: XOY 平面 ---
    subplot(2, 3, 1);
    imagesc(x_axis, y_axis, mx_xoy'); set(gca, 'YDir', 'normal'); axis equal tight;
    title(sprintf('mx on XOY plane (z=%.1fnm)', zc_index*cellsize.dz*1e9)); colorbar; xlabel('x (nm)'); ylabel('y (nm)');

    subplot(2, 3, 2);
    imagesc(x_axis, y_axis, my_xoy'); set(gca, 'YDir', 'normal'); axis equal tight;
    title('my on XOY plane'); colorbar; xlabel('x (nm)');

    subplot(2, 3, 3);
    imagesc(x_axis, y_axis, mz_xoy'); set(gca, 'YDir', 'normal'); axis equal tight;
    title('mz on XOY plane'); colorbar; xlabel('x (nm)');

    % --- 第二行: YOZ 平面 ---
    subplot(2, 3, 4);
    imagesc(y_axis, z_axis, mx_yoz); set(gca, 'YDir', 'normal'); axis equal tight;
    title(sprintf('mx on YOZ plane (x=%.1fnm)', xc_index*cellsize.dx*1e9)); colorbar; xlabel('y (nm)'); ylabel('z (nm)');

    subplot(2, 3, 5);
    imagesc(y_axis, z_axis, my_yoz); set(gca, 'YDir', 'normal'); axis equal tight;
    title('my on YOZ plane'); colorbar; xlabel('y (nm)');

    subplot(2, 3, 6);
    imagesc(y_axis, z_axis, mz_yoz); set(gca, 'YDir', 'normal'); axis equal tight;
    title('mz on YOZ plane'); colorbar; xlabel('y (nm)');
    
    colormap(jet); % 使用统一的色谱
    
    % 保存
    print(gcf, save_path, '-dpng', '-r200');
    fprintf('诊断图像已保存为 %s\n', save_path);
end