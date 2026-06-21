"""관광 KG 시드 — 27개 도시 축제/음식 큐레이션 데이터를 Postgres 인접테이블에 멱등 적재.

사용:
  # 호스트(컨테이너 밖)에서 실행 시 DATABASE_URL 을 127.0.0.1:5432 로 지정
  $env:DATABASE_URL="postgresql://admin:changeme@127.0.0.1:5432/devanalysis114"
  python scripts/seed_tourism_graph.py

데이터 성격: 널리 알려진 공개 사실(대표 축제·향토 음식)만 보수적으로 큐레이션.
도시 id/좌표/국가코드는 ingest 의 CITY_REGISTRY 를 그대로 사용해 POI(Qdrant)와 정합.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from typing import Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.ingest_tourism_city import CITY_REGISTRY  # noqa: E402
from backend.services.tourism_kb.graph import get_tourism_graph  # noqa: E402

# city_id -> [(name, month|None, season, description)]
CITY_FESTIVALS: Dict[str, List[Tuple[str, int | None, str, str]]] = {
    "seoul": [
        ("연등회 (Lotus Lantern Festival)", 5, "spring", "부처님오신날 전후 종로 일대 등불 행렬. 유네스코 인류무형문화유산."),
        ("서울빛초롱축제", 11, "autumn", "청계천 일대 등불 전시 야간 축제."),
    ],
    "busan": [
        ("부산국제영화제 (BIFF)", 10, "autumn", "아시아 대표 영화제. 해운대·영화의전당 중심."),
    ],
    "jeju": [
        ("제주들불축제", 3, "spring", "정월대보름 즈음 새별오름 들불 점화 행사."),
    ],
    "incheon": [
        ("인천 펜타포트 락 페스티벌", 8, "summer", "국내 대표 여름 록 음악 축제."),
    ],
    "tokyo": [
        ("산자 마쓰리 (Sanja Matsuri)", 5, "spring", "아사쿠사 신사 대표 마쓰리. 미코시 행렬."),
        ("스미다강 불꽃축제", 7, "summer", "도쿄 대표 여름 하나비(불꽃) 축제."),
    ],
    "osaka": [
        ("덴진 마쓰리 (Tenjin Matsuri)", 7, "summer", "일본 3대 마쓰리. 배 행렬과 불꽃."),
        ("기시와다 단지리 마쓰리", 9, "autumn", "거대한 단지리 수레를 끄는 역동적 축제."),
    ],
    "kyoto": [
        ("기온 마쓰리 (Gion Matsuri)", 7, "summer", "야사카 신사 한 달간 이어지는 일본 최대급 마쓰리."),
        ("아오이 마쓰리", 5, "spring", "교토 3대 마쓰리. 헤이안 시대 의상 행렬."),
    ],
    "fukuoka": [
        ("하카타 기온 야마카사", 7, "summer", "거대한 가마(야마카사)를 메고 달리는 전통 축제."),
    ],
    "sapporo": [
        ("삿포로 눈축제 (Snow Festival)", 2, "winter", "오도리 공원의 대형 눈·얼음 조각 전시. 세계적 겨울 축제."),
    ],
    "bangkok": [
        ("송끄란 (Songkran)", 4, "spring", "태국 설. 도시 전역 물놀이 축제."),
        ("러이끄라통 (Loy Krathong)", 11, "autumn", "강에 등불(끄라통)을 띄우는 빛의 축제."),
    ],
    "chiangmai": [
        ("이펑 (Yi Peng) 풍등 축제", 11, "autumn", "수천 개의 풍등을 밤하늘에 띄우는 치앙마이 명물."),
    ],
    "singapore": [
        ("타이푸삼 (Thaipusam)", 1, "winter", "힌두 신앙 행렬 축제. 카바디 행진."),
        ("싱가포르 푸드 페스티벌", 8, "summer", "현지 호커 음식을 즐기는 미식 축제."),
    ],
    "taipei": [
        ("타이베이 등불축제 (Lantern Festival)", 2, "winter", "음력 정월대보름 대형 등불 전시."),
    ],
    "hongkong": [
        ("청차우 빵 축제 (Bun Festival)", 5, "spring", "빵 탑 오르기로 유명한 청차우섬 전통 축제."),
    ],
    "hanoi": [
        ("뗏 (Tết) 베트남 설", 2, "winter", "베트남 최대 명절. 꽃시장과 거리 장식."),
    ],
    "danang": [
        ("다낭 국제 불꽃 축제 (DIFF)", 6, "summer", "한강(Han River) 위 국가대항 불꽃 경연."),
    ],
    "bali": [
        ("녜피 (Nyepi) 침묵의 날", 3, "spring", "발리 힌두 새해. 하루 동안 섬 전체가 정적에 잠김."),
    ],
    "kualalumpur": [
        ("타이푸삼 (바투 동굴)", 1, "winter", "바투 동굴 계단을 오르는 대규모 힌두 순례 축제."),
    ],
    "paris": [
        ("음악 축제 (Fête de la Musique)", 6, "summer", "하지에 도시 곳곳에서 무료 길거리 공연."),
        ("프랑스 혁명 기념일 (Bastille Day)", 7, "summer", "군사 퍼레이드와 에펠탑 불꽃놀이."),
    ],
    "rome": [
        ("로마 건국 기념일 (Natale di Roma)", 4, "spring", "고대 로마 복식 행렬과 검투사 재현."),
    ],
    "barcelona": [
        ("라 메르세 (La Mercè)", 9, "autumn", "바르셀로나 수호성인 축제. 인간탑(카스텔)과 불꽃 행렬."),
        ("산트 조르디 (Sant Jordi)", 4, "spring", "책과 장미를 주고받는 카탈루냐의 날."),
    ],
    "london": [
        ("노팅힐 카니발 (Notting Hill Carnival)", 8, "summer", "유럽 최대급 카리브 거리 축제."),
    ],
    "amsterdam": [
        ("킹스데이 (Koningsdag)", 4, "spring", "국왕 생일. 도시 전체가 오렌지빛 거리 파티."),
    ],
    "newyork": [
        ("메이시스 추수감사절 퍼레이드", 11, "autumn", "대형 풍선 퍼레이드. 맨해튼 명물."),
        ("NYC 프라이드", 6, "summer", "세계 최대급 프라이드 퍼레이드."),
    ],
    "losangeles": [
        ("로즈 퍼레이드 (Rose Parade)", 1, "winter", "패서디나의 꽃 장식 신년 퍼레이드."),
    ],
    "dubai": [
        ("두바이 쇼핑 페스티벌 (DSF)", 1, "winter", "대규모 세일·불꽃·공연이 어우러진 쇼핑 축제."),
    ],
    "sydney": [
        ("비비드 시드니 (Vivid Sydney)", 5, "autumn", "오페라하우스 일대 빛·음악·아이디어 축제."),
        ("시드니 새해 불꽃축제", 12, "summer", "하버브리지 카운트다운 불꽃놀이."),
    ],
}

# 국가 scope 음식: country_code -> [(name, description)]
COUNTRY_FOODS: Dict[str, List[Tuple[str, str]]] = {
    "KR": [("김치", "발효 채소 반찬. 한식의 상징."), ("비빔밥", "밥에 나물·고기·고추장을 비벼 먹는 요리."), ("불고기", "양념한 소고기 구이."), ("떡볶이", "고추장 양념의 떡 분식.")],
    "JP": [("스시", "초밥. 신선한 생선과 식초밥."), ("라멘", "진한 육수의 일본식 면 요리."), ("텐푸라", "해산물·채소 튀김."), ("우동", "굵은 밀가루 면 요리.")],
    "TH": [("팟타이", "새콤달콤한 볶음 쌀국수."), ("똠얌꿍", "매콤새콤한 새우 수프."), ("그린 카레", "코코넛 베이스의 매운 카레."), ("망고 찰밥", "망고와 코코넛 찰밥 디저트.")],
    "SG": [("하이난 치킨라이스", "닭 육수밥과 부드러운 닭고기."), ("칠리 크랩", "매콤달콤 소스의 게 요리."), ("락사", "코코넛 커리 국수.")],
    "TW": [("우육면", "소고기 국수."), ("샤오롱바오", "육즙 가득 소룡포."), ("버블티", "타피오카 펄 밀크티."), ("지파이", "대형 닭튀김.")],
    "HK": [("딤섬", "한 입 크기 광둥식 점심 요리."), ("완탕면", "새우 완탕과 국수."), ("에그타르트", "포르투갈식 영향의 달걀 타르트.")],
    "VN": [("포 (쌀국수)", "맑은 육수의 베트남 쌀국수."), ("반미", "바게트 샌드위치."), ("분짜", "숯불 돼지고기와 면.")],
    "ID": [("나시고렝", "인도네시아식 볶음밥."), ("사테", "꼬치 구이."), ("렌당", "향신료 소고기 조림.")],
    "MY": [("나시 르막", "코코넛 밥과 삼발."), ("락사", "매콤한 커리 국수."), ("사테", "땅콩소스 꼬치 구이.")],
    "FR": [("크루아상", "버터 페이스트리."), ("바게트", "겉바속촉 프랑스 빵."), ("마카롱", "아몬드 머랭 과자."), ("에스카르고", "달팽이 버터 요리.")],
    "IT": [("파스타", "다양한 소스의 면 요리."), ("피자", "나폴리식 화덕 피자."), ("젤라또", "이탈리아식 아이스크림."), ("리조또", "쌀을 볶아 끓인 요리.")],
    "ES": [("파에야", "사프란 해물 쌀 요리."), ("타파스", "소량의 안주 모음."), ("하몽", "건조 숙성 햄.")],
    "GB": [("피시 앤 칩스", "생선튀김과 감자튀김."), ("선데이 로스트", "구운 고기와 채소 정찬."), ("애프터눈 티", "차와 스콘·디저트.")],
    "NL": [("스트룹와플", "시럽 채운 와플 과자."), ("비터발렌", "튀긴 고기 크로켓 안주."), ("청어 (하링)", "절인 생청어 길거리 음식.")],
    "US": [("햄버거", "패티 버거. 미국 대표 음식."), ("바비큐 (BBQ)", "훈제 고기 요리."), ("프라이드 치킨", "남부식 닭튀김.")],
    "AE": [("샤와르마", "회전구이 고기 랩."), ("마치부스", "향신료 쌀과 고기 요리."), ("후무스", "병아리콩 딥.")],
    "AU": [("미트 파이", "고기 속을 채운 파이."), ("배러먼디", "호주산 생선 구이."), ("랍스터·해산물", "신선한 해산물 바비큐.")],
}

# 도시 scope 음식: city_id -> [(name, description)]
CITY_FOODS: Dict[str, List[Tuple[str, str]]] = {
    "busan": [("돼지국밥", "부산 향토 돼지고기 국밥."), ("밀면", "부산식 밀가루 냉면.")],
    "jeju": [("흑돼지구이", "제주 흑돼지 숯불구이."), ("갈치조림", "제주 은갈치 매운 조림.")],
    "osaka": [("타코야키", "문어가 든 동그란 간식."), ("오코노미야키", "오사카식 부침 요리.")],
    "sapporo": [("미소라멘", "삿포로식 된장 라멘."), ("징기스칸", "양고기 철판 구이.")],
    "fukuoka": [("하카타 라멘", "돈코츠(돼지뼈) 라멘."), ("모츠나베", "곱창 전골.")],
    "kyoto": [("가이세키", "교토 정식 코스 요리."), ("유도후", "두부 전골.")],
    "chiangmai": [("카오소이", "북부 태국 커리 국수.")],
    "taipei": [("망고빙수", "대만식 망고 빙수."), ("펑리수", "파인애플 케이크.")],
    "hanoi": [("분짜", "하노이 대표 숯불고기 국수.")],
    "danang": [("미꽝", "중부 베트남 비빔 국수.")],
    "bali": [("바비굴링", "발리식 통돼지 구이.")],
    "newyork": [("뉴욕 피자", "넓고 얇은 조각 피자."), ("베이글", "뉴욕식 베이글."), ("치즈케이크", "뉴욕 스타일 치즈케이크.")],
    "losangeles": [("타코", "멕시칸 길거리 타코."), ("인앤아웃 버거", "캘리포니아 명물 버거.")],
}


def _hid(*parts: str) -> str:
    return hashlib.md5("::".join(parts).encode("utf-8")).hexdigest()[:16]


def main() -> int:
    graph = get_tourism_graph()
    if not graph.available:
        print("[seed] DB 미연결 — DATABASE_URL 을 확인하세요(호스트: 127.0.0.1:5432).")
        return 2
    graph.ensure_schema()

    cities = []
    for cid, (bbox, cc) in CITY_REGISTRY.items():
        lat = (bbox[0] + bbox[2]) / 2.0
        lon = (bbox[1] + bbox[3]) / 2.0
        cities.append({"id": cid, "name": cid.capitalize(), "country_code": cc, "lat": lat, "lon": lon})
    n_city = graph.upsert_cities(cities)

    festivals = []
    for cid, items in CITY_FESTIVALS.items():
        for (name, month, season, desc) in items:
            festivals.append({
                "id": f"{cid}:{_hid(cid, name)}",
                "city_id": cid,
                "name": name,
                "season": season,
                "month": month,
                "description": desc,
                "source": "curated",
                "license": "public-knowledge",
            })
    n_fest = graph.upsert_festivals(festivals)

    foods = []
    for cc, items in COUNTRY_FOODS.items():
        for (name, desc) in items:
            foods.append({
                "id": f"country:{cc}:{_hid(cc, name)}",
                "scope_type": "country",
                "scope_code": cc,
                "name": name,
                "description": desc,
                "source": "curated",
                "license": "public-knowledge",
            })
    for cid, items in CITY_FOODS.items():
        for (name, desc) in items:
            foods.append({
                "id": f"city:{cid}:{_hid(cid, name)}",
                "scope_type": "city",
                "scope_code": cid,
                "name": name,
                "description": desc,
                "source": "curated",
                "license": "public-knowledge",
            })
    n_food = graph.upsert_foods(foods)

    print(f"[seed] cities={n_city} festivals={n_fest} foods={n_food}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
