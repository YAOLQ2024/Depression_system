param(
    [ValidateSet("bridge", "replay")]
    [string]$Command = "bridge",
    [ValidateSet("raw", "simulate")]
    [string]$Mode,
    [string]$ReplayFile,
    [double]$Speed,
    [double]$DurationSeconds,
    [int]$MaxRecords,
    [switch]$Loop,
    [switch]$PrintConfig
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$toolRoot = Join-Path $repoRoot "tools/eeg-tools"
$existingPythonPath = [Environment]::GetEnvironmentVariable("PYTHONPATH", "Process")

if ([string]::IsNullOrWhiteSpace($existingPythonPath)) {
    [Environment]::SetEnvironmentVariable("PYTHONPATH", $toolRoot, "Process")
} else {
    [Environment]::SetEnvironmentVariable("PYTHONPATH", "$toolRoot;$existingPythonPath", "Process")
}
[Environment]::SetEnvironmentVariable("MCS_EEG_TOOLS_ROOT", $repoRoot, "Process")

Set-Location $toolRoot

$pythonArgs = @("-m", "eeg_tools.main", $Command)
if ($Command -eq "replay") {
    if ([string]::IsNullOrWhiteSpace($Mode)) {
        throw "Replay mode is required. Use -Mode raw or -Mode simulate."
    }
    $pythonArgs += $Mode
}
if ($PrintConfig) {
    $pythonArgs += "--print-config"
}
if (-not [string]::IsNullOrWhiteSpace($ReplayFile)) {
    $pythonArgs += @("--file", $ReplayFile)
}
if ($PSBoundParameters.ContainsKey("Speed")) {
    $pythonArgs += @("--speed", [string]$Speed)
}
if ($PSBoundParameters.ContainsKey("DurationSeconds")) {
    $pythonArgs += @("--duration-seconds", [string]$DurationSeconds)
}
if ($PSBoundParameters.ContainsKey("MaxRecords")) {
    $pythonArgs += @("--max-records", [string]$MaxRecords)
}
if ($Loop) {
    $pythonArgs += "--loop"
}

python @pythonArgs
