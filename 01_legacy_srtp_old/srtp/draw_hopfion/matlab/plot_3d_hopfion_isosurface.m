function plot_3d_hopfion_isosurface(m, cellsize, nodes, radius, height, save_path)
    fprintf('正在计算 mz=0 等值面...\n');

    % 1. 创建网格坐标 (物理单位：nm)
    x = (1:nodes.x) * cellsize.dx * 1e9;
    y = (1:nodes.y) * cellsize.dy * 1e9;
    z = (1:nodes.z) * cellsize.dz * 1e9;
    
    % meshgrid(x,y,z) 创建的网格维度为 (length(y), length(x), length(z))
    % 即 (ynodes, xnodes, znodes)
    [X, Y, Z] = meshgrid(x, y, z);
    
    % =====================================================================
    % --- 核心修正 ---
    % 原始 m 的维度是 (znodes, ynodes, xnodes, 3)
    % 为了匹配meshgrid的(ynodes, xnodes, znodes)，需要进行正确的维度换位
    % 新顺序: 2(y) -> 1, 3(x) -> 2, 1(z) -> 3
    permuted_m = permute(m, [2, 3, 1, 4]); 
    % =====================================================================

    % 2. 提取 mz=0 的等值面
    % 现在 V 的维度 (ynodes, xnodes, znodes) 与 X,Y,Z 完全匹配
    [faces, verts] = isosurface(X, Y, Z, permuted_m(:,:,:,3), 0);

    if isempty(verts)
        error('在数据中未找到mz=0的等值面。');
    end
    
    fprintf('正在为表面顶点插值计算颜色...\n');
    
    % 3. 使用interp3为每个顶点精确计算磁化矢量
    % verts的列分别是 x, y, z 坐标
    mx_interp = interp3(X, Y, Z, permuted_m(:,:,:,1), verts(:,1), verts(:,2), verts(:,3));
    my_interp = interp3(X, Y, Z, permuted_m(:,:,:,2), verts(:,1), verts(:,2), verts(:,3));

    % 4. 计算颜色数据 (xy平面角度)
    angles = atan2(my_interp, mx_interp);

    fprintf('正在进行三维渲染...\n');
    
    % 5. 创建图形和坐标轴
    figure('Position', [100, 100, 800, 650], 'Color', 'white');
    ax = axes;
    
    % 6. 使用 patch 函数绘制三维表面
    p = patch('Vertices', verts, 'Faces', faces, ...
          'FaceVertexCData', angles, ...
          'FaceColor', 'interp', ...
          'EdgeColor', 'none');
          
    % 7. 设置样式
    colormap(jet);
    lighting gouraud;
    camlight head;
    axis equal;
    grid on;
    
    xlabel('x (nm)');
    ylabel('y (nm)');
    zlabel('z (nm)');
    
    title_str = {'Hopfion 3D Isosurface (mz=0)'; ...
        sprintf('Est. Radius: %.2f nm, Est. Height: %.2f nm', radius, height)};
    title(title_str);
    
    view(30, 60);
    
    % 设置颜色条
    cb = colorbar;
    set(ax, 'CLim', [-pi, pi]);
    ylabel(cb, 'Angle atan2(m_y, m_x)');
    cb.Ticks = -pi : pi/2 : pi;
    cb.TickLabels = {'-p', '-p/2', '0', 'p/2', 'p'};
    
    % 8. 保存图像
    print(gcf, save_path, '-dpng', '-r300');
    fprintf('三维Hopfion图像已保存为 %s\n', save_path);
end