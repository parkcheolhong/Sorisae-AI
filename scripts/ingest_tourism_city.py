"""관광 KB PoC 적재기 — 도시 1곳 POI 를 OSM(Overpass) + Wikidata 에서 수집해 Qdrant 에 적재.

설계: docs/worldlinco-v2/TOURISM_AI_KNOWLEDGE_RAG_DESIGN.md
- 소스: OpenStreetMap(ODbL) 우선 + Wikidata(CC0) 보강. 둘 다 상업·TTS·저장·학습 허용.
- 저장: backend.services.tourism_kb 의 TourismVectorStore → Qdrant 'tourism_places'.
- 멱등(idempotent): source+source_id 해시로 point id 를 고정해 재실행 시 중복 없이 갱신.

사용:
  python scripts/ingest_tourism_city.py --city osaka
  python scripts/ingest_tourism_city.py --city seoul --limit 800
  python scripts/ingest_tourism_city.py --bbox 34.55,135.40,34.75,135.60 --country JP --name custom
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# repo 루트를 import 경로에 추가.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.services.tourism_kb import get_tourism_store  # noqa: E402

# (south, west, north, east), country_code — 전 세계 주요 관광도시(도심 코어 기준 bbox).
CITY_REGISTRY: Dict[str, Tuple[Tuple[float, float, float, float], str]] = {
    # 한국
    "seoul": ((37.45, 126.85, 37.65, 127.10), "KR"),
    "busan": ((35.06, 128.95, 35.24, 129.18), "KR"),
    "jeju": ((33.45, 126.45, 33.56, 126.62), "KR"),
    "incheon": ((37.40, 126.58, 37.55, 126.75), "KR"),
    # 일본
    "tokyo": ((35.62, 139.65, 35.73, 139.82), "JP"),
    "osaka": ((34.55, 135.40, 34.75, 135.60), "JP"),
    "kyoto": ((34.95, 135.68, 35.08, 135.83), "JP"),
    "fukuoka": ((33.53, 130.34, 33.66, 130.46), "JP"),
    "sapporo": ((43.02, 141.30, 43.10, 141.40), "JP"),
    # 동남아·대만·홍콩·싱가포르
    "bangkok": ((13.68, 100.45, 13.82, 100.60), "TH"),
    "chiangmai": ((18.74, 98.95, 18.83, 99.03), "TH"),
    "singapore": ((1.27, 103.78, 1.37, 103.90), "SG"),
    "taipei": ((25.00, 121.50, 25.10, 121.60), "TW"),
    "hongkong": ((22.26, 114.14, 22.34, 114.22), "HK"),
    "hanoi": ((20.98, 105.79, 21.06, 105.88), "VN"),
    "danang": ((16.02, 108.18, 16.10, 108.25), "VN"),
    "bali": ((-8.74, 115.14, -8.62, 115.28), "ID"),
    "kualalumpur": ((3.10, 101.66, 3.20, 101.74), "MY"),
    # 유럽
    "paris": ((48.82, 2.28, 48.90, 2.41), "FR"),
    "rome": ((41.86, 12.45, 41.94, 12.55), "IT"),
    "barcelona": ((41.36, 2.13, 41.43, 2.22), "ES"),
    "london": ((51.48, -0.18, 51.55, 0.00), "GB"),
    "amsterdam": ((52.34, 4.85, 52.40, 4.95), "NL"),
    # 미주·중동·오세아니아
    "newyork": ((40.70, -74.02, 40.80, -73.93), "US"),
    "losangeles": ((34.00, -118.30, 34.10, -118.20), "US"),
    "dubai": ((25.16, 55.24, 25.27, 55.36), "AE"),
    "sydney": ((-33.89, 151.18, -33.84, 151.24), "AU"),
}

# 카테고리 → 다국어 동의어. 일본어 고유명사 위주 POI 에 한·영·일 카테고리 신호를 주입해
# 'ramen/라멘/맛집' 같은 다국어 질의가 올바른 종류(식당)로 매칭되게 한다(양자화 임베딩 보강).
CATEGORY_SYNONYMS: Dict[str, str] = {
    "restaurant": "식당 레스토랑 맛집 음식점 restaurant レストラン 飲食店 グルメ 라멘 ramen",
    "cafe": "카페 커피 디저트 cafe coffee カフェ 喫茶店",
    "fast_food": "패스트푸드 분식 간식 fast food ファストフード",
    "bar": "바 술집 이자카야 호프 bar pub izakaya 居酒屋 バー",
    "pharmacy": "약국 드러그스토어 pharmacy drugstore 薬局 ドラッグストア",
    "hospital": "병원 의원 클리닉 hospital clinic 病院 クリニック",
    "bank": "은행 bank 銀行",
    "atm": "현금인출기 atm cash machine ATM 現金",
    "police": "경찰 파출소 지구대 police koban 交番 警察",
    "marketplace": "시장 재래시장 market 市場 マーケット",
    "hotel": "호텔 숙소 숙박 hotel accommodation ホテル 宿泊",
    "hostel": "호스텔 게스트하우스 숙소 hostel guesthouse ホステル",
    "guest_house": "게스트하우스 민박 숙소 guest house 民宿 ゲストハウス",
    "attraction": "관광 명소 가볼만한곳 attraction sightseeing 観光 観光地 名所",
    "museum": "박물관 미술관 museum gallery 博物館 美術館",
    "gallery": "미술관 갤러리 gallery art 美術館 ギャラリー",
    "viewpoint": "전망대 전망 뷰포인트 viewpoint scenic 展望台 景色",
    "theme_park": "테마파크 놀이공원 theme park amusement 遊園地 テーマパーク",
    "zoo": "동물원 zoo 動物園",
    "aquarium": "수족관 아쿠아리움 aquarium 水族館",
}


def _build_embed_text(place: Dict[str, Any]) -> str:
    """임베딩용 텍스트 = 이름 + 카테고리 다국어 동의어 + 주소. 카테고리 신호를 강하게."""
    cat = str(place.get("category") or "").strip()
    syn = CATEGORY_SYNONYMS.get(cat, cat)
    parts = [str(place.get("name") or "").strip(), syn, str(place.get("address") or "").strip()]
    return " · ".join(p for p in parts if p)


OVERPASS_ENDPOINT = "https://overpass-api.de/api/interpreter"
WIKIDATA_SPARQL = "https://query.wikidata.org/sparql"
USER_AGENT = "SorisaeAI-TourismKB/1.0 (PoC ingestion; OSM ODbL + Wikidata CC0)"

# 카테고리별 균형 수집 캡(관광객 질의 빈도 기준). 일본은 交番(police)·병원이 과밀해
# 단일 out 캡이면 식당·호텔·명소가 거의 안 잡히므로, 종류별로 따로 상한을 둔다.
# (key, value_regex, cap)
OSM_CATEGORY_CAPS = [
    ("tourism", "attraction|museum|gallery|viewpoint|theme_park|zoo|aquarium", 150),
    ("tourism", "hotel|hostel|guest_house", 80),
    ("amenity", "restaurant", 120),
    ("amenity", "cafe", 60),
    ("amenity", "bar|fast_food", 50),
    ("amenity", "pharmacy", 30),
    ("amenity", "hospital", 25),
    ("amenity", "bank|atm", 25),
    ("amenity", "marketplace", 20),
    ("amenity", "police", 10),
]


def _http_get_json(url: str, timeout: float = 60.0, data: Optional[bytes] = None) -> Any:
    req = urllib.request.Request(
        url,
        data=data,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        method="POST" if data else "GET",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def _assemble_address(tags: Dict[str, str]) -> str:
    parts = [
        tags.get("addr:housenumber"),
        tags.get("addr:street"),
        tags.get("addr:neighbourhood"),
        tags.get("addr:district"),
        tags.get("addr:city"),
        tags.get("addr:province") or tags.get("addr:state"),
        tags.get("addr:postcode"),
        tags.get("addr:country"),
    ]
    return ", ".join(p for p in parts if p)


def fetch_osm(bbox: Tuple[float, float, float, float], limit: int, country: str) -> List[Dict[str, Any]]:
    s, w, n, e = bbox
    bbox_str = f"{s},{w},{n},{e}"
    # 카테고리별로 개별 out 캡을 둬 균형 있게 수집(scale 인자로 전체 규모 조절).
    scale = max(0.2, min(3.0, limit / 500.0))
    blocks = []
    for key, val, cap in OSM_CATEGORY_CAPS:
        capped = max(5, int(cap * scale))
        blocks.append(f'( node["{key}"~"{val}"]["name"]({bbox_str}); ); out body {capped};')
    query = f"[out:json][timeout:90];" + "".join(blocks)
    url = OVERPASS_ENDPOINT
    data = urllib.parse.urlencode({"data": query}).encode("utf-8")
    print(f"[osm] Overpass 균형 조회 bbox={bbox_str} (scale={scale:.2f}) ...")
    payload = _http_get_json(url, timeout=120.0, data=data)
    elements = payload.get("elements", []) if isinstance(payload, dict) else []
    out: List[Dict[str, Any]] = []
    for el in elements:
        tags = el.get("tags", {}) or {}
        name = tags.get("name") or tags.get("name:en") or tags.get("name:ko")
        if not name or el.get("lat") is None or el.get("lon") is None:
            continue
        category = tags.get("tourism") or tags.get("amenity") or "poi"
        out.append({
            "source": "osm",
            "source_id": str(el.get("id")),
            "name": name,
            "lat": float(el["lat"]),
            "lon": float(el["lon"]),
            "category": category,
            "address": _assemble_address(tags),
            "country": country,
            "license": "ODbL (© OpenStreetMap contributors)",
            "phone": tags.get("phone") or tags.get("contact:phone"),
            "hours": tags.get("opening_hours"),
            "website": tags.get("website") or tags.get("contact:website"),
        })
    print(f"[osm] 수집 {len(out)}건")
    return out


def fetch_wikidata(bbox: Tuple[float, float, float, float], limit: int, country: str) -> List[Dict[str, Any]]:
    """Wikidata(CC0)에서 bbox 내 관광명소(분류: tourist attraction 등)를 SPARQL 로 수집."""
    s, w, n, e = bbox
    # 박스 코너(서남, 동북)로 wikibase:box 공간 필터.
    sparql = f"""
SELECT ?item ?itemLabel ?coord ?typeLabel WHERE {{
  SERVICE wikibase:box {{
    ?item wdt:P625 ?coord .
    bd:serviceParam wikibase:cornerSouthWest "Point({w} {s})"^^geo:wktLiteral .
    bd:serviceParam wikibase:cornerNorthEast "Point({e} {n})"^^geo:wktLiteral .
  }}
  ?item wdt:P31 ?type .
  VALUES ?type {{ wd:Q570116 wd:Q33506 wd:Q2065736 wd:Q839954 wd:Q4989906 }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "ko,en,ja". }}
}} LIMIT {int(limit)}
"""
    url = f"{WIKIDATA_SPARQL}?{urllib.parse.urlencode({'query': sparql, 'format': 'json'})}"
    print(f"[wikidata] SPARQL 조회 bbox={s},{w},{n},{e} limit={limit} ...")
    try:
        payload = _http_get_json(url, timeout=60.0)
    except Exception as exc:
        print(f"[wikidata] 조회 실패(건너뜀): {exc}")
        return []
    bindings = (((payload or {}).get("results") or {}).get("bindings")) or []
    out: List[Dict[str, Any]] = []
    for b in bindings:
        try:
            item_uri = b["item"]["value"]
            qid = item_uri.rsplit("/", 1)[-1]
            label = b.get("itemLabel", {}).get("value") or qid
            coord = b.get("coord", {}).get("value", "")  # 'Point(lon lat)'
            lon, lat = None, None
            if coord.startswith("Point("):
                nums = coord[len("Point("):-1].split()
                if len(nums) == 2:
                    lon, lat = float(nums[0]), float(nums[1])
            if lat is None or lon is None:
                continue
            out.append({
                "source": "wikidata",
                "source_id": qid,
                "name": label,
                "lat": lat,
                "lon": lon,
                "category": b.get("typeLabel", {}).get("value") or "attraction",
                "address": "",
                "country": country,
                "license": "CC0 (Wikidata)",
            })
        except Exception:
            continue
    print(f"[wikidata] 수집 {len(out)}건")
    return out


def ingest_city(
    label: str,
    bbox: Tuple[float, float, float, float],
    country: str,
    *,
    limit: int = 600,
    with_wikidata: bool = True,
    fresh: bool = False,
) -> Dict[str, Any]:
    """도시 1곳 수집→정제→임베딩→Qdrant 적재(멱등). 결과 요약 dict 반환.

    배치 드라이버(scripts/ingest_tourism_batch.py)와 CLI 양쪽에서 재사용한다.
    fresh=True 는 컬렉션 전체를 비우므로 다도시 배치에서는 쓰지 말 것(첫 도시만 차원 리셋용).
    """
    t0 = time.time()
    places = fetch_osm(bbox, limit, country)
    if with_wikidata:
        places += fetch_wikidata(bbox, min(limit, 300), country)
    if not places:
        return {"label": label, "ok": False, "count": 0, "reason": "no_data"}
    # QC 게이트 — 좌표범위·필수필드·중복 검증 후 정제(설계 §5-d ④).
    from backend.services.tourism_kb import validate_places

    places, qc = validate_places(places, bbox=bbox)
    print(
        f"[qc] total={qc['total']} kept={qc['kept']} dropped={qc['dropped']} "
        f"drop_rate={qc['drop_rate']} unknown_cat={qc['unknown_category']} reasons={qc['reasons']}"
    )
    if qc["blocked"]:
        return {
            "label": label, "ok": False, "count": 0,
            "reason": f"qc_blocked(kept={qc['kept']}, drop_rate={qc['drop_rate']})",
        }
    for p in places:
        p["text"] = _build_embed_text(p)
    store = get_tourism_store()
    if not store.available:
        return {"label": label, "ok": False, "count": 0, "reason": "qdrant_down"}
    if fresh:
        print(f"[qdrant] 컬렉션 초기화: '{store.collection}'")
        store.recreate()
    print(f"[qdrant] 임베딩+적재 시작: {len(places)}건 → '{store.collection}'")
    count = store.upsert_places(places)
    elapsed = time.time() - t0
    print(f"[done] '{label}' 적재 완료: {count}건 / 소요 {elapsed:.1f}s")
    return {"label": label, "ok": True, "count": count, "elapsed_sec": round(elapsed, 1)}


def resolve_target(args) -> Tuple[str, Tuple[float, float, float, float], str]:
    if args.city:
        bbox, country = CITY_REGISTRY[args.city]
        return args.city, bbox, country
    nums = [float(x) for x in args.bbox.split(",")]
    if len(nums) != 4:
        raise ValueError("--bbox 는 south,west,north,east 4개 값")
    return args.name, (nums[0], nums[1], nums[2], nums[3]), args.country


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--city", choices=sorted(CITY_REGISTRY.keys()), help="사전 등록 도시")
    ap.add_argument("--bbox", help="south,west,north,east (수동 지정)")
    ap.add_argument("--country", default="", help="국가코드(수동 bbox 시)")
    ap.add_argument("--name", default="custom", help="수동 bbox 라벨")
    ap.add_argument("--limit", type=int, default=600, help="소스별 최대 수집 건수")
    ap.add_argument("--no-wikidata", action="store_true", help="Wikidata 보강 생략")
    ap.add_argument("--fresh", action="store_true", help="적재 전 컬렉션 초기화(편향/차원 변경 시)")
    args = ap.parse_args()

    if not args.city and not args.bbox:
        ap.error("--city 또는 --bbox 중 하나는 필수")
    label, bbox, country = resolve_target(args)
    result = ingest_city(
        label, bbox, country,
        limit=args.limit, with_wikidata=not args.no_wikidata, fresh=args.fresh,
    )
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
