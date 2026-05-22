param(
  [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$multimodalRoot = Join-Path $repoRoot "services\multimodal-service"
$consultationRoot = Join-Path $repoRoot "services\consultation-service"

function Invoke-FaceTestSuite {
  param(
    [string]$ServicePythonPath,
    [string[]]$TestFiles
  )

  $env:PYTHONPATH = $ServicePythonPath
  & $PythonExe -m pytest @TestFiles -q
  if ($LASTEXITCODE -ne 0) {
    throw "pytest failed for $ServicePythonPath"
  }
}

Write-Host "[1/3] multimodal route smoke tests"
Invoke-FaceTestSuite `
  -ServicePythonPath $multimodalRoot `
  -TestFiles @(
    (Join-Path $multimodalRoot "tests\test_multimodal_routes.py")
  )

Write-Host "[2/3] multimodal face service tests"
Invoke-FaceTestSuite `
  -ServicePythonPath $multimodalRoot `
  -TestFiles @(
    (Join-Path $multimodalRoot "tests\test_multimodal_face_service.py")
  )

Write-Host "[3/3] consultation face cache tests"
Invoke-FaceTestSuite `
  -ServicePythonPath $consultationRoot `
  -TestFiles @(
    (Join-Path $consultationRoot "tests\test_consultation_face_capture_service.py")
  )

Write-Host "All face modality checks passed."
