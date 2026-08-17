# 🌍 GPS 연동 서비스 구조 분석

**확인일**: 2026-01-09
**위치**: `tmp/external_migrations/upstream_sources/run_all_shinsegye.py-main-20260505/`

---

## 📍 현재 구현된 GPS 시스템 (3가지)

### 1️⃣ **윤리 기반 GPS 시스템** (`ethical_gps_system.py`)
**용도**: GPS 위치 기반 국가별 윤리의식 & 법률 준수

#### 윤리 GPS 핵심 기능

```python
class EthicalGPSSystem:
    """GPS 기반 윤리의식 및 법률 준수 시스템"""
    
    - init_location_services()
      → GPS 위치 서비스 초기화
      → Nominatim 지오코더 사용
    
    - get_current_location()
      → 현재 위치 확인 (실제 또는 시뮬레이션)
      → IP 기반 위치 조회 (ipapi.co)
      → 위도/경도/국가코드/도시 반환
    
    - apply_location_based_ethics()
      → 위치 기반 윤리 프로필 적용
      → 국가별 법률 준수 검사
      → 문화적 맥락 반영
```

#### 지원 국가 (시뮬레이션 예시)

```python
- 서울 (37.5665°N, 126.9780°E) - 한국
- 도쿄 (35.6762°N, 139.6503°E) - 일본
- 뉴욕 (40.7128°N, -74.0060°W) - 미국
- 런던 (51.5074°N, -0.1278°W) - 영국
- 베를린 (52.5200°N, 13.4050°E) - 독일
```

#### 윤리 프로필 적용 항목

```
🇰🇷 한국: 높임말 문화, KPIPA 준수
🇺🇸 미국: 직접적 소통, COPPA/HIPAA
🇯🇵 일본: 극존댓말, APPI 준수
🇩🇪 독일: 정중한 표현, GDPR
```

**상태**: ⏳ **구현됨 (시뮬레이션)**

---

### 2️⃣ **GPS 기반 사이버 수사 시스템** (`cyber_detective_gps_radius.py`)
**용도**: GPS + IP 연동 200km 근거리 수사

#### 사이버 수사 GPS 핵심 기능

```python
class GPSBasedCyberInvestigation:
    """GPS 기반 사이버수사 시스템"""
    
    - calculate_distance(coord1, coord2)
      → 두 GPS 좌표 간 직선거리 계산
      → 하버사인 공식 사용
    
    - analyze_gps_based_detection_probability()
      → 지역별 탐지 확률 분석
      → 도시/교외/농촌/산간 지역
    
    - simulate_200km_radius_investigation()
      → 200km 반경 수사 시뮬레이션
      → 실제 사건 케이스 분석
```

#### 지역별 탐지 능력

```
🏙️ 도시 지역 (±10m):
   - GPS+IP 매칭: 95%
   - 셀룰러 기지국: 90%
   - WiFi MAC: 85%
   - CCTV 얼굴인식: 80%
   - 종합: 99%
   - 시간: 실시간-30분

🏘️ 교외 지역 (±50m):
   - GPS+IP 매칭: 80%
   - 셀룰러 기지국: 75%
   - WiFi MAC: 60%
   - 종합: 85%
   - 시간: 30분-2시간

🌾 농촌 지역 (±200m):
   - GPS+IP 매칭: 60%
   - 셀룰러 기지국: 50%
   - WiFi MAC: 30%
   - 종합: 70%
   - 시간: 2-6시간

⛰️ 산간/격오지 (±1km):
   - GPS+IP 매칭: 40%
   - 위성 추적: 70%
   - 종합: 50%
   - 시간: 6-24시간
```

#### 실제 사건 시뮬레이션

```python
# 탐사 중심점: 서울 (37.5515°N, 126.9753°E)

사건 1: 온라인 사기
  위치: 서울 (약 10km)
  성공률: 99%

사건 2: 해킹 그룹
  위치: 경기도 (약 50km)
  성공률: 90%

사건 3: 마약 거래
  위치: 수원 (약 40km)
  성공률: 88%

사건 4: 온라인 명예훼손
  위치: 대전 (약 140km)
  성공률: 75%
```

**상태**: ⏳ **구현됨 (시뮬레이션)**

---

### 3️⃣ **위성 WiFi 시스템** (`sorisae_satellite_wifi_system.py`)
**용도**: GPS 기반 위성 인터넷 연결

#### 위성 WiFi 핵심 기능

```python
class SorisaeSatelliteWiFiSystem:
    """소리새 차세대 인공위성 와이파이 시스템"""
    
    - find_optimal_satellite(user_lat, user_lon)
      → 사용자 위치 기준 최적 위성 찾기
      → 신호 강도, 대역폭, 지연, 거리 점수 계산
    
    - start_satellite_connection(user_lat, user_lon)
      → 위성 인터넷 연결 시작
      → GPS 좌표 기반 위성 선택
    
    - retry_connection()
      → 자동 재연결 (최대 3회)
      → 커버리지 내 다른 위성 시도
```

#### 위성 데이터

```python
# 활성 위성 5개

위성 1: Starlink-42
  위도: 38.2°N, 경도: 125.5°E
  고도: 550km, 신호강도: -95dBm
  커버리지: 500km 반경

위성 2: OneWeb-117
  위도: 35.2°N, 경도: 128.3°E
  고도: 1200km, 신호강도: -92dBm
  커버리지: 800km 반경

... (3개 더)
```

#### 글로벌 테스트 위치

```python
demo_scenarios = [
    {
        'location': '서울, 대한민국',
        'lat': 37.5665,
        'lon': 126.9780,
        'description': '도심에서의 고속 인터넷'
    },
    {
        'location': '에베레스트 베이스캠프',
        'lat': 28.0026,
        'lon': 86.8528,
        'description': '극한 환경에서의 연결'
    },
    {
        'location': '사하라 사막 중심부',
        'lat': 23.8060,
        'lon': 11.1540,
        'description': '극한 환경에서의 연결'
    }
]
```

**상태**: ⏳ **구현됨 (데모)**

---

## 📍 나도통역사 위치 기반 서비스 (부분 구현, 제품 미연동)

현재 구현된 GPS 시스템들은 주로 **보안/윤리/통신** 중심이며, 지도 검색 인프라는 일부 존재하지만 **나도통역사 고객 경로에는 연결되지 않았습니다**.

**현재 확인된 상태**:
- ✅ 백엔드 범용 외부검색 API에 Google Maps 리뷰 검색 엔드포인트 존재 (`/api/external-search/maps-reviews`)
- ✅ 관리자 LLM 패널에서 위 엔드포인트 호출 가능
- ❌ 나도통역사 모바일/마켓플레이스 화면에는 지도/POI 호출 코드 없음
- ❌ 호텔/공항/식당/관광명소 전용 도메인 모델, 거리 검색, 예약 흐름 없음

**사용자가 요청한 기능** (고객 제품 기준 아직 미구현):
- 🏨 근처 **호텔** 검색 및 예약
- ✈️ 근처 **공항** 정보
- 🍽️ 근처 **식당** 추천
- 🎯 근처 **관광 명소** 가이드
- 🗺️ **지도 통합** (Google Maps, 네이버 지도)

---

## 🎯 위치 기반 서비스 구현 로드맵

### Phase 1: POI (Point of Interest) 데이터베이스

```python
class LocationBasedService:
    def __init__(self):
        self.places = {
            'hotel': [],      # 호텔 DB
            'airport': [],    # 공항 DB
            'restaurant': [], # 식당 DB
            'attraction': []  # 관광명소 DB
        }
    
    def load_poi_database(self):
        """POI 데이터 로드"""
        # Google Places API
        # Naver Map API
        # OpenStreetMap (OSM)
```

### Phase 2: 거리 기반 검색

```python
def find_nearby_places(lat, lon, category, radius=1000):
    """GPS 좌표 기반 근처 장소 검색"""
    # 1. 현재 GPS 위치 취득
    # 2. POI DB에서 반경 내 장소 검색
    # 3. 거리순 정렬 & 추천 점수 계산
    # 4. 다국어 설명 반환
```

### Phase 3: 통역사 통합

```python
def translate_poi_info(place_info, source_lang='ko', target_lang='en'):
    """POI 정보 다국어 번역"""
    # 호텔/식당 정보
    # 리뷰 번역
    # 영업 시간 다국어화
    # 예약 가이드
```

### Phase 4: 실시간 예약

```python
def book_nearby_hotel(hotel_id, checkin, checkout, guests):
    """근처 호텔 실시간 예약"""
    # 가용성 확인
    # 가격 조회
    # 예약 확정
    # 확인 번역
```

---

## 📋 구현 우선순위

| 우선순위 | 기능 | 예상 시간 | 복잡도 |
|---------|------|---------|------|
| 1️⃣ | POI 데이터베이스 | 1-2주 | 중간 |
| 2️⃣ | 거리 기반 검색 | 1주 | 낮음 |
| 3️⃣ | 다국어 통역 연동 | 1주 | 낮음 |
| 4️⃣ | 예약 시스템 | 2-3주 | 높음 |
| 5️⃣ | 실시간 지도 표시 | 1-2주 | 중간 |

---

## 🔧 필요한 외부 API

```python
# 지도 & POI
- Google Places API
- Naver Map API
- Kakao Map API
- OpenStreetMap (무료)

# 예약 시스템
- Booking.com API
- Agoda API
- Airbnb API
- 항공사 API

# 번역
- 기존 SorisaeInterpreter (내부)
- Google Translate API (백업)
```

---

## 📝 결론

**현재 상태**:
- ✅ GPS 기반 윤리 시스템 구현
- ✅ GPS 기반 수사 시스템 구현
- ✅ GPS 기반 위성 연결 구현
- ✅ 백엔드에 범용 Google Maps 리뷰 검색 API 존재
- ❌ **나도통역사 고객 제품에서 호텔/공항/식당/관광 POI 검색은 아직 미연동**
- ❌ 지도 UI, 반경 검색, 예약 플로우는 아직 미구현

**다음 단계**:
1. POI 데이터 통합 (Google Places, Naver Map, OSM)
2. 거리 기반 필터링 및 검색 로직 구현
3. 기존 번역 시스템 통합
4. 실시간 지도 UI 추가
5. 예약 시스템 연동

**예상 개발 기간**: 6-8주 (풀타임 기준)
