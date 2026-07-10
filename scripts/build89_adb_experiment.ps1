#!/usr/bin/env pwsh
param(
    [string]$CallerDevice = "R83W70QY11H",
    [string]$CalleeDevice = "172.30.1.19:5555",
    [string]$PackageName = "com.parkcheolhong.worldlinco",
    [string]$CalleeVoiceId = "nado-000001",
    [string]$ApiBaseUrl = "https://metanova1004.com"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$RunDir = Join-Path $RepoRoot "evidence\build89_adb_test_$Stamp"
New-Item -ItemType Directory -Force -Path $RunDir | Out-Null

function Write-Step([string]$Message) {
    $line = "[$(Get-Date -Format 'HH:mm:ss')] $Message"
    Write-Host $line
    Add-Content -Path (Join-Path $RunDir "run.log") -Value $line
}

function Invoke-Adb {
    param([string]$Device, [string[]]$AdbArgs)
    $prev = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        & adb -s $Device @AdbArgs 2>&1 | ForEach-Object { "$_" }
    } finally {
        $ErrorActionPreference = $prev
    }
}

function Get-LogcatText([string]$Device) {
    return (Invoke-Adb $Device @("logcat", "-d", "-v", "time", "-s", "ReactNativeJS:*", "ReactNative:*", "MediaPlayer:*", "NuPlayer:*", "Ringtone:*", "Vibrator:*", "TextToSpeech:*")) -join "`n"
}

function Wait-ForLogPattern {
    param([string]$Device, [string]$Pattern, [int]$TimeoutSec = 90)
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        if ((Get-LogcatText $Device) -match $Pattern) { return $true }
        Start-Sleep -Seconds 2
    }
    return $false
}

function Get-UiDump([string]$Device, [string]$OutPath) {
    $remote = "/sdcard/window_dump.xml"
    Invoke-Adb $Device @("shell", "uiautomator", "dump", $remote) | Out-Null
    Invoke-Adb $Device @("pull", $remote, $OutPath) | Out-Null
}

function Tap-ByResourceId {
    param([string]$Device, [string]$ResourceId, [string]$DumpPath)
    Get-UiDump -Device $Device -OutPath $DumpPath | Out-Null
    if (-not (Test-Path $DumpPath)) { return $false }
    [xml]$doc = Get-Content -Raw $DumpPath
    $node = $doc.SelectSingleNode("//node[contains(@resource-id,'$ResourceId')]")
    if (-not $node) { return $false }
    $bounds = [string]$node.GetAttribute("bounds")
    if ($bounds -notmatch '^\[(\d+),(\d+)\]\[(\d+),(\d+)\]$') { return $false }
    $cx = [int](([int]$matches[1] + [int]$matches[3]) / 2)
    $cy = [int](([int]$matches[2] + [int]$matches[4]) / 2)
    Write-Step "Tap $ResourceId at ${cx},${cy} on $Device"
    Invoke-Adb $Device @("shell", "input", "tap", "$cx", "$cy") | Out-Null
    return $true
}

function Find-ScrollableNode([string]$DumpPath) {
    if (-not (Test-Path $DumpPath)) { return $null }
    [xml]$doc = Get-Content -Raw $DumpPath
    $nodes = $doc.SelectNodes("//node[@scrollable='true']")
    return @($nodes)
}

function Get-ApiToken {
    $password = $env:WORLDLINCO_VOIP_API_PASSWORD
    if (-not $password) {
        $passwordFile = Join-Path $RepoRoot ".runtime\secrets\fixed_admin_password.txt"
        if (Test-Path $passwordFile) {
            $password = (Get-Content -Raw $passwordFile).Trim()
        }
    }
    if (-not $password) { return $null }
    $loginJson = & curl.exe -s --max-time 20 -X POST "$ApiBaseUrl/api/auth/login" `
        -H "Content-Type: application/x-www-form-urlencoded" `
        --data-urlencode "username=119cash@naver.com" `
        --data-urlencode "password=$password"
    $login = $loginJson | ConvertFrom-Json
    return [string]$login.access_token
}

function Send-ChatProbe {
    param([string]$Token)
    if (-not $Token) { return @{ ok = $false; reason = "no_token" } }
    $roomsJson = & curl.exe -s --max-time 20 -H "Authorization: Bearer $Token" "$ApiBaseUrl/api/mobile/chat/rooms"
    $rooms = ($roomsJson | ConvertFrom-Json)
    $roomList = @($rooms.rooms)
    if (-not $roomList.Count) { return @{ ok = $false; reason = "no_rooms" } }
    $room = $roomList | Where-Object { $_.counterpart -and $_.counterpart.voice_id -eq "nado-000001" } | Select-Object -First 1
    if (-not $room) { $room = $roomList | Select-Object -First 1 }
    $roomId = [string]$room.room_id
    $body = @{ message_type = "text"; body = "build89 adb chat alert probe $(Get-Date -Format 'HH:mm:ss')" } | ConvertTo-Json -Compress
    $resp = & curl.exe -s --max-time 20 -X POST "$ApiBaseUrl/api/mobile/chat/rooms/$roomId/messages" `
        -H "Authorization: Bearer $Token" -H "Content-Type: application/json" -d $body
    return @{ ok = $true; room_id = $roomId; response = $resp }
}

Write-Step "Run dir: $RunDir"

Write-Step "Wake + launch apps"
Invoke-Adb $CallerDevice @("shell", "input", "keyevent", "KEYCODE_WAKEUP") | Out-Null
Invoke-Adb $CalleeDevice @("shell", "input", "keyevent", "KEYCODE_WAKEUP") | Out-Null
Invoke-Adb $CallerDevice @("shell", "am", "start", "-n", "$PackageName/.MainActivity") | Out-Null
Invoke-Adb $CalleeDevice @("shell", "am", "start", "-n", "$PackageName/.MainActivity") | Out-Null
Start-Sleep -Seconds 12

Invoke-Adb $CallerDevice @("logcat", "-c") | Out-Null
Invoke-Adb $CalleeDevice @("logcat", "-c") | Out-Null

Write-Step "Wait callee presence"
$presenceOk = Wait-ForLogPattern $CalleeDevice "VOIP_PRESENCE_CONNECTED" 120
Write-Step "callee_presence=$presenceOk"

# --- Test 1: friend folder modal scroll (Tab) ---
Write-Step "TEST1 friend-folder scroll on Tab"
Invoke-Adb $CallerDevice @("shell", "am", "start", "-W", "-a", "android.intent.action.VIEW", "-d", "worldlingo://voip/open?action=validation") | Out-Null
Start-Sleep -Seconds 5
$dumpBefore = Join-Path $RunDir "tab_voip_lobby.xml"
Get-UiDump $CallerDevice $dumpBefore | Out-Null
Tap-ByResourceId -Device $CallerDevice -ResourceId "worldlinco-voip-lobby-friend-folder-open" -DumpPath (Join-Path $RunDir "tab_friend_open_tap.xml") | Out-Null
Start-Sleep -Seconds 4
$dumpModalBefore = Join-Path $RunDir "tab_friend_modal_before.xml"
Get-UiDump $CallerDevice $dumpModalBefore | Out-Null
$scrollablesBefore = Find-ScrollableNode $dumpModalBefore
Invoke-Adb $CallerDevice @("shell", "input", "swipe", "400", "1500", "400", "500", "500") | Out-Null
Start-Sleep -Seconds 2
$dumpModalAfter = Join-Path $RunDir "tab_friend_modal_after.xml"
Get-UiDump $CallerDevice $dumpModalAfter | Out-Null
$scrollablesAfter = Find-ScrollableNode $dumpModalAfter
$friendVisibleBefore = (Get-Content -Raw $dumpModalBefore) -match "119cash@naver.com|nado-000001|보이스톡 걸기"
$friendVisibleAfter = (Get-Content -Raw $dumpModalAfter) -match "119cash@naver.com|nado-000001|보이스톡 걸기"
$scrollableCount = @($scrollablesAfter).Count
Write-Step "TEST1 scrollable_nodes=$scrollableCount friend_before=$friendVisibleBefore friend_after=$friendVisibleAfter"
Invoke-Adb $CallerDevice @("shell", "input", "keyevent", "KEYCODE_BACK") | Out-Null
Start-Sleep -Seconds 2

# --- Test 2: background VoIP incoming on S10 ---
Write-Step "TEST2 background VoIP incoming on S10"
Invoke-Adb $CallerDevice @("logcat", "-c") | Out-Null
Invoke-Adb $CalleeDevice @("logcat", "-c") | Out-Null
Invoke-Adb $CalleeDevice @("shell", "input", "keyevent", "KEYCODE_HOME") | Out-Null
Start-Sleep -Seconds 2
$runToken = Get-Date -Format "HHmmss"
Invoke-Adb $CallerDevice @("shell", "am", "start", "-W", "-a", "android.intent.action.VIEW", "-d", "worldlingo://voip/open?action=validation&callee_voice_id=$CalleeVoiceId&force=1&run=$runToken") | Out-Null
Start-Sleep -Seconds 8
for ($i = 0; $i -lt 8; $i++) {
    Tap-ByResourceId -Device $CallerDevice -ResourceId "worldlinco-friend-voice-call-$CalleeVoiceId" -DumpPath (Join-Path $RunDir "tab_call_tap_$i.xml") | Out-Null
    Start-Sleep -Seconds 2
    if ((Get-LogcatText $CallerDevice) -match 'VOIP_FRIEND_CALL_SUCCESS|VOIP_START_CALL|call_id') { break }
}
Start-Sleep -Seconds 20
$calleeLog = Get-LogcatText $CalleeDevice
$callerLog = Get-LogcatText $CallerDevice
$calleeLog | Out-File (Join-Path $RunDir "callee_bg_voip.log") -Encoding utf8
$callerLog | Out-File (Join-Path $RunDir "caller_bg_voip.log") -Encoding utf8
$voipAlert = [bool]($calleeLog -match 'VOIP_INCOMING_ALERT_STARTED|VOIP_INCOMING_ALERT_REASSERT')
$voipNative = [bool]($calleeLog -match 'VOIP_PENDING_CALL_FETCHED|VOIP_INCOMING_CALL_APPLIED|incoming_call')
$voipNoti = [bool]($calleeLog -match 'VOIP_NOTIFICATION_PERMISSION|notifications_enabled')
$ringEvidence = [bool]($calleeLog -match 'NuPlayer|Ringtone|worldlinco:incoming_voip_alert')
Write-Step "TEST2 alert_started=$voipAlert pending_or_applied=$voipNative ring_evidence=$ringEvidence noti_probe=$voipNoti"

# --- Test 3: background chat FCM on S10 ---
Write-Step "TEST3 background chat push on S10"
Invoke-Adb $CalleeDevice @("logcat", "-c") | Out-Null
Invoke-Adb $CalleeDevice @("shell", "input", "keyevent", "KEYCODE_HOME") | Out-Null
Start-Sleep -Seconds 2
$token = Get-ApiToken
$chatProbe = Send-ChatProbe -Token $token
$chatProbe | ConvertTo-Json -Depth 4 | Out-File (Join-Path $RunDir "chat_probe.json") -Encoding utf8
Write-Step "chat_probe room=$($chatProbe.room_id) ok=$($chatProbe.ok)"
Start-Sleep -Seconds 15
$chatLog = Get-LogcatText $CalleeDevice
$chatLog | Out-File (Join-Path $RunDir "callee_bg_chat.log") -Encoding utf8
$chatFcm = [bool]($chatLog -match 'chat_message|WorldlincoFCM|CHAT_DEEP_LINK|친구야')
$chatNative = [bool]($chatLog -match 'friend-hey|TextToSpeech|playNotificationBurst')
Write-Step "TEST3 chat_fcm=$chatFcm chat_native=$chatNative"

$notiDump = Invoke-Adb $CalleeDevice @("shell", "dumpsys", "notification") | Out-String
($notiDump | Select-String -Pattern "com.parkcheolhong.worldlinco" -Context 0,4 | Out-String) | Out-File (Join-Path $RunDir "callee_notification_settings.txt") -Encoding utf8

$summary = [ordered]@{
    timestamp = (Get-Date).ToString("o")
    run_dir = $RunDir
    build = "89 / 1.0.59"
    callee_presence = $presenceOk
    test1_friend_scroll = @{
        scrollable_nodes = $scrollableCount
        friend_visible_before = $friendVisibleBefore
        friend_visible_after = $friendVisibleAfter
        pass = ($scrollableCount -gt 0 -and $friendVisibleAfter)
    }
    test2_bg_voip = @{
        alert_started = $voipAlert
        pending_or_applied = $voipNative
        ring_evidence = $ringEvidence
        notifications_probe = $voipNoti
        pass = ($voipAlert -or $ringEvidence)
    }
    test3_bg_chat = @{
        probe = $chatProbe
        chat_fcm_log = $chatFcm
        chat_native_log = $chatNative
        pass = ($chatFcm -or $chatNative)
    }
    callee_allow_noti = [bool]($notiDump -match 'allowNoti=false')
}
$summary | ConvertTo-Json -Depth 6 | Out-File (Join-Path $RunDir "summary.json") -Encoding utf8
Write-Step "SUMMARY written: $(Join-Path $RunDir 'summary.json')"
Write-Step "allowNoti_disabled=$($summary.callee_allow_noti)"
