param(
    [string]$TaskPrefix = "CodeAI",
    [ValidateSet("Auto", "System", "User")]
    [string]$Scope = "Auto"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Test-IsAdmin {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Invoke-SelfElevatedSystemInstall {
    if (-not $PSCommandPath) {
        throw "Cannot auto-elevate because PSCommandPath is unavailable. Run from a script file path."
    }

    $args = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", ('"{0}"' -f $PSCommandPath),
        "-TaskPrefix", ('"{0}"' -f $TaskPrefix),
        "-Scope", "System"
    )

    Write-Host "[ops-automation] requesting administrator elevation for System scope..."
    $proc = Start-Process -FilePath "pwsh.exe" -ArgumentList $args -Verb RunAs -PassThru -Wait
    if ($null -eq $proc) {
        throw "Failed to start elevated PowerShell process."
    }
    if ($proc.ExitCode -ne 0) {
        throw ("Elevated registration failed (exit code: {0})." -f $proc.ExitCode)
    }
}

$scriptRoot = (Resolve-Path $PSScriptRoot).Path
$watchdogScript = Join-Path $scriptRoot "ops_domain_watchdog.ps1"
$postbootScript = Join-Path $scriptRoot "postboot_recovery_verify.ps1"
$logDir = Join-Path $scriptRoot "logs"

$watchdogTaskName = "$TaskPrefix-DomainWatchdog"
$postbootTaskName = "$TaskPrefix-PostbootRecoveryVerify"
$postbootExternalTaskName = "$TaskPrefix-PostbootExternalVerify"

$watchdogCmd = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$watchdogScript`" -Continuous -AutoRemediate -EnforceComposeOnly -IntervalSec 60"
$postbootCmd = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$postbootScript`""
$postbootExternalCmd = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$postbootScript`" -RequireExternalDomains -RecoveryTimeoutSec 180"

function Register-SystemStartupTasks {
    schtasks /Create /TN $watchdogTaskName /TR $watchdogCmd /SC ONSTART /DELAY 0001:00 /RU SYSTEM /F | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw "failed to register task: $watchdogTaskName"
    }

    schtasks /Create /TN $postbootTaskName /TR $postbootCmd /SC ONSTART /DELAY 0000:30 /RU SYSTEM /F | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw "failed to register task: $postbootTaskName"
    }

    schtasks /Create /TN $postbootExternalTaskName /TR $postbootExternalCmd /SC HOURLY /MO 1 /ST 00:05 /RU SYSTEM /F | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw "failed to register task: $postbootExternalTaskName"
    }

    Write-Host "[ops-automation] installed scope=System trigger=ONSTART run-as=SYSTEM"
}

function Write-SystemTaskEvidence {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    $evidencePath = Join-Path $logDir "ops_task_registration_latest.txt"
    $timestamp = (Get-Date).ToString("s")

    $watchdogQuery = (schtasks /Query /TN $watchdogTaskName /V /FO LIST 2>&1) | Out-String
    $postbootQuery = (schtasks /Query /TN $postbootTaskName /V /FO LIST 2>&1) | Out-String
    $postbootExternalQuery = (schtasks /Query /TN $postbootExternalTaskName /V /FO LIST 2>&1) | Out-String

    $payload = @(
        "timestamp=$timestamp",
        "scope=System",
        "task=$watchdogTaskName",
        $watchdogQuery.TrimEnd(),
        "",
        "task=$postbootTaskName",
        $postbootQuery.TrimEnd(),
        "",
        "task=$postbootExternalTaskName",
        $postbootExternalQuery.TrimEnd()
    )

    Set-Content -Path $evidencePath -Value $payload -Encoding UTF8
    Write-Host "[ops-automation] evidence written: $evidencePath"
}

function Register-UserLogonTasks {
    try {
        schtasks /Create /TN $watchdogTaskName /TR $watchdogCmd /SC ONLOGON /DELAY 0000:30 /F | Out-Host
        if ($LASTEXITCODE -ne 0) {
            throw "failed to register task: $watchdogTaskName"
        }

        schtasks /Create /TN $postbootTaskName /TR $postbootCmd /SC ONLOGON /DELAY 0000:10 /F | Out-Host
        if ($LASTEXITCODE -ne 0) {
            throw "failed to register task: $postbootTaskName"
        }

        schtasks /Create /TN $postbootExternalTaskName /TR $postbootExternalCmd /SC HOURLY /MO 1 /ST 00:05 /F | Out-Host
        if ($LASTEXITCODE -ne 0) {
            throw "failed to register task: $postbootExternalTaskName"
        }

        Write-Host "[ops-automation] installed scope=User trigger=ONLOGON run-as=current-session-user"
        return
    }
    catch {
        Write-Warning ("scheduled-task user registration failed: {0}" -f $_.Exception.Message)
    }

    $startupDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Startup"
    New-Item -ItemType Directory -Path $startupDir -Force | Out-Null
    $bootstrapPath = Join-Path $startupDir "codeai_ops_bootstrap.cmd"

    $bootstrapLines = @(
        "@echo off",
        "setlocal",
        ('start "codeai-watchdog" /min powershell.exe -NoProfile -ExecutionPolicy Bypass -File "{0}" -Continuous -AutoRemediate -EnforceComposeOnly -IntervalSec 60' -f $watchdogScript),
        ('powershell.exe -NoProfile -ExecutionPolicy Bypass -File "{0}"' -f $postbootScript),
        ('powershell.exe -NoProfile -ExecutionPolicy Bypass -File "{0}" -RequireExternalDomains' -f $postbootScript),
        "endlocal"
    )
    Set-Content -Path $bootstrapPath -Value $bootstrapLines -Encoding ASCII
    Write-Host "[ops-automation] installed fallback=StartupFolder path=$bootstrapPath"
}

switch ($Scope) {
    "System" {
        if (-not (Test-IsAdmin)) {
            Invoke-SelfElevatedSystemInstall
            return
        }
        Register-SystemStartupTasks
        Write-SystemTaskEvidence
        break
    }
    "User" {
        Register-UserLogonTasks
        break
    }
    default {
        if (Test-IsAdmin) {
            Register-SystemStartupTasks
        }
        else {
            Write-Warning "Administrator privileges not detected. Falling back to user logon tasks."
            Register-UserLogonTasks
        }
        break
    }
}

Write-Host "[ops-automation] registered tasks: $watchdogTaskName, $postbootTaskName, $postbootExternalTaskName"
Write-Host "[ops-automation] list tasks with: schtasks /Query /TN $TaskPrefix* /V /FO LIST"
