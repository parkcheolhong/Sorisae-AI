param(
    [Parameter(Mandatory = $false)]
    [string]$SourceRoot = "C:\Users\WORK\source\repos\parkcheolhong\codeAI",

    [Parameter(Mandatory = $false)]
    [string]$OutputRoot = "C:\Users\WORK\source\repos\parkcheolhong\codeAI\exports\bundle-331-featured",

    [Parameter(Mandatory = $false)]
    [switch]$CleanOutput
)

$ErrorActionPreference = "Stop"

function Ensure-Dir {
    param([string]$Path)
    if (-not (Test-Path $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
}

function Copy-RelativeFile {
    param(
        [string]$Root,
        [string]$RelativePath,
        [string]$OutRoot
    )

    $src = Join-Path $Root $RelativePath
    if (-not (Test-Path $src)) {
        Write-Warning "SKIP (missing): $RelativePath"
        return
    }

    $dst = Join-Path $OutRoot $RelativePath
    $dstDir = Split-Path -Parent $dst
    Ensure-Dir $dstDir
    Copy-Item -Path $src -Destination $dst -Force
    Write-Host "COPIED FILE: $RelativePath"
}

function Copy-RelativeDir {
    param(
        [string]$Root,
        [string]$RelativePath,
        [string]$OutRoot
    )

    $src = Join-Path $Root $RelativePath
    if (-not (Test-Path $src)) {
        Write-Warning "SKIP (missing dir): $RelativePath"
        return
    }

    $dst = Join-Path $OutRoot $RelativePath
    Ensure-Dir (Split-Path -Parent $dst)
    Copy-Item -Path $src -Destination $dst -Recurse -Force
    Write-Host "COPIED DIR : $RelativePath"
}

if ($CleanOutput -and (Test-Path $OutputRoot)) {
    Remove-Item -Path $OutputRoot -Recurse -Force
}

Ensure-Dir $OutputRoot

# 1) Build 331 anchors and evidence
$build331Files = @(
    "apps/mobile-nadotongryoksa/app.json",
    "apps/mobile-nadotongryoksa/eas.json",
    "apps/mobile-nadotongryoksa/android/app/build.gradle",
    "uploads/marketplace_local/apk/nadotongryoksa-v1.0.246-build331-current.apk",
    "uploads/marketplace_local/apk/nadotongryoksa-v1.manifest.json",
    "knowledge/worldlinco_apk_baseline.json",
    "docs/program-birth-and-technical-dossier-20260516.md",
    "docs/checklists/worldlinco-build331-apk-reproduction-checklist-20260817.md"
)

$build331Dirs = @(
    "docs/checklists/evidence/build331-rehearsal-20260818-003405",
    "apps/mobile-nadotongryoksa/evidence/device-validation-20260813"
)

# 2) SNS + passkey login + related auth flow
$authFiles = @(
    "backend/auth_router.py",
    "backend/marketplace/models.py",
    "frontend/frontend/app/marketplace/page.tsx",
    "scripts/verify_passkey_callback_real_token.ps1",
    "frontend/frontend/tests/admin-passkey-operational.playwright.spec.ts",
    "frontend/frontend/tests/marketplace-passkey-login.playwright.spec.ts",
    "frontend/frontend/tests/marketplace-passkey-feature-experience.playwright.spec.ts",
    "apps/mobile-nadotongryoksa/src/features/sns-share/snsShare.ts",
    "apps/mobile-nadotongryoksa/src/features/chat/screens/ChatRoomScreen.tsx",
    "docs/checklists/sorisae-passkey-fab-integrated-close-checklist-20260816.md"
)

# 3) Public data + other implemented programs/modules
$programFiles = @(
    "backend/services/friend_public_portal.py",
    "backend/admin_router.py",
    "frontend/frontend/components/admin/admin-system-settings-panel.tsx",
    "frontend/frontend/components/admin/admin-worldlinco-bulk-chat-panel.tsx",
    "docker-compose.yml",
    "apps/mobile-nadotongryoksa/App.tsx"
)

$programDirs = @(
    "apps/mobile-nadotongryoksa/src/features/travel-booking",
    "apps/mobile-nadotongryoksa/src/features/travel-itinerary",
    "apps/mobile-nadotongryoksa/src/features/tourism",
    "apps/mobile-nadotongryoksa/src/features/sorisae",
    "apps/mobile-nadotongryoksa/src/features/contacts",
    "apps/mobile-nadotongryoksa/src/features/voip-auto",
    "apps/mobile-nadotongryoksa/src/features/pstn-assist",
    "backend/services",
    "backend/marketplace",
    "frontend/frontend/components/admin",
    "frontend/frontend/app/admin",
    "frontend/frontend/app/marketplace"
)

$allFiles = @($build331Files + $authFiles + $programFiles | Select-Object -Unique)
$allDirs = @($build331Dirs + $programDirs | Select-Object -Unique)

foreach ($f in $allFiles) {
    Copy-RelativeFile -Root $SourceRoot -RelativePath $f -OutRoot $OutputRoot
}

foreach ($d in $allDirs) {
    Copy-RelativeDir -Root $SourceRoot -RelativePath $d -OutRoot $OutputRoot
}

$manifestPath = Join-Path $OutputRoot "EXTRACT_MANIFEST.txt"
$lines = @()
$lines += "Bundle created: $(Get-Date -Format o)"
$lines += "SourceRoot: $SourceRoot"
$lines += "OutputRoot: $OutputRoot"
$lines += ""
$lines += "[Build331 Files]"
$lines += $build331Files
$lines += ""
$lines += "[Build331 Dirs]"
$lines += $build331Dirs
$lines += ""
$lines += "[Auth+SNS Files]"
$lines += $authFiles
$lines += ""
$lines += "[Program Files]"
$lines += $programFiles
$lines += ""
$lines += "[Program Dirs]"
$lines += $programDirs

Set-Content -Path $manifestPath -Value $lines -Encoding UTF8
Write-Host "DONE: $OutputRoot"
Write-Host "MANIFEST: $manifestPath"
