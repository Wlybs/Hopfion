"""Generate quench controls and clean ringdowns from an equilibrated state."""

from __future__ import annotations

import csv
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

from resonance_analysis import (  # noqa: E402
    generate_circular_burst_mx3,
    generate_equilibrated_state_mx3,
    generate_sinc_ringdown_mx3,
)


def generate_control_files(output_root):
    """Write the approved recovery matrix after detecting boundary quench."""
    root = Path(output_root).resolve()
    mx3_dir = root / "mx3"
    results_dir = root / "results"
    mx3_dir.mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)
    equilibrated = (
        mx3_dir
        / "equilibrate_open_boundary.out"
        / "equilibrated_open_boundary.ovf"
    )
    rows = []

    def add(name, stage, kind, **parameters):
        rows.append({
            "name": name,
            "stage": stage,
            "kind": kind,
            "b0_t": parameters.get("b0_t", ""),
            "run_ns": parameters.get("run_ns", ""),
            "initial_state": parameters.get("initial_state", ""),
            "mx3": f"mx3/{name}.mx3",
        })

    quench_name = "control_quench_Bz_0mT_05ns"
    generate_sinc_ringdown_mx3(
        mx3_dir / f"{quench_name}.mx3",
        drive_axis="z",
        b0_t=0.0,
        run_ns=0.5,
        table_dt_ps=0.05,
    )
    add(
        quench_name,
        "quench_control",
        "sinc",
        b0_t=0.0,
        run_ns=0.5,
        initial_state="pbc_relaxed_then_open",
    )

    equilibrium_name = "equilibrate_open_boundary"
    generate_equilibrated_state_mx3(mx3_dir / f"{equilibrium_name}.mx3")
    add(
        equilibrium_name,
        "equilibration",
        "relax",
        initial_state="pbc_relaxed_then_open",
    )

    for amplitude in (0.0, 0.001, 0.002, 0.005):
        millitesla = int(round(amplitude * 1000))
        name = f"clean_Bz_{millitesla}mT_05ns"
        generate_sinc_ringdown_mx3(
            mx3_dir / f"{name}.mx3",
            drive_axis="z",
            b0_t=amplitude,
            run_ns=0.5,
            table_dt_ps=0.05,
            init_ovf=str(equilibrated),
        )
        add(
            name,
            "clean_linearity",
            "sinc",
            b0_t=amplitude,
            run_ns=0.5,
            initial_state="equilibrated_open_boundary",
        )

    for amplitude in (0.0, 0.001):
        millitesla = int(round(amplitude * 1000))
        linewidth_name = f"clean_Bz_{millitesla}mT_10ns"
        generate_sinc_ringdown_mx3(
            mx3_dir / f"{linewidth_name}.mx3",
            drive_axis="z",
            b0_t=amplitude,
            run_ns=1.0,
            table_dt_ps=0.05,
            init_ovf=str(equilibrated),
        )
        add(
            linewidth_name,
            "clean_validation",
            "sinc",
            b0_t=amplitude,
            run_ns=1.0,
            initial_state="equilibrated_open_boundary",
        )

    for amplitude in (0.0, 0.005):
        millitesla = int(round(amplitude * 1000))
        name = f"clean_spatial_Bz_{millitesla}mT"
        generate_sinc_ringdown_mx3(
            mx3_dir / f"{name}.mx3",
            drive_axis="z",
            b0_t=amplitude,
            run_ns=0.3,
            table_dt_ps=0.05,
            init_ovf=str(equilibrated),
            spatial_roi=(26, 74, 26, 74, 26, 74),
            spatial_dt_ps=0.2,
        )
        add(
            name,
            "clean_validation",
            "spatial_sinc",
            b0_t=amplitude,
            run_ns=0.3,
            initial_state="equilibrated_open_boundary",
        )

    uniform_name = "clean_spatial_uniform_Bz_5mT"
    generate_sinc_ringdown_mx3(
        mx3_dir / f"{uniform_name}.mx3",
        drive_axis="z",
        b0_t=0.005,
        run_ns=0.3,
        table_dt_ps=0.05,
        uniform_background=True,
        spatial_roi=(26, 74, 26, 74, 26, 74),
        spatial_dt_ps=0.2,
    )
    add(
        uniform_name,
        "clean_validation",
        "spatial_sinc",
        b0_t=0.005,
        run_ns=0.3,
        initial_state="uniform_z",
    )

    for handedness, label in ((1, "plus"), (-1, "minus")):
        name = f"clean_circular_{label}_2mT"
        generate_circular_burst_mx3(
            mx3_dir / f"{name}.mx3",
            handedness=handedness,
            b0_t=0.002,
            run_ns=0.5,
            init_ovf=str(equilibrated),
        )
        add(
            name,
            "clean_validation",
            "circular",
            b0_t=0.002,
            run_ns=0.5,
            initial_state="equilibrated_open_boundary",
        )

    manifest_path = results_dir / "control_simulation_manifest.csv"
    with manifest_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return rows


if __name__ == "__main__":
    generate_control_files(Path(__file__).resolve().parents[1])
