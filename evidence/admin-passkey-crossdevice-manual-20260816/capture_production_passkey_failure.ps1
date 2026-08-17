param(
    [string]$Domain = "xn--114-2p7l635dz3bh5j.com",
    [string]$Email = "119cash@naver.com"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$evidenceRoot = Join-Path $PSScriptRoot ("failure-capture-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
New-Item -ItemType Directory -Path $evidenceRoot -Force | Out-Null

function Save-Text {
    param(
        [string]$Path,
        [string]$Content
    )
    Set-Content -Path $Path -Value $Content -Encoding UTF8
}

function Invoke-HttpCapture {
    param(
        [string]$Name,
        [string]$Method,
        [string]$Url,
        [hashtable]$Headers,
        [string]$Body
    )

    $out = [ordered]@{
        name = $Name
        method = $Method
        url = $Url
        timestamp = (Get-Date).ToString("o")
        status = $null
        headers = @{}
        body = $null
        error = $null
    }

    try {
        if ($Body) {
            $resp = Invoke-WebRequest -Method $Method -Uri $Url -Headers $Headers -Body $Body -ContentType "application/json" -TimeoutSec 25
        } else {
            $resp = Invoke-WebRequest -Method $Method -Uri $Url -Headers $Headers -TimeoutSec 25
        }
        $out.status = [int]$resp.StatusCode
        $out.headers = @{}
        foreach ($k in $resp.Headers.Keys) { $out.headers[$k] = [string]$resp.Headers[$k] }
        $out.body = [string]$resp.Content
    }
    catch {
        $ex = $_.Exception
        if ($ex.Response) {
            $out.status = [int]$ex.Response.StatusCode
            $out.headers = @{}
            foreach ($k in $ex.Response.Headers.Keys) { $out.headers[$k] = [string]$ex.Response.Headers[$k] }
            $sr = New-Object System.IO.StreamReader($ex.Response.GetResponseStream())
            $out.body = $sr.ReadToEnd()
        } else {
            $out.error = [string]$ex.Message
        }
    }

    $json = $out | ConvertTo-Json -Depth 8
    Save-Text -Path (Join-Path $evidenceRoot ($Name + ".json")) -Content $json
}

$domainUrl = "https://$Domain"
$adminLoginUrl = "$domainUrl/admin/login"
$startUrl = "$domainUrl/api/auth/passkey/login/start"
$finishUrl = "$domainUrl/api/auth/passkey/login/finish"

$meta = @{
    captured_at = (Get-Date).ToString("o")
    machine = $env:COMPUTERNAME
    domain = $Domain
    email = $Email
    urls = @{
        admin_login = $adminLoginUrl
        passkey_start = $startUrl
        passkey_finish = $finishUrl
    }
} | ConvertTo-Json -Depth 8
Save-Text -Path (Join-Path $evidenceRoot "meta.json") -Content $meta

# 1) Capture raw login HTML and chunk refs
$html = ""
try {
    $html = (Invoke-WebRequest -Uri $adminLoginUrl -TimeoutSec 25).Content
} catch {
    $html = "[ERROR] " + $_.Exception.Message
}
Save-Text -Path (Join-Path $evidenceRoot "admin_login.html") -Content $html

$chunkRefs = [regex]::Matches($html, '_next/static/chunks/[^\s>]+\.js') | ForEach-Object { $_.Value }
Save-Text -Path (Join-Path $evidenceRoot "admin_login_chunks.txt") -Content ($chunkRefs -join [Environment]::NewLine)

# 2) Capture passkey start
$payload = @{ email = $Email } | ConvertTo-Json -Compress
Invoke-HttpCapture -Name "passkey_login_start" -Method "POST" -Url $startUrl -Headers @{} -Body $payload

# 3) Capture CORS preflight behavior
$preflightHeaders = @{
    "Origin" = $domainUrl
    "Access-Control-Request-Method" = "POST"
    "Access-Control-Request-Headers" = "content-type"
}
Invoke-HttpCapture -Name "passkey_login_start_preflight" -Method "OPTIONS" -Url $startUrl -Headers $preflightHeaders -Body ""

# 4) Guidance note
$note = @"
Capture completed.
- failure evidence dir: $evidenceRoot
Next:
1) Attach this folder as evidence.
2) If possible, add Chrome console snippet JSON from chrome_passkey_debug_snippet.js.
"@
Save-Text -Path (Join-Path $evidenceRoot "README.txt") -Content $note

Write-Host "[capture] done: $evidenceRoot"
