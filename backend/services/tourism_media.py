"""Wikimedia Commons / Wikidata 이미지 + 라이선스 연동 → 미디어 저작권 게이트 경유.

법·윤리·품질 체크리스트 '콘텐츠 저작권' 의 실연동 경로.
- 입력: POI payload 의 `wikimedia_commons`(예: 'File:Foo.jpg') 또는 `wikidata`(예: 'Q243').
- Wikidata P18(image) → Commons 파일명, 또는 commons 태그 직접 사용.
- Commons API(imageinfo + extmetadata)로 썸네일 URL·라이선스·작성자 취득.
- **media_license.filter_media** 로 default-deny 게이트 통과분만 반환(NC/미상 차단, CC-BY 출처표기 강제).
- 호출은 realtime_cache(ns='media', 7일) 캐시. 네트워크/파싱 실패는 fail-open(빈 리스트) → 추론 무영향.
"""

from __future__ import annotations

import json
import logging
import re
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_UA = "MetaNova-TourismBot/1.0 (https://devanalysis114.com; contact: ops@devanalysis114.com)"
_TIMEOUT = 6.0
_COMMONS_API = "https://commons.wikimedia.org/w/api.php"
_WIKIDATA_API = "https://www.wikidata.org/w/api.php"
_TAG_RE = re.compile(r"<[^>]+>")


def _http_json(url: str) -> Optional[dict]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": _UA, "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:  # noqa: S310 (고정 https 도메인)
            if resp.status != 200:
                return None
            return json.loads(resp.read().decode("utf-8", "ignore"))
    except Exception as exc:
        logger.debug("[tourism_media] http 실패: %s", exc)
        return None


def _strip_html(text: str) -> str:
    return _TAG_RE.sub("", str(text or "")).strip()


def _commons_filename(value: str) -> str:
    name = str(value or "").strip()
    if name.lower().startswith("file:"):
        name = name[5:]
    return name.strip().replace(" ", "_")


def _commons_image(filename: str, *, width: int = 800) -> Optional[Dict[str, Any]]:
    name = _commons_filename(filename)
    if not name:
        return None

    def _do() -> Optional[Dict[str, Any]]:
        params = {
            "action": "query", "format": "json", "prop": "imageinfo",
            "iiprop": "url|extmetadata", "iiurlwidth": str(width),
            "titles": f"File:{name}",
        }
        data = _http_json(f"{_COMMONS_API}?{urllib.parse.urlencode(params)}")
        pages = (((data or {}).get("query") or {}).get("pages")) or {}
        for _pid, page in pages.items():
            infos = page.get("imageinfo") or []
            if not infos:
                continue
            info = infos[0]
            meta = info.get("extmetadata") or {}

            def _m(key: str) -> str:
                return _strip_html((meta.get(key) or {}).get("value") or "")

            return {
                "url": info.get("thumburl") or info.get("url"),
                "license": _m("LicenseShortName") or _m("License"),
                "author": _m("Artist"),
                "source": "Wikimedia Commons",
                "license_url": (meta.get("LicenseUrl") or {}).get("value") or info.get("descriptionurl"),
                "title": name.replace("_", " "),
                "type": "image",
            }
        return None

    from backend.services.realtime_cache import cached_fetch

    return cached_fetch("media", ["commons", name, width], _do)


def _wikidata_p18(qid: str) -> Optional[str]:
    q = str(qid or "").strip()
    if not re.fullmatch(r"[Qq]\d+", q):
        return None

    def _do() -> Optional[str]:
        params = {"action": "wbgetclaims", "format": "json", "property": "P18", "entity": q.upper()}
        data = _http_json(f"{_WIKIDATA_API}?{urllib.parse.urlencode(params)}")
        claims = ((data or {}).get("claims") or {}).get("P18") or []
        for c in claims:
            val = (((c.get("mainsnak") or {}).get("datavalue") or {}).get("value"))
            if isinstance(val, str) and val.strip():
                return val.strip()
        return None

    from backend.services.realtime_cache import cached_fetch

    return cached_fetch("media", ["wikidata-p18", q.upper()], _do)


def place_media(payload: Dict[str, Any], *, max_items: int = 2) -> List[Dict[str, Any]]:
    """POI payload 에서 Wikimedia 이미지 디스크립터를 만들어 저작권 게이트 통과분만 반환.

    참조 우선순위: wikimedia_commons(직접 파일명) → wikidata(P18 조회).
    """
    if not isinstance(payload, dict):
        return []
    descriptors: List[Dict[str, Any]] = []

    commons_tag = payload.get("wikimedia_commons") or payload.get("commons")
    if commons_tag and not str(commons_tag).lower().startswith("category:"):
        info = _commons_image(str(commons_tag))
        if info:
            descriptors.append(info)

    if len(descriptors) < max_items:
        qid = payload.get("wikidata") or payload.get("wikidata_id")
        if qid:
            fname = _wikidata_p18(str(qid))
            if fname:
                info = _commons_image(fname)
                if info:
                    descriptors.append(info)

    from backend.services.media_license import filter_media

    return filter_media(descriptors)[:max_items]


def has_media_ref(payload: Dict[str, Any]) -> bool:
    """payload 에 이미지 참조(commons/wikidata)가 있는지 — 불필요한 네트워크 호출 방지용."""
    if not isinstance(payload, dict):
        return False
    return bool(
        (payload.get("wikimedia_commons") or payload.get("commons"))
        or (payload.get("wikidata") or payload.get("wikidata_id"))
    )
