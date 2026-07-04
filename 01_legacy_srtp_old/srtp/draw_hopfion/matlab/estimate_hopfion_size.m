function [radius, height, bounds] = estimate_hopfion_size(m, cellsize, ~, threshold) % nodes 参数在此函数中未被使用
    mz = m(:,:,:,3);
    mask = abs(mz) < threshold;
    
    % R2014a 兼容性修改：使用 any(mask(:)) 替代 any(mask, 'all')
    if ~any(mask(:))
        warning('未检测到Hopfion核心，无法计算尺寸。');
        radius = NaN; height = NaN; bounds = struct();
        return;
    end
    
    [z_coords, y_coords, x_coords] = ind2sub(size(mask), find(mask));
    
    xmin = min(x_coords); xmax = max(x_coords);
    ymin = min(y_coords); ymax = max(y_coords);
    zmin = min(z_coords); zmax = max(z_coords);
    
    bounds = struct('xmin', xmin, 'xmax', xmax, 'ymin', ymin, 'ymax', ymax, 'zmin', zmin, 'zmax', zmax);

    radius_x = (xmax - xmin) * cellsize.dx / 2;
    radius_y = (ymax - ymin) * cellsize.dy / 2;
    height_z = (zmax - zmin) * cellsize.dz;

    radius = (radius_x + radius_y) / 2 * 1e9; % nm
    height = height_z * 1e9; % nm

    fprintf('尺寸估算完成: 半径 ≈ %.2f nm, 高度 ≈ %.2f nm\n', radius, height);
end