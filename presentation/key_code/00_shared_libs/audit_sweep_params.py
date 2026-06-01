"""
audit_sweep_params.py
Pre-simulation parameter audit for controlled-variable experiments.

Usage:
    python audit_sweep_params.py <directory>

Scans all .mx3 files in <directory>, extracts key parameters, and reports
any inconsistencies that violate controlled-variable experimental design.

The ONLY parameter that should differ between files is the intended sweep
variable (Ku1, frequency, source position, etc.). All other physics
parameters must be identical.

Exit code 0 = PASS, 1 = FAIL (inconsistencies found).
"""

import os
import re
import sys
from collections import defaultdict


# Parameters to extract and check for consistency
PARAM_PATTERNS = {
    "alpha":         r'^\s*alpha\s*=\s*([0-9.e+\-]+)',
    "Ku1":           r'^\s*Ku1\s*=\s*([^\s/]+)',
    "Msat/Ms_val":   r'(?:Ms_val|Ms)\s*:?=\s*([0-9.e+\-]+)',
    "Aex/A_base":    r'(?:A_base|Aex)\s*:?=\s*([0-9.e+\-]+)',
    "EnableDemag":   r'EnableDemag\s*=\s*(\w+)',
    "GridSize":      r'SetGridSize\(([^)]+)\)',
    "CellSize":      r'SetCellSize\(([^)]+)\)',
    "PBC":           r'SetPBC\(([^)]+)\)',
    "run_time":      r'^\s*run\(([^)]+)\)',
    "autosave":      r'autosave\(m,\s*([^)]+)\)',
    "tableautosave": r'tableautosave\(([^)]+)\)',
    "LoadFile":      r'LoadFile\("([^"]+)"\)',
    "J2_coeff":      r'A_J2\s*:=\s*A_base\s*\*\s*\(([^)]+)\)',
    "J4_coeff":      r'A_J4\s*:=\s*A_base\s*\*\s*\(([^)]+)\)',
}


def extract_params(filepath):
    """Extract parameter values from a .mx3 file."""
    params = {}
    with open(filepath) as f:
        content = f.read()
    for name, pattern in PARAM_PATTERNS.items():
        match = re.search(pattern, content, re.MULTILINE)
        params[name] = match.group(1).strip() if match else "<not set>"
    return params


def audit_directory(dirpath):
    """Audit all .mx3 files in directory for parameter consistency."""
    mx3_files = sorted(f for f in os.listdir(dirpath) if f.endswith('.mx3'))
    if not mx3_files:
        print(f"No .mx3 files found in {dirpath}")
        return True

    print(f"Auditing {len(mx3_files)} mx3 files in: {dirpath}\n")

    # Extract params from all files
    all_params = {}
    for fname in mx3_files:
        fpath = os.path.join(dirpath, fname)
        all_params[fname] = extract_params(fpath)

    # Find which parameters vary
    varying = {}
    constant = {}
    for param_name in PARAM_PATTERNS:
        values = {fname: p[param_name] for fname, p in all_params.items()}
        unique_values = set(values.values())
        if len(unique_values) == 1:
            constant[param_name] = list(unique_values)[0]
        else:
            varying[param_name] = values

    # Report
    print("--- Constant parameters (identical across all files) ---")
    for name, val in constant.items():
        print(f"  {name:20s} = {val}")

    print(f"\n--- Varying parameters ({len(varying)} found) ---")
    if not varying:
        print("  (none — all parameters identical)")
    else:
        for name, file_vals in varying.items():
            print(f"\n  ** {name} **")
            for fname, val in file_vals.items():
                print(f"     {fname:40s} = {val}")

    # Verdict
    # Expected: exactly 1 varying parameter (the sweep variable)
    # Warning: 2+ varying parameters may indicate a control violation
    n_vary = len(varying)
    print(f"\n{'='*60}")
    if n_vary == 0:
        print("RESULT: All files identical — is this a sweep?")
        return True
    elif n_vary == 1:
        sweep_var = list(varying.keys())[0]
        print(f"PASS: Only '{sweep_var}' varies — controlled experiment OK.")
        return True
    else:
        # Check if additional variance is just LoadFile (acceptable for
        # experiments where initial state matches sweep variable, e.g.
        # centered_stability_test uses different pre-equilibrated states)
        non_trivial = [k for k in varying if k != "LoadFile"]
        if len(non_trivial) == 1:
            print(f"PASS: '{non_trivial[0]}' is the sweep variable. "
                  f"LoadFile also varies (may be intentional, e.g. "
                  f"pre-equilibrated states).")
            return True
        else:
            print(f"FAIL: {n_vary} parameters vary — possible control violation!")
            print(f"  Varying: {', '.join(varying.keys())}")
            print(f"  Review each difference and confirm intentionality.")
            return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)

    target = sys.argv[1]
    if not os.path.isdir(target):
        print(f"Error: {target} is not a directory")
        sys.exit(2)

    ok = audit_directory(target)
    sys.exit(0 if ok else 1)
