param(
    [string]$TargetFile = ".runtime/secrets/fixed_admin_password.txt",
    [switch]$ElevatedRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Test-IsAdministrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Invoke-SelfElevated {
    if (-not $PSCommandPath) {
        throw "Cannot self-elevate because PSCommandPath is unavailable."
    }

    $escapedScript = $PSCommandPath.Replace("'", "''")
    $escapedTarget = $TargetFile.Replace("'", "''")
    $invokeCommand = "& '$escapedScript' -TargetFile '$escapedTarget' -ElevatedRun"
    $args = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-Command", $invokeCommand
    )

    $logPath = Join-Path ([System.IO.Path]::GetTempPath()) "enable_fixed_admin_4663_audit.log"
    if (Test-Path $logPath) {
        Remove-Item $logPath -Force -ErrorAction SilentlyContinue
    }

    Write-Host "Administrator privileges are required. Requesting elevation..."
    $workingDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
    $proc = Start-Process -FilePath "powershell.exe" -ArgumentList $args -Verb RunAs -WorkingDirectory $workingDir -PassThru -Wait
    if ($null -eq $proc) {
        throw "Failed to start elevated PowerShell process."
    }
    if ($proc.ExitCode -ne 0) {
        if (Test-Path $logPath) {
            Write-Host "--- Elevated run log (last 80 lines) ---"
            Get-Content $logPath -Tail 80 | Out-Host
            Write-Host "--- End elevated run log ---"
        }
        throw ("Elevated run failed with exit code: {0}. Log: {1}" -f $proc.ExitCode, $logPath)
    }
}

if (-not (Test-IsAdministrator)) {
    if ($ElevatedRun) {
        throw "Elevation was attempted, but this process still does not have Administrator privileges. Check UAC approval and local admin membership for this account."
    }

    $logPath = Join-Path ([System.IO.Path]::GetTempPath()) "enable_fixed_admin_4663_audit.log"
    Start-Transcript -Path $logPath -Force | Out-Null
    try {
        Invoke-SelfElevated
    }
    finally {
        Stop-Transcript | Out-Null
    }
    exit 0
}

if ($ElevatedRun) {
    $logPath = Join-Path ([System.IO.Path]::GetTempPath()) "enable_fixed_admin_4663_audit.log"
    Start-Transcript -Path $logPath -Append -Force | Out-Null
}

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$targetPath = Join-Path $root $TargetFile
if (-not (Test-Path $targetPath -PathType Leaf)) {
    throw "Target file not found: $targetPath"
}

$targetDir = Split-Path -Parent $targetPath
$fileSystemSubcategoryGuid = "{0CCE921D-69AE-11D9-BED3-505054503030}"

Write-Host "[1/4] Enable audit policy: File System (Success/Failure)"
auditpol /set /subcategory:$fileSystemSubcategoryGuid /success:enable /failure:enable | Out-Host

Write-Host "[2/4] Apply SACL on secrets directory"
$dirAcl = Get-Acl $targetDir
$dirRights =
[System.Security.AccessControl.FileSystemRights]::CreateFiles -bor
[System.Security.AccessControl.FileSystemRights]::CreateDirectories -bor
[System.Security.AccessControl.FileSystemRights]::Delete -bor
[System.Security.AccessControl.FileSystemRights]::DeleteSubdirectoriesAndFiles -bor
[System.Security.AccessControl.FileSystemRights]::WriteData -bor
[System.Security.AccessControl.FileSystemRights]::AppendData -bor
[System.Security.AccessControl.FileSystemRights]::WriteAttributes -bor
[System.Security.AccessControl.FileSystemRights]::WriteExtendedAttributes
$dirRule = New-Object System.Security.AccessControl.FileSystemAuditRule(
    "Everyone",
    $dirRights,
    [System.Security.AccessControl.InheritanceFlags]"ContainerInherit,ObjectInherit",
    [System.Security.AccessControl.PropagationFlags]::None,
    [System.Security.AccessControl.AuditFlags]"Success,Failure"
)
$dirAcl.AddAuditRule($dirRule)
Set-Acl -Path $targetDir -AclObject $dirAcl

Write-Host "[3/4] Apply SACL on target file"
$fileAcl = Get-Acl $targetPath
$fileRights =
[System.Security.AccessControl.FileSystemRights]::WriteData -bor
[System.Security.AccessControl.FileSystemRights]::AppendData -bor
[System.Security.AccessControl.FileSystemRights]::WriteAttributes -bor
[System.Security.AccessControl.FileSystemRights]::WriteExtendedAttributes -bor
[System.Security.AccessControl.FileSystemRights]::Delete -bor
[System.Security.AccessControl.FileSystemRights]::ChangePermissions -bor
[System.Security.AccessControl.FileSystemRights]::TakeOwnership
$fileRule = New-Object System.Security.AccessControl.FileSystemAuditRule(
    "Everyone",
    $fileRights,
    [System.Security.AccessControl.InheritanceFlags]::None,
    [System.Security.AccessControl.PropagationFlags]::None,
    [System.Security.AccessControl.AuditFlags]"Success,Failure"
)
$fileAcl.AddAuditRule($fileRule)
Set-Acl -Path $targetPath -AclObject $fileAcl

Write-Host "[4/4] Show effective configuration"
auditpol /get /subcategory:$fileSystemSubcategoryGuid | Out-Host
Write-Host "Directory audit rules:"
(Get-Acl $targetDir).Audit |
Format-Table IdentityReference, FileSystemRights, InheritanceFlags, AuditFlags -AutoSize | Out-Host
Write-Host "File audit rules:"
(Get-Acl $targetPath).Audit |
Format-Table IdentityReference, FileSystemRights, InheritanceFlags, AuditFlags -AutoSize | Out-Host

Write-Host "Done. Future changes should emit Security event ID 4663 with account and process name."
Write-Host "Example query:" 
Write-Host "Get-WinEvent -FilterHashtable @{LogName='Security'; Id=4663; StartTime=(Get-Date).AddMinutes(-30)} | Where-Object { $_.Message -match 'fixed_admin_password.txt' }"

if ($ElevatedRun) {
    Stop-Transcript | Out-Null
}
