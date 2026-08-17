# daytrade-ai C++ 코어 빌드 (Windows).
#
# 기본 전략:
#   - CMakePresets.json 의 windows-ninja-release 프리셋을 우선 사용(VS Code/CLI 경로 단일화).
#   - 프리셋이 없거나 실패할 때만 레거시 생성기 자동 감지로 fallback.
#   - cmake 가 PATH 에 없으면 pip 설치본을 사용:  python -m pip install cmake
#
# 사용:  pwsh cpp/build.ps1
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$app = Split-Path -Parent $here

# --- Python: 이 스크립트를 부른 python 을 SSOT 로 고정(다중 버전 혼선 방지) ---
$py = (python -c "import sys; print(sys.executable)").Trim()
Write-Host "[info] python = $py"

python -m pip install --quiet pybind11 cmake
$pybind = (python -m pybind11 --cmakedir).Trim()

# cmake 실행기(PATH 우선, 없으면 pip 설치본).
$cmakeExe = (Get-Command cmake -ErrorAction SilentlyContinue).Source
if (-not $cmakeExe) { $cmakeExe = (python -c "import cmake,os;print(os.path.join(os.path.dirname(cmake.__file__),'data','bin','cmake.exe'))").Trim() }
Write-Host "[info] cmake = $cmakeExe"

# --- 프리셋 우선 빌드 (VS Code CMake Tools 와 동일 경로) ---
$presetName = "windows-ninja-release"
$presetPath = Join-Path $here "CMakePresets.json"
$configuredWithPreset = $false

if (Test-Path $presetPath) {
  try {
    Write-Host "[info] preset 우선 빌드 사용: $presetName"
    & $cmakeExe --preset $presetName -Dpybind11_DIR="$pybind" -DPython_EXECUTABLE="$py" -Wno-dev
    & $cmakeExe --build --preset $presetName
    $configuredWithPreset = $true
  } catch {
    Write-Warning "프리셋 빌드 실패. 레거시 생성기 경로로 fallback 합니다: $($_.Exception.Message)"
    $configuredWithPreset = $false
  }
}

if (-not $configuredWithPreset) {
  # --- 레거시 fallback: 생성기 자동 감지 ---
  $genArgs = @()
  if (Get-Command cl.exe -ErrorAction SilentlyContinue) {
    Write-Host "[info] MSVC(cl.exe) 감지 → 기본 생성기 사용"
  } else {
    $gpp = Get-Command g++ -ErrorAction SilentlyContinue
    if (-not $gpp) {
      # winget WinLibs 설치 경로에서 탐색.
      $found = Get-ChildItem -Path "$env:LOCALAPPDATA\Microsoft\WinGet\Packages" -Recurse -Filter "g++.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
      if ($found) { $env:Path = (Split-Path $found.FullName) + ";" + $env:Path; $gpp = Get-Command g++ -ErrorAction SilentlyContinue }
    }
    if (-not $gpp) {
      Write-Error "C++ 컴파일러를 찾지 못했습니다. MSVC Build Tools 또는 MinGW-w64 를 설치하세요. (winget install BrechtSanders.WinLibs.POSIX.UCRT)"
    }
    Write-Host "[info] MinGW(g++) 감지 → 'MinGW Makefiles' 생성기 사용: $($gpp.Source)"
    $genArgs = @("-G", "MinGW Makefiles")
  }

  & $cmakeExe -S $here -B "$here/build" @genArgs -Dpybind11_DIR="$pybind" -DPython_EXECUTABLE="$py" -DCMAKE_BUILD_TYPE=Release -Wno-dev
  & $cmakeExe --build "$here/build" --config Release
}

# 빌드 산출물(.pyd)을 패키지 루트로 복사 → `import daytrade_cpp` 가능.
$pyd = Get-ChildItem -Path "$here/build" -Recurse -Include "daytrade_cpp*.pyd" | Select-Object -First 1
if ($pyd) {
  Copy-Item $pyd.FullName -Destination $app -Force
  Write-Host "[OK] copied $($pyd.Name) -> $app"
  # 골든 동일성 테스트 자동 실행(Python 레퍼런스 대비 1e-9 수치 일치 검증)
  Write-Host "[RUN] golden equivalence test ..."
  Push-Location $app
  python -m pytest tests/test_cpp_golden.py -q
  $code = $LASTEXITCODE
  Pop-Location
  if ($code -eq 0) { Write-Host "[OK] 골든 동일성 통과 — C++ 코어가 Python 레퍼런스와 일치합니다." }
  else { Write-Warning "골든 테스트 실패(exit=$code). 수치 동일성 회귀를 확인하세요." }
} else {
  Write-Warning "빌드 산출물(.pyd)을 찾지 못했습니다. 빌드 로그를 확인하세요."
}
