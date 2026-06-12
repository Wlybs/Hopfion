"""Generate the stage-1 Mumax3 scripts and machine-readable manifest."""

import csv
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

from resonance_analysis import (  # noqa: E402
    generate_circular_burst_mx3,
    generate_sinc_ringdown_mx3,
)


def generate_stage1_files(output_root):
    """Write the seven approved stage-1 scripts and return manifest rows."""
    root = Path(output_root)
    mx3_dir = root / "mx3"
    results_dir = root / "results"
    mx3_dir.mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)

    cases = [
        {
            "name": "linear_Bz_1mT_05ns",
            "kind": "sinc",
            "b0_t": 0.001,
            "run_ns": 0.5,
            "initial_state": "hopfion",
            "spatial": False,
        },
        {
            "name": "linear_Bz_2mT_05ns",
            "kind": "sinc",
            "b0_t": 0.002,
            "run_ns": 0.5,
            "initial_state": "hopfion",
            "spatial": False,
        },
        {
            "name": "linewidth_Bz_1mT_10ns",
            "kind": "sinc",
            "b0_t": 0.001,
            "run_ns": 1.0,
            "initial_state": "hopfion",
            "spatial": False,
        },
        {
            "name": "spatial_hopfion_Bz",
            "kind": "sinc",
            "b0_t": 0.005,
            "run_ns": 0.3,
            "initial_state": "hopfion",
            "spatial": True,
        },
        {
            "name": "spatial_uniform_Bz",
            "kind": "sinc",
            "b0_t": 0.005,
            "run_ns": 0.3,
            "initial_state": "uniform_z",
            "spatial": True,
        },
        {
            "name": "circular_plus_2mT",
            "kind": "circular",
            "b0_t": 0.002,
            "run_ns": 0.5,
            "initial_state": "hopfion",
            "spatial": False,
            "handedness": 1,
        },
        {
            "name": "circular_minus_2mT",
            "kind": "circular",
            "b0_t": 0.002,
            "run_ns": 0.5,
            "initial_state": "hopfion",
            "spatial": False,
            "handedness": -1,
        },
    ]

    for case in cases:
        path = mx3_dir / f"{case['name']}.mx3"
        if case["kind"] == "circular":
            generate_circular_burst_mx3(
                path,
                handedness=case["handedness"],
                b0_t=case["b0_t"],
                run_ns=case["run_ns"],
            )
        else:
            spatial_roi = (26, 74, 26, 74, 26, 74) if case["spatial"] else None
            generate_sinc_ringdown_mx3(
                path,
                drive_axis="z",
                cutoff_ghz=2000.0,
                b0_t=case["b0_t"],
                run_ns=case["run_ns"],
                table_dt_ps=0.05,
                uniform_background=case["initial_state"] == "uniform_z",
                spatial_roi=spatial_roi,
                spatial_dt_ps=0.2 if case["spatial"] else None,
            )
        case["mx3"] = f"mx3/{path.name}"

    fieldnames = [
        "name",
        "kind",
        "b0_t",
        "run_ns",
        "initial_state",
        "spatial",
        "handedness",
        "mx3",
    ]
    manifest_path = results_dir / "simulation_manifest.csv"
    with manifest_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(cases)
    return cases


if __name__ == "__main__":
    generate_stage1_files(Path(__file__).resolve().parents[1])
