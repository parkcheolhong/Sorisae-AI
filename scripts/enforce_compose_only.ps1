param(
    [switch]$KillRogueNextDev,
    [switch]$FailOnRogue
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$frontendPathNeedle = "frontend\\frontend"

function Get-RogueNextDevProcesses {
    $items = Get-CimInstance Win32_Process -ErrorAction Stop |
        Where-Object {
            $_.Name -match "^node(\\.exe)?$" -and
            $_.CommandLine -and
            $_.CommandLine -match "next\\s+dev" -and
            $_.CommandLine -match [regex]::Escape($frontendPathNeedle)
        } |
        Select-Object ProcessId, Name, CommandLine
    return @($items)
}

$rogue = @(Get-RogueNextDevProcesses)
if ($rogue.Count -eq 0) {
    Write-Host "[compose-only] no rogue 'next dev' process found"
    exit 0
}

Write-Warning ("[compose-only] found {0} rogue 'next dev' process(es)" -f $rogue.Count)
$rogue | ForEach-Object {
    Write-Host ("[compose-only] pid={0} cmd={1}" -f $_.ProcessId, $_.CommandLine)
}

if ($KillRogueNextDev) {
    foreach ($proc in $rogue) {
        try {
            Stop-Process -Id $proc.ProcessId -Force -ErrorAction Stop
            Write-Host ("[compose-only] terminated pid={0}" -f $proc.ProcessId)
        }
        catch {
            Write-Warning ("[compose-only] failed to terminate pid={0}: {1}" -f $proc.ProcessId, $_.Exception.Message)
        }
    }
}

if ($FailOnRogue) {
    exit 2
}

exit 0
