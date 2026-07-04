# vibY Point Source — Run all 36 simulations sequentially
# Usage: cd to this folder, then: .\run_all.ps1

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

$mx3Files = Get-ChildItem -Filter "ps_*.mx3" | Sort-Object Name
$total = $mx3Files.Count
$i = 0

Write-Host "=== vibY Point Source: $total simulations ===" -ForegroundColor Cyan
$startTime = Get-Date

foreach ($f in $mx3Files) {
    $i++
    $outDir = $f.BaseName + ".out"
    if (Test-Path $outDir) {
        $ovfCount = (Get-ChildItem "$outDir\m*.ovf" -ErrorAction SilentlyContinue).Count
        if ($ovfCount -ge 200) {
            Write-Host "[$i/$total] SKIP (already done): $($f.Name)" -ForegroundColor Yellow
            continue
        }
    }
    Write-Host "[$i/$total] Running: $($f.Name) ..." -ForegroundColor Green
    & mumax3 $f.Name
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: $($f.Name) failed with exit code $LASTEXITCODE" -ForegroundColor Red
    }
}

$elapsed = (Get-Date) - $startTime
Write-Host "`n=== All done! Elapsed: $($elapsed.ToString('hh\:mm\:ss')) ===" -ForegroundColor Cyan
