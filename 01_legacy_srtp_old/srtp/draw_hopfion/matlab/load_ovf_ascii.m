function [m, cellsize, nodes] = load_ovf_ascii(filename)
    fprintf('正在加载OVF文件...\n');
    fid = fopen(filename, 'r');
    if fid == -1
        error('无法打开文件: %s', filename);
    end
    
    xnodes = 0; ynodes = 0; znodes = 0;
    xstep = 0; ystep = 0; zstep = 0;
    line = fgetl(fid);
    while ischar(line)
        % R2014a 兼容性修改：使用 ~isempty(strfind(...)) 替代 contains()
        if ~isempty(strfind(line, 'xnodes'))
            parts = strsplit(line, ':'); xnodes = str2double(parts{2});
        elseif ~isempty(strfind(line, 'ynodes'))
            parts = strsplit(line, ':'); ynodes = str2double(parts{2});
        elseif ~isempty(strfind(line, 'znodes'))
            parts = strsplit(line, ':'); znodes = str2double(parts{2});
        elseif ~isempty(strfind(line, 'xstepsize'))
            parts = strsplit(line, ':'); xstep = str2double(parts{2});
        elseif ~isempty(strfind(line, 'ystepsize'))
            parts = strsplit(line, ':'); ystep = str2double(parts{2});
        elseif ~isempty(strfind(line, 'zstepsize'))
            parts = strsplit(line, ':'); zstep = str2double(parts{2});
        elseif ~isempty(strfind(line, '# Begin: Data Text'))
            break;
        end
        line = fgetl(fid);
    end
    
    num_lines = xnodes * ynodes * znodes;
    data_block = textscan(fid, '%f %f %f', num_lines);
    fclose(fid);
    
    data_matrix = cell2mat(data_block);
    
    m_reshaped = reshape(data_matrix', [3, xnodes, ynodes, znodes]);
    m = permute(m_reshaped, [4, 3, 2, 1]);
    
    cellsize = struct('dx', xstep, 'dy', ystep, 'dz', zstep);
    nodes = struct('x', xnodes, 'y', ynodes, 'z', znodes);
end