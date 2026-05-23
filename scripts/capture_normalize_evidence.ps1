param(
    [string]$BaseUrl = "https://metanova1004.com",
    [string]$Email = "119cash@naver.com",
    [string]$Password = "",
    [string]$PasswordFile = ".runtime/secrets/fixed_admin_password.txt",
    [string]$OutputPath = "tmp/normalize-evidence.json",
    [switch]$CleanupOnly
)

$ErrorActionPreference = 'Stop'

if (-not $Password) {
    $resolvedPasswordFile = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($PasswordFile)
    if (-not (Test-Path $resolvedPasswordFile)) {
        throw "비밀번호 파일을 찾을 수 없습니다: $resolvedPasswordFile"
    }

    $Password = (Get-Content -Raw $resolvedPasswordFile).Trim()
    if (-not $Password) {
        throw "비밀번호 파일이 비어 있습니다: $resolvedPasswordFile"
    }
}

function Get-AccessToken {
    param(
        [string]$ApiBaseUrl,
        [string]$Username,
        [string]$PlainPassword
    )

    $loginJson = & curl.exe -s -X POST "$ApiBaseUrl/api/auth/login" `
        -H "Content-Type: application/x-www-form-urlencoded" `
        --data-urlencode "username=$Username" `
        --data-urlencode "password=$PlainPassword"

    if (-not $loginJson) {
        throw "로그인 응답이 비어 있습니다."
    }

    $login = $loginJson | ConvertFrom-Json
    if (-not $login.access_token) {
        throw "로그인 토큰을 가져오지 못했습니다."
    }

    return [string]$login.access_token
}

function Save-NormalizeEvidenceRawBytes {
    param(
        [string]$ApiBaseUrl,
        [string]$BearerToken,
        [string]$TargetPath,
        [bool]$UseCleanupOnly
    )

    $targetDirectory = Split-Path -Parent $TargetPath
    if ($targetDirectory) {
        New-Item -ItemType Directory -Force -Path $targetDirectory | Out-Null
    }

    $body = @{ cleanup_only = $UseCleanupOnly } | ConvertTo-Json -Depth 5 -Compress
    $tempPath = [System.IO.Path]::GetTempFileName()
    $bodyPath = [System.IO.Path]::GetTempFileName()
    try {
        [System.IO.File]::WriteAllText($bodyPath, $body, [System.Text.UTF8Encoding]::new($false))
        & curl.exe -s -o $tempPath -X POST "$ApiBaseUrl/api/admin/workspace-self-run-record/normalize" `
            -H "Authorization: Bearer $BearerToken" `
            -H "Content-Type: application/json; charset=utf-8" `
            --data-binary "@$bodyPath"

        $bytes = [System.IO.File]::ReadAllBytes($tempPath)
        if ($bytes.Length -eq 0) {
            throw "normalize 응답 바이트가 비어 있습니다."
        }

        [System.IO.File]::WriteAllBytes($TargetPath, $bytes)
        $utf8 = New-Object System.Text.UTF8Encoding($false, $true)
        $jsonText = $utf8.GetString($bytes)
        return $jsonText | ConvertFrom-Json
    }
    finally {
        if (Test-Path $tempPath) {
            Remove-Item $tempPath -Force
        }
        if (Test-Path $bodyPath) {
            Remove-Item $bodyPath -Force
        }
    }
}

$resolvedOutputPath = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($OutputPath)
$token = Get-AccessToken -ApiBaseUrl $BaseUrl -Username $Email -PlainPassword $Password
$payload = Save-NormalizeEvidenceRawBytes -ApiBaseUrl $BaseUrl -BearerToken $token -TargetPath $resolvedOutputPath -UseCleanupOnly $CleanupOnly.IsPresent

[pscustomobject]@{
    output_path       = $resolvedOutputPath
    normalized        = [bool]$payload.normalized
    action            = [string]$payload.action
    message           = [string]$payload.message
    retry_approval_id = [string]($payload.retry.approval_id)
} | ConvertTo-Json -Depth 5