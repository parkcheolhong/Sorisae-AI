$ErrorActionPreference = 'Stop'

$login = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/api/auth/login' -Method POST -ContentType 'application/x-www-form-urlencoded' -Body 'username=119cash%40naver.com&password=space0215%40' -UseBasicParsing
$token = ($login.Content | ConvertFrom-Json).access_token
$headers = @{ Authorization = "Bearer $token" }

Write-Output '=== Gate 4 Reverify ==='
$gate4Paths = @(
    'https://metanova1004.com/api/marketplace/interpreter/health',
    'https://metanova1004.com/api/marketplace/music/health',
    'https://metanova1004.com/api/marketplace/extras/health',
    'https://metanova1004.com/api/marketplace/extras/iot/health',
    'https://metanova1004.com/api/marketplace/extras/game/health'
)
$gate4Pass = 0
foreach ($p in $gate4Paths) {
    try {
        $resp = Invoke-WebRequest -Uri $p -Headers $headers -UseBasicParsing
        $json = $resp.Content | ConvertFrom-Json
        if ($json.status -eq 'ok') {
            $gate4Pass += 1
            Write-Output "PASS $p status=$($json.status)"
        }
        else {
            Write-Output "FAIL $p status=$($json.status)"
        }
    }
    catch {
        Write-Output "FAIL $p error=$($_.Exception.Message)"
    }
}
Write-Output "Gate4 result: $gate4Pass/5"

Write-Output '=== Gate 5 Reverify ==='
$gate5Path = 'https://metanova1004.com/api/marketplace/extras/health'
$gate5Pass = 0
try {
    $resp = Invoke-WebRequest -Uri $gate5Path -Headers $headers -UseBasicParsing
    $json = $resp.Content | ConvertFrom-Json
    $cb = $json.circuit_breakers
    if ($null -ne $cb -and $cb.iot.state -eq 'CLOSED' -and $cb.game.state -eq 'CLOSED' -and [int]$cb.iot.failures -eq 0 -and [int]$cb.game.failures -eq 0 -and [int]$cb.iot.threshold -eq 3 -and [int]$cb.game.threshold -eq 3) {
        $gate5Pass = 1
        Write-Output "PASS $gate5Path iot=$($cb.iot.state)/$($cb.iot.failures)/$($cb.iot.threshold) game=$($cb.game.state)/$($cb.game.failures)/$($cb.game.threshold)"
    }
    else {
        Write-Output "FAIL $gate5Path circuit_breakers contract mismatch"
    }
}
catch {
    Write-Output "FAIL $gate5Path error=$($_.Exception.Message)"
}
Write-Output "Gate5 result: $gate5Pass/1"
