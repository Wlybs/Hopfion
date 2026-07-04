import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from skimage import measure
from matplotlib.colors import Normalize
import os
import discretisedfield as df
from scipy.optimize import least_squares
from scipy.ndimage import map_coordinates

# =============== Angular Median (from both versions) ===============
def angular_median(angles):
    x = np.cos(angles)
    y = np.sin(angles)
    mean_x = np.mean(x, axis=1)
    mean_y = np.mean(y, axis=1)
    median_angles = np.arctan2(mean_y, mean_x)
    return median_angles

# =============== CORRECT CALCULATION LOGIC (from Version A) ===============
def circle_fit_residuals(params, points):
    xc, yc, R = params
    x, y = points[:, 0], points[:, 1]
    return np.sqrt((x - xc)**2 + (y - yc)**2) - R

def calculate_hopfion_radii_topological(m_field, core_mz_threshold=0.02):
    """
    [Correct Algorithm from Version A] Uses topological preimage and circle fitting.
    """
    print("Calculating R and r using [Topological Preimage Method]...")
    mz = m_field.array[..., 2]

    # --- 1. Calculate R ---
    print("Step 1/2: Calculating major radius R...")
    mz_min = np.min(mz)
    preimage_mask = mz < (mz_min + core_mz_threshold)

    if not np.any(preimage_mask):
        print(f"WARNING: Could not find topological preimage (mz ≈ {mz_min:.3f}). Cannot calculate dimensions.")
        return None, None

    preimage_coords_grid = np.array(np.where(preimage_mask)).T
    preimage_coords_real = m_field.mesh.region.pmin + preimage_coords_grid * m_field.mesh.cell

    xy_coords = preimage_coords_real[:, :2]
    if len(xy_coords) < 3:
        print("WARNING: Too few core points found to perform a circle fit.")
        return None, None
        
    center_guess = np.mean(xy_coords, axis=0)
    radius_guess = np.mean(np.sqrt(np.sum((xy_coords - center_guess)**2, axis=1)))
    
    try:
        res = least_squares(circle_fit_residuals, [center_guess[0], center_guess[1], radius_guess], args=(xy_coords,))
        xc, yc, R_hopfion = res.x
    except Exception as e:
        print(f"ERROR: Circle fit for the core ring failed: {e}")
        return None, None

    print(f"Core ring fit complete: center≈({xc*1e9:.1f}, {yc*1e9:.1f})nm, R≈{R_hopfion*1e9:.2f}nm")

    # --- 2. Calculate r ---
    print("Step 2/2: Calculating minor radius r...")
    try:
        verts, _, _, _ = measure.marching_cubes(volume=mz, level=0, spacing=m_field.mesh.cell)
        verts += m_field.mesh.region.pmin
    except (ValueError, RuntimeError) as e:
        print(f"Failed to extract mz=0 isosurface: {e}")
        return R_hopfion, None

    if len(verts) == 0:
        print("WARNING: mz=0 isosurface contains no vertices. Cannot calculate r.")
        return R_hopfion, None

    core_z_center = np.mean(preimage_coords_real[:, 2])
    dist_xy_from_center = np.sqrt((verts[:, 0] - xc)**2 + (verts[:, 1] - yc)**2)
    distances_to_core_ring = np.sqrt((dist_xy_from_center - R_hopfion)**2 + (verts[:, 2] - core_z_center)**2)
    r_hopfion = np.mean(distances_to_core_ring)

    print(f"Calculation complete: Major R ≈ {R_hopfion*1e9:.2f} nm, Minor r ≈ {r_hopfion*1e9:.2f} nm")
    return R_hopfion, r_hopfion

# =============== Color Interpolation (from both versions) ===============
def interpolate_colors_for_vertices(m_field, verts):
    print("Calculating colors for vertices (using interpolation)...")
    pmin = m_field.mesh.region.pmin
    cell_size = m_field.mesh.cell
    indices = (verts - pmin) / cell_size
    indices = indices.T
    mx_interp = map_coordinates(m_field.array[..., 0], indices, order=1, mode='nearest')
    my_interp = map_coordinates(m_field.array[..., 1], indices, order=1, mode='nearest')
    colors = np.arctan2(my_interp, mx_interp)
    return colors

# =============== AFM Demodulation (from both versions) ===============
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
    sign = _build_sign_field(arr.shape[:3], mode, offsets).astype(m_field.dtype)[..., None]
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

# =============== FAST PLOTTING FUNCTION (from Version B) ===============
def draw_isosurface(ovf_filename, R_hopfion, r_hopfion, m_field, title_info=""):
    mz_volume = m_field.array[..., 2]
    print("\nCalculating mz=0 isosurface for plotting...")
    try:
        # KEY FEATURE: step_size=2 for fast plotting
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
    mesh.set_edgecolor((0, 0, 0, 0.1)) # Keep nice edges
    ax.add_collection3d(mesh)

    ax.set_xlim(verts[:, 0].min()*1e9, verts[:, 0].max()*1e9)
    ax.set_ylim(verts[:, 1].min()*1e9, verts[:, 1].max()*1e9)
    ax.set_zlim(verts[:, 2].min()*1e9, verts[:, 2].max()*1e9)
    ax.set_xlabel("x (nm)")
    ax.set_ylabel("y (nm)")
    ax.set_zlabel("z (nm)")
    ax.view_init(elev=30, azim=45) # Keep nice view angle

    title_text = f"Hopfion Isosurface (mz=0) - {title_info}\n{os.path.basename(ovf_filename)}"
    if R_hopfion is None:
        title_text += "\nCould not calculate Hopfion dimensions."
    else:
        r_str = f"{r_hopfion*1e9:.2f}" if r_hopfion is not None else "?"
        title_text += f"\nEst. R≈{R_hopfion*1e9:.2f}nm, r≈{r_str}nm"
    ax.set_title(title_text)

    axis_limits = np.array([ax.get_xlim(), ax.get_ylim(), ax.get_zlim()])
    ax.set_box_aspect(np.ptp(axis_limits, axis=1))
    sm = plt.cm.ScalarMappable(cmap='hsv', norm=norm)
    cbar = fig.colorbar(sm, ax=ax, shrink=0.6, aspect=20, pad=0.1)
    cbar.set_label('Angle arctan(my/mx)')
    cbar.set_ticks([-np.pi, -np.pi/2, 0, np.pi/2, np.pi])
    cbar.set_ticklabels(['-pi', '-pi/2', '0', 'pi/2', 'pi'])
    
    output_filename = os.path.splitext(ovf_filename)[0] + '_final_version.png'
    plt.savefig(output_filename, dpi=250)
    print(f"Image successfully saved to: {output_filename}")
    plt.close()

# =============== Main Function (Adapted from B) ===============
def main(ovf_files, afm_hint="auto", offset_hint=None):
    print("Loading OVF file(s) for plotting...")
    for ovf_file in ovf_files:
        try:
            print(f"\n--- Processing {ovf_file} ---")
            raw = df.Field.from_file(ovf_file)
            m_demod, (mode, offsets) = demodulate_afm(raw, afm_hint=afm_hint, offset_hint=offset_hint)
            
            # MODIFICATION: Call the correct calculation function
            R, r = calculate_hopfion_radii_topological(m_demod)
            
            title_info = f"demod: {mode}{' '+str(offsets) if mode!='none' else ''}"
            # MODIFICATION: Call the drawing function with the new R, r variables
            draw_isosurface(ovf_file, R, r, m_demod, title_info=title_info)
        except Exception as e:
            print(f"A critical error occurred while processing file {ovf_file}: {e}")

if __name__ == "__main__":
    import sys
    import glob
    args = sys.argv[1:]
    files = []
    afm_hint = "auto"
    offset_hint = None

    # MODIFICATION: Removed the --percentile argument parsing
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
        else:
            files.append(arg)
        i += 1
        
    if not files:
        # Keep the smart file finding from B
        files = glob.glob("*.ovf") + glob.glob("*.omf")
        if not files:
            print("ERROR: No .ovf or .omf files found in the current directory.")
            sys.exit(1)
        print(f"No file specified. Found {len(files)} file(s) to process.")
        
    main(files, afm_hint=afm_hint, offset_hint=offset_hint)
