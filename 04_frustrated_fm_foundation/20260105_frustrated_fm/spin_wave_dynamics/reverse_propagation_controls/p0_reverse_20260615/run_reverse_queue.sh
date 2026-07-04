#!/usr/bin/env bash
set -uo pipefail

WORKDIR="/home/wujiale/hopfion_reverse_propagation_20260615"
MUMAX3="/home/wujiale/go/bin/mumax3"
CACHE_DIR="/home/wujiale/.cache/mumax3"

export PATH="/home/wujiale/go/bin:${PATH}"
export LD_LIBRARY_PATH="/home/wujiale/.local/cuda-12.8/lib64:${LD_LIBRARY_PATH:-}"
export TMPDIR="/home/wujiale/tmp"
export CUDA_CACHE_PATH="/home/wujiale/.cache/nv"

mkdir -p "$CACHE_DIR" "$TMPDIR" "$CUDA_CACHE_PATH"
cd "$WORKDIR" || exit 2

cases=(
  "reverse_srcX_200GHz.mx3"
  "reverse_srcZ_100GHz.mx3"
  "reverse_srcZ_1100GHz.mx3"
)

queue_log="$WORKDIR/queue.log"
printf '[%s] queue start pid=%s\n' "$(date --iso-8601=seconds)" "$$" >> "$queue_log"

for input in "${cases[@]}"; do
  stem="${input%.mx3}"
  output_dir="$WORKDIR/${stem}.out"
  case_log="$WORKDIR/${stem}.log"

  if [[ -e "$output_dir" ]]; then
    printf '[%s] refusing to overwrite existing %s\n' "$(date --iso-8601=seconds)" "$output_dir" >> "$queue_log"
    exit 3
  fi

  printf '[%s] START %s\n' "$(date --iso-8601=seconds)" "$input" >> "$queue_log"
  if "$MUMAX3" -gpu=0 -cache="$CACHE_DIR" "$input" >> "$case_log" 2>&1; then
    printf '[%s] DONE  %s\n' "$(date --iso-8601=seconds)" "$input" >> "$queue_log"
  else
    rc=$?
    printf '[%s] FAIL  %s rc=%s\n' "$(date --iso-8601=seconds)" "$input" "$rc" >> "$queue_log"
    exit "$rc"
  fi
done

printf '[%s] queue complete\n' "$(date --iso-8601=seconds)" >> "$queue_log"
touch "$WORKDIR/QUEUE_COMPLETE"
