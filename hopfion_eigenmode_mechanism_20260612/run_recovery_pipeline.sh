#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MUMAX3="${MUMAX3:-/home/wujiale/go/bin/mumax3}"
export LD_LIBRARY_PATH="/home/wujiale/mumax3/mumax3.11.1_linux_cuda12.9/lib:/home/wujiale/.local/cuda-12.8/targets/x86_64-linux/lib:${LD_LIBRARY_PATH:-}"
source /mnt/d/Research/Hopfion/hopfion/bin/activate
export PYTHONDONTWRITEBYTECODE=1

mkdir -p "$ROOT/logs" "$ROOT/results"
exec 9> "$ROOT/results/recovery_pipeline.lock"
if ! flock -n 9; then
    printf 'recovery pipeline is already running\n'
    exit 0
fi

python3 "$ROOT/analysis/generate_controls.py"
status_file="$ROOT/results/control_run_status.tsv"
if [[ ! -f "$status_file" ]]; then
    printf 'name\tstatus\tstarted_at\tfinished_at\texit_code\n' > "$status_file"
fi

run_case() {
    local name="$1"
    local mx3="$ROOT/mx3/${name}.mx3"
    local out="$ROOT/mx3/${name}.out"
    local log="$ROOT/logs/${name}.log"
    if [[ -f "$out/.complete" ]]; then
        return 0
    fi
    "$MUMAX3" -vet "$mx3" > "$ROOT/logs/${name}.vet.log" 2>&1
    local started_at
    started_at="$(date --iso-8601=seconds)"
    set +e
    "$MUMAX3" -o "$out" "$mx3" > "$log" 2>&1
    local exit_code=$?
    set -e
    local finished_at
    finished_at="$(date --iso-8601=seconds)"
    local status="failed"
    if [[ $exit_code -eq 0 ]]; then
        status="complete"
        touch "$out/.complete"
    fi
    printf '%s\t%s\t%s\t%s\t%s\n' \
        "$name" "$status" "$started_at" "$finished_at" "$exit_code" >> "$status_file"
    return "$exit_code"
}

json_true() {
    python3 - "$1" "$2" <<'PY'
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
raise SystemExit(0 if payload.get(sys.argv[2]) is True else 1)
PY
}

run_case control_quench_Bz_0mT_05ns
python3 "$ROOT/analysis/analyze_controls.py" quench > "$ROOT/logs/control_quench_analysis.log" 2>&1
if ! json_true "$ROOT/results/control_quench_audit.json" quench_dominated; then
    printf 'quench control did not support the contamination hypothesis; stopping for review\n'
    exit 0
fi

run_case equilibrate_open_boundary
python3 - "$ROOT" <<'PY'
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
sys.path.insert(0, str(root.parent / "20260105_frustrated_fm"))
from compute_hopf_index import compute_hopf_index

initial = Path("/mnt/d/Research/Hopfion/20260105_frustrated_fm/centered_stability_test/stability_Ku10k.out/m000020.ovf")
final = root / "mx3" / "equilibrate_open_boundary.out" / "equilibrated_open_boundary.ovf"
initial_qh = float(compute_hopf_index(initial, pbc=False, verbose=False))
final_qh = float(compute_hopf_index(final, pbc=False, verbose=False))
relative_change = abs(final_qh - initial_qh) / max(abs(initial_qh), 1e-12)
payload = {
    "initial_qh_numeric": initial_qh,
    "final_qh_numeric": final_qh,
    "relative_change": relative_change,
    "passed": relative_change <= 0.15,
    "warning": "numeric Hopf integral is used as a relative preservation check, not forced to exactly one",
}
(root / "results" / "equilibrated_topology_check.json").write_text(
    json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
PY
if ! json_true "$ROOT/results/equilibrated_topology_check.json" passed; then
    printf 'equilibration did not preserve the numerical Hopf index; stopping\n'
    exit 0
fi

run_case clean_Bz_0mT_05ns
run_case clean_Bz_1mT_05ns
run_case clean_Bz_2mT_05ns
run_case clean_Bz_5mT_05ns
python3 "$ROOT/analysis/analyze_controls.py" clean > "$ROOT/logs/clean_linearity_analysis.log" 2>&1
if ! json_true "$ROOT/results/clean_linearity_gate.json" passed; then
    printf 'clean linearity gate failed; expensive validation is not launched\n'
    exit 0
fi

python3 - "$ROOT" <<'PY'
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
sys.path.insert(0, str(root.parent / "scripts"))
from resonance_analysis import generate_circular_burst_mx3

gate = json.loads((root / "results" / "clean_linearity_gate.json").read_text(encoding="utf-8"))
frequency = float(gate["candidate_frequency_ghz"])
initial = root / "mx3" / "equilibrate_open_boundary.out" / "equilibrated_open_boundary.ovf"
for handedness, label in ((1, "plus"), (-1, "minus")):
    generate_circular_burst_mx3(
        root / "mx3" / f"clean_circular_{label}_2mT.mx3",
        handedness=handedness,
        frequency_ghz=frequency,
        b0_t=0.002,
        run_ns=0.5,
        init_ovf=str(initial),
    )
PY

run_case clean_Bz_0mT_10ns
run_case clean_Bz_1mT_10ns
run_case clean_spatial_Bz_0mT
run_case clean_spatial_Bz_5mT
run_case clean_spatial_uniform_Bz_5mT
run_case clean_circular_plus_2mT
run_case clean_circular_minus_2mT
python3 "$ROOT/analysis/analyze_clean_validation.py" > "$ROOT/logs/clean_validation_analysis.log" 2>&1
if json_true "$ROOT/results/stage1_gate.json" passed; then
    bash "$ROOT/run_stage2.sh"
else
    printf 'clean spatial gate failed; CW and k-spectrum stage is not launched\n'
fi
