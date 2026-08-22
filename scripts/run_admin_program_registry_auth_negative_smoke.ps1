param(
    [string]$BaseUrl = "http://127.0.0.1:8000"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Invoke-JsonAllowError {
    param(
        [Parameter(Mandatory=$true)][string]$Method,
        [Parameter(Mandatory=$true)][string]$Url,
        [hashtable]$Headers = @{},
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
        if ($_.Exception.Response -and $_.Exception.Response.StatusCode) {
            $statusCode = [int]$_.Exception.Response.StatusCode
        }
        return [pscustomobject]@{
            StatusCode = $statusCode
            Data       = $null
        }
    }
}

function Get-Token {
    param(
        [Parameter(Mandatory=$true)][string]$BaseUrl,
        [Parameter(Mandatory=$true)][string]$Username,
        [Parameter(Mandatory=$true)][string]$Password
    )

    try {
        $res = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/auth/login" -ContentType "application/x-www-form-urlencoded" -Body @{ username = $Username; password = $Password }
        $token = [string]$res.access_token
        if ([string]::IsNullOrWhiteSpace($token)) { return "" }
        return $token
    }
    catch {
        return ""
    }
}

$adminBase = "$($BaseUrl.TrimEnd('/'))/api/admin"
$target = "$adminBase/program-registry"

Write-Host "[1/2] Validate 401 without auth header"
$unauthRes = Invoke-JsonAllowError -Method "GET" -Url $target
if ($unauthRes.StatusCode -ne 401) {
    throw "Expected 401 without auth header, got $($unauthRes.StatusCode)"
}

Write-Host "[2/2] Validate 403 with non-admin token"
$candidates = @(
    @{ Username = "ui.pod.round.a@devanalysis.local"; Password = "x" },
    @{ Username = "ui.pod.round.b@devanalysis.local"; Password = "x" }
)

$nonAdminToken = ""
$selectedUser = ""
foreach ($c in $candidates) {
    $token = Get-Token -BaseUrl $BaseUrl -Username $c.Username -Password $c.Password
    if (-not [string]::IsNullOrWhiteSpace($token)) {
        $nonAdminToken = $token
        $selectedUser = $c.Username
        break
    }
}

if ([string]::IsNullOrWhiteSpace($nonAdminToken)) {
    throw "Failed to obtain non-admin token. Seed non-admin test account first."
}

$forbiddenRes = Invoke-JsonAllowError -Method "GET" -Url $target -Headers @{ Authorization = "Bearer $nonAdminToken" }
if ($forbiddenRes.StatusCode -ne 403) {
    throw "Expected 403 with non-admin token, got $($forbiddenRes.StatusCode)"
}

Write-Host "AUTH NEGATIVE SMOKE PASSED"
Write-Host "non_admin_user=$selectedUser"
