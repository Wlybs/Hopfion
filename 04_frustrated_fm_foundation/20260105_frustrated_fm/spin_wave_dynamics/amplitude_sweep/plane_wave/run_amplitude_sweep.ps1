# ================================================================
# run_amplitude_sweep.ps1 - Amplitude sweep runner (Windows)
# Fixed: f = 440 GHz, srcX_vibX
# Sweep: B = 0.05, 0.1, 0.2, 0.5, 1.0, 2.0 T (6 points)
#
# Usage (open PowerShell in this folder):
#   .\run_amplitude_sweep.ps1 -InitOvf .\m000020.ovf
#   .\run_amplitude_sweep.ps1 -InitOvf .\m000020.ovf -MumaxPath C:\mumax3\mumax3.exe
# ================================================================

param(
    [Parameter(Mandatory=$true)]
    [string]$InitOvf,

    [string]$MumaxPath = "mumax3"
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$LogFile   = Join-Path $ScriptDir "amplitude_sweep.log"

# Use forward slashes for mumax3 cross-platform compatibility
$OvfPath = (Resolve-Path $InitOvf).Path.Replace('\', '/')

function Write-Log($msg) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$ts] $msg"
    Write-Host $line
    Add-Content -Path $LogFile -Value $line
}

# Validate inputs
if (-not (Test-Path $InitOvf)) {
    Write-Error "OVF file not found: $InitOvf"
    exit 1
}
if (-not (Get-Command $MumaxPath -ErrorAction SilentlyContinue)) {
    Write-Error "mumax3 not found: $MumaxPath`nUse -MumaxPath to specify full path, e.g.: C:\mumax3\mumax3.exe"
    exit 1
}

Write-Log "=== Amplitude Sweep: 440 GHz, srcX_vibX ==="
Write-Log "B = 0.05 / 0.1 / 0.2 / 0.5 / 1.0 / 2.0 T"
Write-Log "Init OVF : $OvfPath"
Write-Log "Mumax3   : $MumaxPath"

# Generate .mx3 file for given amplitude
function Gen-Mx3($bAmp, $label) {
    $outFile = Join-Path $ScriptDir "sw_B${label}T.mx3"

    $content = @"
// === Amplitude Sweep: B = $bAmp T, f = 440 GHz, srcX_vibX ===

CellSize := 0.5e-9
SetGridSize(100, 100, 100)
SetCellSize(CellSize, CellSize, CellSize)

DefRegion(1, XRange(22.5e-9, 25e-9))
DefRegion(2, XRange(-25e-9, -22.5e-9))
DefRegion(3, YRange(22.5e-9, 25e-9))
DefRegion(4, YRange(-25e-9, -22.5e-9))
DefRegion(5, ZRange(22.5e-9, 25e-9))
DefRegion(6, ZRange(-25e-9, -22.5e-9))

DefRegion(7, XRange(-10e-9, -9.5e-9))

EnableDemag = false
MaxErr = 1e-4

Ms     := 1.5e5
Msat    = Ms
A_base := 5e-12
Aex     = A_base
Dbulk   = 0
Dind    = 0
Ku1     = 1e4
anisU   = vector(0, 0, 1)

alpha = 0.001
alpha.setRegion(1, 100)
alpha.setRegion(2, 100)
alpha.setRegion(3, 100)
alpha.setRegion(4, 100)
alpha.setRegion(5, 100)
alpha.setRegion(6, 100)

A_J4     := A_base * (-0.082)
Coeff_J4 := A_J4 * 2.0 / (Ms * CellSize * CellSize)
sum_J4   := Add(Shifted(m, 2, 0, 0), Shifted(m, -2, 0, 0))
sum_J4    = Add(sum_J4, Shifted(m, 0, 2, 0))
sum_J4    = Add(sum_J4, Shifted(m, 0, -2, 0))
sum_J4    = Add(sum_J4, Shifted(m, 0, 0, 2))
sum_J4    = Add(sum_J4, Shifted(m, 0, 0, -2))
AddFieldTerm(Mul(Const(Coeff_J4), sum_J4))

A_J2     := A_base * (-0.164)
Coeff_J2 := A_J2 * 2.0 / (Ms * CellSize * CellSize)
sum_J2   := Add(Shifted(m, 1, 1, 0), Shifted(m, 1, -1, 0))
sum_J2    = Add(sum_J2, Shifted(m, -1, 1, 0))
sum_J2    = Add(sum_J2, Shifted(m, -1, -1, 0))
sum_J2    = Add(sum_J2, Shifted(m, 0, 1, 1))
sum_J2    = Add(sum_J2, Shifted(m, 0, 1, -1))
sum_J2    = Add(sum_J2, Shifted(m, 0, -1, 1))
sum_J2    = Add(sum_J2, Shifted(m, 0, -1, -1))
sum_J2    = Add(sum_J2, Shifted(m, 1, 0, 1))
sum_J2    = Add(sum_J2, Shifted(m, 1, 0, -1))
sum_J2    = Add(sum_J2, Shifted(m, -1, 0, 1))
sum_J2    = Add(sum_J2, Shifted(m, -1, 0, -1))
AddFieldTerm(Mul(Const(Coeff_J2), sum_J2))

m.LoadFile("$OvfPath")

f_sw := 440e9 * 2 * pi
B_ext.setRegion(7, Vector($bAmp*sin(f_sw*t), 0, 0))

autosave(m, 5e-11)
tableautosave(1e-12)
TableAdd(E_Total)

run(0.5e-9)
"@

    [System.IO.File]::WriteAllText($outFile, $content, [System.Text.UTF8Encoding]::new($false))
}

# Run all 6 amplitude points sequentially
$runs = @(
    @{ label="0p05"; amp="0.05" },
    @{ label="0p1";  amp="0.1"  },
    @{ label="0p2";  amp="0.2"  },
    @{ label="0p5";  amp="0.5"  },
    @{ label="1p0";  amp="1.0"  },
    @{ label="2p0";  amp="2.0"  }
)

foreach ($run in $runs) {
    $label = $run.label
    $amp   = $run.amp
    $mx3   = Join-Path $ScriptDir "sw_B${label}T.mx3"

    Gen-Mx3 $amp $label
    Write-Log ">>> B=${amp} T start"
    & $MumaxPath $mx3 2>&1 | Select-Object -Last 3 | ForEach-Object { Write-Log $_ }
    Write-Log "<<< B=${amp} T done (exit=$LASTEXITCODE)"
}

Write-Log "=== All done ==="
