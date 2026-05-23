param(
    [switch]$InstallAdvancedAI,
    [switch]$SkipRun,
    [switch]$SkipBrokerStart
)

$target = Join-Path $PSScriptRoot "tmp\external_migrations\upstream_sources\run_all_shinsegye.py-main-20260505\start_original_sorisae.ps1"

if (-not (Test-Path $target)) {
    Write-Error "Launcher script not found: $target"
    exit 1
}

$invokeArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $target)
if ($InstallAdvancedAI) { $invokeArgs += "-InstallAdvancedAI" }
if ($SkipRun) { $invokeArgs += "-SkipRun" }
if ($SkipBrokerStart) { $invokeArgs += "-SkipBrokerStart" }

powershell @invokeArgs
