
# 1. ZIP 다운로드 엔드포인트 상태 코드 및 콘텐츠 크기 확인
Write-Host "=== 1. ZIP 다운로드 엔드포인트 검증 ===" -ForegroundColor Cyan
$response = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/marketplace/zip/sorisae-interpreter-v1.zip" -UseBasicParsing
Write-Host "  상태 코드: $($response.StatusCode)" -ForegroundColor Green
Write-Host "  Content-Type: $($response.Headers['Content-Type'])" -ForegroundColor Green
Write-Host "  파일 크기: $($response.Content.Length) bytes" -ForegroundColor Green

# 2. ZIP 파일 검증 (임시 저장 후 압축 해제 확인)
Write-Host "`n=== 2. ZIP 파일 무결성 검증 ===" -ForegroundColor Cyan
$temp_zip = "$env:TEMP\sorisae-test-$([datetime]::Now.Ticks).zip"
[System.IO.File]::WriteAllBytes($temp_zip, $response.Content)
Write-Host "  임시 저장: $temp_zip" -ForegroundColor Gray

try {
    $shell = New-Object -Com Shell.Application
    $zip = $shell.NameSpace($temp_zip)
    $items = $zip.Items()
    Write-Host "  포함 파일: $($items.Count)개" -ForegroundColor Green
    foreach ($item in $items) {
        Write-Host "    - $($item.Name)" -ForegroundColor Gray
    }
}
catch {
    Write-Host "  ⚠️ ZIP 검증 실패: $_" -ForegroundColor Yellow
}
finally {
    Remove-Item $temp_zip -Force -ErrorAction SilentlyContinue
}

# 3. 마켓플레이스 API에서 상품 조회
Write-Host "`n=== 3. 마켓플레이스 상품 API ===" -ForegroundColor Cyan
try {
    $api_response = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/marketplace/projects" -UseBasicParsing
    $sorisae = $api_response.items | Where-Object { $_.title -like "*sorisae*" }
    if ($sorisae) {
        Write-Host "  ✅ 상품 발견 (ID $($sorisae.id))" -ForegroundColor Green
        Write-Host "    제목: $($sorisae.title)" -ForegroundColor Green
    }
    else {
        Write-Host "  ⚠️ 검색 결과에서 미발견 (전체 상품 수: $($api_response.items.Count))" -ForegroundColor Yellow
    }
}
catch {
    Write-Host "  ❌ API 오류: $_" -ForegroundColor Red
}
