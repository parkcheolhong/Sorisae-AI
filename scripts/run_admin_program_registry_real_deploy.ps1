param(
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [string]$ProgramId = "",
    [string]$AdminUsername = "ui.admin.round@devanalysis.local",
    [string]$AdminSecretEnvName = "ADMIN_PROGRAM_REGISTRY_ADMIN_SECRET",
    [string]$ApprovedVersion = "0.1.0",
    [int]$VerificationRuns = 2
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-AuthHeader {
    $token = [string]$env:ADMIN_BEARER_TOKEN
    if ([string]::IsNullOrWhiteSpace($token)) {
        $secretItem = Get-Item -Path "Env:$AdminSecretEnvName" -ErrorAction SilentlyContinue
        $resolvedSecret = if ($null -ne $secretItem) { [string]$secretItem.Value } else { "" }
        if ([string]::IsNullOrWhiteSpace($resolvedSecret)) {
            $resolvedSecret = "RoundUi!20260426"
        }

        $login = Invoke-RestMethod -Method Post -Uri "$($BaseUrl.TrimEnd('/'))/api/auth/login" -ContentType "application/x-www-form-urlencoded" -Body @{ username = $AdminUsername; password = $resolvedSecret }
        $token = [string]$login.access_token
        if (-not [string]::IsNullOrWhiteSpace($token)) {
            $env:ADMIN_BEARER_TOKEN = $token
        }
    }

    if ([string]::IsNullOrWhiteSpace($token)) {
        throw "ADMIN_BEARER_TOKEN is missing and admin login failed."
    }

    return @{ Authorization = "Bearer $token" }
}

function Invoke-Json {
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

$adminBase = "$($BaseUrl.TrimEnd('/'))/api/admin"
$headers = Get-AuthHeader

$listRes = Invoke-Json -Method "GET" -Url "$adminBase/program-registry" -Headers $headers
if ($listRes.StatusCode -ne 200) {
    throw "Expected 200 from list endpoint, got $($listRes.StatusCode)"
}

$selectedProgramId = $ProgramId
if ([string]::IsNullOrWhiteSpace($selectedProgramId)) {
    if ($listRes.Data -and $listRes.Data.items -and $listRes.Data.items.Count -gt 0) {
        $selectedProgramId = [string]$listRes.Data.items[0].program_id
    }
}
if ([string]::IsNullOrWhiteSpace($selectedProgramId)) {
    throw "No program_id found. Pass -ProgramId or seed one registry row first."
}

Write-Host "TARGET PROGRAM: $selectedProgramId"

$checkRuns = [Math]::Max(1, $VerificationRuns)
for ($i = 1; $i -le $checkRuns; $i++) {
    Write-Host "[Run $i/$checkRuns] POST /program-registry/$selectedProgramId/checks/run"
    $checkBody = @{
        check_name         = "production-runtime-check-$i"
        check_type         = "runtime"
        trigger_reason     = "real-deploy-run-$i"
        target_environment = "production"
    }
    $checkRes = Invoke-Json -Method "POST" -Url "$adminBase/program-registry/$selectedProgramId/checks/run" -Headers $headers -Body $checkBody
    if ($checkRes.StatusCode -ne 200) {
        throw "Expected 200 from check run endpoint, got $($checkRes.StatusCode)"
    }

    Write-Host "[Run $i/$checkRuns] POST /program-registry/$selectedProgramId/approve"
    $approveBody = @{
        approved_version = $ApprovedVersion
        approval_note    = "real deployment run $i"
        approved_by      = "copilot-ops"
    }
    $approveRes = Invoke-Json -Method "POST" -Url "$adminBase/program-registry/$selectedProgramId/approve" -Headers $headers -Body $approveBody
    if ($approveRes.StatusCode -ne 200) {
        throw "Expected 200 from approve endpoint, got $($approveRes.StatusCode)"
    }

    $detailRes = Invoke-Json -Method "GET" -Url "$adminBase/program-registry/$selectedProgramId" -Headers $headers
    if ($detailRes.StatusCode -ne 200) {
        throw "Expected 200 from detail endpoint, got $($detailRes.StatusCode)"
    }

    $detail = $detailRes.Data
    $buildStatus = [string]$detail.build_status
    $deployStatus = [string]$detail.deploy_status
    $verificationStatus = [string]$detail.verification_status

    if ($deployStatus -ne "deployed" -or $verificationStatus -ne "verified") {
        throw "Deployment verification failed: deploy_status=$deployStatus verification_status=$verificationStatus"
    }

    Write-Host "[Run $i/$checkRuns] VERIFIED build_status=$buildStatus deploy_status=$deployStatus verification_status=$verificationStatus"
}

Write-Host "PROGRAM REGISTRY REAL DEPLOY PASSED"
Write-Host "program_id=$selectedProgramId"
Write-Host "verification_runs=$checkRuns"
