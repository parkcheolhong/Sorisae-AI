#!/usr/bin/env pwsh
# WorldLinco 50-language alignment audit (mobile LANGS ↔ backend API)
param(
    [string]$ApiBaseUrl = "https://metanova1004.com",
    [string]$EvidenceRoot = ""
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
if (-not $EvidenceRoot) {
    $EvidenceRoot = Join-Path $RepoRoot "evidence\worldlinco-v1-launch"
}
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$RunDir = Join-Path $EvidenceRoot "50lang_audit_$Stamp"
New-Item -ItemType Directory -Force -Path $RunDir | Out-Null

$MobileCodes = @(
    "ko","en","zh","zh-tw","ja","es","fr","de","pt","ru",
    "ar","hi","it","tr","vi","th","id","ms","nl","pl",
    "uk","sv","no","da","fi","cs","ro","hu","el","he",
    "bg","hr","sr","sk","sl","lt","lv","et","fa","ur",
    "bn","ta","te","ml","gu","mr","fil","sw","ca","am"
)

function Write-Step([string]$Message) {
    $line = "[$(Get-Date -Format 'HH:mm:ss')] $Message"
    Write-Host $line
    Add-Content -Path (Join-Path $RunDir "run.log") -Value $line
}

Write-Step "50-language alignment audit -> $RunDir"

# Local backend SSOT
$localJson = & python -c @"
from backend.services.nadotongryoksa.translator import SUPPORTED_LANGUAGES
import json
print(json.dumps({'count': len(SUPPORTED_LANGUAGES), 'codes': sorted(SUPPORTED_LANGUAGES.keys())}))
"@ 2>&1
$local = $localJson | ConvertFrom-Json
Write-Step "Local SUPPORTED_LANGUAGES count=$($local.count)"

$missingLocal = @($MobileCodes | Where-Object { $_ -notin $local.codes })
$extraLocal = @($local.codes | Where-Object { $_ -notin $MobileCodes })
Write-Step "Local missing vs mobile: $($missingLocal -join ', ')"
Write-Step "Local extra vs mobile: $($extraLocal -join ', ')"

# Remote API
$remoteRaw = & curl.exe -s --max-time 20 "$ApiBaseUrl/api/llm/translate/languages"
$remoteRaw | Out-File (Join-Path $RunDir "remote_languages.json") -Encoding utf8
$remote = $remoteRaw | ConvertFrom-Json
$remoteCodes = @($remote.languages.PSObject.Properties.Name)
Write-Step "Remote API count=$($remote.count) codes=$($remoteCodes.Count)"

$missingRemote = @($MobileCodes | Where-Object { $_ -notin $remoteCodes })
$extraRemote = @($remoteCodes | Where-Object { $_ -notin $MobileCodes })

# ko↔ja voice-translate smoke (transcript mode)
$koJaPath = Join-Path $RunDir "ko_ja_body.json"
@'
{"transcript":"안녕하세요. 반갑습니다.","from_lang":"ko","to_lang":"ja","language":"ko"}
'@ | Set-Content -Path $koJaPath -Encoding utf8 -NoNewline
$koJaRaw = & curl.exe -s --max-time 30 -X POST "$ApiBaseUrl/api/llm/voice-translate" `
    -H "Content-Type: application/json" --data-binary "@$koJaPath"
$koJaRaw | Out-File (Join-Path $RunDir "ko_ja_translate.json") -Encoding utf8
$koJaOk = $false
$koJaErr = $null
try {
    $koJa = $koJaRaw | ConvertFrom-Json
    $koJaText = if ($koJa.translated_text) { [string]$koJa.translated_text } else { [string]$koJa.translated }
    $koJaOk = [bool]$koJaText
    Write-Step "ko->ja translate OK: $koJaText"
} catch {
    $koJaErr = $koJaRaw
    Write-Step "ko->ja translate FAIL: $koJaRaw"
}

$jaKoPath = Join-Path $RunDir "ja_ko_body.json"
@'
{"transcript":"こんにちは。よろしくお願いします。","from_lang":"ja","to_lang":"ko","language":"ja"}
'@ | Set-Content -Path $jaKoPath -Encoding utf8 -NoNewline
$jaKoRaw = & curl.exe -s --max-time 30 -X POST "$ApiBaseUrl/api/llm/voice-translate" `
    -H "Content-Type: application/json" --data-binary "@$jaKoPath"
$jaKoRaw | Out-File (Join-Path $RunDir "ja_ko_translate.json") -Encoding utf8
$jaKoOk = $false
try {
    $jaKo = $jaKoRaw | ConvertFrom-Json
    $jaKoText = if ($jaKo.translated_text) { [string]$jaKo.translated_text } else { [string]$jaKo.translated }
    $jaKoOk = [bool]$jaKoText
    Write-Step "ja->ko translate OK: $jaKoText"
} catch {
    Write-Step "ja->ko translate FAIL: $jaKoRaw"
}

$summary = [pscustomobject]@{
    timestamp = (Get-Date).ToString("o")
    run_dir = $RunDir
    mobile_count = $MobileCodes.Count
    local_count = $local.count
    local_aligned = ($missingLocal.Count -eq 0 -and $extraLocal.Count -eq 0 -and $local.count -eq 50)
    remote_count = $remote.count
    remote_missing = $missingRemote
    remote_extra = $extraRemote
    remote_aligned = ($missingRemote.Count -eq 0 -and $extraRemote.Count -eq 0 -and $remote.count -eq 50)
    ko_ja_api_ok = $koJaOk
    ja_ko_api_ok = $jaKoOk
    pass = ($local.count -eq 50 -and $missingLocal.Count -eq 0 -and $koJaOk -and $jaKoOk)
}
$summary | ConvertTo-Json -Depth 5 | Out-File (Join-Path $RunDir "summary.json") -Encoding utf8
Write-Step "Verdict local_aligned=$($summary.local_aligned) remote_aligned=$($summary.remote_aligned) ko_ja=$koJaOk ja_ko=$jaKoOk"
if (-not $summary.pass) { exit 1 }
