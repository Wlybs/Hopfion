import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from skimage import measure
from matplotlib.colors import Normalize
import os
import discretisedfield as df
from sklearn.decomposition import PCA

# =============== Angular Median ===============
def angular_median(angles):
    x = np.cos(angles)
    y = np.sin(angles)
    mean_x = np.mean(x, axis=1)
    mean_y = np.mean(y, axis=1)
    median_angles = np.arctan2(mean_y, mean_x)
    return median_angles

# =============== [Strategy 7.1] Percentile-Based Gradient Algorithm ===============
def calculate_hopfion_radii_advanced(m_field, percentile_threshold=99.9, **kwargs):
    """
    [Strategy 7.1] Percentile-Based Gradient Method.
    This version uses a percentile threshold to be robust against extreme outliers
    in the gradient field, which are likely numerical artifacts.
    """
    print("Calculating R and r using [Strategy 7.1] Percentile-Based Gradient Method...")
    m_array = m_field.array
    cell_size = m_field.mesh.cell
    pmin = m_field.mesh.region.pmin

    # Step 1: Calculate the magnitude of the magnetization gradient.
    print("Step 1/4: Calculating magnetization gradient magnitude...")
    grad_m = np.gradient(m_array, cell_size[0], cell_size[1], cell_size[2], axis=(0, 1, 2))
    grad_mag_sq = np.sum([np.sum(g**2, axis=3) for g in grad_m])

    # Step 2: Identify core region using a percentile threshold.
    print(f"Step 2/4: Identifying core region using {percentile_threshold}th percentile threshold...")
    threshold_value = np.percentile(grad_mag_sq, percentile_threshold)
    core_mask = grad_mag_sq > threshold_value

    if not np.any(core_mask):
        print("WARNING: Could not identify any high-gradient core region with percentile method. Try a lower --percentile value.")
        return []
    
    core_points_3d = pmin + np.array(np.where(core_mask)).T * cell_size
    print(f"DEBUG: Found {len(core_points_3d)} points in the high-gradient core region (top {100-percentile_threshold:.2f}%).")

    if len(core_points_3d) < 10:
        print("WARNING: Not enough points found in core region to perform a reliable fit. Try a lower --percentile value.")
        return []

    # Step 3: Use PCA on the gradient-defined core to find its true orientation.
    print("Step 3/4: Determining hopfion orientation with PCA...")
    pca = PCA(n_components=3).fit(core_points_3d)
    center = pca.mean_
    transformed_points = pca.transform(core_points_3d)

    # Step 4: Calculate radial distribution in the correct plane and find R, r.
    print("Step 4/4: Calculating radial distribution in PCA plane...")
    radial_distances = np.linalg.norm(transformed_points[:, :2], axis=1)

    R_hopfion = np.mean(radial_distances)
    r_hopfion = np.std(radial_distances)

    print(f"Calculation complete: R ≈ {R_hopfion*1e9:.2f} nm, r ≈ {r_hopfion*1e9:.2f} nm (from gradient-based core)")

    hopfion_results = [{'R': R_hopfion, 'r': r_hopfion, 'center': center}]
    return hopfion_results

# =============== Color Interpolation ===============
def interpolate_colors_for_vertices(m_field, verts):
    print("Calculating colors for vertices (using interpolation)...")
    pmin = m_field.mesh.region.pmin
    cell_size = m_field.mesh.cell
    indices = (verts - pmin) / cell_size
    indices = indices.T
    from scipy.ndimage import map_coordinates # Re-added import here for safety
    mx_interp = map_coordinates(m_field.array[..., 0], indices, order=1, mode='nearest')
    my_interp = map_coordinates(m_field.array[..., 1], indices, order=1, mode='nearest')
    colors = np.arctan2(my_interp, mx_interp)
    return colors

# =============== AFM Demodulation (unchanged) ===============
def demodulate_afm(m_field, afm_hint="auto", offset_hint=None):
    arr = m_field.array.copy()
    if afm_hint == "none": return m_field, ("none",(0,0,0))
    if afm_hint == "auto":
        mode = _auto_detect_afm_mode(arr)
        if mode is None:
            print("No typical AFM mode detected, treating as 'none'.")
            return m_field, ("none",(0,0,0))
    else: mode = afm_hint
    if offset_hint is None: offsets = _best_phase_for_mode(arr, mode)
    else: offsets = offset_hint
    sign = _build_sign_field(arr.shape[:3], mode, offsets).astype(m.dtype)[..., None]
    m_demod = df.Field(mesh=m_field.mesh, nvdim=3, value=arr * sign)
    return m_demod, (mode, offsets)

def _avg_neighbor_dot(m):
    mx = []
    for axis in range(3):
        a = m[..., :-1] if axis == 2 else (m[:, :-1, :] if axis == 1 else m[:-1, :, :])
        b = m[..., 1:]  if axis == 2 else (m[:, 1:, :]  if axis == 1 else m[1:, :, :])
        dots = np.sum(a * b, axis=-1)
        mx.append(np.mean(dots))
    return np.array(mx)

def _build_sign_field(shape, mode, offsets=(0,0,0)):
    nx, ny, nz = shape[:3]
    ix, iy, iz = np.ogrid[0:nx, 0:ny, 0:nz]
    ox, oy, oz = offsets
    if mode == "checker": sign = 1 - 2 * (((ix+ox) + (iy+oy) + (iz+oz)) % 2)
    elif mode == "layerX": sign = 1 - 2 * (((ix+ox) % 2))
    elif mode == "layerY": sign = 1 - 2 * (((iy+oy) % 2))
    elif mode == "layerZ": sign = 1 - 2 * (((iz+oz) % 2))
    else: sign = np.ones((nx, ny, nz), dtype=np.int8)
    return sign

def _auto_detect_afm_mode(m):
    avg = _avg_neighbor_dot(m)
    is_neg = avg < -0.6
    if np.all(is_neg): return "checker"
    if is_neg[0] and not is_neg[1] and not is_neg[2]: return "layerX"
    if is_neg[1] and not is_neg[0] and not is_neg[2]: return "layerY"
    if is_neg[2] and not is_neg[0] and not is_neg[1]: return "layerZ"
    return None

def _best_phase_for_mode(m, mode):
    shape = m.shape[:3]
    if mode == "checker": offs = [(ox,oy,oz) for ox in (0,1) for oy in (0,1) for oz in (0,1)]
    elif mode == "layerX": offs = [(ox,0,0) for ox in (0,1)]
    elif mode == "layerY": offs = [(0,oy,0) for oy in (0,1)]
    elif mode == "layerZ": offs = [(0,0,oz) for oz in (0,1)]
    else: return (0,0,0)
    best_off, best_score = None, -1e9
    for off in offs:
        sign = _build_sign_field(shape, mode, off).astype(m.dtype)[..., None]
        score = _avg_neighbor_dot(m * sign).mean()
        if score > best_score: best_score, best_off = score, off
    return best_off

# =============== Plotting Function ===============
def draw_isosurface(ovf_filename, hopfion_results, m_field, title_info=""):
    mz_volume = m_field.array[..., 2]
    print("\nCalculating mz=0 isosurface for plotting...")
    try:
        verts, faces, _, _ = measure.marching_cubes(
            volume=mz_volume, 
            level=0, 
            spacing=m_field.mesh.cell,
            step_size=2
        )
        verts += m_field.mesh.region.pmin
    except Exception as e:
        print(f"CRITICAL ERROR: Marching Cubes execution for plotting failed: {e}")
        return
    if len(verts) == 0:
        print("CRITICAL WARNING: Marching cubes for plotting generated 0 vertices.")
        return
    print(f"Generated {len(verts)} vertices for plot.")
    
    print("Calculating colors for vertices...")
    vertex_colors_angles = interpolate_colors_for_vertices(m_field, verts)
    print("Calculating colors for faces...")
    face_angles = vertex_colors_angles[faces]
    median_face_angles = angular_median(face_angles)
    norm = Normalize(vmin=-np.pi, vmax=np.pi)
    face_colors = plt.cm.hsv(norm(median_face_angles))

    print("Rendering 3D plot...")
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')
    mesh = Poly3DCollection(verts[faces]*1e9)
    mesh.set_facecolor(face_colors)
    mesh.set_edgecolor((0, 0, 0, 0.1))
    ax.add_collection3d(mesh)

    ax.set_xlim(verts[:, 0].min()*1e9, verts[:, 0].max()*1e9)
    ax.set_ylim(verts[:, 1].min()*1e9, verts[:, 1].max()*1e9)
    ax.set_zlim(verts[:, 2].min()*1e9, verts[:, 2].max()*1e9)
    ax.set_xlabel("x (nm)")
    ax.set_ylabel("y (nm)")
    ax.set_zlabel("z (nm)")
    ax.view_init(elev=30, azim=45)

    title_text = f"Hopfion Isosurface (mz=0)\n{os.path.basename(ovf_filename)}"
    if not hopfion_results:
        title_text += "\nCould not calculate Hopfion dimensions."
    else:
        for i, h in enumerate(hopfion_results):
            R_nm = h['R'] * 1e9
            r_str = f"{h['r']*1e9:.2f}" if h['r'] is not None else "?"
            title_text += f"\nCore {i+1}: R≈{R_nm:.2f}nm, r≈{r_str}nm"
    ax.set_title(title_text)

    axis_limits = np.array([ax.get_xlim(), ax.get_ylim(), ax.get_zlim()])
    ax.set_box_aspect(np.ptp(axis_limits, axis=1))
    sm = plt.cm.ScalarMappable(cmap='hsv', norm=norm)
    cbar = fig.colorbar(sm, ax=ax, shrink=0.6, aspect=20, pad=0.1)
    cbar.set_label('Angle arctan(my/mx)')
    cbar.set_ticks([-np.pi, -np.pi/2, 0, np.pi/2, np.pi])
    cbar.set_ticklabels(['-pi', '-pi/2', '0', 'pi/2', 'pi'])
    
    output_filename = os.path.splitext(ovf_filename)[0] + '_final_result.png'
    plt.savefig(output_filename, dpi=250)
    print(f"Image successfully saved to: {output_filename}")
    plt.close()

# =============== Main Function ===============
def main(ovf_files, afm_hint="auto", offset_hint=None, percentile_threshold=99.9, **kwargs):
    print("Loading OVF file(s) for plotting...")
    for ovf_file in ovf_files:
        try:
            raw = df.Field.from_file(ovf_file)
            m_demod, (mode, offsets) = demodulate_afm(raw, afm_hint=afm_hint, offset_hint=offset_hint)
            
            hopfion_results = calculate_hopfion_radii_advanced(m_demod, percentile_threshold=percentile_threshold)
            
            title_info = f"demod: {mode}{' '+str(offsets) if mode!='none' else ''}"
            draw_isosurface(ovf_file, hopfion_results, m_demod, title_info=title_info)
        except Exception as e:
            print(f"A critical error occurred while processing file {ovf_file}: {e}")

if __name__ == "__main__":
    import sys
    import glob
    args = sys.argv[1:]
    files = []
    afm_hint = "auto"
    offset_hint = None
    percentile_threshold = 99.9 # Default value

    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--afm":
            if i + 1 < len(args):
                afm_hint = args[i+1].lower(); i += 1
            else: print("ERROR: --afm requires a mode"); sys.exit(1)
        elif arg == "--offset":
            if i + 3 < len(args):
                try: offset_hint = (int(args[i+1]), int(args[i+2]), int(args[i+3])); i += 3
                except ValueError: print("ERROR: --offset requires three integers"); sys.exit(1)
            else: print("ERROR: --offset requires three integers"); sys.exit(1)
        elif arg == "--percentile":
            if i + 1 < len(args):
                try:
                    percentile_threshold = float(args[i+1])
                    i += 1
                except ValueError:
                    print("ERROR: --percentile requires a float value (e.g. '99.0')")
                    sys.exit(1)
            else:
                print("ERROR: --percentile requires a float value")
                sys.exit(1)
        else:
            files.append(arg)
        i += 1
        
    if not files:
        test_file = "stable-state-h+1+2.ovf"
        if os.path.exists(test_file): files = [test_file]
        else: files = glob.glob("*.ovf") + glob.glob("*.omf")
        if not files:
            print("ERROR: No .ovf or .omf files found.")
            sys.exit(1)
        print(f"Found {len(files)} file(s), beginning processing.")
        
    main(files, afm_hint=afm_hint, offset_hint=offset_hint, percentile_threshold=percentile_threshold)