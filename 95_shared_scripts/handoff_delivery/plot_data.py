"""Generate bounded, non-OVF plotting data for spatial handoff figures."""

from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile

import numpy as np


PINNED_PYTHON = Path("/mnt/d/Research/Hopfion/hopfion/bin/python")
_PINNED_MARKER = "HOPFION_PLOT_DATA_PINNED"


def _write(path: Path, header: tuple[str, ...], rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def _field(path: Path):
    import discretisedfield as df

    return df.Field.from_file(str(path))


def _archive_arrays(path: Path):
    import zstandard

    with path.open("rb") as raw:
        with zstandard.ZstdDecompressor().stream_reader(raw) as stream:
            with tarfile.open(fileobj=stream, mode="r|") as archive:
                for member in archive:
                    if not member.isfile() or not member.name.endswith(".ovf"):
                        continue
                    if Path(member.name).name != member.name:
                        raise RuntimeError(f"unsafe archive member: {member.name}")
                    source = archive.extractfile(member)
                    if source is None:
                        raise RuntimeError(f"cannot read archive member: {member.name}")
                    with tempfile.NamedTemporaryFile(suffix=".ovf", dir="/tmp") as tmp:
                        while chunk := source.read(1024 * 1024):
                            tmp.write(chunk)
                        tmp.flush()
                        field = _field(Path(tmp.name))
                        yield (
                            member.name,
                            np.asarray(field.array, dtype=np.float32).copy(),
                            np.asarray(field.mesh.cell, dtype=float) * 1e9,
                            np.asarray(field.mesh.region.pmin, dtype=float) * 1e9,
                        )


def _centroid(array: np.ndarray, cell_nm: np.ndarray, pmin_nm: np.ndarray) -> np.ndarray:
    weight = np.maximum(1.0 - array[..., 2], 0.0)
    total = float(weight.sum())
    result = []
    for axis, length in enumerate(weight.shape):
        coordinates = pmin_nm[axis] + cell_nm[axis] * (np.arange(length) + 0.5)
        shape = [1, 1, 1]
        shape[axis] = length
        result.append(float(np.sum(coordinates.reshape(shape) * weight) / total))
    return np.asarray(result)


def _surface_mesh(source: Path, output: Path) -> None:
    from scipy.ndimage import map_coordinates
    from skimage import measure

    field = _field(source)
    array = np.asarray(field.array)
    verts, faces, _, _ = measure.marching_cubes(
        array[..., 2], level=0, spacing=field.mesh.cell
    )
    verts += field.mesh.region.pmin
    indexes = ((verts - field.mesh.region.pmin) / field.mesh.cell).T
    mx = map_coordinates(array[..., 0], indexes, order=1, mode="nearest")
    my = map_coordinates(array[..., 1], indexes, order=1, mode="nearest")
    angles = np.arctan2(
        np.mean(np.sin(np.arctan2(my, mx))[faces], axis=1),
        np.mean(np.cos(np.arctan2(my, mx))[faces], axis=1),
    )
    rows = (
        (face_id, vertex_id, *(verts[index] * 1e9), angles[face_id])
        for face_id, face in enumerate(faces)
        for vertex_id, index in enumerate(face)
    )
    _write(output, ("face_id", "vertex_id", "x_nm", "y_nm", "z_nm", "phi_rad"), rows)


def _trajectory(source: Path, output: Path, dt_ns: float = 0.05) -> None:
    rows = []
    initial = None
    for frame, (_name, array, cell, pmin) in enumerate(_archive_arrays(source)):
        center = _centroid(array, cell, pmin)
        if initial is None:
            initial = center
        delta = center - initial
        rows.append((frame, frame * dt_ns, *delta, float(np.linalg.norm(delta))))
    _write(output, ("frame", "time_ns", "dx_nm", "dy_nm", "dz_nm", "dr_nm"), rows)


def _projections(source: Path, output: Path, dt_ns: float = 0.01) -> None:
    initial = cell = pmin = None
    sum_sq = peak = final = None
    count = 0
    for _name, array, cell_now, pmin_now in _archive_arrays(source):
        if initial is None:
            initial, cell, pmin = array, cell_now, pmin_now
            continue
        amplitude = np.linalg.norm(array - initial, axis=-1)
        sum_sq = amplitude * amplitude if sum_sq is None else sum_sq + amplitude * amplitude
        peak = amplitude if peak is None else np.maximum(peak, amplitude)
        final = amplitude
        count += 1
    if initial is None or final is None or sum_sq is None or peak is None:
        raise RuntimeError(f"archive has insufficient OVF frames: {source}")
    rms = np.sqrt(sum_sq / count)
    core = initial[..., 2] < 0
    assert cell is not None and pmin is not None
    rows = []
    for label, volume in (("rms", rms), ("final", final), ("peak", peak), ("core", core.astype(float))):
        for plane, axis in (("xy", 2), ("xz", 1), ("yz", 0)):
            projection = np.max(volume, axis=axis) if label == "core" else np.mean(volume, axis=axis)
            kept = [value for value in range(3) if value != axis]
            for indexes in np.ndindex(projection.shape):
                u = pmin[kept[0]] + cell[kept[0]] * (indexes[0] + 0.5)
                v = pmin[kept[1]] + cell[kept[1]] * (indexes[1] + 0.5)
                rows.append((label, plane, indexes[0], indexes[1], u, v, projection[indexes]))
    _write(output, ("map", "plane", "i", "j", "u_nm", "v_nm", "value"), rows)


def _generate(project: Path, output: Path) -> tuple[Path, ...]:
    outputs: list[Path] = []
    qh = (
        ("qh1", "hopfion_Qh1_p1q1.ovf"),
        ("qh2_p2q1", "hopfion_Qh2_p2q1.ovf"),
        ("qh2_p1q2", "hopfion_Qh2_p1q2.ovf"),
        ("qh4", "hopfion_Qh4_p2q2.ovf"),
    )
    for label, name in qh:
        target = output / f"fig3_1_{label}_mesh.csv"
        _surface_mesh(project / "95_shared_scripts" / name, target)
        outputs.append(target)
    direction_root = project / "04_frustrated_fm_foundation/20260105_frustrated_fm/spin_wave_dynamics/drive_selection/plane_wave"
    for label in ("srcX_vibX", "srcX_vibZ", "srcY_vibX", "srcZ_vibX", "srcZ_vibZ"):
        target = output / f"direction_{label}_centroid.csv"
        _trajectory(direction_root / f"sw_{label}.out/ovf_archive.tar.zst", target)
        outputs.append(target)
    mode_root = project / "04_frustrated_fm_foundation/20260105_frustrated_fm/spin_wave_dynamics/freq_sweep/plane_wave"
    mode = (
        ("srcx1000", "srcX/05ns/sw_f1000GHz.out/ovf_archive.tar.zst"),
        ("srcx200", "srcX/02ns/sw_f200GHz.out/ovf_archive.tar.zst"),
        ("srcz100", "srcZ/sw_srcZ_f100GHz.out/ovf_archive.tar.zst"),
        ("srcz1100", "srcZ/sw_srcZ_fine_f1100GHz.out/ovf_archive.tar.zst"),
    )
    for label, relative in mode:
        target = output / f"mode_map_{label}_projections.csv"
        _projections(mode_root / relative, target)
        outputs.append(target)
    return tuple(outputs)


def generate_all(project: Path, output: Path) -> tuple[Path, ...]:
    project, output = project.resolve(), output.resolve()
    if os.environ.get(_PINNED_MARKER) == "1":
        return _generate(project, output)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(project / "95_shared_scripts")
    env[_PINNED_MARKER] = "1"
    subprocess.run(
        [str(PINNED_PYTHON), "-m", "handoff_delivery.plot_data", "--project", str(project), "--output", str(output)],
        env=env,
        check=True,
        timeout=1800,
    )
    return tuple(sorted(output.glob("*.csv")))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    _generate(args.project.resolve(), args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
