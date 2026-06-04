param(
    [int]$Port = 8017,
    [switch]$SkipAlembic,
    [switch]$SkipAutoFetch
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Set-DefaultEnvValue {
    param(
        [string]$Name,
        [string]$Value
    )

    $current = [Environment]::GetEnvironmentVariable($Name, "Process")
    if ([string]::IsNullOrWhiteSpace($current)) {
        [Environment]::SetEnvironmentVariable($Name, $Value, "Process")
    }
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$serviceRoot = Join-Path $repoRoot "services/multimodal-service"
$runtimeAssetsDir = Join-Path $serviceRoot "runtime-assets"
$dolphinModelDir = Join-Path $runtimeAssetsDir "asr/base.cn.streaming"
$workflowPythonPath = [Environment]::GetEnvironmentVariable("PYTHONPATH", "Process")

if ([string]::IsNullOrWhiteSpace($workflowPythonPath)) {
    [Environment]::SetEnvironmentVariable("PYTHONPATH", $serviceRoot, "Process")
} else {
    [Environment]::SetEnvironmentVariable(
        "PYTHONPATH",
        "$serviceRoot;$workflowPythonPath",
        "Process"
    )
}

Set-DefaultEnvValue -Name "DATABASE_URL" -Value "postgresql://mcs:mcs@127.0.0.1:5432/mcs"
Set-DefaultEnvValue -Name "MINIO_ENDPOINT" -Value "http://127.0.0.1:9000"
Set-DefaultEnvValue -Name "MINIO_ACCESS_KEY" -Value "minioadmin"
Set-DefaultEnvValue -Name "MINIO_SECRET_KEY" -Value "minioadmin"
Set-DefaultEnvValue -Name "MINIO_SECURE" -Value "false"
Set-DefaultEnvValue -Name "MULTIMODAL_BUCKET" -Value "mcs-multimodal"
Set-DefaultEnvValue -Name "REDIS_ENABLED" -Value "true"
Set-DefaultEnvValue -Name "REDIS_URL" -Value "redis://127.0.0.1:6379/0"
Set-DefaultEnvValue -Name "REDIS_KEY_PREFIX" -Value "mcs:multimodal"
Set-DefaultEnvValue -Name "RUNTIME_ASSETS_DIR" -Value $runtimeAssetsDir
Set-DefaultEnvValue -Name "DOLPHIN_MODEL_NAME" -Value "base.cn.streaming"
Set-DefaultEnvValue -Name "DOLPHIN_MODEL_REPO_ID" -Value "DataoceanAI1/dolphin-cn-dialect-base-streaming"
Set-DefaultEnvValue -Name "DOLPHIN_MODEL_DIR" -Value $dolphinModelDir
Set-DefaultEnvValue -Name "AUTO_FETCH_DOLPHIN_ASR" -Value "true"
Set-DefaultEnvValue -Name "ASR_DEVICE" -Value "auto"
Set-DefaultEnvValue -Name "ASR_SYNC_TIMEOUT_MS" -Value "15000"
Set-DefaultEnvValue -Name "ASR_PREVIEW_MAX_DURATION_MS" -Value "10000"
Set-DefaultEnvValue -Name "EEG_ENABLED" -Value "true"
Set-DefaultEnvValue -Name "EEG_PROVIDER" -Value "ble"
Set-DefaultEnvValue -Name "EEG_DEVICE_NAME_HINT" -Value "EEG"
Set-DefaultEnvValue -Name "EEG_NOTIFY_CHAR_UUID" -Value "6e400003-b5a3-f393-e0a9-e50e24dcca9e"
Set-DefaultEnvValue -Name "EEG_CHANNEL_NAMES" -Value "T7,T8,Fpz"
Set-DefaultEnvValue -Name "EEG_SAMPLING_RATE" -Value "500"
Set-DefaultEnvValue -Name "EEG_PREVIEW_SECONDS" -Value "4"
Set-DefaultEnvValue -Name "EEG_WINDOW_SECONDS" -Value "60"
Set-DefaultEnvValue -Name "EEG_SCAN_SECONDS" -Value "5"
Set-DefaultEnvValue -Name "EEG_RECONNECT_DELAY_SECONDS" -Value "5"
Set-DefaultEnvValue -Name "EEG_MODEL_PATH" -Value (Join-Path $runtimeAssetsDir "eeg/model_combined_3class.pkl")

Set-Location $serviceRoot

if (-not $SkipAutoFetch) {
    $hasDolphinAssets = $false
    if (Test-Path $dolphinModelDir) {
        $assetFiles = Get-ChildItem -Path $dolphinModelDir -File -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -notin @("README.md", ".gitkeep") }
        $hasDolphinAssets = $assetFiles.Count -gt 0
    }

    if (-not $hasDolphinAssets) {
        Write-Host "[INFO] Dolphin ASR assets are missing; downloading runtime assets..."
        python ./scripts/fetch_dolphin_model.py
    }
}

if (-not $SkipAlembic) {
    python -m alembic upgrade head
}

python -m uvicorn app.main:app --host 0.0.0.0 --port $Port
