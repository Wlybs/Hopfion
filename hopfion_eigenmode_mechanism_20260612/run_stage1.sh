#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MUMAX3="/home/wujiale/go/bin/mumax3"
QUIET_RUNNER="$ROOT/../scripts/run_mumax_with_quiet_hours.sh"
export LD_LIBRARY_PATH="/home/wujiale/mumax3/mumax3.11.1_linux_cuda12.9/lib:/home/wujiale/.local/cuda-12.8/targets/x86_64-linux/lib:${LD_LIBRARY_PATH:-}"

mkdir -p "$ROOT/logs" "$ROOT/results"
STATUS="$ROOT/results/stage1_run_status.tsv"
if [[ ! -f "$STATUS" ]]; then
    printf 'name\tstatus\tstarted_at\tfinished_at\texit_code\n' > "$STATUS"
fi

run_case() {
    local name="$1"
    local mx3="$ROOT/mx3/${name}.mx3"
    local out="$ROOT/mx3/${name}.out"
    local log="$ROOT/logs/${name}.log"
    local done_marker="$out/.complete"

    if [[ -f "$done_marker" ]]; then
        printf '%s\tskipped_complete\t%s\t%s\t0\n' \
            "$name" "$(date --iso-8601=seconds)" "$(date --iso-8601=seconds)" >> "$STATUS"
        return
    fi

    local started
    started="$(date --iso-8601=seconds)"
    set +e
    bash "$QUIET_RUNNER" --mx3 "$mx3" --table "$out/table.txt" -- \
        "$MUMAX3" -o "$out" "$mx3" >> "$log" 2>&1
    local code=$?
    set -e
    local finished
    finished="$(date --iso-8601=seconds)"
    printf '%s\t%s\t%s\t%s\t%s\n' \
        "$name" "$([[ $code -eq 0 ]] && printf completed || printf failed)" \
        "$started" "$finished" "$code" >> "$STATUS"
    if [[ $code -ne 0 ]]; then
        return "$code"
    fi
    touch "$done_marker"
}

run_case linear_Bz_1mT_05ns
run_case linear_Bz_2mT_05ns
run_case linewidth_Bz_1mT_10ns
run_case circular_plus_2mT
run_case circular_minus_2mT
run_case spatial_hopfion_Bz
run_case spatial_uniform_Bz
