<#
.SYNOPSIS
    codeAI 전체 체크리스트 실검증 + 기동 스크립트
.DESCRIPTION
    PLANNER.md 미체크 항목 순서대로 검증합니다.
    검증 성공 시 [PASS], 실패 시 [FAIL] 출력.
    마지막에 docker compose up 전체 기동.
#>
param(
    [switch]$SkipBuild,
    [switch]$SkipDocker,
    [switch]$SkipTests
)

$ErrorActionPreference = "Continue"
$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path
$FRONTEND = Join-Path $ROOT "frontend\frontend"
$BACKEND = Join-Path $ROOT "backend"
$RESULTS = @()

function Log-Result {
    param([string]$Step, [bool]$Pass, [string]$Detail)
    $icon = if ($Pass) { "[PASS]" } else { "[FAIL]" }
    $color = if ($Pass) { "Green" } else { "Red" }
    Write-Host "$icon $Step - $Detail" -ForegroundColor $color
    $script:RESULTS += [PSCustomObject]@{Step=$Step; Pass=$Pass; Detail=$Detail}
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host " codeAI 전체 실검증 스크립트" -ForegroundColor Cyan
Write-Host " $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# ──────────────────────────────────────────────
# Step 1. 프론트엔드 빌드 검증
# ──────────────────────────────────────────────
Write-Host "─── Step 1: 프론트엔드 빌드 검증 ───" -ForegroundColor Yellow

if (-not $SkipBuild) {
    Push-Location $FRONTEND
    try {
        if (-not (Test-Path "node_modules")) {
            Write-Host "  npm install 실행 중..."
            npm install --legacy-peer-deps 2>&1 | Out-Null
        }
        Write-Host "  npm run build 실행 중..."
        $buildResult = npm run build 2>&1
        $buildExitCode = $LASTEXITCODE
        if ($buildExitCode -eq 0) {
            Log-Result "프론트엔드 빌드" $true "next build 성공"
        } else {
            $errorLines = ($buildResult | Select-String "Error|error" | Select-Object -First 5) -join "`n"
            Log-Result "프론트엔드 빌드" $false "빌드 실패: $errorLines"
        }
    } catch {
        Log-Result "프론트엔드 빌드" $false $_.Exception.Message
    }
    Pop-Location
} else {
    Write-Host "  (빌드 스킵)" -ForegroundColor DarkGray
}

# ──────────────────────────────────────────────
# Step 2. 백엔드 Python 임포트 검증
# ──────────────────────────────────────────────
Write-Host ""
Write-Host "─── Step 2: 백엔드 Python 임포트 검증 ───" -ForegroundColor Yellow

Push-Location $ROOT
try {
    # main.py 임포트
    $importResult = python -c "import backend.main; print('OK')" 2>&1
    if ($importResult -match "OK") {
        Log-Result "backend.main 임포트" $true "FastAPI app 로딩 성공"
    } else {
        Log-Result "backend.main 임포트" $false ($importResult -join " ")
    }
} catch {
    Log-Result "backend.main 임포트" $false $_.Exception.Message
}

try {
    # ArcFace 어댑터
    $arcfaceResult = python -c "from backend.movie_studio.quality.arcface_adapter import build_face_recognition_adapter; a,s = build_face_recognition_adapter(); print(f'adapter={s.get(\"adapter_name\")} available={a.is_available()}')" 2>&1
    if ($arcfaceResult -match "adapter=") {
        Log-Result "ArcFace 어댑터 로딩" $true $arcfaceResult
    } else {
        Log-Result "ArcFace 어댑터 로딩" $false ($arcfaceResult -join " ")
    }
} catch {
    Log-Result "ArcFace 어댑터 로딩" $false $_.Exception.Message
}

try {
    # ML 검출기
    $mlResult = python -c "from backend.movie_studio.quality.ml_detector_runtime import FaceEmbeddingDetectorRunner, HandLandmarkDetectorRunner; print(f'face={FaceEmbeddingDetectorRunner.detector_name} hand={HandLandmarkDetectorRunner.detector_name}')" 2>&1
    if ($mlResult -match "face=") {
        Log-Result "ML 검출기 런타임 로딩" $true $mlResult
    } else {
        Log-Result "ML 검출기 런타임 로딩" $false ($mlResult -join " ")
    }
} catch {
    Log-Result "ML 검출기 런타임 로딩" $false $_.Exception.Message
}

try {
    # 벡터 서비스
    $vectorResult = python -c "from backend.marketplace.vector_service import vector_service; print(f'VectorService loaded')" 2>&1
    if ($vectorResult -match "loaded") {
        Log-Result "VectorService 로딩" $true $vectorResult
    } else {
        Log-Result "VectorService 로딩" $false ($vectorResult -join " ")
    }
} catch {
    Log-Result "VectorService 로딩" $false $_.Exception.Message
}

try {
    # 코드 제너레이터
    $codegenResult = python -c "from backend.python_code_generator import SUPPORTED_PYTHON_PROFILES; print(f'profiles={len(SUPPORTED_PYTHON_PROFILES)}')" 2>&1
    if ($codegenResult -match "profiles=") {
        Log-Result "코드 제너레이터 프로필" $true $codegenResult
    } else {
        Log-Result "코드 제너레이터 프로필" $false ($codegenResult -join " ")
    }
} catch {
    Log-Result "코드 제너레이터 프로필" $false $_.Exception.Message
}

try {
    # 본인인증 프로바이더
    $authResult = python -c "from backend.services.auth_identity_provider import resolve_identity_provider; p=resolve_identity_provider('pass'); print(f'provider={p.provider_name} live={p._is_live_configured()}')" 2>&1
    if ($authResult -match "provider=") {
        Log-Result "본인인증 프로바이더" $true $authResult
    } else {
        Log-Result "본인인증 프로바이더" $false ($authResult -join " ")
    }
} catch {
    Log-Result "본인인증 프로바이더" $false $_.Exception.Message
}
Pop-Location

# ──────────────────────────────────────────────
# Step 3. pytest 통합 테스트
# ──────────────────────────────────────────────
Write-Host ""
Write-Host "─── Step 3: pytest 통합 테스트 ───" -ForegroundColor Yellow

if (-not $SkipTests) {
    Push-Location $ROOT
    try {
        $pytestResult = python -m pytest backend/tests/integration/ -v --tb=short 2>&1
        $pytestExit = $LASTEXITCODE
        if ($pytestExit -eq 0) {
            $passCount = ($pytestResult | Select-String "passed" | Select-Object -First 1)
            Log-Result "통합 테스트 (pytest)" $true "전체 통과: $passCount"
        } else {
            $failLines = ($pytestResult | Select-String "FAILED|ERROR" | Select-Object -First 5) -join "`n"
            Log-Result "통합 테스트 (pytest)" $false "실패: $failLines"
        }
    } catch {
        Log-Result "통합 테스트 (pytest)" $false $_.Exception.Message
    }
    Pop-Location
} else {
    Write-Host "  (테스트 스킵)" -ForegroundColor DarkGray
}

# ──────────────────────────────────────────────
# Step 4. Docker 빌드 검증
# ──────────────────────────────────────────────
Write-Host ""
Write-Host "─── Step 4: Docker 빌드 검증 ───" -ForegroundColor Yellow

if (-not $SkipDocker) {
    Push-Location $ROOT
    try {
        $dockerCheck = docker version 2>&1
        if ($LASTEXITCODE -eq 0) {
            Log-Result "Docker 엔진" $true "Docker 사용 가능"
        } else {
            Log-Result "Docker 엔진" $false "Docker 미실행"
        }
    } catch {
        Log-Result "Docker 엔진" $false "Docker 미설치"
    }

    try {
        Write-Host "  docker compose config 검증 중..."
        $configResult = docker compose config 2>&1
        if ($LASTEXITCODE -eq 0) {
            $serviceCount = ($configResult | Select-String "^\s{2}\w" | Measure-Object).Count
            Log-Result "docker-compose.yml 구성" $true "YAML 유효, 서비스 감지"
        } else {
            Log-Result "docker-compose.yml 구성" $false ($configResult | Select-Object -First 3) -join " "
        }
    } catch {
        Log-Result "docker-compose.yml 구성" $false $_.Exception.Message
    }

    try {
        Write-Host "  nogpu 오버라이드 검증 중..."
        $nogpuResult = docker compose -f docker-compose.yml -f docker-compose.nogpu.yml config 2>&1
        if ($LASTEXITCODE -eq 0) {
            Log-Result "docker-compose.nogpu.yml" $true "오버라이드 유효"
        } else {
            Log-Result "docker-compose.nogpu.yml" $false ($nogpuResult | Select-Object -First 3) -join " "
        }
    } catch {
        Log-Result "docker-compose.nogpu.yml" $false $_.Exception.Message
    }
    Pop-Location
} else {
    Write-Host "  (Docker 스킵)" -ForegroundColor DarkGray
}

# ──────────────────────────────────────────────
# Step 5. 전체 기동
# ──────────────────────────────────────────────
Write-Host ""
Write-Host "─── Step 5: 전체 기동 ───" -ForegroundColor Yellow

if (-not $SkipDocker) {
    Push-Location $ROOT
    try {
        Write-Host "  docker compose up -d --build 실행 중..."
        docker compose up -d --build 2>&1
        if ($LASTEXITCODE -eq 0) {
            Log-Result "전체 기동 (docker compose up)" $true "전체 서비스 기동 시작"
        } else {
            Log-Result "전체 기동 (docker compose up)" $false "기동 실패"
        }

        Write-Host "  30초 대기 후 헬스체크..."
        Start-Sleep -Seconds 30

        # 헬스체크
        try {
            $healthResult = Invoke-RestMethod -Uri "http://localhost:8000/api/health" -TimeoutSec 10 -ErrorAction Stop
            Log-Result "백엔드 헬스체크" $true "http://localhost:8000/api/health 응답 정상"
        } catch {
            Log-Result "백엔드 헬스체크" $false $_.Exception.Message
        }

        try {
            $mpResult = Invoke-WebRequest -Uri "http://localhost:3000" -TimeoutSec 10 -ErrorAction Stop
            if ($mpResult.StatusCode -eq 200) {
                Log-Result "마켓플레이스 프론트" $true "http://localhost:3000 응답 정상"
            }
        } catch {
            Log-Result "마켓플레이스 프론트" $false $_.Exception.Message
        }

        try {
            $adminResult = Invoke-WebRequest -Uri "http://localhost:3005" -TimeoutSec 10 -ErrorAction Stop
            if ($adminResult.StatusCode -eq 200) {
                Log-Result "Admin 프론트" $true "http://localhost:3005 응답 정상"
            }
        } catch {
            Log-Result "Admin 프론트" $false $_.Exception.Message
        }

        # 컨테이너 상태
        docker compose ps 2>&1

    } catch {
        Log-Result "전체 기동" $false $_.Exception.Message
    }
    Pop-Location
} else {
    Write-Host "  (Docker 기동 스킵)" -ForegroundColor DarkGray
}

# ──────────────────────────────────────────────
# 최종 리포트
# ──────────────────────────────────────────────
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host " 실검증 최종 리포트" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

$passCount = ($RESULTS | Where-Object { $_.Pass }).Count
$failCount = ($RESULTS | Where-Object { -not $_.Pass }).Count
$total = $RESULTS.Count

Write-Host ""
Write-Host "  전체: $total 건" -ForegroundColor White
Write-Host "  통과: $passCount 건" -ForegroundColor Green
Write-Host "  실패: $failCount 건" -ForegroundColor Red
Write-Host "  통과율: $([math]::Round($passCount/$total*100, 1))%" -ForegroundColor $(if ($failCount -eq 0) { "Green" } else { "Yellow" })
Write-Host ""

if ($failCount -gt 0) {
    Write-Host "  실패 항목:" -ForegroundColor Red
    $RESULTS | Where-Object { -not $_.Pass } | ForEach-Object {
        Write-Host "    - $($_.Step): $($_.Detail)" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "완료: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Cyan
