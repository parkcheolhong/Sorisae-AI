Param(
    [string]$BaseApiUrl = "http://127.0.0.1:8000",
    [string]$MarketplaceUrl = "http://127.0.0.1:3000/marketplace",
    [string]$AdminUrl3000 = "http://127.0.0.1:3000/admin/login",
    [string]$AdminUrl3005 = "http://127.0.0.1:3005/admin/login",
    [int]$UiTimeoutMs = 20000,
    [switch]$SkipUi,
    [switch]$SkipApi,
    [switch]$CollectAdbLog,
    [bool]$CollectHarOnUiOnlyFailure = $true,
    [string]$AdbFilter = "*:E ReactNativeJS:V chromium:W",
    [string]$OutRoot = "",
    [string]$SlackWebhookUrl = "",
    [string]$TeamsWebhookUrl = "",
    [string]$ArtifactPublicBaseUrl = "",
    [string]$ArtifactPublicRootPath = ""
)

$ErrorActionPreference = "Stop"

function New-Stamp {
    return (Get-Date).ToString("yyyyMMdd_HHmmss")
}

function Ensure-Dir([string]$PathValue) {
    if (-not (Test-Path -LiteralPath $PathValue)) {
        New-Item -ItemType Directory -Path $PathValue | Out-Null
    }
}

function Write-UiOnlyFailureAlert([string]$OutDir, [string]$ResultJsonPath) {
    $alertsDir = Join-Path $PSScriptRoot "ui_api_alerts"
    Ensure-Dir -PathValue $alertsDir

    $stamp = New-Stamp
    $alertFile = Join-Path $alertsDir ("ui_only_failure_" + $stamp + ".txt")
    $latestFile = Join-Path $alertsDir "ui_only_failure_latest.txt"

    $content = @(
        "event=UI_ONLY_FAILURE"
        "time=" + (Get-Date).ToString("o")
        "out_dir=$OutDir"
        "result_json=$ResultJsonPath"
    )

    $content | Out-File -FilePath $alertFile -Encoding utf8
    $content | Out-File -FilePath $latestFile -Encoding utf8

    return [ordered]@{
        alertFile = $alertFile
        latestFile = $latestFile
    }
}

function Resolve-WebhookUrl([string]$ExplicitUrl, [string[]]$EnvNames) {
    if (-not [string]::IsNullOrWhiteSpace($ExplicitUrl)) {
        return $ExplicitUrl
    }
    foreach ($envName in $EnvNames) {
        $value = [string](Get-Item -Path ("Env:" + $envName) -ErrorAction SilentlyContinue).Value
        if (-not [string]::IsNullOrWhiteSpace($value)) {
            return $value
        }
    }
    return ""
}

function Invoke-WebhookJson([string]$Url, [hashtable]$Payload) {
    if ([string]::IsNullOrWhiteSpace($Url)) {
        return [ordered]@{ configured = $false; sent = $false; status = "not_configured" }
    }

    try {
        $json = $Payload | ConvertTo-Json -Depth 10
        $res = Invoke-WebRequest -Uri $Url -Method Post -ContentType "application/json" -Body $json -TimeoutSec 20 -UseBasicParsing
        return [ordered]@{
            configured = $true
            sent = $true
            status = [int]$res.StatusCode
        }
    }
    catch {
        $status = $null
        if ($_.Exception.Response) {
            $status = [int]$_.Exception.Response.StatusCode
        }
        return [ordered]@{
            configured = $true
            sent = $false
            status = $status
            error = $_.Exception.Message
        }
    }
}

function Convert-ToFileUri([string]$PathValue) {
    if ([string]::IsNullOrWhiteSpace($PathValue)) {
        return ""
    }
    try {
        return ([System.Uri]([System.IO.Path]::GetFullPath($PathValue))).AbsoluteUri
    }
    catch {
        return ""
    }
}

function Convert-ToPublicHttpUrl([string]$PathValue, [string]$BaseUrl, [string]$RootPath) {
    if ([string]::IsNullOrWhiteSpace($PathValue)) {
        return ""
    }

    $text = [string]$PathValue
    if ($text -match '^https?://') {
        return $text
    }

    if ([string]::IsNullOrWhiteSpace($BaseUrl) -or [string]::IsNullOrWhiteSpace($RootPath)) {
        return ""
    }

    try {
        $fullPath = [System.IO.Path]::GetFullPath($text)
        $fullRoot = [System.IO.Path]::GetFullPath($RootPath)
        if (-not $fullPath.StartsWith($fullRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
            return ""
        }

        $relative = $fullPath.Substring($fullRoot.Length).TrimStart('\','/') -replace '\\','/'
        if ([string]::IsNullOrWhiteSpace($relative)) {
            return ""
        }
        $escaped = ($relative -split '/') | ForEach-Object { [System.Uri]::EscapeDataString($_) }
        return ($BaseUrl.TrimEnd('/')) + '/' + ($escaped -join '/')
    }
    catch {
        return ""
    }
}

function Resolve-PreferredArtifactUrl([string]$PathValue, [string]$ArtifactBaseUrl, [string]$ArtifactRootPath) {
    $publicUrl = Convert-ToPublicHttpUrl -PathValue $PathValue -BaseUrl $ArtifactBaseUrl -RootPath $ArtifactRootPath
    if (-not [string]::IsNullOrWhiteSpace($publicUrl)) {
        return $publicUrl
    }
    return Convert-ToFileUri -PathValue $PathValue
}

function Test-IsHttpUrl([string]$Value) {
    return (-not [string]::IsNullOrWhiteSpace($Value)) -and ($Value -match '^https?://')
}

function Get-UiSmokeTopSummary([string]$OutDir, [string]$ArtifactBaseUrl = "", [string]$ArtifactRootPath = "") {
    $uiReportPath = Join-Path $OutDir "ui_smoke_report.json"
    if (-not (Test-Path -LiteralPath $uiReportPath)) {
        return [ordered]@{
            reportPath = $uiReportPath
            hasReport = $false
            pageTop3 = @("none")
            requestFailedTop3 = @("none")
            consoleErrorTop3 = @("none")
            screenshotTop3 = @("none")
            screenshotTop3Items = @()
        }
    }

    try {
        $report = Get-Content -LiteralPath $uiReportPath -Raw | ConvertFrom-Json
    }
    catch {
        return [ordered]@{
            reportPath = $uiReportPath
            hasReport = $false
            pageTop3 = @("none")
            requestFailedTop3 = @("none")
            consoleErrorTop3 = @("none")
            screenshotTop3 = @("none")
            screenshotTop3Items = @()
            error = $_.Exception.Message
        }
    }

    $pages = @()
    foreach ($p in @($report.pages)) {
        $pageErrCount = @($p.pageErrors).Count
        $reqFailCount = @($p.requestFailed).Count
        $apiErrCount = @($p.apiHttpErrors).Count
        $consoleErrCount = @($p.consoleErrors).Count
        $score = $pageErrCount + $reqFailCount + $apiErrCount + $consoleErrCount
        if (-not [bool]$p.ok -or $score -gt 0) {
            $pages += [pscustomobject]@{
                label = [string]$p.pageLabel
                score = $score
                breakdown = "pageErr=$pageErrCount reqFail=$reqFailCount apiErr=$apiErrCount consoleErr=$consoleErrCount"
            }
        }
    }

    $pageTop3 = @($pages | Sort-Object score -Descending | Select-Object -First 3 | ForEach-Object {
            "[$($_.label)] score=$($_.score) $($_.breakdown)"
        })
    if ($pageTop3.Count -eq 0) {
        $pageTop3 = @("none")
    }

    $requestRows = @()
    foreach ($p in @($report.pages)) {
        foreach ($r in @($p.requestFailed)) {
            $requestRows += [pscustomobject]@{
                key = ([string]$r.method + " " + [string]$r.url + " " + [string]$r.errorText)
                label = ([string]$p.pageLabel + " :: " + [string]$r.method + " " + [string]$r.url + " (" + [string]$r.errorText + ")")
            }
        }
    }
    $requestTop3 = @($requestRows |
        Group-Object key |
        Sort-Object Count -Descending |
        Select-Object -First 3 |
        ForEach-Object {
            "$($_.Count)x " + [string]$_.Group[0].label
        })
    if ($requestTop3.Count -eq 0) {
        $requestTop3 = @("none")
    }

    $consoleRows = @()
    foreach ($p in @($report.pages)) {
        foreach ($c in @($p.consoleErrors)) {
            $consoleRows += [pscustomobject]@{
                key = [string]$c
                label = ([string]$p.pageLabel + " :: " + [string]$c)
            }
        }
    }
    $consoleTop3 = @($consoleRows |
        Group-Object key |
        Sort-Object Count -Descending |
        Select-Object -First 3 |
        ForEach-Object {
            "$($_.Count)x " + [string]$_.Group[0].label
        })
    if ($consoleTop3.Count -eq 0) {
        $consoleTop3 = @("none")
    }

    $screenshotTop3Items = @($pages | Sort-Object score -Descending | Select-Object -First 3 | ForEach-Object {
            $currentLabel = [string]$_.label
            $matched = @($report.pages | Where-Object { [string]$_.pageLabel -eq $currentLabel })
            if ($matched.Count -gt 0 -and -not [string]::IsNullOrWhiteSpace([string]$matched[0].screenshot)) {
                [pscustomobject]@{
                    pageLabel = $currentLabel
                    screenshotPath = [string]$matched[0].screenshot
                    screenshotUrl = (Convert-ToPublicHttpUrl -PathValue ([string]$matched[0].screenshot) -BaseUrl $ArtifactBaseUrl -RootPath $ArtifactRootPath)
                }
            }
        } | Where-Object { $_ -ne $null })
    $screenshotTop3 = @($screenshotTop3Items | ForEach-Object {
            "[$([string]$_.pageLabel)] $([string]$_.screenshotPath)"
        })
    if ($screenshotTop3.Count -eq 0) {
        $screenshotTop3 = @("none")
        $screenshotTop3Items = @()
    }

    return [ordered]@{
        reportPath = $uiReportPath
        reportUrl = (Resolve-PreferredArtifactUrl -PathValue $uiReportPath -ArtifactBaseUrl $ArtifactBaseUrl -ArtifactRootPath $ArtifactRootPath)
        hasReport = $true
        pageTop3 = $pageTop3
        requestFailedTop3 = $requestTop3
        consoleErrorTop3 = $consoleTop3
        screenshotTop3 = $screenshotTop3
        screenshotTop3Items = $screenshotTop3Items
    }
}

function Send-UiOnlyFailureNotifications([string]$OutDir, [string]$ResultJsonPath, [string]$HarDir, [hashtable]$UiTopSummary, [string]$ArtifactBaseUrl, [string]$ArtifactRootPath, [string]$SlackUrl, [string]$TeamsUrl) {
    $timeIso = (Get-Date).ToString("o")
    $title = "[SoriSae] UI_ONLY_FAILURE detected"
    $pageLines = @($UiTopSummary.pageTop3)
    $requestLines = @($UiTopSummary.requestFailedTop3)
    $consoleLines = @($UiTopSummary.consoleErrorTop3)
    $screenshotLines = @($UiTopSummary.screenshotTop3)
    $screenshotItems = @($UiTopSummary.screenshotTop3Items)
    $resultJsonUri = Resolve-PreferredArtifactUrl -PathValue $ResultJsonPath -ArtifactBaseUrl $ArtifactBaseUrl -ArtifactRootPath $ArtifactRootPath
    $harDirUri = Resolve-PreferredArtifactUrl -PathValue $HarDir -ArtifactBaseUrl $ArtifactBaseUrl -ArtifactRootPath $ArtifactRootPath
    $uiReportUri = [string]$UiTopSummary.reportUrl

    $resultJsonButtonLabel = if (Test-IsHttpUrl $resultJsonUri) { "Open public result" } else { "Open local result" }
    $harDirButtonLabel = if (Test-IsHttpUrl $harDirUri) { "Open public HAR" } else { "Open local HAR" }
    $uiReportButtonLabel = if (Test-IsHttpUrl $uiReportUri) { "Open public report" } else { "Open local report" }

    $slackFields = @(
        "*Time*`n$timeIso",
        "*Out Dir*`n$OutDir",
        "*HAR Dir*`n$HarDir",
        "*Result JSON*`n$ResultJsonPath",
        "*Page Top3*`n" + ($pageLines -join "`n"),
        "*RequestFailed Top3*`n" + ($requestLines -join "`n"),
        "*ConsoleError Top3*`n" + ($consoleLines -join "`n"),
        "*Failed Page Screenshot Top3*`n" + ($screenshotLines -join "`n")
    )

    $slackBlocks = @(
        @{ type = "header"; text = @{ type = "plain_text"; text = $title } },
        @{ type = "section"; fields = @($slackFields | ForEach-Object { @{ type = "mrkdwn"; text = $_ } }) },
        @{ 
            type = "actions"
            elements = @(
                @{ type = "button"; text = @{ type = "plain_text"; text = $resultJsonButtonLabel }; url = $resultJsonUri; value = "result_json" },
                @{ type = "button"; text = @{ type = "plain_text"; text = $harDirButtonLabel }; url = $harDirUri; value = "har_dir" },
                @{ type = "button"; text = @{ type = "plain_text"; text = $uiReportButtonLabel }; url = $uiReportUri; value = "ui_report" }
            )
        }
    )

    foreach ($item in @($screenshotItems | Select-Object -First 3)) {
        $slackImageUrl = [string]$item.screenshotUrl
        if ([string]::IsNullOrWhiteSpace($slackImageUrl)) {
            continue
        }
        $slackBlocks += @{
            type = "image"
            image_url = $slackImageUrl
            alt_text = ([string]$item.pageLabel + " screenshot")
            title = @{ type = "plain_text"; text = ([string]$item.pageLabel + " screenshot") }
        }
    }

    $slackPayload = @{
        text = $title
        blocks = $slackBlocks
    }

    $teamsThumbnailBlocks = @()
    foreach ($item in @($screenshotItems | Select-Object -First 3)) {
        $publicUrl = [string]$item.screenshotUrl
        if ([string]::IsNullOrWhiteSpace($publicUrl)) {
            continue
        }
        $teamsThumbnailBlocks += @{
            type = "TextBlock"
            text = ("Screenshot Preview: " + [string]$item.pageLabel)
            weight = "Bolder"
            wrap = $true
        }
        $teamsThumbnailBlocks += @{
            type = "Image"
            url = $publicUrl
            altText = ([string]$item.pageLabel + " screenshot")
            size = "Medium"
        }
    }

    $teamsBody = @(
        @{ 
            type = "Container"
            style = "attention"
            bleed = $true
            items = @(
                @{ type = "TextBlock"; text = "STATUS: UI_ONLY_FAILURE"; weight = "Bolder"; size = "Medium"; color = "Light"; wrap = $true }
            )
        },
        @{ type = "TextBlock"; text = $title; weight = "Bolder"; size = "Large"; wrap = $true },
        @{ type = "FactSet"; facts = @(
                @{ title = "Time"; value = $timeIso },
                @{ title = "Out Dir"; value = $OutDir },
                @{ title = "HAR Dir"; value = $HarDir },
                @{ title = "Result JSON"; value = $ResultJsonPath }
            )
        },
        @{ type = "TextBlock"; text = "Public Links"; weight = "Bolder"; wrap = $true },
        @{ type = "FactSet"; facts = @(
                @{ title = "result_json URL"; value = $resultJsonUri },
                @{ title = "ui_report URL"; value = $uiReportUri }
            )
        },
        @{ type = "TextBlock"; text = "Page Top3"; weight = "Bolder"; wrap = $true },
        @{ type = "TextBlock"; text = ($pageLines -join "`n"); wrap = $true },
        @{ type = "TextBlock"; text = "RequestFailed Top3"; weight = "Bolder"; wrap = $true },
        @{ type = "TextBlock"; text = ($requestLines -join "`n"); wrap = $true },
        @{ type = "TextBlock"; text = "ConsoleError Top3"; weight = "Bolder"; wrap = $true },
        @{ type = "TextBlock"; text = ($consoleLines -join "`n"); wrap = $true },
        @{ type = "TextBlock"; text = "Failed Page Screenshot Top3"; weight = "Bolder"; wrap = $true },
        @{ 
            type = "ColumnSet"
            columns = @(
                @{
                    type = "Column"
                    width = "stretch"
                    items = @(
                        @{ type = "TextBlock"; text = "Page"; weight = "Bolder"; wrap = $true },
                        @{ type = "TextBlock"; text = ((@($screenshotItems | ForEach-Object { [string]$_.pageLabel }) -join "`n")); wrap = $true }
                    )
                },
                @{
                    type = "Column"
                    width = 2
                    items = @(
                        @{ type = "TextBlock"; text = "Screenshot Path"; weight = "Bolder"; wrap = $true },
                        @{ type = "TextBlock"; text = ((@($screenshotItems | ForEach-Object { [string]$_.screenshotPath }) -join "`n")); wrap = $true }
                    )
                }
            )
        }
    )
    if ($teamsThumbnailBlocks.Count -gt 0) {
        $teamsBody += $teamsThumbnailBlocks
    }

    $teamsPayload = @{
        type = "message"
        attachments = @(
            @{
                contentType = "application/vnd.microsoft.card.adaptive"
                content = @{
                    '$schema' = "http://adaptivecards.io/schemas/adaptive-card.json"
                    type = "AdaptiveCard"
                    version = "1.4"
                    body = $teamsBody
                    actions = @(
                        @{ type = "Action.OpenUrl"; title = $resultJsonButtonLabel; url = $resultJsonUri },
                        @{ type = "Action.OpenUrl"; title = $harDirButtonLabel; url = $harDirUri },
                        @{ type = "Action.OpenUrl"; title = $uiReportButtonLabel; url = $uiReportUri }
                    )
                    msteams = @{ width = "Full" }
                }
            }
        )
    }

    return [ordered]@{
        slack = Invoke-WebhookJson -Url $SlackUrl -Payload $slackPayload
        teams = Invoke-WebhookJson -Url $TeamsUrl -Payload $teamsPayload
    }
}

function Invoke-AdminSorisaeFailurePush([string]$ResultJsonPath) {
    $repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
    $helperPath = Join-Path $PSScriptRoot "notify_admin_sorisae_failure.py"
    $backendContainerName = "devanalysis114-backend"
    if (-not (Test-Path -LiteralPath $helperPath)) {
        return [ordered]@{
            attempted = $false
            success = $false
            skipped_reason = "helper_not_found"
        }
    }

    $dockerCmd = Get-Command docker -ErrorAction SilentlyContinue
    if ($dockerCmd) {
        $containerRunning = $false
        try {
            $running = (& docker ps --filter "name=$backendContainerName" --format "{{.Names}}" 2>$null) -join "`n"
            $containerRunning = $running -split "`n" | Where-Object { $_.Trim() -eq $backendContainerName } | ForEach-Object { $true } | Select-Object -First 1
        }
        catch {
            $containerRunning = $false
        }

        if ($containerRunning) {
            $resolvedResultPath = [System.IO.Path]::GetFullPath($ResultJsonPath)
            $resolvedRepoRoot = [System.IO.Path]::GetFullPath($repoRoot)
            $containerResultPath = $resolvedResultPath
            if ($resolvedResultPath.StartsWith($resolvedRepoRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
                $relative = $resolvedResultPath.Substring($resolvedRepoRoot.Length).TrimStart('\', '/')
                $containerResultPath = "/app/" + ($relative -replace "\\", "/")
            }

            $containerOutput = & docker exec $backendContainerName python /app/scripts/notify_admin_sorisae_failure.py --result-json-path $containerResultPath 2>&1
            if ($LASTEXITCODE -eq 0) {
                try {
                    $parsed = (($containerOutput | Out-String).Trim() | ConvertFrom-Json)
                    if ($null -ne $parsed) {
                        return $parsed
                    }
                }
                catch {
                    return [ordered]@{
                        attempted = $false
                        success = $false
                        skipped_reason = "container_helper_output_parse_failed"
                        error = ($containerOutput | Out-String).Trim()
                    }
                }
            }
            else {
                return [ordered]@{
                    attempted = $false
                    success = $false
                    skipped_reason = "container_helper_failed"
                    error = ($containerOutput | Out-String).Trim()
                }
            }
        }
    }

    $pythonCandidates = @(
        (Join-Path $repoRoot ".venv\Scripts\python.exe"),
        "python"
    )
    $pythonExe = $null
    foreach ($candidate in $pythonCandidates) {
        if ($candidate -eq "python") {
            $cmd = Get-Command python -ErrorAction SilentlyContinue
            if ($cmd) {
                $pythonExe = $cmd.Source
                break
            }
        }
        elseif (Test-Path -LiteralPath $candidate) {
            $pythonExe = $candidate
            break
        }
    }

    if ([string]::IsNullOrWhiteSpace($pythonExe)) {
        return [ordered]@{
            attempted = $false
            success = $false
            skipped_reason = "python_not_found"
        }
    }

    $output = & $pythonExe $helperPath --result-json-path $ResultJsonPath 2>&1
    if ($LASTEXITCODE -ne 0) {
        return [ordered]@{
            attempted = $false
            success = $false
            skipped_reason = "helper_failed"
            error = ($output | Out-String).Trim()
        }
    }

    try {
        $parsed = (($output | Out-String).Trim() | ConvertFrom-Json)
        if ($null -eq $parsed) {
            throw "empty_helper_output"
        }
        return $parsed
    }
    catch {
        return [ordered]@{
            attempted = $false
            success = $false
            skipped_reason = "helper_output_parse_failed"
            error = ($output | Out-String).Trim()
        }
    }
}

function Probe-Api([string]$BaseUrl, [string]$OutDir) {
    $apiResult = [ordered]@{
        baseUrl   = $BaseUrl
        startedAt = (Get-Date).ToString("o")
        probes    = @()
        summary   = [ordered]@{
            total = 0
            ok    = 0
            fail  = 0
        }
    }

    $friendPayload = @{
        transcript   = "오늘 상태 점검 스모크"
        language     = "ko"
        tts          = $false
        region_hint  = "Seoul"
        country_code = "KR"
        latitude     = 37.5665
        longitude    = 126.9780
        accuracy_m   = 20
        conversation = @()
        web_search   = $false
    }

    $facePayload = @{
        transcript = "안녕 스모크"
        from_lang  = "ko"
        to_lang    = "en"
        mode       = "designated"
        tts        = $false
        device_tts = $true
    }

    $targets = @(
        @{
            name    = "friend_chat"
            path    = "/api/llm/voice/friend-chat"
            payload = $friendPayload
        },
        @{
            name    = "face_translate"
            path    = "/api/llm/face/voice-translate"
            payload = $facePayload
        }
    )

    $okCount = 0
    $failCount = 0

    foreach ($t in $targets) {
        $url = ($BaseUrl.TrimEnd("/")) + $t.path
        $entry = [ordered]@{
            name         = $t.name
            url          = $url
            ok           = $false
            status       = $null
            elapsedMs    = 0
            attempts     = 0
            error        = ""
            responseBody = ""
        }

        $elapsed = 0.0
        for ($attempt = 1; $attempt -le 2; $attempt++) {
            $entry.attempts = $attempt
            $payload = $t.payload.Clone()
            if ($attempt -gt 1 -and $payload.ContainsKey("transcript")) {
                $payload.transcript = "smoke fallback"
            }

            $body = $payload | ConvertTo-Json -Depth 8
            $sw = [System.Diagnostics.Stopwatch]::StartNew()
            try {
                $res = Invoke-WebRequest -Uri $url -Method Post -ContentType "application/json" -Body $body -TimeoutSec 30 -UseBasicParsing
                $sw.Stop()
                $elapsed += $sw.Elapsed.TotalMilliseconds
                $entry.status = [int]$res.StatusCode
                $entry.ok = ($res.StatusCode -ge 200 -and $res.StatusCode -lt 300)
                $entry.responseBody = [string]$res.Content
                $entry.error = ""
                if ($entry.ok) {
                    break
                }
            }
            catch {
                $sw.Stop()
                $elapsed += $sw.Elapsed.TotalMilliseconds
                if ($_.Exception.Response) {
                    $entry.status = [int]$_.Exception.Response.StatusCode
                    try {
                        $sr = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
                        $entry.responseBody = $sr.ReadToEnd()
                    }
                    catch {
                        $entry.responseBody = [string]$_.ErrorDetails.Message
                    }
                }
                else {
                    $entry.responseBody = [string]$_.ErrorDetails.Message
                }
                $entry.ok = $false
                $entry.error = $_.Exception.Message
            }
        }

        $entry.elapsedMs = [math]::Round($elapsed, 1)
        $apiResult.probes += $entry
        if ($entry.ok) {
            $okCount += 1
        }
        else {
            $failCount += 1
        }
    }

    $apiResult.summary.total = $apiResult.probes.Count
    $apiResult.summary.ok = $okCount
    $apiResult.summary.fail = $failCount

    $jsonPath = Join-Path $OutDir "api_probe_report.json"
    $summaryPath = Join-Path $OutDir "api_probe_summary.txt"
    $apiResult | ConvertTo-Json -Depth 10 | Out-File -FilePath $jsonPath -Encoding utf8

    @(
        "api_total=$($apiResult.summary.total)"
        "api_ok=$($apiResult.summary.ok)"
        "api_fail=$($apiResult.summary.fail)"
        "api_report=$jsonPath"
    ) | Out-File -FilePath $summaryPath -Encoding utf8

    return $apiResult
}

function Probe-Ui([string]$OutDir, [string]$Marketplace, [string]$Admin3000, [string]$Admin3005, [int]$TimeoutMs, [string]$HarDir = "") {
    $scriptPath = Join-Path $PSScriptRoot "ui_api_failure_split_smoke.mjs"
    if (-not (Test-Path -LiteralPath $scriptPath)) {
        throw "UI smoke script not found: $scriptPath"
    }

    $cmd = @(
        "node"
        ('"' + $scriptPath + '"')
        "--out-dir"
        ('"' + $OutDir + '"')
        "--marketplace-url"
        ('"' + $Marketplace + '"')
        "--admin-url-3000"
        ('"' + $Admin3000 + '"')
        "--admin-url-3005"
        ('"' + $Admin3005 + '"')
        "--timeout-ms"
        "$TimeoutMs"
    ) -join " "

    if (-not [string]::IsNullOrWhiteSpace($HarDir)) {
        $cmd = $cmd + " --har-dir " + ('"' + $HarDir + '"')
    }

    cmd /c $cmd | Out-Host
    return $LASTEXITCODE
}

function Collect-Adb([string]$OutDir, [string]$FilterSpec) {
    try {
        $adb = Get-Command adb -ErrorAction SilentlyContinue
        if (-not $adb) {
            return [ordered]@{ collected = $false; reason = "adb_not_found" }
        }

        $devicesRaw = (& adb devices) 2>$null
        $deviceRows = @($devicesRaw | Select-Object -Skip 1 | Where-Object { $_ -match "\tdevice$" })
        if ($deviceRows.Count -lt 1) {
            return [ordered]@{ collected = $false; reason = "no_ready_device" }
        }
        $deviceId = (($deviceRows[0] -split "\t")[0]).Trim()
        if ([string]::IsNullOrWhiteSpace($deviceId)) {
            return [ordered]@{ collected = $false; reason = "no_ready_device" }
        }

        $outPath = Join-Path $OutDir "mobile_adb_logcat.txt"
        if ([string]::IsNullOrWhiteSpace($FilterSpec)) {
            & adb -s $deviceId logcat -d *>&1 | Out-File -FilePath $outPath -Encoding utf8
        }
        else {
            cmd /c "adb -s $deviceId logcat -d $FilterSpec" *>&1 | Out-File -FilePath $outPath -Encoding utf8
        }

        return [ordered]@{ collected = $true; reason = "ok"; path = $outPath; device = $deviceId }
    }
    catch {
        return [ordered]@{ collected = $false; reason = "adb_error"; error = $_.Exception.Message }
    }
}

$stamp = New-Stamp
if ([string]::IsNullOrWhiteSpace($OutRoot)) {
    $repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
    $OutRoot = Join-Path (Join-Path $repoRoot "backend\tmp") ("ui_api_failure_split_" + $stamp)
}
Ensure-Dir -PathValue $OutRoot

$resolvedArtifactPublicBaseUrl = Resolve-WebhookUrl -ExplicitUrl $ArtifactPublicBaseUrl -EnvNames @("ARTIFACT_PUBLIC_BASE_URL", "SORISAE_ARTIFACT_PUBLIC_BASE_URL")
$resolvedArtifactPublicRootPath = Resolve-WebhookUrl -ExplicitUrl $ArtifactPublicRootPath -EnvNames @("ARTIFACT_PUBLIC_ROOT_PATH", "SORISAE_ARTIFACT_PUBLIC_ROOT_PATH")
if ([string]::IsNullOrWhiteSpace($resolvedArtifactPublicRootPath)) {
    $resolvedArtifactPublicRootPath = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

$result = [ordered]@{
    startedAt  = (Get-Date).ToString("o")
    outDir     = $OutRoot
    api        = $null
    uiExitCode = $null
    uiHarExitCode = $null
    uiHarDir = ""
    adb        = $null
    alert      = $null
    notification = $null
}

if (-not $SkipApi) {
    Write-Host "[smoke] api probe..."
    $result.api = Probe-Api -BaseUrl $BaseApiUrl -OutDir $OutRoot
}

if (-not $SkipUi) {
    Write-Host "[smoke] ui probe (playwright)..."
    $result.uiExitCode = Probe-Ui -OutDir $OutRoot -Marketplace $MarketplaceUrl -Admin3000 $AdminUrl3000 -Admin3005 $AdminUrl3005 -TimeoutMs $UiTimeoutMs -HarDir ""
}

if ($CollectAdbLog) {
    Write-Host "[smoke] adb log collection..."
    $result.adb = Collect-Adb -OutDir $OutRoot -FilterSpec $AdbFilter
}

$resultPath = Join-Path $OutRoot "smoke_result.json"
$result | ConvertTo-Json -Depth 10 | Out-File -FilePath $resultPath -Encoding utf8

$apiFail = 0
if ($result.api -ne $null) {
    $apiFail = [int]$result.api.summary.fail
}
$uiFail = 0
if ($result.uiExitCode -ne $null -and [int]$result.uiExitCode -ne 0) {
    $uiFail = 1
}

$classification = "unknown"
if ($apiFail -eq 0 -and $uiFail -eq 1) {
    $classification = "UI_ONLY_FAILURE"
}
elseif ($apiFail -gt 0 -and $uiFail -eq 0) {
    $classification = "API_ONLY_FAILURE"
}
elseif ($apiFail -gt 0 -and $uiFail -eq 1) {
    $classification = "BOTH_FAIL"
}
elseif ($apiFail -eq 0 -and $uiFail -eq 0) {
    $classification = "ALL_PASS"
}

$summary = @(
    "out_dir=$OutRoot"
    "classification=$classification"
    "api_fail=$apiFail"
    "ui_fail=$uiFail"
    "result_json=$resultPath"
)
$summaryPath = Join-Path $OutRoot "smoke_summary.txt"
$summary | Out-File -FilePath $summaryPath -Encoding utf8
$summary | ForEach-Object { Write-Host $_ }

$result.classification = $classification
$result.apiFail = $apiFail
$result.uiFail = $uiFail
$result.summaryPath = $summaryPath
$result.resultJsonPath = $resultPath
$result | ConvertTo-Json -Depth 10 | Out-File -FilePath $resultPath -Encoding utf8

if ($classification -eq "UI_ONLY_FAILURE") {
    $result.alert = Write-UiOnlyFailureAlert -OutDir $OutRoot -ResultJsonPath $resultPath
    $result | ConvertTo-Json -Depth 10 | Out-File -FilePath $resultPath -Encoding utf8

    if ($CollectHarOnUiOnlyFailure -and -not $SkipUi) {
        $harDir = Join-Path $OutRoot "har_capture"
        Ensure-Dir -PathValue $harDir
        Write-Host "[smoke] UI_ONLY_FAILURE detected, collecting HAR..."
        $result.uiHarDir = $harDir
        $result.uiHarExitCode = Probe-Ui -OutDir $OutRoot -Marketplace $MarketplaceUrl -Admin3000 $AdminUrl3000 -Admin3005 $AdminUrl3005 -TimeoutMs $UiTimeoutMs -HarDir $harDir
        $result | ConvertTo-Json -Depth 10 | Out-File -FilePath $resultPath -Encoding utf8
    }

    $resolvedSlackWebhook = Resolve-WebhookUrl -ExplicitUrl $SlackWebhookUrl -EnvNames @("SLACK_WEBHOOK_URL", "SORISAE_SLACK_WEBHOOK_URL")
    $resolvedTeamsWebhook = Resolve-WebhookUrl -ExplicitUrl $TeamsWebhookUrl -EnvNames @("TEAMS_WEBHOOK_URL", "SORISAE_TEAMS_WEBHOOK_URL")
    $uiTopSummary = Get-UiSmokeTopSummary -OutDir $OutRoot -ArtifactBaseUrl $resolvedArtifactPublicBaseUrl -ArtifactRootPath $resolvedArtifactPublicRootPath
    $result.uiTopSummary = $uiTopSummary
    $result.notification = Send-UiOnlyFailureNotifications -OutDir $OutRoot -ResultJsonPath $resultPath -HarDir $result.uiHarDir -UiTopSummary $uiTopSummary -ArtifactBaseUrl $resolvedArtifactPublicBaseUrl -ArtifactRootPath $resolvedArtifactPublicRootPath -SlackUrl $resolvedSlackWebhook -TeamsUrl $resolvedTeamsWebhook
    $result | ConvertTo-Json -Depth 10 | Out-File -FilePath $resultPath -Encoding utf8

    $slackSent = [bool]($result.notification.slack.sent)
    $teamsSent = [bool]($result.notification.teams.sent)
    $result.adminPush = Invoke-AdminSorisaeFailurePush -ResultJsonPath $resultPath
    $result | ConvertTo-Json -Depth 10 | Out-File -FilePath $resultPath -Encoding utf8

    Write-Host "slack_notified=$slackSent"
    Write-Host "teams_notified=$teamsSent"
    Write-Host "admin_push_success=$([bool]($result.adminPush.success))"

    exit 3
}
if ($classification -eq "API_ONLY_FAILURE") {
    exit 4
}
if ($classification -eq "BOTH_FAIL") {
    $result.uiTopSummary = Get-UiSmokeTopSummary -OutDir $OutRoot -ArtifactBaseUrl $resolvedArtifactPublicBaseUrl -ArtifactRootPath $resolvedArtifactPublicRootPath
    $result | ConvertTo-Json -Depth 10 | Out-File -FilePath $resultPath -Encoding utf8
    $result.adminPush = Invoke-AdminSorisaeFailurePush -ResultJsonPath $resultPath
    $result | ConvertTo-Json -Depth 10 | Out-File -FilePath $resultPath -Encoding utf8
    Write-Host "admin_push_success=$([bool]($result.adminPush.success))"
    exit 5
}
exit 0
