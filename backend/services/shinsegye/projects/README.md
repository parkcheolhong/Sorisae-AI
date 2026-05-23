# 신세계 프로젝트 분리 폴더 구조
# Shinsegye Projects Separated Structure

> **생성일**: 2025년 12월 05일 10:04:34  
> **총 프로젝트 수**: 18

---

## 📋 프로젝트 목록


### Business

- **[토목 입찰 시스템](civil-bidding/README.md)** (Civil Engineering Bidding)
  - AI 기반 건설 프로젝트 입찰 분석
  - Port: 5055
  - 파일 수: 2
- **[쇼핑몰 시스템](shopping-mall/README.md)** (Shopping Mall System)
  - 7개 AI 에이전트 자율 쇼핑몰 (소피움 에이아이)
  - Port: 5057
  - 파일 수: 3

### Core Systems

- **[소리새 핵심](sorisae-core/README.md)** (Sorisae Core System)
  - Two-Cycle Brain AI 핵심 시스템
  - Port: 5050
  - 파일 수: 25
- **[음성 처리](voice-processing/README.md)** (Voice Processing)
  - 음성 인식 및 처리 시스템
  - No Web UI
  - 파일 수: 7

### Creative Tools

- **[4D 영화 제작](movie-studio/README.md)** (4D Movie Studio)
  - 음성 기반 4D 영화 제작 시스템
  - Port: 5000
  - 파일 수: 4
- **[작사/작곡](music-composer/README.md)** (Music Composer)
  - AI 기반 음악 작곡 및 작사 시스템
  - Port: 5061
  - 파일 수: 4
- **[애니메이션 스튜디오](animation-studio/README.md)** (Animation Studio)
  - AI 기반 애니메이션 제작
  - Port: 5062
  - 파일 수: 4

### Development Support

- **[개발 도구](dev-tools/README.md)** (Development Tools)
  - 코드 분석 및 개선 도구
  - No Web UI
  - 파일 수: 18
- **[테스트/검증](testing/README.md)** (Testing & Validation)
  - 테스트 및 검증 도구
  - No Web UI
  - 파일 수: 16

### Finance

- **[투자 어드바이저](investment-advisor/README.md)** (Investment Advisor)
  - 듀얼브레인 AI 투자 조언 (200% 수익률)
  - Port: 5058
  - 파일 수: 2

### Gaming

- **[게임 경제 시스템](game-economy/README.md)** (Game Economy System)
  - 세계 최초 '게임으로 먹고살기' 플랫폼
  - Port: 5056
  - 파일 수: 4
- **[VR/게임](vr-games/README.md)** (VR & Games)
  - VR 및 게임 생성 시스템
  - Port: 5065
  - 파일 수: 3

### Infrastructure

- **[위성 시스템](satellite/README.md)** (Satellite System)
  - 차세대 인공위성 WiFi 시스템
  - Port: 5059
  - 파일 수: 4

### IoT

- **[IoT 스마트홈](iot-smarthome/README.md)** (IoT Smart Home)
  - 스마트홈 디바이스 제어 시스템
  - Port: 5053
  - 파일 수: 6

### Language Processing

- **[나도 통역사](interpreter/README.md)** (Multi-Language Interpreter)
  - 실시간 13개 언어 통역 시스템
  - Port: 5051
  - 파일 수: 6

### Security & Analysis

- **[사이버 탐정](cyber-detective/README.md)** (Cyber Detective)
  - AI 기반 사이버 수사 시스템
  - Port: 5052
  - 파일 수: 12
- **[GPS & 경찰 시스템](gps-police/README.md)** (GPS & Police System)
  - 윤리적 GPS 추적 및 경찰 시스템
  - Port: 5063
  - 파일 수: 5
- **[보안 시스템](security/README.md)** (Security System)
  - 다층 보안 시스템
  - Port: 5064
  - 파일 수: 5

---

## 🚀 사용 방법

### 1. 전체 시스템 실행
```bash
# 루트 디렉토리에서
python run_all_shinsegye.py
```

### 2. 개별 프로젝트 실행
```bash
# 프로젝트 폴더에서
cd projects_separated/[프로젝트명]
python run_[프로젝트명].py

# 예시
cd projects_separated/sorisae-core
python run_sorisae_core.py
```

### 3. Docker로 실행
```bash
# 개별 프로젝트
docker-compose -f dockerfiles/docker-compose.all-projects.yml up [서비스명]

# 전체 시스템
docker-compose -f dockerfiles/docker-compose.all-projects.yml up
```

---

## 📁 폴더 구조

각 프로젝트 폴더는 다음과 같은 구조를 가집니다:

```
project-name/
├── src/                 # 소스 파일 (심볼릭 링크)
├── docs/                # 문서
├── data/                # 데이터 파일
├── config/              # 설정 파일
├── README.md            # 프로젝트 설명
├── requirements.txt     # 의존성
└── run_project_name.py  # 실행 스크립트
```

---

## 🔗 관련 문서

- [전체 시스템 README](../README.md)
- [설치 가이드](../INSTALL.md)
- [빠른 시작](../QUICKSTART.md)
- [Docker 가이드](../dockerfiles/README.md)
- [프로그램 분류](../programs_by_category/README.md)

---

## 📝 참고사항

1. **심볼릭 링크**: 실제 소스 파일은 루트 디렉토리에 위치하며, 각 프로젝트의 `src/` 폴더에는 심볼릭 링크로 연결됩니다.
2. **의존성**: 각 프로젝트의 `requirements.txt`는 해당 프로젝트에 필요한 최소 의존성만 포함합니다. 전체 의존성은 루트의 `requirements.txt`를 참고하세요.
3. **독립 실행**: 각 프로젝트는 독립적으로 실행 가능하도록 설계되었지만, 일부 프로젝트는 다른 모듈에 대한 의존성이 있을 수 있습니다.

---

**버전**: 1.0.0  
**상태**: ✅ 프로덕션 준비 완료
