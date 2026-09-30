# Windows fallback for `make` (this machine has no GNU make).
# Usage:  powershell -ExecutionPolicy Bypass -File setup.ps1 setup|test|demo|run|browse|review|learn|eval
param(
    [Parameter(Position = 0)][string]$Task = "setup",
    [string]$V = ""
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Ensure-Venv {
    if (-not (Test-Path ".venv")) { python -m venv .venv }
    & ".venv\Scripts\python.exe" -m pip install -q -r requirements.txt
    if (-not (Test-Path ".env")) { Copy-Item .env.example .env }
}

switch ($Task) {
    "setup"  { Ensure-Venv; Write-Host "setup done" }
    "test"   { Ensure-Venv; & ".venv\Scripts\python.exe" -m pytest tests/ -q }
    "demo"   { Ensure-Venv; & ".venv\Scripts\python.exe" -m app demo }
    "run"    { Ensure-Venv; & ".venv\Scripts\python.exe" -m app run }
    "browse" { Ensure-Venv; & ".venv\Scripts\python.exe" -m app browse }
    "review" { Ensure-Venv; & ".venv\Scripts\python.exe" -m app review }
    "learn"  { Ensure-Venv; & ".venv\Scripts\python.exe" -m app learn }
    "eval"   { Ensure-Venv; & ".venv\Scripts\python.exe" -m app eval }
    "rules"  { Ensure-Venv; & ".venv\Scripts\python.exe" -m app rules rollback $V }
    default  { Write-Host "unknown task: $Task (use setup|test|demo|run|browse|review|learn|eval|rules)" }
}
