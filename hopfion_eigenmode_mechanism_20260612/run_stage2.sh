#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MUMAX3="${MUMAX3:-/home/wujiale/go/bin/mumax3}"
export LD_LIBRARY_PATH="/home/wujiale/mumax3/mumax3.11.1_linux_cuda12.9/lib:/home/wujiale/.local/cuda-12.8/targets/x86_64-linux/lib:${LD_LIBRARY_PATH:-}"
mkdir -p "$ROOT/logs" "$ROOT/results"

source /mnt/d/Research/Hopfion/hopfion/bin/activate
export PYTHONDONTWRITEBYTECODE=1
python3 "$ROOT/analysis/generate_stage2.py"

if ! python3 - "$ROOT/results/stage2_generation_status.json" <<'PY'
import json
import sys
from pathlib import Path

status = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
raise SystemExit(0 if status.get("generated") else 1)
PY
then
    printf 'stage2 not generated because the stage1 gate did not pass\n'
    exit 0
fi

mapfile -t CASES < <(python3 - "$ROOT/results/stage2_simulation_manifest.csv" <<'PY'
import csv
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    for row in csv.DictReader(handle):
        print(f"{row['name']}\t{row['mx3']}")
PY
)

for entry in "${CASES[@]}"; do
    IFS=$'\t' read -r name relative_mx3 <<< "$entry"
    "$MUMAX3" -vet "$ROOT/$relative_mx3" > "$ROOT/logs/${name}.vet.log" 2>&1
done

status_file="$ROOT/results/stage2_run_status.tsv"
if [[ ! -f "$status_file" ]]; then
    printf 'name\tstatus\tstarted_at\tfinished_at\texit_code\n' > "$status_file"
fi

for entry in "${CASES[@]}"; do
    IFS=$'\t' read -r name relative_mx3 <<< "$entry"
    output_dir="$ROOT/mx3/${name}.out"
    if [[ -f "$output_dir/.complete" ]]; then
        continue
    fi
    started_at="$(date --iso-8601=seconds)"
    set +e
    "$MUMAX3" -o "$output_dir" "$ROOT/$relative_mx3" > "$ROOT/logs/${name}.log" 2>&1
    exit_code=$?
    set -e
    finished_at="$(date --iso-8601=seconds)"
    if [[ $exit_code -eq 0 ]]; then
        touch "$output_dir/.complete"
        status="complete"
    else
        status="failed"
    fi
    printf '%s\t%s\t%s\t%s\t%s\n' \
        "$name" "$status" "$started_at" "$finished_at" "$exit_code" >> "$status_file"
    if [[ $exit_code -ne 0 ]]; then
        exit "$exit_code"
    fi
done

python3 "$ROOT/analysis/analyze_stage2.py"
python3 "$ROOT/analysis/analyze_k_spectrum.py"
