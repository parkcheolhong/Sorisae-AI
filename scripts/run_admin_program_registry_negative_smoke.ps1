param(
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [string]$ProgramId = "",
    [string]$AdminUsername = "ui.admin.round@devanalysis.local",
    [string]$AdminPassword = "RoundUi!20260426"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-AuthHeader {
    $token = [string]$env:ADMIN_BEARER_TOKEN

    if ([string]::IsNullOrWhiteSpace($token)) {
        try {
            $login = Invoke-RestMethod -Method Post -Uri "$($BaseUrl.TrimEnd('/'))/api/auth/login" -ContentType "application/x-www-form-urlencoded" -Body @{ username = $AdminUsername; password = $AdminPassword }
            $token = [string]$login.access_token
            if (-not [string]::IsNullOrWhiteSpace($token)) {
                $env:ADMIN_BEARER_TOKEN = $token
            }
        }
        catch {
            $token = ""
        }
    }

    if ([string]::IsNullOrWhiteSpace($token)) {
        throw "ADMIN_BEARER_TOKEN is missing and admin auto-login failed."
    }
    return @{ Authorization = "Bearer $token" }
}

function Invoke-JsonAllowError {
    param(
        [Parameter(Mandatory = $true)][string]$Method,
        [Parameter(Mandatory = $true)][string]$Url,
        [Parameter(Mandatory = $true)][hashtable]$Headers,
        [object]$Body = $null
    )

    $req = @{
        Method      = $Method
        Uri         = $Url
        Headers     = $Headers
        ContentType = "application/json"
    }
    if ($null -ne $Body) {
        $req.Body = ($Body | ConvertTo-Json -Depth 10)
    }

    try {
        $resp = Invoke-WebRequest @req
        $data = $null
        if (-not [string]::IsNullOrWhiteSpace($resp.Content)) {
            $data = $resp.Content | ConvertFrom-Json
        }
        return [pscustomobject]@{
            StatusCode = [int]$resp.StatusCode
            Data       = $data
        }
    }
    catch {
        $statusCode = -1
        $content = ""
        if ($_.Exception.Response) {
            try {
                $statusCode = [int]$_.Exception.Response.StatusCode
            }
            catch {}
            try {
                $stream = $_.Exception.Response.GetResponseStream()
                if ($stream) {
                    $reader = New-Object System.IO.StreamReader($stream)
                    $content = $reader.ReadToEnd()
                    $reader.Close()
                }
            }
            catch {}
        }

        $data = $null
        if (-not [string]::IsNullOrWhiteSpace($content)) {
            try { $data = $content | ConvertFrom-Json } catch {}
        }

        return [pscustomobject]@{
            StatusCode = $statusCode
            Data       = $data
        }
    }
}

$headers = Get-AuthHeader
$adminBase = "$($BaseUrl.TrimEnd('/'))/api/admin"

# 준비: 유효한 program_id 확보
$selectedProgramId = $ProgramId
if ([string]::IsNullOrWhiteSpace($selectedProgramId)) {
    $listRes = Invoke-JsonAllowError -Method "GET" -Url "$adminBase/program-registry" -Headers $headers
    if ($listRes.StatusCode -ne 200) {
        throw "Failed to load program list. Expected 200, got $($listRes.StatusCode)"
    }
    if ($listRes.Data -and $listRes.Data.items -and $listRes.Data.items.Count -gt 0) {
        $selectedProgramId = [string]$listRes.Data.items[0].program_id
    }
}
if ([string]::IsNullOrWhiteSpace($selectedProgramId)) {
    throw "No valid program_id found. Pass -ProgramId or seed one program first."
}

Write-Host "[1/3] Validate 404 for missing program_id"
$missingId = "missing-program-id-404"
$missingRes = Invoke-JsonAllowError -Method "GET" -Url "$adminBase/program-registry/$missingId" -Headers $headers
if ($missingRes.StatusCode -ne 404) {
    throw "Expected 404 for missing program_id, got $($missingRes.StatusCode)"
}

Write-Host "[2/3] Validate 400 for rollback confirm=false"
$rollbackBody = @{
    target_version = "0.0.0"
    reason         = "negative-smoke"
    confirm        = $false
}
$rollbackRes = Invoke-JsonAllowError -Method "POST" -Url "$adminBase/program-registry/$selectedProgramId/rollback" -Headers $headers -Body $rollbackBody
if ($rollbackRes.StatusCode -ne 400) {
    throw "Expected 400 for confirm=false rollback request, got $($rollbackRes.StatusCode)"
}

Write-Host "[3/3] Validate 400 for invalid status"
$statusBody = @{
    verification_status = "bad-status-value"
}
$statusRes = Invoke-JsonAllowError -Method "PATCH" -Url "$adminBase/program-registry/$selectedProgramId/status" -Headers $headers -Body $statusBody
if ($statusRes.StatusCode -ne 400) {
    throw "Expected 400 for invalid status string, got $($statusRes.StatusCode)"
}

Write-Host "NEGATIVE SMOKE PASSED"
Write-Host "program_id=$selectedProgramId"
