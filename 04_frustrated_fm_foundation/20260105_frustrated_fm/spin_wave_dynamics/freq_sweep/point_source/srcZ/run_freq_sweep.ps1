# Point Source Frequency Sweep - srcZ_vibX
# Contrast with srcX: DefRegionCell(7,30,50,50) -> (7,50,50,30), z=-10nm source
# Run all 10 simulations sequentially (100-1000 GHz, B_amp=500)
# Usage: cd to this directory, then .\run_freq_sweep.ps1

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$Scripts = @(
    "ps_srcZ_f100GHz.mx3",
    "ps_srcZ_f200GHz.mx3",
    "ps_srcZ_f300GHz.mx3",
    "ps_srcZ_f400GHz.mx3",
    "ps_srcZ_f500GHz.mx3",
    "ps_srcZ_f600GHz.mx3",
    "ps_srcZ_f700GHz.mx3",
    "ps_srcZ_f800GHz.mx3",
    "ps_srcZ_f900GHz.mx3",
    "ps_srcZ_f1000GHz.mx3"
)

foreach ($script in $Scripts) {
    $outdir = $script -replace "\.mx3$", ".out"
    $ovfCount = 0
    if (Test-Path $outdir) {
        $ovfCount = (Get-ChildItem "$outdir\*.ovf" -ErrorAction SilentlyContinue).Count
    }
    if ($ovfCount -ge 51) {
        Write-Host "[SKIP] $script -- already complete ($ovfCount OVFs)" -ForegroundColor Yellow
        continue
    }
    Write-Host "[RUN]  $script -- $(Get-Date -Format 'HH:mm:ss')" -ForegroundColor Cyan
    mumax3 $script 2>&1 | Tee-Object -FilePath ($script -replace "\.mx3$", ".log")
    Write-Host "[DONE] $script -- $(Get-Date -Format 'HH:mm:ss')" -ForegroundColor Green
}

Write-Host "`nAll srcZ frequency sweep simulations finished at $(Get-Date)" -ForegroundColor Green
