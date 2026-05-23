#!/usr/bin/env pwsh
<#
.SYNOPSIS
    EAS APK 자동화 빌드 및 배포 스크립트
    
.DESCRIPTION
    Expo EAS를 사용하여 preview 프로필로 Android APK를 빌드하고
    마켓플레이스에 자동 배포합니다.
    
.PARAMETER Profile
    빌드 프로필: development, preview, staging, production
    기본값: preview
    
.PARAMETER OutputPath
    APK 배포 경로
    기본값: uploads/marketplace_local/apk
    
.PARAMETER SkipBuild
    빌드 스킵하고 기존 APK 사용 (테스트용)
    
.EXAMPLE
    .\build_apk_automated.ps1 -Profile preview
    
.NOTES
    필수 조건:
    - Node.js >= 18.0.0
    - EAS CLI: npm install -g eas-cli@latest
    - Expo 계정 인증: eas login
#>

param(
    [string]$Profile = "preview",
    [string]$OutputPath = "uploads/marketplace_local/apk",
    [switch]$SkipBuild,
    [switch]$Verbose = $false
)

$ErrorActionPreference = "Stop"
$VerbosePreference = if ($Verbose) { "Continue" } else { "SilentlyContinue" }

# 색상 정의
$Colors = @{
    Green   = "`e[32m"
    Yellow  = "`e[33m"
    Red     = "`e[31m"
    Blue    = "`e[34m"
    Cyan    = "`e[36m"
    Reset   = "`e[0m"
}

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    
    $color = switch ($Level) {
        "SUCCESS" { $Colors.Green }
        "WARNING" { $Colors.Yellow }
        "ERROR"   { $Colors.Red }
        "INFO"    { $Colors.Cyan }
        default   { $Colors.Reset }
    }
    
    Write-Host "${color}[$Level]${Colors.Reset} [$timestamp] $Message"
}

function Test-Prerequisites {
    Write-Log "필수 조건 확인 중..." "INFO"
    
    # Node.js 확인
    $nodeVersion = & node --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Log "Node.js가 설치되지 않았습니다. npm install -g node" "ERROR"
        exit 1
    }
    Write-Log "✓ Node.js $nodeVersion" "SUCCESS"
    
    # EAS CLI 확인
    $easVersion = & eas --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Log "EAS CLI가 설치되지 않았습니다. npm install -g eas-cli@latest" "ERROR"
        exit 1
    }
    Write-Log "✓ EAS CLI $easVersion" "SUCCESS"
    
    # Expo 로그인 확인
    $whoamiOutput = & eas whoami 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Log "Expo 계정에 로그인하지 않았습니다. eas login을 실행하세요." "ERROR"
        exit 1
    }
    Write-Log "✓ Expo 계정: $whoamiOutput" "SUCCESS"
    
    Write-Log "모든 필수 조건 확인 완료" "SUCCESS"
}

function Invoke-Build {
    param([string]$Profile)
    
    Write-Log "프로필 검증: $Profile" "INFO"
    $validProfiles = @("development", "preview", "staging", "production")
    if ($validProfiles -notcontains $Profile) {
        Write-Log "유효하지 않은 프로필입니다. 허용됨: $($validProfiles -join ', ')" "ERROR"
        exit 1
    }
    
    Write-Log "EAS APK 빌드 시작 (프로필: $Profile)" "INFO"
    Write-Log "빌드 서버: https://expo.dev" "INFO"
    Write-Log "빌드 시간: 약 15-30분" "INFO"
    Write-Log ""
    
    # 빌드 실행
    $buildCmd = "eas build --platform android --profile $Profile --non-interactive"
    Write-Log "명령어: $buildCmd" "VERBOSE"
    
    try {
        $output = & cmd /c "$buildCmd 2>&1"
        
        if ($LASTEXITCODE -ne 0) {
            Write-Log "빌드 실패:" "ERROR"
            Write-Host $output
            exit 1
        }
        
        Write-Log "빌드 출력:" "VERBOSE"
        Write-Host $output
        
        # 빌드 ID 추출 (EAS API 응답에서)
        $buildId = $output | Select-String -Pattern "Build (\w+) has" | ForEach-Object { $_.Matches.Groups[1].Value }
        
        if (-not $buildId) {
            Write-Log "빌드 ID를 추출할 수 없습니다. 수동으로 대시보드 확인: https://expo.dev/accounts/@{username}/builds" "WARNING"
            return $null
        }
        
        Write-Log "빌드 ID: $buildId" "SUCCESS"
        return $buildId
    }
    catch {
        Write-Log "빌드 명령어 실행 실패: $_" "ERROR"
        exit 1
    }
}

function Wait-BuildCompletion {
    param([string]$BuildId)
    
    if (-not $BuildId) {
        Write-Log "빌드 ID가 없습니다. 수동으로 진행 상황 모니터링하세요: https://expo.dev/accounts/@{username}/builds" "WARNING"
        return $null
    }
    
    Write-Log "빌드 진행 상황 폴링 시작..." "INFO"
    
    $maxAttempts = 180  # 30분 (10초 간격)
    $attempt = 0
    
    while ($attempt -lt $maxAttempts) {
        try {
            $statusJson = & eas build --status --json 2>&1 | ConvertFrom-Json -ErrorAction SilentlyContinue
            
            if ($statusJson -and $statusJson.builds) {
                $build = $statusJson.builds | Where-Object { $_.id -eq $BuildId } | Select-Object -First 1
                
                if ($build) {
                    $status = $build.status
                    Write-Log "[폴링 $($attempt+1)/$maxAttempts] 상태: $status" "INFO"
                    
                    if ($status -eq "finished") {
                        if ($build.result -eq "success") {
                            Write-Log "✓ 빌드 완료! (APK URL 추출 중...)" "SUCCESS"
                            return $build
                        }
                        else {
                            Write-Log "빌드 실패: $($build.result)" "ERROR"
                            return $null
                        }
                    }
                }
            }
        }
        catch {
            Write-Log "상태 조회 오류 (무시하고 계속): $_" "WARNING"
        }
        
        $attempt++
        Start-Sleep -Seconds 10
    }
    
    Write-Log "빌드 시간 초과 (30분)" "WARNING"
    Write-Log "https://expo.dev/accounts/@{username}/builds 에서 진행 상황 확인하세요" "INFO"
    return $null
}

function Download-Apk {
    param([string]$BuildId, [string]$OutputPath)
    
    Write-Log "APK 다운로드 준비 중..." "INFO"
    
    # 출력 디렉토리 생성
    if (-not (Test-Path $OutputPath)) {
        New-Item -ItemType Directory -Path $OutputPath -Force | Out-Null
        Write-Log "디렉토리 생성: $OutputPath" "SUCCESS"
    }
    
    if (-not $BuildId) {
        Write-Log "빌드 ID가 없어 자동 다운로드를 스킵합니다." "WARNING"
        Write-Log "EAS 대시보드에서 수동으로 다운로드: https://expo.dev/accounts/@{username}/builds" "INFO"
        return $false
    }
    
    try {
        # EAS 대시보드에서 APK URL 조회
        Write-Log "APK URL 조회 중..." "INFO"
        
        # Note: eas build --status가 URL을 포함해야 함
        # 실제 URL은 빌드 완료 후 대시보드에서 복사 필요
        
        $apkUrl = Read-Host "APK 다운로드 URL을 입력하세요 (또는 건너뛰려면 Enter)"
        
        if ([string]::IsNullOrWhiteSpace($apkUrl)) {
            Write-Log "APK 다운로드 스킵" "INFO"
            return $false
        }
        
        $outputFile = Join-Path $OutputPath "nadotongryoksa-v1.apk"
        Write-Log "다운로드: $apkUrl" "INFO"
        Write-Log "저장 위치: $outputFile" "INFO"
        
        # Invoke-WebRequest를 사용한 다운로드
        Invoke-WebRequest -Uri $apkUrl -OutFile $outputFile -UseBasicParsing
        
        if (Test-Path $outputFile) {
            $fileSize = (Get-Item $outputFile).Length / 1MB
            Write-Log "✓ APK 다운로드 완료: $([Math]::Round($fileSize, 2)) MB" "SUCCESS"
            return $true
        }
        else {
            Write-Log "APK 파일 생성 실패" "ERROR"
            return $false
        }
    }
    catch {
        Write-Log "APK 다운로드 실패: $_" "ERROR"
        return $false
    }
}

function Verify-Apk {
    param([string]$ApkPath)
    
    Write-Log "APK 검증 중..." "INFO"
    
    if (-not (Test-Path $ApkPath)) {
        Write-Log "APK 파일이 없습니다: $ApkPath" "ERROR"
        return $false
    }
    
    $fileSize = (Get-Item $ApkPath).Length
    
    # ZIP 파일 서명 확인 (APK는 ZIP 형식)
    $magic = [System.IO.File]::ReadAllBytes($ApkPath) | Select-Object -First 4
    $isZip = ($magic[0] -eq 0x50 -and $magic[1] -eq 0x4B)  # PK
    
    if ($fileSize -lt 1MB) {
        Write-Log "⚠ 경고: APK 파일 크기가 작습니다 ($([Math]::Round($fileSize/1KB, 2)) KB)" "WARNING"
        Write-Log "소스 번들일 수 있습니다. 실제 APK는 5-15 MB 크기입니다." "WARNING"
        return $false
    }
    
    if (-not $isZip) {
        Write-Log "⚠ 경고: APK가 ZIP 형식이 아닙니다" "WARNING"
        return $false
    }
    
    Write-Log "✓ APK 검증 성공 ($([Math]::Round($fileSize/1MB, 2)) MB)" "SUCCESS"
    return $true
}

# ==================== 메인 실행 ====================

Write-Log "========================================" "CYAN"
Write-Log "EAS APK 자동화 빌드 및 배포" "CYAN"
Write-Log "========================================" "CYAN"
Write-Log ""

try {
    # 1. 필수 조건 확인
    Test-Prerequisites
    Write-Log ""
    
    # 2. 빌드 (스킵 옵션 있으면 건너뜀)
    $buildId = $null
    if (-not $SkipBuild) {
        $buildId = Invoke-Build -Profile $Profile
        Write-Log ""
        
        # 3. 빌드 완료 대기
        $buildResult = Wait-BuildCompletion -BuildId $buildId
        Write-Log ""
    }
    else {
        Write-Log "빌드 스킵 (테스트 모드)" "WARNING"
    }
    
    # 4. APK 다운로드
    $downloadSuccess = Download-Apk -BuildId $buildId -OutputPath $OutputPath
    Write-Log ""
    
    # 5. APK 검증
    $apkPath = Join-Path $OutputPath "nadotongryoksa-v1.apk"
    if (Test-Path $apkPath) {
        Verify-Apk -ApkPath $apkPath
    }
    
    Write-Log ""
    Write-Log "========================================" "CYAN"
    Write-Log "빌드 프로세스 완료" "SUCCESS"
    Write-Log "========================================" "CYAN"
    Write-Log ""
    Write-Log "다음 단계:" "INFO"
    Write-Log "1. 마켓플레이스에서 APK 다운로드 테스트: http://127.0.0.1:3000/marketplace"
    Write-Log "2. 안드로이드 설치 및 실행 검증"
    Write-Log "3. 앱 기능 테스트 (음성 통역 등)"
    Write-Log ""
}
catch {
    Write-Log "오류 발생: $_" "ERROR"
    exit 1
}
