param(
    [string]$BaseUrl = 'http://127.0.0.1:8000',
    [int]$SamplesPerMode = 5,
    [int]$TimeoutSec = 90,
    [string]$OutputPath = 'artifacts/sorisae/timing-breakdown-latest.json'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Invoke-FriendChatSample {
    param(
        [bool]$Tts,
        [int]$Index
    )

    $seed = [guid]::NewGuid().ToString('N').Substring(0, 8)
    $body = @{
        transcript = "소리새 구간측정 샘플-${Index}-${seed}"
        language = 'ko'
        country_code = 'KR'
        tts = $Tts
    } | ConvertTo-Json -Compress

    $start = Get-Date
    $response = Invoke-RestMethod -Uri ("{0}/api/llm/voice/friend-chat" -f $BaseUrl.TrimEnd('/')) -Method Post -ContentType 'application/json' -Body $body -TimeoutSec $TimeoutSec
    $elapsedMs = [int]((Get-Date) - $start).TotalMilliseconds

    $timing = $null
    if ($null -ne $response -and $null -ne $response.timing_ms) {
        $timing = $response.timing_ms
    }

    [pscustomobject]@{
        tts = $Tts
        index = $Index
        elapsed_ms = $elapsedMs
        has_timing = ($null -ne $timing)
        timing_ms = $timing
    }
}

function Get-Stats {
    param(
        [double[]]$Values
    )

    if (-not $Values -or $Values.Count -eq 0) {
        return $null
    }

    $sorted = $Values | Sort-Object
    $count = $sorted.Count
    $p95Index = [math]::Floor(($count - 1) * 0.95)
    if ($p95Index -lt 0) { $p95Index = 0 }
    if ($p95Index -ge $count) { $p95Index = $count - 1 }

    [pscustomobject]@{
        count = $count
        avg = [math]::Round((($sorted | Measure-Object -Average).Average), 2)
        min = [math]::Round($sorted[0], 2)
        max = [math]::Round($sorted[$count - 1], 2)
        p95 = [math]::Round($sorted[$p95Index], 2)
    }
}

function Build-ModeSummary {
    param(
        [object[]]$Rows
    )

    $timedRows = @($Rows | Where-Object { $_.has_timing -and $null -ne $_.timing_ms })
    $segments = @('stt', 'grounding', 'llm', 'postprocess', 'tts', 'total')
    $segmentStats = @{}

    foreach ($segment in $segments) {
        $vals = @()
        foreach ($row in $timedRows) {
            $v = $row.timing_ms.$segment
            if ($v -is [double] -or $v -is [int] -or $v -is [long] -or $v -is [decimal]) {
                $vals += [double]$v
            }
        }
        $segmentStats[$segment] = Get-Stats -Values $vals
    }

    [pscustomobject]@{
        sample_count = $Rows.Count
        timing_available = $timedRows.Count
        elapsed_total = Get-Stats -Values @($Rows | ForEach-Object { [double]$_.elapsed_ms })
        segments = $segmentStats
    }
}

$all = @()

foreach ($mode in @($false, $true)) {
    for ($i = 1; $i -le $SamplesPerMode; $i++) {
        try {
            $row = Invoke-FriendChatSample -Tts $mode -Index $i
            $all += $row
            Write-Host ("[timing] tts={0} sample={1}/{2} elapsed={3}ms has_timing={4}" -f $mode, $i, $SamplesPerMode, $row.elapsed_ms, $row.has_timing)
        } catch {
            $all += [pscustomobject]@{
                tts = $mode
                index = $i
                elapsed_ms = -1
                has_timing = $false
                timing_ms = $null
                error = $_.Exception.Message
            }
            Write-Host ("[timing] tts={0} sample={1}/{2} failed={3}" -f $mode, $i, $SamplesPerMode, $_.Exception.Message)
        }
    }
}

$falseRows = @($all | Where-Object { $_.tts -eq $false })
$trueRows = @($all | Where-Object { $_.tts -eq $true })

$result = [pscustomobject]@{
    base_url = $BaseUrl
    measured_at = (Get-Date).ToUniversalTime().ToString('o')
    samples_per_mode = $SamplesPerMode
    modes = [pscustomobject]@{
        tts_false = Build-ModeSummary -Rows $falseRows
        tts_true = Build-ModeSummary -Rows $trueRows
    }
    raw = $all
}

$outputDir = Split-Path -Parent $OutputPath
if ($outputDir) {
    New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
}
$result | ConvertTo-Json -Depth 8 | Out-File -FilePath $OutputPath -Encoding utf8

Write-Host "[timing] report saved: $OutputPath"
$result | ConvertTo-Json -Depth 6
