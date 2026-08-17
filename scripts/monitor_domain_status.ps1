param(
    [string]$Domain = "metanova1004.com",
    [string[]]$Paths = @("/api/health", "/admin/login", "/marketplace"),
    [int]$IntervalSec = 30,
    [int]$TimeoutSec = 10,
    [switch]$Continuous
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$logDir = Join-Path $repoRoot "scripts\logs"
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
$logPath = Join-Path $logDir ("domain_status_{0}.log" -f (Get-Date -Format "yyyyMMdd"))

function Write-Log {
    param(
        [string]$Level,
        [string]$Message
    )
    $line = "[{0}] [{1}] {2}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Level, $Message
    $line | Tee-Object -FilePath $logPath -Append
}

function Test-Endpoint {
    param(
        [string]$Url,
        [int]$Timeout
    )

    try {
        $response = Invoke-WebRequest -Uri $Url -TimeoutSec $Timeout -UseBasicParsing
        $code = [int]$response.StatusCode
        if ($code -ge 200 -and $code -lt 500) {
            return @{ Ok = $true; Code = $code; Detail = "ok" }
        }
        return @{ Ok = $false; Code = $code; Detail = "unexpected_status" }
    }
    catch {
        $msg = $_.Exception.Message
        return @{ Ok = $false; Code = -1; Detail = $msg }
    }
}

function Invoke-Probe {
    $anyFailure = $false
    foreach ($path in $Paths) {
        $url = "https://{0}{1}" -f $Domain, $path
        $result = Test-Endpoint -Url $url -Timeout $TimeoutSec
        if ($result.Ok) {
            Write-Log -Level "INFO" -Message ("{0} -> {1}" -f $url, $result.Code)
        }
        else {
            $anyFailure = $true
            Write-Log -Level "ALERT" -Message ("{0} -> FAIL code={1} detail={2}" -f $url, $result.Code, $result.Detail)
        }
    }

    if ($anyFailure) {
        Write-Log -Level "ALERT" -Message "One or more domain checks failed."
    }
    else {
        Write-Log -Level "INFO" -Message "All domain checks passed."
    }
}

Write-Log -Level "INFO" -Message ("Domain monitor started for {0}. continuous={1}, interval={2}s" -f $Domain, [bool]$Continuous, $IntervalSec)

if ($Continuous) {
    while ($true) {
        Invoke-Probe
        Start-Sleep -Seconds $IntervalSec
    }
}
else {
    Invoke-Probe
}
