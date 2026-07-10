# VoIP 실통화 ADB 증적 — S10 + Tab + 백엔드 bridge (단일 writer, 파일 잠금 방지)
param(
    [string]$S10 = "172.30.1.19:5555",
    [string]$Tab = "R83W70QY11H",
    [int]$Minutes = 15
)
$ErrorActionPreference = "Continue"
$ts = Get-Date -Format "yyyyMMdd-HHmmss"
$dir = Join-Path $PSScriptRoot "..\evidence\voip-adb-live-$ts" | Resolve-Path -ErrorAction SilentlyContinue
if (-not $dir) {
    $dir = (New-Item -ItemType Directory -Path (Join-Path $PSScriptRoot "..\evidence\voip-adb-live-$ts") -Force).FullName
} else {
    $dir = (New-Item -ItemType Directory -Path "c:\Users\WORK\source\repos\parkcheolhong\codeAI\evidence\voip-adb-live-$ts" -Force).FullName
}
Write-Host "EVIDENCE_DIR=$dir"
@"
{
  "run_id": "voip-adb-live-$ts",
  "s10": "$S10",
  "tab": "$Tab",
  "duration_min": $Minutes,
  "filters": ["ReactNativeJS:VoIP", "WebRTC", "VoipAudio", "bridge"]
}
"@ | Set-Content "$dir\manifest.json" -Encoding UTF8

adb -s $S10 logcat -c 2>$null
adb -s $Tab logcat -c 2>$null

$jobs = @(
    Start-Job -Name s10_log -ScriptBlock {
        param($d, $dev)
        adb -s $dev logcat -v time ReactNativeJS:V chromium:V WebRTC:V VoipAudio:V *:S 2>&1 |
            Out-File -FilePath "$d\s10-voip.log" -Encoding utf8
    } -ArgumentList $dir, $S10
    Start-Job -Name tab_log -ScriptBlock {
        param($d, $dev)
        adb -s $dev logcat -v time ReactNativeJS:V chromium:V WebRTC:V VoipAudio:V *:S 2>&1 |
            Out-File -FilePath "$d\tab-voip.log" -Encoding utf8
    } -ArgumentList $dir, $Tab
    Start-Job -Name s10_audio -ScriptBlock {
        param($d, $dev, $min)
        $end = (Get-Date).AddMinutes($min)
        while ((Get-Date) -lt $end) {
            $t = Get-Date -Format "o"
            $a = adb -s $dev shell dumpsys audio 2>&1 | Out-String
            $mode = if ($a -match 'mode\s*=\s*(\S+)') { $Matches[1] } else { '?' }
            $sp = if ($a -match '2 \(speaker\):\s*(\d+)') { $Matches[1] } else { '?' }
            $ep = if ($a -match '0 \(earpiece\):\s*(\d+)') { $Matches[1] } else { '?' }
            Add-Content "$d\s10-audio.tsv" "$t`tmode=$mode`tsp=$sp`tep=$ep"
            Start-Sleep -Seconds 3
        }
    } -ArgumentList $dir, $S10, $Minutes
    Start-Job -Name backend -ScriptBlock {
        param($d, $min)
        $end = (Get-Date).AddMinutes($min)
        docker logs -f --tail 20 devanalysis114-backend 2>&1 |
            ForEach-Object -Begin { $sw = [Diagnostics.Stopwatch]::StartNew() } -Process {
                if ($sw.Elapsed.TotalMinutes -gt $min) { return }
                if ($_ -match '\[bridge\]|\[VoIP\]|ICE|forward_live|segment|interpret') {
                    $_ | Add-Content "$d\backend-bridge.log"
                }
            }
    } -ArgumentList $dir, $Minutes
)

Write-Host "Capturing $Minutes min → $dir"
Wait-Job -Job $jobs -Timeout ($Minutes * 60 + 30) | Out-Null
$jobs | Stop-Job -ErrorAction SilentlyContinue
$jobs | Remove-Job -Force -ErrorAction SilentlyContinue
Write-Host "DONE $dir"
