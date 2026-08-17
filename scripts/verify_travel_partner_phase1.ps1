param(
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [string]$AdminEmail = "",
    [string]$AdminPassword = ""
)

$ErrorActionPreference = "Stop"

function Invoke-RestWithRetry {
    param(
        [Parameter(Mandatory = $true)][string]$Method,
        [Parameter(Mandatory = $true)][string]$Uri,
        [hashtable]$Headers,
        $Body = $null,
        [int]$MaxAttempts = 10,
        [int]$DelaySeconds = 2
    )

    for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
        try {
            if ($null -ne $Body) {
                return Invoke-RestMethod -Method $Method -Uri $Uri -Headers $Headers -Body $Body
            }
            return Invoke-RestMethod -Method $Method -Uri $Uri -Headers $Headers
        }
        catch {
            $message = $_.Exception.Message
            $isRetryable = (
                $message -like "*connection was closed unexpectedly*" -or
                $message -like "*underlying connection was closed*" -or
                $message -like "*Unable to connect*" -or
                $message -like "*No connection could be made*"
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
        [int]$MaxAttempts = 30,
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

if ([string]::IsNullOrWhiteSpace($AdminEmail)) {
    $AdminEmail = if ($env:PROBE_LOGIN_EMAIL) { $env:PROBE_LOGIN_EMAIL } else { "119cash@naver.com" }
}
if ([string]::IsNullOrWhiteSpace($AdminPassword)) {
    $AdminPassword = if ($env:PROBE_LOGIN_PASSWORD) { $env:PROBE_LOGIN_PASSWORD } else { "changeme-probe-local" }
}

Write-Host "[INFO] BaseUrl: $BaseUrl"
Write-Host "[INFO] AdminEmail: $AdminEmail"

Wait-ApiReady -BaseUrl $BaseUrl

$form = "username=$([uri]::EscapeDataString($AdminEmail))&password=$([uri]::EscapeDataString($AdminPassword))"
$loginHeaders = @{ "Content-Type" = "application/x-www-form-urlencoded" }
$loginResponse = Invoke-RestWithRetry -Method Post -Uri "$BaseUrl/api/auth/login" -Headers $loginHeaders -Body $form

if (-not $loginResponse.access_token) {
    throw "login failed: access_token missing"
}

$token = [string]$loginResponse.access_token
$authHeaders = @{ Authorization = "Bearer $token"; "Content-Type" = "application/json" }

$partnerId = "phase1-hotel-$(Get-Date -Format 'yyyyMMddHHmmss')"
$partnerPayload = @{
    partner_id        = $partnerId
    name              = "Phase1 Hotel Partner"
    category          = "hotel"
    integration_type  = "affiliate"
    regions_supported = @("KR", "JP")
    commission_model  = "cpa"
    base_url          = "https://example.com/hotel"
    metadata          = @{
        source = "phase1_e2e"
    }
} | ConvertTo-Json -Depth 6

Write-Host "[STEP] POST /api/admin/travel-partners"
$postResult = Invoke-RestWithRetry -Method Post -Uri "$BaseUrl/api/admin/travel-partners" -Headers $authHeaders -Body $partnerPayload
if (-not $postResult.created) {
    throw "partner create failed: created flag is false"
}

Write-Host "[STEP] GET /api/admin/travel-partners"
$getResult = Invoke-RestWithRetry -Method Get -Uri "$BaseUrl/api/admin/travel-partners" -Headers @{ Authorization = "Bearer $token" }
$matched = @($getResult.partners | Where-Object { $_.partner_id -eq $partnerId })
if ($matched.Count -lt 1) {
    throw "partner verification failed: created partner not found in list"
}

$policyPayload = @{
    version                      = "v1"
    default_hotel_partner_id     = $partnerId
    default_tour_partner_id      = $null
    default_transport_partner_id = $null
    rules                        = @(
        @{
            country_code         = "KR"
            city_code            = "SEL"
            hotel_partner_id     = $partnerId
            tour_partner_id      = $null
            transport_partner_id = $null
            fallback_partner_ids = @($partnerId)
            active               = $true
        }
    )
} | ConvertTo-Json -Depth 8

Write-Host "[STEP] PUT /api/admin/travel-routing-policy"
$putResult = Invoke-RestWithRetry -Method Put -Uri "$BaseUrl/api/admin/travel-routing-policy" -Headers $authHeaders -Body $policyPayload
if (-not $putResult.saved) {
    throw "routing policy save failed: saved flag is false"
}

$effectiveDefaultHotel = [string]$putResult.routing_policy.default_hotel_partner_id
if ($effectiveDefaultHotel -ne $partnerId) {
    throw "routing policy verification failed: expected default_hotel_partner_id=$partnerId, actual=$effectiveDefaultHotel"
}

Write-Host "[STEP] POST /api/admin/travel-connectors/$partnerId/test"
$connectorTestResult = Invoke-RestWithRetry -Method Post -Uri "$BaseUrl/api/admin/travel-connectors/$partnerId/test" -Headers $authHeaders -Body "{}"
if (-not $connectorTestResult.tested) {
    throw "connector test failed: tested flag is false"
}
if ([string]$connectorTestResult.connector_id -ne $partnerId) {
    throw "connector test verification failed: expected connector_id=$partnerId, actual=$([string]$connectorTestResult.connector_id)"
}

Write-Host "[PASS] Travel partner Phase 1 e2e verification succeeded"
Write-Host "[DATA] Created partner_id: $partnerId"
