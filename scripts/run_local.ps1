param(
  [switch]$Reload
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location ..

if ($Reload) {
  python -m uvicorn app:app --host 127.0.0.1 --port 8800 --reload
} else {
  python app.py
}
