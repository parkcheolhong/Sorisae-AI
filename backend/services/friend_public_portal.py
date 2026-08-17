import html
import math
import re
from typing import Any, Optional
from urllib.parse import parse_qsl, quote_plus, urlencode, urlsplit, urlunsplit
from xml.etree import ElementTree

import httpx

from backend.secret_store import read_secret_env
from backend.time_utils import utcnow


_HTML_TAG_RE = re.compile(r"<[^>]+>")

_MEDICAL_REGION_SIDO = (
    "서울특별시",
    "서울",
    "부산광역시",
    "부산",
    "대구광역시",
    "대구",
    "인천광역시",
    "인천",
    "광주광역시",
    "광주",
    "대전광역시",
    "대전",
    "울산광역시",
    "울산",
    "세종특별자치시",
    "세종",
    "경기도",
    "경기",
    "강원특별자치도",
    "강원",
    "충청북도",
    "충북",
    "충청남도",
    "충남",
    "전북특별자치도",
    "전북",
    "전라남도",
    "전남",
    "경상북도",
    "경북",
    "경상남도",
    "경남",
    "제주특별자치도",
    "제주",
)

_MEDICAL_REGION_SIGUNGU = (
    "강남구",
    "강동구",
    "강북구",
    "강서구",
    "관악구",
    "광진구",
    "구로구",
    "금천구",
    "노원구",
    "도봉구",
    "동대문구",
    "동작구",
    "마포구",
    "서대문구",
    "서초구",
    "성동구",
    "성북구",
    "송파구",
    "양천구",
    "영등포구",
    "용산구",
    "은평구",
    "종로구",
    "중구",
    "중랑구",
)

_MEDICAL_REGION_ALIASES = {
    "서울역": ("서울특별시", "중구"),
    "광화문": ("서울특별시", "종로구"),
    "종로": ("서울특별시", "종로구"),
    "명동": ("서울특별시", "중구"),
    "시청": ("서울특별시", "중구"),
    "용산역": ("서울특별시", "용산구"),
    "여의도": ("서울특별시", "영등포구"),
    "홍대": ("서울특별시", "마포구"),
    "홍대입구": ("서울특별시", "마포구"),
    "합정": ("서울특별시", "마포구"),
    "신촌": ("서울특별시", "서대문구"),
    "이대": ("서울특별시", "서대문구"),
    "건대": ("서울특별시", "광진구"),
    "왕십리": ("서울특별시", "성동구"),
    "강남": ("서울특별시", "강남구"),
    "강남역": ("서울특별시", "강남구"),
    "역삼": ("서울특별시", "강남구"),
    "선릉": ("서울특별시", "강남구"),
    "삼성역": ("서울특별시", "강남구"),
    "삼성동": ("서울특별시", "강남구"),
    "대치": ("서울특별시", "강남구"),
    "코엑스": ("서울특별시", "강남구"),
    "서초": ("서울특별시", "서초구"),
    "논현": ("서울특별시", "강남구"),
    "신사": ("서울특별시", "강남구"),
    "압구정": ("서울특별시", "강남구"),
    "잠실": ("서울특별시", "송파구"),
    "수서": ("서울특별시", "강남구"),
    "판교": ("경기도", "성남시"),
    "분당": ("경기도", "성남시"),
    "수원역": ("경기도", "수원시"),
    "부산역": ("부산광역시", "동구"),
    "해운대": ("부산광역시", "해운대구"),
    "센텀": ("부산광역시", "해운대구"),
    "동대구역": ("대구광역시", "동구"),
    "대전역": ("대전광역시", "동구"),
    "광주송정역": ("광주광역시", "광산구"),
    "인천공항": ("인천광역시", "중구"),
    "김포공항": ("서울특별시", "강서구"),
    "제주공항": ("제주특별자치도", "제주시"),
}

_MEDICAL_SPECIALTY_CODES = {
    "정신건강의학과": "D003",
    "정신과": "D003",
    "내과": "D001",
    "신경과": "D002",
    "외과": "D004",
    "정형외과": "D005",
    "신경외과": "D006",
    "산부인과": "D010",
    "소아청소년과": "D011",
    "소아과": "D011",
    "안과": "D012",
    "이비인후과": "D013",
    "피부과": "D014",
    "비뇨의학과": "D015",
    "비뇨기과": "D015",
    "영상의학과": "D016",
    "방사선과": "D016",
    "재활의학과": "D021",
    "가정의학과": "D023",
    "응급의학과": "D024",
    "치과": "D027",
    "한의원": "D028",
    "한방": "D028",
}

_MEDICAL_WEEKDAY_CODES = {
    "월요일": "1",
    "화요일": "2",
    "수요일": "3",
    "목요일": "4",
    "금요일": "5",
    "토요일": "6",
    "일요일": "7",
    "공휴일": "8",
    "월": "1",
    "화": "2",
    "수": "3",
    "목": "4",
    "금": "5",
    "토": "6",
    "일": "7",
}

_MEDICAL_SPECIALTY_KEYWORDS = tuple(_MEDICAL_SPECIALTY_CODES.keys())

_MEDICAL_CHILD_KEYWORDS = (
    "소아",
    "소아청소년",
    "어린이",
    "가족보건",
    "건강증진",
)

_MEDICAL_WEEKEND_KEYWORDS = (
    "토요일",
    "주말",
    "휴일",
)


def _strip_empty_query_params(url: str) -> str:
    rendered = str(url or "").strip()
    if not rendered or "?" not in rendered:
        return rendered
    split = urlsplit(rendered)
    query_pairs = parse_qsl(split.query, keep_blank_values=True)
    filtered = [
        (key, value)
        for key, value in query_pairs
        if str(value).strip()
    ]
    return urlunsplit(
        (
            split.scheme,
            split.netloc,
            split.path,
            urlencode(filtered),
            split.fragment,
        )
    )


def _infer_medical_query_context(
    query: str,
    overrides: Optional[dict[str, str]] = None,
) -> dict[str, str]:
    raw_query = str(query or "").strip()
    normalized = raw_query.replace("병·의원", "병원").replace("  ", " ")

    q0 = next(
        (name for name in _MEDICAL_REGION_SIDO if name in normalized),
        "",
    )
    q1 = next(
        (name for name in _MEDICAL_REGION_SIGUNGU if name in normalized),
        "",
    )
    if not q0 or not q1:
        for alias, (alias_q0, alias_q1) in _MEDICAL_REGION_ALIASES.items():
            if alias in normalized:
                q0 = q0 or alias_q0
                q1 = q1 or alias_q1
                break
    qd = next(
        (
            code
            for name, code in _MEDICAL_SPECIALTY_CODES.items()
            if name in normalized
        ),
        "",
    )
    qt = next(
        (
            code
            for name, code in _MEDICAL_WEEKDAY_CODES.items()
            if name in normalized
        ),
        "",
    )

    if "의원" in normalized or "클리닉" in normalized:
        qz = "C"
    elif any(token in normalized for token in ("병원", "의료원", "메디컬센터")):
        qz = "B"
    else:
        qz = ""

    qn = normalized
    for token in _MEDICAL_REGION_SIDO:
        qn = qn.replace(token, " ")
    for token in _MEDICAL_REGION_SIGUNGU:
        qn = qn.replace(token, " ")
    for token in _MEDICAL_SPECIALTY_CODES:
        qn = qn.replace(token, " ")
    for token in _MEDICAL_WEEKDAY_CODES:
        qn = qn.replace(token, " ")
    qn = qn.replace("병원", " ").replace("의원", " ").replace("클리닉", " ")
    qn = " ".join(qn.split())
    if len(qn) < 2:
        qn = raw_query

    if overrides:
        q0 = overrides.get("medical_q0", q0)
        q1 = overrides.get("medical_q1", q1)
        qd = overrides.get("medical_qd", qd)
        qt = overrides.get("medical_qt", qt)
        qn = overrides.get("medical_qn", qn)
        qz = overrides.get("medical_qz", qz)

    return {
        "medical_q0": q0,
        "medical_q1": q1,
        "medical_qd": qd,
        "medical_qt": qt,
        "medical_qz": qz,
        "medical_qn": qn,
    }


def _infer_medical_filters(
    query: str,
    overrides: Optional[dict[str, str]] = None,
) -> dict[str, str]:
    context = _infer_medical_query_context(query, overrides)

    return {
        key: quote_plus(value)
        for key, value in context.items()
    }


def _score_medical_item(
    query: str,
    item: dict[str, Any],
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
) -> tuple[int, str]:
    return _score_portal_item(
        "medical",
        query,
        item,
        latitude=latitude,
        longitude=longitude,
    )


def _rerank_items(
    label: str,
    query: str,
    items: list[dict[str, Any]],
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
) -> list[dict[str, Any]]:
    if len(items) <= 1:
        return items

    return sorted(
        items,
        key=lambda item: _score_portal_item(
            label,
            query,
            item,
            latitude=latitude,
            longitude=longitude,
        ),
        reverse=True,
    )


def _parse_xml_items(payload_text: str) -> list[dict[str, Any]]:
    text = str(payload_text or "").strip()
    if not text.startswith("<"):
        return []
    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError:
        return []

    items: list[dict[str, Any]] = []
    for item in root.findall(".//body/items/item"):
        record = {child.tag: child.text or "" for child in item}
        if record:
            items.append(record)
    return items


def _env_flag(name: str, default: str = "0") -> bool:
    value = read_secret_env(name, default=str(default or "")).strip()
    return value.lower() not in {"", "0", "false", "no", "off"}


def _clean_text(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    text = html.unescape(text)
    text = _HTML_TAG_RE.sub("", text)
    return " ".join(text.split())


def _extract_item_text(item: dict[str, Any], *keys: str) -> str:
    for key in keys:
        text = _clean_text(item.get(key))
        if text:
            return text
    return ""


def _extract_item_coords(
    item: dict[str, Any],
) -> tuple[Optional[float], Optional[float]]:
    coord_pairs = (
        ("wgs84Lat", "wgs84Lon"),
        ("mapy", "mapx"),
        ("latitude", "longitude"),
        ("lat", "lon"),
        ("y", "x"),
    )
    for lat_key, lon_key in coord_pairs:
        try:
            latitude = float(item.get(lat_key) or 0.0)
            longitude = float(item.get(lon_key) or 0.0)
        except (TypeError, ValueError):
            continue
        if latitude and longitude:
            return latitude, longitude
    return None, None


def _build_map_link(
    title: str,
    address: str,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
) -> str:
    if latitude is not None and longitude is not None:
        return (
            "https://www.google.com/maps/search/?api=1&query="
            f"{quote_plus(f'{latitude},{longitude}')}"
        )

    parts = []
    for part in (address, title):
        cleaned = _clean_text(part)
        if cleaned and cleaned not in parts:
            parts.append(cleaned)
    if not parts:
        return ""
    return (
        "https://www.google.com/maps/search/?api=1&query="
        f"{quote_plus(' '.join(parts[:2]))}"
    )


def _extract_query_terms(query: str) -> list[str]:
    terms = []
    for part in re.split(r"[\s,/]+", str(query or "").strip()):
        cleaned = _clean_text(part)
        if len(cleaned) >= 2 and cleaned not in terms:
            terms.append(cleaned)
    return terms


def _build_portal_haystack(label: str, item: dict[str, Any]) -> str:
    title = _extract_item_text(
        item,
        "title",
        "name",
        "koreanName",
        "airFln",
        "airlineKorean",
        "clcln_bzmn_trfc_mns_nm",
        "dutyName",
        "yadmNm",
    )
    address = _extract_item_text(
        item,
        "address",
        "addr1",
        "dutyAddr",
        "addr",
    )
    summary = _extract_item_text(
        item,
        "description",
        "overview",
        "remark",
        "rmkKor",
        "line",
        "clCdNm",
        "airport",
        "city",
        "boardingKor",
        "arrivedKor",
        "dutyDivNam",
        "dutyInf",
        "dutyEtc",
        "dutyMapimg",
    )
    extras: list[str] = []
    if label == "medical":
        extras.extend(
            _clean_text(item.get(key))
            for key in (
                "dutyInf",
                "dutyMapimg",
                "dutyEtc",
                "dutyDivNam",
            )
        )
        extras.extend(
            _clean_text(item.get(key))
            for key in (
                "dutyTime1s",
                "dutyTime2s",
                "dutyTime3s",
                "dutyTime4s",
                "dutyTime5s",
                "dutyTime6s",
                "dutyTime7s",
                "dutyTime8s",
            )
        )
    elif label == "flight":
        extras.extend(
            _clean_text(item.get(key))
            for key in (
                "airport",
                "city",
                "boardingKor",
                "boardingEng",
                "arrivedKor",
                "arrivedEng",
                "airlineKorean",
                "airlineEnglish",
                "rmkKor",
                "rmkEng",
            )
        )
    elif label == "transit":
        extras.extend(
            _clean_text(item.get(key))
            for key in (
                "clcln_bzmn_trfc_mns_nm",
                "clcln_bzmn_trfc_mns_cd",
            )
        )

    return " ".join(
        part for part in (title, address, summary, *extras) if part
    )


def _score_portal_item(
    label: str,
    query: str,
    item: dict[str, Any],
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
) -> tuple[int, str]:
    normalized_query = str(query or "").strip()
    title = _extract_item_text(
        item,
        "title",
        "name",
        "koreanName",
        "airFln",
        "airlineKorean",
        "clcln_bzmn_trfc_mns_nm",
        "dutyName",
        "yadmNm",
    )
    address = _extract_item_text(
        item,
        "address",
        "addr1",
        "dutyAddr",
        "addr",
    )
    haystack = _build_portal_haystack(label, item)
    score = 0

    if normalized_query:
        if normalized_query in title:
            score += 16
        elif normalized_query in haystack:
            score += 8

    for term in _extract_query_terms(normalized_query):
        if term in title:
            score += 4
        if term in address:
            score += 3
        if term in haystack:
            score += 2

    if label == "medical":
        context = _infer_medical_query_context(query)

        qn = context.get("medical_qn", "")
        if qn and qn in title:
            score += 20
        elif qn and qn in haystack:
            score += 12
        elif normalized_query and normalized_query in title:
            score += 10

        q0 = context.get("medical_q0", "")
        q1 = context.get("medical_q1", "")
        if q0 and q0 in address:
            score += 8
        if q1 and q1 in address:
            score += 10

        qz = context.get("medical_qz", "")
        div_name = _clean_text(item.get("dutyDivNam") or item.get("clCdNm"))
        if qz == "B" and any(token in div_name for token in ("병원", "의료원")):
            score += 12
        if qz == "C" and "의원" in div_name:
            score += 12

        qd = context.get("medical_qd", "")
        specialty_name = next(
            (
                name
                for name, code in _MEDICAL_SPECIALTY_CODES.items()
                if code == qd
            ),
            "",
        )
        if specialty_name and specialty_name in haystack:
            score += 14

        qt = context.get("medical_qt", "")
        weekend_query = any(
            keyword in normalized_query
            for keyword in _MEDICAL_WEEKEND_KEYWORDS
        )
        child_query = "소아" in normalized_query or "어린이" in normalized_query
        weekday_time_key = {
            "1": "dutyTime1s",
            "2": "dutyTime2s",
            "3": "dutyTime3s",
            "4": "dutyTime4s",
            "5": "dutyTime5s",
            "6": "dutyTime6s",
            "7": "dutyTime7s",
            "8": "dutyTime8s",
        }.get(qt, "")
        if weekday_time_key and str(item.get(weekday_time_key) or "").strip():
            score += 12
        if qt == "6" and str(item.get("dutyTime6c") or "").strip():
            score += 6
        if qt == "7" and str(item.get("dutyTime7c") or "").strip():
            score += 6
        if qt == "8" and str(item.get("dutyTime8c") or "").strip():
            score += 6

        info = _clean_text(
            item.get("dutyInf")
            or item.get("description")
            or item.get("overview")
        )
        map_info = _clean_text(item.get("dutyMapimg"))
        etc_info = _clean_text(item.get("dutyEtc"))
        for term in _extract_query_terms(normalized_query):
            if term in info:
                score += 4
            if term in map_info:
                score += 2
            if term in etc_info:
                score += 2
        if child_query and any(
            keyword in haystack for keyword in _MEDICAL_CHILD_KEYWORDS
        ):
            score += 10
        if weekend_query and any(
            keyword in haystack for keyword in _MEDICAL_WEEKEND_KEYWORDS
        ):
            score += 6

    elif label == "flight":
        if normalized_query and normalized_query in haystack:
            score += 6

    elif label == "transit":
        if normalized_query and normalized_query in haystack:
            score += 6

    elif label == "local":
        if normalized_query and normalized_query in address:
            score += 6

    item_lat, item_lng = _extract_item_coords(item)
    if (
        latitude is not None
        and longitude is not None
        and item_lat
        and item_lng
    ):
        distance = math.hypot(latitude - item_lat, longitude - item_lng)
        if distance < 0.01:
            score += 12
        elif distance < 0.03:
            score += 8
        elif distance < 0.08:
            score += 4

    return score, haystack


def _build_url(
    base_url: str,
    template: str,
    query: str,
    display: int,
    latitude: Optional[float],
    longitude: Optional[float],
    *,
    service_key: str,
    radius_m: int = 2000,
    category: str = "",
    country_code: str = "KR",
    medical_filters_overrides: Optional[dict[str, str]] = None,
) -> str:
    enc_query = quote_plus(query)
    medical_filters = _infer_medical_filters(query, medical_filters_overrides)
    digits_only = "".join(ch for ch in (query or "") if ch.isdigit())
    if len(digits_only) >= 8:
        query_yyyymmdd = digits_only[:8]
    else:
        query_yyyymmdd = utcnow().strftime("%Y%m%d")

    values = {
        "service_key": service_key,
        "query": query,
        "enc_query": enc_query,
        "query_yyyymmdd": query_yyyymmdd,
        "display": str(display),
        "start": "1",
        "radius_m": str(radius_m),
        "category": category,
        "country_code": country_code,
        "latitude": "" if latitude is None else str(latitude),
        "longitude": "" if longitude is None else str(longitude),
        **medical_filters,
    }
    rendered = _strip_empty_query_params(template.format(**values))
    if rendered.startswith("http://") or rendered.startswith("https://"):
        return rendered
    return f"{base_url.rstrip('/')}/{rendered.lstrip('/')}"


def _build_candidate_urls(
    label: str,
    base_url: str,
    template: str,
    query: str,
    display: int,
    latitude: Optional[float],
    longitude: Optional[float],
    *,
    service_key: str,
    radius_m: int = 2000,
    category: str = "",
    country_code: str = "KR",
) -> list[str]:
    candidates = [
        _build_url(
            base_url,
            template,
            query,
            display,
            latitude,
            longitude,
            service_key=service_key,
            radius_m=radius_m,
            category=category,
            country_code=country_code,
        )
    ]
    if label != "medical" or "HsptlAsembySearchService" not in template:
        if label == "local" and "locationBasedList2" in template:
            keyword_template = template.replace(
                "locationBasedList2",
                "searchKeyword2",
            )
            if "keyword=" not in keyword_template:
                keyword_template = f"{keyword_template}&keyword={{enc_query}}"
            keyword_candidate = _build_url(
                base_url,
                keyword_template,
                query,
                display,
                latitude,
                longitude,
                service_key=service_key,
                radius_m=radius_m,
                category=category,
                country_code=country_code,
            )
            if keyword_candidate not in candidates:
                candidates.append(keyword_candidate)
        return candidates

    relaxed_overrides = [
        {"medical_qn": ""},
        {"medical_qt": "", "medical_qn": ""},
        {"medical_qd": "", "medical_qt": "", "medical_qn": ""},
    ]
    for overrides in relaxed_overrides:
        candidate = _build_url(
            base_url,
            template,
            query,
            display,
            latitude,
            longitude,
            service_key=service_key,
            radius_m=radius_m,
            category=category,
            country_code=country_code,
            medical_filters_overrides=overrides,
        )
        if candidate not in candidates:
            candidates.append(candidate)
    return candidates


def _call_naver(
    url: str,
    client_id: str,
    client_secret: str,
    timeout_sec: float,
    auth_mode: str,
) -> list[dict[str, Any]]:
    lower_url = (url or "").lower()
    headers: dict[str, str] = {"Accept": "application/json"}
    is_public_data = "apis.data.go.kr" in lower_url

    if not is_public_data:
        mode = (auth_mode or "naver").strip().lower()
        if mode == "ncp":
            if not client_id or not client_secret:
                raise ValueError("ncp client key missing")
            headers.update(
                {
                    "X-NCP-APIGW-API-KEY-ID": client_id,
                    "X-NCP-APIGW-API-KEY": client_secret,
                }
            )
        elif not client_id or not client_secret:
            raise ValueError("naver client credentials missing")
        else:
            headers.update(
                {
                    "X-Naver-Client-Id": client_id,
                    "X-Naver-Client-Secret": client_secret,
                }
            )

    with httpx.Client(timeout=timeout_sec, follow_redirects=True) as client:
        response = client.get(url, headers=headers)
        response.raise_for_status()
        response_text = response.text

    try:
        payload = response.json()
    except ValueError:
        payload = None

    if payload is None:
        return _parse_xml_items(response_text)
    if not isinstance(payload, dict):
        return []
    if "Error" in payload and isinstance(payload.get("Error"), dict):
        return []

    items = payload.get("items")
    if isinstance(items, list):
        return [item for item in items if isinstance(item, dict)]

    response_obj = payload.get("response") or payload.get("Response")
    if isinstance(response_obj, dict):
        body = response_obj.get("body")
        if isinstance(body, dict):
            raw_items = body.get("items")
            if isinstance(raw_items, dict):
                raw_item = raw_items.get("item")
                if isinstance(raw_item, list):
                    return [
                        item for item in raw_item if isinstance(item, dict)
                    ]
                if isinstance(raw_item, dict):
                    return [raw_item]
            if isinstance(raw_items, list):
                return [item for item in raw_items if isinstance(item, dict)]

    return []


def _format_items(
    label: str,
    items: list[dict[str, Any]],
    max_items: int,
) -> list[str]:
    lines = [f"[{label}]"]
    if not items:
        lines.append("- no result")
        return lines
    for item in items[:max_items]:
        title = _clean_text(
            item.get("title")
            or item.get("name")
            or item.get("koreanName")
            or item.get("airFln")
            or item.get("clcln_bzmn_trfc_mns_nm")
            or item.get("airlineKorean")
            or item.get("dutyName")
            or item.get("yadmNm")
        )
        desc = _clean_text(
            item.get("description")
            or item.get("overview")
            or item.get("remark")
            or item.get("rmkKor")
            or item.get("line")
            or item.get("clCdNm")
            or item.get("airport")
            or item.get("city")
            or item.get("boardingKor")
            or item.get("arrivedKor")
            or item.get("dutyInf")
            or item.get("dutyEtc")
        )
        link = _clean_text(
            item.get("link")
            or item.get("homepage")
            or item.get("url")
            or item.get("hospUrl")
        )
        address = _clean_text(
            item.get("address")
            or item.get("addr1")
            or item.get("dutyAddr")
            or item.get("addr")
        )
        road_address = _clean_text(item.get("roadAddress"))
        latitude, longitude = _extract_item_coords(item)
        map_link = _build_map_link(
            title,
            road_address or address,
            latitude,
            longitude,
        )

        row_parts = []
        if title:
            row_parts.append(f"title={title}")
        if desc:
            row_parts.append(f"summary={desc}")
        if address or road_address:
            row_parts.append(f"address={road_address or address}")
        if latitude is not None and longitude is not None:
            row_parts.append(f"coords={latitude:.6f},{longitude:.6f}")
        if map_link:
            row_parts.append(f"map={map_link}")
        if link:
            row_parts.append(f"link={link}")

        if row_parts:
            lines.append("- " + " | ".join(row_parts))
    return lines


def fetch_friend_public_portal_grounding(
    query: str,
    *,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    max_items: int = 4,
    timeout_sec: float = 8.0,
) -> str:
    """Fetches real-time grounding snippets from Naver APIs for friend-chat.

    This function returns an empty string when disabled or unconfigured so
    callers can
    safely fall back to other grounding sources.
    """
    if not _env_flag("VOICE_FRIEND_PUBLIC_PORTAL_GROUNDING", "0"):
        return ""

    client_id = (
        read_secret_env("SORISAE_NAVER_API_CLIENT_ID", default="").strip()
    )
    client_secret = (
        read_secret_env("SORISAE_NAVER_API_CLIENT_SECRET", default="").strip()
    )

    base_url = read_secret_env(
        "SORISAE_NAVER_API_BASE_URL",
        default="https://openapi.naver.com",
    ).strip().rstrip("/")
    auth_mode = read_secret_env(
        "SORISAE_NAVER_API_AUTH_MODE",
        default="naver",
    ).strip().lower()
    display = max(1, min(max_items, 10))
    if not query.strip():
        return ""

    common_service_key = read_secret_env(
        "VOICE_FRIEND_PUBLIC_PORTAL_API_KEY",
        default="",
    ).strip()
    tour_service_key = (
        read_secret_env(
            "VOICE_FRIEND_PUBLIC_PORTAL_TOUR_API_KEY",
            default="",
        ).strip()
        or common_service_key
    )
    medical_service_key = (
        read_secret_env(
            "VOICE_FRIEND_PUBLIC_PORTAL_MEDICAL_API_KEY",
            default="",
        ).strip()
        or common_service_key
    )
    transit_service_key = (
        read_secret_env(
            "VOICE_FRIEND_PUBLIC_PORTAL_TRANSIT_API_KEY",
            default="",
        ).strip()
        or common_service_key
    )
    flight_service_key = (
        read_secret_env(
            "VOICE_FRIEND_PUBLIC_PORTAL_FLIGHT_API_KEY",
            default="",
        ).strip()
        or common_service_key
    )

    templates = [
        (
            "search",
            read_secret_env(
                "VOICE_FRIEND_PUBLIC_PORTAL_URL_TEMPLATE",
                default=(
                    "/v1/search/news.json?query={enc_query}&display={display}"
                    "&sort=date"
                ),
            ).strip(),
            common_service_key,
        ),
        (
            "flight",
            read_secret_env(
                "VOICE_FRIEND_PUBLIC_PORTAL_FLIGHT_URL_TEMPLATE",
                default=(
                    "https://apis.data.go.kr/B551178/flight-search?"
                    "serviceKey={service_key}"
                ),
            ).strip(),
            flight_service_key,
        ),
        (
            "local",
            read_secret_env(
                "VOICE_FRIEND_PUBLIC_PORTAL_TOUR_URL_TEMPLATE",
                default=(
                    "/v1/search/local.json?query={enc_query}&display={display}"
                    "&sort=random"
                ),
            ).strip(),
            tour_service_key,
        ),
        (
            "medical",
            read_secret_env(
                "VOICE_FRIEND_PUBLIC_PORTAL_MEDICAL_URL_TEMPLATE",
                default=(
                    "/v1/search/kin.json?query={enc_query}&display={display}"
                    "&sort=sim"
                ),
            ).strip(),
            medical_service_key,
        ),
        (
            "transit",
            read_secret_env(
                "VOICE_FRIEND_PUBLIC_PORTAL_TRANSIT_URL_TEMPLATE",
                default="",
            ).strip(),
            transit_service_key,
        ),
    ]

    sections: list[str] = ["[friend-public-portal-grounding]"]
    any_success = False
    for label, template, service_key in templates:
        if not template:
            sections.extend([f"[{label}]", "- template missing"])
            continue
        try:
            items: list[dict[str, Any]] = []
            candidate_urls = _build_candidate_urls(
                label,
                base_url,
                template,
                query,
                display,
                latitude,
                longitude,
                service_key=service_key,
                radius_m=2000,
                category="",
                country_code="KR",
            )
            for url in candidate_urls:
                items = _call_naver(
                    url,
                    client_id,
                    client_secret,
                    timeout_sec,
                    auth_mode=auth_mode,
                )
                items = _rerank_items(
                    label,
                    query,
                    items,
                    latitude=latitude,
                    longitude=longitude,
                )
                if items:
                    break
            sections.extend(_format_items(label, items, max_items))
            any_success = any_success or bool(items)
        except Exception as exc:
            sections.extend([f"[{label}]", f"- error={_clean_text(exc)}"])

    has_error = any(line.startswith("- error=") for line in sections)
    return "\n".join(sections) if (any_success or has_error) else ""
