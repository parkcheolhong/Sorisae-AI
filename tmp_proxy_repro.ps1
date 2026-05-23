$ErrorActionPreference = 'Continue'
$base = 'http://127.0.0.1:3005'
$backend = 'http://127.0.0.1:8000'
$loginBody = 'username=119cash%40naver.com&password=space0215%40'

$login = Invoke-WebRequest -Uri "$backend/api/auth/login" -Method POST -ContentType 'application/x-www-form-urlencoded' -Body $loginBody -UseBasicParsing
$token = ($login.Content | ConvertFrom-Json).access_token
$h = @{ Authorization = "Bearer $token" }

Write-Host '=== system-settings x5 ==='
for ($i = 1; $i -le 5; $i++) {
    try {
        $r = Invoke-WebRequest -Uri "$base/api/admin/system-settings" -Headers $h -UseBasicParsing -TimeoutSec 30
        Write-Host "system-settings#$i http=$($r.StatusCode)"
    }
    catch {
        if ($_.ErrorDetails -and $_.ErrorDetails.Message) {
            Write-Host "system-settings#$i FAIL body=$($_.ErrorDetails.Message)"
        }
        else {
            Write-Host "system-settings#$i FAIL msg=$($_.Exception.Message.Split([char]10)[0])"
        }
    }
}

Write-Host '=== orchestrate chat x3 ==='
for ($i = 1; $i -le 3; $i++) {
    $body = @{ task = '헬스체크'; message = '오케스트레이션 연결 확인용 짧은 질의'; mode = 'balanced' } | ConvertTo-Json -Compress
    try {
        $headers = @{ Authorization = "Bearer $token"; 'Content-Type' = 'application/json' }
        $r = Invoke-WebRequest -Uri "$base/api/llm/orchestrate/chat" -Method POST -Headers $headers -Body $body -UseBasicParsing -TimeoutSec 60
        $j = $r.Content | ConvertFrom-Json
        Write-Host "chat#$i http=$($r.StatusCode) gateway=$($j.gateway) hasReply=$([bool]$j.reply)"
    }
    catch {
        if ($_.ErrorDetails -and $_.ErrorDetails.Message) {
            Write-Host "chat#$i FAIL body=$($_.ErrorDetails.Message)"
        }
        else {
            Write-Host "chat#$i FAIL msg=$($_.Exception.Message.Split([char]10)[0])"
        }
    }
}
