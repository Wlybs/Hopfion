# Point Source Frequency Sweep - srcX_vibX
# Run all 10 simulations sequentially (100-1000 GHz, B_amp=500)
# Usage: cd to this directory, then .\run_freq_sweep.ps1

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$Scripts = @(
    "ps_srcX_f100GHz.mx3",
    "ps_srcX_f200GHz.mx3",
    "ps_srcX_f300GHz.mx3",
    "ps_srcX_f400GHz.mx3",
    "ps_srcX_f500GHz.mx3",
    "ps_srcX_f600GHz.mx3",
    "ps_srcX_f700GHz.mx3",
    "ps_srcX_f800GHz.mx3",
    "ps_srcX_f900GHz.mx3",
    "ps_srcX_f1000GHz.mx3"
)

foreach ($script in $Scripts) {
    $outdir = $script -replace "\.mx3$", ".out"
    $ovfCount = 0
    if (Test-Path $outdir) {
        $ovfCount = (Get-ChildItem "$outdir\*.ovf" -ErrorAction SilentlyContinue).Count
    }
    if ($ovfCount -ge 51) {
        Write-Host "[SKIP] $script — already complete ($ovfCount OVFs)" -ForegroundColor Yellow
        continue
    }
    Write-Host "[RUN]  $script — $(Get-Date -Format 'HH:mm:ss')" -ForegroundColor Cyan
    mumax3 $script 2>&1 | Tee-Object -FilePath ($script -replace "\.mx3$", ".log")
    Write-Host "[DONE] $script — $(Get-Date -Format 'HH:mm:ss')" -ForegroundColor Green
}

Write-Host "`nAll frequency sweep simulations finished at $(Get-Date)" -ForegroundColor Green
