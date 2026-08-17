param(
    [string]$DeviceSerial = "",
    [string]$AccessToken,
    [string]$Email = "119cash@naver.com",
    [int]$UserId = 6,
    [string]$Username = "119cash@naver.com",
    [string]$DisplayName = "Passkey Device Probe",
    [string]$EvidenceDir = "",
    [string]$MetroStartLog = "",
    [string]$DevClientUrl = "",
    [string]$AuthApiBase = "https://metanova1004.com",
    [switch]$SkipTokenPreflight
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($AccessToken)) {
    throw "AccessToken is required."
}

$normalizedToken = $AccessToken.Trim()
$hasNonAscii = $false
foreach ($ch in $normalizedToken.ToCharArray()) {
    if ([int][char]$ch -gt 127) {
        $hasNonAscii = $true
        break
    }
}

if ($normalizedToken.StartsWith("<") -and $normalizedToken.EndsWith(">")) {
    throw "AccessToken appears to be a placeholder value. Replace it with a real JWT string (ASCII only)."
}

if ($hasNonAscii) {
    throw "AccessToken contains non-ASCII characters. Use the raw JWT string only (A-Z, a-z, 0-9, '-', '_', '.')."
}

$isJwtLike = $AccessToken -match '^[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+$'
if (-not $isJwtLike) {
    Write-Warning "AccessToken does not look like JWT (expected x.y.z)."
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if ([string]::IsNullOrWhiteSpace($EvidenceDir)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $EvidenceDir = Join-Path $repoRoot "evidence/apk-passkey-real-token-e2e-$stamp"
}
if ([string]::IsNullOrWhiteSpace($MetroStartLog)) {
    $MetroStartLog = Join-Path $repoRoot "apps/mobile-nadotongryoksa/.expo/dev/logs/start.log"
}
New-Item -ItemType Directory -Force -Path $EvidenceDir | Out-Null

$packageName = "com.parkcheolhong.worldlinco"
$mainActivity = "com.parkcheolhong.worldlinco.MainActivity"

function Invoke-Adb {
    param([string[]]$AdbArgs)
    $cmd = @()
    if (-not [string]::IsNullOrWhiteSpace($DeviceSerial)) {
        $cmd += @("-s", $DeviceSerial)
    }
    $cmd += $AdbArgs
    $out = & adb @cmd 2>&1
    return , $out
}

function Save-TextFile {
    param(
        [string]$Path,
        [object[]]$Lines
    )
    $text = ($Lines | Out-String)
    Set-Content -Path $Path -Value $text -Encoding utf8
}

function Build-CallbackUrl {
    param([int]$Round)

    $params = [ordered]@{
        provider     = "passkey"
        auth_mode    = "passkey_login"
        access_token = $AccessToken
        email        = $Email
        user_id      = [string]$UserId
        username     = $Username
        display_name = $DisplayName
        round        = [string]$Round
        ts           = [string]([DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds())
    }

    $parts = @()
    foreach ($k in $params.Keys) {
        $parts += ("{0}={1}" -f [uri]::EscapeDataString($k), [uri]::EscapeDataString([string]$params[$k]))
    }
    return "worldlingo://auth/callback?" + ($parts -join "&")
}

function Get-AuthMe {
    param(
        [string]$BaseUrl,
        [string]$Token
    )

    $normalizedBase = $BaseUrl.TrimEnd('/')
    $url = "$normalizedBase/api/auth/me"
    try {
        return Invoke-RestMethod -Method Get -Uri $url -Headers @{ Authorization = "Bearer $Token" } -TimeoutSec 20
    }
    catch {
        $status = "unknown"
        if ($_.Exception.Response -and $_.Exception.Response.StatusCode) {
            $status = [int]$_.Exception.Response.StatusCode
        }
        $reason = $_.Exception.Message
        throw "token preflight failed: /api/auth/me status=$status base=$normalizedBase reason=$reason"
    }
}

function Get-PatternMatchCount {
    param(
        [string]$Text,
        [string]$Pattern
    )

    return [regex]::Matches($Text, $Pattern, [System.Text.RegularExpressions.RegexOptions]::IgnoreCase).Count
}

function Get-FabAlternativeEvidence {
    param([string]$Text)

    $passkeySuccess = Get-PatternMatchCount -Text $Text -Pattern "PASSKEY_LOGIN_CALLBACK_SUCCESS"
    $socialSuccess = Get-PatternMatchCount -Text $Text -Pattern "SOCIAL_LOGIN_CALLBACK_SUCCESS"
    $tokenReadyCount = Get-PatternMatchCount -Text $Text -Pattern '"token_ready"\s*:\s*true'
    $userReadyCount = Get-PatternMatchCount -Text $Text -Pattern '"user_ready"\s*:\s*true'
    $showLoginFalseCount = Get-PatternMatchCount -Text $Text -Pattern 'show_login"\s*:\s*false'
    $presenceConnectedCount = Get-PatternMatchCount -Text $Text -Pattern 'VOIP_PRESENCE_CONNECTED'

    $score = 0
    if ($passkeySuccess -gt 0) { $score += 1 }
    if ($socialSuccess -gt 0) { $score += 1 }
    if ($tokenReadyCount -gt 0) { $score += 1 }
    if ($userReadyCount -gt 0) { $score += 1 }
    if ($showLoginFalseCount -gt 0) { $score += 1 }
    if ($presenceConnectedCount -gt 0) { $score += 1 }

    $evidenceOk = ($score -ge 4) -and ($showLoginFalseCount -gt 0) -and (($passkeySuccess -gt 0) -or ($socialSuccess -gt 0))

    return [pscustomobject]@{
        score = $score
        evidence_ok = $evidenceOk
        passkey_success = $passkeySuccess
        social_success = $socialSuccess
        token_ready_true = $tokenReadyCount
        user_ready_true = $userReadyCount
        show_login_false = $showLoginFalseCount
        voip_presence_connected = $presenceConnectedCount
    }
}

function Wait-ForReactRuntime {
    param([int]$TimeoutSeconds = 45)

    $startAt = Get-Date
    while (((Get-Date) - $startAt).TotalSeconds -lt $TimeoutSeconds) {
        $logcatOut = Invoke-Adb -AdbArgs @("logcat", "-d", "-v", "time")
        $text = ($logcatOut | Out-String)
        if ($text.Contains("ReactNativeJS") -or $text.Contains('Running "main"')) {
            return $true
        }
        Start-Sleep -Seconds 2
    }

    return $false
}

$tokenPreflightPassed = $false
if (-not $SkipTokenPreflight) {
    $me = Get-AuthMe -BaseUrl $AuthApiBase -Token $AccessToken
    if (-not $me -or -not $me.id -or -not $me.email) {
        throw "token preflight failed: /api/auth/me returned incomplete profile"
    }
    # 토큰 진실 소스와 콜백 파라미터를 강제 동기화한다.
    $UserId = [int]$me.id
    $Email = [string]$me.email
    if (-not [string]::IsNullOrWhiteSpace([string]$me.username)) {
        $Username = [string]$me.username
    }
    $tokenPreflightPassed = $true
}

$deviceList = Invoke-Adb -AdbArgs @("devices")
Save-TextFile -Path (Join-Path $EvidenceDir "00_adb_devices.txt") -Lines $deviceList

Invoke-Adb -AdbArgs @("logcat", "-c") | Out-Null
# 고정 번들/낡은 세션 잔류를 막기 위해 프로세스 종료와 앱 데이터 초기화를 함께 수행한다.
Invoke-Adb -AdbArgs @("shell", "am", "force-stop", $packageName) | Out-Null
Invoke-Adb -AdbArgs @("shell", "pm", "clear", $packageName) | Out-Null
if ([string]::IsNullOrWhiteSpace($DevClientUrl)) {
    $launchOut = Invoke-Adb -AdbArgs @("shell", "am", "start", "-W", "-n", "$packageName/$mainActivity")
}
else {
    $launchOut = Invoke-Adb -AdbArgs @("shell", "am", "start", "-W", "-a", "android.intent.action.VIEW", "-d", $DevClientUrl)
}
Save-TextFile -Path (Join-Path $EvidenceDir "00_main_start.txt") -Lines $launchOut
Start-Sleep -Seconds 5
$runtimeReady = Wait-ForReactRuntime -TimeoutSeconds 45
Set-Content -Path (Join-Path $EvidenceDir "00_runtime_ready.txt") -Value ("runtime_ready=" + $runtimeReady) -Encoding utf8

$roundResults = @()
for ($round = 1; $round -le 2; $round++) {
    $callbackUrl = Build-CallbackUrl -Round $round
    # Keep the callback URL intact through adb shell by passing it as a quoted shell token.
    $callbackUrlForShell = "'$callbackUrl'"
    $callbackStartOut = Invoke-Adb -AdbArgs @("shell", "am", "start", "-W", "-a", "android.intent.action.VIEW", "-d", $callbackUrlForShell)
    Start-Sleep -Milliseconds 800
    # Re-inject once more to avoid listener race during bridgeless runtime resume.
    $callbackRetryOut = Invoke-Adb -AdbArgs @("shell", "am", "start", "-W", "-a", "android.intent.action.VIEW", "-d", $callbackUrlForShell)
    Save-TextFile -Path (Join-Path $EvidenceDir (("{0:00}" -f $round) + "_callback_start.txt")) -Lines ($callbackStartOut + "`n--- retry ---`n" + $callbackRetryOut)

    $activityOut = Invoke-Adb -AdbArgs @("shell", "dumpsys", "activity", "activities")
    Save-TextFile -Path (Join-Path $EvidenceDir (("{0:00}" -f $round) + "_activities.txt")) -Lines $activityOut

    Start-Sleep -Seconds 8
    $logcatOut = Invoke-Adb -AdbArgs @("logcat", "-d", "-v", "time")
    Save-TextFile -Path (Join-Path $EvidenceDir (("{0:00}" -f $round) + "_logcat.txt")) -Lines $logcatOut

    $logText = ($logcatOut | Out-String)
    $hasPasskey = $logText.Contains("PASSKEY_LOGIN_CALLBACK_SUCCESS")
    $hasSocial = $logText.Contains("SOCIAL_LOGIN_CALLBACK_SUCCESS")
    $passkeySuccessCount = Get-PatternMatchCount -Text $logText -Pattern "PASSKEY_LOGIN_CALLBACK_SUCCESS"
    $passkeyFailCount = Get-PatternMatchCount -Text $logText -Pattern "PASSKEY_LOGIN_CALLBACK_FAIL"
    $socialSuccessCount = Get-PatternMatchCount -Text $logText -Pattern "SOCIAL_LOGIN_CALLBACK_SUCCESS"
    $socialFailCount = Get-PatternMatchCount -Text $logText -Pattern "SOCIAL_LOGIN_CALLBACK_FAIL"
    $showLoginTrueCount = Get-PatternMatchCount -Text $logText -Pattern 'show_login"\s*:\s*true'
    $showLoginFalseCount = Get-PatternMatchCount -Text $logText -Pattern 'show_login"\s*:\s*false'
    $sorisaeFabEvalCount = Get-PatternMatchCount -Text $logText -Pattern "SORISAE_FAB_VISIBLE_EVAL"
    $fabAltEvidence = Get-FabAlternativeEvidence -Text $logText
    $fabGateStatus = if ($sorisaeFabEvalCount -gt 0) { "PASS" } elseif ($fabAltEvidence.evidence_ok) { "HOLD" } else { "BLOCKED" }
    $hasErrorActivity = $logText.Contains("ErrorActivity") -or $logText.Contains("host.exp.exponent")

    $roundResults += [pscustomobject]@{
        round                          = $round
        has_passkey_callback_success   = $hasPasskey
        has_social_callback_success    = $hasSocial
        has_error_activity             = $hasErrorActivity
        passkey_success_count          = $passkeySuccessCount
        passkey_fail_count             = $passkeyFailCount
        social_success_count           = $socialSuccessCount
        social_fail_count              = $socialFailCount
        show_login_true_count          = $showLoginTrueCount
        show_login_false_count         = $showLoginFalseCount
        sorisae_fab_eval_count         = $sorisaeFabEvalCount
        sorisae_fab_alt_score          = $fabAltEvidence.score
        sorisae_fab_alt_evidence_ok    = $fabAltEvidence.evidence_ok
        sorisae_fab_gate_status        = $fabGateStatus
        callback_url                   = $callbackUrl
        callback_url_for_shell         = $callbackUrlForShell
    }

    Invoke-Adb -AdbArgs @("logcat", "-c") | Out-Null
}

$allPass = ($roundResults | Where-Object {
        -not (
            $_.has_passkey_callback_success -and
            $_.has_social_callback_success -and
            $_.passkey_fail_count -eq 0 -and
            $_.social_fail_count -eq 0
        )
    }).Count -eq 0
$anyErrorActivity = ($roundResults | Where-Object { $_.has_error_activity }).Count -gt 0
$fabGateStatus = if (($roundResults | Where-Object { $_.sorisae_fab_eval_count -gt 0 }).Count -gt 0) {
    "PASS"
}
elseif (($roundResults | Where-Object { $_.sorisae_fab_alt_evidence_ok }).Count -gt 0) {
    "HOLD"
}
else {
    "BLOCKED"
}
$status = if ($allPass -and -not $anyErrorActivity) { "PASS" } else { "FAILED" }

$summaryLines = @(
    "status: $status",
    "objective: same real-token callback reinjection x2 with PASSKEY_LOGIN_CALLBACK_SUCCESS and SOCIAL_LOGIN_CALLBACK_SUCCESS (logcat-only source of truth)",
    "run_dir: $($EvidenceDir.Replace('\\','/'))",
    "",
    "round_results:"
)

foreach ($r in $roundResults) {
    $summaryLines += "- round $($r.round): passkey_success=$($r.has_passkey_callback_success) social_success=$($r.has_social_callback_success) error_activity=$($r.has_error_activity) passkey_success_count=$($r.passkey_success_count) passkey_fail_count=$($r.passkey_fail_count) social_success_count=$($r.social_success_count) social_fail_count=$($r.social_fail_count) show_login_true_count=$($r.show_login_true_count) show_login_false_count=$($r.show_login_false_count) sorisae_fab_eval_count=$($r.sorisae_fab_eval_count)"
}

$summaryLines += ""
$summaryLines += "notes:"
$summaryLines += "- callback path: worldlingo://auth/callback"
if ([string]::IsNullOrWhiteSpace($DevClientUrl)) {
    $summaryLines += "- app launch path: am start -W -n com.parkcheolhong.worldlinco/com.parkcheolhong.worldlinco.MainActivity"
}
else {
    $summaryLines += "- app launch path: am start -W -a android.intent.action.VIEW -d $DevClientUrl"
}
$summaryLines += "- runtime_ready_before_rounds: $runtimeReady"
$summaryLines += "- callback reinjection policy: per-round double start (initial + retry)"
$summaryLines += "- verdict rule: each round must have passkey/social success event and zero passkey/social fail events (logcat-only)"
$summaryLines += "- fab_gate_status: $fabGateStatus (actual SORISAE_FAB_VISIBLE_EVAL preferred; temp alt evidence uses callback success + show_login=false + token/user ready + VOIP_PRESENCE_CONNECTED)"
$summaryLines += "- temp_fab_alt_evidence_allowed: true until the actual FAB event is observed in released runtime"
$summaryLines += "- token_preflight_passed: $tokenPreflightPassed"
$summaryLines += "- token_jwt_like: $isJwtLike"
$summaryLines += "- auth_api_base: $AuthApiBase"

Set-Content -Path (Join-Path $EvidenceDir "validation_summary.txt") -Value ($summaryLines -join "`r`n") -Encoding utf8

$roundResults | ConvertTo-Json -Depth 4 | Set-Content -Path (Join-Path $EvidenceDir "result.json") -Encoding utf8

Write-Host "[VERIFY] status=$status"
Write-Host "[VERIFY] evidence=$EvidenceDir"
Write-Host "[FAB_GATE] status=$fabGateStatus"
if ($status -ne "PASS") {
    exit 1
}
