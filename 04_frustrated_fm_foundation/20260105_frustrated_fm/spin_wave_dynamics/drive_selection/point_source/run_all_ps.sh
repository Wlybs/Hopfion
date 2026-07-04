#!/bin/bash
# Run all point-source simulations sequentially (single GPU)
# ps_srcX_vibX already done (symlinked from point_source_excitation)

cd "$(dirname "$0")"

SCRIPTS=(
    ps_srcX_vibZ.mx3
    ps_srcY_vibX.mx3
    ps_srcY_vibZ.mx3
    ps_srcZ_vibX.mx3
    ps_srcZ_vibZ.mx3
)

for script in "${SCRIPTS[@]}"; do
    outdir="${script%.mx3}.out"
    if [ -d "$outdir" ] && [ "$(find "$outdir" -name '*.ovf' | wc -l)" -ge 11 ]; then
        echo "[SKIP] $script — already complete ($outdir)"
        continue
    fi
    echo "[RUN] $script — $(date)"
    mumax3 "$script" > "${script%.mx3}.log" 2>&1
    echo "[DONE] $script — $(date)"
done

echo "All point-source simulations finished at $(date)"
