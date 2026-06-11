param(
    [string]$PythonExe = "python"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$toolRoot = Join-Path $repoRoot "tools/eeg-tools"
$entryFile = Join-Path $toolRoot "eeg_tools/bridge_entry.py"
$buildDir = Join-Path $toolRoot "build/eeg-bridge"
$bridgeAppData = Join-Path $toolRoot "bridge-runtime/app"

Push-Location $repoRoot
try {
    & $PythonExe -m PyInstaller `
        --noconfirm `
        --clean `
        --onefile `
        --name eeg-bridge `
        --distpath $repoRoot `
        --workpath $buildDir `
        --specpath $toolRoot `
        --paths $toolRoot `
        --collect-all bleak `
        --collect-all redis `
        --add-data "$bridgeAppData;tools/eeg-tools/bridge-runtime/app" `
        $entryFile
}
finally {
    Pop-Location
}
