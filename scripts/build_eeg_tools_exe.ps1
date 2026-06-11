param(
    [string]$PythonExe = "python"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$toolRoot = Join-Path $repoRoot "tools/eeg-tools"
$entryFile = Join-Path $toolRoot "eeg_tools/main.py"
$distDir = Join-Path $toolRoot "dist"
$buildDir = Join-Path $toolRoot "build"
$bridgeAppData = Join-Path $toolRoot "bridge-runtime/app"
$replayAppData = Join-Path $toolRoot "replay-runtime/app"

Push-Location $repoRoot
try {
    & $PythonExe -m PyInstaller `
        --noconfirm `
        --clean `
        --onefile `
        --name eeg-tools `
        --distpath $distDir `
        --workpath $buildDir `
        --specpath $toolRoot `
        --paths $toolRoot `
        --collect-all bleak `
        --collect-all redis `
        --add-data "$bridgeAppData;tools/eeg-tools/bridge-runtime/app" `
        --add-data "$replayAppData;tools/eeg-tools/replay-runtime/app" `
        $entryFile
}
finally {
    Pop-Location
}
