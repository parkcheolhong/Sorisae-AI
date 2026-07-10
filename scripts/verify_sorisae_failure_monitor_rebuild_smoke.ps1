param(
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [string]$MarketplaceUrl = "http://127.0.0.1:3000/marketplace",
    [string]$AdminUrl3000 = "http://127.0.0.1:3000/admin/login",
    [string]$AdminUrl3005 = "http://127.0.0.1:3005/admin/login",
    [string]$AdminEmail = "119cash@naver.com",
    [pscredential]$AdminCredential = $null,
    [string]$AdminSecretFile = ".runtime/secrets/fixed_admin_password.txt",
    [switch]$SkipBackendRebuild,
    [switch]$SkipUi,
    [switch]$SkipApiProbe,
    [int]$UiTimeoutMs = 20000
)

$ErrorActionPreference = "Stop"

function Invoke-RestWithRetry {
    param(
        [Parameter(Mandatory = $true)][string]$Method,
        [Parameter(Mandatory = $true)][string]$Uri,
        [hashtable]$Headers,
        $Body = $null,
        [string]$ContentType = "",
        [int]$MaxAttempts = 30,
        [int]$DelaySeconds = 2
    )

    for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
        try {
            $params = @{
                Method = $Method
                Uri = $Uri
            }
            if ($Headers) {
                $params.Headers = $Headers
            }
            if ($null -ne $Body) {
                $params.Body = $Body
            }
            if (-not [string]::IsNullOrWhiteSpace($ContentType)) {
                $params.ContentType = $ContentType
            }
            return Invoke-RestMethod @params
        }
        catch {
            $message = $_.Exception.Message
            $isRetryable = (
                $message -like "*connection was closed unexpectedly*" -or
                $message -like "*underlying connection was closed*" -or
                $message -like "*Unable to connect*" -or
                $message -like "*No connection could be made*" -or
                $message -like "*actively refused*"
            )
            if (-not $isRetryable -or $attempt -eq $MaxAttempts) {
                throw
            }
            Write-Host "[RETRY] $Method $Uri (attempt $attempt/$MaxAttempts)"
            Start-Sleep -Seconds $DelaySeconds
        }
    }
}

function Wait-ApiReady {
    param(
        [Parameter(Mandatory = $true)][string]$BaseUrl,
        [int]$MaxAttempts = 60,
        [int]$DelaySeconds = 2
    )

    for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
        try {
            $health = Invoke-RestMethod -Method Get -Uri "$BaseUrl/api/health"
            if ($null -ne $health) {
                if ($attempt -gt 1) {
                    Write-Host "[INFO] API ready after retry ($attempt/$MaxAttempts)"
                }
                return
            }
        }
        catch {
            if ($attempt -eq $MaxAttempts) {
                throw "api health check failed after $MaxAttempts attempts: $($_.Exception.Message)"
            }
            Start-Sleep -Seconds $DelaySeconds
        }
    }
}

function Resolve-AdminPassword {
    param(
        [pscredential]$Credential,
        [string]$SecretFilePath
    )

    if ($null -ne $Credential) {
        return $Credential.GetNetworkCredential().Password
    }

    $repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
    $candidatePath = Join-Path $repoRoot $SecretFilePath
    if (-not (Test-Path -LiteralPath $candidatePath)) {
        throw "admin password file not found: $candidatePath"
    }

    return (Get-Content -LiteralPath $candidatePath -Raw).Trim()
}

function Invoke-BackendRebuild {
    Write-Host "[STEP] docker compose build backend"
    & docker compose build backend
    if ($LASTEXITCODE -ne 0) {
        throw "docker compose build backend failed with exit code $LASTEXITCODE"
    }

    Write-Host "[STEP] docker compose up -d backend"
    & docker compose up -d backend
    if ($LASTEXITCODE -ne 0) {
        throw "docker compose up -d backend failed with exit code $LASTEXITCODE"
    }
}

function Invoke-UiApiSmoke {
    param(
        [string]$OutRoot,
        [string]$BaseUrl,
        [string]$MarketplaceUrl,
        [string]$AdminUrl3000,
        [string]$AdminUrl3005,
        [int]$UiTimeoutMs,
        [bool]$SkipUi,
        [bool]$SkipApiProbe
    )

    $smokeScript = Join-Path $PSScriptRoot "run_ui_api_failure_split_smoke.ps1"
    if (-not (Test-Path -LiteralPath $smokeScript)) {
        throw "smoke script not found: $smokeScript"
    }

    $smokeParams = @{
        BaseApiUrl = $BaseUrl
        MarketplaceUrl = $MarketplaceUrl
        AdminUrl3000 = $AdminUrl3000
        AdminUrl3005 = $AdminUrl3005
        UiTimeoutMs = $UiTimeoutMs
        OutRoot = $OutRoot
    }
    if ($SkipUi) {
        $smokeParams.SkipUi = $true
    }
    if ($SkipApiProbe) {
        $smokeParams.SkipApi = $true
    }

    & $smokeScript @smokeParams
    if ($LASTEXITCODE -ne 0) {
        throw "run_ui_api_failure_split_smoke.ps1 failed with exit code $LASTEXITCODE"
    }

    $resultPath = Join-Path $OutRoot "smoke_result.json"
    if (-not (Test-Path -LiteralPath $resultPath)) {
        throw "smoke result file not found: $resultPath"
    }

    return Get-Content -LiteralPath $resultPath -Raw | ConvertFrom-Json
}

function Convert-ToComparablePathSuffix {
    param(
        [Parameter(Mandatory = $true)][string]$PathValue
    )

    $normalized = $PathValue.Replace('/', [System.IO.Path]::DirectorySeparatorChar).ToLowerInvariant()
    $marker = "backend\tmp\"
    $markerIndex = $normalized.IndexOf($marker)
    if ($markerIndex -ge 0) {
        return $normalized.Substring($markerIndex)
    }
    return [System.IO.Path]::GetFileName($normalized).ToLowerInvariant()
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $repoRoot

$resolvedAdminPassword = Resolve-AdminPassword -Credential $AdminCredential -SecretFilePath $AdminSecretFile
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$outRoot = Join-Path $repoRoot ("backend/tmp/ui_api_failure_split_verify_" + $stamp)

if (-not $SkipBackendRebuild) {
    Invoke-BackendRebuild
}

Wait-ApiReady -BaseUrl $BaseUrl

Write-Host "[STEP] Running UI/API split smoke"
$smokeCall = @{
    OutRoot = $outRoot
    BaseUrl = $BaseUrl
    MarketplaceUrl = $MarketplaceUrl
    AdminUrl3000 = $AdminUrl3000
    AdminUrl3005 = $AdminUrl3005
    UiTimeoutMs = $UiTimeoutMs
    SkipUi = [bool]$SkipUi
    SkipApiProbe = [bool]$SkipApiProbe
}
$smokeResult = Invoke-UiApiSmoke @smokeCall

$form = "username=$([uri]::EscapeDataString($AdminEmail))&password=$([uri]::EscapeDataString($resolvedAdminPassword))"
$login = Invoke-RestWithRetry -Method Post -Uri "$BaseUrl/api/auth/login" -Body $form -ContentType "application/x-www-form-urlencoded"
if (-not $login.access_token) {
    throw "login failed: access_token missing"
}

$token = [string]$login.access_token
$authHeaders = @{ Authorization = "Bearer $token" }

Write-Host "[STEP] GET /api/admin/sorisae-failure-monitor/latest"
$latest = Invoke-RestWithRetry -Method Get -Uri "$BaseUrl/api/admin/sorisae-failure-monitor/latest" -Headers $authHeaders
Write-Host "[STEP] GET /api/admin/sorisae-failure-monitor/latest/result-json"
$resultJson = Invoke-RestWithRetry -Method Get -Uri "$BaseUrl/api/admin/sorisae-failure-monitor/latest/result-json" -Headers $authHeaders

$expectedResultPath = [System.IO.Path]::GetFullPath((Join-Path $outRoot "smoke_result.json"))
$expectedResultSuffix = Convert-ToComparablePathSuffix -PathValue $expectedResultPath
$actualLatestResultPath = [string]$latest.result_json_path
$actualLatestResultSuffix = Convert-ToComparablePathSuffix -PathValue $actualLatestResultPath
$actualPayloadResultPath = [string]$resultJson.result_json_path
$actualPayloadResultSuffix = Convert-ToComparablePathSuffix -PathValue $actualPayloadResultPath

if ($actualLatestResultSuffix -ne $expectedResultSuffix) {
    throw "latest endpoint path mismatch: expected=$expectedResultPath actual=$actualLatestResultPath"
}
if ($actualPayloadResultSuffix -ne $expectedResultSuffix) {
    throw "result-json endpoint path mismatch: expected=$expectedResultPath actual=$actualPayloadResultPath"
}

$expectedClassification = [string]$smokeResult.classification
if ([string]$latest.classification -ne $expectedClassification) {
    throw "latest endpoint classification mismatch: expected=$expectedClassification actual=$([string]$latest.classification)"
}
if ([string]$resultJson.payload.classification -ne $expectedClassification) {
    throw "result-json payload classification mismatch: expected=$expectedClassification actual=$([string]$resultJson.payload.classification)"
}

$expectedMonitorRoot = [System.IO.Path]::GetFullPath((Join-Path $repoRoot "backend/tmp"))
$expectedMonitorRootSuffix = Convert-ToComparablePathSuffix -PathValue $expectedMonitorRoot
$actualMonitorRoot = [string]$latest.monitor_root
$actualMonitorRootSuffix = Convert-ToComparablePathSuffix -PathValue $actualMonitorRoot
if ($actualMonitorRootSuffix -ne $expectedMonitorRootSuffix) {
    throw "monitor_root mismatch: expected=$expectedMonitorRoot actual=$actualMonitorRoot"
}

$monitorRoots = @([object[]]$latest.monitor_roots | ForEach-Object { Convert-ToComparablePathSuffix -PathValue ([string]$_) })
if ($monitorRoots -notcontains $expectedMonitorRootSuffix) {
    throw "monitor_roots does not include backend/tmp: $($monitorRoots -join ', ')"
}

Write-Host "[PASS] Sorisae failure monitor rebuild smoke verification succeeded"
Write-Host "[DATA] classification=$expectedClassification"
Write-Host "[DATA] result_json_path=$expectedResultPath"
Write-Host "[DATA] monitor_root=$actualMonitorRoot"
