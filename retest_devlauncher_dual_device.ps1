param(
    [string[]]$Devices = @("R83W70QY11H", "172.30.1.19:5555"),
    [string]$PackageName = "com.parkcheolhong.worldlinco",
    [int]$MetroPort = 8081,
    [string]$ProjectSlug = "nadotongryoksa",
    [string[]]$ForceToolsOnlyBlankDevices = @(),
    [switch]$ForceToolsOnlyBlankAll
)

$ErrorActionPreference = "Stop"

function Assert-Command {
    param([string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command not found: $Name"
    }
}

function Get-Classification {
    param(
        [string[]]$UiTokens,
        [string]$FilteredLogText,
        [string]$ActivityText
    )

    $CombinedText = (($UiTokens -join "`n") + "`n" + $FilteredLogText + "`n" + $ActivityText)

    if ($CombinedText -match "DevLauncherManifestParser|Failed to open app") {
        return "Manifest parser"
    }

    if ($CombinedText -match "Unable to resolve host|ERR_NAME_NOT_RESOLVED|Failed to connect|Connection refused|No route to host") {
        return "URL resolver/network"
    }

    if ($CombinedText -match "runtimeVersion|expo-updates|incompatible update|embedded manifest") {
        return "Runtime metadata"
    }

    if ($UiTokens -contains "continue") {
        return "Dev menu (continue visible)"
    }

    if ($UiTokens.Count -eq 1 -and $UiTokens[0] -eq "tools") {
        return "Tools-only blank"
    }

    if ($UiTokens -contains "worldlinco") {
        return "App/DevLauncher visible"
    }

    return "Unknown"
}

function Get-XmlBoundsCenter {
    param(
        [string]$Bounds
    )

    if ($Bounds -notmatch '^\[(\d+),(\d+)\]\[(\d+),(\d+)\]$') {
        return $null
    }

    return [pscustomobject]@{
        x = [int](([int]$matches[1] + [int]$matches[3]) / 2)
        y = [int](([int]$matches[2] + [int]$matches[4]) / 2)
    }
}

function Get-UiSnapshotFromXml {
    param([string]$XmlPath)

    try {
        [xml]$doc = Get-Content -Raw $XmlPath
        $nodes = $doc.SelectNodes("//node")
        $tokens = New-Object System.Collections.Generic.List[string]
        $texts = New-Object System.Collections.Generic.List[string]
        $desc = New-Object System.Collections.Generic.List[string]
        $resourceIds = New-Object System.Collections.Generic.List[string]

        foreach ($n in $nodes) {
            $t = [string]$n.GetAttribute("text")
            $d = [string]$n.GetAttribute("content-desc")
            $r = [string]$n.GetAttribute("resource-id")

            if ($t -and $t.Trim().Length -gt 0) {
                $v = $t.Trim()
                $texts.Add($v)
                $tokens.Add($v.ToLowerInvariant())
            }

            if ($d -and $d.Trim().Length -gt 0) {
                $v = $d.Trim()
                $desc.Add($v)
                $tokens.Add($v.ToLowerInvariant())
            }

            if ($r -and $r.Trim().Length -gt 0) {
                $v = $r.Trim()
                $resourceIds.Add($v)
                $tail = ($v -split '/|:')[-1]
                if ($tail) {
                    $tokens.Add($tail.ToLowerInvariant())
                }
            }
        }

        $rootNode = $doc.SelectSingleNode("/hierarchy/node")
        $rootBounds = if ($rootNode) { [string]$rootNode.GetAttribute("bounds") } else { "" }
        $rootCenter = Get-XmlBoundsCenter -Bounds $rootBounds

        return [pscustomobject]@{
            tokens      = $tokens | Select-Object -Unique
            texts       = $texts | Select-Object -Unique
            contentDesc = $desc | Select-Object -Unique
            resourceIds = $resourceIds | Select-Object -Unique
            nodeCount   = $nodes.Count
            rootBounds  = $rootBounds
            rootCenter  = $rootCenter
        }
    }
    catch {
        return [pscustomobject]@{
            tokens      = @()
            texts       = @()
            contentDesc = @()
            resourceIds = @()
            nodeCount   = 0
            rootBounds  = ""
            rootCenter  = $null
        }
    }
}

function Get-UiTapCandidates {
    param(
        [string]$XmlPath,
        [string[]]$Labels
    )

    $candidates = New-Object System.Collections.Generic.List[object]

    try {
        [xml]$doc = Get-Content -Raw $XmlPath
        $nodes = $doc.SelectNodes("//node")
        foreach ($n in $nodes) {
            $text = ([string]$n.GetAttribute("text")).Trim()
            $desc = ([string]$n.GetAttribute("content-desc")).Trim()
            $rid = ([string]$n.GetAttribute("resource-id")).Trim()
            $bounds = [string]$n.GetAttribute("bounds")
            $center = Get-XmlBoundsCenter -Bounds $bounds
            if (-not $center) {
                continue
            }

            $score = -1
            foreach ($label in $Labels) {
                $l = $label.ToLowerInvariant()
                if ($text -and $text.ToLowerInvariant() -eq $l) {
                    $score = [Math]::Max($score, 100)
                }
                elseif ($desc -and $desc.ToLowerInvariant() -eq $l) {
                    $score = [Math]::Max($score, 95)
                }
                elseif ($rid -and $rid.ToLowerInvariant().Contains($l)) {
                    $score = [Math]::Max($score, 80)
                }
            }

            if ($score -ge 0) {
                $candidates.Add([pscustomobject]@{
                        x      = $center.x
                        y      = $center.y
                        score  = $score
                        text   = $text
                        desc   = $desc
                        rid    = $rid
                        source = "ui-node"
                    }) | Out-Null
            }
        }

        $snap = Get-UiSnapshotFromXml -XmlPath $XmlPath
        if ($snap.rootCenter) {
            $candidates.Add([pscustomobject]@{
                    x      = $snap.rootCenter.x
                    y      = $snap.rootCenter.y
                    score  = 40
                    text   = ""
                    desc   = ""
                    rid    = ""
                    source = "fallback-center"
                }) | Out-Null
            $candidates.Add([pscustomobject]@{
                    x      = $snap.rootCenter.x
                    y      = [int]($snap.rootCenter.y * 0.70)
                    score  = 35
                    text   = ""
                    desc   = ""
                    rid    = ""
                    source = "fallback-mid-lower"
                }) | Out-Null
            $candidates.Add([pscustomobject]@{
                    x      = [int]($snap.rootCenter.x * 1.50)
                    y      = $snap.rootCenter.y
                    score  = 30
                    text   = ""
                    desc   = ""
                    rid    = ""
                    source = "fallback-right"
                }) | Out-Null
        }
    }
    catch {
        return @()
    }

    return $candidates |
    Sort-Object -Property score -Descending |
    Group-Object -Property { "{0},{1}" -f $_.x, $_.y } |
    ForEach-Object { $_.Group[0] } |
    Select-Object -First 6
}

function Get-ActivityTopLine {
    param([string]$ActivityText)

    if (-not $ActivityText) {
        return ""
    }

    $patterns = @(
        'mResumedActivity:.*',
        'topResumedActivity=.*',
        'ResumedActivity:.*',
        'ACTIVITY .*'
    )

    foreach ($p in $patterns) {
        $m = [regex]::Match($ActivityText, $p)
        if ($m.Success) {
            return $m.Value.Trim()
        }
    }

    return ""
}

function Get-AutoTags {
    param(
        [string]$Classification,
        [bool]$PrimaryTapped,
        [bool]$SecondaryAttempted,
        [string]$FilteredLogText,
        [string]$ActivityTop,
        [string[]]$PreTokens,
        [string[]]$PostTokens
    )

    $tags = New-Object System.Collections.Generic.List[string]

    if ($PrimaryTapped) { $tags.Add("action.primary_label_tap") | Out-Null }
    if ($SecondaryAttempted) { $tags.Add("action.secondary_candidates") | Out-Null }

    if ($Classification -eq "Tools-only blank") {
        $tags.Add("ui.tools_only_blank") | Out-Null
    }
    elseif ($Classification -eq "App/DevLauncher visible") {
        $tags.Add("ui.app_or_devlauncher_visible") | Out-Null
    }

    if ($ActivityTop -match "DevLauncherErrorActivity") {
        $tags.Add("activity.devlauncher_error") | Out-Null
    }

    if ($FilteredLogText -notmatch "DevLauncherManifestParser|UnexpectedServerData|No returned query result") {
        $tags.Add("signal.no_legacy_parser_signature") | Out-Null
    }

    $added = @($PostTokens | Where-Object { $_ -notin $PreTokens })
    if ($added.Count -gt 0) {
        $tags.Add("ui.changed_after_actions") | Out-Null
    }
    else {
        $tags.Add("ui.no_change_after_actions") | Out-Null
    }

    return $tags | Select-Object -Unique
}
Assert-Command -Name adb

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$captureRoot = Join-Path $repoRoot "tmp/device-captures/devlauncher-retest-$timestamp"
New-Item -ItemType Directory -Force -Path $captureRoot | Out-Null

$statusUrl = "http://127.0.0.1:$MetroPort/status"
$metroStatus = "unreachable"
for ($i = 0; $i -lt 5; $i++) {
    try {
        $resp = Invoke-WebRequest -Uri $statusUrl -UseBasicParsing -TimeoutSec 3
        $rawStatus = ($resp.Content | Out-String).Trim()

        $lines = $rawStatus -split "`r?`n" | Where-Object { $_ -ne "" }
        if ($lines.Count -gt 0 -and ($lines | Where-Object { $_ -notmatch '^[0-9]+$' }).Count -eq 0) {
            $chars = $lines | ForEach-Object { [char][int]$_ }
            $metroStatus = -join $chars
        }
        else {
            $metroStatus = $rawStatus
        }
        break
    }
    catch {
        if ($i -lt 4) {
            Start-Sleep -Seconds 1
        }
    }
}

$deepLink = "exp+${ProjectSlug}://expo-development-client/?url=http%3A%2F%2F127.0.0.1%3A$MetroPort"
$results = @()

foreach ($device in $Devices) {
    $forceToolsOnlyBlank = $ForceToolsOnlyBlankAll -or ($ForceToolsOnlyBlankDevices -contains $device)
    $safeId = ($device -replace "[^A-Za-z0-9_.-]", "_")
    $deviceDir = Join-Path $captureRoot $safeId
    New-Item -ItemType Directory -Force -Path $deviceDir | Out-Null

    adb -s $device logcat -c | Out-Null
    adb -s $device reverse --remove-all | Out-Null
    adb -s $device reverse "tcp:$MetroPort" "tcp:$MetroPort" | Out-Null

    $startOut = adb -s $device shell am start -W -a android.intent.action.VIEW -d $deepLink $PackageName
    $startOut | Out-File -FilePath (Join-Path $deviceDir "start_intent.txt") -Encoding utf8

    Start-Sleep -Seconds 2

    $preXmlRemote = "/sdcard/Download/devlauncher_retest_${safeId}_pre.xml"
    $preXmlLocal = Join-Path $deviceDir "ui_pre.xml"
    adb -s $device shell uiautomator dump $preXmlRemote | Out-Null
    adb -s $device pull $preXmlRemote $preXmlLocal | Out-Null
    adb -s $device shell rm $preXmlRemote | Out-Null

    $actionLabels = @("Continue", "Open", "Launch", "Resume")
    $primaryCandidates = Get-UiTapCandidates -XmlPath $preXmlLocal -Labels $actionLabels
    $primaryTapped = $false
    $primaryTapTrace = @()

    if ($forceToolsOnlyBlank) {
        $primaryTapTrace += "primary:forced-skip:tools-only-blank-validation"
    }
    else {
        foreach ($c in $primaryCandidates) {
            adb -s $device shell input tap $($c.x) $($c.y) | Out-Null
            $primaryTapped = $true
            $primaryTapTrace += "primary:$($c.source):$($c.score):$($c.x),$($c.y):$($c.text):$($c.desc):$($c.rid)"
            Start-Sleep -Seconds 1
            break
        }
    }

    $pngRemote = "/sdcard/Download/devlauncher_retest_$safeId.png"
    $xmlRemote = "/sdcard/Download/devlauncher_retest_$safeId.xml"
    $pngLocal = Join-Path $deviceDir "screen.png"
    $xmlLocal = Join-Path $deviceDir "ui.xml"
    $preRecoveryPng = Join-Path $deviceDir "screen_before_recovery.png"
    $preRecoveryXml = Join-Path $deviceDir "ui_before_recovery.xml"
    $logLocal = Join-Path $deviceDir "logcat_filtered.txt"
    $actLocal = Join-Path $deviceDir "activity.txt"

    adb -s $device shell screencap -p $pngRemote | Out-Null
    adb -s $device pull $pngRemote $pngLocal | Out-Null
    adb -s $device shell rm $pngRemote | Out-Null

    adb -s $device shell uiautomator dump $xmlRemote | Out-Null
    adb -s $device pull $xmlRemote $xmlLocal | Out-Null
    adb -s $device shell rm $xmlRemote | Out-Null

    Copy-Item $pngLocal $preRecoveryPng -Force
    Copy-Item $xmlLocal $preRecoveryXml -Force

    $beforeRecoverySnap = Get-UiSnapshotFromXml -XmlPath $preRecoveryXml
    $beforeRecoveryClass = if ($forceToolsOnlyBlank) { "Tools-only blank" } else { Get-Classification -UiTokens $beforeRecoverySnap.tokens -FilteredLogText "" -ActivityText "" }
    $secondaryAttempted = $false
    $secondaryTapTrace = @()

    if ($beforeRecoveryClass -eq "Tools-only blank") {
        $secondaryAttempted = $true
        $secondaryLabels = @("Continue", "Open", "Launch", "Resume", "Tools")
        $secondaryCandidates = Get-UiTapCandidates -XmlPath $preRecoveryXml -Labels $secondaryLabels
        foreach ($c in $secondaryCandidates | Select-Object -First 4) {
            adb -s $device shell input tap $($c.x) $($c.y) | Out-Null
            $secondaryTapTrace += "secondary:$($c.source):$($c.score):$($c.x),$($c.y):$($c.text):$($c.desc):$($c.rid)"
            Start-Sleep -Seconds 1
        }

        Start-Sleep -Seconds 2
        adb -s $device shell screencap -p $pngRemote | Out-Null
        adb -s $device pull $pngRemote $pngLocal | Out-Null
        adb -s $device shell rm $pngRemote | Out-Null

        adb -s $device shell uiautomator dump $xmlRemote | Out-Null
        adb -s $device pull $xmlRemote $xmlLocal | Out-Null
        adb -s $device shell rm $xmlRemote | Out-Null
    }

    $activityOut = adb -s $device shell dumpsys activity activities
    $activityOut | Out-File -FilePath $actLocal -Encoding utf8

    $logOut = adb -s $device logcat -d -v time
    $pattern = "DevLauncherManifestParser|devlauncher.launcher.manifest|Failed to open app|DevLauncherErrorActivity|runtimeVersion|expo-updates|Unable to resolve host|Failed to connect|Connection refused"
    $filtered = $logOut | Select-String -Pattern $pattern
    $filtered | Out-File -FilePath $logLocal -Encoding utf8

    $preSnap = Get-UiSnapshotFromXml -XmlPath $preXmlLocal
    $postSnap = Get-UiSnapshotFromXml -XmlPath $xmlLocal
    $uiTexts = $postSnap.texts
    $uiTextPath = Join-Path $deviceDir "ui_texts.txt"
    $uiTexts | Out-File -FilePath $uiTextPath -Encoding utf8

    $filteredText = ($filtered | ForEach-Object { $_.Line }) -join "`n"
    $activityText = Get-Content -Raw $actLocal
    $classification = Get-Classification -UiTokens $postSnap.tokens -FilteredLogText $filteredText -ActivityText $activityText
    $activityTop = Get-ActivityTopLine -ActivityText $activityText

    $preTokenSet = @($preSnap.tokens)
    $postTokenSet = @($postSnap.tokens)
    $addedTokens = @($postTokenSet | Where-Object { $_ -notin $preTokenSet })
    $removedTokens = @($preTokenSet | Where-Object { $_ -notin $postTokenSet })
    $autoTags = Get-AutoTags -Classification $classification -PrimaryTapped $primaryTapped -SecondaryAttempted $secondaryAttempted -FilteredLogText $filteredText -ActivityTop $activityTop -PreTokens $preTokenSet -PostTokens $postTokenSet

    $tapTracePath = Join-Path $deviceDir "tap_trace.txt"
    @($primaryTapTrace + $secondaryTapTrace) | Out-File -FilePath $tapTracePath -Encoding utf8

    $results += [pscustomobject]@{
        device                  = $device
        metro_status            = $metroStatus
        classification          = $classification
        continue_tapped         = ($postTokenSet -contains "continue")
        primary_tapped          = $primaryTapped
        secondary_attempt       = $secondaryAttempted
        forced_tools_only_blank = $forceToolsOnlyBlank
        pre_xml_path            = $preXmlLocal
        post_xml_path           = $xmlLocal
        pre_recovery_xml        = $preRecoveryXml
        pre_recovery_png        = $preRecoveryPng
        pre_node_count          = $preSnap.nodeCount
        post_node_count         = $postSnap.nodeCount
        pre_root_bounds         = $preSnap.rootBounds
        post_root_bounds        = $postSnap.rootBounds
        ui_diff_added           = $addedTokens
        ui_diff_removed         = $removedTokens
        activity_top            = $activityTop
        auto_tags               = $autoTags
        tap_trace_path          = $tapTracePath
        ui_text_path            = $uiTextPath
        filtered_log_path       = $logLocal
        screenshot_path         = $pngLocal
        activity_path           = $actLocal
    }
}

$summaryPath = Join-Path $captureRoot "summary.json"
$results | ConvertTo-Json -Depth 4 | Out-File -FilePath $summaryPath -Encoding utf8

Write-Host "=== DevLauncher Retest Summary ==="
$results | Format-Table -AutoSize
Write-Host "Artifacts:" $captureRoot
Write-Host "Summary:" $summaryPath
