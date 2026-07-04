# srcZ_vibX Freq Sweep - Device B (Windows PowerShell)
# Usage: Right-click -> Run with PowerShell, or: powershell -ExecutionPolicy Bypass -File run_all.ps1

$LOG = "run_all.log"
$timestamp = { Get-Date -Format "yyyy-MM-dd HH:mm:ss" }

# Copy initial state if not present
if (-not (Test-Path "initial_state.ovf")) {
    Write-Host "ERROR: initial_state.ovf not found! Copy it to this directory first." -ForegroundColor Red
    Write-Host "Source: centered_stability_test/stability_Ku10k.out/m000020.ovf"
    pause
    exit 1
}

$msg = "[$(& $timestamp)] === srcZ_vibX Freq Sweep Device B ==="
Write-Host $msg
Add-Content $LOG $msg

$msg = "[$(& $timestamp)] >>> f=100GHz start"
Write-Host $msg -ForegroundColor Cyan
Add-Content $LOG $msg
mumax3 sw_srcZ_f100GHz.mx3 2>&1 | Tee-Object -Variable output
$msg = "[$(& $timestamp)] <<< f=100GHz done (exit=$LASTEXITCODE)"
Write-Host $msg -ForegroundColor Green
Add-Content $LOG $msg
Add-Content $LOG ($output | Select-Object -Last 5 | Out-String)

$msg = "[$(& $timestamp)] >>> f=300GHz start"
Write-Host $msg -ForegroundColor Cyan
Add-Content $LOG $msg
mumax3 sw_srcZ_f300GHz.mx3 2>&1 | Tee-Object -Variable output
$msg = "[$(& $timestamp)] <<< f=300GHz done (exit=$LASTEXITCODE)"
Write-Host $msg -ForegroundColor Green
Add-Content $LOG $msg
Add-Content $LOG ($output | Select-Object -Last 5 | Out-String)

$msg = "[$(& $timestamp)] >>> f=400GHz start"
Write-Host $msg -ForegroundColor Cyan
Add-Content $LOG $msg
mumax3 sw_srcZ_f400GHz.mx3 2>&1 | Tee-Object -Variable output
$msg = "[$(& $timestamp)] <<< f=400GHz done (exit=$LASTEXITCODE)"
Write-Host $msg -ForegroundColor Green
Add-Content $LOG $msg
Add-Content $LOG ($output | Select-Object -Last 5 | Out-String)

$msg = "[$(& $timestamp)] >>> f=500GHz start"
Write-Host $msg -ForegroundColor Cyan
Add-Content $LOG $msg
mumax3 sw_srcZ_f500GHz.mx3 2>&1 | Tee-Object -Variable output
$msg = "[$(& $timestamp)] <<< f=500GHz done (exit=$LASTEXITCODE)"
Write-Host $msg -ForegroundColor Green
Add-Content $LOG $msg
Add-Content $LOG ($output | Select-Object -Last 5 | Out-String)

$msg = "[$(& $timestamp)] >>> f=600GHz start"
Write-Host $msg -ForegroundColor Cyan
Add-Content $LOG $msg
mumax3 sw_srcZ_f600GHz.mx3 2>&1 | Tee-Object -Variable output
$msg = "[$(& $timestamp)] <<< f=600GHz done (exit=$LASTEXITCODE)"
Write-Host $msg -ForegroundColor Green
Add-Content $LOG $msg
Add-Content $LOG ($output | Select-Object -Last 5 | Out-String)

$msg = "[$(& $timestamp)] >>> f=700GHz start"
Write-Host $msg -ForegroundColor Cyan
Add-Content $LOG $msg
mumax3 sw_srcZ_f700GHz.mx3 2>&1 | Tee-Object -Variable output
$msg = "[$(& $timestamp)] <<< f=700GHz done (exit=$LASTEXITCODE)"
Write-Host $msg -ForegroundColor Green
Add-Content $LOG $msg
Add-Content $LOG ($output | Select-Object -Last 5 | Out-String)

$msg = "[$(& $timestamp)] >>> f=800GHz start"
Write-Host $msg -ForegroundColor Cyan
Add-Content $LOG $msg
mumax3 sw_srcZ_f800GHz.mx3 2>&1 | Tee-Object -Variable output
$msg = "[$(& $timestamp)] <<< f=800GHz done (exit=$LASTEXITCODE)"
Write-Host $msg -ForegroundColor Green
Add-Content $LOG $msg
Add-Content $LOG ($output | Select-Object -Last 5 | Out-String)

$msg = "[$(& $timestamp)] >>> f=900GHz start"
Write-Host $msg -ForegroundColor Cyan
Add-Content $LOG $msg
mumax3 sw_srcZ_f900GHz.mx3 2>&1 | Tee-Object -Variable output
$msg = "[$(& $timestamp)] <<< f=900GHz done (exit=$LASTEXITCODE)"
Write-Host $msg -ForegroundColor Green
Add-Content $LOG $msg
Add-Content $LOG ($output | Select-Object -Last 5 | Out-String)

$msg = "[$(& $timestamp)] >>> f=1000GHz start"
Write-Host $msg -ForegroundColor Cyan
Add-Content $LOG $msg
mumax3 sw_srcZ_f1000GHz.mx3 2>&1 | Tee-Object -Variable output
$msg = "[$(& $timestamp)] <<< f=1000GHz done (exit=$LASTEXITCODE)"
Write-Host $msg -ForegroundColor Green
Add-Content $LOG $msg
Add-Content $LOG ($output | Select-Object -Last 5 | Out-String)

$msg = "[$(& $timestamp)] === ALL COMPLETE ==="
Write-Host $msg -ForegroundColor Yellow
Add-Content $LOG $msg

Write-Host ""
Write-Host "Transfer back: all sw_srcZ_f*GHz.out/ directories" -ForegroundColor Yellow
pause
