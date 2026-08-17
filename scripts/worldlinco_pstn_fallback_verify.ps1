#!/usr/bin/env pwsh
# PSTN fallback path verification (production API + optional device dialer intent).
param(
    [string]$ApiBaseUrl = "https://metanova1004.com",
    [string]$VoipApiEmail = "119cash@naver.com",
    [string]$VoipApiPasswordFile = ".runtime/secrets/fixed_admin_password.txt",
    [string]$CalleePhone = "+821011112222",
    [string]$Device = "",
    [switch]$ApiOnly
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$EvidenceDir = Join-Path (Join-Path $RepoRoot "evidence") "pstn-fallback-$(Get-Date -Format yyyyMMdd-HHmmss)"
New-Item -ItemType Directory -Force -Path $EvidenceDir | Out-Null

function Get-AccessToken {
    $password = $env:WORLDLINCO_VOIP_API_PASSWORD
    if (-not $password) {
        $path = Join-Path $RepoRoot $VoipApiPasswordFile
        if (Test-Path $path) {
            $raw = (Get-Content -Raw $path).Trim()
            if ($raw -and $raw -ne "SET_VIA_ENV_ONLY") { $password = $raw }
        }
    }
    if (-not $password) {
        throw "Set WORLDLINCO_VOIP_API_PASSWORD for production PSTN API verify"
    }
    $loginJson = & curl.exe -s --max-time 20 -X POST "$ApiBaseUrl/api/auth/login" `
        -H "Content-Type: application/x-www-form-urlencoded" `
        --data-urlencode "username=$VoipApiEmail" `
        --data-urlencode "password=$password"
    $login = $loginJson | ConvertFrom-Json
    if (-not $login.access_token) { throw "Login failed: $loginJson" }
    return [string]$login.access_token
}

$token = Get-AccessToken
$sessionId = "pstn-fallback-verify-$(Get-Date -Format yyyyMMddHHmmss)"

# 1) Phone-only initiate (no app callee) — native dialer fallback
$bodyPhoneOnly = (@{
    callee_phone = $CalleePhone
    caller_id = "pstn-verify"
    session_id = $sessionId
    mode = "pstn_assist"
} | ConvertTo-Json -Compress)

$phoneResp = & curl.exe -s --max-time 30 -X POST "$ApiBaseUrl/api/v1/voip/calls/initiate" `
    -H "Authorization: Bearer $token" `
    -H "Content-Type: application/json" `
    -d $bodyPhoneOnly
$phonePayload = $phoneResp | ConvertFrom-Json
$phoneResp | Out-File (Join-Path $EvidenceDir "initiate_phone_only.json") -Encoding utf8

$checks = [ordered]@{
    phone_dialer_required = ($phonePayload.phone_dialer_required -eq $true)
    call_route_native = ($phonePayload.call_route -eq "native_phone_dialer")
    status_dialer_required = ($phonePayload.status -eq "dialer_required")
    fallback_dial_url = ($phonePayload.fallback_dial_url -match "^tel:")
    resolved_mode_pstn_assist = ($phonePayload.resolved_mode -eq "pstn_assist")
}

# 2) Friend + phone (app target preferred when online) — documents mixed request
$bodyMixed = (@{
    callee_phone = $CalleePhone
    callee_voice_id = "nado-000001"
    friend_id = 55
    caller_id = "pstn-verify-mixed"
    session_id = "$sessionId-mixed"
    mode = "voip_full_auto"
} | ConvertTo-Json -Compress)

$mixedResp = & curl.exe -s --max-time 30 -X POST "$ApiBaseUrl/api/v1/voip/calls/initiate" `
    -H "Authorization: Bearer $token" `
    -H "Content-Type: application/json" `
    -d $bodyMixed
$mixedPayload = $mixedResp | ConvertFrom-Json
$mixedResp | Out-File (Join-Path $EvidenceDir "initiate_mixed_friend_phone.json") -Encoding utf8

$checks["mixed_app_webrtc_when_friend_online"] = ($mixedPayload.call_route -eq "app_webrtc")
$checks["mixed_phone_dialer_not_required"] = ($mixedPayload.phone_dialer_required -eq $false)

$report = [pscustomobject]@{
    timestamp = (Get-Date).ToString("o")
    api_base = $ApiBaseUrl
    evidence_dir = $EvidenceDir
    phone_only_call_id = $phonePayload.call_id
    mixed_call_id = $mixedPayload.call_id
    checks = $checks
    verdict = if (($checks.Values | Where-Object { $_ -eq $false }).Count -eq 0) { "PASS" } else { "FAIL" }
    note = "PSTN incoming translation (carrier SIP) not in scope — this verifies dialer fallback contract only."
}
$report | ConvertTo-Json -Depth 5 | Out-File (Join-Path $EvidenceDir "PSTN_FALLBACK_REPORT.json") -Encoding utf8
$report | ConvertTo-Json -Depth 5 | Write-Host

if ($report.verdict -ne "PASS") { exit 1 }

if (-not $ApiOnly -and $Device) {
    $tel = $phonePayload.fallback_dial_url -replace "^tel:", ""
    Write-Host "Launching device dialer intent on $Device -> $tel"
    & adb -s $Device shell am start -a android.intent.action.DIAL -d "tel:$tel" | Out-Null
    Start-Sleep -Seconds 3
    & adb -s $Device shell uiautomator dump /sdcard/pstn_dialer.xml | Out-Null
    & adb -s $Device pull /sdcard/pstn_dialer.xml (Join-Path $EvidenceDir "pstn_dialer_ui.xml") | Out-Null
}

exit 0
