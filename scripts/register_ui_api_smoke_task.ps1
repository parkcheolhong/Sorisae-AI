Param(
    [string]$TaskName = "SorisaeUiApiSmokeEvery5Min",
    [string]$ScriptPath = "",
    [string]$WorkingDirectory = "",
    [switch]$CollectAdbLog,
    [switch]$Disable,
    [switch]$Remove
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($ScriptPath)) {
    $ScriptPath = Join-Path $PSScriptRoot "run_ui_api_failure_split_smoke.ps1"
}

if (-not (Test-Path -LiteralPath $ScriptPath)) {
    throw "Smoke script not found: $ScriptPath"
}

if ([string]::IsNullOrWhiteSpace($WorkingDirectory)) {
    $WorkingDirectory = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

if ($Remove) {
    try {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction Stop
        Write-Host "Removed scheduled task: $TaskName"
        exit 0
    }
    catch {
        Write-Host "Task not removed (not found or no permission): $TaskName"
        exit 0
    }
}

$psArgs = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", ('"' + $ScriptPath + '"')
)
if ($CollectAdbLog) {
    $psArgs += "-CollectAdbLog"
}
$argLine = $psArgs -join " "

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argLine -WorkingDirectory $WorkingDirectory

$startAt = (Get-Date).AddMinutes(1)
$trigger = New-ScheduledTaskTrigger -Once -At $startAt -RepetitionInterval (New-TimeSpan -Minutes 5) -RepetitionDuration (New-TimeSpan -Days 3650)

$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 15)

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Description "Run Sorisae UI/API split smoke every 5 minutes" -Force | Out-Null

if ($Disable) {
    Disable-ScheduledTask -TaskName $TaskName | Out-Null
}

Write-Host "TaskName=$TaskName"
Write-Host "ScriptPath=$ScriptPath"
Write-Host "WorkingDirectory=$WorkingDirectory"
Write-Host "Enabled=$([bool](-not $Disable))"
Write-Host "Interval=5 minutes"
