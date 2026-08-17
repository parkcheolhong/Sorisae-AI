# Critical 2: EAS/AAB APK 빌드 플랜

## 📋 현황 분석

### 문제
- 마켓플레이스의 현재 `nadotongryoksa-v1.apk` (11KB)는 **ZIP 소스 번들**
- 실제 설치 불가능한 배포물
- 상용 판매를 위해 진정한 APK 필요

### 프로젝트 구조

```
apps/mobile-nadotongryoksa/
├── app.json                 # Expo 설정 (bundle: com.shinsegye.nadotongryoksa)
├── eas.json                 # EAS 빌드 프로필 (preview, staging, production)
├── package.json             # NPM scripts (eas:android:preview, etc.)
├── src/                     # React Native 소스코드
└── assets/                  # 아이콘, 스플래시 이미지
```

### 빌드 프로필 현황

| 프로필 | buildType | 용도 | APK? |
|--------|-----------|------|------|
| development | apk | 개발 (developmentClient) | ✅ |
| **preview** | **apk** | 내부 테스트 | **✅** |
| **staging** | **apk** | 프리-프로덕션 | **✅** |
| production | app-bundle | 스토어 배포 | ❌ (AAB) |

---

## 🎯 빌드 플랜

### Phase 1: EAS CLI 준비 (1분)

```bash
npm install -g eas-cli@latest
eas login  # Expo 계정 인증
```

### Phase 2: preview 프로필로 APK 빌드 (15-30분)

```bash
cd apps/mobile-nadotongryoksa
npm run eas:android:preview
# or directly:
# eas build --platform android --profile preview
```

**특징:**
- 빌드 시간: 15-30분 (EAS 클라우드에서)
- 결과: 설치 가능한 진정한 APK
- 배포: 내부 테스트 전용 (내부 배포 채널)
- URL 반환: 빌드 완료 후 다운로드 가능

### Phase 3: APK 배포 (2분)

```bash
# 빌드 완료 후 APK 다운로드
wget <APK_URL> -O uploads/marketplace_local/apk/nadotongryoksa-v1.apk

# 또는 수동 다운로드 후 복사
cp ~/Downloads/nadotongryoksa-*.apk uploads/marketplace_local/apk/nadotongryoksa-v1.apk
```

### Phase 4: 검증 (2분)

```bash
# 파일 크기 확인 (5MB+ 예상)
ls -lh uploads/marketplace_local/apk/nadotongryoksa-v1.apk

# 마켓플레이스 다운로드 테스트
# http://127.0.0.1:3000/marketplace → APK 다운로드 → 설치 검증
```

---

## ⚙️ 자동화 스크립트

### 옵션 1: PowerShell 자동화 (Windows)
- **파일**: `build_apk_automated.ps1`
- **기능**:
  - EAS CLI 버전 확인
  - preview 프로필 빌드 트리거
  - 빌드 상태 폴링 (10초 마다)
  - 완료 후 APK URL에서 다운로드
  - 자동 배포 (uploads/marketplace_local/apk/)

### 옵션 2: Node.js/Bash 자동화
- **파일**: `build_apk_automated.sh`
- **기능**: 동일 (Linux/macOS 환경)

### 옵션 3: GitHub Actions 자동화 (CI/CD)
- **파일**: `.github/workflows/build-apk.yml`
- **기능**:
  - 커밋 시 자동 빌드
  - 스케줄 빌드 (주간)
  - 빌드 결과 이메일 알림

---

## 🔧 선택지별 가이드

### ✅ 추천: PowerShell 자동화 (build_apk_automated.ps1)
**장점:**
- Windows 환경에 최적화
- 별도 설치 불필요 (PowerShell 내장)
- 실시간 진행 상황 표시
- 오류 시 자동 재시도

**조건:**
- EAS CLI 설치 필수: `npm install -g eas-cli@latest`
- Expo 계정 인증 필수: `eas login`
- Node.js >= 18.0.0

**실행:**

```powershell
cd C:\Users\WORK\source\repos\parkcheolhong\codeAI
powershell -NoProfile -ExecutionPolicy Bypass -File .\build_apk_automated.ps1
```

### 대안: EAS 클라우드 웹 대시보드
**URL**: <https://expo.dev/@{username}/nadotongryoksa>
- 웹에서 빌드 관리
- 진행 상황 실시간 모니터링
- 빌드 히스토리 관리
- 복잡한 자동화 불필요

---

## 📅 타이밍

| 단계 | 소요 시간 | 누적 시간 |
|------|----------|---------|
| EAS 인증 | 1분 | 1분 |
| APK 빌드 (EAS 클라우드) | 20분 | 21분 |
| APK 다운로드 | 2분 | 23분 |
| 배포 및 검증 | 2분 | **25분** |

**전체 소요 시간: ~25분 (첫 빌드 기준)**

---

## 🚀 다음 단계

### 즉시 필요한 조치
1. ✅ 이 플랜 읽기 (지금)
2. ⏭️ `build_apk_automated.ps1` 생성 및 실행
3. ⏭️ APK 배포 및 마켓플레이스 테스트

### 보조 조치 (선택)
- GitHub Actions 워크플로우 설정 (자동 주간 빌드)
- APK 버전 관리 (nadotongryoksa-v1.1.0.apk 등)
- 앱 서명 인증서 설정 (스토어 배포 시)

---

## 📞 문제 해결

### EAS 로그인 실패

```powershell
eas logout
eas login
```

### 빌드 실패

```
상태: EAS 대시보드에서 빌드 로그 확인
https://expo.dev/@{username}/nadotongryoksa/builds
```

### APK 다운로드 실패

```powershell
# 직접 다운로드 (수동)
Start-Process "https://expo.dev/accounts/{username}/builds"
```

---

## 결과물

### 최종 상태

```
✅ uploads/marketplace_local/apk/nadotongryoksa-v1.apk
   ├─ 크기: 5-15 MB (실제 APK)
   ├─ 형식: ZIP + Android 바이너리
   ├─ 서명: EAS 자동 서명
   └─ 설치: 안드로이드 디바이스/에뮬레이터 설치 가능
```

### 검증
- ✅ 마켓플레이스에서 다운로드 가능
- ✅ 안드로이드 설치 가능
- ✅ 앱 실행 가능 (나도통역사)
