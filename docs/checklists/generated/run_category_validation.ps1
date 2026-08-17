param(
    [string]$Round = "round1",
    [string]$ApiBase = "http://127.0.0.1:8000",
    [string]$UiBase = "http://127.0.0.1:3000"
)

$ErrorActionPreference = 'Stop'

function Invoke-Json {
    param(
        [string]$Method,
        [string]$Url,
        [object]$Body = $null,
        [hashtable]$Headers = @{}
    )
    $params = @{
        Method          = $Method
        Uri             = $Url
        TimeoutSec      = 30
        Headers         = $Headers
        UseBasicParsing = $true
    }
    if ($null -ne $Body) {
        $params.ContentType = 'application/json'
        $params.Body = ($Body | ConvertTo-Json -Depth 10)
    }
    return Invoke-WebRequest @params
}

function Add-Result {
    param(
        [System.Collections.Generic.List[object]]$Rows,
        [string]$Category,
        [string]$Check,
        [string]$Status,
        [string]$Detail
    )
    $Rows.Add([pscustomobject]@{
            round     = $Round
            category  = $Category
            check     = $Check
            status    = $Status
            detail    = $Detail
            timestamp = (Get-Date).ToString('s')
        }) | Out-Null
}

$rows = New-Object System.Collections.Generic.List[object]

# bootstrap auth
$seed = Get-Date -Format 'yyyyMMddHHmmssfff'
$email = "engine-matrix-$seed@example.com"
$secret = "Pass!23456"
try {
    $signupBody = @{ email = $email; username = "matrix_$seed"; password = $secret }
    $null = Invoke-Json -Method POST -Url "$ApiBase/api/auth/signup" -Body $signupBody
    Add-Result -Rows $rows -Category '보안/권한' -Check 'signup' -Status 'PASS' -Detail '201/200'
}
catch {
    Add-Result -Rows $rows -Category '보안/권한' -Check 'signup' -Status 'FAIL' -Detail $_.Exception.Message
}

$token = $null
try {
    $loginResp = Invoke-WebRequest -Method POST -Uri "$ApiBase/api/auth/login" -ContentType 'application/x-www-form-urlencoded' -Body "username=$([uri]::EscapeDataString($email))&password=$([uri]::EscapeDataString($secret))" -TimeoutSec 30 -UseBasicParsing
    $loginObj = $loginResp.Content | ConvertFrom-Json
    $token = $loginObj.access_token
    Add-Result -Rows $rows -Category '보안/권한' -Check 'login' -Status 'PASS' -Detail '200'
}
catch {
    Add-Result -Rows $rows -Category '보안/권한' -Check 'login' -Status 'FAIL' -Detail $_.Exception.Message
}

$authHeader = @{}
if ($token) {
    $authHeader = @{ Authorization = "Bearer $token" }
    try {
        $me = Invoke-Json -Method GET -Url "$ApiBase/api/auth/me" -Headers $authHeader
        Add-Result -Rows $rows -Category '보안/권한' -Check 'auth_me' -Status 'PASS' -Detail "HTTP $($me.StatusCode)"
    }
    catch {
        Add-Result -Rows $rows -Category '보안/권한' -Check 'auth_me' -Status 'FAIL' -Detail $_.Exception.Message
    }
}

# runtime checks
$checks = @(
    @{ C = '운영관측/헬스'; N = 'backend_health'; M = 'GET'; U = "$ApiBase/health"; B = $null; H = @{} },
    @{ C = 'API/서버'; N = 'categories'; M = 'GET'; U = "$ApiBase/api/marketplace/categories"; B = $null; H = @{} },
    @{ C = 'API/서버'; N = 'stats_overview'; M = 'GET'; U = "$ApiBase/api/marketplace/stats/overview"; B = $null; H = @{} },
    @{ C = '통역/언어'; N = 'interpreter_health'; M = 'GET'; U = "$ApiBase/api/marketplace/interpreter/health"; B = $null; H = $authHeader },
    @{ C = '통역/언어'; N = 'interpreter_translate'; M = 'POST'; U = "$ApiBase/api/marketplace/interpreter/translate"; B = @{ text = 'hello'; source_lang = 'en'; target_lang = 'ko' }; H = $authHeader },
    @{ C = '음악/오디오'; N = 'music_health'; M = 'GET'; U = "$ApiBase/api/marketplace/music/health"; B = $null; H = $authHeader },
    @{ C = '음악/오디오'; N = 'music_compose_emotion'; M = 'POST'; U = "$ApiBase/api/marketplace/music/compose/emotion"; B = @{ emotion = 'calm'; intensity = 0.65; theme = 'validation' }; H = $authHeader },
    @{ C = '코드/개발'; N = 'codegen_profiles'; M = 'GET'; U = "$ApiBase/api/marketplace/code-generator/profiles"; B = $null; H = @{} },
    @{ C = '코드/개발'; N = 'codegen_generate'; M = 'POST'; U = "$ApiBase/api/marketplace/code-generator/generate"; B = @{ project_name = 'matrix-test'; task = 'create hello world python app'; profile = 'python_fastapi' }; H = $authHeader },
    @{ C = '브레인/학습'; N = 'feature_catalog'; M = 'GET'; U = "$ApiBase/api/marketplace/feature-catalog"; B = $null; H = @{} },
    @{ C = '오케스트레이션/에이전트'; N = 'customer_stage_run_create'; M = 'POST'; U = "$ApiBase/api/marketplace/customer-orchestrate/stage-runs"; B = @{ project_name = 'matrix-orch'; task = 'validate orchestrator'; mode = 'manual' }; H = $authHeader },
    @{ C = '기타'; N = 'campaign_strategies'; M = 'GET'; U = "$ApiBase/api/marketplace/campaign-orchestrate/strategies"; B = $null; H = @{} },
    @{ C = '대시보드/UI'; N = 'ui_codegen'; M = 'GET'; U = "$UiBase/marketplace/code-generator"; B = $null; H = @{} }
)

foreach ($chk in $checks) {
    try {
        $resp = Invoke-Json -Method $chk.M -Url $chk.U -Body $chk.B -Headers $chk.H
        $ok = ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 300)
        Add-Result -Rows $rows -Category $chk.C -Check $chk.N -Status ($(if ($ok) { 'PASS' } else { 'FAIL' })) -Detail "HTTP $($resp.StatusCode)"
    }
    catch {
        Add-Result -Rows $rows -Category $chk.C -Check $chk.N -Status 'FAIL' -Detail $_.Exception.Message
    }
}

# 데이터/저장소 분류군은 코드 생성 이력과 다운로드 가능 여부로 검증
$generatedEntry = $rows | Where-Object { $_.check -eq 'codegen_generate' -and $_.status -eq 'PASS' } | Select-Object -First 1
if ($generatedEntry) {
    try {
        $historyResp = Invoke-Json -Method GET -Url "$ApiBase/api/marketplace/code-generator/history" -Headers $authHeader
        Add-Result -Rows $rows -Category '데이터/저장소' -Check 'codegen_history' -Status 'PASS' -Detail "HTTP $($historyResp.StatusCode)"
        $historyObj = $historyResp.Content | ConvertFrom-Json
        $generationId = $null
        if ($historyObj -and $historyObj.items -and $historyObj.items.Count -gt 0) {
            $generationId = $historyObj.items[0].generation_id
        }
        if ([string]::IsNullOrWhiteSpace($generationId)) {
            Add-Result -Rows $rows -Category '데이터/저장소' -Check 'codegen_download' -Status 'FAIL' -Detail 'generation_id 미확인'
        }
        else {
            $downloadResp = Invoke-Json -Method GET -Url "$ApiBase/api/marketplace/code-generator/download/$generationId" -Headers $authHeader
            $downloadOk = ($downloadResp.StatusCode -ge 200 -and $downloadResp.StatusCode -lt 300)
            Add-Result -Rows $rows -Category '데이터/저장소' -Check 'codegen_download' -Status ($(if ($downloadOk) { 'PASS' } else { 'FAIL' })) -Detail "HTTP $($downloadResp.StatusCode)"
        }
    }
    catch {
        Add-Result -Rows $rows -Category '데이터/저장소' -Check 'codegen_storage_probe' -Status 'FAIL' -Detail $_.Exception.Message
    }
}
else {
    Add-Result -Rows $rows -Category '데이터/저장소' -Check 'codegen_storage_probe' -Status 'BLOCKED' -Detail 'codegen_generate 실패로 저장소 검증 보류'
}

$outDir = 'docs/checklists/generated'
New-Item -ItemType Directory -Path $outDir -Force | Out-Null
$jsonPath = Join-Path $outDir "category_validation_$Round.json"
$rows | ConvertTo-Json -Depth 6 | Set-Content -Path $jsonPath -Encoding UTF8

$summary = $rows | Group-Object category | ForEach-Object {
    $c = $_.Name
    $all = $_.Group
    if (($all.status -contains 'FAIL')) {
        [pscustomobject]@{ category = $c; round = $Round; result = 'FAIL' }
    }
    elseif (($all.status -contains 'BLOCKED')) {
        [pscustomobject]@{ category = $c; round = $Round; result = 'BLOCKED' }
    }
    else {
        [pscustomobject]@{ category = $c; round = $Round; result = 'PASS' }
    }
}
$summaryPath = Join-Path $outDir "category_validation_$Round.summary.json"
$summary | ConvertTo-Json -Depth 4 | Set-Content -Path $summaryPath -Encoding UTF8

$summary | Format-Table -AutoSize | Out-Host
Write-Host "WROTE $jsonPath"
Write-Host "WROTE $summaryPath"
