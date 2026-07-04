function plot_final_slices(m, cellsize, nodes, bounds, radius, height, inner_thresh, outer_thresh, save_path)
    if isempty(fieldnames(bounds))
        return;
    end
    fprintf('正在生成最终平滑渲染图像...\n');
    
    mx = m(:,:,:,1); my = m(:,:,:,2);
    xc_index = round((bounds.xmin + bounds.xmax) / 2);
    zc_index = round((bounds.zmin + bounds.zmax) / 2);

    in_plane_magnitude = sqrt(mx.^2 + my.^2);
    mask = (in_plane_magnitude > inner_thresh) & (in_plane_magnitude < outer_thresh);

    angle_xoy = atan2(squeeze(my(zc_index,:,:)), squeeze(mx(zc_index,:,:)));
    mask_xoy_slice = squeeze(mask(zc_index,:,:));
    
    angle_yoz = atan2(squeeze(my(:,:,xc_index)), squeeze(mx(:,:,xc_index)));
    mask_yoz_slice = squeeze(mask(:,:,xc_index));
    
    figure('Position', [100, 100, 1000, 420], 'Color', 'white');
    
    % --- 绘制XOY平面图 ---
    h_ax1 = subplot(1, 2, 1);
    x_axis = (1:nodes.x) * cellsize.dx * 1e9;
    y_axis = (1:nodes.y) * cellsize.dy * 1e9;
    [X, Y] = meshgrid(x_axis, y_axis);
    
    h1 = surf(X, Y, zeros(size(angle_xoy')), angle_xoy');
    
    shading interp;
    % =====================================================================
    % --- 核心修正 1：将逻辑类型的mask转换为数值类型 ---
    set(h1, 'AlphaData', double(mask_xoy_slice'));
    % =====================================================================
    set(h1, 'FaceAlpha', 'interp');
    
    view(2);
    axis equal; axis tight; box on;
    title(sprintf('XY-Plane Angle at z = %.1f nm', zc_index * cellsize.dz * 1e9));
    xlabel('x (nm)'); ylabel('y (nm)');
    text(x_axis(1)*1.5, y_axis(1)*1.5, sprintf('Radius ≈ %.2f nm', radius), ...
        'BackgroundColor', 'w', 'EdgeColor', 'k', 'FontSize', 10);
    
    % --- 绘制YOZ平面图 ---
    h_ax2 = subplot(1, 2, 2);
    y_axis_2 = (1:nodes.y) * cellsize.dy * 1e9;
    z_axis = (1:nodes.z) * cellsize.dz * 1e9;
    [Y2, Z2] = meshgrid(y_axis_2, z_axis);
    
    h2 = surf(Y2, Z2, zeros(size(angle_yoz')), angle_yoz');
    
    shading interp;
    % =====================================================================
    % --- 核心修正 2：将逻辑类型的mask转换为数值类型 ---
    set(h2, 'AlphaData', double(mask_yoz_slice'));
    % =====================================================================
    set(h2, 'FaceAlpha', 'interp');
    
    view(2);
    axis equal; axis tight; box on;
    title(sprintf('XY-Plane Angle at x = %.1f nm', xc_index * cellsize.dx * 1e9));
    xlabel('y (nm)'); ylabel('z (nm)');
    text(y_axis_2(1)*1.5, z_axis(1)*1.5, sprintf('Height ≈ %.2f nm', height), ...
        'BackgroundColor', 'w', 'EdgeColor', 'k', 'FontSize', 10);

    % --- 设置共享颜色映射和颜色条 ---
    colormap(hsv);
    set(h_ax1, 'CLim', [-pi, pi]);
    set(h_ax2, 'CLim', [-pi, pi]);
    colorbar;
    
    print(gcf, save_path, '-dpng', '-r600');
    fprintf('最终版平滑二维切片图像已保存为 %s\n', save_path);
end