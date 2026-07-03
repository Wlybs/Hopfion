"""Generate gated CW-bridge and source-geometry wavefield simulations."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

from resonance_analysis import generate_cw_mx3, generate_wavefield_mx3  # noqa: E402


def _write_manifest(path: Path, rows: list[dict]):
    fieldnames = [
        "name",
        "kind",
        "frequency_ghz",
        "source_axis",
        "vib_axis",
        "geometry",
        "b_amp_t",
        "run_ps",
        "mx3",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def generate_stage2_files(output_root, gate_path=None):
    """Generate stage-2 files only after the spatial localization gate passes."""
    root = Path(output_root)
    results_dir = root / "results"
    mx3_dir = root / "mx3"
    results_dir.mkdir(parents=True, exist_ok=True)
    mx3_dir.mkdir(parents=True, exist_ok=True)
    if gate_path is None:
        gate_path = results_dir / "stage1_gate.json"
    gate_path = Path(gate_path)

    status_path = results_dir / "stage2_generation_status.json"
    if not gate_path.is_file():
        status_path.write_text(
            json.dumps({"generated": False, "reason": "stage1_gate_missing"}, indent=2) + "\n",
            encoding="utf-8",
        )
        return []
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    if gate.get("passed") is not True:
        status_path.write_text(
            json.dumps({"generated": False, "reason": "stage1_gate_failed"}, indent=2) + "\n",
            encoding="utf-8",
        )
        return []

    target_frequency = float(gate.get("target_frequency_ghz", 174.0))

    def frequency_label(value):
        return f"{value:g}".replace(".", "p").replace("-", "m")

    rows = []
    cw_cases = []
    for offset in (-24, -14, -4, 0, 6, 16, 26):
        frequency = target_frequency + offset
        cw_cases.append(("x", "x", frequency, 0.2))
    cw_cases.extend([
        ("x", "x", target_frequency, 0.05),
        ("x", "x", target_frequency, 0.1),
        ("z", "x", target_frequency, 0.2),
        ("x", "z", target_frequency, 0.2),
    ])
    for source_axis, vib_axis, frequency, amplitude in cw_cases:
        millitesla = int(round(amplitude * 1000))
        name = (
            f"cw_src{source_axis.upper()}_vib{vib_axis.upper()}_"
            f"f{frequency_label(frequency)}_B{millitesla:03d}mT"
        )
        path = mx3_dir / f"{name}.mx3"
        generate_cw_mx3(
            path,
            freq_ghz=frequency,
            source_axis=source_axis,
            vib_axis=vib_axis,
            B_amp=amplitude,
            run_ns=0.3,
            table_dt_ps=0.1,
            save_m=False,
            spatial_roi=(26, 74, 26, 74, 26, 74),
            spatial_dt_ps=1.0,
        )
        rows.append({
            "name": name,
            "kind": "cw",
            "frequency_ghz": frequency,
            "source_axis": source_axis,
            "vib_axis": vib_axis,
            "geometry": "plane",
            "b_amp_t": amplitude,
            "run_ps": 300,
            "mx3": f"mx3/{path.name}",
        })

    for frequency in (700, 1000):
        for geometry in ("plane", "point"):
            name = f"wavefield_{geometry}_f{frequency}"
            path = mx3_dir / f"{name}.mx3"
            generate_wavefield_mx3(path, geometry=geometry, frequency_ghz=frequency)
            rows.append({
                "name": name,
                "kind": "wavefield",
                "frequency_ghz": frequency,
                "source_axis": "x",
                "vib_axis": "x",
                "geometry": geometry,
                "b_amp_t": 0.1 if geometry == "plane" else 10.0,
                "run_ps": 30,
                "mx3": f"mx3/{path.name}",
            })

    _write_manifest(results_dir / "stage2_simulation_manifest.csv", rows)
    status_path.write_text(
        json.dumps({
            "generated": True,
            "run_count": len(rows),
            "target_frequency_ghz": target_frequency,
        }, indent=2) + "\n",
        encoding="utf-8",
    )
    return rows


if __name__ == "__main__":
    generate_stage2_files(Path(__file__).resolve().parents[1])
