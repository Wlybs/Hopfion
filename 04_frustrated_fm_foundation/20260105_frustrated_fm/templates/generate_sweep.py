"""
generate_sweep.py
Template-based mx3 generator for controlled-variable sweep experiments.

Usage:
    python generate_sweep.py <config.json>

Config format (JSON):
{
    "output_dir": "path/to/output",
    "template": "templates/frustrated_fm_base.mx3.template",
    "description_prefix": "Drift experiment",
    "sweep_var": "LoadFile",
    "defaults": {
        "cellsize": "0.5e-9",
        "Ms_val": "1.5e5",
        "A_base": "5e-12",
        ...
    },
    "runs": [
        {"name": "bg_mz_axis_z", "LoadFile": "path/to/ovf"},
        {"name": "bg_mx_axis_x", "LoadFile": "path/to/ovf"},
        ...
    ]
}

Each run inherits ALL defaults, overriding only the fields specified.
After generation, automatically runs audit_sweep_params.py to verify
controlled-variable consistency.
"""

import json
import os
import sys
import subprocess


HERE = os.path.dirname(os.path.abspath(__file__))

# Default parameters for frustrated FM model
FRUSTRATED_FM_DEFAULTS = {
    "cellsize":       "0.5e-9",
    "Ms_val":         "1.5e5",
    "A_base":         "5e-12",
    "Nx":             "100",
    "Ny":             "100",
    "Nz":             "100",
    "PBC_x":          "1",
    "PBC_y":          "1",
    "PBC_z":          "1",
    "Ku1":            "0",
    "anisU_line":     "",
    "EnableDemag":    "false",
    "alpha":          "0.2",
    "J2_ratio":       "-0.164",
    "J4_ratio":       "-0.082",
    "run_time":       "2e-9",
    "autosave":       "1e-10",
    "tableautosave":  "1e-11",
    "extra_setup":    "",
    "LoadFile":       "",
}


def generate(config_path):
    with open(config_path) as f:
        config = json.load(f)

    output_dir = os.path.join(HERE, config["output_dir"])
    template_path = os.path.join(HERE, config.get("template",
                                 "templates/frustrated_fm_base.mx3.template"))
    sweep_var = config["sweep_var"]
    desc_prefix = config.get("description_prefix", "Sweep experiment")

    os.makedirs(output_dir, exist_ok=True)

    with open(template_path) as f:
        template = f.read()

    # Merge defaults: built-in < config defaults < per-run overrides
    base_params = dict(FRUSTRATED_FM_DEFAULTS)
    base_params.update(config.get("defaults", {}))

    runs = config["runs"]
    print(f"Generating {len(runs)} mx3 files in: {output_dir}")
    print(f"Sweep variable: {sweep_var}")
    print(f"Template: {template_path}")
    print()

    # Show controlled parameters
    print("--- Controlled parameters (constant across all runs) ---")
    for k, v in sorted(base_params.items()):
        if k in ("extra_setup", "anisU_line"):
            continue
        print(f"  {k:20s} = {v}")
    print()

    # Generate each file
    generated_files = []
    for run in runs:
        name = run["name"]
        params = dict(base_params)
        params.update(run)
        params["sweep_var"] = sweep_var
        params["sweep_val"] = params.get(sweep_var, "N/A")
        params["description"] = f"{desc_prefix} — {name}"

        # Handle anisU: if Ku1 != 0 and no anisU_line set, add default
        if params["Ku1"] != "0" and not params["anisU_line"]:
            params["anisU_line"] = 'anisU = vector(0, 0, 1)\n'

        content = template.format(**params)
        out_path = os.path.join(output_dir, f"{name}.mx3")
        with open(out_path, "w") as f:
            f.write(content)
        generated_files.append(out_path)
        print(f"  [{name}] {sweep_var} = {params['sweep_val']}")

    print(f"\nGenerated {len(generated_files)} files.")

    # Auto-audit
    print("\n" + "=" * 60)
    print("Running parameter audit...")
    print("=" * 60 + "\n")

    audit_script = os.path.join(HERE, "audit_sweep_params.py")
    result = subprocess.run(
        [sys.executable, audit_script, output_dir],
        capture_output=False
    )

    if result.returncode != 0:
        print("\n" + "!" * 60)
        print("AUDIT FAILED — DO NOT RUN these simulations!")
        print("Fix the configuration and re-generate.")
        print("!" * 60)
        sys.exit(1)
    else:
        print("\nAudit passed. Safe to run simulations.")

    # Generate runner script
    runner_path = os.path.join(output_dir, "run_sweep.sh")
    mumax = "/home/wujiale/go/bin/mumax3"
    lines = [
        "#!/bin/bash",
        f"# Auto-generated runner for {desc_prefix}",
        "set -e",
        f'MUMAX={mumax}',
        f'DIR="$(cd "$(dirname "$0")" && pwd)"',
        f'LOG="$DIR/run_sweep.log"',
        "",
        'echo "=== Sweep Runner ===" | tee "$LOG"',
        'echo "Start: $(date)" | tee -a "$LOG"',
        "",
    ]
    for run in runs:
        name = run["name"]
        lines.append(f'echo ">>> {name}.mx3 at $(date)" | tee -a "$LOG"')
        lines.append(f'cd "$DIR" && $MUMAX "{name}.mx3" 2>&1 | tee -a "$LOG"')
        lines.append("")
    lines.append('echo "=== Complete: $(date) ===" | tee -a "$LOG"')

    with open(runner_path, "w") as f:
        f.write("\n".join(lines) + "\n")
    os.chmod(runner_path, 0o755)
    print(f"\nRunner script: {runner_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    generate(sys.argv[1])
