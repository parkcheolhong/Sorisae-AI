param(
    [string]$TaskPrefix = "CodeAI",
    [ValidateSet("Auto", "System", "User")]
    [string]$Scope = "Auto"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$target = Join-Path $PSScriptRoot "scripts\install_ops_automation_tasks.ps1"
if (-not (Test-Path $target)) {
    throw "Target script not found: $target"
}

& $target -TaskPrefix $TaskPrefix -Scope $Scope
