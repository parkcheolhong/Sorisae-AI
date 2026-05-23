# 🌍 GPS 연동 시스템 저장소 위치 및 구조 완전 분석

**정리일**: 2026-01-09
**저장소 경로**: `tmp/external_migrations/upstream_sources/run_all_shinsegye.py-main-20260505/`

---

## 📂 저장소 구조

```
tmp/external_migrations/upstream_sources/run_all_shinsegye.py-main-20260505/
│
├── 🌍 GPS 시스템
│   ├── ethical_gps_system.py                    ⭐ 국가별 윤리 기반 GPS
│   ├── cyber_detective_gps_radius.py            ⭐ 200km 근거리 사이버 수사
│   ├── sorisae_satellite_wifi_system.py         ⭐ 위성 기반 WiFi 연결
│   │
│   └── 관련 데모
│       ├── sorisae_gps_ethics_completion_report.py  (윤리 GPS 보고서)
│       └── sorisae_satellite_demo.py               (위성 데모)
│
└── projects_separated/
    └── cyber-detective/src/
        └── cyber_detective_gps_radius.py        (별도 복사본)
```

---

## 📍 파일별 상세 정보

### 1️⃣ **ethical_gps_system.py** ⭐ 핵심

```
경로: tmp/external_migrations/upstream_sources/run_all_shinsegye.py-main-20260505/
      ethical_gps_system.py

크기: ~500-700 라인

주요 클래스:
├── EthicalGPSSystem
│   ├── init_database()
│   ├── init_location_services()
│   ├── load_country_ethics_database()
│   ├── get_current_location()
│   ├── get_country_ethics_profile()
│   ├── apply_location_based_ethics()
│   ├── log_location_change()
│   └── display_applied_ethics()

기능:
✅ IP 기반 실제 위치 조회 (ipapi.co)
✅ 위치 시뮬레이션 (서울/도쿄/뉴욕/런던/베를린)
✅ 국가별 윤리 프로필 적용
✅ 법률 준수 검사
✅ SQLite 데이터베이스 저장
✅ 위치 변경 이력 추적

데이터베이스:
├── country_ethics (국가별 윤리)
├── ethics_log (윤리 적용 이력)
└── location_history (위치 변경 이력)

의존성:
├── geopy.geocoders.Nominatim  (주소 역지오코딩)
├── requests                    (HTTP 요청)
└── sqlite3                     (데이터 저장)
```

**용도**: 나도통역사 사용자 위치 기반 국가별 윤리 준수

---

### 2️⃣ **cyber_detective_gps_radius.py** ⭐ 고급

```
경로: tmp/external_migrations/upstream_sources/run_all_shinsegye.py-main-20260505/
      cyber_detective_gps_radius.py

크기: ~400-600 라인

주요 클래스:
├── GPSBasedCyberInvestigation
│   ├── calculate_distance(coord1, coord2)
│   └── analyze_gps_based_detection_probability()

주요 함수:
├── analyze_gps_based_detection_probability()    (지역별 탐지율)
├── analyze_ip_gps_correlation()                 (IP-GPS 상관분석)
├── simulate_200km_radius_investigation()        (200km 수사 시뮬)
├── analyze_evidence_collection_methods()        (증거 수집 방법)
├── show_success_probability_matrix()            (성공률 행렬)
└── calculate_success_probability()              (성공률 계산)

기능:
✅ GPS 좌표 간 거리 계산 (하버사인 공식)
✅ 지역별 탐지 확률 분석
   - 도시: 99% (±10m)
   - 교외: 85% (±50m)
   - 농촌: 70% (±200m)
   - 산간: 50% (±1km)
✅ IP+GPS 상관관계 분석
✅ 200km 반경 실제 사건 시뮬레이션
✅ 추적 방법별 정확도 비교
✅ 증거 확보 시간 예측

추적 방법:
├── GPS+IP 매칭
├── 셀룰러 기지국 추적
├── WiFi MAC 주소 추적
├── CCTV 얼굴인식
├── 위성 추적
└── 기업 네트워크 IP 분석

의존성:
├── math (거리 계산)
└── typing (타입 힌팅)
```

**용도**: 나도통역사 보안/추적 기능 (필요시)

---

### 3️⃣ **sorisae_satellite_wifi_system.py** ⭐ 인프라

```
경로: tmp/external_migrations/upstream_sources/run_all_shinsegyе.py-main-20260505/
      sorisae_satellite_wifi_system.py

크기: ~600-800 라인

주요 클래스:
├── SatelliteInfo (위성 정보)
│   ├── name
│   ├── latitude / longitude
│   ├── altitude
│   ├── signal_strength
│   ├── coverage_radius
│   └── status
│
└── SorisaeSatelliteWiFiSystem
    ├── find_optimal_satellite(user_lat, user_lon)
    ├── start_satellite_connection(user_lat, user_lon)
    ├── retry_connection(user_lat, user_lon, max_retries)
    ├── start_monitoring()
    └── calculate_distance(lat1, lon1, lat2, lon2)

기능:
✅ 5개 위성 데이터 관리
✅ 사용자 위치 기반 최적 위성 선택
✅ 신호 강도, 대역폭, 지연, 거리 기반 점수 계산
✅ 자동 재연결 (최대 3회)
✅ 실시간 신호 모니터링
✅ 멀티 위성 지원

위성 데이터 (예):
├── Starlink-42     (고도 550km, 커버리지 500km)
├── OneWeb-117      (고도 1200km, 커버리지 800km)
├── Kuiper-88       (고도 630km, 커버리지 600km)
├── Iridium-Next-42 (고도 780km, 커버리지 650km)
└── Viasat-3        (고도 35,786km, 커버리지 3000km)

의존성:
├── math (거리/점수 계산)
├── dataclasses (SatelliteInfo)
└── typing (타입 힌팅)
```

**용도**: 오프라인/원격지 인터넷 제공 (고급 기능)

---

### 📄 관련 문서

#### sorisae_gps_ethics_completion_report.py

```
경로: tmp/external_migrations/upstream_sources/run_all_shinsegyе.py-main-20260505/
내용: 윤리 GPS 시스템의 완성도 보고서
기능: 
  ✅ 통합 시스템 요약
  ✅ 5개 국가 윤리 예시
  ✅ 다국어 응답 샘플
```

#### sorisae_satellite_demo.py

```
경로: tmp/external_migrations/upstream_sources/run_all_shinsegyе.py-main-20260505/
내용: 위성 시스템 데모
기능:
  ✅ 3개 글로벌 위치 테스트
  ✅ 자동 데모 시퀀스
  ✅ 신호 강도 시뮬레이션
```

---

## 🎯 나도통역사에 통합 가능한 기능

### 현재 가능한 것 (구현됨)
✅ GPS 기반 국가 감지 (ethical_gps_system.py)
✅ 국가별 언어/문화 자동 적응
✅ 오프라인 지역 위성 인터넷 제공 (sorisae_satellite_wifi_system.py)

### 구현 필요한 것 (고객 제품 기준 미연동)
✅ 범용 외부검색 API의 Google Maps 리뷰 검색 엔드포인트는 존재
✅ 관리자 패널에서는 위 API 호출 가능
❌ 호텔/공항/식당 전용 POI 데이터베이스
❌ 거리 기반 검색 (반경 N km 내)
❌ 실시간 예약 시스템
❌ 나도통역사 지도 UI 통합 (Google Maps, Naver)

---

## 💡 통합 방법

### 방법 1: 기존 GPS 시스템 활용

```python
# ethical_gps_system.py 활용
from ethical_gps_system import EthicalGPSSystem

gps = EthicalGPSSystem()
gps.apply_location_based_ethics()

current_location = gps.current_location  # {'latitude': ..., 'longitude': ..., 'country': ...}
current_country = gps.current_country    # 'KR' / 'US' / 'JP' ...
ethics_profile = gps.current_ethics_profile
```

### 방법 2: GPS + 번역 통합

```python
# 나도통역사 마켓플레이스에 추가
from ethical_gps_system import EthicalGPSSystem
from sorisae_interpreter import SorisaeInterpreter

gps = EthicalGPSSystem()
location = gps.apply_location_based_ethics()

# 위치 기반 인사말 번역
interpreter = SorisaeInterpreter()
greeting = {
    'KR': '안녕하세요!',
    'US': 'Hi!',
    'JP': 'こんにちは!',
    'CN': '你好!',
}[location['country_code']]

# 해당 국가 언어로 자동 인사
print(greeting)
```

### 방법 3: 위성 인터넷 백업

```python
# 오프라인 지역에서 위성으로 자동 전환
from sorisae_satellite_wifi_system import SorisaeSatelliteWiFiSystem

sat_system = SorisaeSatelliteWiFiSystem()
optimal_sat = sat_system.find_optimal_satellite(
    user_lat=37.5665,  # 현재 위치
    user_lon=126.9780
)

if optimal_sat:
    sat_system.start_satellite_connection(37.5665, 126.9780)
    # → 위성으로 인터넷 제공
```

---

## 📋 다음 단계 (로드맵)

| 단계 | 작업 | 파일 | 우선순위 |
|------|------|------|---------|
| 1️⃣ | POI DB 통합 | `location_service.py` (신규) | 🔴 높음 |
| 2️⃣ | 거리 검색 | `nearby_search.py` (신규) | 🔴 높음 |
| 3️⃣ | 기존 GPS + 번역 연동 | `nadotongryoksa/location.ts` (수정) | 🟠 중간 |
| 4️⃣ | 위성 폴백 | `hybrid_interpreter_system.py` (수정) | 🟡 낮음 |
| 5️⃣ | 실시간 예약 UI | `marketplace/nadotongryoksa/page.tsx` (확장) | 🟡 낮음 |

---

## ✅ 최종 결론

**현재 상태**:
- ✅ GPS 기반 윤리 시스템 완성
- ✅ GPS 기반 수사 시스템 완성
- ✅ GPS 기반 위성 시스템 완성
- ✅ 백엔드 범용 지도 검색 API 존재
- ❌ **호텔/공항/식당 위치 검색은 나도통역사 고객 경로에 아직 미연동**

**모든 파일이 위치**:
`tmp/external_migrations/upstream_sources/run_all_shinsegyе.py-main-20260505/`

**다음 구현**: POI (Point of Interest) 데이터베이스 + 거리 기반 검색 추가
