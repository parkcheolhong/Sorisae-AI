"""콘텐츠(사진·동영상) 저작권 게이트 — default-deny + 필수 출처표기.

법·윤리·품질 체크리스트 '콘텐츠 저작권' 항목.
원칙:
- **라이선스를 모르면 차단**(unknown/None/all-rights-reserved → deny).
- 상업 플랫폼이므로 **NonCommercial(NC) 라이선스는 차단**.
- 허용: 퍼블릭도메인/CC0, CC-BY 계열(BY/BY-SA/BY-ND, NC 미포함), 자체보유·상업허가(`owned`/`commercial`).
- CC-BY 계열·ND·상업허가는 **출처표기(attribution) 필수** → 표기 문자열을 생성해 함께 반환.
- 표시 레이어(모바일 `LicensedImage`)도 동일 규칙을 강제(이중 게이트).

이 모듈은 소스 비의존(미디어 디스크립터 dict 만 받음). 현재 앱은 지도·텍스트만 표시하므로
실데이터 유입은 없으나, 추후 Wikimedia/Wikidata 등 이미지 도입 시 이 게이트를 반드시 통과시킨다.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

# 퍼블릭도메인/CC0 — 표기 불필요(권장은 함).
_PUBLIC_DOMAIN = {
    "cc0", "cc0-1.0", "cc-0", "pd", "pdm", "publicdomain", "public-domain",
    "public domain", "no rights reserved", "wtfpl",
}
# 자체보유·상업 라이선스(외부 증빙 전제) — 표기 권장.
_OWNED = {"owned", "own", "self", "proprietary", "commercial", "licensed", "purchased", "stock-licensed"}

# 차단 신호.
_DENY_TOKENS = {"all rights reserved", "arr", "copyright", "©", "unknown", "none", "", "n/a", "tba"}

_CC_LICENSE_URLS = {
    "cc0": "https://creativecommons.org/publicdomain/zero/1.0/",
    "pd": "https://creativecommons.org/publicdomain/mark/1.0/",
}


def _norm(value: Optional[str]) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def _cc_components(license_norm: str) -> Optional[List[str]]:
    """'cc-by-sa-4.0' / 'cc by 4.0' / 'by-nc-nd' 등에서 BY/SA/NC/ND 토큰 추출. CC 아니면 None."""
    if "cc" not in license_norm and not license_norm.startswith("by"):
        return None
    tokens = re.split(r"[\s\-_/]+", license_norm)
    flags = [t for t in tokens if t in {"by", "sa", "nc", "nd"}]
    return flags or None


def _cc_label(flags: List[str]) -> str:
    return "CC " + "-".join(f.upper() for f in flags)


def _cc_url(flags: List[str], version: str = "4.0") -> str:
    path = "-".join(flags)
    return f"https://creativecommons.org/licenses/{path}/{version}/"


def _version_from(license_norm: str) -> str:
    m = re.search(r"(\d\.\d)", license_norm)
    return m.group(1) if m else "4.0"


def evaluate_media(item: Dict[str, Any]) -> Dict[str, Any]:
    """단일 미디어 디스크립터 평가.

    입력 키(유연): url|src, license|license_id, author|creator|attribution_author,
    source|provider, license_url, title, type(image|video).
    반환: allowed, license_id, license_label, requires_attribution, attribution,
          license_url, reason, (통과 시) url/type/title 보존.
    """
    license_raw = item.get("license") or item.get("license_id")
    license_norm = _norm(license_raw)
    url = item.get("url") or item.get("src")
    author = (item.get("author") or item.get("creator") or item.get("attribution_author") or "").strip()
    source = (item.get("source") or item.get("provider") or "").strip()
    title = (item.get("title") or "").strip()
    media_type = _norm(item.get("type")) or "image"

    base = {
        "url": url,
        "type": media_type,
        "title": title or None,
        "license_id": license_raw or None,
        "author": author or None,
        "source": source or None,
    }

    if not url:
        return {**base, "allowed": False, "reason": "missing url", "requires_attribution": False, "attribution": None, "license_label": None, "license_url": None}

    # default-deny: 라이선스 미상/저작권 보유 표기.
    if license_norm in _DENY_TOKENS:
        return {**base, "allowed": False, "reason": "unknown or all-rights-reserved license", "requires_attribution": False, "attribution": None, "license_label": None, "license_url": None}

    # 퍼블릭도메인/CC0.
    if license_norm in _PUBLIC_DOMAIN:
        label = "CC0" if "cc0" in license_norm or license_norm in {"cc-0"} else "Public Domain"
        return {
            **base, "allowed": True, "reason": "public domain / cc0",
            "license_label": label, "requires_attribution": False,
            "attribution": _build_attribution(author, label, source, required=False),
            "license_url": item.get("license_url") or _CC_LICENSE_URLS.get("cc0"),
        }

    # 자체보유·상업 허가.
    if license_norm in _OWNED:
        return {
            **base, "allowed": True, "reason": "owned / commercial license",
            "license_label": "Licensed (commercial)", "requires_attribution": bool(author or source),
            "attribution": _build_attribution(author, "Licensed", source, required=bool(author or source)),
            "license_url": item.get("license_url"),
        }

    # Creative Commons 계열.
    flags = _cc_components(license_norm)
    if flags:
        if "nc" in flags:
            return {**base, "allowed": False, "reason": "NonCommercial (NC) not allowed on commercial platform", "requires_attribution": False, "attribution": None, "license_label": _cc_label(flags), "license_url": None}
        if "by" not in flags:
            # 'cc' 만 있고 by 없음 → 모호 → 차단.
            return {**base, "allowed": False, "reason": "ambiguous CC license without BY", "requires_attribution": False, "attribution": None, "license_label": None, "license_url": None}
        if not author and not source:
            return {**base, "allowed": False, "reason": "CC-BY requires attribution (author/source missing)", "requires_attribution": True, "attribution": None, "license_label": _cc_label(flags), "license_url": _cc_url(flags, _version_from(license_norm))}
        label = _cc_label(flags)
        return {
            **base, "allowed": True, "reason": "cc-by family (non-NC)",
            "license_label": label, "requires_attribution": True,
            "attribution": _build_attribution(author, label, source, required=True),
            "license_url": item.get("license_url") or _cc_url(flags, _version_from(license_norm)),
        }

    # 그 외 미식별 라이선스 → 차단.
    return {**base, "allowed": False, "reason": f"unrecognized license: {license_raw!r}", "requires_attribution": False, "attribution": None, "license_label": None, "license_url": None}


def _build_attribution(author: str, license_label: str, source: str, *, required: bool) -> Optional[str]:
    if not (author or source):
        return None if required else f"{license_label}"
    parts = []
    if author:
        parts.append(author)
    bits = " / ".join([p for p in [", ".join(parts), license_label] if p])
    if source:
        bits = f"{bits} (via {source})" if bits else f"via {source}"
    return bits or None


def filter_media(items: Any) -> List[Dict[str, Any]]:
    """미디어 리스트에서 게이트 통과분만 반환(각 항목에 attribution/license_label 부착)."""
    if not isinstance(items, list):
        return []
    out: List[Dict[str, Any]] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        decision = evaluate_media(it)
        if decision.get("allowed"):
            out.append({
                "url": decision["url"],
                "type": decision["type"],
                "title": decision.get("title"),
                "author": decision.get("author"),
                "source": decision.get("source"),
                "license_id": decision.get("license_id"),
                "license_label": decision.get("license_label"),
                "license_url": decision.get("license_url"),
                "requires_attribution": decision.get("requires_attribution", False),
                "attribution": decision.get("attribution"),
            })
    return out


def gate_payload_media(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """POI payload 에 미디어성 필드가 있으면 게이트 통과분만 추출.

    지원 형태:
    - payload["media"] = [ {url, license, author, source, ...}, ... ]
    - 단일 평면 필드: image/image_url(+ image_license/image_author/image_source)
    """
    if not isinstance(payload, dict):
        return []
    candidates: List[Dict[str, Any]] = []
    if isinstance(payload.get("media"), list):
        candidates.extend([m for m in payload["media"] if isinstance(m, dict)])
    img = payload.get("image") or payload.get("image_url")
    if img:
        candidates.append({
            "url": img,
            "license": payload.get("image_license") or payload.get("license"),
            "author": payload.get("image_author"),
            "source": payload.get("image_source") or payload.get("source"),
            "license_url": payload.get("image_license_url"),
            "type": "image",
        })
    return filter_media(candidates)
